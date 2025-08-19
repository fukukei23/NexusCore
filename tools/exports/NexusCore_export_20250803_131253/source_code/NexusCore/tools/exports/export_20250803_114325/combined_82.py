
# === NexusCore/openenv\Lib\site-packages\git\index\base.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Module containing :class:`IndexFile`, an Index implementation facilitating all kinds
of index manipulations such as querying and merging."""

__all__ = ["IndexFile", "CheckoutError", "StageType"]

import contextlib
import datetime
import glob
from io import BytesIO
import os
import os.path as osp
from stat import S_ISLNK
import subprocess
import sys
import tempfile

from gitdb.base import IStream
from gitdb.db import MemoryDB

from git.compat import defenc, force_bytes
import git.diff as git_diff
from git.exc import CheckoutError, GitCommandError, GitError, InvalidGitRepositoryError
from git.objects import Blob, Commit, Object, Submodule, Tree
from git.objects.util import Serializable
from git.util import (
    Actor,
    LazyMixin,
    LockedFD,
    join_path_native,
    file_contents_ro,
    to_native_path_linux,
    unbare_repo,
    to_bin_sha,
)

from .fun import (
    S_IFGITLINK,
    aggressive_tree_merge,
    entry_key,
    read_cache,
    run_commit_hook,
    stat_mode_to_index_mode,
    write_cache,
    write_tree_from_cache,
)
from .typ import BaseIndexEntry, IndexEntry, StageType
from .util import TemporaryFileSwap, post_clear_cache, default_index, git_working_dir

# typing -----------------------------------------------------------------------------

from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    Generator,
    IO,
    Iterable,
    Iterator,
    List,
    NoReturn,
    Sequence,
    TYPE_CHECKING,
    Tuple,
    Union,
)

from git.types import Literal, PathLike

if TYPE_CHECKING:
    from subprocess import Popen

    from git.refs.reference import Reference
    from git.repo import Repo


Treeish = Union[Tree, Commit, str, bytes]

# ------------------------------------------------------------------------------------


@contextlib.contextmanager
def _named_temporary_file_for_subprocess(directory: PathLike) -> Generator[str, None, None]:
    """Create a named temporary file git subprocesses can open, deleting it afterward.

    :param directory:
        The directory in which the file is created.

    :return:
        A context manager object that creates the file and provides its name on entry,
        and deletes it on exit.
    """
    if sys.platform == "win32":
        fd, name = tempfile.mkstemp(dir=directory)
        os.close(fd)
        try:
            yield name
        finally:
            os.remove(name)
    else:
        with tempfile.NamedTemporaryFile(dir=directory) as ctx:
            yield ctx.name


class IndexFile(LazyMixin, git_diff.Diffable, Serializable):
    """An Index that can be manipulated using a native implementation in order to save
    git command function calls wherever possible.

    This provides custom merging facilities allowing to merge without actually changing
    your index or your working tree. This way you can perform your own test merges based
    on the index only without having to deal with the working copy. This is useful in
    case of partial working trees.

    Entries:

        The index contains an entries dict whose keys are tuples of type
        :class:`~git.index.typ.IndexEntry` to facilitate access.

        You may read the entries dict or manipulate it using IndexEntry instance, i.e.::

            index.entries[index.entry_key(index_entry_instance)] = index_entry_instance

    Make sure you use :meth:`index.write() <write>` once you are done manipulating the
    index directly before operating on it using the git command.
    """

    __slots__ = ("repo", "version", "entries", "_extension_data", "_file_path")

    _VERSION = 2
    """The latest version we support."""

    S_IFGITLINK = S_IFGITLINK
    """Flags for a submodule."""

    def __init__(self, repo: "Repo", file_path: Union[PathLike, None] = None) -> None:
        """Initialize this Index instance, optionally from the given `file_path`.

        If no `file_path` is given, we will be created from the current index file.

        If a stream is not given, the stream will be initialized from the current
        repository's index on demand.
        """
        self.repo = repo
        self.version = self._VERSION
        self._extension_data = b""
        self._file_path: PathLike = file_path or self._index_path()

    def _set_cache_(self, attr: str) -> None:
        if attr == "entries":
            try:
                fd = os.open(self._file_path, os.O_RDONLY)
            except OSError:
                # In new repositories, there may be no index, which means we are empty.
                self.entries: Dict[Tuple[PathLike, StageType], IndexEntry] = {}
                return
            # END exception handling

            try:
                stream = file_contents_ro(fd, stream=True, allow_mmap=True)
            finally:
                os.close(fd)

            self._deserialize(stream)
        else:
            super()._set_cache_(attr)

    def _index_path(self) -> PathLike:
        if self.repo.git_dir:
            return join_path_native(self.repo.git_dir, "index")
        else:
            raise GitCommandError("No git directory given to join index path")

    @property
    def path(self) -> PathLike:
        """:return: Path to the index file we are representing"""
        return self._file_path

    def _delete_entries_cache(self) -> None:
        """Safely clear the entries cache so it can be recreated."""
        try:
            del self.entries
        except AttributeError:
            # It failed in Python 2.6.5 with AttributeError.
            # FIXME: Look into whether we can just remove this except clause now.
            pass
        # END exception handling

    # { Serializable Interface

    def _deserialize(self, stream: IO) -> "IndexFile":
        """Initialize this instance with index values read from the given stream."""
        self.version, self.entries, self._extension_data, _conten_sha = read_cache(stream)
        return self

    def _entries_sorted(self) -> List[IndexEntry]:
        """:return: List of entries, in a sorted fashion, first by path, then by stage"""
        return sorted(self.entries.values(), key=lambda e: (e.path, e.stage))

    def _serialize(self, stream: IO, ignore_extension_data: bool = False) -> "IndexFile":
        entries = self._entries_sorted()
        extension_data = self._extension_data  # type: Union[None, bytes]
        if ignore_extension_data:
            extension_data = None
        write_cache(entries, stream, extension_data)
        return self

    # } END serializable interface

    def write(
        self,
        file_path: Union[None, PathLike] = None,
        ignore_extension_data: bool = False,
    ) -> None:
        """Write the current state to our file path or to the given one.

        :param file_path:
            If ``None``, we will write to our stored file path from which we have been
            initialized. Otherwise we write to the given file path. Please note that
            this will change the `file_path` of this index to the one you gave.

        :param ignore_extension_data:
            If ``True``, the TREE type extension data read in the index will not be
            written to disk. NOTE that no extension data is actually written. Use this
            if you have altered the index and would like to use
            :manpage:`git-write-tree(1)` afterwards to create a tree representing your
            written changes. If this data is present in the written index,
            :manpage:`git-write-tree(1)` will instead write the stored/cached tree.
            Alternatively, use :meth:`write_tree` to handle this case automatically.
        """
        # Make sure we have our entries read before getting a write lock.
        # Otherwise it would be done when streaming.
        # This can happen if one doesn't change the index, but writes it right away.
        self.entries  # noqa: B018
        lfd = LockedFD(file_path or self._file_path)
        stream = lfd.open(write=True, stream=True)

        try:
            self._serialize(stream, ignore_extension_data)
        except BaseException:
            lfd.rollback()
            raise

        lfd.commit()

        # Make sure we represent what we have written.
        if file_path is not None:
            self._file_path = file_path

    @post_clear_cache
    @default_index
    def merge_tree(self, rhs: Treeish, base: Union[None, Treeish] = None) -> "IndexFile":
        """Merge the given `rhs` treeish into the current index, possibly taking
        a common base treeish into account.

        As opposed to the :func:`from_tree` method, this allows you to use an already
        existing tree as the left side of the merge.

        :param rhs:
            Treeish reference pointing to the 'other' side of the merge.

        :param base:
            Optional treeish reference pointing to the common base of `rhs` and this
            index which equals lhs.

        :return:
            self (containing the merge and possibly unmerged entries in case of
            conflicts)

        :raise git.exc.GitCommandError:
            If there is a merge conflict. The error will be raised at the first
            conflicting path. If you want to have proper merge resolution to be done by
            yourself, you have to commit the changed index (or make a valid tree from
            it) and retry with a three-way :meth:`index.from_tree <from_tree>` call.
        """
        # -i : ignore working tree status
        # --aggressive : handle more merge cases
        # -m : do an actual merge
        args: List[Union[Treeish, str]] = ["--aggressive", "-i", "-m"]
        if base is not None:
            args.append(base)
        args.append(rhs)

        self.repo.git.read_tree(args)
        return self

    @classmethod
    def new(cls, repo: "Repo", *tree_sha: Union[str, Tree]) -> "IndexFile":
        """Merge the given treeish revisions into a new index which is returned.

        This method behaves like ``git-read-tree --aggressive`` when doing the merge.

        :param repo:
            The repository treeish are located in.

        :param tree_sha:
            20 byte or 40 byte tree sha or tree objects.

        :return:
            New :class:`IndexFile` instance. Its path will be undefined.
            If you intend to write such a merged Index, supply an alternate
            ``file_path`` to its :meth:`write` method.
        """
        tree_sha_bytes: List[bytes] = [to_bin_sha(str(t)) for t in tree_sha]
        base_entries = aggressive_tree_merge(repo.odb, tree_sha_bytes)

        inst = cls(repo)
        # Convert to entries dict.
        entries: Dict[Tuple[PathLike, int], IndexEntry] = dict(
            zip(
                ((e.path, e.stage) for e in base_entries),
                (IndexEntry.from_base(e) for e in base_entries),
            )
        )

        inst.entries = entries
        return inst

    @classmethod
    def from_tree(cls, repo: "Repo", *treeish: Treeish, **kwargs: Any) -> "IndexFile":
        R"""Merge the given treeish revisions into a new index which is returned.
        The original index will remain unaltered.

        :param repo:
            The repository treeish are located in.

        :param treeish:
            One, two or three :class:`~git.objects.tree.Tree` objects,
            :class:`~git.objects.commit.Commit`\s or 40 byte hexshas.

            The result changes according to the amount of trees:

            1. If 1 Tree is given, it will just be read into a new index.
            2. If 2 Trees are given, they will be merged into a new index using a two
               way merge algorithm. Tree 1 is the 'current' tree, tree 2 is the 'other'
               one. It behaves like a fast-forward.
            3. If 3 Trees are given, a 3-way merge will be performed with the first tree
               being the common ancestor of tree 2 and tree 3. Tree 2 is the 'current'
               tree, tree 3 is the 'other' one.

        :param kwargs:
            Additional arguments passed to :manpage:`git-read-tree(1)`.

        :return:
            New :class:`IndexFile` instance. It will point to a temporary index location
            which does not exist anymore. If you intend to write such a merged Index,
            supply an alternate ``file_path`` to its :meth:`write` method.

        :note:
            In the three-way merge case, ``--aggressive`` will be specified to
            automatically resolve more cases in a commonly correct manner. Specify
            ``trivial=True`` as a keyword argument to override that.

            As the underlying :manpage:`git-read-tree(1)` command takes into account the
            current index, it will be temporarily moved out of the way to prevent any
            unexpected interference.
        """
        if len(treeish) == 0 or len(treeish) > 3:
            raise ValueError("Please specify between 1 and 3 treeish, got %i" % len(treeish))

        arg_list: List[Union[Treeish, str]] = []
        # Ignore that the working tree and index possibly are out of date.
        if len(treeish) > 1:
            # Drop unmerged entries when reading our index and merging.
            arg_list.append("--reset")
            # Handle non-trivial cases the way a real merge does.
            arg_list.append("--aggressive")
        # END merge handling

        # Create the temporary file in the .git directory to be sure renaming
        # works - /tmp/ directories could be on another device.
        with _named_temporary_file_for_subprocess(repo.git_dir) as tmp_index:
            arg_list.append("--index-output=%s" % tmp_index)
            arg_list.extend(treeish)

            # Move the current index out of the way - otherwise the merge may fail as it
            # considers existing entries. Moving it essentially clears the index.
            # Unfortunately there is no 'soft' way to do it.
            # The TemporaryFileSwap ensures the original file gets put back.
            with TemporaryFileSwap(join_path_native(repo.git_dir, "index")):
                repo.git.read_tree(*arg_list, **kwargs)
                index = cls(repo, tmp_index)
                index.entries  # noqa: B018 # Force it to read the file as we will delete the temp-file.
                return index
            # END index merge handling

    # UTILITIES

    @unbare_repo
    def _iter_expand_paths(self: "IndexFile", paths: Sequence[PathLike]) -> Iterator[PathLike]:
        """Expand the directories in list of paths to the corresponding paths
        accordingly.

        :note:
            git will add items multiple times even if a glob overlapped with manually
            specified paths or if paths where specified multiple times - we respect that
            and do not prune.
        """

        def raise_exc(e: Exception) -> NoReturn:
            raise e

        r = str(self.repo.working_tree_dir)
        rs = r + os.sep
        for path in paths:
            abs_path = str(path)
            if not osp.isabs(abs_path):
                abs_path = osp.join(r, path)
            # END make absolute path

            try:
                st = os.lstat(abs_path)  # Handles non-symlinks as well.
            except OSError:
                # The lstat call may fail as the path may contain globs as well.
                pass
            else:
                if S_ISLNK(st.st_mode):
                    yield abs_path.replace(rs, "")
                    continue
            # END check symlink

            # If the path is not already pointing to an existing file, resolve globs if possible.
            if not os.path.exists(abs_path) and ("?" in abs_path or "*" in abs_path or "[" in abs_path):
                resolved_paths = glob.glob(abs_path)
                # not abs_path in resolved_paths:
                #   A glob() resolving to the same path we are feeding it with is a
                #   glob() that failed to resolve. If we continued calling ourselves
                #   we'd endlessly recurse. If the condition below evaluates to true
                #   then we are likely dealing with a file whose name contains wildcard
                #   characters.
                if abs_path not in resolved_paths:
                    for f in self._iter_expand_paths(glob.glob(abs_path)):
                        yield str(f).replace(rs, "")
                    continue
            # END glob handling
            try:
                for root, _dirs, files in os.walk(abs_path, onerror=raise_exc):
                    for rela_file in files:
                        # Add relative paths only.
                        yield osp.join(root.replace(rs, ""), rela_file)
                    # END for each file in subdir
                # END for each subdirectory
            except OSError:
                # It was a file or something that could not be iterated.
                yield abs_path.replace(rs, "")
            # END path exception handling
        # END for each path

    def _write_path_to_stdin(
        self,
        proc: "Popen",
        filepath: PathLike,
        item: PathLike,
        fmakeexc: Callable[..., GitError],
        fprogress: Callable[[PathLike, bool, PathLike], None],
        read_from_stdout: bool = True,
    ) -> Union[None, str]:
        """Write path to ``proc.stdin`` and make sure it processes the item, including
        progress.

        :return:
            stdout string

        :param read_from_stdout:
            If ``True``, ``proc.stdout`` will be read after the item was sent to stdin.
            In that case, it will return ``None``.

        :note:
            There is a bug in :manpage:`git-update-index(1)` that prevents it from
            sending reports just in time. This is why we have a version that tries to
            read stdout and one which doesn't. In fact, the stdout is not important as
            the piped-in files are processed anyway and just in time.

        :note:
            Newlines are essential here, git's behaviour is somewhat inconsistent on
            this depending on the version, hence we try our best to deal with newlines
            carefully. Usually the last newline will not be sent, instead we will close
            stdin to break the pipe.
        """
        fprogress(filepath, False, item)
        rval: Union[None, str] = None

        if proc.stdin is not None:
            try:
                proc.stdin.write(("%s\n" % filepath).encode(defenc))
            except IOError as e:
                # Pipe broke, usually because some error happened.
                raise fmakeexc() from e
            # END write exception handling
            proc.stdin.flush()

        if read_from_stdout and proc.stdout is not None:
            rval = proc.stdout.readline().strip()
        fprogress(filepath, True, item)
        return rval

    def iter_blobs(
        self, predicate: Callable[[Tuple[StageType, Blob]], bool] = lambda t: True
    ) -> Iterator[Tuple[StageType, Blob]]:
        """
        :return:
            Iterator yielding tuples of :class:`~git.objects.blob.Blob` objects and
            stages, tuple(stage, Blob).

        :param predicate:
            Function(t) returning ``True`` if tuple(stage, Blob) should be yielded by
            the iterator. A default filter, the `~git.index.typ.BlobFilter`, allows you
            to yield blobs only if they match a given list of paths.
        """
        for entry in self.entries.values():
            blob = entry.to_blob(self.repo)
            blob.size = entry.size
            output = (entry.stage, blob)
            if predicate(output):
                yield output
        # END for each entry

    def unmerged_blobs(self) -> Dict[PathLike, List[Tuple[StageType, Blob]]]:
        """
        :return:
            Dict(path : list(tuple(stage, Blob, ...))), being a dictionary associating a
            path in the index with a list containing sorted stage/blob pairs.

        :note:
            Blobs that have been removed in one side simply do not exist in the given
            stage. That is, a file removed on the 'other' branch whose entries are at
            stage 3 will not have a stage 3 entry.
        """
        is_unmerged_blob = lambda t: t[0] != 0
        path_map: Dict[PathLike, List[Tuple[StageType, Blob]]] = {}
        for stage, blob in self.iter_blobs(is_unmerged_blob):
            path_map.setdefault(blob.path, []).append((stage, blob))
        # END for each unmerged blob
        for line in path_map.values():
            line.sort()

        return path_map

    @classmethod
    def entry_key(cls, *entry: Union[BaseIndexEntry, PathLike, StageType]) -> Tuple[PathLike, StageType]:
        return entry_key(*entry)

    def resolve_blobs(self, iter_blobs: Iterator[Blob]) -> "IndexFile":
        """Resolve the blobs given in blob iterator.

        This will effectively remove the index entries of the respective path at all
        non-null stages and add the given blob as new stage null blob.

        For each path there may only be one blob, otherwise a :exc:`ValueError` will be
        raised claiming the path is already at stage 0.

        :raise ValueError:
            If one of the blobs already existed at stage 0.

        :return:
            self

        :note:
            You will have to write the index manually once you are done, i.e.
            ``index.resolve_blobs(blobs).write()``.
        """
        for blob in iter_blobs:
            stage_null_key = (blob.path, 0)
            if stage_null_key in self.entries:
                raise ValueError("Path %r already exists at stage 0" % str(blob.path))
            # END assert blob is not stage 0 already

            # Delete all possible stages.
            for stage in (1, 2, 3):
                try:
                    del self.entries[(blob.path, stage)]
                except KeyError:
                    pass
                # END ignore key errors
            # END for each possible stage

            self.entries[stage_null_key] = IndexEntry.from_blob(blob)
        # END for each blob

        return self

    def update(self) -> "IndexFile":
        """Reread the contents of our index file, discarding all cached information
        we might have.

        :note:
            This is a possibly dangerous operations as it will discard your changes to
            :attr:`index.entries <entries>`.

        :return:
            self
        """
        self._delete_entries_cache()
        # Allows to lazily reread on demand.
        return self

    def write_tree(self) -> Tree:
        """Write this index to a corresponding :class:`~git.objects.tree.Tree` object
        into the repository's object database and return it.

        :return:
            :class:`~git.objects.tree.Tree` object representing this index.

        :note:
            The tree will be written even if one or more objects the tree refers to does
            not yet exist in the object database. This could happen if you added entries
            to the index directly.

        :raise ValueError:
            If there are no entries in the cache.

        :raise git.exc.UnmergedEntriesError:
        """
        # We obtain no lock as we just flush our contents to disk as tree.
        # If we are a new index, the entries access will load our data accordingly.
        mdb = MemoryDB()
        entries = self._entries_sorted()
        binsha, tree_items = write_tree_from_cache(entries, mdb, slice(0, len(entries)))

        # Copy changed trees only.
        mdb.stream_copy(mdb.sha_iter(), self.repo.odb)

        # Note: Additional deserialization could be saved if write_tree_from_cache would
        # return sorted tree entries.
        root_tree = Tree(self.repo, binsha, path="")
        root_tree._cache = tree_items
        return root_tree

    def _process_diff_args(
        self,
        args: List[Union[PathLike, "git_diff.Diffable"]],
    ) -> List[Union[PathLike, "git_diff.Diffable"]]:
        try:
            args.pop(args.index(self))
        except IndexError:
            pass
        # END remove self
        return args

    def _to_relative_path(self, path: PathLike) -> PathLike:
        """
        :return:
            Version of path relative to our git directory or raise :exc:`ValueError` if
            it is not within our git directory.

        :raise ValueError:
        """
        if not osp.isabs(path):
            return path
        if self.repo.bare:
            raise InvalidGitRepositoryError("require non-bare repository")
        if not osp.normpath(str(path)).startswith(str(self.repo.working_tree_dir)):
            raise ValueError("Absolute path %r is not in git repository at %r" % (path, self.repo.working_tree_dir))
        return os.path.relpath(path, self.repo.working_tree_dir)

    def _preprocess_add_items(
        self, items: Union[PathLike, Sequence[Union[PathLike, Blob, BaseIndexEntry, "Submodule"]]]
    ) -> Tuple[List[PathLike], List[BaseIndexEntry]]:
        """Split the items into two lists of path strings and BaseEntries."""
        paths = []
        entries = []
        # if it is a string put in list
        if isinstance(items, (str, os.PathLike)):
            items = [items]

        for item in items:
            if isinstance(item, (str, os.PathLike)):
                paths.append(self._to_relative_path(item))
            elif isinstance(item, (Blob, Submodule)):
                entries.append(BaseIndexEntry.from_blob(item))
            elif isinstance(item, BaseIndexEntry):
                entries.append(item)
            else:
                raise TypeError("Invalid Type: %r" % item)
        # END for each item
        return paths, entries

    def _store_path(self, filepath: PathLike, fprogress: Callable) -> BaseIndexEntry:
        """Store file at filepath in the database and return the base index entry.

        :note:
            This needs the :func:`~git.index.util.git_working_dir` decorator active!
            This must be ensured in the calling code.
        """
        st = os.lstat(filepath)  # Handles non-symlinks as well.
        if S_ISLNK(st.st_mode):
            # In PY3, readlink is a string, but we need bytes.
            # In PY2, it was just OS encoded bytes, we assumed UTF-8.
            open_stream: Callable[[], BinaryIO] = lambda: BytesIO(force_bytes(os.readlink(filepath), encoding=defenc))
        else:
            open_stream = lambda: open(filepath, "rb")
        with open_stream() as stream:
            fprogress(filepath, False, filepath)
            istream = self.repo.odb.store(IStream(Blob.type, st.st_size, stream))
            fprogress(filepath, True, filepath)
        return BaseIndexEntry(
            (
                stat_mode_to_index_mode(st.st_mode),
                istream.binsha,
                0,
                to_native_path_linux(filepath),
            )
        )

    @unbare_repo
    @git_working_dir
    def _entries_for_paths(
        self,
        paths: List[str],
        path_rewriter: Union[Callable, None],
        fprogress: Callable,
        entries: List[BaseIndexEntry],
    ) -> List[BaseIndexEntry]:
        entries_added: List[BaseIndexEntry] = []
        if path_rewriter:
            for path in paths:
                if osp.isabs(path):
                    abspath = path
                    gitrelative_path = path[len(str(self.repo.working_tree_dir)) + 1 :]
                else:
                    gitrelative_path = path
                    if self.repo.working_tree_dir:
                        abspath = osp.join(self.repo.working_tree_dir, gitrelative_path)
                # END obtain relative and absolute paths

                blob = Blob(
                    self.repo,
                    Blob.NULL_BIN_SHA,
                    stat_mode_to_index_mode(os.stat(abspath).st_mode),
                    to_native_path_linux(gitrelative_path),
                )
                # TODO: variable undefined
                entries.append(BaseIndexEntry.from_blob(blob))
            # END for each path
            del paths[:]
        # END rewrite paths

        # HANDLE PATHS
        assert len(entries_added) == 0
        for filepath in self._iter_expand_paths(paths):
            entries_added.append(self._store_path(filepath, fprogress))
        # END for each filepath
        # END path handling
        return entries_added

    def add(
        self,
        items: Union[PathLike, Sequence[Union[PathLike, Blob, BaseIndexEntry, "Submodule"]]],
        force: bool = True,
        fprogress: Callable = lambda *args: None,
        path_rewriter: Union[Callable[..., PathLike], None] = None,
        write: bool = True,
        write_extension_data: bool = False,
    ) -> List[BaseIndexEntry]:
        R"""Add files from the working tree, specific blobs, or
        :class:`~git.index.typ.BaseIndexEntry`\s to the index.

        :param items:
            Multiple types of items are supported, types can be mixed within one call.
            Different types imply a different handling. File paths may generally be
            relative or absolute.

            - path string

                Strings denote a relative or absolute path into the repository pointing
                to an existing file, e.g., ``CHANGES``, `lib/myfile.ext``,
                ``/home/gitrepo/lib/myfile.ext``.

                Absolute paths must start with working tree directory of this index's
                repository to be considered valid. For example, if it was initialized
                with a non-normalized path, like ``/root/repo/../repo``, absolute paths
                to be added must start with ``/root/repo/../repo``.

                Paths provided like this must exist. When added, they will be written
                into the object database.

                PathStrings may contain globs, such as ``lib/__init__*``. Or they can be
                directories like ``lib``, which will add all the files within the
                directory and subdirectories.

                This equals a straight :manpage:`git-add(1)`.

                They are added at stage 0.

            - :class:~`git.objects.blob.Blob` or
              :class:`~git.objects.submodule.base.Submodule` object

                Blobs are added as they are assuming a valid mode is set.

                The file they refer to may or may not exist in the file system, but must
                be a path relative to our repository.

                If their sha is null (40*0), their path must exist in the file system
                relative to the git repository as an object will be created from the
                data at the path.

                The handling now very much equals the way string paths are processed,
                except that the mode you have set will be kept. This allows you to
                create symlinks by settings the mode respectively and writing the target
                of the symlink directly into the file. This equals a default Linux
                symlink which is not dereferenced automatically, except that it can be
                created on filesystems not supporting it as well.

                Please note that globs or directories are not allowed in
                :class:`~git.objects.blob.Blob` objects.

                They are added at stage 0.

            - :class:`~git.index.typ.BaseIndexEntry` or type

                Handling equals the one of :class:~`git.objects.blob.Blob` objects, but
                the stage may be explicitly set. Please note that Index Entries require
                binary sha's.

        :param force:
            **CURRENTLY INEFFECTIVE**
            If ``True``, otherwise ignored or excluded files will be added anyway. As
            opposed to the :manpage:`git-add(1)` command, we enable this flag by default
            as the API user usually wants the item to be added even though they might be
            excluded.

        :param fprogress:
            Function with signature ``f(path, done=False, item=item)`` called for each
            path to be added, one time once it is about to be added where ``done=False``
            and once after it was added where ``done=True``.

            ``item`` is set to the actual item we handle, either a path or a
            :class:`~git.index.typ.BaseIndexEntry`.

            Please note that the processed path is not guaranteed to be present in the
            index already as the index is currently being processed.

        :param path_rewriter:
            Function, with signature ``(string) func(BaseIndexEntry)``, returning a path
            for each passed entry which is the path to be actually recorded for the
            object created from :attr:`entry.path <git.index.typ.BaseIndexEntry.path>`.
            This allows you to write an index which is not identical to the layout of
            the actual files on your hard-disk. If not ``None`` and `items` contain
            plain paths, these paths will be converted to Entries beforehand and passed
            to the path_rewriter. Please note that ``entry.path`` is relative to the git
            repository.

        :param write:
            If ``True``, the index will be written once it was altered. Otherwise the
            changes only exist in memory and are not available to git commands.

        :param write_extension_data:
            If ``True``, extension data will be written back to the index. This can lead
            to issues in case it is containing the 'TREE' extension, which will cause
            the :manpage:`git-commit(1)` command to write an old tree, instead of a new
            one representing the now changed index.

            This doesn't matter if you use :meth:`IndexFile.commit`, which ignores the
            'TREE' extension altogether. You should set it to ``True`` if you intend to
            use :meth:`IndexFile.commit` exclusively while maintaining support for
            third-party extensions. Besides that, you can usually safely ignore the
            built-in extensions when using GitPython on repositories that are not
            handled manually at all.

            All current built-in extensions are listed here:
            https://git-scm.com/docs/index-format

        :return:
            List of :class:`~git.index.typ.BaseIndexEntry`\s representing the entries
            just actually added.

        :raise OSError:
            If a supplied path did not exist. Please note that
            :class:`~git.index.typ.BaseIndexEntry` objects that do not have a null sha
            will be added even if their paths do not exist.
        """
        # Sort the entries into strings and Entries.
        # Blobs are converted to entries automatically.
        # Paths can be git-added. For everything else we use git-update-index.
        paths, entries = self._preprocess_add_items(items)
        entries_added: List[BaseIndexEntry] = []
        # This code needs a working tree, so we try not to run it unless required.
        # That way, we are OK on a bare repository as well.
        # If there are no paths, the rewriter has nothing to do either.
        if paths:
            entries_added.extend(self._entries_for_paths(paths, path_rewriter, fprogress, entries))

        # HANDLE ENTRIES
        if entries:
            null_mode_entries = [e for e in entries if e.mode == 0]
            if null_mode_entries:
                raise ValueError(
                    "At least one Entry has a null-mode - please use index.remove to remove files for clarity"
                )
            # END null mode should be remove

            # HANDLE ENTRY OBJECT CREATION
            # Create objects if required, otherwise go with the existing shas.
            null_entries_indices = [i for i, e in enumerate(entries) if e.binsha == Object.NULL_BIN_SHA]
            if null_entries_indices:

                @git_working_dir
                def handle_null_entries(self: "IndexFile") -> None:
                    for ei in null_entries_indices:
                        null_entry = entries[ei]
                        new_entry = self._store_path(null_entry.path, fprogress)

                        # Update null entry.
                        entries[ei] = BaseIndexEntry(
                            (
                                null_entry.mode,
                                new_entry.binsha,
                                null_entry.stage,
                                null_entry.path,
                            )
                        )
                    # END for each entry index

                # END closure

                handle_null_entries(self)
            # END null_entry handling

            # REWRITE PATHS
            # If we have to rewrite the entries, do so now, after we have generated all
            # object sha's.
            if path_rewriter:
                for i, e in enumerate(entries):
                    entries[i] = BaseIndexEntry((e.mode, e.binsha, e.stage, path_rewriter(e)))
                # END for each entry
            # END handle path rewriting

            # Just go through the remaining entries and provide progress info.
            for i, entry in enumerate(entries):
                progress_sent = i in null_entries_indices
                if not progress_sent:
                    fprogress(entry.path, False, entry)
                    fprogress(entry.path, True, entry)
                # END handle progress
            # END for each entry
            entries_added.extend(entries)
        # END if there are base entries

        # FINALIZE
        # Add the new entries to this instance.
        for entry in entries_added:
            self.entries[(entry.path, 0)] = IndexEntry.from_base(entry)

        if write:
            self.write(ignore_extension_data=not write_extension_data)
        # END handle write

        return entries_added

    def _items_to_rela_paths(
        self,
        items: Union[PathLike, Sequence[Union[PathLike, BaseIndexEntry, Blob, Submodule]]],
    ) -> List[PathLike]:
        """Returns a list of repo-relative paths from the given items which
        may be absolute or relative paths, entries or blobs."""
        paths = []
        # If string, put in list.
        if isinstance(items, (str, os.PathLike)):
            items = [items]

        for item in items:
            if isinstance(item, (BaseIndexEntry, (Blob, Submodule))):
                paths.append(self._to_relative_path(item.path))
            elif isinstance(item, (str, os.PathLike)):
                paths.append(self._to_relative_path(item))
            else:
                raise TypeError("Invalid item type: %r" % item)
        # END for each item
        return paths

    @post_clear_cache
    @default_index
    def remove(
        self,
        items: Union[PathLike, Sequence[Union[PathLike, Blob, BaseIndexEntry, "Submodule"]]],
        working_tree: bool = False,
        **kwargs: Any,
    ) -> List[str]:
        R"""Remove the given items from the index and optionally from the working tree
        as well.

        :param items:
            Multiple types of items are supported which may be be freely mixed.

            - path string

                Remove the given path at all stages. If it is a directory, you must
                specify the ``r=True`` keyword argument to remove all file entries below
                it. If absolute paths are given, they will be converted to a path
                relative to the git repository directory containing the working tree

                The path string may include globs, such as ``*.c``.

            - :class:~`git.objects.blob.Blob` object

                Only the path portion is used in this case.

            - :class:`~git.index.typ.BaseIndexEntry` or compatible type

                The only relevant information here is the path. The stage is ignored.

        :param working_tree:
            If ``True``, the entry will also be removed from the working tree,
            physically removing the respective file. This may fail if there are
            uncommitted changes in it.

        :param kwargs:
            Additional keyword arguments to be passed to :manpage:`git-rm(1)`, such as
            ``r`` to allow recursive removal.

        :return:
            List(path_string, ...) list of repository relative paths that have been
            removed effectively.

            This is interesting to know in case you have provided a directory or globs.
            Paths are relative to the repository.
        """
        args = []
        if not working_tree:
            args.append("--cached")
        args.append("--")

        # Preprocess paths.
        paths = self._items_to_rela_paths(items)
        removed_paths = self.repo.git.rm(args, paths, **kwargs).splitlines()

        # Process output to gain proper paths.
        # rm 'path'
        return [p[4:-1] for p in removed_paths]

    @post_clear_cache
    @default_index
    def move(
        self,
        items: Union[PathLike, Sequence[Union[PathLike, Blob, BaseIndexEntry, "Submodule"]]],
        skip_errors: bool = False,
        **kwargs: Any,
    ) -> List[Tuple[str, str]]:
        """Rename/move the items, whereas the last item is considered the destination of
        the move operation.

        If the destination is a file, the first item (of two) must be a file as well.

        If the destination is a directory, it may be preceded by one or more directories
        or files.

        The working tree will be affected in non-bare repositories.

        :param items:
            Multiple types of items are supported, please see the :meth:`remove` method
            for reference.

        :param skip_errors:
            If ``True``, errors such as ones resulting from missing source files will be
            skipped.

        :param kwargs:
            Additional arguments you would like to pass to :manpage:`git-mv(1)`, such as
            ``dry_run`` or ``force``.

        :return:
            List(tuple(source_path_string, destination_path_string), ...)

            A list of pairs, containing the source file moved as well as its actual
            destination. Relative to the repository root.

        :raise ValueError:
            If only one item was given.

        :raise git.exc.GitCommandError:
            If git could not handle your request.
        """
        args = []
        if skip_errors:
            args.append("-k")

        paths = self._items_to_rela_paths(items)
        if len(paths) < 2:
            raise ValueError("Please provide at least one source and one destination of the move operation")

        was_dry_run = kwargs.pop("dry_run", kwargs.pop("n", None))
        kwargs["dry_run"] = True

        # First execute rename in dry run so the command tells us what it actually does
        # (for later output).
        out = []
        mvlines = self.repo.git.mv(args, paths, **kwargs).splitlines()

        # Parse result - first 0:n/2 lines are 'checking ', the remaining ones are the
        # 'renaming' ones which we parse.
        for ln in range(int(len(mvlines) / 2), len(mvlines)):
            tokens = mvlines[ln].split(" to ")
            assert len(tokens) == 2, "Too many tokens in %s" % mvlines[ln]

            # [0] = Renaming x
            # [1] = y
            out.append((tokens[0][9:], tokens[1]))
        # END for each line to parse

        # Either prepare for the real run, or output the dry-run result.
        if was_dry_run:
            return out
        # END handle dry run

        # Now apply the actual operation.
        kwargs.pop("dry_run")
        self.repo.git.mv(args, paths, **kwargs)

        return out

    def commit(
        self,
        message: str,
        parent_commits: Union[List[Commit], None] = None,
        head: bool = True,
        author: Union[None, Actor] = None,
        committer: Union[None, Actor] = None,
        author_date: Union[datetime.datetime, str, None] = None,
        commit_date: Union[datetime.datetime, str, None] = None,
        skip_hooks: bool = False,
    ) -> Commit:
        """Commit the current default index file, creating a
        :class:`~git.objects.commit.Commit` object.

        For more information on the arguments, see
        :meth:`Commit.create_from_tree <git.objects.commit.Commit.create_from_tree>`.

        :note:
            If you have manually altered the :attr:`entries` member of this instance,
            don't forget to :meth:`write` your changes to disk beforehand.

        :note:
            Passing ``skip_hooks=True`` is the equivalent of using ``-n`` or
            ``--no-verify`` on the command line.

        :return:
            :class:`~git.objects.commit.Commit` object representing the new commit
        """
        if not skip_hooks:
            run_commit_hook("pre-commit", self)

            self._write_commit_editmsg(message)
            run_commit_hook("commit-msg", self, self._commit_editmsg_filepath())
            message = self._read_commit_editmsg()
            self._remove_commit_editmsg()
        tree = self.write_tree()
        rval = Commit.create_from_tree(
            self.repo,
            tree,
            message,
            parent_commits,
            head,
            author=author,
            committer=committer,
            author_date=author_date,
            commit_date=commit_date,
        )
        if not skip_hooks:
            run_commit_hook("post-commit", self)
        return rval

    def _write_commit_editmsg(self, message: str) -> None:
        with open(self._commit_editmsg_filepath(), "wb") as commit_editmsg_file:
            commit_editmsg_file.write(message.encode(defenc))

    def _remove_commit_editmsg(self) -> None:
        os.remove(self._commit_editmsg_filepath())

    def _read_commit_editmsg(self) -> str:
        with open(self._commit_editmsg_filepath(), "rb") as commit_editmsg_file:
            return commit_editmsg_file.read().decode(defenc)

    def _commit_editmsg_filepath(self) -> str:
        return osp.join(self.repo.common_dir, "COMMIT_EDITMSG")

    def _flush_stdin_and_wait(cls, proc: "Popen[bytes]", ignore_stdout: bool = False) -> bytes:
        stdin_IO = proc.stdin
        if stdin_IO:
            stdin_IO.flush()
            stdin_IO.close()

        stdout = b""
        if not ignore_stdout and proc.stdout:
            stdout = proc.stdout.read()

        if proc.stdout:
            proc.stdout.close()
            proc.wait()
        return stdout

    @default_index
    def checkout(
        self,
        paths: Union[None, Iterable[PathLike]] = None,
        force: bool = False,
        fprogress: Callable = lambda *args: None,
        **kwargs: Any,
    ) -> Union[None, Iterator[PathLike], Sequence[PathLike]]:
        """Check out the given paths or all files from the version known to the index
        into the working tree.

        :note:
            Be sure you have written pending changes using the :meth:`write` method in
            case you have altered the entries dictionary directly.

        :param paths:
            If ``None``, all paths in the index will be checked out.
            Otherwise an iterable of relative or absolute paths or a single path
            pointing to files or directories in the index is expected.

        :param force:
            If ``True``, existing files will be overwritten even if they contain local
            modifications.
            If ``False``, these will trigger a :exc:`~git.exc.CheckoutError`.

        :param fprogress:
            See :meth:`IndexFile.add` for signature and explanation.

            The provided progress information will contain ``None`` as path and item if
            no explicit paths are given. Otherwise progress information will be send
            prior and after a file has been checked out.

        :param kwargs:
            Additional arguments to be passed to :manpage:`git-checkout-index(1)`.

        :return:
            Iterable yielding paths to files which have been checked out and are
            guaranteed to match the version stored in the index.

        :raise git.exc.CheckoutError:
            * If at least one file failed to be checked out. This is a summary, hence it
              will checkout as many files as it can anyway.
            * If one of files or directories do not exist in the index (as opposed to
              the original git command, which ignores them).

        :raise git.exc.GitCommandError:
            If error lines could not be parsed - this truly is an exceptional state.

        :note:
            The checkout is limited to checking out the files in the index. Files which
            are not in the index anymore and exist in the working tree will not be
            deleted. This behaviour is fundamentally different to ``head.checkout``,
            i.e. if you want :manpage:`git-checkout(1)`-like behaviour, use
            ``head.checkout`` instead of ``index.checkout``.
        """
        args = ["--index"]
        if force:
            args.append("--force")

        failed_files = []
        failed_reasons = []
        unknown_lines = []

        def handle_stderr(proc: "Popen[bytes]", iter_checked_out_files: Iterable[PathLike]) -> None:
            stderr_IO = proc.stderr
            if not stderr_IO:
                return  # Return early if stderr empty.

            stderr_bytes = stderr_IO.read()
            # line contents:
            stderr = stderr_bytes.decode(defenc)
            # git-checkout-index: this already exists
            endings = (
                " already exists",
                " is not in the cache",
                " does not exist at stage",
                " is unmerged",
            )
            for line in stderr.splitlines():
                if not line.startswith("git checkout-index: ") and not line.startswith("git-checkout-index: "):
                    is_a_dir = " is a directory"
                    unlink_issue = "unable to unlink old '"
                    already_exists_issue = " already exists, no checkout"  # created by entry.c:checkout_entry(...)
                    if line.endswith(is_a_dir):
                        failed_files.append(line[: -len(is_a_dir)])
                        failed_reasons.append(is_a_dir)
                    elif line.startswith(unlink_issue):
                        failed_files.append(line[len(unlink_issue) : line.rfind("'")])
                        failed_reasons.append(unlink_issue)
                    elif line.endswith(already_exists_issue):
                        failed_files.append(line[: -len(already_exists_issue)])
                        failed_reasons.append(already_exists_issue)
                    else:
                        unknown_lines.append(line)
                    continue
                # END special lines parsing

                for e in endings:
                    if line.endswith(e):
                        failed_files.append(line[20 : -len(e)])
                        failed_reasons.append(e)
                        break
                    # END if ending matches
                # END for each possible ending
            # END for each line
            if unknown_lines:
                raise GitCommandError(("git-checkout-index",), 128, stderr)
            if failed_files:
                valid_files = list(set(iter_checked_out_files) - set(failed_files))
                raise CheckoutError(
                    "Some files could not be checked out from the index due to local modifications",
                    failed_files,
                    valid_files,
                    failed_reasons,
                )

        # END stderr handler

        if paths is None:
            args.append("--all")
            kwargs["as_process"] = 1
            fprogress(None, False, None)
            proc = self.repo.git.checkout_index(*args, **kwargs)
            proc.wait()
            fprogress(None, True, None)
            rval_iter = (e.path for e in self.entries.values())
            handle_stderr(proc, rval_iter)
            return rval_iter
        else:
            if isinstance(paths, str):
                paths = [paths]

            # Make sure we have our entries loaded before we start checkout_index, which
            # will hold a lock on it. We try to get the lock as well during our entries
            # initialization.
            self.entries  # noqa: B018

            args.append("--stdin")
            kwargs["as_process"] = True
            kwargs["istream"] = subprocess.PIPE
            proc = self.repo.git.checkout_index(args, **kwargs)
            # FIXME: Reading from GIL!
            make_exc = lambda: GitCommandError(("git-checkout-index",) + tuple(args), 128, proc.stderr.read())
            checked_out_files: List[PathLike] = []

            for path in paths:
                co_path = to_native_path_linux(self._to_relative_path(path))
                # If the item is not in the index, it could be a directory.
                path_is_directory = False

                try:
                    self.entries[(co_path, 0)]
                except KeyError:
                    folder = str(co_path)
                    if not folder.endswith("/"):
                        folder += "/"
                    for entry in self.entries.values():
                        if str(entry.path).startswith(folder):
                            p = entry.path
                            self._write_path_to_stdin(proc, p, p, make_exc, fprogress, read_from_stdout=False)
                            checked_out_files.append(p)
                            path_is_directory = True
                        # END if entry is in directory
                    # END for each entry
                # END path exception handlnig

                if not path_is_directory:
                    self._write_path_to_stdin(proc, co_path, path, make_exc, fprogress, read_from_stdout=False)
                    checked_out_files.append(co_path)
                # END path is a file
            # END for each path
            try:
                self._flush_stdin_and_wait(proc, ignore_stdout=True)
            except GitCommandError:
                # Without parsing stdout we don't know what failed.
                raise CheckoutError(  # noqa: B904
                    "Some files could not be checked out from the index, probably because they didn't exist.",
                    failed_files,
                    [],
                    failed_reasons,
                )

            handle_stderr(proc, checked_out_files)
            return checked_out_files
        # END paths handling

    @default_index
    def reset(
        self,
        commit: Union[Commit, "Reference", str] = "HEAD",
        working_tree: bool = False,
        paths: Union[None, Iterable[PathLike]] = None,
        head: bool = False,
        **kwargs: Any,
    ) -> "IndexFile":
        """Reset the index to reflect the tree at the given commit. This will not adjust
        our HEAD reference by default, as opposed to
        :meth:`HEAD.reset <git.refs.head.HEAD.reset>`.

        :param commit:
            Revision, :class:`~git.refs.reference.Reference` or
            :class:`~git.objects.commit.Commit` specifying the commit we should
            represent.

            If you want to specify a tree only, use :meth:`IndexFile.from_tree` and
            overwrite the default index.

        :param working_tree:
            If ``True``, the files in the working tree will reflect the changed index.
            If ``False``, the working tree will not be touched.
            Please note that changes to the working copy will be discarded without
            warning!

        :param head:
            If ``True``, the head will be set to the given commit. This is ``False`` by
            default, but if ``True``, this method behaves like
            :meth:`HEAD.reset <git.refs.head.HEAD.reset>`.

        :param paths:
            If given as an iterable of absolute or repository-relative paths, only these
            will be reset to their state at the given commit-ish.
            The paths need to exist at the commit, otherwise an exception will be
            raised.

        :param kwargs:
            Additional keyword arguments passed to :manpage:`git-reset(1)`.

        :note:
            :meth:`IndexFile.reset`, as opposed to
            :meth:`HEAD.reset <git.refs.head.HEAD.reset>`, will not delete any files in
            order to maintain a consistent working tree. Instead, it will just check out
            the files according to their state in the index.
            If you want :manpage:`git-reset(1)`-like behaviour, use
            :meth:`HEAD.reset <git.refs.head.HEAD.reset>` instead.

        :return:
            self
        """
        # What we actually want to do is to merge the tree into our existing index,
        # which is what git-read-tree does.
        new_inst = type(self).from_tree(self.repo, commit)
        if not paths:
            self.entries = new_inst.entries
        else:
            nie = new_inst.entries
            for path in paths:
                path = self._to_relative_path(path)
                try:
                    key = entry_key(path, 0)
                    self.entries[key] = nie[key]
                except KeyError:
                    # If key is not in theirs, it mustn't be in ours.
                    try:
                        del self.entries[key]
                    except KeyError:
                        pass
                    # END handle deletion keyerror
                # END handle keyerror
            # END for each path
        # END handle paths
        self.write()

        if working_tree:
            self.checkout(paths=paths, force=True)
        # END handle working tree

        if head:
            self.repo.head.set_commit(self.repo.commit(commit), logmsg="%s: Updating HEAD" % commit)
        # END handle head change

        return self

    # FIXME: This is documented to accept the same parameters as Diffable.diff, but this
    # does not handle NULL_TREE for `other`. (The suppressed mypy error is about this.)
    def diff(
        self,
        other: Union[  # type: ignore[override]
            Literal[git_diff.DiffConstants.INDEX],
            "Tree",
            "Commit",
            str,
            None,
        ] = git_diff.INDEX,
        paths: Union[PathLike, List[PathLike], Tuple[PathLike, ...], None] = None,
        create_patch: bool = False,
        **kwargs: Any,
    ) -> git_diff.DiffIndex[git_diff.Diff]:
        """Diff this index against the working copy or a :class:`~git.objects.tree.Tree`
        or :class:`~git.objects.commit.Commit` object.

        For documentation of the parameters and return values, see
        :meth:`Diffable.diff <git.diff.Diffable.diff>`.

        :note:
            Will only work with indices that represent the default git index as they
            have not been initialized with a stream.
        """
        # Only run if we are the default repository index.
        if self._file_path != self._index_path():
            raise AssertionError("Cannot call %r on indices that do not represent the default git index" % self.diff())
        # Index against index is always empty.
        if other is self.INDEX:
            return git_diff.DiffIndex()

        # Index against anything but None is a reverse diff with the respective item.
        # Handle existing -R flags properly.
        # Transform strings to the object so that we can call diff on it.
        if isinstance(other, str):
            other = self.repo.rev_parse(other)
        # END object conversion

        if isinstance(other, Object):  # For Tree or Commit.
            # Invert the existing R flag.
            cur_val = kwargs.get("R", False)
            kwargs["R"] = not cur_val
            return other.diff(self.INDEX, paths, create_patch, **kwargs)
        # END diff against other item handling

        # If other is not None here, something is wrong.
        if other is not None:
            raise ValueError("other must be None, Diffable.INDEX, a Tree or Commit, was %r" % other)

        # Diff against working copy - can be handled by superclass natively.
        return super().diff(other, paths, create_patch, **kwargs)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\generative_service\client.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from collections import OrderedDict
import os
import re
from typing import (
    Callable,
    Dict,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import generative_service, safety
from google.ai.generativelanguage_v1beta.types import content
from google.ai.generativelanguage_v1beta.types import content as gag_content

from .transports.base import DEFAULT_CLIENT_INFO, GenerativeServiceTransport
from .transports.grpc import GenerativeServiceGrpcTransport
from .transports.grpc_asyncio import GenerativeServiceGrpcAsyncIOTransport
from .transports.rest import GenerativeServiceRestTransport


class GenerativeServiceClientMeta(type):
    """Metaclass for the GenerativeService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = (
        OrderedDict()
    )  # type: Dict[str, Type[GenerativeServiceTransport]]
    _transport_registry["grpc"] = GenerativeServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = GenerativeServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = GenerativeServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[GenerativeServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class GenerativeServiceClient(metaclass=GenerativeServiceClientMeta):
    """API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            GenerativeServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            GenerativeServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> GenerativeServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            GenerativeServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def cached_content_path(
        id: str,
    ) -> str:
        """Returns a fully-qualified cached_content string."""
        return "cachedContents/{id}".format(
            id=id,
        )

    @staticmethod
    def parse_cached_content_path(path: str) -> Dict[str, str]:
        """Parses a cached_content path into its component segments."""
        m = re.match(r"^cachedContents/(?P<id>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = GenerativeServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = GenerativeServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = GenerativeServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = GenerativeServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = GenerativeServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or GenerativeServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[
                str,
                GenerativeServiceTransport,
                Callable[..., GenerativeServiceTransport],
            ]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the generative service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,GenerativeServiceTransport,Callable[..., GenerativeServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the GenerativeServiceTransport constructor.
                If set to None, a transport is chosen automatically.
            client_options (Optional[Union[google.api_core.client_options.ClientOptions, dict]]):
                Custom options for the client.

                1. The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client when ``transport`` is
                not explicitly provided. Only if this property is not set and
                ``transport`` was not explicitly provided, the endpoint is
                determined by the GOOGLE_API_USE_MTLS_ENDPOINT environment
                variable, which have one of the following values:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto-switch to the
                default mTLS endpoint if client certificate is present; this is
                the default value).

                2. If the GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide a client certificate for mTLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

                3. The ``universe_domain`` property can be used to override the
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = GenerativeServiceClient._read_environment_variables()
        self._client_cert_source = GenerativeServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = GenerativeServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, GenerativeServiceTransport)
        if transport_provided:
            # transport is a GenerativeServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(GenerativeServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = (
            self._api_endpoint
            or GenerativeServiceClient._get_api_endpoint(
                self._client_options.api_endpoint,
                self._client_cert_source,
                self._universe_domain,
                self._use_mtls_endpoint,
            )
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[GenerativeServiceTransport],
                Callable[..., GenerativeServiceTransport],
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., GenerativeServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def generate_content(
        self,
        request: Optional[
            Union[generative_service.GenerateContentRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.GenerateContentResponse:
        r"""Generates a response from the model given an input
        ``GenerateContentRequest``.

        Input capabilities differ between models, including tuned
        models. See the `model
        guide <https://ai.google.dev/models/gemini>`__ and `tuning
        guide <https://ai.google.dev/docs/model_tuning_guidance>`__ for
        details.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_generate_content():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GenerateContentRequest(
                    model="model_value",
                )

                # Make the request
                response = client.generate_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GenerateContentRequest, dict]):
                The request object. Request to generate a completion from
                the model.
            model (str):
                Required. The name of the ``Model`` to use for
                generating the completion.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.GenerateContentResponse:
                Response from the model supporting multiple candidates.

                   Note on safety ratings and content filtering. They
                   are reported for both prompt in
                   GenerateContentResponse.prompt_feedback and for each
                   candidate in finish_reason and in safety_ratings. The
                   API contract is that: - either all requested
                   candidates are returned or no candidates at all - no
                   candidates are returned only if there was something
                   wrong with the prompt (see prompt_feedback) -
                   feedback on each candidate is reported on
                   finish_reason and safety_ratings.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateContentRequest):
            request = generative_service.GenerateContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if contents is not None:
                request.contents = contents

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.generate_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def generate_answer(
        self,
        request: Optional[Union[generative_service.GenerateAnswerRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        safety_settings: Optional[MutableSequence[safety.SafetySetting]] = None,
        answer_style: Optional[
            generative_service.GenerateAnswerRequest.AnswerStyle
        ] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.GenerateAnswerResponse:
        r"""Generates a grounded answer from the model given an input
        ``GenerateAnswerRequest``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_generate_answer():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GenerateAnswerRequest(
                    model="model_value",
                    answer_style="VERBOSE",
                )

                # Make the request
                response = client.generate_answer(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GenerateAnswerRequest, dict]):
                The request object. Request to generate a grounded answer
                from the model.
            model (str):
                Required. The name of the ``Model`` to use for
                generating the grounded response.

                Format: ``model=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
                Required. The content of the current conversation with
                the model. For single-turn queries, this is a single
                question to answer. For multi-turn queries, this is a
                repeated field that contains conversation history and
                the last ``Content`` in the list containing the
                question.

                Note: GenerateAnswer currently only supports queries in
                English.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            safety_settings (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetySetting]):
                Optional. A list of unique ``SafetySetting`` instances
                for blocking unsafe content.

                This will be enforced on the
                ``GenerateAnswerRequest.contents`` and
                ``GenerateAnswerResponse.candidate``. There should not
                be more than one setting for each ``SafetyCategory``
                type. The API will block any contents and responses that
                fail to meet the thresholds set by these settings. This
                list overrides the default settings for each
                ``SafetyCategory`` specified in the safety_settings. If
                there is no ``SafetySetting`` for a given
                ``SafetyCategory`` provided in the list, the API will
                use the default safety setting for that category. Harm
                categories HARM_CATEGORY_HATE_SPEECH,
                HARM_CATEGORY_SEXUALLY_EXPLICIT,
                HARM_CATEGORY_DANGEROUS_CONTENT,
                HARM_CATEGORY_HARASSMENT are supported.

                This corresponds to the ``safety_settings`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            answer_style (google.ai.generativelanguage_v1beta.types.GenerateAnswerRequest.AnswerStyle):
                Required. Style in which answers
                should be returned.

                This corresponds to the ``answer_style`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.GenerateAnswerResponse:
                Response from the model for a
                grounded answer.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents, safety_settings, answer_style])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateAnswerRequest):
            request = generative_service.GenerateAnswerRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if contents is not None:
                request.contents = contents
            if safety_settings is not None:
                request.safety_settings = safety_settings
            if answer_style is not None:
                request.answer_style = answer_style

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.generate_answer]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def stream_generate_content(
        self,
        request: Optional[
            Union[generative_service.GenerateContentRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> Iterable[generative_service.GenerateContentResponse]:
        r"""Generates a streamed response from the model given an input
        ``GenerateContentRequest``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_stream_generate_content():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GenerateContentRequest(
                    model="model_value",
                )

                # Make the request
                stream = client.stream_generate_content(request=request)

                # Handle the response
                for response in stream:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GenerateContentRequest, dict]):
                The request object. Request to generate a completion from
                the model.
            model (str):
                Required. The name of the ``Model`` to use for
                generating the completion.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            Iterable[google.ai.generativelanguage_v1beta.types.GenerateContentResponse]:
                Response from the model supporting multiple candidates.

                   Note on safety ratings and content filtering. They
                   are reported for both prompt in
                   GenerateContentResponse.prompt_feedback and for each
                   candidate in finish_reason and in safety_ratings. The
                   API contract is that: - either all requested
                   candidates are returned or no candidates at all - no
                   candidates are returned only if there was something
                   wrong with the prompt (see prompt_feedback) -
                   feedback on each candidate is reported on
                   finish_reason and safety_ratings.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateContentRequest):
            request = generative_service.GenerateContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if contents is not None:
                request.contents = contents

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.stream_generate_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def embed_content(
        self,
        request: Optional[Union[generative_service.EmbedContentRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        content: Optional[gag_content.Content] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.EmbedContentResponse:
        r"""Generates an embedding from the model given an input
        ``Content``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_embed_content():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.EmbedContentRequest(
                    model="model_value",
                )

                # Make the request
                response = client.embed_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.EmbedContentRequest, dict]):
                The request object. Request containing the ``Content`` for the model to
                embed.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            content (google.ai.generativelanguage_v1beta.types.Content):
                Required. The content to embed. Only the ``parts.text``
                fields will be counted.

                This corresponds to the ``content`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.EmbedContentResponse:
                The response to an EmbedContentRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, content])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.EmbedContentRequest):
            request = generative_service.EmbedContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if content is not None:
                request.content = content

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.embed_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def batch_embed_contents(
        self,
        request: Optional[
            Union[generative_service.BatchEmbedContentsRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        requests: Optional[
            MutableSequence[generative_service.EmbedContentRequest]
        ] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.BatchEmbedContentsResponse:
        r"""Generates multiple embeddings from the model given
        input text in a synchronous call.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_batch_embed_contents():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1beta.EmbedContentRequest()
                requests.model = "model_value"

                request = generativelanguage_v1beta.BatchEmbedContentsRequest(
                    model="model_value",
                    requests=requests,
                )

                # Make the request
                response = client.batch_embed_contents(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.BatchEmbedContentsRequest, dict]):
                The request object. Batch request to get embeddings from
                the model for a list of prompts.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            requests (MutableSequence[google.ai.generativelanguage_v1beta.types.EmbedContentRequest]):
                Required. Embed requests for the batch. The model in
                each of these requests must match the model specified
                ``BatchEmbedContentsRequest.model``.

                This corresponds to the ``requests`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.BatchEmbedContentsResponse:
                The response to a BatchEmbedContentsRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, requests])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.BatchEmbedContentsRequest):
            request = generative_service.BatchEmbedContentsRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if requests is not None:
                request.requests = requests

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.batch_embed_contents]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def count_tokens(
        self,
        request: Optional[Union[generative_service.CountTokensRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.CountTokensResponse:
        r"""Runs a model's tokenizer on input content and returns
        the token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_count_tokens():
                # Create a client
                client = generativelanguage_v1beta.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CountTokensRequest(
                    model="model_value",
                )

                # Make the request
                response = client.count_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CountTokensRequest, dict]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
                Optional. The input given to the model as a prompt. This
                field is ignored when ``generate_content_request`` is
                set.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CountTokensResponse:
                A response from CountTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.CountTokensRequest):
            request = generative_service.CountTokensRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if contents is not None:
                request.contents = contents

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.count_tokens]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def __enter__(self) -> "GenerativeServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("GenerativeServiceClient",)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\__init__.py ===
"""
Module for dealing with 'gvar'-style font variations, also known as run-time
interpolation.

The ideas here are very similar to MutatorMath.  There is even code to read
MutatorMath .designspace files in the varLib.designspace module.

For now, if you run this file on a designspace file, it tries to find
ttf-interpolatable files for the masters and build a variable-font from
them.  Such ttf-interpolatable and designspace files can be generated from
a Glyphs source, eg., using noto-source as an example:

    .. code-block:: sh

        $ fontmake -o ttf-interpolatable -g NotoSansArabic-MM.glyphs

Then you can make a variable-font this way:

    .. code-block:: sh

        $ fonttools varLib master_ufo/NotoSansArabic.designspace

API *will* change in near future.
"""

from typing import List
from fontTools.misc.vector import Vector
from fontTools.misc.roundTools import noRound, otRound
from fontTools.misc.fixedTools import floatToFixed as fl2fi
from fontTools.misc.textTools import Tag, tostr
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._f_v_a_r import Axis, NamedInstance
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates, dropImpliedOnCurvePoints
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables.otBase import OTTableWriter
from fontTools.varLib import builder, models, varStore
from fontTools.varLib.merger import VariationMerger, COLRVariationMerger
from fontTools.varLib.mvar import MVAR_ENTRIES
from fontTools.varLib.iup import iup_delta_optimize
from fontTools.varLib.featureVars import addFeatureVariations
from fontTools.designspaceLib import DesignSpaceDocument, InstanceDescriptor
from fontTools.designspaceLib.split import splitInterpolable, splitVariableFonts
from fontTools.varLib.stat import buildVFStatTable
from fontTools.colorLib.builder import buildColrV1
from fontTools.colorLib.unbuilder import unbuildColrV1
from functools import partial
from collections import OrderedDict, defaultdict, namedtuple
import os.path
import logging
from copy import deepcopy
from pprint import pformat
from re import fullmatch
from .errors import VarLibError, VarLibValidationError

log = logging.getLogger("fontTools.varLib")

# This is a lib key for the designspace document. The value should be
# a comma-separated list of OpenType feature tag(s), to be used as the
# FeatureVariations feature.
# If present, the DesignSpace <rules processing="..."> flag is ignored.
FEAVAR_FEATURETAG_LIB_KEY = "com.github.fonttools.varLib.featureVarsFeatureTag"

#
# Creation routines
#


def _add_fvar(font, axes, instances: List[InstanceDescriptor]):
    """
    Add 'fvar' table to font.

    axes is an ordered dictionary of DesignspaceAxis objects.

    instances is list of dictionary objects with 'location', 'stylename',
    and possibly 'postscriptfontname' entries.
    """

    assert axes
    assert isinstance(axes, OrderedDict)

    log.info("Generating fvar")

    fvar = newTable("fvar")
    nameTable = font["name"]

    # if there are not currently any mac names don't add them here, that's inconsistent
    # https://github.com/fonttools/fonttools/issues/683
    macNames = any(nr.platformID == 1 for nr in getattr(nameTable, "names", ()))

    # we have all the best ways to express mac names
    platforms = ((3, 1, 0x409),)
    if macNames:
        platforms = ((1, 0, 0),) + platforms

    for a in axes.values():
        axis = Axis()
        axis.axisTag = Tag(a.tag)
        # TODO Skip axes that have no variation.
        axis.minValue, axis.defaultValue, axis.maxValue = (
            a.minimum,
            a.default,
            a.maximum,
        )
        axis.axisNameID = nameTable.addMultilingualName(
            a.labelNames, font, minNameID=256, mac=macNames
        )
        axis.flags = int(a.hidden)
        fvar.axes.append(axis)

    default_coordinates = {axis.axisTag: axis.defaultValue for axis in fvar.axes}

    for instance in instances:
        # Filter out discrete axis locations
        coordinates = {
            name: value for name, value in instance.location.items() if name in axes
        }

        if "en" not in instance.localisedStyleName:
            if not instance.styleName:
                raise VarLibValidationError(
                    f"Instance at location '{coordinates}' must have a default English "
                    "style name ('stylename' attribute on the instance element or a "
                    "stylename element with an 'xml:lang=\"en\"' attribute)."
                )
            localisedStyleName = dict(instance.localisedStyleName)
            localisedStyleName["en"] = tostr(instance.styleName)
        else:
            localisedStyleName = instance.localisedStyleName

        psname = instance.postScriptFontName

        inst = NamedInstance()
        inst.coordinates = {
            axes[k].tag: axes[k].map_backward(v) for k, v in coordinates.items()
        }

        subfamilyNameID = nameTable.findMultilingualName(
            localisedStyleName, windows=True, mac=macNames
        )
        if subfamilyNameID in {2, 17} and inst.coordinates == default_coordinates:
            # Instances can only reuse an existing name ID 2 or 17 if they are at the
            # default location across all axes, see:
            # https://github.com/fonttools/fonttools/issues/3825.
            inst.subfamilyNameID = subfamilyNameID
        else:
            inst.subfamilyNameID = nameTable.addMultilingualName(
                localisedStyleName, windows=True, mac=macNames, minNameID=256
            )

        if psname is not None:
            psname = tostr(psname)
            inst.postscriptNameID = nameTable.addName(psname, platforms=platforms)
        fvar.instances.append(inst)

    assert "fvar" not in font
    font["fvar"] = fvar

    return fvar


def _add_avar(font, axes, mappings, axisTags):
    """
    Add 'avar' table to font.

    axes is an ordered dictionary of AxisDescriptor objects.
    """

    assert axes
    assert isinstance(axes, OrderedDict)

    log.info("Generating avar")

    avar = newTable("avar")

    interesting = False
    vals_triples = {}
    for axis in axes.values():
        # Currently, some rasterizers require that the default value maps
        # (-1 to -1, 0 to 0, and 1 to 1) be present for all the segment
        # maps, even when the default normalization mapping for the axis
        # was not modified.
        # https://github.com/googlei18n/fontmake/issues/295
        # https://github.com/fonttools/fonttools/issues/1011
        # TODO(anthrotype) revert this (and 19c4b37) when issue is fixed
        curve = avar.segments[axis.tag] = {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}

        keys_triple = (axis.minimum, axis.default, axis.maximum)
        vals_triple = tuple(axis.map_forward(v) for v in keys_triple)
        vals_triples[axis.tag] = vals_triple

        if not axis.map:
            continue

        items = sorted(axis.map)
        keys = [item[0] for item in items]
        vals = [item[1] for item in items]

        # Current avar requirements.  We don't have to enforce
        # these on the designer and can deduce some ourselves,
        # but for now just enforce them.
        if axis.minimum != min(keys):
            raise VarLibValidationError(
                f"Axis '{axis.name}': there must be a mapping for the axis minimum "
                f"value {axis.minimum} and it must be the lowest input mapping value."
            )
        if axis.maximum != max(keys):
            raise VarLibValidationError(
                f"Axis '{axis.name}': there must be a mapping for the axis maximum "
                f"value {axis.maximum} and it must be the highest input mapping value."
            )
        if axis.default not in keys:
            raise VarLibValidationError(
                f"Axis '{axis.name}': there must be a mapping for the axis default "
                f"value {axis.default}."
            )
        # No duplicate input values (output values can be >= their preceeding value).
        if len(set(keys)) != len(keys):
            raise VarLibValidationError(
                f"Axis '{axis.name}': All axis mapping input='...' values must be "
                "unique, but we found duplicates."
            )
        # Ascending values
        if sorted(vals) != vals:
            raise VarLibValidationError(
                f"Axis '{axis.name}': mapping output values must be in ascending order."
            )

        keys = [models.normalizeValue(v, keys_triple) for v in keys]
        vals = [models.normalizeValue(v, vals_triple) for v in vals]

        if all(k == v for k, v in zip(keys, vals)):
            continue
        interesting = True

        curve.update(zip(keys, vals))

        assert 0.0 in curve and curve[0.0] == 0.0
        assert -1.0 not in curve or curve[-1.0] == -1.0
        assert +1.0 not in curve or curve[+1.0] == +1.0
        # curve.update({-1.0: -1.0, 0.0: 0.0, 1.0: 1.0})

    if mappings:
        interesting = True

        inputLocations = [
            {
                axes[name].tag: models.normalizeValue(v, vals_triples[axes[name].tag])
                for name, v in mapping.inputLocation.items()
            }
            for mapping in mappings
        ]
        outputLocations = [
            {
                axes[name].tag: models.normalizeValue(v, vals_triples[axes[name].tag])
                for name, v in mapping.outputLocation.items()
            }
            for mapping in mappings
        ]
        assert len(inputLocations) == len(outputLocations)

        # If base-master is missing, insert it at zero location.
        if not any(all(v == 0 for k, v in loc.items()) for loc in inputLocations):
            inputLocations.insert(0, {})
            outputLocations.insert(0, {})

        model = models.VariationModel(inputLocations, axisTags)
        storeBuilder = varStore.OnlineVarStoreBuilder(axisTags)
        storeBuilder.setModel(model)
        varIdxes = {}
        for tag in axisTags:
            masterValues = []
            for vo, vi in zip(outputLocations, inputLocations):
                if tag not in vo:
                    masterValues.append(0)
                    continue
                v = vo[tag] - vi.get(tag, 0)
                masterValues.append(fl2fi(v, 14))
            varIdxes[tag] = storeBuilder.storeMasters(masterValues)[1]

        store = storeBuilder.finish()
        optimized = store.optimize()
        varIdxes = {axis: optimized[value] for axis, value in varIdxes.items()}

        varIdxMap = builder.buildDeltaSetIndexMap(varIdxes[t] for t in axisTags)

        avar.majorVersion = 2
        avar.table = ot.avar()
        avar.table.VarIdxMap = varIdxMap
        avar.table.VarStore = store

    assert "avar" not in font
    if not interesting:
        log.info("No need for avar")
        avar = None
    else:
        font["avar"] = avar

    return avar


def _add_stat(font):
    # Note: this function only gets called by old code that calls `build()`
    # directly. Newer code that wants to benefit from STAT data from the
    # designspace should call `build_many()`

    if "STAT" in font:
        return

    from ..otlLib.builder import buildStatTable

    fvarTable = font["fvar"]
    axes = [dict(tag=a.axisTag, name=a.axisNameID) for a in fvarTable.axes]
    buildStatTable(font, axes)


_MasterData = namedtuple("_MasterData", ["glyf", "hMetrics", "vMetrics"])


def _add_gvar(font, masterModel, master_ttfs, tolerance=0.5, optimize=True):
    if tolerance < 0:
        raise ValueError("`tolerance` must be a positive number.")

    log.info("Generating gvar")
    assert "gvar" not in font
    gvar = font["gvar"] = newTable("gvar")
    glyf = font["glyf"]
    defaultMasterIndex = masterModel.reverseMapping[0]

    master_datas = [
        _MasterData(
            m["glyf"], m["hmtx"].metrics, getattr(m.get("vmtx"), "metrics", None)
        )
        for m in master_ttfs
    ]

    for glyph in font.getGlyphOrder():
        log.debug("building gvar for glyph '%s'", glyph)

        allData = [
            m.glyf._getCoordinatesAndControls(glyph, m.hMetrics, m.vMetrics)
            for m in master_datas
        ]

        if allData[defaultMasterIndex][1].numberOfContours != 0:
            # If the default master is not empty, interpret empty non-default masters
            # as missing glyphs from a sparse master
            allData = [
                d if d is not None and d[1].numberOfContours != 0 else None
                for d in allData
            ]

        model, allData = masterModel.getSubModel(allData)

        allCoords = [d[0] for d in allData]
        allControls = [d[1] for d in allData]
        control = allControls[0]
        if not models.allEqual(allControls):
            log.warning("glyph %s has incompatible masters; skipping" % glyph)
            continue
        del allControls

        # Update gvar
        gvar.variations[glyph] = []
        deltas = model.getDeltas(
            allCoords, round=partial(GlyphCoordinates.__round__, round=round)
        )
        supports = model.supports
        assert len(deltas) == len(supports)

        # Prepare for IUP optimization
        origCoords = deltas[0]
        endPts = control.endPts

        for i, (delta, support) in enumerate(zip(deltas[1:], supports[1:])):
            if all(v == 0 for v in delta.array):
                continue
            var = TupleVariation(support, delta)
            if optimize:
                delta_opt = iup_delta_optimize(
                    delta, origCoords, endPts, tolerance=tolerance
                )

                if None in delta_opt:
                    # Use "optimized" version only if smaller...
                    var_opt = TupleVariation(support, delta_opt)

                    axis_tags = sorted(
                        support.keys()
                    )  # Shouldn't matter that this is different from fvar...?
                    tupleData, auxData = var.compile(axis_tags)
                    unoptimized_len = len(tupleData) + len(auxData)
                    tupleData, auxData = var_opt.compile(axis_tags)
                    optimized_len = len(tupleData) + len(auxData)

                    if optimized_len < unoptimized_len:
                        var = var_opt

            gvar.variations[glyph].append(var)


def _remove_TTHinting(font):
    for tag in ("cvar", "cvt ", "fpgm", "prep"):
        if tag in font:
            del font[tag]
    maxp = font["maxp"]
    for attr in (
        "maxTwilightPoints",
        "maxStorage",
        "maxFunctionDefs",
        "maxInstructionDefs",
        "maxStackElements",
        "maxSizeOfInstructions",
    ):
        setattr(maxp, attr, 0)
    maxp.maxZones = 1
    font["glyf"].removeHinting()
    # TODO: Modify gasp table to deactivate gridfitting for all ranges?


def _merge_TTHinting(font, masterModel, master_ttfs):
    log.info("Merging TT hinting")
    assert "cvar" not in font

    # Check that the existing hinting is compatible

    # fpgm and prep table

    for tag in ("fpgm", "prep"):
        all_pgms = [m[tag].program for m in master_ttfs if tag in m]
        if not all_pgms:
            continue
        font_pgm = getattr(font.get(tag), "program", None)
        if any(pgm != font_pgm for pgm in all_pgms):
            log.warning(
                "Masters have incompatible %s tables, hinting is discarded." % tag
            )
            _remove_TTHinting(font)
            return

    # glyf table

    font_glyf = font["glyf"]
    master_glyfs = [m["glyf"] for m in master_ttfs]
    for name, glyph in font_glyf.glyphs.items():
        all_pgms = [getattr(glyf.get(name), "program", None) for glyf in master_glyfs]
        if not any(all_pgms):
            continue
        glyph.expand(font_glyf)
        font_pgm = getattr(glyph, "program", None)
        if any(pgm != font_pgm for pgm in all_pgms if pgm):
            log.warning(
                "Masters have incompatible glyph programs in glyph '%s', hinting is discarded."
                % name
            )
            # TODO Only drop hinting from this glyph.
            _remove_TTHinting(font)
            return

    # cvt table

    all_cvs = [Vector(m["cvt "].values) if "cvt " in m else None for m in master_ttfs]

    nonNone_cvs = models.nonNone(all_cvs)
    if not nonNone_cvs:
        # There is no cvt table to make a cvar table from, we're done here.
        return

    if not models.allEqual(len(c) for c in nonNone_cvs):
        log.warning("Masters have incompatible cvt tables, hinting is discarded.")
        _remove_TTHinting(font)
        return

    variations = []
    deltas, supports = masterModel.getDeltasAndSupports(
        all_cvs, round=round
    )  # builtin round calls into Vector.__round__, which uses builtin round as we like
    for i, (delta, support) in enumerate(zip(deltas[1:], supports[1:])):
        if all(v == 0 for v in delta):
            continue
        var = TupleVariation(support, delta)
        variations.append(var)

    # We can build the cvar table now.
    if variations:
        cvar = font["cvar"] = newTable("cvar")
        cvar.version = 1
        cvar.variations = variations


_MetricsFields = namedtuple(
    "_MetricsFields",
    [
        "tableTag",
        "metricsTag",
        "sb1",
        "sb2",
        "advMapping",
        "vOrigMapping",
        "phantomIndex",
    ],
)

HVAR_FIELDS = _MetricsFields(
    tableTag="HVAR",
    metricsTag="hmtx",
    sb1="LsbMap",
    sb2="RsbMap",
    advMapping="AdvWidthMap",
    vOrigMapping=None,
    phantomIndex=0,
)

VVAR_FIELDS = _MetricsFields(
    tableTag="VVAR",
    metricsTag="vmtx",
    sb1="TsbMap",
    sb2="BsbMap",
    advMapping="AdvHeightMap",
    vOrigMapping="VOrgMap",
    phantomIndex=1,
)


def _add_HVAR(font, masterModel, master_ttfs, axisTags):
    getAdvanceMetrics = partial(
        _get_advance_metrics, font, masterModel, master_ttfs, axisTags, HVAR_FIELDS
    )
    _add_VHVAR(font, axisTags, HVAR_FIELDS, getAdvanceMetrics)


def _add_VVAR(font, masterModel, master_ttfs, axisTags):
    getAdvanceMetrics = partial(
        _get_advance_metrics, font, masterModel, master_ttfs, axisTags, VVAR_FIELDS
    )
    _add_VHVAR(font, axisTags, VVAR_FIELDS, getAdvanceMetrics)


def _add_VHVAR(font, axisTags, tableFields, getAdvanceMetrics):
    tableTag = tableFields.tableTag
    assert tableTag not in font
    glyphOrder = font.getGlyphOrder()
    log.info("Generating " + tableTag)
    VHVAR = newTable(tableTag)
    tableClass = getattr(ot, tableTag)
    vhvar = VHVAR.table = tableClass()
    vhvar.Version = 0x00010000

    vhAdvanceDeltasAndSupports, vOrigDeltasAndSupports = getAdvanceMetrics()

    if vOrigDeltasAndSupports:
        singleModel = False
    else:
        singleModel = models.allEqual(
            id(v[1]) for v in vhAdvanceDeltasAndSupports.values()
        )

    directStore = None
    if singleModel:
        # Build direct mapping
        supports = next(iter(vhAdvanceDeltasAndSupports.values()))[1][1:]
        varTupleList = builder.buildVarRegionList(supports, axisTags)
        varTupleIndexes = list(range(len(supports)))
        varData = builder.buildVarData(varTupleIndexes, [], optimize=False)
        for glyphName in glyphOrder:
            varData.addItem(vhAdvanceDeltasAndSupports[glyphName][0], round=noRound)
        varData.optimize()
        directStore = builder.buildVarStore(varTupleList, [varData])
        # remove unused regions from VarRegionList
        directStore.prune_regions()

    # Build optimized indirect mapping
    storeBuilder = varStore.OnlineVarStoreBuilder(axisTags)
    advMapping = {}
    for glyphName in glyphOrder:
        deltas, supports = vhAdvanceDeltasAndSupports[glyphName]
        storeBuilder.setSupports(supports)
        advMapping[glyphName] = storeBuilder.storeDeltas(deltas, round=noRound)

    if vOrigDeltasAndSupports:
        vOrigMap = {}
        for glyphName in glyphOrder:
            deltas, supports = vOrigDeltasAndSupports[glyphName]
            storeBuilder.setSupports(supports)
            vOrigMap[glyphName] = storeBuilder.storeDeltas(deltas, round=noRound)

    indirectStore = storeBuilder.finish()
    mapping2 = indirectStore.optimize(use_NO_VARIATION_INDEX=False)
    advMapping = [mapping2[advMapping[g]] for g in glyphOrder]
    advanceMapping = builder.buildVarIdxMap(advMapping, glyphOrder)

    if vOrigDeltasAndSupports:
        vOrigMap = [mapping2[vOrigMap[g]] for g in glyphOrder]

    useDirect = False
    vOrigMapping = None
    if directStore:
        # Compile both, see which is more compact

        writer = OTTableWriter()
        directStore.compile(writer, font)
        directSize = len(writer.getAllData())

        writer = OTTableWriter()
        indirectStore.compile(writer, font)
        advanceMapping.compile(writer, font)
        indirectSize = len(writer.getAllData())

        useDirect = directSize < indirectSize

    if useDirect:
        metricsStore = directStore
        advanceMapping = None
    else:
        metricsStore = indirectStore
        if vOrigDeltasAndSupports:
            vOrigMapping = builder.buildVarIdxMap(vOrigMap, glyphOrder)

    vhvar.VarStore = metricsStore
    setattr(vhvar, tableFields.advMapping, advanceMapping)
    if vOrigMapping is not None:
        setattr(vhvar, tableFields.vOrigMapping, vOrigMapping)
    setattr(vhvar, tableFields.sb1, None)
    setattr(vhvar, tableFields.sb2, None)

    font[tableTag] = VHVAR
    return


def _get_advance_metrics(font, masterModel, master_ttfs, axisTags, tableFields):
    tableTag = tableFields.tableTag
    glyphOrder = font.getGlyphOrder()

    # Build list of source font advance widths for each glyph
    metricsTag = tableFields.metricsTag
    advMetricses = [m[metricsTag].metrics for m in master_ttfs]

    # Build list of source font vertical origin coords for each glyph
    if tableTag == "VVAR" and "VORG" in master_ttfs[0]:
        vOrigMetricses = [m["VORG"].VOriginRecords for m in master_ttfs]
        defaultYOrigs = [m["VORG"].defaultVertOriginY for m in master_ttfs]
        vOrigMetricses = list(zip(vOrigMetricses, defaultYOrigs))
    else:
        vOrigMetricses = None

    vhAdvanceDeltasAndSupports = {}
    vOrigDeltasAndSupports = {}
    # HACK: we treat width 65535 as a sentinel value to signal that a glyph
    # from a non-default master should not participate in computing {H,V}VAR,
    # as if it were missing. Allows to variate other glyph-related data independently
    # from glyph metrics
    sparse_advance = 0xFFFF
    for glyph in glyphOrder:
        vhAdvances = [
            (
                metrics[glyph][0]
                if glyph in metrics and metrics[glyph][0] != sparse_advance
                else None
            )
            for metrics in advMetricses
        ]
        vhAdvanceDeltasAndSupports[glyph] = masterModel.getDeltasAndSupports(
            vhAdvances, round=round
        )

    if vOrigMetricses:
        for glyph in glyphOrder:
            # We need to supply a vOrigs tuple with non-None default values
            # for each glyph. vOrigMetricses contains values only for those
            # glyphs which have a non-default vOrig.
            vOrigs = [
                metrics[glyph] if glyph in metrics else defaultVOrig
                for metrics, defaultVOrig in vOrigMetricses
            ]
            vOrigDeltasAndSupports[glyph] = masterModel.getDeltasAndSupports(
                vOrigs, round=round
            )

    return vhAdvanceDeltasAndSupports, vOrigDeltasAndSupports


def _add_MVAR(font, masterModel, master_ttfs, axisTags):
    log.info("Generating MVAR")

    store_builder = varStore.OnlineVarStoreBuilder(axisTags)

    records = []
    lastTableTag = None
    fontTable = None
    tables = None
    # HACK: we need to special-case post.underlineThickness and .underlinePosition
    # and unilaterally/arbitrarily define a sentinel value to distinguish the case
    # when a post table is present in a given master simply because that's where
    # the glyph names in TrueType must be stored, but the underline values are not
    # meant to be used for building MVAR's deltas. The value of -0x8000 (-36768)
    # the minimum FWord (int16) value, was chosen for its unlikelyhood to appear
    # in real-world underline position/thickness values.
    specialTags = {"unds": -0x8000, "undo": -0x8000}

    for tag, (tableTag, itemName) in sorted(MVAR_ENTRIES.items(), key=lambda kv: kv[1]):
        # For each tag, fetch the associated table from all fonts (or not when we are
        # still looking at a tag from the same tables) and set up the variation model
        # for them.
        if tableTag != lastTableTag:
            tables = fontTable = None
            if tableTag in font:
                fontTable = font[tableTag]
                tables = []
                for master in master_ttfs:
                    if tableTag not in master or (
                        tag in specialTags
                        and getattr(master[tableTag], itemName) == specialTags[tag]
                    ):
                        tables.append(None)
                    else:
                        tables.append(master[tableTag])
                model, tables = masterModel.getSubModel(tables)
                store_builder.setModel(model)
            lastTableTag = tableTag

        if tables is None:  # Tag not applicable to the master font.
            continue

        # TODO support gasp entries

        master_values = [getattr(table, itemName) for table in tables]
        if models.allEqual(master_values):
            base, varIdx = master_values[0], None
        else:
            base, varIdx = store_builder.storeMasters(master_values)
        setattr(fontTable, itemName, base)

        if varIdx is None:
            continue
        log.info("	%s: %s.%s	%s", tag, tableTag, itemName, master_values)
        rec = ot.MetricsValueRecord()
        rec.ValueTag = tag
        rec.VarIdx = varIdx
        records.append(rec)

    assert "MVAR" not in font
    if records:
        store = store_builder.finish()
        # Optimize
        mapping = store.optimize()
        for rec in records:
            rec.VarIdx = mapping[rec.VarIdx]

        MVAR = font["MVAR"] = newTable("MVAR")
        mvar = MVAR.table = ot.MVAR()
        mvar.Version = 0x00010000
        mvar.Reserved = 0
        mvar.VarStore = store
        # XXX these should not be hard-coded but computed automatically
        mvar.ValueRecordSize = 8
        mvar.ValueRecordCount = len(records)
        mvar.ValueRecord = sorted(records, key=lambda r: r.ValueTag)


def _add_BASE(font, masterModel, master_ttfs, axisTags):
    log.info("Generating BASE")

    merger = VariationMerger(masterModel, axisTags, font)
    merger.mergeTables(font, master_ttfs, ["BASE"])
    store = merger.store_builder.finish()

    if not store:
        return
    base = font["BASE"].table
    assert base.Version == 0x00010000
    base.Version = 0x00010001
    base.VarStore = store


def _merge_OTL(font, model, master_fonts, axisTags):
    otl_tags = ["GSUB", "GDEF", "GPOS"]
    if not any(tag in font for tag in otl_tags):
        return

    log.info("Merging OpenType Layout tables")
    merger = VariationMerger(model, axisTags, font)

    merger.mergeTables(font, master_fonts, otl_tags)
    store = merger.store_builder.finish()
    if not store:
        return
    try:
        GDEF = font["GDEF"].table
        assert GDEF.Version <= 0x00010002
    except KeyError:
        font["GDEF"] = newTable("GDEF")
        GDEFTable = font["GDEF"] = newTable("GDEF")
        GDEF = GDEFTable.table = ot.GDEF()
        GDEF.GlyphClassDef = None
        GDEF.AttachList = None
        GDEF.LigCaretList = None
        GDEF.MarkAttachClassDef = None
        GDEF.MarkGlyphSetsDef = None

    GDEF.Version = 0x00010003
    GDEF.VarStore = store

    # Optimize
    varidx_map = store.optimize()
    GDEF.remap_device_varidxes(varidx_map)
    if "GPOS" in font:
        font["GPOS"].table.remap_device_varidxes(varidx_map)


def _add_GSUB_feature_variations(
    font, axes, internal_axis_supports, rules, featureTags
):
    def normalize(name, value):
        return models.normalizeLocation({name: value}, internal_axis_supports)[name]

    log.info("Generating GSUB FeatureVariations")

    axis_tags = {name: axis.tag for name, axis in axes.items()}

    conditional_subs = []
    for rule in rules:
        region = []
        for conditions in rule.conditionSets:
            space = {}
            for condition in conditions:
                axis_name = condition["name"]
                if condition["minimum"] is not None:
                    minimum = normalize(axis_name, condition["minimum"])
                else:
                    minimum = -1.0
                if condition["maximum"] is not None:
                    maximum = normalize(axis_name, condition["maximum"])
                else:
                    maximum = 1.0
                tag = axis_tags[axis_name]
                space[tag] = (minimum, maximum)
            region.append(space)

        subs = {k: v for k, v in rule.subs}

        conditional_subs.append((region, subs))

    addFeatureVariations(font, conditional_subs, featureTags)


_DesignSpaceData = namedtuple(
    "_DesignSpaceData",
    [
        "axes",
        "axisMappings",
        "internal_axis_supports",
        "base_idx",
        "normalized_master_locs",
        "masters",
        "instances",
        "rules",
        "rulesProcessingLast",
        "lib",
    ],
)


def _add_CFF2(varFont, model, master_fonts):
    from .cff import merge_region_fonts

    glyphOrder = varFont.getGlyphOrder()
    if "CFF2" not in varFont:
        from fontTools.cffLib.CFFToCFF2 import convertCFFToCFF2

        convertCFFToCFF2(varFont)

    ordered_fonts_list = model.reorderMasters(master_fonts, model.reverseMapping)
    # re-ordering the master list simplifies building the CFF2 data item lists.
    merge_region_fonts(varFont, model, ordered_fonts_list, glyphOrder)


def _add_COLR(font, model, master_fonts, axisTags, colr_layer_reuse=True):
    merger = COLRVariationMerger(
        model, axisTags, font, allowLayerReuse=colr_layer_reuse
    )
    merger.mergeTables(font, master_fonts)
    store = merger.store_builder.finish()

    colr = font["COLR"].table
    if store:
        mapping = store.optimize()
        colr.VarStore = store
        varIdxes = [mapping[v] for v in merger.varIdxes]
        colr.VarIndexMap = builder.buildDeltaSetIndexMap(varIdxes)


def load_designspace(designspace, log_enabled=True, *, require_sources=True):
    # TODO: remove this and always assume 'designspace' is a DesignSpaceDocument,
    # never a file path, as that's already handled by caller
    if hasattr(designspace, "sources"):  # Assume a DesignspaceDocument
        ds = designspace
    else:  # Assume a file path
        ds = DesignSpaceDocument.fromfile(designspace)

    masters = ds.sources
    if require_sources and not masters:
        raise VarLibValidationError("Designspace must have at least one source.")
    instances = ds.instances

    # TODO: Use fontTools.designspaceLib.tagForAxisName instead.
    standard_axis_map = OrderedDict(
        [
            ("weight", ("wght", {"en": "Weight"})),
            ("width", ("wdth", {"en": "Width"})),
            ("slant", ("slnt", {"en": "Slant"})),
            ("optical", ("opsz", {"en": "Optical Size"})),
            ("italic", ("ital", {"en": "Italic"})),
        ]
    )

    # Setup axes
    if not ds.axes:
        raise VarLibValidationError(f"Designspace must have at least one axis.")

    axes = OrderedDict()
    for axis_index, axis in enumerate(ds.axes):
        axis_name = axis.name
        if not axis_name:
            if not axis.tag:
                raise VarLibValidationError(f"Axis at index {axis_index} needs a tag.")
            axis_name = axis.name = axis.tag

        if axis_name in standard_axis_map:
            if axis.tag is None:
                axis.tag = standard_axis_map[axis_name][0]
            if not axis.labelNames:
                axis.labelNames.update(standard_axis_map[axis_name][1])
        else:
            if not axis.tag:
                raise VarLibValidationError(f"Axis at index {axis_index} needs a tag.")
            if not axis.labelNames:
                axis.labelNames["en"] = tostr(axis_name)

        axes[axis_name] = axis
    if log_enabled:
        log.info("Axes:\n%s", pformat([axis.asdict() for axis in axes.values()]))

    axisMappings = ds.axisMappings
    if axisMappings and log_enabled:
        log.info("Mappings:\n%s", pformat(axisMappings))

    # Check all master and instance locations are valid and fill in defaults
    for obj in masters + instances:
        obj_name = obj.name or obj.styleName or ""
        loc = obj.getFullDesignLocation(ds)
        obj.designLocation = loc
        if loc is None:
            raise VarLibValidationError(
                f"Source or instance '{obj_name}' has no location."
            )
        for axis_name in loc.keys():
            if axis_name not in axes:
                raise VarLibValidationError(
                    f"Location axis '{axis_name}' unknown for '{obj_name}'."
                )
        for axis_name, axis in axes.items():
            v = axis.map_backward(loc[axis_name])
            if not (axis.minimum <= v <= axis.maximum):
                raise VarLibValidationError(
                    f"Source or instance '{obj_name}' has out-of-range location "
                    f"for axis '{axis_name}': is mapped to {v} but must be in "
                    f"mapped range [{axis.minimum}..{axis.maximum}] (NOTE: all "
                    "values are in user-space)."
                )

    # Normalize master locations

    internal_master_locs = [o.getFullDesignLocation(ds) for o in masters]
    if log_enabled:
        log.info("Internal master locations:\n%s", pformat(internal_master_locs))

    # TODO This mapping should ideally be moved closer to logic in _add_fvar/avar
    internal_axis_supports = {}
    for axis in axes.values():
        triple = (axis.minimum, axis.default, axis.maximum)
        internal_axis_supports[axis.name] = [axis.map_forward(v) for v in triple]
    if log_enabled:
        log.info("Internal axis supports:\n%s", pformat(internal_axis_supports))

    normalized_master_locs = [
        models.normalizeLocation(m, internal_axis_supports)
        for m in internal_master_locs
    ]
    if log_enabled:
        log.info("Normalized master locations:\n%s", pformat(normalized_master_locs))

    # Find base master
    base_idx = None
    for i, m in enumerate(normalized_master_locs):
        if all(v == 0 for v in m.values()):
            if base_idx is not None:
                raise VarLibValidationError(
                    "More than one base master found in Designspace."
                )
            base_idx = i
    if require_sources and base_idx is None:
        raise VarLibValidationError(
            "Base master not found; no master at default location?"
        )
    if log_enabled:
        log.info("Index of base master: %s", base_idx)

    return _DesignSpaceData(
        axes,
        axisMappings,
        internal_axis_supports,
        base_idx,
        normalized_master_locs,
        masters,
        instances,
        ds.rules,
        ds.rulesProcessingLast,
        ds.lib,
    )


# https://docs.microsoft.com/en-us/typography/opentype/spec/os2#uswidthclass
WDTH_VALUE_TO_OS2_WIDTH_CLASS = {
    50: 1,
    62.5: 2,
    75: 3,
    87.5: 4,
    100: 5,
    112.5: 6,
    125: 7,
    150: 8,
    200: 9,
}


def set_default_weight_width_slant(font, location):
    if "OS/2" in font:
        if "wght" in location:
            weight_class = otRound(max(1, min(location["wght"], 1000)))
            if font["OS/2"].usWeightClass != weight_class:
                log.info("Setting OS/2.usWeightClass = %s", weight_class)
                font["OS/2"].usWeightClass = weight_class

        if "wdth" in location:
            # map 'wdth' axis (50..200) to OS/2.usWidthClass (1..9), rounding to closest
            widthValue = min(max(location["wdth"], 50), 200)
            widthClass = otRound(
                models.piecewiseLinearMap(widthValue, WDTH_VALUE_TO_OS2_WIDTH_CLASS)
            )
            if font["OS/2"].usWidthClass != widthClass:
                log.info("Setting OS/2.usWidthClass = %s", widthClass)
                font["OS/2"].usWidthClass = widthClass

    if "slnt" in location and "post" in font:
        italicAngle = max(-90, min(location["slnt"], 90))
        if font["post"].italicAngle != italicAngle:
            log.info("Setting post.italicAngle = %s", italicAngle)
            font["post"].italicAngle = italicAngle


def drop_implied_oncurve_points(*masters: TTFont) -> int:
    """Drop impliable on-curve points from all the simple glyphs in masters.

    In TrueType glyf outlines, on-curve points can be implied when they are located
    exactly at the midpoint of the line connecting two consecutive off-curve points.

    The input masters' glyf tables are assumed to contain same-named glyphs that are
    interpolatable. Oncurve points are only dropped if they can be implied for all
    the masters. The fonts are modified in-place.

    Args:
        masters: The TTFont(s) to modify

    Returns:
        The total number of points that were dropped if any.

    Reference:
    https://developer.apple.com/fonts/TrueType-Reference-Manual/RM01/Chap1.html
    """

    count = 0
    glyph_masters = defaultdict(list)
    # multiple DS source may point to the same TTFont object and we want to
    # avoid processing the same glyph twice as they are modified in-place
    for font in {id(m): m for m in masters}.values():
        glyf = font["glyf"]
        for glyphName in glyf.keys():
            glyph_masters[glyphName].append(glyf[glyphName])
    count = 0
    for glyphName, glyphs in glyph_masters.items():
        try:
            dropped = dropImpliedOnCurvePoints(*glyphs)
        except ValueError as e:
            # we don't fail for incompatible glyphs in _add_gvar so we shouldn't here
            log.warning("Failed to drop implied oncurves for %r: %s", glyphName, e)
        else:
            count += len(dropped)
    return count


def build_many(
    designspace: DesignSpaceDocument,
    master_finder=lambda s: s,
    exclude=[],
    optimize=True,
    skip_vf=lambda vf_name: False,
    colr_layer_reuse=True,
    drop_implied_oncurves=False,
):
    """
    Build variable fonts from a designspace file, version 5 which can define
    several VFs, or version 4 which has implicitly one VF covering the whole doc.

    If master_finder is set, it should be a callable that takes master
    filename as found in designspace file and map it to master font
    binary as to be opened (eg. .ttf or .otf).

    skip_vf can be used to skip building some of the variable fonts defined in
    the input designspace. It's a predicate that takes as argument the name
    of the variable font and returns `bool`.

    Always returns a Dict[str, TTFont] keyed by VariableFontDescriptor.name
    """
    res = {}
    # varLib.build (used further below) by default only builds an incomplete 'STAT'
    # with an empty AxisValueArray--unless the VF inherited 'STAT' from its base master.
    # Designspace version 5 can also be used to define 'STAT' labels or customize
    # axes ordering, etc. To avoid overwriting a pre-existing 'STAT' or redoing the
    # same work twice, here we check if designspace contains any 'STAT' info before
    # proceeding to call buildVFStatTable for each VF.
    # https://github.com/fonttools/fonttools/pull/3024
    # https://github.com/fonttools/fonttools/issues/3045
    doBuildStatFromDSv5 = (
        "STAT" not in exclude
        and designspace.formatTuple >= (5, 0)
        and (
            any(a.axisLabels or a.axisOrdering is not None for a in designspace.axes)
            or designspace.locationLabels
        )
    )
    for _location, subDoc in splitInterpolable(designspace):
        for name, vfDoc in splitVariableFonts(subDoc):
            if skip_vf(name):
                log.debug(f"Skipping variable TTF font: {name}")
                continue
            vf = build(
                vfDoc,
                master_finder,
                exclude=exclude,
                optimize=optimize,
                colr_layer_reuse=colr_layer_reuse,
                drop_implied_oncurves=drop_implied_oncurves,
            )[0]
            if doBuildStatFromDSv5:
                buildVFStatTable(vf, designspace, name)
            res[name] = vf
    return res


def build(
    designspace,
    master_finder=lambda s: s,
    exclude=[],
    optimize=True,
    colr_layer_reuse=True,
    drop_implied_oncurves=False,
):
    """
    Build variation font from a designspace file.

    If master_finder is set, it should be a callable that takes master
    filename as found in designspace file and map it to master font
    binary as to be opened (eg. .ttf or .otf).
    """
    if hasattr(designspace, "sources"):  # Assume a DesignspaceDocument
        pass
    else:  # Assume a file path
        designspace = DesignSpaceDocument.fromfile(designspace)

    ds = load_designspace(designspace)
    log.info("Building variable font")

    log.info("Loading master fonts")
    master_fonts = load_masters(designspace, master_finder)

    # TODO: 'master_ttfs' is unused except for return value, remove later
    master_ttfs = []
    for master in master_fonts:
        try:
            master_ttfs.append(master.reader.file.name)
        except AttributeError:
            master_ttfs.append(None)  # in-memory fonts have no path

    if drop_implied_oncurves and "glyf" in master_fonts[ds.base_idx]:
        drop_count = drop_implied_oncurve_points(*master_fonts)
        log.info(
            "Dropped %s on-curve points from simple glyphs in the 'glyf' table",
            drop_count,
        )

    # Copy the base master to work from it
    vf = deepcopy(master_fonts[ds.base_idx])

    if "DSIG" in vf:
        del vf["DSIG"]

    # TODO append masters as named-instances as well; needs .designspace change.
    fvar = _add_fvar(vf, ds.axes, ds.instances)
    if "STAT" not in exclude:
        _add_stat(vf)

    # Map from axis names to axis tags...
    normalized_master_locs = [
        {ds.axes[k].tag: v for k, v in loc.items()} for loc in ds.normalized_master_locs
    ]
    # From here on, we use fvar axes only
    axisTags = [axis.axisTag for axis in fvar.axes]

    # Assume single-model for now.
    model = models.VariationModel(normalized_master_locs, axisOrder=axisTags)
    assert 0 == model.mapping[ds.base_idx]

    log.info("Building variations tables")
    if "avar" not in exclude:
        _add_avar(vf, ds.axes, ds.axisMappings, axisTags)
    if "BASE" not in exclude and "BASE" in vf:
        _add_BASE(vf, model, master_fonts, axisTags)
    if "MVAR" not in exclude:
        _add_MVAR(vf, model, master_fonts, axisTags)
    if "HVAR" not in exclude:
        _add_HVAR(vf, model, master_fonts, axisTags)
    if "VVAR" not in exclude and "vmtx" in vf:
        _add_VVAR(vf, model, master_fonts, axisTags)
    if "GDEF" not in exclude or "GPOS" not in exclude:
        _merge_OTL(vf, model, master_fonts, axisTags)
    if "gvar" not in exclude and "glyf" in vf:
        _add_gvar(vf, model, master_fonts, optimize=optimize)
    if "cvar" not in exclude and "glyf" in vf:
        _merge_TTHinting(vf, model, master_fonts)
    if "GSUB" not in exclude and ds.rules:
        featureTags = _feature_variations_tags(ds)
        _add_GSUB_feature_variations(
            vf, ds.axes, ds.internal_axis_supports, ds.rules, featureTags
        )
    if "CFF2" not in exclude and ("CFF " in vf or "CFF2" in vf):
        _add_CFF2(vf, model, master_fonts)
        if "post" in vf:
            # set 'post' to format 2 to keep the glyph names dropped from CFF2
            post = vf["post"]
            if post.formatType != 2.0:
                post.formatType = 2.0
                post.extraNames = []
                post.mapping = {}
    if "COLR" not in exclude and "COLR" in vf and vf["COLR"].version > 0:
        _add_COLR(vf, model, master_fonts, axisTags, colr_layer_reuse)

    set_default_weight_width_slant(
        vf, location={axis.axisTag: axis.defaultValue for axis in vf["fvar"].axes}
    )

    for tag in exclude:
        if tag in vf:
            del vf[tag]

    # TODO: Only return vf for 4.0+, the rest is unused.
    return vf, model, master_ttfs


def _open_font(path, master_finder=lambda s: s):
    # load TTFont masters from given 'path': this can be either a .TTX or an
    # OpenType binary font; or if neither of these, try use the 'master_finder'
    # callable to resolve the path to a valid .TTX or OpenType font binary.
    from fontTools.ttx import guessFileType

    master_path = os.path.normpath(path)
    tp = guessFileType(master_path)
    if tp is None:
        # not an OpenType binary/ttx, fall back to the master finder.
        master_path = master_finder(master_path)
        tp = guessFileType(master_path)
    if tp in ("TTX", "OTX"):
        font = TTFont()
        font.importXML(master_path)
    elif tp in ("TTF", "OTF", "WOFF", "WOFF2"):
        font = TTFont(master_path)
    else:
        raise VarLibValidationError("Invalid master path: %r" % master_path)
    return font


def load_masters(designspace, master_finder=lambda s: s):
    """Ensure that all SourceDescriptor.font attributes have an appropriate TTFont
    object loaded, or else open TTFont objects from the SourceDescriptor.path
    attributes.

    The paths can point to either an OpenType font, a TTX file, or a UFO. In the
    latter case, use the provided master_finder callable to map from UFO paths to
    the respective master font binaries (e.g. .ttf, .otf or .ttx).

    Return list of master TTFont objects in the same order they are listed in the
    DesignSpaceDocument.
    """
    for master in designspace.sources:
        # If a SourceDescriptor has a layer name, demand that the compiled TTFont
        # be supplied by the caller. This spares us from modifying MasterFinder.
        if master.layerName and master.font is None:
            raise VarLibValidationError(
                f"Designspace source '{master.name or '<Unknown>'}' specified a "
                "layer name but lacks the required TTFont object in the 'font' "
                "attribute."
            )

    return designspace.loadSourceFonts(_open_font, master_finder=master_finder)


class MasterFinder(object):
    def __init__(self, template):
        self.template = template

    def __call__(self, src_path):
        fullname = os.path.abspath(src_path)
        dirname, basename = os.path.split(fullname)
        stem, ext = os.path.splitext(basename)
        path = self.template.format(
            fullname=fullname,
            dirname=dirname,
            basename=basename,
            stem=stem,
            ext=ext,
        )
        return os.path.normpath(path)


def _feature_variations_tags(ds):
    raw_tags = ds.lib.get(
        FEAVAR_FEATURETAG_LIB_KEY,
        "rclt" if ds.rulesProcessingLast else "rvrn",
    )
    return sorted({t.strip() for t in raw_tags.split(",")})


def addGSUBFeatureVariations(vf, designspace, featureTags=(), *, log_enabled=False):
    """Add GSUB FeatureVariations table to variable font, based on DesignSpace rules.

    Args:
        vf: A TTFont object representing the variable font.
        designspace: A DesignSpaceDocument object.
        featureTags: Optional feature tag(s) to use for the FeatureVariations records.
            If unset, the key 'com.github.fonttools.varLib.featureVarsFeatureTag' is
            looked up in the DS <lib> and used; otherwise the default is 'rclt' if
            the <rules processing="last"> attribute is set, else 'rvrn'.
            See <https://fonttools.readthedocs.io/en/latest/designspaceLib/xml.html#rules-element>
        log_enabled: If True, log info about DS axes and sources. Default is False, as
            the same info may have already been logged as part of varLib.build.
    """
    ds = load_designspace(designspace, log_enabled=log_enabled)
    if not ds.rules:
        return
    if not featureTags:
        featureTags = _feature_variations_tags(ds)
    _add_GSUB_feature_variations(
        vf, ds.axes, ds.internal_axis_supports, ds.rules, featureTags
    )


def main(args=None):
    """Build variable fonts from a designspace file and masters"""
    from argparse import ArgumentParser
    from fontTools import configLogger

    parser = ArgumentParser(prog="varLib", description=main.__doc__)
    parser.add_argument("designspace")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-o", metavar="OUTPUTFILE", dest="outfile", default=None, help="output file"
    )
    output_group.add_argument(
        "-d",
        "--output-dir",
        metavar="OUTPUTDIR",
        default=None,
        help="output dir (default: same as input designspace file)",
    )
    parser.add_argument(
        "-x",
        metavar="TAG",
        dest="exclude",
        action="append",
        default=[],
        help="exclude table",
    )
    parser.add_argument(
        "--disable-iup",
        dest="optimize",
        action="store_false",
        help="do not perform IUP optimization",
    )
    parser.add_argument(
        "--no-colr-layer-reuse",
        dest="colr_layer_reuse",
        action="store_false",
        help="do not rebuild variable COLR table to optimize COLR layer reuse",
    )
    parser.add_argument(
        "--drop-implied-oncurves",
        action="store_true",
        help=(
            "drop on-curve points that can be implied when exactly in the middle of "
            "two off-curve points (only applies to TrueType fonts)"
        ),
    )
    parser.add_argument(
        "--master-finder",
        default="master_ttf_interpolatable/{stem}.ttf",
        help=(
            "templated string used for finding binary font "
            "files given the source file names defined in the "
            "designspace document. The following special strings "
            "are defined: {fullname} is the absolute source file "
            "name; {basename} is the file name without its "
            "directory; {stem} is the basename without the file "
            "extension; {ext} is the source file extension; "
            "{dirname} is the directory of the absolute file "
            'name. The default value is "%(default)s".'
        ),
    )
    parser.add_argument(
        "--variable-fonts",
        default=".*",
        metavar="VF_NAME",
        help=(
            "Filter the list of variable fonts produced from the input "
            "Designspace v5 file. By default all listed variable fonts are "
            "generated. To generate a specific variable font (or variable fonts) "
            'that match a given "name" attribute, you can pass as argument '
            "the full name or a regular expression. E.g.: --variable-fonts "
            '"MyFontVF_WeightOnly"; or --variable-fonts "MyFontVFItalic_.*".'
        ),
    )
    logging_group = parser.add_mutually_exclusive_group(required=False)
    logging_group.add_argument(
        "-v", "--verbose", action="store_true", help="Run more verbosely."
    )
    logging_group.add_argument(
        "-q", "--quiet", action="store_true", help="Turn verbosity off."
    )
    options = parser.parse_args(args)

    configLogger(
        level=("DEBUG" if options.verbose else "ERROR" if options.quiet else "INFO")
    )

    designspace_filename = options.designspace
    designspace = DesignSpaceDocument.fromfile(designspace_filename)

    vf_descriptors = designspace.getVariableFonts()
    if not vf_descriptors:
        parser.error(f"No variable fonts in given designspace {designspace.path!r}")

    vfs_to_build = []
    for vf in vf_descriptors:
        # Skip variable fonts that do not match the user's inclusion regex if given.
        if not fullmatch(options.variable_fonts, vf.name):
            continue
        vfs_to_build.append(vf)

    if not vfs_to_build:
        parser.error(f"No variable fonts matching {options.variable_fonts!r}")

    if options.outfile is not None and len(vfs_to_build) > 1:
        parser.error(
            "can't specify -o because there are multiple VFs to build; "
            "use --output-dir, or select a single VF with --variable-fonts"
        )

    output_dir = options.output_dir
    if output_dir is None:
        output_dir = os.path.dirname(designspace_filename)

    vf_name_to_output_path = {}
    if len(vfs_to_build) == 1 and options.outfile is not None:
        vf_name_to_output_path[vfs_to_build[0].name] = options.outfile
    else:
        for vf in vfs_to_build:
            filename = vf.filename if vf.filename is not None else vf.name + ".{ext}"
            vf_name_to_output_path[vf.name] = os.path.join(output_dir, filename)

    finder = MasterFinder(options.master_finder)

    vfs = build_many(
        designspace,
        finder,
        exclude=options.exclude,
        optimize=options.optimize,
        colr_layer_reuse=options.colr_layer_reuse,
        drop_implied_oncurves=options.drop_implied_oncurves,
    )

    for vf_name, vf in vfs.items():
        ext = "otf" if vf.sfntVersion == "OTTO" else "ttf"
        output_path = vf_name_to_output_path[vf_name].format(ext=ext)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        log.info("Saving variation font %s", output_path)
        vf.save(output_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        sys.exit(main())
    import doctest

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\symbolic.py ===
"""Fortran/C symbolic expressions

References:
- J3/21-007: Draft Fortran 202x. https://j3-fortran.org/doc/year/21/21-007.pdf

Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""

# To analyze Fortran expressions to solve dimensions specifications,
# for instances, we implement a minimal symbolic engine for parsing
# expressions into a tree of expression instances. As a first
# instance, we care only about arithmetic expressions involving
# integers and operations like addition (+), subtraction (-),
# multiplication (*), division (Fortran / is Python //, Fortran // is
# concatenate), and exponentiation (**).  In addition, .pyf files may
# contain C expressions that support here is implemented as well.
#
# TODO: support logical constants (Op.BOOLEAN)
# TODO: support logical operators (.AND., ...)
# TODO: support defined operators (.MYOP., ...)
#
__all__ = ['Expr']


import re
import warnings
from enum import Enum
from math import gcd


class Language(Enum):
    """
    Used as Expr.tostring language argument.
    """
    Python = 0
    Fortran = 1
    C = 2


class Op(Enum):
    """
    Used as Expr op attribute.
    """
    INTEGER = 10
    REAL = 12
    COMPLEX = 15
    STRING = 20
    ARRAY = 30
    SYMBOL = 40
    TERNARY = 100
    APPLY = 200
    INDEXING = 210
    CONCAT = 220
    RELATIONAL = 300
    TERMS = 1000
    FACTORS = 2000
    REF = 3000
    DEREF = 3001


class RelOp(Enum):
    """
    Used in Op.RELATIONAL expression to specify the function part.
    """
    EQ = 1
    NE = 2
    LT = 3
    LE = 4
    GT = 5
    GE = 6

    @classmethod
    def fromstring(cls, s, language=Language.C):
        if language is Language.Fortran:
            return {'.eq.': RelOp.EQ, '.ne.': RelOp.NE,
                    '.lt.': RelOp.LT, '.le.': RelOp.LE,
                    '.gt.': RelOp.GT, '.ge.': RelOp.GE}[s.lower()]
        return {'==': RelOp.EQ, '!=': RelOp.NE, '<': RelOp.LT,
                '<=': RelOp.LE, '>': RelOp.GT, '>=': RelOp.GE}[s]

    def tostring(self, language=Language.C):
        if language is Language.Fortran:
            return {RelOp.EQ: '.eq.', RelOp.NE: '.ne.',
                    RelOp.LT: '.lt.', RelOp.LE: '.le.',
                    RelOp.GT: '.gt.', RelOp.GE: '.ge.'}[self]
        return {RelOp.EQ: '==', RelOp.NE: '!=',
                RelOp.LT: '<', RelOp.LE: '<=',
                RelOp.GT: '>', RelOp.GE: '>='}[self]


class ArithOp(Enum):
    """
    Used in Op.APPLY expression to specify the function part.
    """
    POS = 1
    NEG = 2
    ADD = 3
    SUB = 4
    MUL = 5
    DIV = 6
    POW = 7


class OpError(Exception):
    pass


class Precedence(Enum):
    """
    Used as Expr.tostring precedence argument.
    """
    ATOM = 0
    POWER = 1
    UNARY = 2
    PRODUCT = 3
    SUM = 4
    LT = 6
    EQ = 7
    LAND = 11
    LOR = 12
    TERNARY = 13
    ASSIGN = 14
    TUPLE = 15
    NONE = 100


integer_types = (int,)
number_types = (int, float)


def _pairs_add(d, k, v):
    # Internal utility method for updating terms and factors data.
    c = d.get(k)
    if c is None:
        d[k] = v
    else:
        c = c + v
        if c:
            d[k] = c
        else:
            del d[k]


class ExprWarning(UserWarning):
    pass


def ewarn(message):
    warnings.warn(message, ExprWarning, stacklevel=2)


class Expr:
    """Represents a Fortran expression as a op-data pair.

    Expr instances are hashable and sortable.
    """

    @staticmethod
    def parse(s, language=Language.C):
        """Parse a Fortran expression to a Expr.
        """
        return fromstring(s, language=language)

    def __init__(self, op, data):
        assert isinstance(op, Op)

        # sanity checks
        if op is Op.INTEGER:
            # data is a 2-tuple of numeric object and a kind value
            # (default is 4)
            assert isinstance(data, tuple) and len(data) == 2
            assert isinstance(data[0], int)
            assert isinstance(data[1], (int, str)), data
        elif op is Op.REAL:
            # data is a 2-tuple of numeric object and a kind value
            # (default is 4)
            assert isinstance(data, tuple) and len(data) == 2
            assert isinstance(data[0], float)
            assert isinstance(data[1], (int, str)), data
        elif op is Op.COMPLEX:
            # data is a 2-tuple of constant expressions
            assert isinstance(data, tuple) and len(data) == 2
        elif op is Op.STRING:
            # data is a 2-tuple of quoted string and a kind value
            # (default is 1)
            assert isinstance(data, tuple) and len(data) == 2
            assert (isinstance(data[0], str)
                    and data[0][::len(data[0]) - 1] in ('""', "''", '@@'))
            assert isinstance(data[1], (int, str)), data
        elif op is Op.SYMBOL:
            # data is any hashable object
            assert hash(data) is not None
        elif op in (Op.ARRAY, Op.CONCAT):
            # data is a tuple of expressions
            assert isinstance(data, tuple)
            assert all(isinstance(item, Expr) for item in data), data
        elif op in (Op.TERMS, Op.FACTORS):
            # data is {<term|base>:<coeff|exponent>} where dict values
            # are nonzero Python integers
            assert isinstance(data, dict)
        elif op is Op.APPLY:
            # data is (<function>, <operands>, <kwoperands>) where
            # operands are Expr instances
            assert isinstance(data, tuple) and len(data) == 3
            # function is any hashable object
            assert hash(data[0]) is not None
            assert isinstance(data[1], tuple)
            assert isinstance(data[2], dict)
        elif op is Op.INDEXING:
            # data is (<object>, <indices>)
            assert isinstance(data, tuple) and len(data) == 2
            # function is any hashable object
            assert hash(data[0]) is not None
        elif op is Op.TERNARY:
            # data is (<cond>, <expr1>, <expr2>)
            assert isinstance(data, tuple) and len(data) == 3
        elif op in (Op.REF, Op.DEREF):
            # data is Expr instance
            assert isinstance(data, Expr)
        elif op is Op.RELATIONAL:
            # data is (<relop>, <left>, <right>)
            assert isinstance(data, tuple) and len(data) == 3
        else:
            raise NotImplementedError(
                f'unknown op or missing sanity check: {op}')

        self.op = op
        self.data = data

    def __eq__(self, other):
        return (isinstance(other, Expr)
                and self.op is other.op
                and self.data == other.data)

    def __hash__(self):
        if self.op in (Op.TERMS, Op.FACTORS):
            data = tuple(sorted(self.data.items()))
        elif self.op is Op.APPLY:
            data = self.data[:2] + tuple(sorted(self.data[2].items()))
        else:
            data = self.data
        return hash((self.op, data))

    def __lt__(self, other):
        if isinstance(other, Expr):
            if self.op is not other.op:
                return self.op.value < other.op.value
            if self.op in (Op.TERMS, Op.FACTORS):
                return (tuple(sorted(self.data.items()))
                        < tuple(sorted(other.data.items())))
            if self.op is Op.APPLY:
                if self.data[:2] != other.data[:2]:
                    return self.data[:2] < other.data[:2]
                return tuple(sorted(self.data[2].items())) < tuple(
                    sorted(other.data[2].items()))
            return self.data < other.data
        return NotImplemented

    def __le__(self, other): return self == other or self < other

    def __gt__(self, other): return not (self <= other)

    def __ge__(self, other): return not (self < other)

    def __repr__(self):
        return f'{type(self).__name__}({self.op}, {self.data!r})'

    def __str__(self):
        return self.tostring()

    def tostring(self, parent_precedence=Precedence.NONE,
                 language=Language.Fortran):
        """Return a string representation of Expr.
        """
        if self.op in (Op.INTEGER, Op.REAL):
            precedence = (Precedence.SUM if self.data[0] < 0
                          else Precedence.ATOM)
            r = str(self.data[0]) + (f'_{self.data[1]}'
                                     if self.data[1] != 4 else '')
        elif self.op is Op.COMPLEX:
            r = ', '.join(item.tostring(Precedence.TUPLE, language=language)
                          for item in self.data)
            r = '(' + r + ')'
            precedence = Precedence.ATOM
        elif self.op is Op.SYMBOL:
            precedence = Precedence.ATOM
            r = str(self.data)
        elif self.op is Op.STRING:
            r = self.data[0]
            if self.data[1] != 1:
                r = self.data[1] + '_' + r
            precedence = Precedence.ATOM
        elif self.op is Op.ARRAY:
            r = ', '.join(item.tostring(Precedence.TUPLE, language=language)
                          for item in self.data)
            r = '[' + r + ']'
            precedence = Precedence.ATOM
        elif self.op is Op.TERMS:
            terms = []
            for term, coeff in sorted(self.data.items()):
                if coeff < 0:
                    op = ' - '
                    coeff = -coeff
                else:
                    op = ' + '
                if coeff == 1:
                    term = term.tostring(Precedence.SUM, language=language)
                elif term == as_number(1):
                    term = str(coeff)
                else:
                    term = f'{coeff} * ' + term.tostring(
                        Precedence.PRODUCT, language=language)
                if terms:
                    terms.append(op)
                elif op == ' - ':
                    terms.append('-')
                terms.append(term)
            r = ''.join(terms) or '0'
            precedence = Precedence.SUM if terms else Precedence.ATOM
        elif self.op is Op.FACTORS:
            factors = []
            tail = []
            for base, exp in sorted(self.data.items()):
                op = ' * '
                if exp == 1:
                    factor = base.tostring(Precedence.PRODUCT,
                                           language=language)
                elif language is Language.C:
                    if exp in range(2, 10):
                        factor = base.tostring(Precedence.PRODUCT,
                                               language=language)
                        factor = ' * '.join([factor] * exp)
                    elif exp in range(-10, 0):
                        factor = base.tostring(Precedence.PRODUCT,
                                               language=language)
                        tail += [factor] * -exp
                        continue
                    else:
                        factor = base.tostring(Precedence.TUPLE,
                                               language=language)
                        factor = f'pow({factor}, {exp})'
                else:
                    factor = base.tostring(Precedence.POWER,
                                           language=language) + f' ** {exp}'
                if factors:
                    factors.append(op)
                factors.append(factor)
            if tail:
                if not factors:
                    factors += ['1']
                factors += ['/', '(', ' * '.join(tail), ')']
            r = ''.join(factors) or '1'
            precedence = Precedence.PRODUCT if factors else Precedence.ATOM
        elif self.op is Op.APPLY:
            name, args, kwargs = self.data
            if name is ArithOp.DIV and language is Language.C:
                numer, denom = [arg.tostring(Precedence.PRODUCT,
                                             language=language)
                                for arg in args]
                r = f'{numer} / {denom}'
                precedence = Precedence.PRODUCT
            else:
                args = [arg.tostring(Precedence.TUPLE, language=language)
                        for arg in args]
                args += [k + '=' + v.tostring(Precedence.NONE)
                         for k, v in kwargs.items()]
                r = f'{name}({", ".join(args)})'
                precedence = Precedence.ATOM
        elif self.op is Op.INDEXING:
            name = self.data[0]
            args = [arg.tostring(Precedence.TUPLE, language=language)
                    for arg in self.data[1:]]
            r = f'{name}[{", ".join(args)}]'
            precedence = Precedence.ATOM
        elif self.op is Op.CONCAT:
            args = [arg.tostring(Precedence.PRODUCT, language=language)
                    for arg in self.data]
            r = " // ".join(args)
            precedence = Precedence.PRODUCT
        elif self.op is Op.TERNARY:
            cond, expr1, expr2 = [a.tostring(Precedence.TUPLE,
                                             language=language)
                                  for a in self.data]
            if language is Language.C:
                r = f'({cond}?{expr1}:{expr2})'
            elif language is Language.Python:
                r = f'({expr1} if {cond} else {expr2})'
            elif language is Language.Fortran:
                r = f'merge({expr1}, {expr2}, {cond})'
            else:
                raise NotImplementedError(
                    f'tostring for {self.op} and {language}')
            precedence = Precedence.ATOM
        elif self.op is Op.REF:
            r = '&' + self.data.tostring(Precedence.UNARY, language=language)
            precedence = Precedence.UNARY
        elif self.op is Op.DEREF:
            r = '*' + self.data.tostring(Precedence.UNARY, language=language)
            precedence = Precedence.UNARY
        elif self.op is Op.RELATIONAL:
            rop, left, right = self.data
            precedence = (Precedence.EQ if rop in (RelOp.EQ, RelOp.NE)
                          else Precedence.LT)
            left = left.tostring(precedence, language=language)
            right = right.tostring(precedence, language=language)
            rop = rop.tostring(language=language)
            r = f'{left} {rop} {right}'
        else:
            raise NotImplementedError(f'tostring for op {self.op}')
        if parent_precedence.value < precedence.value:
            # If parent precedence is higher than operand precedence,
            # operand will be enclosed in parenthesis.
            return '(' + r + ')'
        return r

    def __pos__(self):
        return self

    def __neg__(self):
        return self * -1

    def __add__(self, other):
        other = as_expr(other)
        if isinstance(other, Expr):
            if self.op is other.op:
                if self.op in (Op.INTEGER, Op.REAL):
                    return as_number(
                        self.data[0] + other.data[0],
                        max(self.data[1], other.data[1]))
                if self.op is Op.COMPLEX:
                    r1, i1 = self.data
                    r2, i2 = other.data
                    return as_complex(r1 + r2, i1 + i2)
                if self.op is Op.TERMS:
                    r = Expr(self.op, dict(self.data))
                    for k, v in other.data.items():
                        _pairs_add(r.data, k, v)
                    return normalize(r)
            if self.op is Op.COMPLEX and other.op in (Op.INTEGER, Op.REAL):
                return self + as_complex(other)
            elif self.op in (Op.INTEGER, Op.REAL) and other.op is Op.COMPLEX:
                return as_complex(self) + other
            elif self.op is Op.REAL and other.op is Op.INTEGER:
                return self + as_real(other, kind=self.data[1])
            elif self.op is Op.INTEGER and other.op is Op.REAL:
                return as_real(self, kind=other.data[1]) + other
            return as_terms(self) + as_terms(other)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, number_types):
            return as_number(other) + self
        return NotImplemented

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        if isinstance(other, number_types):
            return as_number(other) - self
        return NotImplemented

    def __mul__(self, other):
        other = as_expr(other)
        if isinstance(other, Expr):
            if self.op is other.op:
                if self.op in (Op.INTEGER, Op.REAL):
                    return as_number(self.data[0] * other.data[0],
                                     max(self.data[1], other.data[1]))
                elif self.op is Op.COMPLEX:
                    r1, i1 = self.data
                    r2, i2 = other.data
                    return as_complex(r1 * r2 - i1 * i2, r1 * i2 + r2 * i1)

                if self.op is Op.FACTORS:
                    r = Expr(self.op, dict(self.data))
                    for k, v in other.data.items():
                        _pairs_add(r.data, k, v)
                    return normalize(r)
                elif self.op is Op.TERMS:
                    r = Expr(self.op, {})
                    for t1, c1 in self.data.items():
                        for t2, c2 in other.data.items():
                            _pairs_add(r.data, t1 * t2, c1 * c2)
                    return normalize(r)

            if self.op is Op.COMPLEX and other.op in (Op.INTEGER, Op.REAL):
                return self * as_complex(other)
            elif other.op is Op.COMPLEX and self.op in (Op.INTEGER, Op.REAL):
                return as_complex(self) * other
            elif self.op is Op.REAL and other.op is Op.INTEGER:
                return self * as_real(other, kind=self.data[1])
            elif self.op is Op.INTEGER and other.op is Op.REAL:
                return as_real(self, kind=other.data[1]) * other

            if self.op is Op.TERMS:
                return self * as_terms(other)
            elif other.op is Op.TERMS:
                return as_terms(self) * other

            return as_factors(self) * as_factors(other)
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, number_types):
            return as_number(other) * self
        return NotImplemented

    def __pow__(self, other):
        other = as_expr(other)
        if isinstance(other, Expr):
            if other.op is Op.INTEGER:
                exponent = other.data[0]
                # TODO: other kind not used
                if exponent == 0:
                    return as_number(1)
                if exponent == 1:
                    return self
                if exponent > 0:
                    if self.op is Op.FACTORS:
                        r = Expr(self.op, {})
                        for k, v in self.data.items():
                            r.data[k] = v * exponent
                        return normalize(r)
                    return self * (self ** (exponent - 1))
                elif exponent != -1:
                    return (self ** (-exponent)) ** -1
                return Expr(Op.FACTORS, {self: exponent})
            return as_apply(ArithOp.POW, self, other)
        return NotImplemented

    def __truediv__(self, other):
        other = as_expr(other)
        if isinstance(other, Expr):
            # Fortran / is different from Python /:
            # - `/` is a truncate operation for integer operands
            return normalize(as_apply(ArithOp.DIV, self, other))
        return NotImplemented

    def __rtruediv__(self, other):
        other = as_expr(other)
        if isinstance(other, Expr):
            return other / self
        return NotImplemented

    def __floordiv__(self, other):
        other = as_expr(other)
        if isinstance(other, Expr):
            # Fortran // is different from Python //:
            # - `//` is a concatenate operation for string operands
            return normalize(Expr(Op.CONCAT, (self, other)))
        return NotImplemented

    def __rfloordiv__(self, other):
        other = as_expr(other)
        if isinstance(other, Expr):
            return other // self
        return NotImplemented

    def __call__(self, *args, **kwargs):
        # In Fortran, parenthesis () are use for both function call as
        # well as indexing operations.
        #
        # TODO: implement a method for deciding when __call__ should
        # return an INDEXING expression.
        return as_apply(self, *map(as_expr, args),
                        **{k: as_expr(v) for k, v in kwargs.items()})

    def __getitem__(self, index):
        # Provided to support C indexing operations that .pyf files
        # may contain.
        index = as_expr(index)
        if not isinstance(index, tuple):
            index = index,
        if len(index) > 1:
            ewarn(f'C-index should be a single expression but got `{index}`')
        return Expr(Op.INDEXING, (self,) + index)

    def substitute(self, symbols_map):
        """Recursively substitute symbols with values in symbols map.

        Symbols map is a dictionary of symbol-expression pairs.
        """
        if self.op is Op.SYMBOL:
            value = symbols_map.get(self)
            if value is None:
                return self
            m = re.match(r'\A(@__f2py_PARENTHESIS_(\w+)_\d+@)\Z', self.data)
            if m:
                # complement to fromstring method
                items, paren = m.groups()
                if paren in ['ROUNDDIV', 'SQUARE']:
                    return as_array(value)
                assert paren == 'ROUND', (paren, value)
            return value
        if self.op in (Op.INTEGER, Op.REAL, Op.STRING):
            return self
        if self.op in (Op.ARRAY, Op.COMPLEX):
            return Expr(self.op, tuple(item.substitute(symbols_map)
                                       for item in self.data))
        if self.op is Op.CONCAT:
            return normalize(Expr(self.op, tuple(item.substitute(symbols_map)
                                                 for item in self.data)))
        if self.op is Op.TERMS:
            r = None
            for term, coeff in self.data.items():
                if r is None:
                    r = term.substitute(symbols_map) * coeff
                else:
                    r += term.substitute(symbols_map) * coeff
            if r is None:
                ewarn('substitute: empty TERMS expression interpreted as'
                      ' int-literal 0')
                return as_number(0)
            return r
        if self.op is Op.FACTORS:
            r = None
            for base, exponent in self.data.items():
                if r is None:
                    r = base.substitute(symbols_map) ** exponent
                else:
                    r *= base.substitute(symbols_map) ** exponent
            if r is None:
                ewarn('substitute: empty FACTORS expression interpreted'
                      ' as int-literal 1')
                return as_number(1)
            return r
        if self.op is Op.APPLY:
            target, args, kwargs = self.data
            if isinstance(target, Expr):
                target = target.substitute(symbols_map)
            args = tuple(a.substitute(symbols_map) for a in args)
            kwargs = {k: v.substitute(symbols_map)
                          for k, v in kwargs.items()}
            return normalize(Expr(self.op, (target, args, kwargs)))
        if self.op is Op.INDEXING:
            func = self.data[0]
            if isinstance(func, Expr):
                func = func.substitute(symbols_map)
            args = tuple(a.substitute(symbols_map) for a in self.data[1:])
            return normalize(Expr(self.op, (func,) + args))
        if self.op is Op.TERNARY:
            operands = tuple(a.substitute(symbols_map) for a in self.data)
            return normalize(Expr(self.op, operands))
        if self.op in (Op.REF, Op.DEREF):
            return normalize(Expr(self.op, self.data.substitute(symbols_map)))
        if self.op is Op.RELATIONAL:
            rop, left, right = self.data
            left = left.substitute(symbols_map)
            right = right.substitute(symbols_map)
            return normalize(Expr(self.op, (rop, left, right)))
        raise NotImplementedError(f'substitute method for {self.op}: {self!r}')

    def traverse(self, visit, *args, **kwargs):
        """Traverse expression tree with visit function.

        The visit function is applied to an expression with given args
        and kwargs.

        Traverse call returns an expression returned by visit when not
        None, otherwise return a new normalized expression with
        traverse-visit sub-expressions.
        """
        result = visit(self, *args, **kwargs)
        if result is not None:
            return result

        if self.op in (Op.INTEGER, Op.REAL, Op.STRING, Op.SYMBOL):
            return self
        elif self.op in (Op.COMPLEX, Op.ARRAY, Op.CONCAT, Op.TERNARY):
            return normalize(Expr(self.op, tuple(
                item.traverse(visit, *args, **kwargs)
                for item in self.data)))
        elif self.op in (Op.TERMS, Op.FACTORS):
            data = {}
            for k, v in self.data.items():
                k = k.traverse(visit, *args, **kwargs)
                v = (v.traverse(visit, *args, **kwargs)
                     if isinstance(v, Expr) else v)
                if k in data:
                    v = data[k] + v
                data[k] = v
            return normalize(Expr(self.op, data))
        elif self.op is Op.APPLY:
            obj = self.data[0]
            func = (obj.traverse(visit, *args, **kwargs)
                    if isinstance(obj, Expr) else obj)
            operands = tuple(operand.traverse(visit, *args, **kwargs)
                             for operand in self.data[1])
            kwoperands = {k: v.traverse(visit, *args, **kwargs)
                              for k, v in self.data[2].items()}
            return normalize(Expr(self.op, (func, operands, kwoperands)))
        elif self.op is Op.INDEXING:
            obj = self.data[0]
            obj = (obj.traverse(visit, *args, **kwargs)
                   if isinstance(obj, Expr) else obj)
            indices = tuple(index.traverse(visit, *args, **kwargs)
                            for index in self.data[1:])
            return normalize(Expr(self.op, (obj,) + indices))
        elif self.op in (Op.REF, Op.DEREF):
            return normalize(Expr(self.op,
                                  self.data.traverse(visit, *args, **kwargs)))
        elif self.op is Op.RELATIONAL:
            rop, left, right = self.data
            left = left.traverse(visit, *args, **kwargs)
            right = right.traverse(visit, *args, **kwargs)
            return normalize(Expr(self.op, (rop, left, right)))
        raise NotImplementedError(f'traverse method for {self.op}')

    def contains(self, other):
        """Check if self contains other.
        """
        found = []

        def visit(expr, found=found):
            if found:
                return expr
            elif expr == other:
                found.append(1)
                return expr

        self.traverse(visit)

        return len(found) != 0

    def symbols(self):
        """Return a set of symbols contained in self.
        """
        found = set()

        def visit(expr, found=found):
            if expr.op is Op.SYMBOL:
                found.add(expr)

        self.traverse(visit)

        return found

    def polynomial_atoms(self):
        """Return a set of expressions used as atoms in polynomial self.
        """
        found = set()

        def visit(expr, found=found):
            if expr.op is Op.FACTORS:
                for b in expr.data:
                    b.traverse(visit)
                return expr
            if expr.op in (Op.TERMS, Op.COMPLEX):
                return
            if expr.op is Op.APPLY and isinstance(expr.data[0], ArithOp):
                if expr.data[0] is ArithOp.POW:
                    expr.data[1][0].traverse(visit)
                    return expr
                return
            if expr.op in (Op.INTEGER, Op.REAL):
                return expr

            found.add(expr)

            if expr.op in (Op.INDEXING, Op.APPLY):
                return expr

        self.traverse(visit)

        return found

    def linear_solve(self, symbol):
        """Return a, b such that a * symbol + b == self.

        If self is not linear with respect to symbol, raise RuntimeError.
        """
        b = self.substitute({symbol: as_number(0)})
        ax = self - b
        a = ax.substitute({symbol: as_number(1)})

        zero, _ = as_numer_denom(a * symbol - ax)

        if zero != as_number(0):
            raise RuntimeError(f'not a {symbol}-linear equation:'
                               f' {a} * {symbol} + {b} == {self}')
        return a, b


def normalize(obj):
    """Normalize Expr and apply basic evaluation methods.
    """
    if not isinstance(obj, Expr):
        return obj

    if obj.op is Op.TERMS:
        d = {}
        for t, c in obj.data.items():
            if c == 0:
                continue
            if t.op is Op.COMPLEX and c != 1:
                t = t * c
                c = 1
            if t.op is Op.TERMS:
                for t1, c1 in t.data.items():
                    _pairs_add(d, t1, c1 * c)
            else:
                _pairs_add(d, t, c)
        if len(d) == 0:
            # TODO: determine correct kind
            return as_number(0)
        elif len(d) == 1:
            (t, c), = d.items()
            if c == 1:
                return t
        return Expr(Op.TERMS, d)

    if obj.op is Op.FACTORS:
        coeff = 1
        d = {}
        for b, e in obj.data.items():
            if e == 0:
                continue
            if b.op is Op.TERMS and isinstance(e, integer_types) and e > 1:
                # expand integer powers of sums
                b = b * (b ** (e - 1))
                e = 1

            if b.op in (Op.INTEGER, Op.REAL):
                if e == 1:
                    coeff *= b.data[0]
                elif e > 0:
                    coeff *= b.data[0] ** e
                else:
                    _pairs_add(d, b, e)
            elif b.op is Op.FACTORS:
                if e > 0 and isinstance(e, integer_types):
                    for b1, e1 in b.data.items():
                        _pairs_add(d, b1, e1 * e)
                else:
                    _pairs_add(d, b, e)
            else:
                _pairs_add(d, b, e)
        if len(d) == 0 or coeff == 0:
            # TODO: determine correct kind
            assert isinstance(coeff, number_types)
            return as_number(coeff)
        elif len(d) == 1:
            (b, e), = d.items()
            if e == 1:
                t = b
            else:
                t = Expr(Op.FACTORS, d)
            if coeff == 1:
                return t
            return Expr(Op.TERMS, {t: coeff})
        elif coeff == 1:
            return Expr(Op.FACTORS, d)
        else:
            return Expr(Op.TERMS, {Expr(Op.FACTORS, d): coeff})

    if obj.op is Op.APPLY and obj.data[0] is ArithOp.DIV:
        dividend, divisor = obj.data[1]
        t1, c1 = as_term_coeff(dividend)
        t2, c2 = as_term_coeff(divisor)
        if isinstance(c1, integer_types) and isinstance(c2, integer_types):
            g = gcd(c1, c2)
            c1, c2 = c1 // g, c2 // g
        else:
            c1, c2 = c1 / c2, 1

        if t1.op is Op.APPLY and t1.data[0] is ArithOp.DIV:
            numer = t1.data[1][0] * c1
            denom = t1.data[1][1] * t2 * c2
            return as_apply(ArithOp.DIV, numer, denom)

        if t2.op is Op.APPLY and t2.data[0] is ArithOp.DIV:
            numer = t2.data[1][1] * t1 * c1
            denom = t2.data[1][0] * c2
            return as_apply(ArithOp.DIV, numer, denom)

        d = dict(as_factors(t1).data)
        for b, e in as_factors(t2).data.items():
            _pairs_add(d, b, -e)
        numer, denom = {}, {}
        for b, e in d.items():
            if e > 0:
                numer[b] = e
            else:
                denom[b] = -e
        numer = normalize(Expr(Op.FACTORS, numer)) * c1
        denom = normalize(Expr(Op.FACTORS, denom)) * c2

        if denom.op in (Op.INTEGER, Op.REAL) and denom.data[0] == 1:
            # TODO: denom kind not used
            return numer
        return as_apply(ArithOp.DIV, numer, denom)

    if obj.op is Op.CONCAT:
        lst = [obj.data[0]]
        for s in obj.data[1:]:
            last = lst[-1]
            if (
                    last.op is Op.STRING
                    and s.op is Op.STRING
                    and last.data[0][0] in '"\''
                    and s.data[0][0] == last.data[0][-1]
            ):
                new_last = as_string(last.data[0][:-1] + s.data[0][1:],
                                     max(last.data[1], s.data[1]))
                lst[-1] = new_last
            else:
                lst.append(s)
        if len(lst) == 1:
            return lst[0]
        return Expr(Op.CONCAT, tuple(lst))

    if obj.op is Op.TERNARY:
        cond, expr1, expr2 = map(normalize, obj.data)
        if cond.op is Op.INTEGER:
            return expr1 if cond.data[0] else expr2
        return Expr(Op.TERNARY, (cond, expr1, expr2))

    return obj


def as_expr(obj):
    """Convert non-Expr objects to Expr objects.
    """
    if isinstance(obj, complex):
        return as_complex(obj.real, obj.imag)
    if isinstance(obj, number_types):
        return as_number(obj)
    if isinstance(obj, str):
        # STRING expression holds string with boundary quotes, hence
        # applying repr:
        return as_string(repr(obj))
    if isinstance(obj, tuple):
        return tuple(map(as_expr, obj))
    return obj


def as_symbol(obj):
    """Return object as SYMBOL expression (variable or unparsed expression).
    """
    return Expr(Op.SYMBOL, obj)


def as_number(obj, kind=4):
    """Return object as INTEGER or REAL constant.
    """
    if isinstance(obj, int):
        return Expr(Op.INTEGER, (obj, kind))
    if isinstance(obj, float):
        return Expr(Op.REAL, (obj, kind))
    if isinstance(obj, Expr):
        if obj.op in (Op.INTEGER, Op.REAL):
            return obj
    raise OpError(f'cannot convert {obj} to INTEGER or REAL constant')


def as_integer(obj, kind=4):
    """Return object as INTEGER constant.
    """
    if isinstance(obj, int):
        return Expr(Op.INTEGER, (obj, kind))
    if isinstance(obj, Expr):
        if obj.op is Op.INTEGER:
            return obj
    raise OpError(f'cannot convert {obj} to INTEGER constant')


def as_real(obj, kind=4):
    """Return object as REAL constant.
    """
    if isinstance(obj, int):
        return Expr(Op.REAL, (float(obj), kind))
    if isinstance(obj, float):
        return Expr(Op.REAL, (obj, kind))
    if isinstance(obj, Expr):
        if obj.op is Op.REAL:
            return obj
        elif obj.op is Op.INTEGER:
            return Expr(Op.REAL, (float(obj.data[0]), kind))
    raise OpError(f'cannot convert {obj} to REAL constant')


def as_string(obj, kind=1):
    """Return object as STRING expression (string literal constant).
    """
    return Expr(Op.STRING, (obj, kind))


def as_array(obj):
    """Return object as ARRAY expression (array constant).
    """
    if isinstance(obj, Expr):
        obj = obj,
    return Expr(Op.ARRAY, obj)


def as_complex(real, imag=0):
    """Return object as COMPLEX expression (complex literal constant).
    """
    return Expr(Op.COMPLEX, (as_expr(real), as_expr(imag)))


def as_apply(func, *args, **kwargs):
    """Return object as APPLY expression (function call, constructor, etc.)
    """
    return Expr(Op.APPLY,
                (func, tuple(map(as_expr, args)),
                 {k: as_expr(v) for k, v in kwargs.items()}))


def as_ternary(cond, expr1, expr2):
    """Return object as TERNARY expression (cond?expr1:expr2).
    """
    return Expr(Op.TERNARY, (cond, expr1, expr2))


def as_ref(expr):
    """Return object as referencing expression.
    """
    return Expr(Op.REF, expr)


def as_deref(expr):
    """Return object as dereferencing expression.
    """
    return Expr(Op.DEREF, expr)


def as_eq(left, right):
    return Expr(Op.RELATIONAL, (RelOp.EQ, left, right))


def as_ne(left, right):
    return Expr(Op.RELATIONAL, (RelOp.NE, left, right))


def as_lt(left, right):
    return Expr(Op.RELATIONAL, (RelOp.LT, left, right))


def as_le(left, right):
    return Expr(Op.RELATIONAL, (RelOp.LE, left, right))


def as_gt(left, right):
    return Expr(Op.RELATIONAL, (RelOp.GT, left, right))


def as_ge(left, right):
    return Expr(Op.RELATIONAL, (RelOp.GE, left, right))


def as_terms(obj):
    """Return expression as TERMS expression.
    """
    if isinstance(obj, Expr):
        obj = normalize(obj)
        if obj.op is Op.TERMS:
            return obj
        if obj.op is Op.INTEGER:
            return Expr(Op.TERMS, {as_integer(1, obj.data[1]): obj.data[0]})
        if obj.op is Op.REAL:
            return Expr(Op.TERMS, {as_real(1, obj.data[1]): obj.data[0]})
        return Expr(Op.TERMS, {obj: 1})
    raise OpError(f'cannot convert {type(obj)} to terms Expr')


def as_factors(obj):
    """Return expression as FACTORS expression.
    """
    if isinstance(obj, Expr):
        obj = normalize(obj)
        if obj.op is Op.FACTORS:
            return obj
        if obj.op is Op.TERMS:
            if len(obj.data) == 1:
                (term, coeff), = obj.data.items()
                if coeff == 1:
                    return Expr(Op.FACTORS, {term: 1})
                return Expr(Op.FACTORS, {term: 1, Expr.number(coeff): 1})
        if (obj.op is Op.APPLY
             and obj.data[0] is ArithOp.DIV
             and not obj.data[2]):
            return Expr(Op.FACTORS, {obj.data[1][0]: 1, obj.data[1][1]: -1})
        return Expr(Op.FACTORS, {obj: 1})
    raise OpError(f'cannot convert {type(obj)} to terms Expr')


def as_term_coeff(obj):
    """Return expression as term-coefficient pair.
    """
    if isinstance(obj, Expr):
        obj = normalize(obj)
        if obj.op is Op.INTEGER:
            return as_integer(1, obj.data[1]), obj.data[0]
        if obj.op is Op.REAL:
            return as_real(1, obj.data[1]), obj.data[0]
        if obj.op is Op.TERMS:
            if len(obj.data) == 1:
                (term, coeff), = obj.data.items()
                return term, coeff
            # TODO: find common divisor of coefficients
        if obj.op is Op.APPLY and obj.data[0] is ArithOp.DIV:
            t, c = as_term_coeff(obj.data[1][0])
            return as_apply(ArithOp.DIV, t, obj.data[1][1]), c
        return obj, 1
    raise OpError(f'cannot convert {type(obj)} to term and coeff')


def as_numer_denom(obj):
    """Return expression as numer-denom pair.
    """
    if isinstance(obj, Expr):
        obj = normalize(obj)
        if obj.op in (Op.INTEGER, Op.REAL, Op.COMPLEX, Op.SYMBOL,
                      Op.INDEXING, Op.TERNARY):
            return obj, as_number(1)
        elif obj.op is Op.APPLY:
            if obj.data[0] is ArithOp.DIV and not obj.data[2]:
                numers, denoms = map(as_numer_denom, obj.data[1])
                return numers[0] * denoms[1], numers[1] * denoms[0]
            return obj, as_number(1)
        elif obj.op is Op.TERMS:
            numers, denoms = [], []
            for term, coeff in obj.data.items():
                n, d = as_numer_denom(term)
                n = n * coeff
                numers.append(n)
                denoms.append(d)
            numer, denom = as_number(0), as_number(1)
            for i in range(len(numers)):
                n = numers[i]
                for j in range(len(numers)):
                    if i != j:
                        n *= denoms[j]
                numer += n
                denom *= denoms[i]
            if denom.op in (Op.INTEGER, Op.REAL) and denom.data[0] < 0:
                numer, denom = -numer, -denom
            return numer, denom
        elif obj.op is Op.FACTORS:
            numer, denom = as_number(1), as_number(1)
            for b, e in obj.data.items():
                bnumer, bdenom = as_numer_denom(b)
                if e > 0:
                    numer *= bnumer ** e
                    denom *= bdenom ** e
                elif e < 0:
                    numer *= bdenom ** (-e)
                    denom *= bnumer ** (-e)
            return numer, denom
    raise OpError(f'cannot convert {type(obj)} to numer and denom')


def _counter():
    # Used internally to generate unique dummy symbols
    counter = 0
    while True:
        counter += 1
        yield counter


COUNTER = _counter()


def eliminate_quotes(s):
    """Replace quoted substrings of input string.

    Return a new string and a mapping of replacements.
    """
    d = {}

    def repl(m):
        kind, value = m.groups()[:2]
        if kind:
            # remove trailing underscore
            kind = kind[:-1]
        p = {"'": "SINGLE", '"': "DOUBLE"}[value[0]]
        k = f'{kind}@__f2py_QUOTES_{p}_{COUNTER.__next__()}@'
        d[k] = value
        return k

    new_s = re.sub(r'({kind}_|)({single_quoted}|{double_quoted})'.format(
        kind=r'\w[\w\d_]*',
        single_quoted=r"('([^'\\]|(\\.))*')",
        double_quoted=r'("([^"\\]|(\\.))*")'),
        repl, s)

    assert '"' not in new_s
    assert "'" not in new_s

    return new_s, d


def insert_quotes(s, d):
    """Inverse of eliminate_quotes.
    """
    for k, v in d.items():
        kind = k[:k.find('@')]
        if kind:
            kind += '_'
        s = s.replace(k, kind + v)
    return s


def replace_parenthesis(s):
    """Replace substrings of input that are enclosed in parenthesis.

    Return a new string and a mapping of replacements.
    """
    # Find a parenthesis pair that appears first.

    # Fortran deliminator are `(`, `)`, `[`, `]`, `(/', '/)`, `/`.
    # We don't handle `/` deliminator because it is not a part of an
    # expression.
    left, right = None, None
    mn_i = len(s)
    for left_, right_ in (('(/', '/)'),
                          '()',
                          '{}',  # to support C literal structs
                          '[]'):
        i = s.find(left_)
        if i == -1:
            continue
        if i < mn_i:
            mn_i = i
            left, right = left_, right_

    if left is None:
        return s, {}

    i = mn_i
    j = s.find(right, i)

    while s.count(left, i + 1, j) != s.count(right, i + 1, j):
        j = s.find(right, j + 1)
        if j == -1:
            raise ValueError(f'Mismatch of {left + right} parenthesis in {s!r}')

    p = {'(': 'ROUND', '[': 'SQUARE', '{': 'CURLY', '(/': 'ROUNDDIV'}[left]

    k = f'@__f2py_PARENTHESIS_{p}_{COUNTER.__next__()}@'
    v = s[i + len(left):j]
    r, d = replace_parenthesis(s[j + len(right):])
    d[k] = v
    return s[:i] + k + r, d


def _get_parenthesis_kind(s):
    assert s.startswith('@__f2py_PARENTHESIS_'), s
    return s.split('_')[4]


def unreplace_parenthesis(s, d):
    """Inverse of replace_parenthesis.
    """
    for k, v in d.items():
        p = _get_parenthesis_kind(k)
        left = {'ROUND': '(', 'SQUARE': '[', 'CURLY': '{', 'ROUNDDIV': '(/'}[p]
        right = {'ROUND': ')', 'SQUARE': ']', 'CURLY': '}', 'ROUNDDIV': '/)'}[p]
        s = s.replace(k, left + v + right)
    return s


def fromstring(s, language=Language.C):
    """Create an expression from a string.

    This is a "lazy" parser, that is, only arithmetic operations are
    resolved, non-arithmetic operations are treated as symbols.
    """
    r = _FromStringWorker(language=language).parse(s)
    if isinstance(r, Expr):
        return r
    raise ValueError(f'failed to parse `{s}` to Expr instance: got `{r}`')


class _Pair:
    # Internal class to represent a pair of expressions

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def substitute(self, symbols_map):
        left, right = self.left, self.right
        if isinstance(left, Expr):
            left = left.substitute(symbols_map)
        if isinstance(right, Expr):
            right = right.substitute(symbols_map)
        return _Pair(left, right)

    def __repr__(self):
        return f'{type(self).__name__}({self.left}, {self.right})'


class _FromStringWorker:

    def __init__(self, language=Language.C):
        self.original = None
        self.quotes_map = None
        self.language = language

    def finalize_string(self, s):
        return insert_quotes(s, self.quotes_map)

    def parse(self, inp):
        self.original = inp
        unquoted, self.quotes_map = eliminate_quotes(inp)
        return self.process(unquoted)

    def process(self, s, context='expr'):
        """Parse string within the given context.

        The context may define the result in case of ambiguous
        expressions. For instance, consider expressions `f(x, y)` and
        `(x, y) + (a, b)` where `f` is a function and pair `(x, y)`
        denotes complex number. Specifying context as "args" or
        "expr", the subexpression `(x, y)` will be parse to an
        argument list or to a complex number, respectively.
        """
        if isinstance(s, (list, tuple)):
            return type(s)(self.process(s_, context) for s_ in s)

        assert isinstance(s, str), (type(s), s)

        # replace subexpressions in parenthesis with f2py @-names
        r, raw_symbols_map = replace_parenthesis(s)
        r = r.strip()

        def restore(r):
            # restores subexpressions marked with f2py @-names
            if isinstance(r, (list, tuple)):
                return type(r)(map(restore, r))
            return unreplace_parenthesis(r, raw_symbols_map)

        # comma-separated tuple
        if ',' in r:
            operands = restore(r.split(','))
            if context == 'args':
                return tuple(self.process(operands))
            if context == 'expr':
                if len(operands) == 2:
                    # complex number literal
                    return as_complex(*self.process(operands))
            raise NotImplementedError(
                f'parsing comma-separated list (context={context}): {r}')

        # ternary operation
        m = re.match(r'\A([^?]+)[?]([^:]+)[:](.+)\Z', r)
        if m:
            assert context == 'expr', context
            oper, expr1, expr2 = restore(m.groups())
            oper = self.process(oper)
            expr1 = self.process(expr1)
            expr2 = self.process(expr2)
            return as_ternary(oper, expr1, expr2)

        # relational expression
        if self.language is Language.Fortran:
            m = re.match(
                r'\A(.+)\s*[.](eq|ne|lt|le|gt|ge)[.]\s*(.+)\Z', r, re.I)
        else:
            m = re.match(
                r'\A(.+)\s*([=][=]|[!][=]|[<][=]|[<]|[>][=]|[>])\s*(.+)\Z', r)
        if m:
            left, rop, right = m.groups()
            if self.language is Language.Fortran:
                rop = '.' + rop + '.'
            left, right = self.process(restore((left, right)))
            rop = RelOp.fromstring(rop, language=self.language)
            return Expr(Op.RELATIONAL, (rop, left, right))

        # keyword argument
        m = re.match(r'\A(\w[\w\d_]*)\s*[=](.*)\Z', r)
        if m:
            keyname, value = m.groups()
            value = restore(value)
            return _Pair(keyname, self.process(value))

        # addition/subtraction operations
        operands = re.split(r'((?<!\d[edED])[+-])', r)
        if len(operands) > 1:
            result = self.process(restore(operands[0] or '0'))
            for op, operand in zip(operands[1::2], operands[2::2]):
                operand = self.process(restore(operand))
                op = op.strip()
                if op == '+':
                    result += operand
                else:
                    assert op == '-'
                    result -= operand
            return result

        # string concatenate operation
        if self.language is Language.Fortran and '//' in r:
            operands = restore(r.split('//'))
            return Expr(Op.CONCAT,
                        tuple(self.process(operands)))

        # multiplication/division operations
        operands = re.split(r'(?<=[@\w\d_])\s*([*]|/)',
                            (r if self.language is Language.C
                             else r.replace('**', '@__f2py_DOUBLE_STAR@')))
        if len(operands) > 1:
            operands = restore(operands)
            if self.language is not Language.C:
                operands = [operand.replace('@__f2py_DOUBLE_STAR@', '**')
                            for operand in operands]
            # Expression is an arithmetic product
            result = self.process(operands[0])
            for op, operand in zip(operands[1::2], operands[2::2]):
                operand = self.process(operand)
                op = op.strip()
                if op == '*':
                    result *= operand
                else:
                    assert op == '/'
                    result /= operand
            return result

        # referencing/dereferencing
        if r.startswith(('*', '&')):
            op = {'*': Op.DEREF, '&': Op.REF}[r[0]]
            operand = self.process(restore(r[1:]))
            return Expr(op, operand)

        # exponentiation operations
        if self.language is not Language.C and '**' in r:
            operands = list(reversed(restore(r.split('**'))))
            result = self.process(operands[0])
            for operand in operands[1:]:
                operand = self.process(operand)
                result = operand ** result
            return result

        # int-literal-constant
        m = re.match(r'\A({digit_string})({kind}|)\Z'.format(
            digit_string=r'\d+',
            kind=r'_(\d+|\w[\w\d_]*)'), r)
        if m:
            value, _, kind = m.groups()
            if kind and kind.isdigit():
                kind = int(kind)
            return as_integer(int(value), kind or 4)

        # real-literal-constant
        m = re.match(r'\A({significant}({exponent}|)|\d+{exponent})({kind}|)\Z'
                     .format(
                         significant=r'[.]\d+|\d+[.]\d*',
                         exponent=r'[edED][+-]?\d+',
                         kind=r'_(\d+|\w[\w\d_]*)'), r)
        if m:
            value, _, _, kind = m.groups()
            if kind and kind.isdigit():
                kind = int(kind)
            value = value.lower()
            if 'd' in value:
                return as_real(float(value.replace('d', 'e')), kind or 8)
            return as_real(float(value), kind or 4)

        # string-literal-constant with kind parameter specification
        if r in self.quotes_map:
            kind = r[:r.find('@')]
            return as_string(self.quotes_map[r], kind or 1)

        # array constructor or literal complex constant or
        # parenthesized expression
        if r in raw_symbols_map:
            paren = _get_parenthesis_kind(r)
            items = self.process(restore(raw_symbols_map[r]),
                                 'expr' if paren == 'ROUND' else 'args')
            if paren == 'ROUND':
                if isinstance(items, Expr):
                    return items
            if paren in ['ROUNDDIV', 'SQUARE']:
                # Expression is a array constructor
                if isinstance(items, Expr):
                    items = (items,)
                return as_array(items)

        # function call/indexing
        m = re.match(r'\A(.+)\s*(@__f2py_PARENTHESIS_(ROUND|SQUARE)_\d+@)\Z',
                     r)
        if m:
            target, args, paren = m.groups()
            target = self.process(restore(target))
            args = self.process(restore(args)[1:-1], 'args')
            if not isinstance(args, tuple):
                args = args,
            if paren == 'ROUND':
                kwargs = {a.left: a.right for a in args
                              if isinstance(a, _Pair)}
                args = tuple(a for a in args if not isinstance(a, _Pair))
                # Warning: this could also be Fortran indexing operation..
                return as_apply(target, *args, **kwargs)
            else:
                # Expression is a C/Python indexing operation
                # (e.g. used in .pyf files)
                assert paren == 'SQUARE'
                return target[args]

        # Fortran standard conforming identifier
        m = re.match(r'\A\w[\w\d_]*\Z', r)
        if m:
            return as_symbol(r)

        # fall-back to symbol
        r = self.finalize_string(restore(r))
        ewarn(
            f'fromstring: treating {r!r} as symbol (original={self.original})')
        return as_symbol(r)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\debug.py ===
#!~/.wine/drive_c/Python25/python.exe
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Debugging.

@group Debugging:
    Debug

@group Warnings:
    MixedBitsWarning
"""

__revision__ = "$Id$"

__all__ = ["Debug", "MixedBitsWarning"]

import sys
from winappdbg import win32
from winappdbg.system import System
from winappdbg.process import Process
from winappdbg.thread import Thread
from winappdbg.module import Module
from winappdbg.window import Window
from winappdbg.breakpoint import _BreakpointContainer, CodeBreakpoint
from winappdbg.event import Event, EventHandler, EventDispatcher, EventFactory
from winappdbg.interactive import ConsoleDebugger

import warnings
##import traceback

# ==============================================================================


# If you set this warning to be considered as an error, you can stop the
# debugger from attaching to 64-bit processes from a 32-bit Python VM and
# visceversa.
class MixedBitsWarning(RuntimeWarning):
    """
    This warning is issued when mixing 32 and 64 bit processes.
    """


# ==============================================================================

# TODO
# * Add memory read and write operations, similar to those in the Process
#   class, but hiding the presence of the code breakpoints.
# * Add a method to get the memory map of a process, but hiding the presence
#   of the page breakpoints.
# * Maybe the previous two features should be implemented at the Process class
#   instead, but how to communicate with the Debug object without creating
#   circular references? Perhaps the "overrides" could be set using private
#   members (so users won't see them), but then there's the problem of the
#   users being able to access the snapshot (i.e. clear it), which is why it's
#   not such a great idea to use the snapshot to store data that really belongs
#   to the Debug class.


class Debug(EventDispatcher, _BreakpointContainer):
    """
    The main debugger class.

    @group Debugging:
        interactive, attach, detach, detach_from_all, execv, execl,
        kill, kill_all,
        get_debugee_count, get_debugee_pids,
        is_debugee, is_debugee_attached, is_debugee_started,
        in_hostile_mode,
        add_existing_session

    @group Debugging loop:
        loop, stop, next, wait, dispatch, cont

    @undocumented: force_garbage_collection

    @type system: L{System}
    @ivar system: A System snapshot that is automatically updated for
        processes being debugged. Processes not being debugged in this snapshot
        may be outdated.
    """

    # Automatically set to True the first time a Debug object is instanced.
    _debug_static_init = False

    def __init__(self, eventHandler=None, bKillOnExit=False, bHostileCode=False):
        """
        Debugger object.

        @type  eventHandler: L{EventHandler}
        @param eventHandler:
            (Optional, recommended) Custom event handler object.

        @type  bKillOnExit: bool
        @param bKillOnExit: (Optional) Kill on exit mode.
            If C{True} debugged processes are killed when the debugger is
            stopped. If C{False} when the debugger stops it detaches from all
            debugged processes and leaves them running (default).

        @type  bHostileCode: bool
        @param bHostileCode: (Optional) Hostile code mode.
            Set to C{True} to take some basic precautions against anti-debug
            tricks. Disabled by default.

        @warn: When hostile mode is enabled, some things may not work as
            expected! This is because the anti-anti debug tricks may disrupt
            the behavior of the Win32 debugging APIs or WinAppDbg itself.

        @note: The L{eventHandler} parameter may be any callable Python object
            (for example a function, or an instance method).
            However you'll probably find it more convenient to use an instance
            of a subclass of L{EventHandler} here.

        @raise WindowsError: Raises an exception on error.
        """
        EventDispatcher.__init__(self, eventHandler)
        _BreakpointContainer.__init__(self)

        self.system = System()
        self.lastEvent = None
        self.__firstDebugee = True
        self.__bKillOnExit = bKillOnExit
        self.__bHostileCode = bHostileCode
        self.__breakOnEP = set()  # set of pids
        self.__attachedDebugees = set()  # set of pids
        self.__startedDebugees = set()  # set of pids

        if not self._debug_static_init:
            self._debug_static_init = True

            # Request debug privileges for the current process.
            # Only do this once, and only after instancing a Debug object,
            # so passive debuggers don't get detected because of this.
            self.system.request_debug_privileges(bIgnoreExceptions=False)

            # Try to fix the symbol store path if it wasn't set.
            # But don't enable symbol downloading by default, since it may
            # degrade performance severely.
            self.system.fix_symbol_store_path(remote=False, force=False)

    ##    # It's hard not to create circular references,
    ##    # and if we have a destructor, we can end up leaking everything.
    ##    # It's best to code the debugging loop properly to always
    ##    # stop the debugger before going out of scope.
    ##    def __del__(self):
    ##        self.stop()

    def __enter__(self):
        """
        Compatibility with the "C{with}" Python statement.
        """
        return self

    def __exit__(self, type, value, traceback):
        """
        Compatibility with the "C{with}" Python statement.
        """
        self.stop()

    def __len__(self):
        """
        @rtype:  int
        @return: Number of processes being debugged.
        """
        return self.get_debugee_count()

    # TODO: maybe custom __bool__ to break out of loop() ?
    # it already does work (because of __len__) but it'd be
    # useful to do it from the event handler anyway

    # ------------------------------------------------------------------------------

    def __setSystemKillOnExitMode(self):
        # Make sure the default system behavior on detaching from processes
        # versus killing them matches our preferences. This only affects the
        # scenario where the Python VM dies unexpectedly without running all
        # the finally clauses, or the user failed to either instance the Debug
        # object inside a with block or call the stop() method before quitting.
        if self.__firstDebugee:
            try:
                System.set_kill_on_exit_mode(self.__bKillOnExit)
                self.__firstDebugee = False
            except Exception:
                pass

    def attach(self, dwProcessId):
        """
        Attaches to an existing process for debugging.

        @see: L{detach}, L{execv}, L{execl}

        @type  dwProcessId: int
        @param dwProcessId: Global ID of a process to attach to.

        @rtype:  L{Process}
        @return: A new Process object. Normally you don't need to use it now,
            it's best to interact with the process from the event handler.

        @raise WindowsError: Raises an exception on error.
            Depending on the circumstances, the debugger may or may not have
            attached to the target process.
        """

        # Get the Process object from the snapshot,
        # if missing create a new one.
        try:
            aProcess = self.system.get_process(dwProcessId)
        except KeyError:
            aProcess = Process(dwProcessId)

        # Warn when mixing 32 and 64 bits.
        # This also allows the user to stop attaching altogether,
        # depending on how the warnings are configured.
        if System.bits != aProcess.get_bits():
            msg = "Mixture of 32 and 64 bits is considered experimental." " Use at your own risk!"
            warnings.warn(msg, MixedBitsWarning)

        # Attach to the process.
        win32.DebugActiveProcess(dwProcessId)

        # Add the new PID to the set of debugees.
        self.__attachedDebugees.add(dwProcessId)

        # Match the system kill-on-exit flag to our own.
        self.__setSystemKillOnExitMode()

        # If the Process object was not in the snapshot, add it now.
        if not self.system.has_process(dwProcessId):
            self.system._add_process(aProcess)

        # Scan the process threads and loaded modules.
        # This is prefered because the thread and library events do not
        # properly give some information, like the filename for each module.
        aProcess.scan_threads()
        aProcess.scan_modules()

        # Return the Process object, like the execv() and execl() methods.
        return aProcess

    def execv(self, argv, **kwargs):
        """
        Starts a new process for debugging.

        This method uses a list of arguments. To use a command line string
        instead, use L{execl}.

        @see: L{attach}, L{detach}

        @type  argv: list( str... )
        @param argv: List of command line arguments to pass to the debugee.
            The first element must be the debugee executable filename.

        @type    bBreakOnEntryPoint: bool
        @keyword bBreakOnEntryPoint: C{True} to automatically set a breakpoint
            at the program entry point.

        @type    bConsole: bool
        @keyword bConsole: True to inherit the console of the debugger.
            Defaults to C{False}.

        @type    bFollow: bool
        @keyword bFollow: C{True} to automatically attach to child processes.
            Defaults to C{False}.

        @type    bInheritHandles: bool
        @keyword bInheritHandles: C{True} if the new process should inherit
            it's parent process' handles. Defaults to C{False}.

        @type    bSuspended: bool
        @keyword bSuspended: C{True} to suspend the main thread before any code
            is executed in the debugee. Defaults to C{False}.

        @keyword dwParentProcessId: C{None} or C{0} if the debugger process
            should be the parent process (default), or a process ID to
            forcefully set as the debugee's parent (only available for Windows
            Vista and above).

            In hostile mode, the default is not the debugger process but the
            process ID for "explorer.exe".

        @type    iTrustLevel: int or None
        @keyword iTrustLevel: Trust level.
            Must be one of the following values:
             - 0: B{No trust}. May not access certain resources, such as
                  cryptographic keys and credentials. Only available since
                  Windows XP and 2003, desktop editions. This is the default
                  in hostile mode.
             - 1: B{Normal trust}. Run with the same privileges as a normal
                  user, that is, one that doesn't have the I{Administrator} or
                  I{Power User} user rights. Only available since Windows XP
                  and 2003, desktop editions.
             - 2: B{Full trust}. Run with the exact same privileges as the
                  current user. This is the default in normal mode.

        @type    bAllowElevation: bool
        @keyword bAllowElevation: C{True} to allow the child process to keep
            UAC elevation, if the debugger itself is running elevated. C{False}
            to ensure the child process doesn't run with elevation. Defaults to
            C{True}.

            This flag is only meaningful on Windows Vista and above, and if the
            debugger itself is running with elevation. It can be used to make
            sure the child processes don't run elevated as well.

            This flag DOES NOT force an elevation prompt when the debugger is
            not running with elevation.

            Note that running the debugger with elevation (or the Python
            interpreter at all for that matter) is not normally required.
            You should only need to if the target program requires elevation
            to work properly (for example if you try to debug an installer).

        @rtype:  L{Process}
        @return: A new Process object. Normally you don't need to use it now,
            it's best to interact with the process from the event handler.

        @raise WindowsError: Raises an exception on error.
        """
        if type(argv) in (str, compat.unicode):
            raise TypeError("Debug.execv expects a list, not a string")
        lpCmdLine = self.system.argv_to_cmdline(argv)
        return self.execl(lpCmdLine, **kwargs)

    def execl(self, lpCmdLine, **kwargs):
        """
        Starts a new process for debugging.

        This method uses a command line string. To use a list of arguments
        instead, use L{execv}.

        @see: L{attach}, L{detach}

        @type  lpCmdLine: str
        @param lpCmdLine: Command line string to execute.
            The first token must be the debugee executable filename.
            Tokens with spaces must be enclosed in double quotes.
            Tokens including double quote characters must be escaped with a
            backslash.

        @type    bBreakOnEntryPoint: bool
        @keyword bBreakOnEntryPoint: C{True} to automatically set a breakpoint
            at the program entry point. Defaults to C{False}.

        @type    bConsole: bool
        @keyword bConsole: True to inherit the console of the debugger.
            Defaults to C{False}.

        @type    bFollow: bool
        @keyword bFollow: C{True} to automatically attach to child processes.
            Defaults to C{False}.

        @type    bInheritHandles: bool
        @keyword bInheritHandles: C{True} if the new process should inherit
            it's parent process' handles. Defaults to C{False}.

        @type    bSuspended: bool
        @keyword bSuspended: C{True} to suspend the main thread before any code
            is executed in the debugee. Defaults to C{False}.

        @type    dwParentProcessId: int or None
        @keyword dwParentProcessId: C{None} or C{0} if the debugger process
            should be the parent process (default), or a process ID to
            forcefully set as the debugee's parent (only available for Windows
            Vista and above).

            In hostile mode, the default is not the debugger process but the
            process ID for "explorer.exe".

        @type    iTrustLevel: int
        @keyword iTrustLevel: Trust level.
            Must be one of the following values:
             - 0: B{No trust}. May not access certain resources, such as
                  cryptographic keys and credentials. Only available since
                  Windows XP and 2003, desktop editions. This is the default
                  in hostile mode.
             - 1: B{Normal trust}. Run with the same privileges as a normal
                  user, that is, one that doesn't have the I{Administrator} or
                  I{Power User} user rights. Only available since Windows XP
                  and 2003, desktop editions.
             - 2: B{Full trust}. Run with the exact same privileges as the
                  current user. This is the default in normal mode.

        @type    bAllowElevation: bool
        @keyword bAllowElevation: C{True} to allow the child process to keep
            UAC elevation, if the debugger itself is running elevated. C{False}
            to ensure the child process doesn't run with elevation. Defaults to
            C{True} in normal mode and C{False} in hostile mode.

            This flag is only meaningful on Windows Vista and above, and if the
            debugger itself is running with elevation. It can be used to make
            sure the child processes don't run elevated as well.

            This flag DOES NOT force an elevation prompt when the debugger is
            not running with elevation.

            Note that running the debugger with elevation (or the Python
            interpreter at all for that matter) is not normally required.
            You should only need to if the target program requires elevation
            to work properly (for example if you try to debug an installer).

        @rtype:  L{Process}
        @return: A new Process object. Normally you don't need to use it now,
            it's best to interact with the process from the event handler.

        @raise WindowsError: Raises an exception on error.
        """
        if type(lpCmdLine) not in (str, compat.unicode):
            warnings.warn("Debug.execl expects a string")

        # Set the "debug" flag to True.
        kwargs["bDebug"] = True

        # Pop the "break on entry point" flag.
        bBreakOnEntryPoint = kwargs.pop("bBreakOnEntryPoint", False)

        # Set the default trust level if requested.
        if "iTrustLevel" not in kwargs:
            if self.__bHostileCode:
                kwargs["iTrustLevel"] = 0
            else:
                kwargs["iTrustLevel"] = 2

        # Set the default UAC elevation flag if requested.
        if "bAllowElevation" not in kwargs:
            kwargs["bAllowElevation"] = not self.__bHostileCode

        # In hostile mode the default parent process is explorer.exe.
        # Only supported for Windows Vista and above.
        if self.__bHostileCode and not kwargs.get("dwParentProcessId", None):
            try:
                vista_and_above = self.__vista_and_above
            except AttributeError:
                osi = win32.OSVERSIONINFOEXW()
                osi.dwMajorVersion = 6
                osi.dwMinorVersion = 0
                osi.dwPlatformId = win32.VER_PLATFORM_WIN32_NT
                mask = 0
                mask = win32.VerSetConditionMask(mask, win32.VER_MAJORVERSION, win32.VER_GREATER_EQUAL)
                mask = win32.VerSetConditionMask(mask, win32.VER_MAJORVERSION, win32.VER_GREATER_EQUAL)
                mask = win32.VerSetConditionMask(mask, win32.VER_PLATFORMID, win32.VER_EQUAL)
                vista_and_above = win32.VerifyVersionInfoW(
                    osi, win32.VER_MAJORVERSION | win32.VER_MINORVERSION | win32.VER_PLATFORMID, mask
                )
                self.__vista_and_above = vista_and_above
            if vista_and_above:
                dwParentProcessId = self.system.get_explorer_pid()
                if dwParentProcessId:
                    kwargs["dwParentProcessId"] = dwParentProcessId
                else:
                    msg = 'Failed to find "explorer.exe"!' " Using the debugger as parent process."
                    warnings.warn(msg, RuntimeWarning)

        # Start the new process.
        aProcess = None
        try:
            aProcess = self.system.start_process(lpCmdLine, **kwargs)
            dwProcessId = aProcess.get_pid()

            # Match the system kill-on-exit flag to our own.
            self.__setSystemKillOnExitMode()

            # Warn when mixing 32 and 64 bits.
            # This also allows the user to stop attaching altogether,
            # depending on how the warnings are configured.
            if System.bits != aProcess.get_bits():
                msg = "Mixture of 32 and 64 bits is considered experimental." " Use at your own risk!"
                warnings.warn(msg, MixedBitsWarning)

            # Add the new PID to the set of debugees.
            self.__startedDebugees.add(dwProcessId)

            # Add the new PID to the set of "break on EP" debugees if needed.
            if bBreakOnEntryPoint:
                self.__breakOnEP.add(dwProcessId)

            # Return the Process object.
            return aProcess

        # On error kill the new process and raise an exception.
        except:
            if aProcess is not None:
                try:
                    try:
                        self.__startedDebugees.remove(aProcess.get_pid())
                    except KeyError:
                        pass
                finally:
                    try:
                        try:
                            self.__breakOnEP.remove(aProcess.get_pid())
                        except KeyError:
                            pass
                    finally:
                        try:
                            aProcess.kill()
                        except Exception:
                            pass
            raise

    def add_existing_session(self, dwProcessId, bStarted=False):
        """
        Use this method only when for some reason the debugger's been attached
        to the target outside of WinAppDbg (for example when integrating with
        other tools).

        You don't normally need to call this method. Most users should call
        L{attach}, L{execv} or L{execl} instead.

        @type  dwProcessId: int
        @param dwProcessId: Global process ID.

        @type  bStarted: bool
        @param bStarted: C{True} if the process was started by the debugger,
            or C{False} if the process was attached to instead.

        @raise WindowsError: The target process does not exist, is not attached
            to the debugger anymore.
        """

        # Register the process object with the snapshot.
        if not self.system.has_process(dwProcessId):
            aProcess = Process(dwProcessId)
            self.system._add_process(aProcess)
        else:
            aProcess = self.system.get_process(dwProcessId)

        # Test for debug privileges on the target process.
        # Raises WindowsException on error.
        aProcess.get_handle()

        # Register the process ID with the debugger.
        if bStarted:
            self.__attachedDebugees.add(dwProcessId)
        else:
            self.__startedDebugees.add(dwProcessId)

        # Match the system kill-on-exit flag to our own.
        self.__setSystemKillOnExitMode()

        # Scan the process threads and loaded modules.
        # This is prefered because the thread and library events do not
        # properly give some information, like the filename for each module.
        aProcess.scan_threads()
        aProcess.scan_modules()

    def __cleanup_process(self, dwProcessId, bIgnoreExceptions=False):
        """
        Perform the necessary cleanup of a process about to be killed or
        detached from.

        This private method is called by L{kill} and L{detach}.

        @type  dwProcessId: int
        @param dwProcessId: Global ID of a process to kill.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when killing the process.

        @raise WindowsError: Raises an exception on error, unless
            C{bIgnoreExceptions} is C{True}.
        """
        # If the process is being debugged...
        if self.is_debugee(dwProcessId):
            # Make sure a Process object exists or the following calls fail.
            if not self.system.has_process(dwProcessId):
                aProcess = Process(dwProcessId)
                try:
                    aProcess.get_handle()
                except WindowsError:
                    pass  # fails later on with more specific reason
                self.system._add_process(aProcess)

            # Erase all breakpoints in the process.
            try:
                self.erase_process_breakpoints(dwProcessId)
            except Exception:
                if not bIgnoreExceptions:
                    raise
                e = sys.exc_info()[1]
                warnings.warn(str(e), RuntimeWarning)

            # Stop tracing all threads in the process.
            try:
                self.stop_tracing_process(dwProcessId)
            except Exception:
                if not bIgnoreExceptions:
                    raise
                e = sys.exc_info()[1]
                warnings.warn(str(e), RuntimeWarning)

            # The process is no longer a debugee.
            try:
                if dwProcessId in self.__attachedDebugees:
                    self.__attachedDebugees.remove(dwProcessId)
                if dwProcessId in self.__startedDebugees:
                    self.__startedDebugees.remove(dwProcessId)
            except Exception:
                if not bIgnoreExceptions:
                    raise
                e = sys.exc_info()[1]
                warnings.warn(str(e), RuntimeWarning)

        # Clear and remove the process from the snapshot.
        # If the user wants to do something with it after detaching
        # a new Process instance should be created.
        try:
            if self.system.has_process(dwProcessId):
                try:
                    self.system.get_process(dwProcessId).clear()
                finally:
                    self.system._del_process(dwProcessId)
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)

        # If the last debugging event is related to this process, forget it.
        try:
            if self.lastEvent and self.lastEvent.get_pid() == dwProcessId:
                self.lastEvent = None
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)

    def kill(self, dwProcessId, bIgnoreExceptions=False):
        """
        Kills a process currently being debugged.

        @see: L{detach}

        @type  dwProcessId: int
        @param dwProcessId: Global ID of a process to kill.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when killing the process.

        @raise WindowsError: Raises an exception on error, unless
            C{bIgnoreExceptions} is C{True}.
        """

        # Keep a reference to the process. We'll need it later.
        try:
            aProcess = self.system.get_process(dwProcessId)
        except KeyError:
            aProcess = Process(dwProcessId)

        # Cleanup all data referring to the process.
        self.__cleanup_process(dwProcessId, bIgnoreExceptions=bIgnoreExceptions)

        # Kill the process.
        try:
            try:
                if self.is_debugee(dwProcessId):
                    try:
                        if aProcess.is_alive():
                            aProcess.suspend()
                    finally:
                        self.detach(dwProcessId, bIgnoreExceptions=bIgnoreExceptions)
            finally:
                aProcess.kill()
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)

        # Cleanup what remains of the process data.
        try:
            aProcess.clear()
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)

    def kill_all(self, bIgnoreExceptions=False):
        """
        Kills from all processes currently being debugged.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when killing each process. C{False} to stop and raise an
            exception when encountering an error.

        @raise WindowsError: Raises an exception on error, unless
            C{bIgnoreExceptions} is C{True}.
        """
        for pid in self.get_debugee_pids():
            self.kill(pid, bIgnoreExceptions=bIgnoreExceptions)

    def detach(self, dwProcessId, bIgnoreExceptions=False):
        """
        Detaches from a process currently being debugged.

        @note: On Windows 2000 and below the process is killed.

        @see: L{attach}, L{detach_from_all}

        @type  dwProcessId: int
        @param dwProcessId: Global ID of a process to detach from.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when detaching. C{False} to stop and raise an exception when
            encountering an error.

        @raise WindowsError: Raises an exception on error, unless
            C{bIgnoreExceptions} is C{True}.
        """

        # Keep a reference to the process. We'll need it later.
        try:
            aProcess = self.system.get_process(dwProcessId)
        except KeyError:
            aProcess = Process(dwProcessId)

        # Determine if there is support for detaching.
        # This check should only fail on Windows 2000 and older.
        try:
            win32.DebugActiveProcessStop
            can_detach = True
        except AttributeError:
            can_detach = False

        # Continue the last event before detaching.
        # XXX not sure about this...
        try:
            if can_detach and self.lastEvent and self.lastEvent.get_pid() == dwProcessId:
                self.cont(self.lastEvent)
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)

        # Cleanup all data referring to the process.
        self.__cleanup_process(dwProcessId, bIgnoreExceptions=bIgnoreExceptions)

        try:
            # Detach from the process.
            # On Windows 2000 and before, kill the process.
            if can_detach:
                try:
                    win32.DebugActiveProcessStop(dwProcessId)
                except Exception:
                    if not bIgnoreExceptions:
                        raise
                    e = sys.exc_info()[1]
                    warnings.warn(str(e), RuntimeWarning)
            else:
                try:
                    aProcess.kill()
                except Exception:
                    if not bIgnoreExceptions:
                        raise
                    e = sys.exc_info()[1]
                    warnings.warn(str(e), RuntimeWarning)

        finally:
            # Cleanup what remains of the process data.
            aProcess.clear()

    def detach_from_all(self, bIgnoreExceptions=False):
        """
        Detaches from all processes currently being debugged.

        @note: To better handle last debugging event, call L{stop} instead.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when detaching.

        @raise WindowsError: Raises an exception on error, unless
            C{bIgnoreExceptions} is C{True}.
        """
        for pid in self.get_debugee_pids():
            self.detach(pid, bIgnoreExceptions=bIgnoreExceptions)

    # ------------------------------------------------------------------------------

    def wait(self, dwMilliseconds=None):
        """
        Waits for the next debug event.

        @see: L{cont}, L{dispatch}, L{loop}

        @type  dwMilliseconds: int
        @param dwMilliseconds: (Optional) Timeout in milliseconds.
            Use C{INFINITE} or C{None} for no timeout.

        @rtype:  L{Event}
        @return: An event that occured in one of the debugees.

        @raise WindowsError: Raises an exception on error.
            If no target processes are left to debug,
            the error code is L{win32.ERROR_INVALID_HANDLE}.
        """

        # Wait for the next debug event.
        raw = win32.WaitForDebugEvent(dwMilliseconds)
        event = EventFactory.get(self, raw)

        # Remember it.
        self.lastEvent = event

        # Return it.
        return event

    def dispatch(self, event=None):
        """
        Calls the debug event notify callbacks.

        @see: L{cont}, L{loop}, L{wait}

        @type  event: L{Event}
        @param event: (Optional) Event object returned by L{wait}.

        @raise WindowsError: Raises an exception on error.
        """

        # If no event object was given, use the last event.
        if event is None:
            event = self.lastEvent

        # Ignore dummy events.
        if not event:
            return

        # Determine the default behaviour for this event.
        # XXX HACK
        # Some undocumented flags are used, but as far as I know in those
        # versions of Windows that don't support them they should behave
        # like DGB_CONTINUE.

        code = event.get_event_code()
        if code == win32.EXCEPTION_DEBUG_EVENT:
            # At this point, by default some exception types are swallowed by
            # the debugger, because we don't know yet if it was caused by the
            # debugger itself or the debugged process.
            #
            # Later on (see breakpoint.py) if we determined the exception was
            # not caused directly by the debugger itself, we set the default
            # back to passing the exception to the debugee.
            #
            # The "invalid handle" exception is also swallowed by the debugger
            # because it's not normally generated by the debugee. But in
            # hostile mode we want to pass it to the debugee, as it may be the
            # result of an anti-debug trick. In that case it's best to disable
            # bad handles detection with Microsoft's gflags.exe utility. See:
            # http://msdn.microsoft.com/en-us/library/windows/hardware/ff549557(v=vs.85).aspx

            exc_code = event.get_exception_code()
            if exc_code in (
                win32.EXCEPTION_BREAKPOINT,
                win32.EXCEPTION_WX86_BREAKPOINT,
                win32.EXCEPTION_SINGLE_STEP,
                win32.EXCEPTION_GUARD_PAGE,
            ):
                event.continueStatus = win32.DBG_CONTINUE
            elif exc_code == win32.EXCEPTION_INVALID_HANDLE:
                if self.__bHostileCode:
                    event.continueStatus = win32.DBG_EXCEPTION_NOT_HANDLED
                else:
                    event.continueStatus = win32.DBG_CONTINUE
            else:
                event.continueStatus = win32.DBG_EXCEPTION_NOT_HANDLED

        elif code == win32.RIP_EVENT and event.get_rip_type() == win32.SLE_ERROR:
            # RIP events that signal fatal events should kill the process.
            event.continueStatus = win32.DBG_TERMINATE_PROCESS

        else:
            # Other events need this continue code.
            # Sometimes other codes can be used and are ignored, sometimes not.
            # For example, when using the DBG_EXCEPTION_NOT_HANDLED code,
            # debug strings are sent twice (!)
            event.continueStatus = win32.DBG_CONTINUE

        # Dispatch the debug event.
        return EventDispatcher.dispatch(self, event)

    def cont(self, event=None):
        """
        Resumes execution after processing a debug event.

        @see: dispatch(), loop(), wait()

        @type  event: L{Event}
        @param event: (Optional) Event object returned by L{wait}.

        @raise WindowsError: Raises an exception on error.
        """

        # If no event object was given, use the last event.
        if event is None:
            event = self.lastEvent

        # Ignore dummy events.
        if not event:
            return

        # Get the event continue status information.
        dwProcessId = event.get_pid()
        dwThreadId = event.get_tid()
        dwContinueStatus = event.continueStatus

        # Check if the process is still being debugged.
        if self.is_debugee(dwProcessId):
            # Try to flush the instruction cache.
            try:
                if self.system.has_process(dwProcessId):
                    aProcess = self.system.get_process(dwProcessId)
                else:
                    aProcess = Process(dwProcessId)
                aProcess.flush_instruction_cache()
            except WindowsError:
                pass

            # XXX TODO
            #
            # Try to execute the UnhandledExceptionFilter for second chance
            # exceptions, at least when in hostile mode (in normal mode it
            # would be breaking compatibility, as users may actually expect
            # second chance exceptions to be raised again).
            #
            # Reportedly in Windows 7 (maybe in Vista too) this seems to be
            # happening already. In XP and below the UnhandledExceptionFilter
            # was never called for processes being debugged.

            # Continue execution of the debugee.
            win32.ContinueDebugEvent(dwProcessId, dwThreadId, dwContinueStatus)

        # If the event is the last event, forget it.
        if event == self.lastEvent:
            self.lastEvent = None

    def stop(self, bIgnoreExceptions=True):
        """
        Stops debugging all processes.

        If the kill on exit mode is on, debugged processes are killed when the
        debugger is stopped. Otherwise when the debugger stops it detaches from
        all debugged processes and leaves them running (default). For more
        details see: L{__init__}

        @note: This method is better than L{detach_from_all} because it can
            gracefully handle the last debugging event before detaching.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when detaching.
        """

        # Determine if we have a last debug event that we need to continue.
        try:
            event = self.lastEvent
            has_event = bool(event)
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)
            has_event = False

        # If we do...
        if has_event:
            # Disable all breakpoints in the process before resuming execution.
            try:
                pid = event.get_pid()
                self.disable_process_breakpoints(pid)
            except Exception:
                if not bIgnoreExceptions:
                    raise
                e = sys.exc_info()[1]
                warnings.warn(str(e), RuntimeWarning)

            # Disable all breakpoints in the thread before resuming execution.
            try:
                tid = event.get_tid()
                self.disable_thread_breakpoints(tid)
            except Exception:
                if not bIgnoreExceptions:
                    raise
                e = sys.exc_info()[1]
                warnings.warn(str(e), RuntimeWarning)

            # Resume execution.
            try:
                event.continueDebugEvent = win32.DBG_CONTINUE
                self.cont(event)
            except Exception:
                if not bIgnoreExceptions:
                    raise
                e = sys.exc_info()[1]
                warnings.warn(str(e), RuntimeWarning)

        # Detach from or kill all debuggees.
        try:
            if self.__bKillOnExit:
                self.kill_all(bIgnoreExceptions)
            else:
                self.detach_from_all(bIgnoreExceptions)
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)

        # Cleanup the process snapshots.
        try:
            self.system.clear()
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)

        # Close all Win32 handles the Python garbage collector failed to close.
        self.force_garbage_collection(bIgnoreExceptions)

    def next(self):
        """
        Handles the next debug event.

        @see: L{cont}, L{dispatch}, L{wait}, L{stop}

        @raise WindowsError: Raises an exception on error.

            If the wait operation causes an error, debugging is stopped
            (meaning all debugees are either killed or detached from).

            If the event dispatching causes an error, the event is still
            continued before returning. This may happen, for example, if the
            event handler raises an exception nobody catches.
        """
        try:
            event = self.wait()
        except Exception:
            self.stop()
            raise
        try:
            self.dispatch()
        finally:
            self.cont()

    def loop(self):
        """
        Simple debugging loop.

        This debugging loop is meant to be useful for most simple scripts.
        It iterates as long as there is at least one debugee, or an exception
        is raised. Multiple calls are allowed.

        This is a trivial example script::
            import sys
            debug = Debug()
            try:
                debug.execv( sys.argv [ 1 : ] )
                debug.loop()
            finally:
                debug.stop()

        @see: L{next}, L{stop}

            U{http://msdn.microsoft.com/en-us/library/ms681675(VS.85).aspx}

        @raise WindowsError: Raises an exception on error.

            If the wait operation causes an error, debugging is stopped
            (meaning all debugees are either killed or detached from).

            If the event dispatching causes an error, the event is still
            continued before returning. This may happen, for example, if the
            event handler raises an exception nobody catches.
        """
        while self:
            self.next()

    def get_debugee_count(self):
        """
        @rtype:  int
        @return: Number of processes being debugged.
        """
        return len(self.__attachedDebugees) + len(self.__startedDebugees)

    def get_debugee_pids(self):
        """
        @rtype:  list( int... )
        @return: Global IDs of processes being debugged.
        """
        return list(self.__attachedDebugees) + list(self.__startedDebugees)

    def is_debugee(self, dwProcessId):
        """
        Determine if the debugger is debugging the given process.

        @see: L{is_debugee_attached}, L{is_debugee_started}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @rtype:  bool
        @return: C{True} if the given process is being debugged
            by this L{Debug} instance.
        """
        return self.is_debugee_attached(dwProcessId) or self.is_debugee_started(dwProcessId)

    def is_debugee_started(self, dwProcessId):
        """
        Determine if the given process was started by the debugger.

        @see: L{is_debugee}, L{is_debugee_attached}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @rtype:  bool
        @return: C{True} if the given process was started for debugging by this
            L{Debug} instance.
        """
        return dwProcessId in self.__startedDebugees

    def is_debugee_attached(self, dwProcessId):
        """
        Determine if the debugger is attached to the given process.

        @see: L{is_debugee}, L{is_debugee_started}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @rtype:  bool
        @return: C{True} if the given process is attached to this
            L{Debug} instance.
        """
        return dwProcessId in self.__attachedDebugees

    def in_hostile_mode(self):
        """
        Determine if we're in hostile mode (anti-anti-debug).

        @rtype:  bool
        @return: C{True} if this C{Debug} instance was started in hostile mode,
            C{False} otherwise.
        """
        return self.__bHostileCode

    # ------------------------------------------------------------------------------

    def interactive(self, bConfirmQuit=True, bShowBanner=True):
        """
        Start an interactive debugging session.

        @type  bConfirmQuit: bool
        @param bConfirmQuit: Set to C{True} to ask the user for confirmation
            before closing the session, C{False} otherwise.

        @type  bShowBanner: bool
        @param bShowBanner: Set to C{True} to show a banner before entering
            the session and after leaving it, C{False} otherwise.

        @warn: This will temporarily disable the user-defined event handler!

        This method returns when the user closes the session.
        """
        print("")
        print("-" * 79)
        print("Interactive debugging session started.")
        print('Use the "help" command to list all available commands.')
        print('Use the "quit" command to close this session.')
        print("-" * 79)
        if self.lastEvent is None:
            print("")
        console = ConsoleDebugger()
        console.confirm_quit = bConfirmQuit
        console.load_history()
        try:
            console.start_using_debugger(self)
            console.loop()
        finally:
            console.stop_using_debugger()
            console.save_history()
        print("")
        print("-" * 79)
        print("Interactive debugging session closed.")
        print("-" * 79)
        print("")

    # ------------------------------------------------------------------------------

    @staticmethod
    def force_garbage_collection(bIgnoreExceptions=True):
        """
        Close all Win32 handles the Python garbage collector failed to close.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when detaching.
        """
        try:
            import gc

            gc.collect()
            bRecollect = False
            for obj in list(gc.garbage):
                try:
                    if isinstance(obj, win32.Handle):
                        obj.close()
                    elif isinstance(obj, Event):
                        obj.debug = None
                    elif isinstance(obj, Process):
                        obj.clear()
                    elif isinstance(obj, Thread):
                        obj.set_process(None)
                        obj.clear()
                    elif isinstance(obj, Module):
                        obj.set_process(None)
                    elif isinstance(obj, Window):
                        obj.set_process(None)
                    else:
                        continue
                    gc.garbage.remove(obj)
                    del obj
                    bRecollect = True
                except Exception:
                    if not bIgnoreExceptions:
                        raise
                    e = sys.exc_info()[1]
                    warnings.warn(str(e), RuntimeWarning)
            if bRecollect:
                gc.collect()
        except Exception:
            if not bIgnoreExceptions:
                raise
            e = sys.exc_info()[1]
            warnings.warn(str(e), RuntimeWarning)

    # ------------------------------------------------------------------------------

    def _notify_create_process(self, event):
        """
        Notify the creation of a new process.

        @warning: This method is meant to be used internally by the debugger.

        @type  event: L{CreateProcessEvent}
        @param event: Create process event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        dwProcessId = event.get_pid()
        if dwProcessId not in self.__attachedDebugees:
            if dwProcessId not in self.__startedDebugees:
                self.__startedDebugees.add(dwProcessId)

        retval = self.system._notify_create_process(event)

        # Set a breakpoint on the program's entry point if requested.
        # Try not to use the Event object's entry point value, as in some cases
        # it may be wrong. See: http://pferrie.host22.com/misc/lowlevel3.htm
        if dwProcessId in self.__breakOnEP:
            try:
                lpEntryPoint = event.get_process().get_entry_point()
            except Exception:
                lpEntryPoint = event.get_start_address()

            # It'd be best to use a hardware breakpoint instead, at least in
            # hostile mode. But since the main thread's context gets smashed
            # by the loader, I haven't found a way to make it work yet.
            self.break_at(dwProcessId, lpEntryPoint)

        # Defeat isDebuggerPresent by patching PEB->BeingDebugged.
        # When we do this, some debugging APIs cease to work as expected.
        # For example, the system breakpoint isn't hit when we attach.
        # For that reason we need to define a code breakpoint at the
        # code location where a new thread is spawned by the debugging
        # APIs, ntdll!DbgUiRemoteBreakin.
        if self.__bHostileCode:
            aProcess = event.get_process()
            try:
                hProcess = aProcess.get_handle(win32.PROCESS_QUERY_INFORMATION)
                pbi = win32.NtQueryInformationProcess(hProcess, win32.ProcessBasicInformation)
                ptr = pbi.PebBaseAddress + 2
                if aProcess.peek(ptr, 1) == "\x01":
                    aProcess.poke(ptr, "\x00")
            except WindowsError:
                e = sys.exc_info()[1]
                warnings.warn("Cannot patch PEB->BeingDebugged, reason: %s" % e.strerror)

        return retval

    def _notify_create_thread(self, event):
        """
        Notify the creation of a new thread.

        @warning: This method is meant to be used internally by the debugger.

        @type  event: L{CreateThreadEvent}
        @param event: Create thread event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        return event.get_process()._notify_create_thread(event)

    def _notify_load_dll(self, event):
        """
        Notify the load of a new module.

        @warning: This method is meant to be used internally by the debugger.

        @type  event: L{LoadDLLEvent}
        @param event: Load DLL event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """

        # Pass the event to the breakpoint container.
        bCallHandler = _BreakpointContainer._notify_load_dll(self, event)

        # Get the process where the DLL was loaded.
        aProcess = event.get_process()

        # Pass the event to the process.
        bCallHandler = aProcess._notify_load_dll(event) and bCallHandler

        # Anti-anti-debugging tricks on ntdll.dll.
        if self.__bHostileCode:
            aModule = event.get_module()
            if aModule.match_name("ntdll.dll"):
                # Since we've overwritten the PEB to hide
                # ourselves, we no longer have the system
                # breakpoint when attaching to the process.
                # Set a breakpoint at ntdll!DbgUiRemoteBreakin
                # instead (that's where the debug API spawns
                # it's auxiliary threads). This also defeats
                # a simple anti-debugging trick: the hostile
                # process could have overwritten the int3
                # instruction at the system breakpoint.
                self.break_at(aProcess.get_pid(), aProcess.resolve_label("ntdll!DbgUiRemoteBreakin"))

        return bCallHandler

    def _notify_exit_process(self, event):
        """
        Notify the termination of a process.

        @warning: This method is meant to be used internally by the debugger.

        @type  event: L{ExitProcessEvent}
        @param event: Exit process event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        bCallHandler1 = _BreakpointContainer._notify_exit_process(self, event)
        bCallHandler2 = self.system._notify_exit_process(event)

        try:
            self.detach(event.get_pid())
        except WindowsError:
            e = sys.exc_info()[1]
            if e.winerror != win32.ERROR_INVALID_PARAMETER:
                warnings.warn("Failed to detach from dead process, reason: %s" % str(e), RuntimeWarning)
        except Exception:
            e = sys.exc_info()[1]
            warnings.warn("Failed to detach from dead process, reason: %s" % str(e), RuntimeWarning)

        return bCallHandler1 and bCallHandler2

    def _notify_exit_thread(self, event):
        """
        Notify the termination of a thread.

        @warning: This method is meant to be used internally by the debugger.

        @type  event: L{ExitThreadEvent}
        @param event: Exit thread event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        bCallHandler1 = _BreakpointContainer._notify_exit_thread(self, event)
        bCallHandler2 = event.get_process()._notify_exit_thread(event)
        return bCallHandler1 and bCallHandler2

    def _notify_unload_dll(self, event):
        """
        Notify the unload of a module.

        @warning: This method is meant to be used internally by the debugger.

        @type  event: L{UnloadDLLEvent}
        @param event: Unload DLL event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        bCallHandler1 = _BreakpointContainer._notify_unload_dll(self, event)
        bCallHandler2 = event.get_process()._notify_unload_dll(event)
        return bCallHandler1 and bCallHandler2

    def _notify_rip(self, event):
        """
        Notify of a RIP event.

        @warning: This method is meant to be used internally by the debugger.

        @type  event: L{RIPEvent}
        @param event: RIP event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        event.debug.detach(event.get_pid())
        return True

    def _notify_debug_control_c(self, event):
        """
        Notify of a Debug Ctrl-C exception.

        @warning: This method is meant to be used internally by the debugger.

        @note: This exception is only raised when a debugger is attached, and
            applications are not supposed to handle it, so we need to handle it
            ourselves or the application may crash.

        @see: U{http://msdn.microsoft.com/en-us/library/aa363082(VS.85).aspx}

        @type  event: L{ExceptionEvent}
        @param event: Debug Ctrl-C exception event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        if event.is_first_chance():
            event.continueStatus = win32.DBG_EXCEPTION_HANDLED
        return True

    def _notify_ms_vc_exception(self, event):
        """
        Notify of a Microsoft Visual C exception.

        @warning: This method is meant to be used internally by the debugger.

        @note: This allows the debugger to understand the
            Microsoft Visual C thread naming convention.

        @see: U{http://msdn.microsoft.com/en-us/library/xcb2z8hs.aspx}

        @type  event: L{ExceptionEvent}
        @param event: Microsoft Visual C exception event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        dwType = event.get_exception_information(0)
        if dwType == 0x1000:
            pszName = event.get_exception_information(1)
            dwThreadId = event.get_exception_information(2)
            dwFlags = event.get_exception_information(3)

            aProcess = event.get_process()
            szName = aProcess.peek_string(pszName, fUnicode=False)
            if szName:
                if dwThreadId == -1:
                    dwThreadId = event.get_tid()

                if aProcess.has_thread(dwThreadId):
                    aThread = aProcess.get_thread(dwThreadId)
                else:
                    aThread = Thread(dwThreadId)
                    aProcess._add_thread(aThread)

                ##                if aThread.get_name() is None:
                ##                    aThread.set_name(szName)
                aThread.set_name(szName)

        return True

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\shortcuts\prompt.py ===
"""
Line editing functionality.
---------------------------

This provides a UI for a line input, similar to GNU Readline, libedit and
linenoise.

Either call the `prompt` function for every line input. Or create an instance
of the :class:`.PromptSession` class and call the `prompt` method from that
class. In the second case, we'll have a 'session' that keeps all the state like
the history in between several calls.

There is a lot of overlap between the arguments taken by the `prompt` function
and the `PromptSession` (like `completer`, `style`, etcetera). There we have
the freedom to decide which settings we want for the whole 'session', and which
we want for an individual `prompt`.

Example::

        # Simple `prompt` call.
        result = prompt('Say something: ')

        # Using a 'session'.
        s = PromptSession()
        result = s.prompt('Say something: ')
"""

from __future__ import annotations

from asyncio import get_running_loop
from contextlib import contextmanager
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Callable, Generic, Iterator, TypeVar, Union, cast

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.auto_suggest import AutoSuggest, DynamicAutoSuggest
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.clipboard import Clipboard, DynamicClipboard, InMemoryClipboard
from prompt_toolkit.completion import Completer, DynamicCompleter, ThreadedCompleter
from prompt_toolkit.cursor_shapes import (
    AnyCursorShapeConfig,
    CursorShapeConfig,
    DynamicCursorShapeConfig,
)
from prompt_toolkit.document import Document
from prompt_toolkit.enums import DEFAULT_BUFFER, SEARCH_BUFFER, EditingMode
from prompt_toolkit.eventloop import InputHook
from prompt_toolkit.filters import (
    Condition,
    FilterOrBool,
    has_arg,
    has_focus,
    is_done,
    is_true,
    renderer_height_is_known,
    to_filter,
)
from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
    fragment_list_to_text,
    merge_formatted_text,
    to_formatted_text,
)
from prompt_toolkit.history import History, InMemoryHistory
from prompt_toolkit.input.base import Input
from prompt_toolkit.key_binding.bindings.auto_suggest import load_auto_suggest_bindings
from prompt_toolkit.key_binding.bindings.completion import (
    display_completions_like_readline,
)
from prompt_toolkit.key_binding.bindings.open_in_editor import (
    load_open_in_editor_bindings,
)
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    DynamicKeyBindings,
    KeyBindings,
    KeyBindingsBase,
    merge_key_bindings,
)
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Float, FloatContainer, HSplit, Window
from prompt_toolkit.layout.containers import ConditionalContainer, WindowAlign
from prompt_toolkit.layout.controls import (
    BufferControl,
    FormattedTextControl,
    SearchBufferControl,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu, MultiColumnCompletionsMenu
from prompt_toolkit.layout.processors import (
    AfterInput,
    AppendAutoSuggestion,
    ConditionalProcessor,
    DisplayMultipleCursors,
    DynamicProcessor,
    HighlightIncrementalSearchProcessor,
    HighlightSelectionProcessor,
    PasswordProcessor,
    Processor,
    ReverseSearchProcessor,
    merge_processors,
)
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.lexers import DynamicLexer, Lexer
from prompt_toolkit.output import ColorDepth, DummyOutput, Output
from prompt_toolkit.styles import (
    BaseStyle,
    ConditionalStyleTransformation,
    DynamicStyle,
    DynamicStyleTransformation,
    StyleTransformation,
    SwapLightAndDarkStyleTransformation,
    merge_style_transformations,
)
from prompt_toolkit.utils import (
    get_cwidth,
    is_dumb_terminal,
    suspend_to_background_supported,
    to_str,
)
from prompt_toolkit.validation import DynamicValidator, Validator
from prompt_toolkit.widgets.toolbars import (
    SearchToolbar,
    SystemToolbar,
    ValidationToolbar,
)

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text.base import MagicFormattedText

__all__ = [
    "PromptSession",
    "prompt",
    "confirm",
    "create_confirm_session",  # Used by '_display_completions_like_readline'.
    "CompleteStyle",
]

_StyleAndTextTuplesCallable = Callable[[], StyleAndTextTuples]
E = KeyPressEvent


def _split_multiline_prompt(
    get_prompt_text: _StyleAndTextTuplesCallable,
) -> tuple[
    Callable[[], bool], _StyleAndTextTuplesCallable, _StyleAndTextTuplesCallable
]:
    """
    Take a `get_prompt_text` function and return three new functions instead.
    One that tells whether this prompt consists of multiple lines; one that
    returns the fragments to be shown on the lines above the input; and another
    one with the fragments to be shown at the first line of the input.
    """

    def has_before_fragments() -> bool:
        for fragment, char, *_ in get_prompt_text():
            if "\n" in char:
                return True
        return False

    def before() -> StyleAndTextTuples:
        result: StyleAndTextTuples = []
        found_nl = False
        for fragment, char, *_ in reversed(explode_text_fragments(get_prompt_text())):
            if found_nl:
                result.insert(0, (fragment, char))
            elif char == "\n":
                found_nl = True
        return result

    def first_input_line() -> StyleAndTextTuples:
        result: StyleAndTextTuples = []
        for fragment, char, *_ in reversed(explode_text_fragments(get_prompt_text())):
            if char == "\n":
                break
            else:
                result.insert(0, (fragment, char))
        return result

    return has_before_fragments, before, first_input_line


class _RPrompt(Window):
    """
    The prompt that is displayed on the right side of the Window.
    """

    def __init__(self, text: AnyFormattedText) -> None:
        super().__init__(
            FormattedTextControl(text=text),
            align=WindowAlign.RIGHT,
            style="class:rprompt",
        )


class CompleteStyle(str, Enum):
    """
    How to display autocompletions for the prompt.
    """

    value: str

    COLUMN = "COLUMN"
    MULTI_COLUMN = "MULTI_COLUMN"
    READLINE_LIKE = "READLINE_LIKE"


# Formatted text for the continuation prompt. It's the same like other
# formatted text, except that if it's a callable, it takes three arguments.
PromptContinuationText = Union[
    str,
    "MagicFormattedText",
    StyleAndTextTuples,
    # (prompt_width, line_number, wrap_count) -> AnyFormattedText.
    Callable[[int, int, int], AnyFormattedText],
]

_T = TypeVar("_T")


class PromptSession(Generic[_T]):
    """
    PromptSession for a prompt application, which can be used as a GNU Readline
    replacement.

    This is a wrapper around a lot of ``prompt_toolkit`` functionality and can
    be a replacement for `raw_input`.

    All parameters that expect "formatted text" can take either just plain text
    (a unicode object), a list of ``(style_str, text)`` tuples or an HTML object.

    Example usage::

        s = PromptSession(message='>')
        text = s.prompt()

    :param message: Plain text or formatted text to be shown before the prompt.
        This can also be a callable that returns formatted text.
    :param multiline: `bool` or :class:`~prompt_toolkit.filters.Filter`.
        When True, prefer a layout that is more adapted for multiline input.
        Text after newlines is automatically indented, and search/arg input is
        shown below the input, instead of replacing the prompt.
    :param wrap_lines: `bool` or :class:`~prompt_toolkit.filters.Filter`.
        When True (the default), automatically wrap long lines instead of
        scrolling horizontally.
    :param is_password: Show asterisks instead of the actual typed characters.
    :param editing_mode: ``EditingMode.VI`` or ``EditingMode.EMACS``.
    :param vi_mode: `bool`, if True, Identical to ``editing_mode=EditingMode.VI``.
    :param complete_while_typing: `bool` or
        :class:`~prompt_toolkit.filters.Filter`. Enable autocompletion while
        typing.
    :param validate_while_typing: `bool` or
        :class:`~prompt_toolkit.filters.Filter`. Enable input validation while
        typing.
    :param enable_history_search: `bool` or
        :class:`~prompt_toolkit.filters.Filter`. Enable up-arrow parting
        string matching.
    :param search_ignore_case:
        :class:`~prompt_toolkit.filters.Filter`. Search case insensitive.
    :param lexer: :class:`~prompt_toolkit.lexers.Lexer` to be used for the
        syntax highlighting.
    :param validator: :class:`~prompt_toolkit.validation.Validator` instance
        for input validation.
    :param completer: :class:`~prompt_toolkit.completion.Completer` instance
        for input completion.
    :param complete_in_thread: `bool` or
        :class:`~prompt_toolkit.filters.Filter`. Run the completer code in a
        background thread in order to avoid blocking the user interface.
        For ``CompleteStyle.READLINE_LIKE``, this setting has no effect. There
        we always run the completions in the main thread.
    :param reserve_space_for_menu: Space to be reserved for displaying the menu.
        (0 means that no space needs to be reserved.)
    :param auto_suggest: :class:`~prompt_toolkit.auto_suggest.AutoSuggest`
        instance for input suggestions.
    :param style: :class:`.Style` instance for the color scheme.
    :param include_default_pygments_style: `bool` or
        :class:`~prompt_toolkit.filters.Filter`. Tell whether the default
        styling for Pygments lexers has to be included. By default, this is
        true, but it is recommended to be disabled if another Pygments style is
        passed as the `style` argument, otherwise, two Pygments styles will be
        merged.
    :param style_transformation:
        :class:`~prompt_toolkit.style.StyleTransformation` instance.
    :param swap_light_and_dark_colors: `bool` or
        :class:`~prompt_toolkit.filters.Filter`. When enabled, apply
        :class:`~prompt_toolkit.style.SwapLightAndDarkStyleTransformation`.
        This is useful for switching between dark and light terminal
        backgrounds.
    :param enable_system_prompt: `bool` or
        :class:`~prompt_toolkit.filters.Filter`. Pressing Meta+'!' will show
        a system prompt.
    :param enable_suspend: `bool` or :class:`~prompt_toolkit.filters.Filter`.
        Enable Control-Z style suspension.
    :param enable_open_in_editor: `bool` or
        :class:`~prompt_toolkit.filters.Filter`. Pressing 'v' in Vi mode or
        C-X C-E in emacs mode will open an external editor.
    :param history: :class:`~prompt_toolkit.history.History` instance.
    :param clipboard: :class:`~prompt_toolkit.clipboard.Clipboard` instance.
        (e.g. :class:`~prompt_toolkit.clipboard.InMemoryClipboard`)
    :param rprompt: Text or formatted text to be displayed on the right side.
        This can also be a callable that returns (formatted) text.
    :param bottom_toolbar: Formatted text or callable which is supposed to
        return formatted text.
    :param prompt_continuation: Text that needs to be displayed for a multiline
        prompt continuation. This can either be formatted text or a callable
        that takes a `prompt_width`, `line_number` and `wrap_count` as input
        and returns formatted text. When this is `None` (the default), then
        `prompt_width` spaces will be used.
    :param complete_style: ``CompleteStyle.COLUMN``,
        ``CompleteStyle.MULTI_COLUMN`` or ``CompleteStyle.READLINE_LIKE``.
    :param mouse_support: `bool` or :class:`~prompt_toolkit.filters.Filter`
        to enable mouse support.
    :param placeholder: Text to be displayed when no input has been given
        yet. Unlike the `default` parameter, this won't be returned as part of
        the output ever. This can be formatted text or a callable that returns
        formatted text.
    :param refresh_interval: (number; in seconds) When given, refresh the UI
        every so many seconds.
    :param input: `Input` object. (Note that the preferred way to change the
        input/output is by creating an `AppSession`.)
    :param output: `Output` object.
    :param interrupt_exception: The exception type that will be raised when
        there is a keyboard interrupt (control-c keypress).
    :param eof_exception: The exception type that will be raised when there is
        an end-of-file/exit event (control-d keypress).
    """

    _fields = (
        "message",
        "lexer",
        "completer",
        "complete_in_thread",
        "is_password",
        "editing_mode",
        "key_bindings",
        "is_password",
        "bottom_toolbar",
        "style",
        "style_transformation",
        "swap_light_and_dark_colors",
        "color_depth",
        "cursor",
        "include_default_pygments_style",
        "rprompt",
        "multiline",
        "prompt_continuation",
        "wrap_lines",
        "enable_history_search",
        "search_ignore_case",
        "complete_while_typing",
        "validate_while_typing",
        "complete_style",
        "mouse_support",
        "auto_suggest",
        "clipboard",
        "validator",
        "refresh_interval",
        "input_processors",
        "placeholder",
        "enable_system_prompt",
        "enable_suspend",
        "enable_open_in_editor",
        "reserve_space_for_menu",
        "tempfile_suffix",
        "tempfile",
    )

    def __init__(
        self,
        message: AnyFormattedText = "",
        *,
        multiline: FilterOrBool = False,
        wrap_lines: FilterOrBool = True,
        is_password: FilterOrBool = False,
        vi_mode: bool = False,
        editing_mode: EditingMode = EditingMode.EMACS,
        complete_while_typing: FilterOrBool = True,
        validate_while_typing: FilterOrBool = True,
        enable_history_search: FilterOrBool = False,
        search_ignore_case: FilterOrBool = False,
        lexer: Lexer | None = None,
        enable_system_prompt: FilterOrBool = False,
        enable_suspend: FilterOrBool = False,
        enable_open_in_editor: FilterOrBool = False,
        validator: Validator | None = None,
        completer: Completer | None = None,
        complete_in_thread: bool = False,
        reserve_space_for_menu: int = 8,
        complete_style: CompleteStyle = CompleteStyle.COLUMN,
        auto_suggest: AutoSuggest | None = None,
        style: BaseStyle | None = None,
        style_transformation: StyleTransformation | None = None,
        swap_light_and_dark_colors: FilterOrBool = False,
        color_depth: ColorDepth | None = None,
        cursor: AnyCursorShapeConfig = None,
        include_default_pygments_style: FilterOrBool = True,
        history: History | None = None,
        clipboard: Clipboard | None = None,
        prompt_continuation: PromptContinuationText | None = None,
        rprompt: AnyFormattedText = None,
        bottom_toolbar: AnyFormattedText = None,
        mouse_support: FilterOrBool = False,
        input_processors: list[Processor] | None = None,
        placeholder: AnyFormattedText | None = None,
        key_bindings: KeyBindingsBase | None = None,
        erase_when_done: bool = False,
        tempfile_suffix: str | Callable[[], str] | None = ".txt",
        tempfile: str | Callable[[], str] | None = None,
        refresh_interval: float = 0,
        input: Input | None = None,
        output: Output | None = None,
        interrupt_exception: type[BaseException] = KeyboardInterrupt,
        eof_exception: type[BaseException] = EOFError,
    ) -> None:
        history = history or InMemoryHistory()
        clipboard = clipboard or InMemoryClipboard()

        # Ensure backwards-compatibility, when `vi_mode` is passed.
        if vi_mode:
            editing_mode = EditingMode.VI

        # Store all settings in this class.
        self._input = input
        self._output = output

        # Store attributes.
        # (All except 'editing_mode'.)
        self.message = message
        self.lexer = lexer
        self.completer = completer
        self.complete_in_thread = complete_in_thread
        self.is_password = is_password
        self.key_bindings = key_bindings
        self.bottom_toolbar = bottom_toolbar
        self.style = style
        self.style_transformation = style_transformation
        self.swap_light_and_dark_colors = swap_light_and_dark_colors
        self.color_depth = color_depth
        self.cursor = cursor
        self.include_default_pygments_style = include_default_pygments_style
        self.rprompt = rprompt
        self.multiline = multiline
        self.prompt_continuation = prompt_continuation
        self.wrap_lines = wrap_lines
        self.enable_history_search = enable_history_search
        self.search_ignore_case = search_ignore_case
        self.complete_while_typing = complete_while_typing
        self.validate_while_typing = validate_while_typing
        self.complete_style = complete_style
        self.mouse_support = mouse_support
        self.auto_suggest = auto_suggest
        self.clipboard = clipboard
        self.validator = validator
        self.refresh_interval = refresh_interval
        self.input_processors = input_processors
        self.placeholder = placeholder
        self.enable_system_prompt = enable_system_prompt
        self.enable_suspend = enable_suspend
        self.enable_open_in_editor = enable_open_in_editor
        self.reserve_space_for_menu = reserve_space_for_menu
        self.tempfile_suffix = tempfile_suffix
        self.tempfile = tempfile
        self.interrupt_exception = interrupt_exception
        self.eof_exception = eof_exception

        # Create buffers, layout and Application.
        self.history = history
        self.default_buffer = self._create_default_buffer()
        self.search_buffer = self._create_search_buffer()
        self.layout = self._create_layout()
        self.app = self._create_application(editing_mode, erase_when_done)

    def _dyncond(self, attr_name: str) -> Condition:
        """
        Dynamically take this setting from this 'PromptSession' class.
        `attr_name` represents an attribute name of this class. Its value
        can either be a boolean or a `Filter`.

        This returns something that can be used as either a `Filter`
        or `Filter`.
        """

        @Condition
        def dynamic() -> bool:
            value = cast(FilterOrBool, getattr(self, attr_name))
            return to_filter(value)()

        return dynamic

    def _create_default_buffer(self) -> Buffer:
        """
        Create and return the default input buffer.
        """
        dyncond = self._dyncond

        # Create buffers list.
        def accept(buff: Buffer) -> bool:
            """Accept the content of the default buffer. This is called when
            the validation succeeds."""
            cast(Application[str], get_app()).exit(result=buff.document.text)
            return True  # Keep text, we call 'reset' later on.

        return Buffer(
            name=DEFAULT_BUFFER,
            # Make sure that complete_while_typing is disabled when
            # enable_history_search is enabled. (First convert to Filter,
            # to avoid doing bitwise operations on bool objects.)
            complete_while_typing=Condition(
                lambda: is_true(self.complete_while_typing)
                and not is_true(self.enable_history_search)
                and not self.complete_style == CompleteStyle.READLINE_LIKE
            ),
            validate_while_typing=dyncond("validate_while_typing"),
            enable_history_search=dyncond("enable_history_search"),
            validator=DynamicValidator(lambda: self.validator),
            completer=DynamicCompleter(
                lambda: ThreadedCompleter(self.completer)
                if self.complete_in_thread and self.completer
                else self.completer
            ),
            history=self.history,
            auto_suggest=DynamicAutoSuggest(lambda: self.auto_suggest),
            accept_handler=accept,
            tempfile_suffix=lambda: to_str(self.tempfile_suffix or ""),
            tempfile=lambda: to_str(self.tempfile or ""),
        )

    def _create_search_buffer(self) -> Buffer:
        return Buffer(name=SEARCH_BUFFER)

    def _create_layout(self) -> Layout:
        """
        Create `Layout` for this prompt.
        """
        dyncond = self._dyncond

        # Create functions that will dynamically split the prompt. (If we have
        # a multiline prompt.)
        (
            has_before_fragments,
            get_prompt_text_1,
            get_prompt_text_2,
        ) = _split_multiline_prompt(self._get_prompt)

        default_buffer = self.default_buffer
        search_buffer = self.search_buffer

        # Create processors list.
        @Condition
        def display_placeholder() -> bool:
            return self.placeholder is not None and self.default_buffer.text == ""

        all_input_processors = [
            HighlightIncrementalSearchProcessor(),
            HighlightSelectionProcessor(),
            ConditionalProcessor(
                AppendAutoSuggestion(), has_focus(default_buffer) & ~is_done
            ),
            ConditionalProcessor(PasswordProcessor(), dyncond("is_password")),
            DisplayMultipleCursors(),
            # Users can insert processors here.
            DynamicProcessor(lambda: merge_processors(self.input_processors or [])),
            ConditionalProcessor(
                AfterInput(lambda: self.placeholder),
                filter=display_placeholder,
            ),
        ]

        # Create bottom toolbars.
        bottom_toolbar = ConditionalContainer(
            Window(
                FormattedTextControl(
                    lambda: self.bottom_toolbar, style="class:bottom-toolbar.text"
                ),
                style="class:bottom-toolbar",
                dont_extend_height=True,
                height=Dimension(min=1),
            ),
            filter=Condition(lambda: self.bottom_toolbar is not None)
            & ~is_done
            & renderer_height_is_known,
        )

        search_toolbar = SearchToolbar(
            search_buffer, ignore_case=dyncond("search_ignore_case")
        )

        search_buffer_control = SearchBufferControl(
            buffer=search_buffer,
            input_processors=[ReverseSearchProcessor()],
            ignore_case=dyncond("search_ignore_case"),
        )

        system_toolbar = SystemToolbar(
            enable_global_bindings=dyncond("enable_system_prompt")
        )

        def get_search_buffer_control() -> SearchBufferControl:
            "Return the UIControl to be focused when searching start."
            if is_true(self.multiline):
                return search_toolbar.control
            else:
                return search_buffer_control

        default_buffer_control = BufferControl(
            buffer=default_buffer,
            search_buffer_control=get_search_buffer_control,
            input_processors=all_input_processors,
            include_default_input_processors=False,
            lexer=DynamicLexer(lambda: self.lexer),
            preview_search=True,
        )

        default_buffer_window = Window(
            default_buffer_control,
            height=self._get_default_buffer_control_height,
            get_line_prefix=partial(
                self._get_line_prefix, get_prompt_text_2=get_prompt_text_2
            ),
            wrap_lines=dyncond("wrap_lines"),
        )

        @Condition
        def multi_column_complete_style() -> bool:
            return self.complete_style == CompleteStyle.MULTI_COLUMN

        # Build the layout.
        layout = HSplit(
            [
                # The main input, with completion menus floating on top of it.
                FloatContainer(
                    HSplit(
                        [
                            ConditionalContainer(
                                Window(
                                    FormattedTextControl(get_prompt_text_1),
                                    dont_extend_height=True,
                                ),
                                Condition(has_before_fragments),
                            ),
                            ConditionalContainer(
                                default_buffer_window,
                                Condition(
                                    lambda: get_app().layout.current_control
                                    != search_buffer_control
                                ),
                            ),
                            ConditionalContainer(
                                Window(search_buffer_control),
                                Condition(
                                    lambda: get_app().layout.current_control
                                    == search_buffer_control
                                ),
                            ),
                        ]
                    ),
                    [
                        # Completion menus.
                        # NOTE: Especially the multi-column menu needs to be
                        #       transparent, because the shape is not always
                        #       rectangular due to the meta-text below the menu.
                        Float(
                            xcursor=True,
                            ycursor=True,
                            transparent=True,
                            content=CompletionsMenu(
                                max_height=16,
                                scroll_offset=1,
                                extra_filter=has_focus(default_buffer)
                                & ~multi_column_complete_style,
                            ),
                        ),
                        Float(
                            xcursor=True,
                            ycursor=True,
                            transparent=True,
                            content=MultiColumnCompletionsMenu(
                                show_meta=True,
                                extra_filter=has_focus(default_buffer)
                                & multi_column_complete_style,
                            ),
                        ),
                        # The right prompt.
                        Float(
                            right=0,
                            top=0,
                            hide_when_covering_content=True,
                            content=_RPrompt(lambda: self.rprompt),
                        ),
                    ],
                ),
                ConditionalContainer(ValidationToolbar(), filter=~is_done),
                ConditionalContainer(
                    system_toolbar, dyncond("enable_system_prompt") & ~is_done
                ),
                # In multiline mode, we use two toolbars for 'arg' and 'search'.
                ConditionalContainer(
                    Window(FormattedTextControl(self._get_arg_text), height=1),
                    dyncond("multiline") & has_arg,
                ),
                ConditionalContainer(search_toolbar, dyncond("multiline") & ~is_done),
                bottom_toolbar,
            ]
        )

        return Layout(layout, default_buffer_window)

    def _create_application(
        self, editing_mode: EditingMode, erase_when_done: bool
    ) -> Application[_T]:
        """
        Create the `Application` object.
        """
        dyncond = self._dyncond

        # Default key bindings.
        auto_suggest_bindings = load_auto_suggest_bindings()
        open_in_editor_bindings = load_open_in_editor_bindings()
        prompt_bindings = self._create_prompt_bindings()

        # Create application
        application: Application[_T] = Application(
            layout=self.layout,
            style=DynamicStyle(lambda: self.style),
            style_transformation=merge_style_transformations(
                [
                    DynamicStyleTransformation(lambda: self.style_transformation),
                    ConditionalStyleTransformation(
                        SwapLightAndDarkStyleTransformation(),
                        dyncond("swap_light_and_dark_colors"),
                    ),
                ]
            ),
            include_default_pygments_style=dyncond("include_default_pygments_style"),
            clipboard=DynamicClipboard(lambda: self.clipboard),
            key_bindings=merge_key_bindings(
                [
                    merge_key_bindings(
                        [
                            auto_suggest_bindings,
                            ConditionalKeyBindings(
                                open_in_editor_bindings,
                                dyncond("enable_open_in_editor")
                                & has_focus(DEFAULT_BUFFER),
                            ),
                            prompt_bindings,
                        ]
                    ),
                    DynamicKeyBindings(lambda: self.key_bindings),
                ]
            ),
            mouse_support=dyncond("mouse_support"),
            editing_mode=editing_mode,
            erase_when_done=erase_when_done,
            reverse_vi_search_direction=True,
            color_depth=lambda: self.color_depth,
            cursor=DynamicCursorShapeConfig(lambda: self.cursor),
            refresh_interval=self.refresh_interval,
            input=self._input,
            output=self._output,
        )

        # During render time, make sure that we focus the right search control
        # (if we are searching). - This could be useful if people make the
        # 'multiline' property dynamic.
        """
        def on_render(app):
            multiline = is_true(self.multiline)
            current_control = app.layout.current_control

            if multiline:
                if current_control == search_buffer_control:
                    app.layout.current_control = search_toolbar.control
                    app.invalidate()
            else:
                if current_control == search_toolbar.control:
                    app.layout.current_control = search_buffer_control
                    app.invalidate()

        app.on_render += on_render
        """

        return application

    def _create_prompt_bindings(self) -> KeyBindings:
        """
        Create the KeyBindings for a prompt application.
        """
        kb = KeyBindings()
        handle = kb.add
        default_focused = has_focus(DEFAULT_BUFFER)

        @Condition
        def do_accept() -> bool:
            return not is_true(self.multiline) and self.app.layout.has_focus(
                DEFAULT_BUFFER
            )

        @handle("enter", filter=do_accept & default_focused)
        def _accept_input(event: E) -> None:
            "Accept input when enter has been pressed."
            self.default_buffer.validate_and_handle()

        @Condition
        def readline_complete_style() -> bool:
            return self.complete_style == CompleteStyle.READLINE_LIKE

        @handle("tab", filter=readline_complete_style & default_focused)
        def _complete_like_readline(event: E) -> None:
            "Display completions (like Readline)."
            display_completions_like_readline(event)

        @handle("c-c", filter=default_focused)
        @handle("<sigint>")
        def _keyboard_interrupt(event: E) -> None:
            "Abort when Control-C has been pressed."
            event.app.exit(exception=self.interrupt_exception(), style="class:aborting")

        @Condition
        def ctrl_d_condition() -> bool:
            """Ctrl-D binding is only active when the default buffer is selected
            and empty."""
            app = get_app()
            return (
                app.current_buffer.name == DEFAULT_BUFFER
                and not app.current_buffer.text
            )

        @handle("c-d", filter=ctrl_d_condition & default_focused)
        def _eof(event: E) -> None:
            "Exit when Control-D has been pressed."
            event.app.exit(exception=self.eof_exception(), style="class:exiting")

        suspend_supported = Condition(suspend_to_background_supported)

        @Condition
        def enable_suspend() -> bool:
            return to_filter(self.enable_suspend)()

        @handle("c-z", filter=suspend_supported & enable_suspend)
        def _suspend(event: E) -> None:
            """
            Suspend process to background.
            """
            event.app.suspend_to_background()

        return kb

    def prompt(
        self,
        # When any of these arguments are passed, this value is overwritten
        # in this PromptSession.
        message: AnyFormattedText | None = None,
        # `message` should go first, because people call it as
        # positional argument.
        *,
        editing_mode: EditingMode | None = None,
        refresh_interval: float | None = None,
        vi_mode: bool | None = None,
        lexer: Lexer | None = None,
        completer: Completer | None = None,
        complete_in_thread: bool | None = None,
        is_password: bool | None = None,
        key_bindings: KeyBindingsBase | None = None,
        bottom_toolbar: AnyFormattedText | None = None,
        style: BaseStyle | None = None,
        color_depth: ColorDepth | None = None,
        cursor: AnyCursorShapeConfig | None = None,
        include_default_pygments_style: FilterOrBool | None = None,
        style_transformation: StyleTransformation | None = None,
        swap_light_and_dark_colors: FilterOrBool | None = None,
        rprompt: AnyFormattedText | None = None,
        multiline: FilterOrBool | None = None,
        prompt_continuation: PromptContinuationText | None = None,
        wrap_lines: FilterOrBool | None = None,
        enable_history_search: FilterOrBool | None = None,
        search_ignore_case: FilterOrBool | None = None,
        complete_while_typing: FilterOrBool | None = None,
        validate_while_typing: FilterOrBool | None = None,
        complete_style: CompleteStyle | None = None,
        auto_suggest: AutoSuggest | None = None,
        validator: Validator | None = None,
        clipboard: Clipboard | None = None,
        mouse_support: FilterOrBool | None = None,
        input_processors: list[Processor] | None = None,
        placeholder: AnyFormattedText | None = None,
        reserve_space_for_menu: int | None = None,
        enable_system_prompt: FilterOrBool | None = None,
        enable_suspend: FilterOrBool | None = None,
        enable_open_in_editor: FilterOrBool | None = None,
        tempfile_suffix: str | Callable[[], str] | None = None,
        tempfile: str | Callable[[], str] | None = None,
        # Following arguments are specific to the current `prompt()` call.
        default: str | Document = "",
        accept_default: bool = False,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        in_thread: bool = False,
        inputhook: InputHook | None = None,
    ) -> _T:
        """
        Display the prompt.

        The first set of arguments is a subset of the :class:`~.PromptSession`
        class itself. For these, passing in ``None`` will keep the current
        values that are active in the session. Passing in a value will set the
        attribute for the session, which means that it applies to the current,
        but also to the next prompts.

        Note that in order to erase a ``Completer``, ``Validator`` or
        ``AutoSuggest``, you can't use ``None``. Instead pass in a
        ``DummyCompleter``, ``DummyValidator`` or ``DummyAutoSuggest`` instance
        respectively. For a ``Lexer`` you can pass in an empty ``SimpleLexer``.

        Additional arguments, specific for this prompt:

        :param default: The default input text to be shown. (This can be edited
            by the user).
        :param accept_default: When `True`, automatically accept the default
            value without allowing the user to edit the input.
        :param pre_run: Callable, called at the start of `Application.run`.
        :param in_thread: Run the prompt in a background thread; block the
            current thread. This avoids interference with an event loop in the
            current thread. Like `Application.run(in_thread=True)`.

        This method will raise ``KeyboardInterrupt`` when control-c has been
        pressed (for abort) and ``EOFError`` when control-d has been pressed
        (for exit).
        """
        # NOTE: We used to create a backup of the PromptSession attributes and
        #       restore them after exiting the prompt. This code has been
        #       removed, because it was confusing and didn't really serve a use
        #       case. (People were changing `Application.editing_mode`
        #       dynamically and surprised that it was reset after every call.)

        # NOTE 2: YES, this is a lot of repeation below...
        #         However, it is a very convenient for a user to accept all
        #         these parameters in this `prompt` method as well. We could
        #         use `locals()` and `setattr` to avoid the repetition, but
        #         then we loose the advantage of mypy and pyflakes to be able
        #         to verify the code.
        if message is not None:
            self.message = message
        if editing_mode is not None:
            self.editing_mode = editing_mode
        if refresh_interval is not None:
            self.refresh_interval = refresh_interval
        if vi_mode:
            self.editing_mode = EditingMode.VI
        if lexer is not None:
            self.lexer = lexer
        if completer is not None:
            self.completer = completer
        if complete_in_thread is not None:
            self.complete_in_thread = complete_in_thread
        if is_password is not None:
            self.is_password = is_password
        if key_bindings is not None:
            self.key_bindings = key_bindings
        if bottom_toolbar is not None:
            self.bottom_toolbar = bottom_toolbar
        if style is not None:
            self.style = style
        if color_depth is not None:
            self.color_depth = color_depth
        if cursor is not None:
            self.cursor = cursor
        if include_default_pygments_style is not None:
            self.include_default_pygments_style = include_default_pygments_style
        if style_transformation is not None:
            self.style_transformation = style_transformation
        if swap_light_and_dark_colors is not None:
            self.swap_light_and_dark_colors = swap_light_and_dark_colors
        if rprompt is not None:
            self.rprompt = rprompt
        if multiline is not None:
            self.multiline = multiline
        if prompt_continuation is not None:
            self.prompt_continuation = prompt_continuation
        if wrap_lines is not None:
            self.wrap_lines = wrap_lines
        if enable_history_search is not None:
            self.enable_history_search = enable_history_search
        if search_ignore_case is not None:
            self.search_ignore_case = search_ignore_case
        if complete_while_typing is not None:
            self.complete_while_typing = complete_while_typing
        if validate_while_typing is not None:
            self.validate_while_typing = validate_while_typing
        if complete_style is not None:
            self.complete_style = complete_style
        if auto_suggest is not None:
            self.auto_suggest = auto_suggest
        if validator is not None:
            self.validator = validator
        if clipboard is not None:
            self.clipboard = clipboard
        if mouse_support is not None:
            self.mouse_support = mouse_support
        if input_processors is not None:
            self.input_processors = input_processors
        if placeholder is not None:
            self.placeholder = placeholder
        if reserve_space_for_menu is not None:
            self.reserve_space_for_menu = reserve_space_for_menu
        if enable_system_prompt is not None:
            self.enable_system_prompt = enable_system_prompt
        if enable_suspend is not None:
            self.enable_suspend = enable_suspend
        if enable_open_in_editor is not None:
            self.enable_open_in_editor = enable_open_in_editor
        if tempfile_suffix is not None:
            self.tempfile_suffix = tempfile_suffix
        if tempfile is not None:
            self.tempfile = tempfile

        self._add_pre_run_callables(pre_run, accept_default)
        self.default_buffer.reset(
            default if isinstance(default, Document) else Document(default)
        )
        self.app.refresh_interval = self.refresh_interval  # This is not reactive.

        # If we are using the default output, and have a dumb terminal. Use the
        # dumb prompt.
        if self._output is None and is_dumb_terminal():
            with self._dumb_prompt(self.message) as dump_app:
                return dump_app.run(in_thread=in_thread, handle_sigint=handle_sigint)

        return self.app.run(
            set_exception_handler=set_exception_handler,
            in_thread=in_thread,
            handle_sigint=handle_sigint,
            inputhook=inputhook,
        )

    @contextmanager
    def _dumb_prompt(self, message: AnyFormattedText = "") -> Iterator[Application[_T]]:
        """
        Create prompt `Application` for prompt function for dumb terminals.

        Dumb terminals have minimum rendering capabilities. We can only print
        text to the screen. We can't use colors, and we can't do cursor
        movements. The Emacs inferior shell is an example of a dumb terminal.

        We will show the prompt, and wait for the input. We still handle arrow
        keys, and all custom key bindings, but we don't really render the
        cursor movements. Instead we only print the typed character that's
        right before the cursor.
        """
        # Send prompt to output.
        self.output.write(fragment_list_to_text(to_formatted_text(self.message)))
        self.output.flush()

        # Key bindings for the dumb prompt: mostly the same as the full prompt.
        key_bindings: KeyBindingsBase = self._create_prompt_bindings()
        if self.key_bindings:
            key_bindings = merge_key_bindings([self.key_bindings, key_bindings])

        # Create and run application.
        application = cast(
            Application[_T],
            Application(
                input=self.input,
                output=DummyOutput(),
                layout=self.layout,
                key_bindings=key_bindings,
            ),
        )

        def on_text_changed(_: object) -> None:
            self.output.write(self.default_buffer.document.text_before_cursor[-1:])
            self.output.flush()

        self.default_buffer.on_text_changed += on_text_changed

        try:
            yield application
        finally:
            # Render line ending.
            self.output.write("\r\n")
            self.output.flush()

            self.default_buffer.on_text_changed -= on_text_changed

    async def prompt_async(
        self,
        # When any of these arguments are passed, this value is overwritten
        # in this PromptSession.
        message: AnyFormattedText | None = None,
        # `message` should go first, because people call it as
        # positional argument.
        *,
        editing_mode: EditingMode | None = None,
        refresh_interval: float | None = None,
        vi_mode: bool | None = None,
        lexer: Lexer | None = None,
        completer: Completer | None = None,
        complete_in_thread: bool | None = None,
        is_password: bool | None = None,
        key_bindings: KeyBindingsBase | None = None,
        bottom_toolbar: AnyFormattedText | None = None,
        style: BaseStyle | None = None,
        color_depth: ColorDepth | None = None,
        cursor: CursorShapeConfig | None = None,
        include_default_pygments_style: FilterOrBool | None = None,
        style_transformation: StyleTransformation | None = None,
        swap_light_and_dark_colors: FilterOrBool | None = None,
        rprompt: AnyFormattedText | None = None,
        multiline: FilterOrBool | None = None,
        prompt_continuation: PromptContinuationText | None = None,
        wrap_lines: FilterOrBool | None = None,
        enable_history_search: FilterOrBool | None = None,
        search_ignore_case: FilterOrBool | None = None,
        complete_while_typing: FilterOrBool | None = None,
        validate_while_typing: FilterOrBool | None = None,
        complete_style: CompleteStyle | None = None,
        auto_suggest: AutoSuggest | None = None,
        validator: Validator | None = None,
        clipboard: Clipboard | None = None,
        mouse_support: FilterOrBool | None = None,
        input_processors: list[Processor] | None = None,
        placeholder: AnyFormattedText | None = None,
        reserve_space_for_menu: int | None = None,
        enable_system_prompt: FilterOrBool | None = None,
        enable_suspend: FilterOrBool | None = None,
        enable_open_in_editor: FilterOrBool | None = None,
        tempfile_suffix: str | Callable[[], str] | None = None,
        tempfile: str | Callable[[], str] | None = None,
        # Following arguments are specific to the current `prompt()` call.
        default: str | Document = "",
        accept_default: bool = False,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
    ) -> _T:
        if message is not None:
            self.message = message
        if editing_mode is not None:
            self.editing_mode = editing_mode
        if refresh_interval is not None:
            self.refresh_interval = refresh_interval
        if vi_mode:
            self.editing_mode = EditingMode.VI
        if lexer is not None:
            self.lexer = lexer
        if completer is not None:
            self.completer = completer
        if complete_in_thread is not None:
            self.complete_in_thread = complete_in_thread
        if is_password is not None:
            self.is_password = is_password
        if key_bindings is not None:
            self.key_bindings = key_bindings
        if bottom_toolbar is not None:
            self.bottom_toolbar = bottom_toolbar
        if style is not None:
            self.style = style
        if color_depth is not None:
            self.color_depth = color_depth
        if cursor is not None:
            self.cursor = cursor
        if include_default_pygments_style is not None:
            self.include_default_pygments_style = include_default_pygments_style
        if style_transformation is not None:
            self.style_transformation = style_transformation
        if swap_light_and_dark_colors is not None:
            self.swap_light_and_dark_colors = swap_light_and_dark_colors
        if rprompt is not None:
            self.rprompt = rprompt
        if multiline is not None:
            self.multiline = multiline
        if prompt_continuation is not None:
            self.prompt_continuation = prompt_continuation
        if wrap_lines is not None:
            self.wrap_lines = wrap_lines
        if enable_history_search is not None:
            self.enable_history_search = enable_history_search
        if search_ignore_case is not None:
            self.search_ignore_case = search_ignore_case
        if complete_while_typing is not None:
            self.complete_while_typing = complete_while_typing
        if validate_while_typing is not None:
            self.validate_while_typing = validate_while_typing
        if complete_style is not None:
            self.complete_style = complete_style
        if auto_suggest is not None:
            self.auto_suggest = auto_suggest
        if validator is not None:
            self.validator = validator
        if clipboard is not None:
            self.clipboard = clipboard
        if mouse_support is not None:
            self.mouse_support = mouse_support
        if input_processors is not None:
            self.input_processors = input_processors
        if placeholder is not None:
            self.placeholder = placeholder
        if reserve_space_for_menu is not None:
            self.reserve_space_for_menu = reserve_space_for_menu
        if enable_system_prompt is not None:
            self.enable_system_prompt = enable_system_prompt
        if enable_suspend is not None:
            self.enable_suspend = enable_suspend
        if enable_open_in_editor is not None:
            self.enable_open_in_editor = enable_open_in_editor
        if tempfile_suffix is not None:
            self.tempfile_suffix = tempfile_suffix
        if tempfile is not None:
            self.tempfile = tempfile

        self._add_pre_run_callables(pre_run, accept_default)
        self.default_buffer.reset(
            default if isinstance(default, Document) else Document(default)
        )
        self.app.refresh_interval = self.refresh_interval  # This is not reactive.

        # If we are using the default output, and have a dumb terminal. Use the
        # dumb prompt.
        if self._output is None and is_dumb_terminal():
            with self._dumb_prompt(self.message) as dump_app:
                return await dump_app.run_async(handle_sigint=handle_sigint)

        return await self.app.run_async(
            set_exception_handler=set_exception_handler, handle_sigint=handle_sigint
        )

    def _add_pre_run_callables(
        self, pre_run: Callable[[], None] | None, accept_default: bool
    ) -> None:
        def pre_run2() -> None:
            if pre_run:
                pre_run()

            if accept_default:
                # Validate and handle input. We use `call_from_executor` in
                # order to run it "soon" (during the next iteration of the
                # event loop), instead of right now. Otherwise, it won't
                # display the default value.
                get_running_loop().call_soon(self.default_buffer.validate_and_handle)

        self.app.pre_run_callables.append(pre_run2)

    @property
    def editing_mode(self) -> EditingMode:
        return self.app.editing_mode

    @editing_mode.setter
    def editing_mode(self, value: EditingMode) -> None:
        self.app.editing_mode = value

    def _get_default_buffer_control_height(self) -> Dimension:
        # If there is an autocompletion menu to be shown, make sure that our
        # layout has at least a minimal height in order to display it.
        if (
            self.completer is not None
            and self.complete_style != CompleteStyle.READLINE_LIKE
        ):
            space = self.reserve_space_for_menu
        else:
            space = 0

        if space and not get_app().is_done:
            buff = self.default_buffer

            # Reserve the space, either when there are completions, or when
            # `complete_while_typing` is true and we expect completions very
            # soon.
            if buff.complete_while_typing() or buff.complete_state is not None:
                return Dimension(min=space)

        return Dimension()

    def _get_prompt(self) -> StyleAndTextTuples:
        return to_formatted_text(self.message, style="class:prompt")

    def _get_continuation(
        self, width: int, line_number: int, wrap_count: int
    ) -> StyleAndTextTuples:
        """
        Insert the prompt continuation.

        :param width: The width that was used for the prompt. (more or less can
            be used.)
        :param line_number:
        :param wrap_count: Amount of times that the line has been wrapped.
        """
        prompt_continuation = self.prompt_continuation

        if callable(prompt_continuation):
            continuation: AnyFormattedText = prompt_continuation(
                width, line_number, wrap_count
            )
        else:
            continuation = prompt_continuation

        # When the continuation prompt is not given, choose the same width as
        # the actual prompt.
        if continuation is None and is_true(self.multiline):
            continuation = " " * width

        return to_formatted_text(continuation, style="class:prompt-continuation")

    def _get_line_prefix(
        self,
        line_number: int,
        wrap_count: int,
        get_prompt_text_2: _StyleAndTextTuplesCallable,
    ) -> StyleAndTextTuples:
        """
        Return whatever needs to be inserted before every line.
        (the prompt, or a line continuation.)
        """
        # First line: display the "arg" or the prompt.
        if line_number == 0 and wrap_count == 0:
            if not is_true(self.multiline) and get_app().key_processor.arg is not None:
                return self._inline_arg()
            else:
                return get_prompt_text_2()

        # For the next lines, display the appropriate continuation.
        prompt_width = get_cwidth(fragment_list_to_text(get_prompt_text_2()))
        return self._get_continuation(prompt_width, line_number, wrap_count)

    def _get_arg_text(self) -> StyleAndTextTuples:
        "'arg' toolbar, for in multiline mode."
        arg = self.app.key_processor.arg
        if arg is None:
            # Should not happen because of the `has_arg` filter in the layout.
            return []

        if arg == "-":
            arg = "-1"

        return [("class:arg-toolbar", "Repeat: "), ("class:arg-toolbar.text", arg)]

    def _inline_arg(self) -> StyleAndTextTuples:
        "'arg' prefix, for in single line mode."
        app = get_app()
        if app.key_processor.arg is None:
            return []
        else:
            arg = app.key_processor.arg

            return [
                ("class:prompt.arg", "(arg: "),
                ("class:prompt.arg.text", str(arg)),
                ("class:prompt.arg", ") "),
            ]

    # Expose the Input and Output objects as attributes, mainly for
    # backward-compatibility.

    @property
    def input(self) -> Input:
        return self.app.input

    @property
    def output(self) -> Output:
        return self.app.output


def prompt(
    message: AnyFormattedText | None = None,
    *,
    history: History | None = None,
    editing_mode: EditingMode | None = None,
    refresh_interval: float | None = None,
    vi_mode: bool | None = None,
    lexer: Lexer | None = None,
    completer: Completer | None = None,
    complete_in_thread: bool | None = None,
    is_password: bool | None = None,
    key_bindings: KeyBindingsBase | None = None,
    bottom_toolbar: AnyFormattedText | None = None,
    style: BaseStyle | None = None,
    color_depth: ColorDepth | None = None,
    cursor: AnyCursorShapeConfig = None,
    include_default_pygments_style: FilterOrBool | None = None,
    style_transformation: StyleTransformation | None = None,
    swap_light_and_dark_colors: FilterOrBool | None = None,
    rprompt: AnyFormattedText | None = None,
    multiline: FilterOrBool | None = None,
    prompt_continuation: PromptContinuationText | None = None,
    wrap_lines: FilterOrBool | None = None,
    enable_history_search: FilterOrBool | None = None,
    search_ignore_case: FilterOrBool | None = None,
    complete_while_typing: FilterOrBool | None = None,
    validate_while_typing: FilterOrBool | None = None,
    complete_style: CompleteStyle | None = None,
    auto_suggest: AutoSuggest | None = None,
    validator: Validator | None = None,
    clipboard: Clipboard | None = None,
    mouse_support: FilterOrBool | None = None,
    input_processors: list[Processor] | None = None,
    placeholder: AnyFormattedText | None = None,
    reserve_space_for_menu: int | None = None,
    enable_system_prompt: FilterOrBool | None = None,
    enable_suspend: FilterOrBool | None = None,
    enable_open_in_editor: FilterOrBool | None = None,
    tempfile_suffix: str | Callable[[], str] | None = None,
    tempfile: str | Callable[[], str] | None = None,
    # Following arguments are specific to the current `prompt()` call.
    default: str = "",
    accept_default: bool = False,
    pre_run: Callable[[], None] | None = None,
    set_exception_handler: bool = True,
    handle_sigint: bool = True,
    in_thread: bool = False,
    inputhook: InputHook | None = None,
) -> str:
    """
    The global `prompt` function. This will create a new `PromptSession`
    instance for every call.
    """
    # The history is the only attribute that has to be passed to the
    # `PromptSession`, it can't be passed into the `prompt()` method.
    session: PromptSession[str] = PromptSession(history=history)

    return session.prompt(
        message,
        editing_mode=editing_mode,
        refresh_interval=refresh_interval,
        vi_mode=vi_mode,
        lexer=lexer,
        completer=completer,
        complete_in_thread=complete_in_thread,
        is_password=is_password,
        key_bindings=key_bindings,
        bottom_toolbar=bottom_toolbar,
        style=style,
        color_depth=color_depth,
        cursor=cursor,
        include_default_pygments_style=include_default_pygments_style,
        style_transformation=style_transformation,
        swap_light_and_dark_colors=swap_light_and_dark_colors,
        rprompt=rprompt,
        multiline=multiline,
        prompt_continuation=prompt_continuation,
        wrap_lines=wrap_lines,
        enable_history_search=enable_history_search,
        search_ignore_case=search_ignore_case,
        complete_while_typing=complete_while_typing,
        validate_while_typing=validate_while_typing,
        complete_style=complete_style,
        auto_suggest=auto_suggest,
        validator=validator,
        clipboard=clipboard,
        mouse_support=mouse_support,
        input_processors=input_processors,
        placeholder=placeholder,
        reserve_space_for_menu=reserve_space_for_menu,
        enable_system_prompt=enable_system_prompt,
        enable_suspend=enable_suspend,
        enable_open_in_editor=enable_open_in_editor,
        tempfile_suffix=tempfile_suffix,
        tempfile=tempfile,
        default=default,
        accept_default=accept_default,
        pre_run=pre_run,
        set_exception_handler=set_exception_handler,
        handle_sigint=handle_sigint,
        in_thread=in_thread,
        inputhook=inputhook,
    )


prompt.__doc__ = PromptSession.prompt.__doc__


def create_confirm_session(
    message: str, suffix: str = " (y/n) "
) -> PromptSession[bool]:
    """
    Create a `PromptSession` object for the 'confirm' function.
    """
    bindings = KeyBindings()

    @bindings.add("y")
    @bindings.add("Y")
    def yes(event: E) -> None:
        session.default_buffer.text = "y"
        event.app.exit(result=True)

    @bindings.add("n")
    @bindings.add("N")
    def no(event: E) -> None:
        session.default_buffer.text = "n"
        event.app.exit(result=False)

    @bindings.add(Keys.Any)
    def _(event: E) -> None:
        "Disallow inserting other text."
        pass

    complete_message = merge_formatted_text([message, suffix])
    session: PromptSession[bool] = PromptSession(
        complete_message, key_bindings=bindings
    )
    return session


def confirm(message: str = "Confirm?", suffix: str = " (y/n) ") -> bool:
    """
    Display a confirmation prompt that returns True/False.
    """
    session = create_confirm_session(message, suffix)
    return session.prompt()

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\generative_service\client.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from collections import OrderedDict
import os
import re
from typing import (
    Callable,
    Dict,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1.types import content
from google.ai.generativelanguage_v1.types import content as gag_content
from google.ai.generativelanguage_v1.types import generative_service

from .transports.base import DEFAULT_CLIENT_INFO, GenerativeServiceTransport
from .transports.grpc import GenerativeServiceGrpcTransport
from .transports.grpc_asyncio import GenerativeServiceGrpcAsyncIOTransport
from .transports.rest import GenerativeServiceRestTransport


class GenerativeServiceClientMeta(type):
    """Metaclass for the GenerativeService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = (
        OrderedDict()
    )  # type: Dict[str, Type[GenerativeServiceTransport]]
    _transport_registry["grpc"] = GenerativeServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = GenerativeServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = GenerativeServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[GenerativeServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class GenerativeServiceClient(metaclass=GenerativeServiceClientMeta):
    """API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            GenerativeServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            GenerativeServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> GenerativeServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            GenerativeServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = GenerativeServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = GenerativeServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = GenerativeServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = GenerativeServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = GenerativeServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or GenerativeServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[
                str,
                GenerativeServiceTransport,
                Callable[..., GenerativeServiceTransport],
            ]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the generative service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,GenerativeServiceTransport,Callable[..., GenerativeServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the GenerativeServiceTransport constructor.
                If set to None, a transport is chosen automatically.
            client_options (Optional[Union[google.api_core.client_options.ClientOptions, dict]]):
                Custom options for the client.

                1. The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client when ``transport`` is
                not explicitly provided. Only if this property is not set and
                ``transport`` was not explicitly provided, the endpoint is
                determined by the GOOGLE_API_USE_MTLS_ENDPOINT environment
                variable, which have one of the following values:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto-switch to the
                default mTLS endpoint if client certificate is present; this is
                the default value).

                2. If the GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide a client certificate for mTLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

                3. The ``universe_domain`` property can be used to override the
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = GenerativeServiceClient._read_environment_variables()
        self._client_cert_source = GenerativeServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = GenerativeServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, GenerativeServiceTransport)
        if transport_provided:
            # transport is a GenerativeServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(GenerativeServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = (
            self._api_endpoint
            or GenerativeServiceClient._get_api_endpoint(
                self._client_options.api_endpoint,
                self._client_cert_source,
                self._universe_domain,
                self._use_mtls_endpoint,
            )
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[GenerativeServiceTransport],
                Callable[..., GenerativeServiceTransport],
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., GenerativeServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def generate_content(
        self,
        request: Optional[
            Union[generative_service.GenerateContentRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.GenerateContentResponse:
        r"""Generates a response from the model given an input
        ``GenerateContentRequest``.

        Input capabilities differ between models, including tuned
        models. See the `model
        guide <https://ai.google.dev/models/gemini>`__ and `tuning
        guide <https://ai.google.dev/docs/model_tuning_guidance>`__ for
        details.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            def sample_generate_content():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.GenerateContentRequest(
                    model="model_value",
                )

                # Make the request
                response = client.generate_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1.types.GenerateContentRequest, dict]):
                The request object. Request to generate a completion from
                the model.
            model (str):
                Required. The name of the ``Model`` to use for
                generating the completion.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (MutableSequence[google.ai.generativelanguage_v1.types.Content]):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.GenerateContentResponse:
                Response from the model supporting multiple candidates.

                   Note on safety ratings and content filtering. They
                   are reported for both prompt in
                   GenerateContentResponse.prompt_feedback and for each
                   candidate in finish_reason and in safety_ratings. The
                   API contract is that: - either all requested
                   candidates are returned or no candidates at all - no
                   candidates are returned only if there was something
                   wrong with the prompt (see prompt_feedback) -
                   feedback on each candidate is reported on
                   finish_reason and safety_ratings.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateContentRequest):
            request = generative_service.GenerateContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if contents is not None:
                request.contents = contents

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.generate_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def stream_generate_content(
        self,
        request: Optional[
            Union[generative_service.GenerateContentRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> Iterable[generative_service.GenerateContentResponse]:
        r"""Generates a streamed response from the model given an input
        ``GenerateContentRequest``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            def sample_stream_generate_content():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.GenerateContentRequest(
                    model="model_value",
                )

                # Make the request
                stream = client.stream_generate_content(request=request)

                # Handle the response
                for response in stream:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1.types.GenerateContentRequest, dict]):
                The request object. Request to generate a completion from
                the model.
            model (str):
                Required. The name of the ``Model`` to use for
                generating the completion.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (MutableSequence[google.ai.generativelanguage_v1.types.Content]):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            Iterable[google.ai.generativelanguage_v1.types.GenerateContentResponse]:
                Response from the model supporting multiple candidates.

                   Note on safety ratings and content filtering. They
                   are reported for both prompt in
                   GenerateContentResponse.prompt_feedback and for each
                   candidate in finish_reason and in safety_ratings. The
                   API contract is that: - either all requested
                   candidates are returned or no candidates at all - no
                   candidates are returned only if there was something
                   wrong with the prompt (see prompt_feedback) -
                   feedback on each candidate is reported on
                   finish_reason and safety_ratings.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.GenerateContentRequest):
            request = generative_service.GenerateContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if contents is not None:
                request.contents = contents

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.stream_generate_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def embed_content(
        self,
        request: Optional[Union[generative_service.EmbedContentRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        content: Optional[gag_content.Content] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.EmbedContentResponse:
        r"""Generates an embedding from the model given an input
        ``Content``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            def sample_embed_content():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.EmbedContentRequest(
                    model="model_value",
                )

                # Make the request
                response = client.embed_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1.types.EmbedContentRequest, dict]):
                The request object. Request containing the ``Content`` for the model to
                embed.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            content (google.ai.generativelanguage_v1.types.Content):
                Required. The content to embed. Only the ``parts.text``
                fields will be counted.

                This corresponds to the ``content`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.EmbedContentResponse:
                The response to an EmbedContentRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, content])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.EmbedContentRequest):
            request = generative_service.EmbedContentRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if content is not None:
                request.content = content

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.embed_content]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def batch_embed_contents(
        self,
        request: Optional[
            Union[generative_service.BatchEmbedContentsRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        requests: Optional[
            MutableSequence[generative_service.EmbedContentRequest]
        ] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.BatchEmbedContentsResponse:
        r"""Generates multiple embeddings from the model given
        input text in a synchronous call.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            def sample_batch_embed_contents():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1.EmbedContentRequest()
                requests.model = "model_value"

                request = generativelanguage_v1.BatchEmbedContentsRequest(
                    model="model_value",
                    requests=requests,
                )

                # Make the request
                response = client.batch_embed_contents(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1.types.BatchEmbedContentsRequest, dict]):
                The request object. Batch request to get embeddings from
                the model for a list of prompts.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            requests (MutableSequence[google.ai.generativelanguage_v1.types.EmbedContentRequest]):
                Required. Embed requests for the batch. The model in
                each of these requests must match the model specified
                ``BatchEmbedContentsRequest.model``.

                This corresponds to the ``requests`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.BatchEmbedContentsResponse:
                The response to a BatchEmbedContentsRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, requests])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.BatchEmbedContentsRequest):
            request = generative_service.BatchEmbedContentsRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if requests is not None:
                request.requests = requests

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.batch_embed_contents]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def count_tokens(
        self,
        request: Optional[Union[generative_service.CountTokensRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        contents: Optional[MutableSequence[content.Content]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> generative_service.CountTokensResponse:
        r"""Runs a model's tokenizer on input content and returns
        the token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            def sample_count_tokens():
                # Create a client
                client = generativelanguage_v1.GenerativeServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.CountTokensRequest(
                    model="model_value",
                )

                # Make the request
                response = client.count_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1.types.CountTokensRequest, dict]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (MutableSequence[google.ai.generativelanguage_v1.types.Content]):
                Optional. The input given to the model as a prompt. This
                field is ignored when ``generate_content_request`` is
                set.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.CountTokensResponse:
                A response from CountTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, generative_service.CountTokensRequest):
            request = generative_service.CountTokensRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if contents is not None:
                request.contents = contents

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.count_tokens]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def __enter__(self) -> "GenerativeServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()

    def list_operations(
        self,
        request: Optional[operations_pb2.ListOperationsRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.ListOperationsResponse:
        r"""Lists operations that match the specified filter in the request.

        Args:
            request (:class:`~.operations_pb2.ListOperationsRequest`):
                The request object. Request message for
                `ListOperations` method.
            retry (google.api_core.retry.Retry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            ~.operations_pb2.ListOperationsResponse:
                Response message for ``ListOperations`` method.
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.ListOperationsRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method.wrap_method(
            self._transport.list_operations,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def get_operation(
        self,
        request: Optional[operations_pb2.GetOperationRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.Operation:
        r"""Gets the latest state of a long-running operation.

        Args:
            request (:class:`~.operations_pb2.GetOperationRequest`):
                The request object. Request message for
                `GetOperation` method.
            retry (google.api_core.retry.Retry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            ~.operations_pb2.Operation:
                An ``Operation`` object.
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.GetOperationRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method.wrap_method(
            self._transport.get_operation,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def cancel_operation(
        self,
        request: Optional[operations_pb2.CancelOperationRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Starts asynchronous cancellation on a long-running operation.

        The server makes a best effort to cancel the operation, but success
        is not guaranteed.  If the server doesn't support this method, it returns
        `google.rpc.Code.UNIMPLEMENTED`.

        Args:
            request (:class:`~.operations_pb2.CancelOperationRequest`):
                The request object. Request message for
                `CancelOperation` method.
            retry (google.api_core.retry.Retry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            None
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.CancelOperationRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method.wrap_method(
            self._transport.cancel_operation,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("GenerativeServiceClient",)