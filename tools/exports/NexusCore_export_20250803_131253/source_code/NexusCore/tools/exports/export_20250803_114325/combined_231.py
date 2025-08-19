
# === NexusCore/tools\backup_tool.py ===
# ==============================================================================
# フォルダ: scripts
# ファイル名: backup_tool.py
# メモ: Gitリポジトリを効率的にバックアップし、世代管理も行うツール。【バグ修正版 v3】
# ==============================================================================

import os
import re
import subprocess
import logging
from datetime import datetime, timedelta

# ==============================================================================
# 設定項目
# ==============================================================================

# バックアップ対象のプロジェクト（Gitリポジトリ）のフルパスを指定
# raw文字列(r"...")を使うことで、パス区切り文字(\)を気にせず記述できます
SOURCE_DIRECTORIES = [
    r"C:\Users\USER\tools\NexusCore",
]

# バックアップファイルの保存先ディレクトリのフルパスを指定
# フォルダ名にスペースを含めないことで、予期せぬエラーを防ぎます
BACKUP_DESTINATION = r"C:\Users\USER\tools\BackupNexusCore"

# バックアップファイルを保持する日数（この日数を超えた古いファイルは自動で削除されます）
RETENTION_DAYS = 30

# ログファイルの保存先ディレクトリ
LOG_DIRECTORY = os.path.join(BACKUP_DESTINATION, "logs")

# ==============================================================================
# スクリプト本体
# ==============================================================================

def setup_logging():
    """ロギング機能のセットアップ"""
    os.makedirs(LOG_DIRECTORY, exist_ok=True)
    log_file = os.path.join(LOG_DIRECTORY, f"backup_{datetime.now():%Y-%m-%d}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def sanitize_filename(name: str) -> str:
    """ファイル名に使用できない文字を除去・置換する"""
    # Windows/Linuxなどでファイル名として使えない文字をアンダースコアに置換
    invalid_chars = r'[<>:"/\\|?*\s]'
    return re.sub(invalid_chars, '_', name)

def create_git_bundle(repo_path: str, dest_dir: str) -> bool:
    """
    指定されたGitリポジトリのバンドルファイルを作成する。
    """
    repo_name = sanitize_filename(os.path.basename(repo_path))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_filename = f"{repo_name}_{timestamp}.bundle"
    bundle_filepath = os.path.join(dest_dir, bundle_filename)

    logging.info(f"リポジトリ '{repo_name}' のバックアップを開始します...")

    # .gitディレクトリの存在確認を強化
    git_dir = os.path.join(repo_path, ".git")
    if not (os.path.isdir(git_dir) or os.path.isfile(git_dir)):
        logging.error(f"'{repo_path}' はGitリポジトリではありません。スキップします。")
        return False

    try:
        # git bundleコマンド実行
        cmd = ["git", "bundle", "create", bundle_filepath, "--all"]
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            timeout=300  # 5分のタイムアウトを追加。巨大なリポジトリでもハングしないようにする
        )
        
        # バンドルファイルのサイズ確認
        if os.path.exists(bundle_filepath):
            file_size = os.path.getsize(bundle_filepath)
            if file_size == 0:
                logging.error(f"生成されたバンドルファイルが空です。削除します: {bundle_filepath}")
                os.remove(bundle_filepath)
                return False
            
            logging.info(f"バンドルファイルを作成しました: {bundle_filepath} ({file_size:,} bytes)")
        
        return True
        
    except subprocess.TimeoutExpired:
        logging.error(f"バンドル作成がタイムアウトしました（5分以上経過）: {repo_name}")
        return False
    except FileNotFoundError:
        logging.error("'git' コマンドが見つかりません。Gitがインストールされ、PATHが通っているか確認してください。")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"バンドルファイルの作成に失敗しました: {repo_name}")
        logging.error(f"リターンコード: {e.returncode}")
        logging.error(f"エラー出力:\n{e.stderr}")
        return False
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)
        return False

def rotate_backups(dest_dir: str):
    """指定されたディレクトリ内の古いバックアップファイルを削除する"""
    logging.info(f"バックアップの世代管理を開始します (保持期間: {RETENTION_DAYS}日)...")
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    
    try:
        bundle_files = [f for f in os.listdir(dest_dir) if f.endswith(".bundle")]
        
        for filename in bundle_files:
            filepath = os.path.join(dest_dir, filename)
            
            # より厳密な正規表現による日付抽出
            match = re.search(r'_(\d{8})_\d{6}\.bundle$', filename)
            
            if not match:
                logging.warning(f"ファイル名の形式が不正です。スキップします: {filename}")
                continue
            
            try:
                date_str = match.group(1)
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    logging.info(f"古いバックアップファイルを削除します: {filename}")
                    os.remove(filepath)
                else:
                    logging.debug(f"保持対象のファイルです: {filename}")

            except ValueError as e:
                logging.error(f"ファイル名に含まれる日付の解析に失敗しました ({filename}): {e}")
            except Exception as e:
                logging.error(f"ファイル処理中に予期せぬエラーが発生しました ({filename}): {e}")

    except FileNotFoundError:
        logging.warning(f"バックアップディレクトリが見つかりません: {dest_dir}")
    except Exception as e:
        logging.error(f"世代管理中に予期せぬエラーが発生しました: {e}", exc_info=True)

def main():
    """メイン処理"""
    setup_logging()
    logging.info("================ バックアップ処理開始 ================")

    # バックアップ先ディレクトリの作成
    try:
        os.makedirs(BACKUP_DESTINATION, exist_ok=True)
        logging.info(f"バックアップ先ディレクトリ: {BACKUP_DESTINATION}")
    except Exception as e:
        logging.critical(f"バックアップ先ディレクトリの作成に失敗しました: {e}")
        return

    # 各リポジトリのバックアップ実行
    success_count = 0
    for src_dir in SOURCE_DIRECTORIES:
        if not os.path.isdir(src_dir):
            logging.warning(f"指定されたソースディレクトリが見つかりません: {src_dir}")
            continue
            
        if create_git_bundle(src_dir, BACKUP_DESTINATION):
            success_count += 1

    logging.info(f"バックアップ作成完了 ({success_count}/{len(SOURCE_DIRECTORIES)}件 成功)")

    # 古いバックアップの削除
    rotate_backups(BACKUP_DESTINATION)

    logging.info("================ バックアップ処理終了 ================")

if __name__ == "__main__":
    main()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\wheel.py ===
import logging
import os
import shutil
from optparse import Values
from typing import List

from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.req_command import RequirementCommand, with_cleanup
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.exceptions import CommandError
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.req.req_install import (
    InstallRequirement,
    check_legacy_setup_py_options,
)
from pip._internal.utils.misc import ensure_dir, normalize_path
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.wheel_builder import build, should_build_for_wheel_command

logger = logging.getLogger(__name__)


class WheelCommand(RequirementCommand):
    """
    Build Wheel archives for your requirements and dependencies.

    Wheel is a built-package format, and offers the advantage of not
    recompiling your software during every install. For more details, see the
    wheel docs: https://wheel.readthedocs.io/en/latest/

    'pip wheel' uses the build system interface as described here:
    https://pip.pypa.io/en/stable/reference/build-system/

    """

    usage = """
      %prog [options] <requirement specifier> ...
      %prog [options] -r <requirements file> ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-w",
            "--wheel-dir",
            dest="wheel_dir",
            metavar="dir",
            default=os.curdir,
            help=(
                "Build wheels into <dir>, where the default is the "
                "current working directory."
            ),
        )
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())
        self.cmd_opts.add_option(cmdoptions.prefer_binary())
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.use_pep517())
        self.cmd_opts.add_option(cmdoptions.no_use_pep517())
        self.cmd_opts.add_option(cmdoptions.check_build_deps())
        self.cmd_opts.add_option(cmdoptions.constraints())
        self.cmd_opts.add_option(cmdoptions.editable())
        self.cmd_opts.add_option(cmdoptions.requirements())
        self.cmd_opts.add_option(cmdoptions.src())
        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())
        self.cmd_opts.add_option(cmdoptions.no_deps())
        self.cmd_opts.add_option(cmdoptions.progress_bar())

        self.cmd_opts.add_option(
            "--no-verify",
            dest="no_verify",
            action="store_true",
            default=False,
            help="Don't verify if built wheel is valid.",
        )

        self.cmd_opts.add_option(cmdoptions.config_settings())
        self.cmd_opts.add_option(cmdoptions.build_options())
        self.cmd_opts.add_option(cmdoptions.global_options())

        self.cmd_opts.add_option(
            "--pre",
            action="store_true",
            default=False,
            help=(
                "Include pre-release and development versions. By default, "
                "pip only finds stable versions."
            ),
        )

        self.cmd_opts.add_option(cmdoptions.require_hashes())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    @with_cleanup
    def run(self, options: Values, args: List[str]) -> int:
        session = self.get_default_session(options)

        finder = self._build_package_finder(options, session)

        options.wheel_dir = normalize_path(options.wheel_dir)
        ensure_dir(options.wheel_dir)

        build_tracker = self.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="wheel",
            globally_managed=True,
        )

        reqs = self.get_requirements(args, options, finder, session)
        check_legacy_setup_py_options(options, reqs)

        wheel_cache = WheelCache(options.cache_dir)

        preparer = self.make_requirement_preparer(
            temp_build_dir=directory,
            options=options,
            build_tracker=build_tracker,
            session=session,
            finder=finder,
            download_dir=options.wheel_dir,
            use_user_site=False,
            verbosity=self.verbosity,
        )

        resolver = self.make_resolver(
            preparer=preparer,
            finder=finder,
            options=options,
            wheel_cache=wheel_cache,
            ignore_requires_python=options.ignore_requires_python,
            use_pep517=options.use_pep517,
        )

        self.trace_basic_info(finder)

        requirement_set = resolver.resolve(reqs, check_supported_wheels=True)

        reqs_to_build: List[InstallRequirement] = []
        for req in requirement_set.requirements.values():
            if req.is_wheel:
                preparer.save_linked_requirement(req)
            elif should_build_for_wheel_command(req):
                reqs_to_build.append(req)

        preparer.prepare_linked_requirements_more(requirement_set.requirements.values())

        # build wheels
        build_successes, build_failures = build(
            reqs_to_build,
            wheel_cache=wheel_cache,
            verify=(not options.no_verify),
            build_options=options.build_options or [],
            global_options=options.global_options or [],
        )
        for req in build_successes:
            assert req.link and req.link.is_wheel
            assert req.local_file_path
            # copy from cache to target directory
            try:
                shutil.copy(req.local_file_path, options.wheel_dir)
            except OSError as e:
                logger.warning(
                    "Building wheel for %s failed: %s",
                    req.name,
                    e,
                )
                build_failures.append(req)
        if len(build_failures) != 0:
            raise CommandError("Failed to build one or more wheels")

        return SUCCESS

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\cachecontrol\caches\file_cache.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import os
from textwrap import dedent
from typing import IO, TYPE_CHECKING
from pathlib import Path

from pip._vendor.cachecontrol.cache import BaseCache, SeparateBodyBaseCache
from pip._vendor.cachecontrol.controller import CacheController

if TYPE_CHECKING:
    from datetime import datetime

    from filelock import BaseFileLock


def _secure_open_write(filename: str, fmode: int) -> IO[bytes]:
    # We only want to write to this file, so open it in write only mode
    flags = os.O_WRONLY

    # os.O_CREAT | os.O_EXCL will fail if the file already exists, so we only
    #  will open *new* files.
    # We specify this because we want to ensure that the mode we pass is the
    # mode of the file.
    flags |= os.O_CREAT | os.O_EXCL

    # Do not follow symlinks to prevent someone from making a symlink that
    # we follow and insecurely open a cache file.
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    # On Windows we'll mark this file as binary
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    # Before we open our file, we want to delete any existing file that is
    # there
    try:
        os.remove(filename)
    except OSError:
        # The file must not exist already, so we can just skip ahead to opening
        pass

    # Open our file, the use of os.O_CREAT | os.O_EXCL will ensure that if a
    # race condition happens between the os.remove and this line, that an
    # error will be raised. Because we utilize a lockfile this should only
    # happen if someone is attempting to attack us.
    fd = os.open(filename, flags, fmode)
    try:
        return os.fdopen(fd, "wb")

    except:
        # An error occurred wrapping our FD in a file object
        os.close(fd)
        raise


class _FileCacheMixin:
    """Shared implementation for both FileCache variants."""

    def __init__(
        self,
        directory: str | Path,
        forever: bool = False,
        filemode: int = 0o0600,
        dirmode: int = 0o0700,
        lock_class: type[BaseFileLock] | None = None,
    ) -> None:
        try:
            if lock_class is None:
                from filelock import FileLock

                lock_class = FileLock
        except ImportError:
            notice = dedent(
                """
            NOTE: In order to use the FileCache you must have
            filelock installed. You can install it via pip:
              pip install cachecontrol[filecache]
            """
            )
            raise ImportError(notice)

        self.directory = directory
        self.forever = forever
        self.filemode = filemode
        self.dirmode = dirmode
        self.lock_class = lock_class

    @staticmethod
    def encode(x: str) -> str:
        return hashlib.sha224(x.encode()).hexdigest()

    def _fn(self, name: str) -> str:
        # NOTE: This method should not change as some may depend on it.
        #       See: https://github.com/ionrock/cachecontrol/issues/63
        hashed = self.encode(name)
        parts = list(hashed[:5]) + [hashed]
        return os.path.join(self.directory, *parts)

    def get(self, key: str) -> bytes | None:
        name = self._fn(key)
        try:
            with open(name, "rb") as fh:
                return fh.read()

        except FileNotFoundError:
            return None

    def set(
        self, key: str, value: bytes, expires: int | datetime | None = None
    ) -> None:
        name = self._fn(key)
        self._write(name, value)

    def _write(self, path: str, data: bytes) -> None:
        """
        Safely write the data to the given path.
        """
        # Make sure the directory exists
        try:
            os.makedirs(os.path.dirname(path), self.dirmode)
        except OSError:
            pass

        with self.lock_class(path + ".lock"):
            # Write our actual file
            with _secure_open_write(path, self.filemode) as fh:
                fh.write(data)

    def _delete(self, key: str, suffix: str) -> None:
        name = self._fn(key) + suffix
        if not self.forever:
            try:
                os.remove(name)
            except FileNotFoundError:
                pass


class FileCache(_FileCacheMixin, BaseCache):
    """
    Traditional FileCache: body is stored in memory, so not suitable for large
    downloads.
    """

    def delete(self, key: str) -> None:
        self._delete(key, "")


class SeparateBodyFileCache(_FileCacheMixin, SeparateBodyBaseCache):
    """
    Memory-efficient FileCache: body is stored in a separate file, reducing
    peak memory usage.
    """

    def get_body(self, key: str) -> IO[bytes] | None:
        name = self._fn(key) + ".body"
        try:
            return open(name, "rb")
        except FileNotFoundError:
            return None

    def set_body(self, key: str, body: bytes) -> None:
        name = self._fn(key) + ".body"
        self._write(name, body)

    def delete(self, key: str) -> None:
        self._delete(key, "")
        self._delete(key, ".body")


def url_to_file_path(url: str, filecache: FileCache) -> str:
    """Return the file cache path based on the URL.

    This does not ensure the file exists!
    """
    key = CacheController.cache_url(url)
    return filecache._fn(key)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\cached_content.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

from google.protobuf import duration_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore
import proto  # type: ignore

from google.ai.generativelanguage_v1beta.types import content

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "CachedContent",
    },
)


class CachedContent(proto.Message):
    r"""Content that has been preprocessed and can be used in
    subsequent request to GenerativeService.

    Cached content can be only used with model it was created for.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        expire_time (google.protobuf.timestamp_pb2.Timestamp):
            Timestamp in UTC of when this resource is considered
            expired. This is *always* provided on output, regardless of
            what was sent on input.

            This field is a member of `oneof`_ ``expiration``.
        ttl (google.protobuf.duration_pb2.Duration):
            Input only. New TTL for this resource, input
            only.

            This field is a member of `oneof`_ ``expiration``.
        name (str):
            Optional. Identifier. The resource name referring to the
            cached content. Format: ``cachedContents/{id}``

            This field is a member of `oneof`_ ``_name``.
        display_name (str):
            Optional. Immutable. The user-generated
            meaningful display name of the cached content.
            Maximum 128 Unicode characters.

            This field is a member of `oneof`_ ``_display_name``.
        model (str):
            Required. Immutable. The name of the ``Model`` to use for
            cached content Format: ``models/{model}``

            This field is a member of `oneof`_ ``_model``.
        system_instruction (google.ai.generativelanguage_v1beta.types.Content):
            Optional. Input only. Immutable. Developer
            set system instruction. Currently text only.

            This field is a member of `oneof`_ ``_system_instruction``.
        contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
            Optional. Input only. Immutable. The content
            to cache.
        tools (MutableSequence[google.ai.generativelanguage_v1beta.types.Tool]):
            Optional. Input only. Immutable. A list of ``Tools`` the
            model may use to generate the next response
        tool_config (google.ai.generativelanguage_v1beta.types.ToolConfig):
            Optional. Input only. Immutable. Tool config.
            This config is shared for all tools.

            This field is a member of `oneof`_ ``_tool_config``.
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. Creation time of the cache
            entry.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. When the cache entry was last
            updated in UTC time.
        usage_metadata (google.ai.generativelanguage_v1beta.types.CachedContent.UsageMetadata):
            Output only. Metadata on the usage of the
            cached content.
    """

    class UsageMetadata(proto.Message):
        r"""Metadata on the usage of the cached content.

        Attributes:
            total_token_count (int):
                Total number of tokens that the cached
                content consumes.
        """

        total_token_count: int = proto.Field(
            proto.INT32,
            number=1,
        )

    expire_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=9,
        oneof="expiration",
        message=timestamp_pb2.Timestamp,
    )
    ttl: duration_pb2.Duration = proto.Field(
        proto.MESSAGE,
        number=10,
        oneof="expiration",
        message=duration_pb2.Duration,
    )
    name: str = proto.Field(
        proto.STRING,
        number=1,
        optional=True,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=11,
        optional=True,
    )
    model: str = proto.Field(
        proto.STRING,
        number=2,
        optional=True,
    )
    system_instruction: content.Content = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=content.Content,
    )
    contents: MutableSequence[content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=4,
        message=content.Content,
    )
    tools: MutableSequence[content.Tool] = proto.RepeatedField(
        proto.MESSAGE,
        number=5,
        message=content.Tool,
    )
    tool_config: content.ToolConfig = proto.Field(
        proto.MESSAGE,
        number=6,
        optional=True,
        message=content.ToolConfig,
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=7,
        message=timestamp_pb2.Timestamp,
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=8,
        message=timestamp_pb2.Timestamp,
    )
    usage_metadata: UsageMetadata = proto.Field(
        proto.MESSAGE,
        number=12,
        message=UsageMetadata,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\litellm\batches\batch_utils.py ===
import json
from typing import Any, List, Literal, Tuple

import litellm
from litellm._logging import verbose_logger
from litellm.types.llms.openai import Batch
from litellm.types.utils import CallTypes, Usage


async def _handle_completed_batch(
    batch: Batch,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"],
) -> Tuple[float, Usage, List[str]]:
    """Helper function to process a completed batch and handle logging"""
    # Get batch results
    file_content_dictionary = await _get_batch_output_file_content_as_dictionary(
        batch, custom_llm_provider
    )

    # Calculate costs and usage
    batch_cost = await _batch_cost_calculator(
        custom_llm_provider=custom_llm_provider,
        file_content_dictionary=file_content_dictionary,
    )
    batch_usage = _get_batch_job_total_usage_from_file_content(
        file_content_dictionary=file_content_dictionary,
        custom_llm_provider=custom_llm_provider,
    )

    batch_models = _get_batch_models_from_file_content(file_content_dictionary)

    return batch_cost, batch_usage, batch_models


def _get_batch_models_from_file_content(
    file_content_dictionary: List[dict],
) -> List[str]:
    """
    Get the models from the file content
    """
    batch_models = []
    for _item in file_content_dictionary:
        if _batch_response_was_successful(_item):
            _response_body = _get_response_from_batch_job_output_file(_item)
            _model = _response_body.get("model")
            if _model:
                batch_models.append(_model)
    return batch_models


async def _batch_cost_calculator(
    file_content_dictionary: List[dict],
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
) -> float:
    """
    Calculate the cost of a batch based on the output file id
    """
    if custom_llm_provider == "vertex_ai":
        raise ValueError("Vertex AI does not support file content retrieval")
    total_cost = _get_batch_job_cost_from_file_content(
        file_content_dictionary=file_content_dictionary,
        custom_llm_provider=custom_llm_provider,
    )
    verbose_logger.debug("total_cost=%s", total_cost)
    return total_cost


async def _get_batch_output_file_content_as_dictionary(
    batch: Batch,
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
) -> List[dict]:
    """
    Get the batch output file content as a list of dictionaries
    """
    from litellm.files.main import afile_content

    if custom_llm_provider == "vertex_ai":
        raise ValueError("Vertex AI does not support file content retrieval")

    if batch.output_file_id is None:
        raise ValueError("Output file id is None cannot retrieve file content")

    _file_content = await afile_content(
        file_id=batch.output_file_id,
        custom_llm_provider=custom_llm_provider,
    )
    return _get_file_content_as_dictionary(_file_content.content)


def _get_file_content_as_dictionary(file_content: bytes) -> List[dict]:
    """
    Get the file content as a list of dictionaries from JSON Lines format
    """
    try:
        _file_content_str = file_content.decode("utf-8")
        # Split by newlines and parse each line as a separate JSON object
        json_objects = []
        for line in _file_content_str.strip().split("\n"):
            if line:  # Skip empty lines
                json_objects.append(json.loads(line))
        verbose_logger.debug("json_objects=%s", json.dumps(json_objects, indent=4))
        return json_objects
    except Exception as e:
        raise e


def _get_batch_job_cost_from_file_content(
    file_content_dictionary: List[dict],
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
) -> float:
    """
    Get the cost of a batch job from the file content
    """
    try:
        total_cost: float = 0.0
        # parse the file content as json
        verbose_logger.debug(
            "file_content_dictionary=%s", json.dumps(file_content_dictionary, indent=4)
        )
        for _item in file_content_dictionary:
            if _batch_response_was_successful(_item):
                _response_body = _get_response_from_batch_job_output_file(_item)
                total_cost += litellm.completion_cost(
                    completion_response=_response_body,
                    custom_llm_provider=custom_llm_provider,
                    call_type=CallTypes.aretrieve_batch.value,
                )
                verbose_logger.debug("total_cost=%s", total_cost)
        return total_cost
    except Exception as e:
        verbose_logger.error("error in _get_batch_job_cost_from_file_content", e)
        raise e


def _get_batch_job_total_usage_from_file_content(
    file_content_dictionary: List[dict],
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
) -> Usage:
    """
    Get the tokens of a batch job from the file content
    """
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    for _item in file_content_dictionary:
        if _batch_response_was_successful(_item):
            _response_body = _get_response_from_batch_job_output_file(_item)
            usage: Usage = _get_batch_job_usage_from_response_body(_response_body)
            total_tokens += usage.total_tokens
            prompt_tokens += usage.prompt_tokens
            completion_tokens += usage.completion_tokens
    return Usage(
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def _get_batch_job_usage_from_response_body(response_body: dict) -> Usage:
    """
    Get the tokens of a batch job from the response body
    """
    _usage_dict = response_body.get("usage", None) or {}
    usage: Usage = Usage(**_usage_dict)
    return usage


def _get_response_from_batch_job_output_file(batch_job_output_file: dict) -> Any:
    """
    Get the response from the batch job output file
    """
    _response: dict = batch_job_output_file.get("response", None) or {}
    _response_body = _response.get("body", None) or {}
    return _response_body


def _batch_response_was_successful(batch_job_output_file: dict) -> bool:
    """
    Check if the batch job response status == 200
    """
    _response: dict = batch_job_output_file.get("response", None) or {}
    return _response.get("status_code", None) == 200

# === NexusCore/openenv\Lib\site-packages\litellm\llms\predibase\chat\transformation.py ===
from typing import TYPE_CHECKING, Any, List, Literal, Optional, Union

from httpx import Headers, Response

from litellm.constants import DEFAULT_MAX_TOKENS
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import ModelResponse

from ..common_utils import PredibaseError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class PredibaseConfig(BaseConfig):
    """
    Reference:  https://docs.predibase.com/user-guide/inference/rest_api
    """

    adapter_id: Optional[str] = None
    adapter_source: Optional[Literal["pbase", "hub", "s3"]] = None
    best_of: Optional[int] = None
    decoder_input_details: Optional[bool] = None
    details: bool = True  # enables returning logprobs + best of
    max_new_tokens: int = (
        DEFAULT_MAX_TOKENS  # openai default - requests hang if max_new_tokens not given
    )
    repetition_penalty: Optional[float] = None
    return_full_text: Optional[
        bool
    ] = False  # by default don't return the input as part of the output
    seed: Optional[int] = None
    stop: Optional[List[str]] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[int] = None
    truncate: Optional[int] = None
    typical_p: Optional[float] = None
    watermark: Optional[bool] = None

    def __init__(
        self,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        details: Optional[bool] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[int] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str):
        return [
            "stream",
            "temperature",
            "max_completion_tokens",
            "max_tokens",
            "top_p",
            "stop",
            "n",
            "response_format",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            # temperature, top_p, n, stream, stop, max_tokens, n, presence_penalty default to None
            if param == "temperature":
                if value == 0.0 or value == 0:
                    # hugging face exception raised when temp==0
                    # Failed: Error occurred: HuggingfaceException - Input validation error: `temperature` must be strictly positive
                    value = 0.01
                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["top_p"] = value
            if param == "n":
                optional_params["best_of"] = value
                optional_params[
                    "do_sample"
                ] = True  # Need to sample if you want best of for hf inference endpoints
            if param == "stream":
                optional_params["stream"] = value
            if param == "stop":
                optional_params["stop"] = value
            if param == "max_tokens" or param == "max_completion_tokens":
                # HF TGI raises the following exception when max_new_tokens==0
                # Failed: Error occurred: HuggingfaceException - Input validation error: `max_new_tokens` must be strictly positive
                if value == 0:
                    value = 1
                optional_params["max_new_tokens"] = value
            if param == "echo":
                # https://huggingface.co/docs/huggingface_hub/main/en/package_reference/inference_client#huggingface_hub.InferenceClient.text_generation.decoder_input_details
                #  Return the decoder input token logprobs and ids. You must set details=True as well for it to be taken into account. Defaults to False
                optional_params["decoder_input_details"] = True
            if param == "response_format":
                optional_params["response_format"] = value
        return optional_params

    def transform_response(
        self,
        model: str,
        raw_response: Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: str,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        raise NotImplementedError(
            "Predibase transformation currently done in handler.py. Need to migrate to this file."
        )

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        raise NotImplementedError(
            "Predibase transformation currently done in handler.py. Need to migrate to this file."
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return PredibaseError(
            status_code=status_code, message=error_message, headers=headers
        )

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        if api_key is None:
            raise ValueError(
                "Missing Predibase API Key - A call is being made to predibase but no key is set either in the environment variables or via params"
            )

        default_headers = {
            "content-type": "application/json",
            "Authorization": "Bearer {}".format(api_key),
        }
        if headers is not None and isinstance(headers, dict):
            headers = {**default_headers, **headers}
        return headers

# === NexusCore/openenv\Lib\site-packages\openai\types\responses\tool_param.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, List, Union, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from .computer_tool_param import ComputerToolParam
from .function_tool_param import FunctionToolParam
from .web_search_tool_param import WebSearchToolParam
from .file_search_tool_param import FileSearchToolParam
from ..chat.chat_completion_tool_param import ChatCompletionToolParam

__all__ = [
    "ToolParam",
    "Mcp",
    "McpAllowedTools",
    "McpAllowedToolsMcpAllowedToolsFilter",
    "McpRequireApproval",
    "McpRequireApprovalMcpToolApprovalFilter",
    "McpRequireApprovalMcpToolApprovalFilterAlways",
    "McpRequireApprovalMcpToolApprovalFilterNever",
    "CodeInterpreter",
    "CodeInterpreterContainer",
    "CodeInterpreterContainerCodeInterpreterToolAuto",
    "ImageGeneration",
    "ImageGenerationInputImageMask",
    "LocalShell",
]


class McpAllowedToolsMcpAllowedToolsFilter(TypedDict, total=False):
    tool_names: List[str]
    """List of allowed tool names."""


McpAllowedTools: TypeAlias = Union[List[str], McpAllowedToolsMcpAllowedToolsFilter]


class McpRequireApprovalMcpToolApprovalFilterAlways(TypedDict, total=False):
    tool_names: List[str]
    """List of tools that require approval."""


class McpRequireApprovalMcpToolApprovalFilterNever(TypedDict, total=False):
    tool_names: List[str]
    """List of tools that do not require approval."""


class McpRequireApprovalMcpToolApprovalFilter(TypedDict, total=False):
    always: McpRequireApprovalMcpToolApprovalFilterAlways
    """A list of tools that always require approval."""

    never: McpRequireApprovalMcpToolApprovalFilterNever
    """A list of tools that never require approval."""


McpRequireApproval: TypeAlias = Union[McpRequireApprovalMcpToolApprovalFilter, Literal["always", "never"]]


class Mcp(TypedDict, total=False):
    server_label: Required[str]
    """A label for this MCP server, used to identify it in tool calls."""

    server_url: Required[str]
    """The URL for the MCP server."""

    type: Required[Literal["mcp"]]
    """The type of the MCP tool. Always `mcp`."""

    allowed_tools: Optional[McpAllowedTools]
    """List of allowed tool names or a filter object."""

    headers: Optional[Dict[str, str]]
    """Optional HTTP headers to send to the MCP server.

    Use for authentication or other purposes.
    """

    require_approval: Optional[McpRequireApproval]
    """Specify which of the MCP server's tools require approval."""


class CodeInterpreterContainerCodeInterpreterToolAuto(TypedDict, total=False):
    type: Required[Literal["auto"]]
    """Always `auto`."""

    file_ids: List[str]
    """An optional list of uploaded files to make available to your code."""


CodeInterpreterContainer: TypeAlias = Union[str, CodeInterpreterContainerCodeInterpreterToolAuto]


class CodeInterpreter(TypedDict, total=False):
    container: Required[CodeInterpreterContainer]
    """The code interpreter container.

    Can be a container ID or an object that specifies uploaded file IDs to make
    available to your code.
    """

    type: Required[Literal["code_interpreter"]]
    """The type of the code interpreter tool. Always `code_interpreter`."""


class ImageGenerationInputImageMask(TypedDict, total=False):
    file_id: str
    """File ID for the mask image."""

    image_url: str
    """Base64-encoded mask image."""


class ImageGeneration(TypedDict, total=False):
    type: Required[Literal["image_generation"]]
    """The type of the image generation tool. Always `image_generation`."""

    background: Literal["transparent", "opaque", "auto"]
    """Background type for the generated image.

    One of `transparent`, `opaque`, or `auto`. Default: `auto`.
    """

    input_image_mask: ImageGenerationInputImageMask
    """Optional mask for inpainting.

    Contains `image_url` (string, optional) and `file_id` (string, optional).
    """

    model: Literal["gpt-image-1"]
    """The image generation model to use. Default: `gpt-image-1`."""

    moderation: Literal["auto", "low"]
    """Moderation level for the generated image. Default: `auto`."""

    output_compression: int
    """Compression level for the output image. Default: 100."""

    output_format: Literal["png", "webp", "jpeg"]
    """The output format of the generated image.

    One of `png`, `webp`, or `jpeg`. Default: `png`.
    """

    partial_images: int
    """
    Number of partial images to generate in streaming mode, from 0 (default value)
    to 3.
    """

    quality: Literal["low", "medium", "high", "auto"]
    """The quality of the generated image.

    One of `low`, `medium`, `high`, or `auto`. Default: `auto`.
    """

    size: Literal["1024x1024", "1024x1536", "1536x1024", "auto"]
    """The size of the generated image.

    One of `1024x1024`, `1024x1536`, `1536x1024`, or `auto`. Default: `auto`.
    """


class LocalShell(TypedDict, total=False):
    type: Required[Literal["local_shell"]]
    """The type of the local shell tool. Always `local_shell`."""


ToolParam: TypeAlias = Union[
    FunctionToolParam,
    FileSearchToolParam,
    WebSearchToolParam,
    ComputerToolParam,
    Mcp,
    CodeInterpreter,
    ImageGeneration,
    LocalShell,
]


ParseableToolParam: TypeAlias = Union[ToolParam, ChatCompletionToolParam]

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\wheel.py ===
import logging
import os
import shutil
from optparse import Values
from typing import List

from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.req_command import RequirementCommand, with_cleanup
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.exceptions import CommandError
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.req.req_install import (
    InstallRequirement,
    check_legacy_setup_py_options,
)
from pip._internal.utils.misc import ensure_dir, normalize_path
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.wheel_builder import build, should_build_for_wheel_command

logger = logging.getLogger(__name__)


class WheelCommand(RequirementCommand):
    """
    Build Wheel archives for your requirements and dependencies.

    Wheel is a built-package format, and offers the advantage of not
    recompiling your software during every install. For more details, see the
    wheel docs: https://wheel.readthedocs.io/en/latest/

    'pip wheel' uses the build system interface as described here:
    https://pip.pypa.io/en/stable/reference/build-system/

    """

    usage = """
      %prog [options] <requirement specifier> ...
      %prog [options] -r <requirements file> ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-w",
            "--wheel-dir",
            dest="wheel_dir",
            metavar="dir",
            default=os.curdir,
            help=(
                "Build wheels into <dir>, where the default is the "
                "current working directory."
            ),
        )
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())
        self.cmd_opts.add_option(cmdoptions.prefer_binary())
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.use_pep517())
        self.cmd_opts.add_option(cmdoptions.no_use_pep517())
        self.cmd_opts.add_option(cmdoptions.check_build_deps())
        self.cmd_opts.add_option(cmdoptions.constraints())
        self.cmd_opts.add_option(cmdoptions.editable())
        self.cmd_opts.add_option(cmdoptions.requirements())
        self.cmd_opts.add_option(cmdoptions.src())
        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())
        self.cmd_opts.add_option(cmdoptions.no_deps())
        self.cmd_opts.add_option(cmdoptions.progress_bar())

        self.cmd_opts.add_option(
            "--no-verify",
            dest="no_verify",
            action="store_true",
            default=False,
            help="Don't verify if built wheel is valid.",
        )

        self.cmd_opts.add_option(cmdoptions.config_settings())
        self.cmd_opts.add_option(cmdoptions.build_options())
        self.cmd_opts.add_option(cmdoptions.global_options())

        self.cmd_opts.add_option(
            "--pre",
            action="store_true",
            default=False,
            help=(
                "Include pre-release and development versions. By default, "
                "pip only finds stable versions."
            ),
        )

        self.cmd_opts.add_option(cmdoptions.require_hashes())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    @with_cleanup
    def run(self, options: Values, args: List[str]) -> int:
        session = self.get_default_session(options)

        finder = self._build_package_finder(options, session)

        options.wheel_dir = normalize_path(options.wheel_dir)
        ensure_dir(options.wheel_dir)

        build_tracker = self.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="wheel",
            globally_managed=True,
        )

        reqs = self.get_requirements(args, options, finder, session)
        check_legacy_setup_py_options(options, reqs)

        wheel_cache = WheelCache(options.cache_dir)

        preparer = self.make_requirement_preparer(
            temp_build_dir=directory,
            options=options,
            build_tracker=build_tracker,
            session=session,
            finder=finder,
            download_dir=options.wheel_dir,
            use_user_site=False,
            verbosity=self.verbosity,
        )

        resolver = self.make_resolver(
            preparer=preparer,
            finder=finder,
            options=options,
            wheel_cache=wheel_cache,
            ignore_requires_python=options.ignore_requires_python,
            use_pep517=options.use_pep517,
        )

        self.trace_basic_info(finder)

        requirement_set = resolver.resolve(reqs, check_supported_wheels=True)

        reqs_to_build: List[InstallRequirement] = []
        for req in requirement_set.requirements.values():
            if req.is_wheel:
                preparer.save_linked_requirement(req)
            elif should_build_for_wheel_command(req):
                reqs_to_build.append(req)

        preparer.prepare_linked_requirements_more(requirement_set.requirements.values())

        # build wheels
        build_successes, build_failures = build(
            reqs_to_build,
            wheel_cache=wheel_cache,
            verify=(not options.no_verify),
            build_options=options.build_options or [],
            global_options=options.global_options or [],
        )
        for req in build_successes:
            assert req.link and req.link.is_wheel
            assert req.local_file_path
            # copy from cache to target directory
            try:
                shutil.copy(req.local_file_path, options.wheel_dir)
            except OSError as e:
                logger.warning(
                    "Building wheel for %s failed: %s",
                    req.name,
                    e,
                )
                build_failures.append(req)
        if len(build_failures) != 0:
            raise CommandError("Failed to build one or more wheels")

        return SUCCESS

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\cachecontrol\caches\file_cache.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import os
from textwrap import dedent
from typing import IO, TYPE_CHECKING
from pathlib import Path

from pip._vendor.cachecontrol.cache import BaseCache, SeparateBodyBaseCache
from pip._vendor.cachecontrol.controller import CacheController

if TYPE_CHECKING:
    from datetime import datetime

    from filelock import BaseFileLock


def _secure_open_write(filename: str, fmode: int) -> IO[bytes]:
    # We only want to write to this file, so open it in write only mode
    flags = os.O_WRONLY

    # os.O_CREAT | os.O_EXCL will fail if the file already exists, so we only
    #  will open *new* files.
    # We specify this because we want to ensure that the mode we pass is the
    # mode of the file.
    flags |= os.O_CREAT | os.O_EXCL

    # Do not follow symlinks to prevent someone from making a symlink that
    # we follow and insecurely open a cache file.
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    # On Windows we'll mark this file as binary
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    # Before we open our file, we want to delete any existing file that is
    # there
    try:
        os.remove(filename)
    except OSError:
        # The file must not exist already, so we can just skip ahead to opening
        pass

    # Open our file, the use of os.O_CREAT | os.O_EXCL will ensure that if a
    # race condition happens between the os.remove and this line, that an
    # error will be raised. Because we utilize a lockfile this should only
    # happen if someone is attempting to attack us.
    fd = os.open(filename, flags, fmode)
    try:
        return os.fdopen(fd, "wb")

    except:
        # An error occurred wrapping our FD in a file object
        os.close(fd)
        raise


class _FileCacheMixin:
    """Shared implementation for both FileCache variants."""

    def __init__(
        self,
        directory: str | Path,
        forever: bool = False,
        filemode: int = 0o0600,
        dirmode: int = 0o0700,
        lock_class: type[BaseFileLock] | None = None,
    ) -> None:
        try:
            if lock_class is None:
                from filelock import FileLock

                lock_class = FileLock
        except ImportError:
            notice = dedent(
                """
            NOTE: In order to use the FileCache you must have
            filelock installed. You can install it via pip:
              pip install cachecontrol[filecache]
            """
            )
            raise ImportError(notice)

        self.directory = directory
        self.forever = forever
        self.filemode = filemode
        self.dirmode = dirmode
        self.lock_class = lock_class

    @staticmethod
    def encode(x: str) -> str:
        return hashlib.sha224(x.encode()).hexdigest()

    def _fn(self, name: str) -> str:
        # NOTE: This method should not change as some may depend on it.
        #       See: https://github.com/ionrock/cachecontrol/issues/63
        hashed = self.encode(name)
        parts = list(hashed[:5]) + [hashed]
        return os.path.join(self.directory, *parts)

    def get(self, key: str) -> bytes | None:
        name = self._fn(key)
        try:
            with open(name, "rb") as fh:
                return fh.read()

        except FileNotFoundError:
            return None

    def set(
        self, key: str, value: bytes, expires: int | datetime | None = None
    ) -> None:
        name = self._fn(key)
        self._write(name, value)

    def _write(self, path: str, data: bytes) -> None:
        """
        Safely write the data to the given path.
        """
        # Make sure the directory exists
        try:
            os.makedirs(os.path.dirname(path), self.dirmode)
        except OSError:
            pass

        with self.lock_class(path + ".lock"):
            # Write our actual file
            with _secure_open_write(path, self.filemode) as fh:
                fh.write(data)

    def _delete(self, key: str, suffix: str) -> None:
        name = self._fn(key) + suffix
        if not self.forever:
            try:
                os.remove(name)
            except FileNotFoundError:
                pass


class FileCache(_FileCacheMixin, BaseCache):
    """
    Traditional FileCache: body is stored in memory, so not suitable for large
    downloads.
    """

    def delete(self, key: str) -> None:
        self._delete(key, "")


class SeparateBodyFileCache(_FileCacheMixin, SeparateBodyBaseCache):
    """
    Memory-efficient FileCache: body is stored in a separate file, reducing
    peak memory usage.
    """

    def get_body(self, key: str) -> IO[bytes] | None:
        name = self._fn(key) + ".body"
        try:
            return open(name, "rb")
        except FileNotFoundError:
            return None

    def set_body(self, key: str, body: bytes) -> None:
        name = self._fn(key) + ".body"
        self._write(name, body)

    def delete(self, key: str) -> None:
        self._delete(key, "")
        self._delete(key, ".body")


def url_to_file_path(url: str, filecache: FileCache) -> str:
    """Return the file cache path based on the URL.

    This does not ensure the file exists!
    """
    key = CacheController.cache_url(url)
    return filecache._fn(key)

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_core_utils.py ===
from __future__ import annotations

import inspect
import os
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Union

from pydantic_core import CoreSchema, core_schema
from pydantic_core import validate_core_schema as _validate_core_schema
from typing_extensions import TypeGuard, get_args, get_origin
from typing_inspection import typing_objects

from . import _repr
from ._typing_extra import is_generic_alias

if TYPE_CHECKING:
    from rich.console import Console

AnyFunctionSchema = Union[
    core_schema.AfterValidatorFunctionSchema,
    core_schema.BeforeValidatorFunctionSchema,
    core_schema.WrapValidatorFunctionSchema,
    core_schema.PlainValidatorFunctionSchema,
]


FunctionSchemaWithInnerSchema = Union[
    core_schema.AfterValidatorFunctionSchema,
    core_schema.BeforeValidatorFunctionSchema,
    core_schema.WrapValidatorFunctionSchema,
]

CoreSchemaField = Union[
    core_schema.ModelField, core_schema.DataclassField, core_schema.TypedDictField, core_schema.ComputedField
]
CoreSchemaOrField = Union[core_schema.CoreSchema, CoreSchemaField]

_CORE_SCHEMA_FIELD_TYPES = {'typed-dict-field', 'dataclass-field', 'model-field', 'computed-field'}
_FUNCTION_WITH_INNER_SCHEMA_TYPES = {'function-before', 'function-after', 'function-wrap'}
_LIST_LIKE_SCHEMA_WITH_ITEMS_TYPES = {'list', 'set', 'frozenset'}


def is_core_schema(
    schema: CoreSchemaOrField,
) -> TypeGuard[CoreSchema]:
    return schema['type'] not in _CORE_SCHEMA_FIELD_TYPES


def is_core_schema_field(
    schema: CoreSchemaOrField,
) -> TypeGuard[CoreSchemaField]:
    return schema['type'] in _CORE_SCHEMA_FIELD_TYPES


def is_function_with_inner_schema(
    schema: CoreSchemaOrField,
) -> TypeGuard[FunctionSchemaWithInnerSchema]:
    return schema['type'] in _FUNCTION_WITH_INNER_SCHEMA_TYPES


def is_list_like_schema_with_items_schema(
    schema: CoreSchema,
) -> TypeGuard[core_schema.ListSchema | core_schema.SetSchema | core_schema.FrozenSetSchema]:
    return schema['type'] in _LIST_LIKE_SCHEMA_WITH_ITEMS_TYPES


def get_type_ref(type_: Any, args_override: tuple[type[Any], ...] | None = None) -> str:
    """Produces the ref to be used for this type by pydantic_core's core schemas.

    This `args_override` argument was added for the purpose of creating valid recursive references
    when creating generic models without needing to create a concrete class.
    """
    origin = get_origin(type_) or type_

    args = get_args(type_) if is_generic_alias(type_) else (args_override or ())
    generic_metadata = getattr(type_, '__pydantic_generic_metadata__', None)
    if generic_metadata:
        origin = generic_metadata['origin'] or origin
        args = generic_metadata['args'] or args

    module_name = getattr(origin, '__module__', '<No __module__>')
    if typing_objects.is_typealiastype(origin):
        type_ref = f'{module_name}.{origin.__name__}:{id(origin)}'
    else:
        try:
            qualname = getattr(origin, '__qualname__', f'<No __qualname__: {origin}>')
        except Exception:
            qualname = getattr(origin, '__qualname__', '<No __qualname__>')
        type_ref = f'{module_name}.{qualname}:{id(origin)}'

    arg_refs: list[str] = []
    for arg in args:
        if isinstance(arg, str):
            # Handle string literals as a special case; we may be able to remove this special handling if we
            # wrap them in a ForwardRef at some point.
            arg_ref = f'{arg}:str-{id(arg)}'
        else:
            arg_ref = f'{_repr.display_as_type(arg)}:{id(arg)}'
        arg_refs.append(arg_ref)
    if arg_refs:
        type_ref = f'{type_ref}[{",".join(arg_refs)}]'
    return type_ref


def get_ref(s: core_schema.CoreSchema) -> None | str:
    """Get the ref from the schema if it has one.
    This exists just for type checking to work correctly.
    """
    return s.get('ref', None)


def validate_core_schema(schema: CoreSchema) -> CoreSchema:
    if os.getenv('PYDANTIC_VALIDATE_CORE_SCHEMAS'):
        return _validate_core_schema(schema)
    return schema


def _clean_schema_for_pretty_print(obj: Any, strip_metadata: bool = True) -> Any:  # pragma: no cover
    """A utility function to remove irrelevant information from a core schema."""
    if isinstance(obj, Mapping):
        new_dct = {}
        for k, v in obj.items():
            if k == 'metadata' and strip_metadata:
                new_metadata = {}

                for meta_k, meta_v in v.items():
                    if meta_k in ('pydantic_js_functions', 'pydantic_js_annotation_functions'):
                        new_metadata['js_metadata'] = '<stripped>'
                    else:
                        new_metadata[meta_k] = _clean_schema_for_pretty_print(meta_v, strip_metadata=strip_metadata)

                if list(new_metadata.keys()) == ['js_metadata']:
                    new_metadata = {'<stripped>'}

                new_dct[k] = new_metadata
            # Remove some defaults:
            elif k in ('custom_init', 'root_model') and not v:
                continue
            else:
                new_dct[k] = _clean_schema_for_pretty_print(v, strip_metadata=strip_metadata)

        return new_dct
    elif isinstance(obj, Sequence) and not isinstance(obj, str):
        return [_clean_schema_for_pretty_print(v, strip_metadata=strip_metadata) for v in obj]
    else:
        return obj


def pretty_print_core_schema(
    val: Any,
    *,
    console: Console | None = None,
    max_depth: int | None = None,
    strip_metadata: bool = True,
) -> None:  # pragma: no cover
    """Pretty-print a core schema using the `rich` library.

    Args:
        val: The core schema to print, or a Pydantic model/dataclass/type adapter
            (in which case the cached core schema is fetched and printed).
        console: A rich console to use when printing. Defaults to the global rich console instance.
        max_depth: The number of nesting levels which may be printed.
        strip_metadata: Whether to strip metadata in the output. If `True` any known core metadata
            attributes will be stripped (but custom attributes are kept). Defaults to `True`.
    """
    # lazy import:
    from rich.pretty import pprint

    # circ. imports:
    from pydantic import BaseModel, TypeAdapter
    from pydantic.dataclasses import is_pydantic_dataclass

    if (inspect.isclass(val) and issubclass(val, BaseModel)) or is_pydantic_dataclass(val):
        val = val.__pydantic_core_schema__
    if isinstance(val, TypeAdapter):
        val = val.core_schema
    cleaned_schema = _clean_schema_for_pretty_print(val, strip_metadata=strip_metadata)

    pprint(cleaned_schema, console=console, max_depth=max_depth)


pps = pretty_print_core_schema

# === NexusCore/openenv\Lib\site-packages\traitlets\utils\descriptions.py ===
from __future__ import annotations

import inspect
import re
import types
from typing import Any


def describe(
    article: str | None,
    value: Any,
    name: str | None = None,
    verbose: bool = False,
    capital: bool = False,
) -> str:
    """Return string that describes a value

    Parameters
    ----------
    article : str or None
        A definite or indefinite article. If the article is
        indefinite (i.e. "a" or "an") the appropriate one
        will be inferred. Thus, the arguments of ``describe``
        can themselves represent what the resulting string
        will actually look like. If None, then no article
        will be prepended to the result. For non-articled
        description, values that are instances are treated
        definitely, while classes are handled indefinitely.
    value : any
        The value which will be named.
    name : str or None (default: None)
        Only applies when ``article`` is "the" - this
        ``name`` is a definite reference to the value.
        By default one will be inferred from the value's
        type and repr methods.
    verbose : bool (default: False)
        Whether the name should be concise or verbose. When
        possible, verbose names include the module, and/or
        class name where an object was defined.
    capital : bool (default: False)
        Whether the first letter of the article should
        be capitalized or not. By default it is not.

    Examples
    --------
    Indefinite description:

    >>> describe("a", object())
    'an object'
    >>> describe("a", object)
    'an object'
    >>> describe("a", type(object))
    'a type'

    Definite description:

    >>> describe("the", object())
    "the object at '...'"
    >>> describe("the", object)
    'the object object'
    >>> describe("the", type(object))
    'the type type'

    Definitely named description:

    >>> describe("the", object(), "I made")
    'the object I made'
    >>> describe("the", object, "I will use")
    'the object I will use'
    """
    if isinstance(article, str):
        article = article.lower()

    if not inspect.isclass(value):
        typename = type(value).__name__
    else:
        typename = value.__name__
    if verbose:
        typename = _prefix(value) + typename

    if article == "the" or (article is None and not inspect.isclass(value)):
        if name is not None:
            result = f"{typename} {name}"
            if article is not None:
                return add_article(result, True, capital)
            else:
                return result
        else:
            tick_wrap = False
            if inspect.isclass(value):
                name = value.__name__
            elif isinstance(value, types.FunctionType):
                name = value.__name__
                tick_wrap = True
            elif isinstance(value, types.MethodType):
                name = value.__func__.__name__
                tick_wrap = True
            elif type(value).__repr__ in (
                object.__repr__,
                type.__repr__,
            ):  # type:ignore[comparison-overlap]
                name = "at '%s'" % hex(id(value))
                verbose = False
            else:
                name = repr(value)
                verbose = False
            if verbose:
                name = _prefix(value) + name
            if tick_wrap:
                name = name.join("''")
            return describe(article, value, name=name, verbose=verbose, capital=capital)
    elif article in ("a", "an") or article is None:
        if article is None:
            return typename
        return add_article(typename, False, capital)
    else:
        raise ValueError(
            "The 'article' argument should be 'the', 'a', 'an', or None not %r" % article
        )


def _prefix(value: Any) -> str:
    if isinstance(value, types.MethodType):
        name = describe(None, value.__self__, verbose=True) + "."
    else:
        module = inspect.getmodule(value)
        if module is not None and module.__name__ != "builtins":
            name = module.__name__ + "."
        else:
            name = ""
    return name


def class_of(value: Any) -> Any:
    """Returns a string of the value's type with an indefinite article.

    For example 'an Image' or 'a PlotValue'.
    """
    if inspect.isclass(value):
        return add_article(value.__name__)
    else:
        return class_of(type(value))


def add_article(name: str, definite: bool = False, capital: bool = False) -> str:
    """Returns the string with a prepended article.

    The input does not need to begin with a character.

    Parameters
    ----------
    name : str
        Name to which to prepend an article
    definite : bool (default: False)
        Whether the article is definite or not.
        Indefinite articles being 'a' and 'an',
        while 'the' is definite.
    capital : bool (default: False)
        Whether the added article should have
        its first letter capitalized or not.
    """
    if definite:
        result = "the " + name
    else:
        first_letters = re.compile(r"[\W_]+").sub("", name)
        if first_letters[:1].lower() in "aeiou":
            result = "an " + name
        else:
            result = "a " + name
    if capital:
        return result[0].upper() + result[1:]
    else:
        return result


def repr_type(obj: Any) -> str:
    """Return a string representation of a value and its type for readable

    error messages.
    """
    the_type = type(obj)
    return f"{obj!r} {the_type!r}"

# === NexusCore/openenv\Lib\site-packages\win32com\client\selecttlb.py ===
"""Utilities for selecting and enumerating the Type Libraries installed on the system"""

import pythoncom
import win32api
import win32con


class TypelibSpec:
    def __init__(self, clsid, lcid, major, minor, flags=0):
        self.clsid = str(clsid)
        self.lcid = int(lcid)
        # We avoid assuming 'major' or 'minor' are integers - when
        # read from the registry there is some confusion about if
        # they are base 10 or base 16 (they *should* be base 16, but
        # how they are written is beyond our control.)
        self.major = major
        self.minor = minor
        self.dll = None
        self.desc = None
        self.ver_desc = None
        self.flags = flags

    # For the SelectList
    def __getitem__(self, item):
        if item == 0:
            return self.ver_desc
        raise IndexError("Can't index me!")

    def __lt__(self, other):
        me = (
            (self.ver_desc or "").lower(),
            (self.desc or "").lower(),
            self.major,
            self.minor,
        )
        them = (
            (other.ver_desc or "").lower(),
            (other.desc or "").lower(),
            other.major,
            other.minor,
        )
        return me < them

    def __eq__(self, other):
        return (
            (self.ver_desc or "").lower() == (other.ver_desc or "").lower()
            and (self.desc or "").lower() == (other.desc or "").lower()
            and self.major == other.major
            and self.minor == other.minor
        )

    def Resolve(self):
        if self.dll is None:
            return 0
        tlb = pythoncom.LoadTypeLib(self.dll)
        self.FromTypelib(tlb, None)
        return 1

    def FromTypelib(self, typelib, dllName=None):
        la = typelib.GetLibAttr()
        self.clsid = str(la[0])
        self.lcid = la[1]
        self.major = la[3]
        self.minor = la[4]
        if dllName:
            self.dll = dllName


def EnumKeys(root):
    index = 0
    ret = []
    while 1:
        try:
            item = win32api.RegEnumKey(root, index)
        except win32api.error:
            break
        try:
            # Note this doesn't handle REG_EXPAND_SZ, but the implementation
            # here doesn't need to - that is handled as the data is read.
            val = win32api.RegQueryValue(root, item)
        except win32api.error:
            val = ""  # code using this assumes a string.

        ret.append((item, val))
        index += 1
    return ret


FLAG_RESTRICTED = 1
FLAG_CONTROL = 2
FLAG_HIDDEN = 4


def EnumTlbs(excludeFlags=0):
    """Return a list of TypelibSpec objects, one for each registered library."""
    key = win32api.RegOpenKey(win32con.HKEY_CLASSES_ROOT, "Typelib")
    iids = EnumKeys(key)
    results = []
    for iid, crap in iids:
        try:
            key2 = win32api.RegOpenKey(key, str(iid))
        except win32api.error:
            # A few good reasons for this, including "access denied".
            continue
        for version, tlbdesc in EnumKeys(key2):
            major_minor = version.split(".", 1)
            if len(major_minor) < 2:
                major_minor.append("0")
            # For some reason, this code used to assume the values were hex.
            # This seems to not be true - particularly for CDO 1.21
            # *sigh* - it appears there are no rules here at all, so when we need
            # to know the info, we must load the tlb by filename and request it.
            # The Resolve() method on the TypelibSpec does this.
            # For this reason, keep the version numbers as strings - that
            # way we can't be wrong!  Let code that really needs an int to work
            # out what to do.  FWIW, https://www.betaarchive.com/wiki/index.php?title=Microsoft_KB_Archive/816970
            # is pretty clear that they *should* be hex.
            major = major_minor[0]
            minor = major_minor[1]
            key3 = win32api.RegOpenKey(key2, str(version))
            try:
                # The "FLAGS" are at this point
                flags = int(win32api.RegQueryValue(key3, "FLAGS"))
            except (win32api.error, ValueError):
                flags = 0
            if flags & excludeFlags == 0:
                for lcid, crap in EnumKeys(key3):
                    try:
                        lcid = int(lcid)
                    except ValueError:  # not an LCID entry
                        continue
                    # Check for both "{lcid}\win32" and "{lcid}\win64" keys.
                    try:
                        key4 = win32api.RegOpenKey(key3, f"{lcid}\\win32")
                    except win32api.error:
                        try:
                            key4 = win32api.RegOpenKey(key3, f"{lcid}\\win64")
                        except win32api.error:
                            continue
                    try:
                        dll, typ = win32api.RegQueryValueEx(key4, None)
                        if typ == win32con.REG_EXPAND_SZ:
                            dll = win32api.ExpandEnvironmentStrings(dll)
                    except win32api.error:
                        dll = None
                    spec = TypelibSpec(iid, lcid, major, minor, flags)
                    spec.dll = dll
                    spec.desc = tlbdesc
                    spec.ver_desc = tlbdesc + " (" + version + ")"
                    results.append(spec)
    return results


def FindTlbsWithDescription(desc):
    """Find all installed type libraries with the specified description"""
    ret = []
    items = EnumTlbs()
    for item in items:
        if item.desc == desc:
            ret.append(item)
    return ret


def SelectTlb(title="Select Library", excludeFlags=0):
    """Display a list of all the type libraries, and select one.   Returns None if cancelled"""
    import pywin.dialogs.list

    items = EnumTlbs(excludeFlags)
    # fixup versions - we assume hex (see __init__ above)
    for i in items:
        i.major = int(i.major, 16)
        i.minor = int(i.minor, 16)
    items.sort()
    rc = pywin.dialogs.list.SelectFromLists(title, items, ["Type Library"])
    if rc is None:
        return None
    return items[rc]


# Test code.
if __name__ == "__main__":
    print(SelectTlb().__dict__)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\operations\check.py ===
"""Validation of dependencies of packages
"""

import logging
from contextlib import suppress
from email.parser import Parser
from functools import reduce
from typing import (
    Callable,
    Dict,
    FrozenSet,
    Generator,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
)

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.tags import Tag, parse_tag
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.distributions import make_distribution_for_install_requirement
from pip._internal.metadata import get_default_environment
from pip._internal.metadata.base import BaseDistribution
from pip._internal.req.req_install import InstallRequirement

logger = logging.getLogger(__name__)


class PackageDetails(NamedTuple):
    version: Version
    dependencies: List[Requirement]


# Shorthands
PackageSet = Dict[NormalizedName, PackageDetails]
Missing = Tuple[NormalizedName, Requirement]
Conflicting = Tuple[NormalizedName, Version, Requirement]

MissingDict = Dict[NormalizedName, List[Missing]]
ConflictingDict = Dict[NormalizedName, List[Conflicting]]
CheckResult = Tuple[MissingDict, ConflictingDict]
ConflictDetails = Tuple[PackageSet, CheckResult]


def create_package_set_from_installed() -> Tuple[PackageSet, bool]:
    """Converts a list of distributions into a PackageSet."""
    package_set = {}
    problems = False
    env = get_default_environment()
    for dist in env.iter_installed_distributions(local_only=False, skip=()):
        name = dist.canonical_name
        try:
            dependencies = list(dist.iter_dependencies())
            package_set[name] = PackageDetails(dist.version, dependencies)
        except (OSError, ValueError) as e:
            # Don't crash on unreadable or broken metadata.
            logger.warning("Error parsing dependencies of %s: %s", name, e)
            problems = True
    return package_set, problems


def check_package_set(
    package_set: PackageSet, should_ignore: Optional[Callable[[str], bool]] = None
) -> CheckResult:
    """Check if a package set is consistent

    If should_ignore is passed, it should be a callable that takes a
    package name and returns a boolean.
    """

    missing = {}
    conflicting = {}

    for package_name, package_detail in package_set.items():
        # Info about dependencies of package_name
        missing_deps: Set[Missing] = set()
        conflicting_deps: Set[Conflicting] = set()

        if should_ignore and should_ignore(package_name):
            continue

        for req in package_detail.dependencies:
            name = canonicalize_name(req.name)

            # Check if it's missing
            if name not in package_set:
                missed = True
                if req.marker is not None:
                    missed = req.marker.evaluate({"extra": ""})
                if missed:
                    missing_deps.add((name, req))
                continue

            # Check if there's a conflict
            version = package_set[name].version
            if not req.specifier.contains(version, prereleases=True):
                conflicting_deps.add((name, version, req))

        if missing_deps:
            missing[package_name] = sorted(missing_deps, key=str)
        if conflicting_deps:
            conflicting[package_name] = sorted(conflicting_deps, key=str)

    return missing, conflicting


def check_install_conflicts(to_install: List[InstallRequirement]) -> ConflictDetails:
    """For checking if the dependency graph would be consistent after \
    installing given requirements
    """
    # Start from the current state
    package_set, _ = create_package_set_from_installed()
    # Install packages
    would_be_installed = _simulate_installation_of(to_install, package_set)

    # Only warn about directly-dependent packages; create a whitelist of them
    whitelist = _create_whitelist(would_be_installed, package_set)

    return (
        package_set,
        check_package_set(
            package_set, should_ignore=lambda name: name not in whitelist
        ),
    )


def check_unsupported(
    packages: Iterable[BaseDistribution],
    supported_tags: Iterable[Tag],
) -> Generator[BaseDistribution, None, None]:
    for p in packages:
        with suppress(FileNotFoundError):
            wheel_file = p.read_text("WHEEL")
            wheel_tags: FrozenSet[Tag] = reduce(
                frozenset.union,
                map(parse_tag, Parser().parsestr(wheel_file).get_all("Tag", [])),
                frozenset(),
            )
            if wheel_tags.isdisjoint(supported_tags):
                yield p


def _simulate_installation_of(
    to_install: List[InstallRequirement], package_set: PackageSet
) -> Set[NormalizedName]:
    """Computes the version of packages after installing to_install."""
    # Keep track of packages that were installed
    installed = set()

    # Modify it as installing requirement_set would (assuming no errors)
    for inst_req in to_install:
        abstract_dist = make_distribution_for_install_requirement(inst_req)
        dist = abstract_dist.get_metadata_distribution()
        name = dist.canonical_name
        package_set[name] = PackageDetails(dist.version, list(dist.iter_dependencies()))

        installed.add(name)

    return installed


def _create_whitelist(
    would_be_installed: Set[NormalizedName], package_set: PackageSet
) -> Set[NormalizedName]:
    packages_affected = set(would_be_installed)

    for package_name in package_set:
        if package_name in packages_affected:
            continue

        for req in package_set[package_name].dependencies:
            if canonicalize_name(req.name) in packages_affected:
                packages_affected.add(package_name)
                break

    return packages_affected

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_breakpoints.py ===
from _pydev_bundle import pydev_log
from _pydevd_bundle import pydevd_import_class
from _pydevd_bundle.pydevd_frame_utils import add_exception_to_frame
from _pydev_bundle._pydev_saved_modules import threading


class ExceptionBreakpoint(object):
    def __init__(
        self,
        qname,
        condition,
        expression,
        notify_on_handled_exceptions,
        notify_on_unhandled_exceptions,
        notify_on_user_unhandled_exceptions,
        notify_on_first_raise_only,
        ignore_libraries,
    ):
        exctype = get_exception_class(qname)
        self.qname = qname
        if exctype is not None:
            self.name = exctype.__name__
        else:
            self.name = None

        self.condition = condition
        self.expression = expression
        self.notify_on_unhandled_exceptions = notify_on_unhandled_exceptions
        self.notify_on_handled_exceptions = notify_on_handled_exceptions
        self.notify_on_first_raise_only = notify_on_first_raise_only
        self.notify_on_user_unhandled_exceptions = notify_on_user_unhandled_exceptions
        self.ignore_libraries = ignore_libraries

        self.type = exctype

    def __str__(self):
        return self.qname

    @property
    def has_condition(self):
        return self.condition is not None

    def handle_hit_condition(self, frame):
        return False


class LineBreakpoint(object):
    def __init__(self, breakpoint_id, line, condition, func_name, expression, suspend_policy="NONE", hit_condition=None, is_logpoint=False):
        self.breakpoint_id = breakpoint_id
        self.line = line
        self.condition = condition
        self.func_name = func_name
        self.expression = expression
        self.suspend_policy = suspend_policy
        self.hit_condition = hit_condition
        self._hit_count = 0
        self._hit_condition_lock = threading.Lock()
        self.is_logpoint = is_logpoint

    @property
    def has_condition(self):
        return bool(self.condition) or bool(self.hit_condition)

    def handle_hit_condition(self, frame):
        if not self.hit_condition:
            return False
        ret = False
        with self._hit_condition_lock:
            self._hit_count += 1
            expr = self.hit_condition.replace("@HIT@", str(self._hit_count))
            try:
                ret = bool(eval(expr, frame.f_globals, frame.f_locals))
            except Exception:
                ret = False
        return ret


class FunctionBreakpoint(object):
    def __init__(self, func_name, condition, expression, suspend_policy="NONE", hit_condition=None, is_logpoint=False):
        self.condition = condition
        self.func_name = func_name
        self.expression = expression
        self.suspend_policy = suspend_policy
        self.hit_condition = hit_condition
        self._hit_count = 0
        self._hit_condition_lock = threading.Lock()
        self.is_logpoint = is_logpoint

    @property
    def has_condition(self):
        return bool(self.condition) or bool(self.hit_condition)

    def handle_hit_condition(self, frame):
        if not self.hit_condition:
            return False
        ret = False
        with self._hit_condition_lock:
            self._hit_count += 1
            expr = self.hit_condition.replace("@HIT@", str(self._hit_count))
            try:
                ret = bool(eval(expr, frame.f_globals, frame.f_locals))
            except Exception:
                ret = False
        return ret


def get_exception_breakpoint(exctype, exceptions):
    if not exctype:
        exception_full_qname = None
    else:
        exception_full_qname = str(exctype.__module__) + "." + exctype.__name__

    exc = None
    if exceptions is not None:
        try:
            return exceptions[exception_full_qname]
        except KeyError:
            for exception_breakpoint in exceptions.values():
                if exception_breakpoint.type is not None and issubclass(exctype, exception_breakpoint.type):
                    if exc is None or issubclass(exception_breakpoint.type, exc.type):
                        exc = exception_breakpoint
    return exc


def stop_on_unhandled_exception(py_db, thread, additional_info, arg):
    exctype, value, tb = arg
    break_on_uncaught_exceptions = py_db.break_on_uncaught_exceptions
    if break_on_uncaught_exceptions:
        exception_breakpoint = py_db.get_exception_breakpoint(exctype, break_on_uncaught_exceptions)
    else:
        exception_breakpoint = None

    if not exception_breakpoint:
        return

    if tb is None:  # sometimes it can be None, e.g. with GTK
        return

    if exctype is KeyboardInterrupt:
        return

    if exctype is SystemExit and py_db.ignore_system_exit_code(value):
        return

    frames = []
    user_frame = None

    while tb is not None:
        if not py_db.exclude_exception_by_filter(exception_breakpoint, tb):
            user_frame = tb.tb_frame
        frames.append(tb.tb_frame)
        tb = tb.tb_next

    if user_frame is None:
        return

    frames_byid = dict([(id(frame), frame) for frame in frames])
    add_exception_to_frame(user_frame, arg)
    if exception_breakpoint.condition is not None:
        eval_result = py_db.handle_breakpoint_condition(additional_info, exception_breakpoint, user_frame)
        if not eval_result:
            return

    if exception_breakpoint.expression is not None:
        py_db.handle_breakpoint_expression(exception_breakpoint, additional_info, user_frame)

    try:
        additional_info.pydev_message = exception_breakpoint.qname
    except:
        additional_info.pydev_message = exception_breakpoint.qname.encode("utf-8")

    pydev_log.debug("Handling post-mortem stop on exception breakpoint %s" % (exception_breakpoint.qname,))

    py_db.do_stop_on_unhandled_exception(thread, user_frame, frames_byid, arg)


def get_exception_class(kls):
    try:
        return eval(kls)
    except:
        return pydevd_import_class.import_name(kls)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_command_line_handling.py ===
import os
import sys


class ArgHandlerWithParam:
    """
    Handler for some arguments which needs a value
    """

    def __init__(self, arg_name, convert_val=None, default_val=None):
        self.arg_name = arg_name
        self.arg_v_rep = "--%s" % (arg_name,)
        self.convert_val = convert_val
        self.default_val = default_val

    def to_argv(self, lst, setup):
        v = setup.get(self.arg_name)
        if v is not None and v != self.default_val:
            lst.append(self.arg_v_rep)
            lst.append("%s" % (v,))

    def handle_argv(self, argv, i, setup):
        assert argv[i] == self.arg_v_rep
        del argv[i]

        val = argv[i]
        if self.convert_val:
            val = self.convert_val(val)

        setup[self.arg_name] = val
        del argv[i]


class ArgHandlerBool:
    """
    If a given flag is received, mark it as 'True' in setup.
    """

    def __init__(self, arg_name, default_val=False):
        self.arg_name = arg_name
        self.arg_v_rep = "--%s" % (arg_name,)
        self.default_val = default_val

    def to_argv(self, lst, setup):
        v = setup.get(self.arg_name)
        if v:
            lst.append(self.arg_v_rep)

    def handle_argv(self, argv, i, setup):
        assert argv[i] == self.arg_v_rep
        del argv[i]
        setup[self.arg_name] = True


def convert_ppid(ppid):
    ret = int(ppid)
    if ret != 0:
        if ret == os.getpid():
            raise AssertionError("ppid passed is the same as the current process pid (%s)!" % (ret,))
    return ret


ACCEPTED_ARG_HANDLERS = [
    ArgHandlerWithParam("port", int, 0),
    ArgHandlerWithParam("ppid", convert_ppid, 0),
    ArgHandlerWithParam("vm_type"),
    ArgHandlerWithParam("client"),
    ArgHandlerWithParam("access-token"),
    ArgHandlerWithParam("client-access-token"),
    ArgHandlerWithParam("debug-mode"),
    ArgHandlerWithParam("preimport"),
    # Logging
    ArgHandlerWithParam("log-file"),
    ArgHandlerWithParam("log-level", int, None),
    ArgHandlerBool("server"),
    ArgHandlerBool("multiproc"),  # Used by PyCharm (reuses connection: ssh tunneling)
    ArgHandlerBool("multiprocess"),  # Used by PyDev (creates new connection to ide)
    ArgHandlerBool("save-signatures"),
    ArgHandlerBool("save-threading"),
    ArgHandlerBool("save-asyncio"),
    ArgHandlerBool("print-in-debugger-startup"),
    ArgHandlerBool("cmd-line"),
    ArgHandlerBool("module"),
    ArgHandlerBool("skip-notify-stdin"),
    # The ones below should've been just one setting to specify the protocol, but for compatibility
    # reasons they're passed as a flag but are mutually exclusive.
    ArgHandlerBool("json-dap"),  # Protocol used by ptvsd to communicate with pydevd (a single json message in each read)
    ArgHandlerBool("json-dap-http"),  # Actual DAP (json messages over http protocol).
    ArgHandlerBool("protocol-quoted-line"),  # Custom protocol with quoted lines.
    ArgHandlerBool("protocol-http"),  # Custom protocol with http.
]

ARGV_REP_TO_HANDLER = {}
for handler in ACCEPTED_ARG_HANDLERS:
    ARGV_REP_TO_HANDLER[handler.arg_v_rep] = handler


def get_pydevd_file():
    import pydevd

    f = pydevd.__file__
    if f.endswith(".pyc"):
        f = f[:-1]
    elif f.endswith("$py.class"):
        f = f[: -len("$py.class")] + ".py"
    return f


def setup_to_argv(setup, skip_names=None):
    """
    :param dict setup:
        A dict previously gotten from process_command_line.

    :param set skip_names:
        The names in the setup which shouldn't be converted to argv.

    :note: does not handle --file nor --DEBUG.
    """
    if skip_names is None:
        skip_names = set()
    ret = [get_pydevd_file()]

    for handler in ACCEPTED_ARG_HANDLERS:
        if handler.arg_name in setup and handler.arg_name not in skip_names:
            handler.to_argv(ret, setup)
    return ret


def process_command_line(argv):
    """parses the arguments.
    removes our arguments from the command line"""
    setup = {}
    for handler in ACCEPTED_ARG_HANDLERS:
        setup[handler.arg_name] = handler.default_val
    setup["file"] = ""
    setup["qt-support"] = ""

    initial_argv = tuple(argv)

    i = 0
    del argv[0]
    while i < len(argv):
        handler = ARGV_REP_TO_HANDLER.get(argv[i])
        if handler is not None:
            handler.handle_argv(argv, i, setup)

        elif argv[i].startswith("--qt-support"):
            # The --qt-support is special because we want to keep backward compatibility:
            # Previously, just passing '--qt-support' meant that we should use the auto-discovery mode
            # whereas now, if --qt-support is passed, it should be passed as --qt-support=<mode>, where
            # mode can be one of 'auto', 'none', 'pyqt5', 'pyqt4', 'pyside', 'pyside2'.
            if argv[i] == "--qt-support":
                setup["qt-support"] = "auto"

            elif argv[i].startswith("--qt-support="):
                qt_support = argv[i][len("--qt-support=") :]
                valid_modes = ("none", "auto", "pyqt5", "pyqt4", "pyside", "pyside2")
                if qt_support not in valid_modes:
                    raise ValueError("qt-support mode invalid: " + qt_support)
                if qt_support == "none":
                    # On none, actually set an empty string to evaluate to False.
                    setup["qt-support"] = ""
                else:
                    setup["qt-support"] = qt_support
            else:
                raise ValueError("Unexpected definition for qt-support flag: " + argv[i])

            del argv[i]

        elif argv[i] == "--file":
            # --file is special because it's the last one (so, no handler for it).
            del argv[i]
            setup["file"] = argv[i]
            i = len(argv)  # pop out, file is our last argument

        elif argv[i] == "--DEBUG":
            sys.stderr.write("pydevd: --DEBUG parameter deprecated. Use `--debug-level=3` instead.\n")

        else:
            raise ValueError("Unexpected option: %s when processing: %s" % (argv[i], initial_argv))
    return setup

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\pydev_umd.py ===
"""
The UserModuleDeleter and runfile methods are copied from
Spyder and carry their own license agreement.
http://code.google.com/p/spyderlib/source/browse/spyderlib/widgets/externalshell/sitecustomize.py

Spyder License Agreement (MIT License)
--------------------------------------

Copyright (c) 2009-2012 Pierre Raybaut

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import sys
import os
from _pydev_bundle._pydev_execfile import execfile


# The following classes and functions are mainly intended to be used from
# an interactive Python session
class UserModuleDeleter:
    """
    User Module Deleter (UMD) aims at deleting user modules
    to force Python to deeply reload them during import

    pathlist [list]: ignore list in terms of module path
    namelist [list]: ignore list in terms of module name
    """

    def __init__(self, namelist=None, pathlist=None):
        if namelist is None:
            namelist = []
        self.namelist = namelist
        if pathlist is None:
            pathlist = []
        self.pathlist = pathlist
        try:
            # ignore all files in org.python.pydev/pysrc
            import pydev_pysrc, inspect

            self.pathlist.append(os.path.dirname(pydev_pysrc.__file__))
        except:
            pass
        self.previous_modules = list(sys.modules.keys())

    def is_module_ignored(self, modname, modpath):
        for path in [sys.prefix] + self.pathlist:
            if modpath.startswith(path):
                return True
        else:
            return set(modname.split(".")) & set(self.namelist)

    def run(self, verbose=False):
        """
        Del user modules to force Python to deeply reload them

        Do not del modules which are considered as system modules, i.e.
        modules installed in subdirectories of Python interpreter's binary
        Do not del C modules
        """
        log = []
        modules_copy = dict(sys.modules)
        for modname, module in modules_copy.items():
            if modname == "aaaaa":
                print(modname, module)
                print(self.previous_modules)
            if modname not in self.previous_modules:
                modpath = getattr(module, "__file__", None)
                if modpath is None:
                    # *module* is a C module that is statically linked into the
                    # interpreter. There is no way to know its path, so we
                    # choose to ignore it.
                    continue
                if not self.is_module_ignored(modname, modpath):
                    log.append(modname)
                    del sys.modules[modname]
        if verbose and log:
            print("\x1b[4;33m%s\x1b[24m%s\x1b[0m" % ("UMD has deleted", ": " + ", ".join(log)))


__umd__ = None

_get_globals_callback = None


def _set_globals_function(get_globals):
    global _get_globals_callback
    _get_globals_callback = get_globals


def _get_globals():
    """Return current Python interpreter globals namespace"""
    if _get_globals_callback is not None:
        return _get_globals_callback()
    else:
        try:
            from __main__ import __dict__ as namespace
        except ImportError:
            try:
                # The import fails on IronPython
                import __main__

                namespace = __main__.__dict__
            except:
                namespace
        shell = namespace.get("__ipythonshell__")
        if shell is not None and hasattr(shell, "user_ns"):
            # IPython 0.12+ kernel
            return shell.user_ns
        else:
            # Python interpreter
            return namespace
        return namespace


def runfile(filename, args=None, wdir=None, namespace=None):
    """
    Run filename
    args: command line arguments (string)
    wdir: working directory
    """
    try:
        if hasattr(filename, "decode"):
            filename = filename.decode("utf-8")
    except (UnicodeError, TypeError):
        pass
    global __umd__
    if os.environ.get("PYDEV_UMD_ENABLED", "").lower() == "true":
        if __umd__ is None:
            namelist = os.environ.get("PYDEV_UMD_NAMELIST", None)
            if namelist is not None:
                namelist = namelist.split(",")
            __umd__ = UserModuleDeleter(namelist=namelist)
        else:
            verbose = os.environ.get("PYDEV_UMD_VERBOSE", "").lower() == "true"
            __umd__.run(verbose=verbose)
    if args is not None and not isinstance(args, (bytes, str)):
        raise TypeError("expected a character buffer object")
    if namespace is None:
        namespace = _get_globals()
    if "__file__" in namespace:
        old_file = namespace["__file__"]
    else:
        old_file = None
    namespace["__file__"] = filename
    sys.argv = [filename]
    if args is not None:
        for arg in args.split():
            sys.argv.append(arg)
    if wdir is not None:
        try:
            if hasattr(wdir, "decode"):
                wdir = wdir.decode("utf-8")
        except (UnicodeError, TypeError):
            pass
        os.chdir(wdir)
    execfile(filename, namespace)
    sys.argv = [""]
    if old_file is None:
        del namespace["__file__"]
    else:
        namespace["__file__"] = old_file

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\commands\scan_cache.py ===
# coding=utf-8
# Copyright 2022-present, the HuggingFace Inc. team.
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
"""Contains command to scan the HF cache directory.

Usage:
    huggingface-cli scan-cache
    huggingface-cli scan-cache -v
    huggingface-cli scan-cache -vvv
    huggingface-cli scan-cache --dir ~/.cache/huggingface/hub
"""

import time
from argparse import Namespace, _SubParsersAction
from typing import Optional

from ..utils import CacheNotFound, HFCacheInfo, scan_cache_dir
from . import BaseHuggingfaceCLICommand
from ._cli_utils import ANSI, tabulate


class ScanCacheCommand(BaseHuggingfaceCLICommand):
    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        scan_cache_parser = parser.add_parser("scan-cache", help="Scan cache directory.")

        scan_cache_parser.add_argument(
            "--dir",
            type=str,
            default=None,
            help="cache directory to scan (optional). Default to the default HuggingFace cache.",
        )
        scan_cache_parser.add_argument(
            "-v",
            "--verbose",
            action="count",
            default=0,
            help="show a more verbose output",
        )
        scan_cache_parser.set_defaults(func=ScanCacheCommand)

    def __init__(self, args: Namespace) -> None:
        self.verbosity: int = args.verbose
        self.cache_dir: Optional[str] = args.dir

    def run(self):
        try:
            t0 = time.time()
            hf_cache_info = scan_cache_dir(self.cache_dir)
            t1 = time.time()
        except CacheNotFound as exc:
            cache_dir = exc.cache_dir
            print(f"Cache directory not found: {cache_dir}")
            return

        self._print_hf_cache_info_as_table(hf_cache_info)

        print(
            f"\nDone in {round(t1 - t0, 1)}s. Scanned {len(hf_cache_info.repos)} repo(s)"
            f" for a total of {ANSI.red(hf_cache_info.size_on_disk_str)}."
        )
        if len(hf_cache_info.warnings) > 0:
            message = f"Got {len(hf_cache_info.warnings)} warning(s) while scanning."
            if self.verbosity >= 3:
                print(ANSI.gray(message))
                for warning in hf_cache_info.warnings:
                    print(ANSI.gray(warning))
            else:
                print(ANSI.gray(message + " Use -vvv to print details."))

    def _print_hf_cache_info_as_table(self, hf_cache_info: HFCacheInfo) -> None:
        print(get_table(hf_cache_info, verbosity=self.verbosity))


def get_table(hf_cache_info: HFCacheInfo, *, verbosity: int = 0) -> str:
    """Generate a table from the [`HFCacheInfo`] object.

    Pass `verbosity=0` to get a table with a single row per repo, with columns
    "repo_id", "repo_type", "size_on_disk", "nb_files", "last_accessed", "last_modified", "refs", "local_path".

    Pass `verbosity=1` to get a table with a row per repo and revision (thus multiple rows can appear for a single repo), with columns
    "repo_id", "repo_type", "revision", "size_on_disk", "nb_files", "last_modified", "refs", "local_path".

    Example:
    ```py
    >>> from huggingface_hub.utils import scan_cache_dir
    >>> from huggingface_hub.commands.scan_cache import get_table

    >>> hf_cache_info = scan_cache_dir()
    HFCacheInfo(...)

    >>> print(get_table(hf_cache_info, verbosity=0))
    REPO ID                                             REPO TYPE SIZE ON DISK NB FILES LAST_ACCESSED LAST_MODIFIED REFS LOCAL PATH
    --------------------------------------------------- --------- ------------ -------- ------------- ------------- ---- --------------------------------------------------------------------------------------------------
    roberta-base                                        model             2.7M        5 1 day ago     1 week ago    main C:\\Users\\admin\\.cache\\huggingface\\hub\\models--roberta-base
    suno/bark                                           model             8.8K        1 1 week ago    1 week ago    main C:\\Users\\admin\\.cache\\huggingface\\hub\\models--suno--bark
    t5-base                                             model           893.8M        4 4 days ago    7 months ago  main C:\\Users\\admin\\.cache\\huggingface\\hub\\models--t5-base
    t5-large                                            model             3.0G        4 5 weeks ago   5 months ago  main C:\\Users\\admin\\.cache\\huggingface\\hub\\models--t5-large

    >>> print(get_table(hf_cache_info, verbosity=1))
    REPO ID                                             REPO TYPE REVISION                                 SIZE ON DISK NB FILES LAST_MODIFIED REFS LOCAL PATH
    --------------------------------------------------- --------- ---------------------------------------- ------------ -------- ------------- ---- -----------------------------------------------------------------------------------------------------------------------------------------------------
    roberta-base                                        model     e2da8e2f811d1448a5b465c236feacd80ffbac7b         2.7M        5 1 week ago    main C:\\Users\\admin\\.cache\\huggingface\\hub\\models--roberta-base\\snapshots\\e2da8e2f811d1448a5b465c236feacd80ffbac7b
    suno/bark                                           model     70a8a7d34168586dc5d028fa9666aceade177992         8.8K        1 1 week ago    main C:\\Users\\admin\\.cache\\huggingface\\hub\\models--suno--bark\\snapshots\\70a8a7d34168586dc5d028fa9666aceade177992
    t5-base                                             model     a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1       893.8M        4 7 months ago  main C:\\Users\\admin\\.cache\\huggingface\\hub\\models--t5-base\\snapshots\\a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1
    t5-large                                            model     150ebc2c4b72291e770f58e6057481c8d2ed331a         3.0G        4 5 months ago  main C:\\Users\\admin\\.cache\\huggingface\\hub\\models--t5-large\\snapshots\\150ebc2c4b72291e770f58e6057481c8d2ed331a                                                 ```
    ```

    Args:
        hf_cache_info ([`HFCacheInfo`]):
            The HFCacheInfo object to print.
        verbosity (`int`, *optional*):
            The verbosity level. Defaults to 0.

    Returns:
        `str`: The table as a string.
    """
    if verbosity == 0:
        return tabulate(
            rows=[
                [
                    repo.repo_id,
                    repo.repo_type,
                    "{:>12}".format(repo.size_on_disk_str),
                    repo.nb_files,
                    repo.last_accessed_str,
                    repo.last_modified_str,
                    ", ".join(sorted(repo.refs)),
                    str(repo.repo_path),
                ]
                for repo in sorted(hf_cache_info.repos, key=lambda repo: repo.repo_path)
            ],
            headers=[
                "REPO ID",
                "REPO TYPE",
                "SIZE ON DISK",
                "NB FILES",
                "LAST_ACCESSED",
                "LAST_MODIFIED",
                "REFS",
                "LOCAL PATH",
            ],
        )
    else:
        return tabulate(
            rows=[
                [
                    repo.repo_id,
                    repo.repo_type,
                    revision.commit_hash,
                    "{:>12}".format(revision.size_on_disk_str),
                    revision.nb_files,
                    revision.last_modified_str,
                    ", ".join(sorted(revision.refs)),
                    str(revision.snapshot_path),
                ]
                for repo in sorted(hf_cache_info.repos, key=lambda repo: repo.repo_path)
                for revision in sorted(repo.revisions, key=lambda revision: revision.commit_hash)
            ],
            headers=[
                "REPO ID",
                "REPO TYPE",
                "REVISION",
                "SIZE ON DISK",
                "NB FILES",
                "LAST_MODIFIED",
                "REFS",
                "LOCAL PATH",
            ],
        )

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\debugger.py ===
import asyncio
import os
import sys

from IPython.core.debugger import Pdb
from IPython.core.completer import IPCompleter
from .ptutils import IPythonPTCompleter
from .shortcuts import create_ipython_shortcuts
from . import embed

from pathlib import Path
from pygments.token import Token
from prompt_toolkit.application import create_app_session
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.history import InMemoryHistory, FileHistory
from concurrent.futures import ThreadPoolExecutor

# we want to avoid ptk as much as possible when using subprocesses
# as it uses cursor positioning requests, deletes color ....
_use_simple_prompt = "IPY_TEST_SIMPLE_PROMPT" in os.environ


class TerminalPdb(Pdb):
    """Standalone IPython debugger."""

    def __init__(self, *args, pt_session_options=None, **kwargs):
        Pdb.__init__(self, *args, **kwargs)
        self._ptcomp = None
        self.pt_init(pt_session_options)
        self.thread_executor = ThreadPoolExecutor(1)

    def pt_init(self, pt_session_options=None):
        """Initialize the prompt session and the prompt loop
        and store them in self.pt_app and self.pt_loop.

        Additional keyword arguments for the PromptSession class
        can be specified in pt_session_options.
        """
        if pt_session_options is None:
            pt_session_options = {}

        def get_prompt_tokens():
            return [(Token.Prompt, self.prompt)]

        if self._ptcomp is None:
            compl = IPCompleter(
                shell=self.shell, namespace={}, global_namespace={}, parent=self.shell
            )
            # add a completer for all the do_ methods
            methods_names = [m[3:] for m in dir(self) if m.startswith("do_")]

            def gen_comp(self, text):
                return [m for m in methods_names if m.startswith(text)]
            import types
            newcomp = types.MethodType(gen_comp, compl)
            compl.custom_matchers.insert(0, newcomp)
            # end add completer.

            self._ptcomp = IPythonPTCompleter(compl)

        # setup history only when we start pdb
        if self.shell.debugger_history is None:
            if self.shell.debugger_history_file is not None:
                p = Path(self.shell.debugger_history_file).expanduser()
                if not p.exists():
                    p.touch()
                self.debugger_history = FileHistory(os.path.expanduser(str(p)))
            else:
                self.debugger_history = InMemoryHistory()
        else:
            self.debugger_history = self.shell.debugger_history

        options = dict(
            message=(lambda: PygmentsTokens(get_prompt_tokens())),
            editing_mode=getattr(EditingMode, self.shell.editing_mode.upper()),
            key_bindings=create_ipython_shortcuts(self.shell),
            history=self.debugger_history,
            completer=self._ptcomp,
            enable_history_search=True,
            mouse_support=self.shell.mouse_support,
            complete_style=self.shell.pt_complete_style,
            style=getattr(self.shell, "style", None),
            color_depth=self.shell.color_depth,
        )

        options.update(pt_session_options)
        if not _use_simple_prompt:
            self.pt_loop = asyncio.new_event_loop()
            self.pt_app = PromptSession(**options)

    def _prompt(self):
        """
        In case other prompt_toolkit apps have to run in parallel to this one (e.g. in madbg),
        create_app_session must be used to prevent mixing up between them. According to the prompt_toolkit docs:

        > If you need multiple applications running at the same time, you have to create a separate
        > `AppSession` using a `with create_app_session():` block.
        """
        with create_app_session():
            return self.pt_app.prompt()

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        override the same methods from cmd.Cmd to provide prompt toolkit replacement.
        """
        if not self.use_rawinput:
            raise ValueError('Sorry ipdb does not support use_rawinput=False')

        # In order to make sure that prompt, which uses asyncio doesn't
        # interfere with applications in which it's used, we always run the
        # prompt itself in a different thread (we can't start an event loop
        # within an event loop). This new thread won't have any event loop
        # running, and here we run our prompt-loop.
        self.preloop()

        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                print(self.intro, file=self.stdout)
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    self._ptcomp.ipy_completer.namespace = self.curframe_locals
                    self._ptcomp.ipy_completer.global_namespace = self.curframe.f_globals

                    # Run the prompt in a different thread.
                    if not _use_simple_prompt:
                        try:
                            line = self.thread_executor.submit(self._prompt).result()
                        except EOFError:
                            line = "EOF"
                    else:
                        line = input("ipdb> ")

                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            self.postloop()
        except Exception:
            raise

    def do_interact(self, arg):
        ipshell = embed.InteractiveShellEmbed(
            config=self.shell.config,
            banner1="*interactive*",
            exit_msg="*exiting interactive console...*",
        )
        global_ns = self.curframe.f_globals
        ipshell(
            module=sys.modules.get(global_ns["__name__"], None),
            local_ns=self.curframe_locals,
        )


def set_trace(frame=None):
    """
    Start debugging from `frame`.

    If frame is not specified, debugging starts from caller's frame.
    """
    TerminalPdb().set_trace(frame or sys._getframe().f_back)


if __name__ == '__main__':
    import pdb
    # IPython.core.debugger.Pdb.trace_dispatch shall not catch
    # bdb.BdbQuit. When started through __main__ and an exception
    # happened after hitting "c", this is needed in order to
    # be able to quit the debugging session (see #9950).
    old_trace_dispatch = pdb.Pdb.trace_dispatch
    pdb.Pdb = TerminalPdb  # type: ignore
    pdb.Pdb.trace_dispatch = old_trace_dispatch  # type: ignore
    pdb.main()

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\packaging.py ===
"""Implementation of packaging-related magic functions.
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2018 The IPython Development Team.
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import functools
import os
import re
import shlex
import sys
from pathlib import Path

from IPython.core.magic import Magics, magics_class, line_magic


def is_conda_environment(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Return True if the current Python executable is in a conda env"""
        # TODO: does this need to change on windows?
        if not Path(sys.prefix, "conda-meta", "history").exists():
            raise ValueError(
                "The python kernel does not appear to be a conda environment.  "
                "Please use ``%pip install`` instead."
            )
        return func(*args, **kwargs)

    return wrapper


def _get_conda_like_executable(command):
    """Find the path to the given executable

    Parameters
    ----------

    executable: string
        Value should be: conda, mamba or micromamba
    """
    # Check for a environment variable bound to the base executable, both conda and mamba
    # set these when activating an environment.
    base_executable = "CONDA_EXE"
    if "mamba" in command.lower():
        base_executable = "MAMBA_EXE"
    if base_executable in os.environ:
        executable = Path(os.environ[base_executable])
        if executable.is_file():
            return str(executable.resolve())

    # Check if there is a conda executable in the same directory as the Python executable.
    # This is the case within conda's root environment.
    executable = Path(sys.executable).parent / command
    if executable.is_file():
        return str(executable)

    # Otherwise, attempt to extract the executable from conda history.
    # This applies in any conda environment. Parsing this way is error prone because
    # different versions of conda and mamba include differing cmd values such as
    # `conda`, `conda-script.py`, or `path/to/conda`, here use the raw command provided.
    history = Path(sys.prefix, "conda-meta", "history").read_text(encoding="utf-8")
    match = re.search(
        rf"^#\s*cmd:\s*(?P<command>.*{command})\s[create|install]",
        history,
        flags=re.MULTILINE,
    )
    if match:
        return match.groupdict()["command"]

    # Fallback: assume the executable is available on the system path.
    return command


CONDA_COMMANDS_REQUIRING_PREFIX = {
    'install', 'list', 'remove', 'uninstall', 'update', 'upgrade',
}
CONDA_COMMANDS_REQUIRING_YES = {
    'install', 'remove', 'uninstall', 'update', 'upgrade',
}
CONDA_ENV_FLAGS = {'-p', '--prefix', '-n', '--name'}
CONDA_YES_FLAGS = {'-y', '--y'}


@magics_class
class PackagingMagics(Magics):
    """Magics related to packaging & installation"""

    @line_magic
    def pip(self, line):
        """Run the pip package manager within the current kernel.

        Usage:
          %pip install [pkgs]
        """
        python = sys.executable
        if sys.platform == "win32":
            python = '"' + python + '"'
        else:
            python = shlex.quote(python)

        self.shell.system(" ".join([python, "-m", "pip", line]))

        print("Note: you may need to restart the kernel to use updated packages.")

    def _run_command(self, cmd, line):
        args = shlex.split(line)
        command = args[0] if len(args) > 0 else ""
        args = args[1:] if len(args) > 1 else [""]

        extra_args = []

        # When the subprocess does not allow us to respond "yes" during the installation,
        # we need to insert --yes in the argument list for some commands
        stdin_disabled = getattr(self.shell, 'kernel', None) is not None
        needs_yes = command in CONDA_COMMANDS_REQUIRING_YES
        has_yes = set(args).intersection(CONDA_YES_FLAGS)
        if stdin_disabled and needs_yes and not has_yes:
            extra_args.append("--yes")

        # Add --prefix to point conda installation to the current environment
        needs_prefix = command in CONDA_COMMANDS_REQUIRING_PREFIX
        has_prefix = set(args).intersection(CONDA_ENV_FLAGS)
        if needs_prefix and not has_prefix:
            extra_args.extend(["--prefix", sys.prefix])

        self.shell.system(" ".join([cmd, command] + extra_args + args))
        print("\nNote: you may need to restart the kernel to use updated packages.")

    @line_magic
    @is_conda_environment
    def conda(self, line):
        """Run the conda package manager within the current kernel.

        Usage:
          %conda install [pkgs]
        """
        conda = _get_conda_like_executable("conda")
        self._run_command(conda, line)

    @line_magic
    @is_conda_environment
    def mamba(self, line):
        """Run the mamba package manager within the current kernel.

        Usage:
          %mamba install [pkgs]
        """
        mamba = _get_conda_like_executable("mamba")
        self._run_command(mamba, line)

    @line_magic
    @is_conda_environment
    def micromamba(self, line):
        """Run the conda package manager within the current kernel.

        Usage:
          %micromamba install [pkgs]
        """
        micromamba = _get_conda_like_executable("micromamba")
        self._run_command(micromamba, line)

    @line_magic
    def uv(self, line):
        """Run the uv package manager within the current kernel.

        Usage:
          %uv pip install [pkgs]
        """
        python = sys.executable
        if sys.platform == "win32":
            python = '"' + python + '"'
        else:
            python = shlex.quote(python)

        self.shell.system(" ".join([python, "-m", "uv", line]))

        print("Note: you may need to restart the kernel to use updated packages.")

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\backend\utils.py ===
import os
import sys
import time
import errno
import signal
import warnings
import subprocess
import traceback

try:
    import psutil
except ImportError:
    psutil = None


def kill_process_tree(process, use_psutil=True):
    """Terminate process and its descendants with SIGKILL"""
    if use_psutil and psutil is not None:
        _kill_process_tree_with_psutil(process)
    else:
        _kill_process_tree_without_psutil(process)


def recursive_terminate(process, use_psutil=True):
    warnings.warn(
        "recursive_terminate is deprecated in loky 3.2, use kill_process_tree"
        "instead",
        DeprecationWarning,
    )
    kill_process_tree(process, use_psutil=use_psutil)


def _kill_process_tree_with_psutil(process):
    try:
        descendants = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        return

    # Kill the descendants in reverse order to avoid killing the parents before
    # the descendant in cases where there are more processes nested.
    for descendant in descendants[::-1]:
        try:
            descendant.kill()
        except psutil.NoSuchProcess:
            pass

    try:
        psutil.Process(process.pid).kill()
    except psutil.NoSuchProcess:
        pass
    process.join()


def _kill_process_tree_without_psutil(process):
    """Terminate a process and its descendants."""
    try:
        if sys.platform == "win32":
            _windows_taskkill_process_tree(process.pid)
        else:
            _posix_recursive_kill(process.pid)
    except Exception:  # pragma: no cover
        details = traceback.format_exc()
        warnings.warn(
            "Failed to kill subprocesses on this platform. Please install"
            "psutil: https://github.com/giampaolo/psutil\n"
            f"Details:\n{details}"
        )
        # In case we cannot introspect or kill the descendants, we fall back to
        # only killing the main process.
        #
        # Note: on Windows, process.kill() is an alias for process.terminate()
        # which in turns calls the Win32 API function TerminateProcess().
        process.kill()
    process.join()


def _windows_taskkill_process_tree(pid):
    # On windows, the taskkill function with option `/T` terminate a given
    # process pid and its children.
    try:
        subprocess.check_output(
            ["taskkill", "/F", "/T", "/PID", str(pid)], stderr=None
        )
    except subprocess.CalledProcessError as e:
        # In Windows, taskkill returns 128, 255 for no process found.
        if e.returncode not in [128, 255]:
            # Let's raise to let the caller log the error details in a
            # warning and only kill the root process.
            raise  # pragma: no cover


def _kill(pid):
    # Not all systems (e.g. Windows) have a SIGKILL, but the C specification
    # mandates a SIGTERM signal. While Windows is handled specifically above,
    # let's try to be safe for other hypothetic platforms that only have
    # SIGTERM without SIGKILL.
    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
    try:
        os.kill(pid, kill_signal)
    except OSError as e:
        # if OSError is raised with [Errno 3] no such process, the process
        # is already terminated, else, raise the error and let the top
        # level function raise a warning and retry to kill the process.
        if e.errno != errno.ESRCH:
            raise  # pragma: no cover


def _posix_recursive_kill(pid):
    """Recursively kill the descendants of a process before killing it."""
    try:
        children_pids = subprocess.check_output(
            ["pgrep", "-P", str(pid)], stderr=None, text=True
        )
    except subprocess.CalledProcessError as e:
        # `ps` returns 1 when no child process has been found
        if e.returncode == 1:
            children_pids = ""
        else:
            raise  # pragma: no cover

    # Decode the result, split the cpid and remove the trailing line
    for cpid in children_pids.splitlines():
        cpid = int(cpid)
        _posix_recursive_kill(cpid)

    _kill(pid)


def get_exitcodes_terminated_worker(processes):
    """Return a formatted string with the exitcodes of terminated workers.

    If necessary, wait (up to .25s) for the system to correctly set the
    exitcode of one terminated worker.
    """
    patience = 5

    # Catch the exitcode of the terminated workers. There should at least be
    # one. If not, wait a bit for the system to correctly set the exitcode of
    # the terminated worker.
    exitcodes = [
        p.exitcode for p in list(processes.values()) if p.exitcode is not None
    ]
    while not exitcodes and patience > 0:
        patience -= 1
        exitcodes = [
            p.exitcode
            for p in list(processes.values())
            if p.exitcode is not None
        ]
        time.sleep(0.05)

    return _format_exitcodes(exitcodes)


def _format_exitcodes(exitcodes):
    """Format a list of exit code with names of the signals if possible"""
    str_exitcodes = [
        f"{_get_exitcode_name(e)}({e})" for e in exitcodes if e is not None
    ]
    return "{" + ", ".join(str_exitcodes) + "}"


def _get_exitcode_name(exitcode):
    if sys.platform == "win32":
        # The exitcode are unreliable  on windows (see bpo-31863).
        # For this case, return UNKNOWN
        return "UNKNOWN"

    if exitcode < 0:
        try:
            import signal

            return signal.Signals(-exitcode).name
        except ValueError:
            return "UNKNOWN"
    elif exitcode != 255:
        # The exitcode are unreliable on forkserver were 255 is always returned
        # (see bpo-30589). For this case, return UNKNOWN
        return "EXIT"

    return "UNKNOWN"

# === NexusCore/openenv\Lib\site-packages\litellm\llms\cohere\embed\handler.py ===
"""
Legacy /v1/embedding handler for Bedrock Cohere. 
"""

import json
from typing import Any, Callable, Optional, Union

import httpx

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.types.llms.bedrock import CohereEmbeddingRequest
from litellm.types.utils import EmbeddingResponse

from .v1_transformation import CohereEmbeddingConfig


def validate_environment(api_key, headers: dict):
    headers.update(
        {
            "Request-Source": "unspecified:litellm",
            "accept": "application/json",
            "content-type": "application/json",
        }
    )
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


class CohereError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(
            method="POST", url="https://api.cohere.ai/v1/generate"
        )
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


async def async_embedding(
    model: str,
    data: Union[dict, CohereEmbeddingRequest],
    input: list,
    model_response: litellm.utils.EmbeddingResponse,
    timeout: Optional[Union[float, httpx.Timeout]],
    logging_obj: LiteLLMLoggingObj,
    optional_params: dict,
    api_base: str,
    api_key: Optional[str],
    headers: dict,
    encoding: Callable,
    client: Optional[AsyncHTTPHandler] = None,
):
    ## LOGGING
    logging_obj.pre_call(
        input=input,
        api_key=api_key,
        additional_args={
            "complete_input_dict": data,
            "headers": headers,
            "api_base": api_base,
        },
    )
    ## COMPLETION CALL

    if client is None:
        client = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.COHERE,
            params={"timeout": timeout},
        )

    try:
        response = await client.post(api_base, headers=headers, data=json.dumps(data))
    except httpx.HTTPStatusError as e:
        ## LOGGING
        logging_obj.post_call(
            input=input,
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=e.response.text,
        )
        raise e
    except Exception as e:
        ## LOGGING
        logging_obj.post_call(
            input=input,
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=str(e),
        )
        raise e

    ## PROCESS RESPONSE ##
    return CohereEmbeddingConfig()._transform_response(
        response=response,
        api_key=api_key,
        logging_obj=logging_obj,
        data=data,
        model_response=model_response,
        model=model,
        encoding=encoding,
        input=input,
    )


def embedding(
    model: str,
    input: list,
    model_response: EmbeddingResponse,
    logging_obj: LiteLLMLoggingObj,
    optional_params: dict,
    headers: dict,
    encoding: Any,
    data: Optional[Union[dict, CohereEmbeddingRequest]] = None,
    complete_api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    aembedding: Optional[bool] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = httpx.Timeout(None),
    client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
):
    headers = validate_environment(api_key, headers=headers)
    embed_url = complete_api_base or "https://api.cohere.ai/v1/embed"
    model = model

    data = data or CohereEmbeddingConfig()._transform_request(
        model=model, input=input, inference_params=optional_params
    )

    ## ROUTING
    if aembedding is True:
        return async_embedding(
            model=model,
            data=data,
            input=input,
            model_response=model_response,
            timeout=timeout,
            logging_obj=logging_obj,
            optional_params=optional_params,
            api_base=embed_url,
            api_key=api_key,
            headers=headers,
            encoding=encoding,
            client=(
                client
                if client is not None and isinstance(client, AsyncHTTPHandler)
                else None
            ),
        )

    ## LOGGING
    logging_obj.pre_call(
        input=input,
        api_key=api_key,
        additional_args={"complete_input_dict": data},
    )

    ## COMPLETION CALL
    if client is None or not isinstance(client, HTTPHandler):
        client = HTTPHandler(concurrent_limit=1)

    response = client.post(embed_url, headers=headers, data=json.dumps(data))

    return CohereEmbeddingConfig()._transform_response(
        response=response,
        api_key=api_key,
        logging_obj=logging_obj,
        data=data,
        model_response=model_response,
        model=model,
        encoding=encoding,
        input=input,
    )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\topaz\image_variations\transformation.py ===
import base64
import time
from io import BytesIO
from typing import Any, List, Mapping, Optional, Tuple, Union

from aiohttp import ClientResponse
from httpx import Headers, Response

from litellm.llms.base_llm.chat.transformation import (
    BaseLLMException,
    LiteLLMLoggingObj,
)
from litellm.types.llms.openai import OpenAIImageVariationOptionalParams
from litellm.types.utils import (
    FileTypes,
    HttpHandlerRequestFields,
    ImageObject,
    ImageResponse,
)

from ...base_llm.image_variations.transformation import BaseImageVariationConfig
from ..common_utils import TopazException, TopazModelInfo


class TopazImageVariationConfig(TopazModelInfo, BaseImageVariationConfig):
    def get_supported_openai_params(
        self, model: str
    ) -> List[OpenAIImageVariationOptionalParams]:
        return ["response_format", "size"]

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        api_base = api_base or "https://api.topazlabs.com"
        return f"{api_base}/image/v1/enhance"

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for k, v in non_default_params.items():
            if k == "response_format":
                optional_params["output_format"] = v
            elif k == "size":
                split_v = v.split("x")
                assert len(split_v) == 2, "size must be in the format of widthxheight"
                optional_params["output_width"] = split_v[0]
                optional_params["output_height"] = split_v[1]
        return optional_params

    def prepare_file_tuple(
        self,
        file_data: FileTypes,
    ) -> Tuple[str, Optional[FileTypes], str, Mapping[str, str]]:
        """
        Convert various file input formats to a consistent tuple format for HTTPX
        Returns: (filename, file_content, content_type, headers)
        """
        # Default values
        filename = "image.png"
        content: Optional[FileTypes] = None
        content_type = "image/png"
        headers: Mapping[str, str] = {}

        if isinstance(file_data, (bytes, BytesIO)):
            # Case 1: Just file content
            content = file_data
        elif isinstance(file_data, tuple):
            if len(file_data) == 2:
                # Case 2: (filename, content)
                filename = file_data[0] or filename
                content = file_data[1]
            elif len(file_data) == 3:
                # Case 3: (filename, content, content_type)
                filename = file_data[0] or filename
                content = file_data[1]
                content_type = file_data[2] or content_type
            elif len(file_data) == 4:
                # Case 4: (filename, content, content_type, headers)
                filename = file_data[0] or filename
                content = file_data[1]
                content_type = file_data[2] or content_type
                headers = file_data[3]

        return (filename, content, content_type, headers)

    def transform_request_image_variation(
        self,
        model: Optional[str],
        image: FileTypes,
        optional_params: dict,
        headers: dict,
    ) -> HttpHandlerRequestFields:
        request_params = HttpHandlerRequestFields(
            files={"image": self.prepare_file_tuple(image)},
            data=optional_params,
        )

        return request_params

    def _common_transform_response_image_variation(
        self,
        image_content: bytes,
        response_ms: float,
    ) -> ImageResponse:
        # Convert to base64
        base64_image = base64.b64encode(image_content).decode("utf-8")

        return ImageResponse(
            created=int(time.time()),
            data=[
                ImageObject(
                    b64_json=base64_image,
                    url=None,
                    revised_prompt=None,
                )
            ],
            response_ms=response_ms,
        )

    async def async_transform_response_image_variation(
        self,
        model: Optional[str],
        raw_response: ClientResponse,
        model_response: ImageResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        image: FileTypes,
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
    ) -> ImageResponse:
        image_content = await raw_response.read()

        response_ms = logging_obj.get_response_ms()

        return self._common_transform_response_image_variation(
            image_content, response_ms
        )

    def transform_response_image_variation(
        self,
        model: Optional[str],
        raw_response: Response,
        model_response: ImageResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        image: FileTypes,
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
    ) -> ImageResponse:
        image_content = raw_response.content

        response_ms = (
            raw_response.elapsed.total_seconds() * 1000
        )  # Convert to milliseconds

        return self._common_transform_response_image_variation(
            image_content, response_ms
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return TopazException(
            status_code=status_code,
            message=error_message,
            headers=headers,
        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\gemini_embeddings\batch_embed_content_handler.py ===
"""
Google AI Studio /batchEmbedContents Embeddings Endpoint
"""

import json
from typing import Any, Literal, Optional, Union

import httpx

import litellm
from litellm import EmbeddingResponse
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.types.llms.openai import EmbeddingInput
from litellm.types.llms.vertex_ai import (
    VertexAIBatchEmbeddingsRequestBody,
    VertexAIBatchEmbeddingsResponseObject,
)

from ..gemini.vertex_and_google_ai_studio_gemini import VertexLLM
from .batch_embed_content_transformation import (
    process_response,
    transform_openai_input_gemini_content,
)


class GoogleBatchEmbeddings(VertexLLM):
    def batch_embeddings(
        self,
        model: str,
        input: EmbeddingInput,
        print_verbose,
        model_response: EmbeddingResponse,
        custom_llm_provider: Literal["gemini", "vertex_ai"],
        optional_params: dict,
        logging_obj: Any,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        encoding=None,
        vertex_project=None,
        vertex_location=None,
        vertex_credentials=None,
        aembedding=False,
        timeout=300,
        client=None,
    ) -> EmbeddingResponse:
        _auth_header, vertex_project = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider=custom_llm_provider,
        )

        auth_header, url = self._get_token_and_url(
            model=model,
            auth_header=_auth_header,
            gemini_api_key=api_key,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=None,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            should_use_v1beta1_features=False,
            mode="batch_embedding",
        )

        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    _httpx_timeout = httpx.Timeout(timeout)
                    _params["timeout"] = _httpx_timeout
            else:
                _params["timeout"] = httpx.Timeout(timeout=600.0, connect=5.0)

            sync_handler: HTTPHandler = HTTPHandler(**_params)  # type: ignore
        else:
            sync_handler = client  # type: ignore

        optional_params = optional_params or {}

        ### TRANSFORMATION ###
        request_data = transform_openai_input_gemini_content(
            input=input, model=model, optional_params=optional_params
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key="",
            additional_args={
                "complete_input_dict": request_data,
                "api_base": url,
                "headers": headers,
            },
        )

        if aembedding is True:
            return self.async_batch_embeddings(  # type: ignore
                model=model,
                api_base=api_base,
                url=url,
                data=request_data,
                model_response=model_response,
                timeout=timeout,
                headers=headers,
                input=input,
            )

        response = sync_handler.post(
            url=url,
            headers=headers,
            data=json.dumps(request_data),
        )

        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        _json_response = response.json()
        _predictions = VertexAIBatchEmbeddingsResponseObject(**_json_response)  # type: ignore

        return process_response(
            model=model,
            model_response=model_response,
            _predictions=_predictions,
            input=input,
        )

    async def async_batch_embeddings(
        self,
        model: str,
        api_base: Optional[str],
        url: str,
        data: VertexAIBatchEmbeddingsRequestBody,
        model_response: EmbeddingResponse,
        input: EmbeddingInput,
        timeout: Optional[Union[float, httpx.Timeout]],
        headers={},
        client: Optional[AsyncHTTPHandler] = None,
    ) -> EmbeddingResponse:
        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    _httpx_timeout = httpx.Timeout(timeout)
                    _params["timeout"] = _httpx_timeout
            else:
                _params["timeout"] = httpx.Timeout(timeout=600.0, connect=5.0)

            async_handler: AsyncHTTPHandler = get_async_httpx_client(
                llm_provider=litellm.LlmProviders.VERTEX_AI,
                params={"timeout": timeout},
            )
        else:
            async_handler = client  # type: ignore

        response = await async_handler.post(
            url=url,
            headers=headers,
            data=json.dumps(data),
        )

        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        _json_response = response.json()
        _predictions = VertexAIBatchEmbeddingsResponseObject(**_json_response)  # type: ignore

        return process_response(
            model=model,
            model_response=model_response,
            _predictions=_predictions,
            input=input,
        )

# === NexusCore/openenv\Lib\site-packages\pip\_internal\operations\check.py ===
"""Validation of dependencies of packages
"""

import logging
from contextlib import suppress
from email.parser import Parser
from functools import reduce
from typing import (
    Callable,
    Dict,
    FrozenSet,
    Generator,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
)

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.tags import Tag, parse_tag
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.distributions import make_distribution_for_install_requirement
from pip._internal.metadata import get_default_environment
from pip._internal.metadata.base import BaseDistribution
from pip._internal.req.req_install import InstallRequirement

logger = logging.getLogger(__name__)


class PackageDetails(NamedTuple):
    version: Version
    dependencies: List[Requirement]


# Shorthands
PackageSet = Dict[NormalizedName, PackageDetails]
Missing = Tuple[NormalizedName, Requirement]
Conflicting = Tuple[NormalizedName, Version, Requirement]

MissingDict = Dict[NormalizedName, List[Missing]]
ConflictingDict = Dict[NormalizedName, List[Conflicting]]
CheckResult = Tuple[MissingDict, ConflictingDict]
ConflictDetails = Tuple[PackageSet, CheckResult]


def create_package_set_from_installed() -> Tuple[PackageSet, bool]:
    """Converts a list of distributions into a PackageSet."""
    package_set = {}
    problems = False
    env = get_default_environment()
    for dist in env.iter_installed_distributions(local_only=False, skip=()):
        name = dist.canonical_name
        try:
            dependencies = list(dist.iter_dependencies())
            package_set[name] = PackageDetails(dist.version, dependencies)
        except (OSError, ValueError) as e:
            # Don't crash on unreadable or broken metadata.
            logger.warning("Error parsing dependencies of %s: %s", name, e)
            problems = True
    return package_set, problems


def check_package_set(
    package_set: PackageSet, should_ignore: Optional[Callable[[str], bool]] = None
) -> CheckResult:
    """Check if a package set is consistent

    If should_ignore is passed, it should be a callable that takes a
    package name and returns a boolean.
    """

    missing = {}
    conflicting = {}

    for package_name, package_detail in package_set.items():
        # Info about dependencies of package_name
        missing_deps: Set[Missing] = set()
        conflicting_deps: Set[Conflicting] = set()

        if should_ignore and should_ignore(package_name):
            continue

        for req in package_detail.dependencies:
            name = canonicalize_name(req.name)

            # Check if it's missing
            if name not in package_set:
                missed = True
                if req.marker is not None:
                    missed = req.marker.evaluate({"extra": ""})
                if missed:
                    missing_deps.add((name, req))
                continue

            # Check if there's a conflict
            version = package_set[name].version
            if not req.specifier.contains(version, prereleases=True):
                conflicting_deps.add((name, version, req))

        if missing_deps:
            missing[package_name] = sorted(missing_deps, key=str)
        if conflicting_deps:
            conflicting[package_name] = sorted(conflicting_deps, key=str)

    return missing, conflicting


def check_install_conflicts(to_install: List[InstallRequirement]) -> ConflictDetails:
    """For checking if the dependency graph would be consistent after \
    installing given requirements
    """
    # Start from the current state
    package_set, _ = create_package_set_from_installed()
    # Install packages
    would_be_installed = _simulate_installation_of(to_install, package_set)

    # Only warn about directly-dependent packages; create a whitelist of them
    whitelist = _create_whitelist(would_be_installed, package_set)

    return (
        package_set,
        check_package_set(
            package_set, should_ignore=lambda name: name not in whitelist
        ),
    )


def check_unsupported(
    packages: Iterable[BaseDistribution],
    supported_tags: Iterable[Tag],
) -> Generator[BaseDistribution, None, None]:
    for p in packages:
        with suppress(FileNotFoundError):
            wheel_file = p.read_text("WHEEL")
            wheel_tags: FrozenSet[Tag] = reduce(
                frozenset.union,
                map(parse_tag, Parser().parsestr(wheel_file).get_all("Tag", [])),
                frozenset(),
            )
            if wheel_tags.isdisjoint(supported_tags):
                yield p


def _simulate_installation_of(
    to_install: List[InstallRequirement], package_set: PackageSet
) -> Set[NormalizedName]:
    """Computes the version of packages after installing to_install."""
    # Keep track of packages that were installed
    installed = set()

    # Modify it as installing requirement_set would (assuming no errors)
    for inst_req in to_install:
        abstract_dist = make_distribution_for_install_requirement(inst_req)
        dist = abstract_dist.get_metadata_distribution()
        name = dist.canonical_name
        package_set[name] = PackageDetails(dist.version, list(dist.iter_dependencies()))

        installed.add(name)

    return installed


def _create_whitelist(
    would_be_installed: Set[NormalizedName], package_set: PackageSet
) -> Set[NormalizedName]:
    packages_affected = set(would_be_installed)

    for package_name in package_set:
        if package_name in packages_affected:
            continue

        for req in package_set[package_name].dependencies:
            if canonicalize_name(req.name) in packages_affected:
                packages_affected.add(package_name)
                break

    return packages_affected

# === NexusCore/openenv\Lib\site-packages\win32com\servers\test_pycomtest.py ===
# This is part of the Python test suite.
# The object is registered when you first run the test suite.
# (and hopefully unregistered once done ;-)

import pythoncom
import winerror

# Ensure the vtables in the tlb are known.
from win32com.client import constants, gencache
from win32com.server.exception import COMException
from win32com.server.util import wrap

pythoncom.__future_currency__ = True
# We use the constants from the module, so must insist on a gencache.
# Otherwise, use of gencache is not necessary (tho still advised)
gencache.EnsureModule("{6BCDCB60-5605-11D0-AE5F-CADD4C000000}", 0, 1, 1)


class PyCOMTest:
    _typelib_guid_ = "{6BCDCB60-5605-11D0-AE5F-CADD4C000000}"
    _typelib_version = 1, 0
    _com_interfaces_ = ["IPyCOMTest"]
    _reg_clsid_ = "{e743d9cd-cb03-4b04-b516-11d3a81c1597}"
    _reg_progid_ = "Python.Test.PyCOMTest"

    def DoubleString(self, str):
        return str * 2

    def DoubleInOutString(self, str):
        return str * 2

    def Fire(self, nID):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetLastVarArgs(self):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetMultipleInterfaces(self, outinterface1, outinterface2):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetSafeArrays(self, attrs, attrs2, ints):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetSetDispatch(self, indisp):
        raise COMException(hresult=winerror.E_NOTIMPL)

    # Result is of type IPyCOMTest
    def GetSetInterface(self, ininterface):
        return wrap(self)

    def GetSetVariant(self, indisp):
        return indisp

    def TestByRefVariant(self, v):
        return v * 2

    def TestByRefString(self, v):
        return v * 2

    # Result is of type IPyCOMTest
    def GetSetInterfaceArray(self, ininterface):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetSetUnknown(self, inunk):
        raise COMException(hresult=winerror.E_NOTIMPL)

    # Result is of type ISimpleCounter
    def GetSimpleCounter(self):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetSimpleSafeArray(self, ints):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetStruct(self):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def SetIntSafeArray(self, ints):
        return len(ints)

    def SetLongLongSafeArray(self, ints):
        return len(ints)

    def SetULongLongSafeArray(self, ints):
        return len(ints)

    def SetBinSafeArray(self, buf):
        return len(buf)

    def SetVarArgs(self, *args):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def SetVariantSafeArray(self, vars):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def Start(self):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def Stop(self, nID):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def StopAll(self):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def TakeByRefDispatch(self, inout):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def TakeByRefTypedDispatch(self, inout):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def Test(self, key, inval):
        return not inval

    def Test2(self, inval):
        return inval

    def Test3(self, inval):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def Test4(self, inval):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def Test5(self, inout):
        if inout == constants.TestAttr1:
            return constants.TestAttr1_1
        elif inout == constants.TestAttr1_1:
            return constants.TestAttr1
        else:
            return -1

    def Test6(self, inval):
        return inval

    def TestInOut(self, fval, bval, lval):
        return winerror.S_OK, fval * 2, not bval, lval * 2

    def TestOptionals(self, strArg="def", sval=0, lval=1, dval=3.1400001049041748):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def TestOptionals2(self, dval, strval="", sval=1):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def CheckVariantSafeArray(self, data):
        return 1

    def LongProp(self):
        return self.longval

    def SetLongProp(self, val):
        self.longval = val

    def ULongProp(self):
        return self.ulongval

    def SetULongProp(self, val):
        self.ulongval = val

    def IntProp(self):
        return self.intval

    def SetIntProp(self, val):
        self.intval = val


class PyCOMTestMI(PyCOMTest):
    _typelib_guid_ = "{6BCDCB60-5605-11D0-AE5F-CADD4C000000}"
    _typelib_version = 1, 0
    # Interfaces with a interface name, a real IID, and an IID as a string
    _com_interfaces_ = [
        "IPyCOMTest",
        pythoncom.IID_IStream,
        str(pythoncom.IID_IStorage),
    ]
    _reg_clsid_ = "{F506E9A1-FB46-4238-A597-FA4EB69787CA}"
    _reg_progid_ = "Python.Test.PyCOMTestMI"


if __name__ == "__main__":
    import win32com.server.register

    win32com.server.register.UseCommandLine(PyCOMTest)
    win32com.server.register.UseCommandLine(PyCOMTestMI)

# === NexusCore/openenv\Lib\site-packages\colorama\win32.py ===
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.

# from winbase.h
STDOUT = -11
STDERR = -12

ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

try:
    import ctypes
    from ctypes import LibraryLoader
    windll = LibraryLoader(ctypes.WinDLL)
    from ctypes import wintypes
except (AttributeError, ImportError):
    windll = None
    SetConsoleTextAttribute = lambda *_: None
    winapi_test = lambda *_: None
else:
    from ctypes import byref, Structure, c_char, POINTER

    COORD = wintypes._COORD

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", wintypes.WORD),
            ("srWindow", wintypes.SMALL_RECT),
            ("dwMaximumWindowSize", COORD),
        ]
        def __str__(self):
            return '(%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d)' % (
                self.dwSize.Y, self.dwSize.X
                , self.dwCursorPosition.Y, self.dwCursorPosition.X
                , self.wAttributes
                , self.srWindow.Top, self.srWindow.Left, self.srWindow.Bottom, self.srWindow.Right
                , self.dwMaximumWindowSize.Y, self.dwMaximumWindowSize.X
            )

    _GetStdHandle = windll.kernel32.GetStdHandle
    _GetStdHandle.argtypes = [
        wintypes.DWORD,
    ]
    _GetStdHandle.restype = wintypes.HANDLE

    _GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
    _GetConsoleScreenBufferInfo.argtypes = [
        wintypes.HANDLE,
        POINTER(CONSOLE_SCREEN_BUFFER_INFO),
    ]
    _GetConsoleScreenBufferInfo.restype = wintypes.BOOL

    _SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
    _SetConsoleTextAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
    ]
    _SetConsoleTextAttribute.restype = wintypes.BOOL

    _SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition
    _SetConsoleCursorPosition.argtypes = [
        wintypes.HANDLE,
        COORD,
    ]
    _SetConsoleCursorPosition.restype = wintypes.BOOL

    _FillConsoleOutputCharacterA = windll.kernel32.FillConsoleOutputCharacterA
    _FillConsoleOutputCharacterA.argtypes = [
        wintypes.HANDLE,
        c_char,
        wintypes.DWORD,
        COORD,
        POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputCharacterA.restype = wintypes.BOOL

    _FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
    _FillConsoleOutputAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
        wintypes.DWORD,
        COORD,
        POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputAttribute.restype = wintypes.BOOL

    _SetConsoleTitleW = windll.kernel32.SetConsoleTitleW
    _SetConsoleTitleW.argtypes = [
        wintypes.LPCWSTR
    ]
    _SetConsoleTitleW.restype = wintypes.BOOL

    _GetConsoleMode = windll.kernel32.GetConsoleMode
    _GetConsoleMode.argtypes = [
        wintypes.HANDLE,
        POINTER(wintypes.DWORD)
    ]
    _GetConsoleMode.restype = wintypes.BOOL

    _SetConsoleMode = windll.kernel32.SetConsoleMode
    _SetConsoleMode.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD
    ]
    _SetConsoleMode.restype = wintypes.BOOL

    def _winapi_test(handle):
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        success = _GetConsoleScreenBufferInfo(
            handle, byref(csbi))
        return bool(success)

    def winapi_test():
        return any(_winapi_test(h) for h in
                   (_GetStdHandle(STDOUT), _GetStdHandle(STDERR)))

    def GetConsoleScreenBufferInfo(stream_id=STDOUT):
        handle = _GetStdHandle(stream_id)
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        success = _GetConsoleScreenBufferInfo(
            handle, byref(csbi))
        return csbi

    def SetConsoleTextAttribute(stream_id, attrs):
        handle = _GetStdHandle(stream_id)
        return _SetConsoleTextAttribute(handle, attrs)

    def SetConsoleCursorPosition(stream_id, position, adjust=True):
        position = COORD(*position)
        # If the position is out of range, do nothing.
        if position.Y <= 0 or position.X <= 0:
            return
        # Adjust for Windows' SetConsoleCursorPosition:
        #    1. being 0-based, while ANSI is 1-based.
        #    2. expecting (x,y), while ANSI uses (y,x).
        adjusted_position = COORD(position.Y - 1, position.X - 1)
        if adjust:
            # Adjust for viewport's scroll position
            sr = GetConsoleScreenBufferInfo(STDOUT).srWindow
            adjusted_position.Y += sr.Top
            adjusted_position.X += sr.Left
        # Resume normal processing
        handle = _GetStdHandle(stream_id)
        return _SetConsoleCursorPosition(handle, adjusted_position)

    def FillConsoleOutputCharacter(stream_id, char, length, start):
        handle = _GetStdHandle(stream_id)
        char = c_char(char.encode())
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        success = _FillConsoleOutputCharacterA(
            handle, char, length, start, byref(num_written))
        return num_written.value

    def FillConsoleOutputAttribute(stream_id, attr, length, start):
        ''' FillConsoleOutputAttribute( hConsole, csbi.wAttributes, dwConSize, coordScreen, &cCharsWritten )'''
        handle = _GetStdHandle(stream_id)
        attribute = wintypes.WORD(attr)
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        return _FillConsoleOutputAttribute(
            handle, attribute, length, start, byref(num_written))

    def SetConsoleTitle(title):
        return _SetConsoleTitleW(title)

    def GetConsoleMode(handle):
        mode = wintypes.DWORD()
        success = _GetConsoleMode(handle, byref(mode))
        if not success:
            raise ctypes.WinError()
        return mode.value

    def SetConsoleMode(handle, mode):
        success = _SetConsoleMode(handle, mode)
        if not success:
            raise ctypes.WinError()

# === NexusCore/openenv\Lib\site-packages\markdown_it\token.py ===
from __future__ import annotations

from collections.abc import Callable, MutableMapping
import dataclasses as dc
from typing import Any, Literal
import warnings

from markdown_it._compat import DATACLASS_KWARGS


def convert_attrs(value: Any) -> Any:
    """Convert Token.attrs set as ``None`` or ``[[key, value], ...]`` to a dict.

    This improves compatibility with upstream markdown-it.
    """
    if not value:
        return {}
    if isinstance(value, list):
        return dict(value)
    return value


@dc.dataclass(**DATACLASS_KWARGS)
class Token:
    type: str
    """Type of the token (string, e.g. "paragraph_open")"""

    tag: str
    """HTML tag name, e.g. 'p'"""

    nesting: Literal[-1, 0, 1]
    """Level change (number in {-1, 0, 1} set), where:
    -  `1` means the tag is opening
    -  `0` means the tag is self-closing
    - `-1` means the tag is closing
    """

    attrs: dict[str, str | int | float] = dc.field(default_factory=dict)
    """HTML attributes.
    Note this differs from the upstream "list of lists" format,
    although than an instance can still be initialised with this format.
    """

    map: list[int] | None = None
    """Source map info. Format: `[ line_begin, line_end ]`"""

    level: int = 0
    """Nesting level, the same as `state.level`"""

    children: list[Token] | None = None
    """Array of child nodes (inline and img tokens)."""

    content: str = ""
    """Inner content, in the case of a self-closing tag (code, html, fence, etc.),"""

    markup: str = ""
    """'*' or '_' for emphasis, fence string for fence, etc."""

    info: str = ""
    """Additional information:
    - Info string for "fence" tokens
    - The value "auto" for autolink "link_open" and "link_close" tokens
    - The string value of the item marker for ordered-list "list_item_open" tokens
    """

    meta: dict[Any, Any] = dc.field(default_factory=dict)
    """A place for plugins to store any arbitrary data"""

    block: bool = False
    """True for block-level tokens, false for inline tokens.
    Used in renderer to calculate line breaks
    """

    hidden: bool = False
    """If true, ignore this element when rendering.
    Used for tight lists to hide paragraphs.
    """

    def __post_init__(self) -> None:
        self.attrs = convert_attrs(self.attrs)

    def attrIndex(self, name: str) -> int:
        warnings.warn(  # noqa: B028
            "Token.attrIndex should not be used, since Token.attrs is a dictionary",
            UserWarning,
        )
        if name not in self.attrs:
            return -1
        return list(self.attrs.keys()).index(name)

    def attrItems(self) -> list[tuple[str, str | int | float]]:
        """Get (key, value) list of attrs."""
        return list(self.attrs.items())

    def attrPush(self, attrData: tuple[str, str | int | float]) -> None:
        """Add `[ name, value ]` attribute to list. Init attrs if necessary."""
        name, value = attrData
        self.attrSet(name, value)

    def attrSet(self, name: str, value: str | int | float) -> None:
        """Set `name` attribute to `value`. Override old value if exists."""
        self.attrs[name] = value

    def attrGet(self, name: str) -> None | str | int | float:
        """Get the value of attribute `name`, or null if it does not exist."""
        return self.attrs.get(name, None)

    def attrJoin(self, name: str, value: str) -> None:
        """Join value to existing attribute via space.
        Or create new attribute if not exists.
        Useful to operate with token classes.
        """
        if name in self.attrs:
            current = self.attrs[name]
            if not isinstance(current, str):
                raise TypeError(
                    f"existing attr 'name' is not a str: {self.attrs[name]}"
                )
            self.attrs[name] = f"{current} {value}"
        else:
            self.attrs[name] = value

    def copy(self, **changes: Any) -> Token:
        """Return a shallow copy of the instance."""
        return dc.replace(self, **changes)

    def as_dict(
        self,
        *,
        children: bool = True,
        as_upstream: bool = True,
        meta_serializer: Callable[[dict[Any, Any]], Any] | None = None,
        filter: Callable[[str, Any], bool] | None = None,
        dict_factory: Callable[..., MutableMapping[str, Any]] = dict,
    ) -> MutableMapping[str, Any]:
        """Return the token as a dictionary.

        :param children: Also convert children to dicts
        :param as_upstream: Ensure the output dictionary is equal to that created by markdown-it
            For example, attrs are converted to null or lists
        :param meta_serializer: hook for serializing ``Token.meta``
        :param filter: A callable whose return code determines whether an
            attribute or element is included (``True``) or dropped (``False``).
            Is called with the (key, value) pair.
        :param dict_factory: A callable to produce dictionaries from.
            For example, to produce ordered dictionaries instead of normal Python
            dictionaries, pass in ``collections.OrderedDict``.

        """
        mapping = dict_factory((f.name, getattr(self, f.name)) for f in dc.fields(self))
        if filter:
            mapping = dict_factory((k, v) for k, v in mapping.items() if filter(k, v))
        if as_upstream and "attrs" in mapping:
            mapping["attrs"] = (
                None
                if not mapping["attrs"]
                else [[k, v] for k, v in mapping["attrs"].items()]
            )
        if meta_serializer and "meta" in mapping:
            mapping["meta"] = meta_serializer(mapping["meta"])
        if children and mapping.get("children", None):
            mapping["children"] = [
                child.as_dict(
                    children=children,
                    filter=filter,
                    dict_factory=dict_factory,
                    as_upstream=as_upstream,
                    meta_serializer=meta_serializer,
                )
                for child in mapping["children"]
            ]
        return mapping

    @classmethod
    def from_dict(cls, dct: MutableMapping[str, Any]) -> Token:
        """Convert a dict to a Token."""
        token = cls(**dct)
        if token.children:
            token.children = [cls.from_dict(c) for c in token.children]  # type: ignore[arg-type]
        return token

# === NexusCore/openenv\Lib\site-packages\trio\_highlevel_ssl_helpers.py ===
from __future__ import annotations

import ssl
from typing import TYPE_CHECKING, NoReturn, TypeVar

import trio

from ._highlevel_open_tcp_stream import DEFAULT_DELAY

T = TypeVar("T")

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from ._highlevel_socket import SocketStream


# It might have been nice to take a ssl_protocols= argument here to set up
# NPN/ALPN, but to do this we have to mutate the context object, which is OK
# if it's one we created, but not OK if it's one that was passed in... and
# the one major protocol using NPN/ALPN is HTTP/2, which mandates that you use
# a specially configured SSLContext anyway! I also thought maybe we could copy
# the given SSLContext and then mutate the copy, but it's no good as SSLContext
# objects can't be copied: https://bugs.python.org/issue33023.
# So... let's punt on that for now. Hopefully we'll be getting a new Python
# TLS API soon and can revisit this then.
async def open_ssl_over_tcp_stream(
    host: str | bytes,
    port: int,
    *,
    https_compatible: bool = False,
    ssl_context: ssl.SSLContext | None = None,
    happy_eyeballs_delay: float | None = DEFAULT_DELAY,
) -> trio.SSLStream[SocketStream]:
    """Make a TLS-encrypted Connection to the given host and port over TCP.

    This is a convenience wrapper that calls :func:`open_tcp_stream` and
    wraps the result in an :class:`~trio.SSLStream`.

    This function does not perform the TLS handshake; you can do it
    manually by calling :meth:`~trio.SSLStream.do_handshake`, or else
    it will be performed automatically the first time you send or receive
    data.

    Args:
      host (bytes or str): The host to connect to. We require the server
          to have a TLS certificate valid for this hostname.
      port (int): The port to connect to.
      https_compatible (bool): Set this to True if you're connecting to a web
          server. See :class:`~trio.SSLStream` for details. Default:
          False.
      ssl_context (:class:`~ssl.SSLContext` or None): The SSL context to
          use. If None (the default), :func:`ssl.create_default_context`
          will be called to create a context.
      happy_eyeballs_delay (float): See :func:`open_tcp_stream`.

    Returns:
      trio.SSLStream: the encrypted connection to the server.

    """
    tcp_stream = await trio.open_tcp_stream(
        host,
        port,
        happy_eyeballs_delay=happy_eyeballs_delay,
    )
    if ssl_context is None:
        ssl_context = ssl.create_default_context()

        if hasattr(ssl, "OP_IGNORE_UNEXPECTED_EOF"):
            ssl_context.options &= ~ssl.OP_IGNORE_UNEXPECTED_EOF

    return trio.SSLStream(
        tcp_stream,
        ssl_context,
        server_hostname=host,
        https_compatible=https_compatible,
    )


async def open_ssl_over_tcp_listeners(
    port: int,
    ssl_context: ssl.SSLContext,
    *,
    host: str | bytes | None = None,
    https_compatible: bool = False,
    backlog: int | None = None,
) -> list[trio.SSLListener[SocketStream]]:
    """Start listening for SSL/TLS-encrypted TCP connections to the given port.

    Args:
      port (int): The port to listen on. See :func:`open_tcp_listeners`.
      ssl_context (~ssl.SSLContext): The SSL context to use for all incoming
          connections.
      host (str, bytes, or None): The address to bind to; use ``None`` to bind
          to the wildcard address. See :func:`open_tcp_listeners`.
      https_compatible (bool): See :class:`~trio.SSLStream` for details.
      backlog (int or None): See :func:`open_tcp_listeners` for details.

    """
    tcp_listeners = await trio.open_tcp_listeners(port, host=host, backlog=backlog)
    ssl_listeners = [
        trio.SSLListener(tcp_listener, ssl_context, https_compatible=https_compatible)
        for tcp_listener in tcp_listeners
    ]
    return ssl_listeners


async def serve_ssl_over_tcp(
    handler: Callable[[trio.SSLStream[SocketStream]], Awaitable[object]],
    port: int,
    ssl_context: ssl.SSLContext,
    *,
    host: str | bytes | None = None,
    https_compatible: bool = False,
    backlog: int | None = None,
    handler_nursery: trio.Nursery | None = None,
    task_status: trio.TaskStatus[
        list[trio.SSLListener[SocketStream]]
    ] = trio.TASK_STATUS_IGNORED,
) -> NoReturn:
    """Listen for incoming TCP connections, and for each one start a task
    running ``handler(stream)``.

    This is a thin convenience wrapper around
    :func:`open_ssl_over_tcp_listeners` and :func:`serve_listeners` – see them
    for full details.

    .. warning::

       If ``handler`` raises an exception, then this function doesn't do
       anything special to catch it – so by default the exception will
       propagate out and crash your server. If you don't want this, then catch
       exceptions inside your ``handler``, or use a ``handler_nursery`` object
       that responds to exceptions in some other way.

    When used with ``nursery.start`` you get back the newly opened listeners.
    See the documentation for :func:`serve_tcp` for an example where this is
    useful.

    Args:
      handler: The handler to start for each incoming connection. Passed to
          :func:`serve_listeners`.

      port (int): The port to listen on. Use 0 to let the kernel pick
          an open port. Ultimately passed to :func:`open_tcp_listeners`.

      ssl_context (~ssl.SSLContext): The SSL context to use for all incoming
          connections. Passed to :func:`open_ssl_over_tcp_listeners`.

      host (str, bytes, or None): The address to bind to; use ``None`` to bind
          to the wildcard address. Ultimately passed to
          :func:`open_tcp_listeners`.

      https_compatible (bool): Set this to True if you want to use
          "HTTPS-style" TLS. See :class:`~trio.SSLStream` for details.

      backlog (int or None): See :class:`~trio.SSLStream` for details.

      handler_nursery: The nursery to start handlers in, or None to use an
          internal nursery. Passed to :func:`serve_listeners`.

      task_status: This function can be used with ``nursery.start``.

    Returns:
      This function only returns when cancelled.

    """
    listeners = await trio.open_ssl_over_tcp_listeners(
        port,
        ssl_context,
        host=host,
        https_compatible=https_compatible,
        backlog=backlog,
    )
    await trio.serve_listeners(
        handler,
        listeners,
        handler_nursery=handler_nursery,
        task_status=task_status,
    )

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\sftp.py ===
import datetime
import logging
import os
import types
import uuid
from stat import S_ISDIR, S_ISLNK

import paramiko

from .. import AbstractFileSystem
from ..utils import infer_storage_options

logger = logging.getLogger("fsspec.sftp")


class SFTPFileSystem(AbstractFileSystem):
    """Files over SFTP/SSH

    Peer-to-peer filesystem over SSH using paramiko.

    Note: if using this with the ``open`` or ``open_files``, with full URLs,
    there is no way to tell if a path is relative, so all paths are assumed
    to be absolute.
    """

    protocol = "sftp", "ssh"

    def __init__(self, host, **ssh_kwargs):
        """

        Parameters
        ----------
        host: str
            Hostname or IP as a string
        temppath: str
            Location on the server to put files, when within a transaction
        ssh_kwargs: dict
            Parameters passed on to connection. See details in
            https://docs.paramiko.org/en/3.3/api/client.html#paramiko.client.SSHClient.connect
            May include port, username, password...
        """
        if self._cached:
            return
        super().__init__(**ssh_kwargs)
        self.temppath = ssh_kwargs.pop("temppath", "/tmp")  # remote temp directory
        self.host = host
        self.ssh_kwargs = ssh_kwargs
        self._connect()

    def _connect(self):
        logger.debug("Connecting to SFTP server %s", self.host)
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(self.host, **self.ssh_kwargs)
        self.ftp = self.client.open_sftp()

    @classmethod
    def _strip_protocol(cls, path):
        return infer_storage_options(path)["path"]

    @staticmethod
    def _get_kwargs_from_urls(urlpath):
        out = infer_storage_options(urlpath)
        out.pop("path", None)
        out.pop("protocol", None)
        return out

    def mkdir(self, path, create_parents=True, mode=511):
        logger.debug("Creating folder %s", path)
        if self.exists(path):
            raise FileExistsError(f"File exists: {path}")

        if create_parents:
            self.makedirs(path)
        else:
            self.ftp.mkdir(path, mode)

    def makedirs(self, path, exist_ok=False, mode=511):
        if self.exists(path) and not exist_ok:
            raise FileExistsError(f"File exists: {path}")

        parts = path.split("/")
        new_path = "/" if path[:1] == "/" else ""

        for part in parts:
            if part:
                new_path = f"{new_path}/{part}" if new_path else part
                if not self.exists(new_path):
                    self.ftp.mkdir(new_path, mode)

    def rmdir(self, path):
        logger.debug("Removing folder %s", path)
        self.ftp.rmdir(path)

    def info(self, path):
        stat = self._decode_stat(self.ftp.stat(path))
        stat["name"] = path
        return stat

    @staticmethod
    def _decode_stat(stat, parent_path=None):
        if S_ISDIR(stat.st_mode):
            t = "directory"
        elif S_ISLNK(stat.st_mode):
            t = "link"
        else:
            t = "file"
        out = {
            "name": "",
            "size": stat.st_size,
            "type": t,
            "uid": stat.st_uid,
            "gid": stat.st_gid,
            "time": datetime.datetime.fromtimestamp(
                stat.st_atime, tz=datetime.timezone.utc
            ),
            "mtime": datetime.datetime.fromtimestamp(
                stat.st_mtime, tz=datetime.timezone.utc
            ),
        }
        if parent_path:
            out["name"] = "/".join([parent_path.rstrip("/"), stat.filename])
        return out

    def ls(self, path, detail=False):
        logger.debug("Listing folder %s", path)
        stats = [self._decode_stat(stat, path) for stat in self.ftp.listdir_iter(path)]
        if detail:
            return stats
        else:
            paths = [stat["name"] for stat in stats]
            return sorted(paths)

    def put(self, lpath, rpath, callback=None, **kwargs):
        logger.debug("Put file %s into %s", lpath, rpath)
        self.ftp.put(lpath, rpath)

    def get_file(self, rpath, lpath, **kwargs):
        if self.isdir(rpath):
            os.makedirs(lpath, exist_ok=True)
        else:
            self.ftp.get(self._strip_protocol(rpath), lpath)

    def _open(self, path, mode="rb", block_size=None, **kwargs):
        """
        block_size: int or None
            If 0, no buffering, if 1, line buffering, if >1, buffer that many
            bytes, if None use default from paramiko.
        """
        logger.debug("Opening file %s", path)
        if kwargs.get("autocommit", True) is False:
            # writes to temporary file, move on commit
            path2 = "/".join([self.temppath, str(uuid.uuid4())])
            f = self.ftp.open(path2, mode, bufsize=block_size if block_size else -1)
            f.temppath = path2
            f.targetpath = path
            f.fs = self
            f.commit = types.MethodType(commit_a_file, f)
            f.discard = types.MethodType(discard_a_file, f)
        else:
            f = self.ftp.open(path, mode, bufsize=block_size if block_size else -1)
        return f

    def _rm(self, path):
        if self.isdir(path):
            self.ftp.rmdir(path)
        else:
            self.ftp.remove(path)

    def mv(self, old, new):
        logger.debug("Renaming %s into %s", old, new)
        self.ftp.posix_rename(old, new)


def commit_a_file(self):
    self.fs.mv(self.temppath, self.targetpath)


def discard_a_file(self):
    self.fs._rm(self.temppath)

# === NexusCore/openenv\Lib\site-packages\google\auth\app_engine.py ===
# Copyright 2016 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google App Engine standard environment support.

This module provides authentication and signing for applications running on App
Engine in the standard environment using the `App Identity API`_.


.. _App Identity API:
    https://cloud.google.com/appengine/docs/python/appidentity/
"""

import datetime

from google.auth import _helpers
from google.auth import credentials
from google.auth import crypt
from google.auth import exceptions

# pytype: disable=import-error
try:
    from google.appengine.api import app_identity  # type: ignore
except ImportError:
    app_identity = None  # type: ignore
# pytype: enable=import-error


class Signer(crypt.Signer):
    """Signs messages using the App Engine App Identity service.

    This can be used in place of :class:`google.auth.crypt.Signer` when
    running in the App Engine standard environment.
    """

    @property
    def key_id(self):
        """Optional[str]: The key ID used to identify this private key.

        .. warning::
           This is always ``None``. The key ID used by App Engine can not
           be reliably determined ahead of time.
        """
        return None

    @_helpers.copy_docstring(crypt.Signer)
    def sign(self, message):
        message = _helpers.to_bytes(message)
        _, signature = app_identity.sign_blob(message)
        return signature


def get_project_id():
    """Gets the project ID for the current App Engine application.

    Returns:
        str: The project ID

    Raises:
        google.auth.exceptions.OSError: If the App Engine APIs are unavailable.
    """
    # pylint: disable=missing-raises-doc
    # Pylint rightfully thinks google.auth.exceptions.OSError is OSError, but doesn't
    # realize it's a valid alias.
    if app_identity is None:
        raise exceptions.OSError("The App Engine APIs are not available.")
    return app_identity.get_application_id()


class Credentials(
    credentials.Scoped, credentials.Signing, credentials.CredentialsWithQuotaProject
):
    """App Engine standard environment credentials.

    These credentials use the App Engine App Identity API to obtain access
    tokens.
    """

    def __init__(
        self,
        scopes=None,
        default_scopes=None,
        service_account_id=None,
        quota_project_id=None,
    ):
        """
        Args:
            scopes (Sequence[str]): Scopes to request from the App Identity
                API.
            default_scopes (Sequence[str]): Default scopes passed by a
                Google client library. Use 'scopes' for user-defined scopes.
            service_account_id (str): The service account ID passed into
                :func:`google.appengine.api.app_identity.get_access_token`.
                If not specified, the default application service account
                ID will be used.
            quota_project_id (Optional[str]): The project ID used for quota
                and billing.

        Raises:
            google.auth.exceptions.OSError: If the App Engine APIs are unavailable.
        """
        # pylint: disable=missing-raises-doc
        # Pylint rightfully thinks google.auth.exceptions.OSError is OSError, but doesn't
        # realize it's a valid alias.
        if app_identity is None:
            raise exceptions.OSError("The App Engine APIs are not available.")

        super(Credentials, self).__init__()
        self._scopes = scopes
        self._default_scopes = default_scopes
        self._service_account_id = service_account_id
        self._signer = Signer()
        self._quota_project_id = quota_project_id

    @_helpers.copy_docstring(credentials.Credentials)
    def refresh(self, request):
        scopes = self._scopes if self._scopes is not None else self._default_scopes
        # pylint: disable=unused-argument
        token, ttl = app_identity.get_access_token(scopes, self._service_account_id)
        expiry = datetime.datetime.utcfromtimestamp(ttl)

        self.token, self.expiry = token, expiry

    @property
    def service_account_email(self):
        """The service account email."""
        if self._service_account_id is None:
            self._service_account_id = app_identity.get_service_account_name()
        return self._service_account_id

    @property
    def requires_scopes(self):
        """Checks if the credentials requires scopes.

        Returns:
            bool: True if there are no scopes set otherwise False.
        """
        return not self._scopes and not self._default_scopes

    @_helpers.copy_docstring(credentials.Scoped)
    def with_scopes(self, scopes, default_scopes=None):
        return self.__class__(
            scopes=scopes,
            default_scopes=default_scopes,
            service_account_id=self._service_account_id,
            quota_project_id=self.quota_project_id,
        )

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        return self.__class__(
            scopes=self._scopes,
            service_account_id=self._service_account_id,
            quota_project_id=quota_project_id,
        )

    @_helpers.copy_docstring(credentials.Signing)
    def sign_bytes(self, message):
        return self._signer.sign(message)

    @property  # type: ignore
    @_helpers.copy_docstring(credentials.Signing)
    def signer_email(self):
        return self.service_account_email

    @property  # type: ignore
    @_helpers.copy_docstring(credentials.Signing)
    def signer(self):
        return self._signer

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\discuss_service\transports\base.py ===
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
import abc
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

import google.api_core
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version
from google.ai.generativelanguage_v1beta3.types import discuss_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class DiscussServiceTransport(abc.ABC):
    """Abstract transport class for DiscussService."""

    AUTH_SCOPES = ()

    DEFAULT_HOST: str = "generativelanguage.googleapis.com"

    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A list of scopes.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
        """

        scopes_kwargs = {"scopes": scopes, "default_scopes": self.AUTH_SCOPES}

        # Save the scopes.
        self._scopes = scopes

        # If no credentials are provided, then determine the appropriate
        # defaults.
        if credentials and credentials_file:
            raise core_exceptions.DuplicateCredentialArgs(
                "'credentials_file' and 'credentials' are mutually exclusive"
            )

        if credentials_file is not None:
            credentials, _ = google.auth.load_credentials_from_file(
                credentials_file, **scopes_kwargs, quota_project_id=quota_project_id
            )
        elif credentials is None:
            credentials, _ = google.auth.default(
                **scopes_kwargs, quota_project_id=quota_project_id
            )
            # Don't apply audience if the credentials file passed from user.
            if hasattr(credentials, "with_gdch_audience"):
                credentials = credentials.with_gdch_audience(
                    api_audience if api_audience else host
                )

        # If the credentials are service account credentials, then always try to use self signed JWT.
        if (
            always_use_jwt_access
            and isinstance(credentials, service_account.Credentials)
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(True)

        # Save the credentials.
        self._credentials = credentials

        # Save the hostname. Default to port 443 (HTTPS) if none is specified.
        if ":" not in host:
            host += ":443"
        self._host = host

    @property
    def host(self):
        return self._host

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.generate_message: gapic_v1.method.wrap_method(
                self.generate_message,
                default_timeout=None,
                client_info=client_info,
            ),
            self.count_message_tokens: gapic_v1.method.wrap_method(
                self.count_message_tokens,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        Union[
            discuss_service.GenerateMessageResponse,
            Awaitable[discuss_service.GenerateMessageResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        Union[
            discuss_service.CountMessageTokensResponse,
            Awaitable[discuss_service.CountMessageTokensResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("DiscussServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_memory_async.py ===
import asyncio
import gc
import shutil

import pytest

from joblib.memory import (
    AsyncMemorizedFunc,
    AsyncNotMemorizedFunc,
    MemorizedResult,
    Memory,
    NotMemorizedResult,
)
from joblib.test.common import np, with_numpy
from joblib.testing import raises

from .test_memory import corrupt_single_cache_item, monkeypatch_cached_func_warn


async def check_identity_lazy_async(func, accumulator, location):
    """Similar to check_identity_lazy_async for coroutine functions"""
    memory = Memory(location=location, verbose=0)
    func = memory.cache(func)
    for i in range(3):
        for _ in range(2):
            value = await func(i)
            assert value == i
            assert len(accumulator) == i + 1


@pytest.mark.asyncio
async def test_memory_integration_async(tmpdir):
    accumulator = list()

    async def f(n):
        await asyncio.sleep(0.1)
        accumulator.append(1)
        return n

    await check_identity_lazy_async(f, accumulator, tmpdir.strpath)

    # Now test clearing
    for compress in (False, True):
        for mmap_mode in ("r", None):
            memory = Memory(
                location=tmpdir.strpath,
                verbose=10,
                mmap_mode=mmap_mode,
                compress=compress,
            )
            # First clear the cache directory, to check that our code can
            # handle that
            # NOTE: this line would raise an exception, as the database
            # file is still open; we ignore the error since we want to
            # test what happens if the directory disappears
            shutil.rmtree(tmpdir.strpath, ignore_errors=True)
            g = memory.cache(f)
            await g(1)
            g.clear(warn=False)
            current_accumulator = len(accumulator)
            out = await g(1)

        assert len(accumulator) == current_accumulator + 1
        # Also, check that Memory.eval works similarly
        evaled = await memory.eval(f, 1)
        assert evaled == out
        assert len(accumulator) == current_accumulator + 1

    # Now do a smoke test with a function defined in __main__, as the name
    # mangling rules are more complex
    f.__module__ = "__main__"
    memory = Memory(location=tmpdir.strpath, verbose=0)
    await memory.cache(f)(1)


@pytest.mark.asyncio
async def test_no_memory_async():
    accumulator = list()

    async def ff(x):
        await asyncio.sleep(0.1)
        accumulator.append(1)
        return x

    memory = Memory(location=None, verbose=0)
    gg = memory.cache(ff)
    for _ in range(4):
        current_accumulator = len(accumulator)
        await gg(1)
        assert len(accumulator) == current_accumulator + 1


@with_numpy
@pytest.mark.asyncio
async def test_memory_numpy_check_mmap_mode_async(tmpdir, monkeypatch):
    """Check that mmap_mode is respected even at the first call"""

    memory = Memory(location=tmpdir.strpath, mmap_mode="r", verbose=0)

    @memory.cache()
    async def twice(a):
        return a * 2

    a = np.ones(3)
    b = await twice(a)
    c = await twice(a)

    assert isinstance(c, np.memmap)
    assert c.mode == "r"

    assert isinstance(b, np.memmap)
    assert b.mode == "r"

    # Corrupts the file,  Deleting b and c mmaps
    # is necessary to be able edit the file
    del b
    del c
    gc.collect()
    corrupt_single_cache_item(memory)

    # Make sure that corrupting the file causes recomputation and that
    # a warning is issued.
    recorded_warnings = monkeypatch_cached_func_warn(twice, monkeypatch)
    d = await twice(a)
    assert len(recorded_warnings) == 1
    exception_msg = "Exception while loading results"
    assert exception_msg in recorded_warnings[0]
    # Asserts that the recomputation returns a mmap
    assert isinstance(d, np.memmap)
    assert d.mode == "r"


@pytest.mark.asyncio
async def test_call_and_shelve_async(tmpdir):
    async def f(x, y=1):
        await asyncio.sleep(0.1)
        return x**2 + y

    # Test MemorizedFunc outputting a reference to cache.
    for func, Result in zip(
        (
            AsyncMemorizedFunc(f, tmpdir.strpath),
            AsyncNotMemorizedFunc(f),
            Memory(location=tmpdir.strpath, verbose=0).cache(f),
            Memory(location=None).cache(f),
        ),
        (
            MemorizedResult,
            NotMemorizedResult,
            MemorizedResult,
            NotMemorizedResult,
        ),
    ):
        for _ in range(2):
            result = await func.call_and_shelve(2)
            assert isinstance(result, Result)
            assert result.get() == 5

        result.clear()
        with raises(KeyError):
            result.get()
        result.clear()  # Do nothing if there is no cache.


@pytest.mark.asyncio
async def test_memorized_func_call_async(memory):
    async def ff(x, counter):
        await asyncio.sleep(0.1)
        counter[x] = counter.get(x, 0) + 1
        return counter[x]

    gg = memory.cache(ff, ignore=["counter"])

    counter = {}
    assert await gg(2, counter) == 1
    assert await gg(2, counter) == 1

    x, meta = await gg.call(2, counter)
    assert x == 2, "f has not been called properly"
    assert isinstance(meta, dict), "Metadata are not returned by MemorizedFunc.call."

# === NexusCore/openenv\Lib\site-packages\matplotlib\testing\jpl_units\UnitDbl.py ===
"""UnitDbl module."""

import functools
import operator

from matplotlib import _api


class UnitDbl:
    """Class UnitDbl in development."""

    # Unit conversion table.  Small subset of the full one but enough
    # to test the required functions.  First field is a scale factor to
    # convert the input units to the units of the second field.  Only
    # units in this table are allowed.
    allowed = {
        "m": (0.001, "km"),
        "km": (1, "km"),
        "mile": (1.609344, "km"),

        "rad": (1, "rad"),
        "deg": (1.745329251994330e-02, "rad"),

        "sec": (1, "sec"),
        "min": (60.0, "sec"),
        "hour": (3600, "sec"),
        }

    _types = {
        "km": "distance",
        "rad": "angle",
        "sec": "time",
        }

    def __init__(self, value, units):
        """
        Create a new UnitDbl object.

        Units are internally converted to km, rad, and sec.  The only
        valid inputs for units are [m, km, mile, rad, deg, sec, min, hour].

        The field UnitDbl.value will contain the converted value.  Use
        the convert() method to get a specific type of units back.

        = ERROR CONDITIONS
        - If the input units are not in the allowed list, an error is thrown.

        = INPUT VARIABLES
        - value     The numeric value of the UnitDbl.
        - units     The string name of the units the value is in.
        """
        data = _api.check_getitem(self.allowed, units=units)
        self._value = float(value * data[0])
        self._units = data[1]

    def convert(self, units):
        """
        Convert the UnitDbl to a specific set of units.

        = ERROR CONDITIONS
        - If the input units are not in the allowed list, an error is thrown.

        = INPUT VARIABLES
        - units     The string name of the units to convert to.

        = RETURN VALUE
        - Returns the value of the UnitDbl in the requested units as a floating
          point number.
        """
        if self._units == units:
            return self._value
        data = _api.check_getitem(self.allowed, units=units)
        if self._units != data[1]:
            raise ValueError(f"Error trying to convert to different units.\n"
                             f"    Invalid conversion requested.\n"
                             f"    UnitDbl: {self}\n"
                             f"    Units:   {units}\n")
        return self._value / data[0]

    def __abs__(self):
        """Return the absolute value of this UnitDbl."""
        return UnitDbl(abs(self._value), self._units)

    def __neg__(self):
        """Return the negative value of this UnitDbl."""
        return UnitDbl(-self._value, self._units)

    def __bool__(self):
        """Return the truth value of a UnitDbl."""
        return bool(self._value)

    def _cmp(self, op, rhs):
        """Check that *self* and *rhs* share units; compare them using *op*."""
        self.checkSameUnits(rhs, "compare")
        return op(self._value, rhs._value)

    __eq__ = functools.partialmethod(_cmp, operator.eq)
    __ne__ = functools.partialmethod(_cmp, operator.ne)
    __lt__ = functools.partialmethod(_cmp, operator.lt)
    __le__ = functools.partialmethod(_cmp, operator.le)
    __gt__ = functools.partialmethod(_cmp, operator.gt)
    __ge__ = functools.partialmethod(_cmp, operator.ge)

    def _binop_unit_unit(self, op, rhs):
        """Check that *self* and *rhs* share units; combine them using *op*."""
        self.checkSameUnits(rhs, op.__name__)
        return UnitDbl(op(self._value, rhs._value), self._units)

    __add__ = functools.partialmethod(_binop_unit_unit, operator.add)
    __sub__ = functools.partialmethod(_binop_unit_unit, operator.sub)

    def _binop_unit_scalar(self, op, scalar):
        """Combine *self* and *scalar* using *op*."""
        return UnitDbl(op(self._value, scalar), self._units)

    __mul__ = functools.partialmethod(_binop_unit_scalar, operator.mul)
    __rmul__ = functools.partialmethod(_binop_unit_scalar, operator.mul)

    def __str__(self):
        """Print the UnitDbl."""
        return f"{self._value:g} *{self._units}"

    def __repr__(self):
        """Print the UnitDbl."""
        return f"UnitDbl({self._value:g}, '{self._units}')"

    def type(self):
        """Return the type of UnitDbl data."""
        return self._types[self._units]

    @staticmethod
    def range(start, stop, step=None):
        """
        Generate a range of UnitDbl objects.

        Similar to the Python range() method.  Returns the range [
        start, stop) at the requested step.  Each element will be a
        UnitDbl object.

        = INPUT VARIABLES
        - start     The starting value of the range.
        - stop      The stop value of the range.
        - step      Optional step to use.  If set to None, then a UnitDbl of
                      value 1 w/ the units of the start is used.

        = RETURN VALUE
        - Returns a list containing the requested UnitDbl values.
        """
        if step is None:
            step = UnitDbl(1, start._units)

        elems = []

        i = 0
        while True:
            d = start + i * step
            if d >= stop:
                break

            elems.append(d)
            i += 1

        return elems

    def checkSameUnits(self, rhs, func):
        """
        Check to see if units are the same.

        = ERROR CONDITIONS
        - If the units of the rhs UnitDbl are not the same as our units,
          an error is thrown.

        = INPUT VARIABLES
        - rhs     The UnitDbl to check for the same units
        - func    The name of the function doing the check.
        """
        if self._units != rhs._units:
            raise ValueError(f"Cannot {func} units of different types.\n"
                             f"LHS: {self._units}\n"
                             f"RHS: {rhs._units}")

# === NexusCore/openenv\Lib\site-packages\nltk\classify\positivenaivebayes.py ===
# Natural Language Toolkit: Positive Naive Bayes Classifier
#
# Copyright (C) 2012 NLTK Project
# Author: Alessandro Presta <alessandro.presta@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A variant of the Naive Bayes Classifier that performs binary classification with
partially-labeled training sets. In other words, assume we want to build a classifier
that assigns each example to one of two complementary classes (e.g., male names and
female names).
If we have a training set with labeled examples for both classes, we can use a
standard Naive Bayes Classifier. However, consider the case when we only have labeled
examples for one of the classes, and other, unlabeled, examples.
Then, assuming a prior distribution on the two labels, we can use the unlabeled set
to estimate the frequencies of the various features.

Let the two possible labels be 1 and 0, and let's say we only have examples labeled 1
and unlabeled examples. We are also given an estimate of P(1).

We compute P(feature|1) exactly as in the standard case.

To compute P(feature|0), we first estimate P(feature) from the unlabeled set (we are
assuming that the unlabeled examples are drawn according to the given prior distribution)
and then express the conditional probability as:

|                  P(feature) - P(feature|1) * P(1)
|  P(feature|0) = ----------------------------------
|                               P(0)

Example:

    >>> from nltk.classify import PositiveNaiveBayesClassifier

Some sentences about sports:

    >>> sports_sentences = [ 'The team dominated the game',
    ...                      'They lost the ball',
    ...                      'The game was intense',
    ...                      'The goalkeeper catched the ball',
    ...                      'The other team controlled the ball' ]

Mixed topics, including sports:

    >>> various_sentences = [ 'The President did not comment',
    ...                       'I lost the keys',
    ...                       'The team won the game',
    ...                       'Sara has two kids',
    ...                       'The ball went off the court',
    ...                       'They had the ball for the whole game',
    ...                       'The show is over' ]

The features of a sentence are simply the words it contains:

    >>> def features(sentence):
    ...     words = sentence.lower().split()
    ...     return dict(('contains(%s)' % w, True) for w in words)

We use the sports sentences as positive examples, the mixed ones ad unlabeled examples:

    >>> positive_featuresets = map(features, sports_sentences)
    >>> unlabeled_featuresets = map(features, various_sentences)
    >>> classifier = PositiveNaiveBayesClassifier.train(positive_featuresets,
    ...                                                 unlabeled_featuresets)

Is the following sentence about sports?

    >>> classifier.classify(features('The cat is on the table'))
    False

What about this one?

    >>> classifier.classify(features('My team lost the game'))
    True
"""

from collections import defaultdict

from nltk.classify.naivebayes import NaiveBayesClassifier
from nltk.probability import DictionaryProbDist, ELEProbDist, FreqDist

##//////////////////////////////////////////////////////
##  Positive Naive Bayes Classifier
##//////////////////////////////////////////////////////


class PositiveNaiveBayesClassifier(NaiveBayesClassifier):
    @staticmethod
    def train(
        positive_featuresets,
        unlabeled_featuresets,
        positive_prob_prior=0.5,
        estimator=ELEProbDist,
    ):
        """
        :param positive_featuresets: An iterable of featuresets that are known as positive
            examples (i.e., their label is ``True``).

        :param unlabeled_featuresets: An iterable of featuresets whose label is unknown.

        :param positive_prob_prior: A prior estimate of the probability of the label
            ``True`` (default 0.5).
        """
        positive_feature_freqdist = defaultdict(FreqDist)
        unlabeled_feature_freqdist = defaultdict(FreqDist)
        feature_values = defaultdict(set)
        fnames = set()

        # Count up how many times each feature value occurred in positive examples.
        num_positive_examples = 0
        for featureset in positive_featuresets:
            for fname, fval in featureset.items():
                positive_feature_freqdist[fname][fval] += 1
                feature_values[fname].add(fval)
                fnames.add(fname)
            num_positive_examples += 1

        # Count up how many times each feature value occurred in unlabeled examples.
        num_unlabeled_examples = 0
        for featureset in unlabeled_featuresets:
            for fname, fval in featureset.items():
                unlabeled_feature_freqdist[fname][fval] += 1
                feature_values[fname].add(fval)
                fnames.add(fname)
            num_unlabeled_examples += 1

        # If a feature didn't have a value given for an instance, then we assume that
        # it gets the implicit value 'None'.
        for fname in fnames:
            count = positive_feature_freqdist[fname].N()
            positive_feature_freqdist[fname][None] += num_positive_examples - count
            feature_values[fname].add(None)

        for fname in fnames:
            count = unlabeled_feature_freqdist[fname].N()
            unlabeled_feature_freqdist[fname][None] += num_unlabeled_examples - count
            feature_values[fname].add(None)

        negative_prob_prior = 1.0 - positive_prob_prior

        # Create the P(label) distribution.
        label_probdist = DictionaryProbDist(
            {True: positive_prob_prior, False: negative_prob_prior}
        )

        # Create the P(fval|label, fname) distribution.
        feature_probdist = {}
        for fname, freqdist in positive_feature_freqdist.items():
            probdist = estimator(freqdist, bins=len(feature_values[fname]))
            feature_probdist[True, fname] = probdist

        for fname, freqdist in unlabeled_feature_freqdist.items():
            global_probdist = estimator(freqdist, bins=len(feature_values[fname]))
            negative_feature_probs = {}
            for fval in feature_values[fname]:
                prob = (
                    global_probdist.prob(fval)
                    - positive_prob_prior * feature_probdist[True, fname].prob(fval)
                ) / negative_prob_prior
                # TODO: We need to add some kind of smoothing here, instead of
                # setting negative probabilities to zero and normalizing.
                negative_feature_probs[fval] = max(prob, 0.0)
            feature_probdist[False, fname] = DictionaryProbDist(
                negative_feature_probs, normalize=True
            )

        return PositiveNaiveBayesClassifier(label_probdist, feature_probdist)


##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////


def demo():
    from nltk.classify.util import partial_names_demo

    classifier = partial_names_demo(PositiveNaiveBayesClassifier.train)
    classifier.show_most_informative_features()

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\toktok.py ===
# Natural Language Toolkit: Python port of the tok-tok.pl tokenizer.
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Jon Dehdari
# Contributors: Liling Tan, Selcuk Ayguney, ikegami, Martijn Pieters,
# Alex Rudnick
#
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

"""
The tok-tok tokenizer is a simple, general tokenizer, where the input has one
sentence per line; thus only final period is tokenized.

Tok-tok has been tested on, and gives reasonably good results for English,
Persian, Russian, Czech, French, German, Vietnamese, Tajik, and a few others.
The input should be in UTF-8 encoding.

Reference:
Jon Dehdari. 2014. A Neurophysiologically-Inspired Statistical Language
Model (Doctoral dissertation). Columbus, OH, USA: The Ohio State University.
"""

import re

from nltk.tokenize.api import TokenizerI


class ToktokTokenizer(TokenizerI):
    """
    This is a Python port of the tok-tok.pl from
    https://github.com/jonsafari/tok-tok/blob/master/tok-tok.pl

    >>> toktok = ToktokTokenizer()
    >>> text = u'Is 9.5 or 525,600 my favorite number?'
    >>> print(toktok.tokenize(text, return_str=True))
    Is 9.5 or 525,600 my favorite number ?
    >>> text = u'The https://github.com/jonsafari/tok-tok/blob/master/tok-tok.pl is a website with/and/or slashes and sort of weird : things'
    >>> print(toktok.tokenize(text, return_str=True))
    The https://github.com/jonsafari/tok-tok/blob/master/tok-tok.pl is a website with/and/or slashes and sort of weird : things
    >>> text = u'\xa1This, is a sentence with weird\xbb symbols\u2026 appearing everywhere\xbf'
    >>> expected = u'\xa1 This , is a sentence with weird \xbb symbols \u2026 appearing everywhere \xbf'
    >>> assert toktok.tokenize(text, return_str=True) == expected
    >>> toktok.tokenize(text) == [u'\xa1', u'This', u',', u'is', u'a', u'sentence', u'with', u'weird', u'\xbb', u'symbols', u'\u2026', u'appearing', u'everywhere', u'\xbf']
    True
    """

    # Replace non-breaking spaces with normal spaces.
    NON_BREAKING = re.compile("\u00A0"), " "

    # Pad some funky punctuation.
    FUNKY_PUNCT_1 = re.compile(r'([،;؛¿!"\])}»›”؟¡%٪°±©®।॥…])'), r" \1 "
    # Pad more funky punctuation.
    FUNKY_PUNCT_2 = re.compile(r"([({\[“‘„‚«‹「『])"), r" \1 "
    # Pad En dash and em dash
    EN_EM_DASHES = re.compile("([–—])"), r" \1 "

    # Replace problematic character with numeric character reference.
    AMPERCENT = re.compile("& "), "&amp; "
    TAB = re.compile("\t"), " &#9; "
    PIPE = re.compile(r"\|"), " &#124; "

    # Pad numbers with commas to keep them from further tokenization.
    COMMA_IN_NUM = re.compile(r"(?<!,)([,،])(?![,\d])"), r" \1 "

    # Just pad problematic (often neurotic) hyphen/single quote, etc.
    PROB_SINGLE_QUOTES = re.compile(r"(['’`])"), r" \1 "
    # Group ` ` stupid quotes ' ' into a single token.
    STUPID_QUOTES_1 = re.compile(r" ` ` "), r" `` "
    STUPID_QUOTES_2 = re.compile(r" ' ' "), r" '' "

    # Don't tokenize period unless it ends the line and that it isn't
    # preceded by another period, e.g.
    # "something ..." -> "something ..."
    # "something." -> "something ."
    FINAL_PERIOD_1 = re.compile(r"(?<!\.)\.$"), r" ."
    # Don't tokenize period unless it ends the line eg.
    # " ... stuff." ->  "... stuff ."
    FINAL_PERIOD_2 = re.compile(r"""(?<!\.)\.\s*(["'’»›”]) *$"""), r" . \1"

    # Treat continuous commas as fake German,Czech, etc.: „
    MULTI_COMMAS = re.compile(r"(,{2,})"), r" \1 "
    # Treat continuous dashes as fake en-dash, etc.
    MULTI_DASHES = re.compile(r"(-{2,})"), r" \1 "
    # Treat multiple periods as a thing (eg. ellipsis)
    MULTI_DOTS = re.compile(r"(\.{2,})"), r" \1 "

    # This is the \p{Open_Punctuation} from Perl's perluniprops
    # see https://perldoc.perl.org/perluniprops.html
    OPEN_PUNCT = str(
        "([{\u0f3a\u0f3c\u169b\u201a\u201e\u2045\u207d"
        "\u208d\u2329\u2768\u276a\u276c\u276e\u2770\u2772"
        "\u2774\u27c5\u27e6\u27e8\u27ea\u27ec\u27ee\u2983"
        "\u2985\u2987\u2989\u298b\u298d\u298f\u2991\u2993"
        "\u2995\u2997\u29d8\u29da\u29fc\u2e22\u2e24\u2e26"
        "\u2e28\u3008\u300a\u300c\u300e\u3010\u3014\u3016"
        "\u3018\u301a\u301d\ufd3e\ufe17\ufe35\ufe37\ufe39"
        "\ufe3b\ufe3d\ufe3f\ufe41\ufe43\ufe47\ufe59\ufe5b"
        "\ufe5d\uff08\uff3b\uff5b\uff5f\uff62"
    )
    # This is the \p{Close_Punctuation} from Perl's perluniprops
    CLOSE_PUNCT = str(
        ")]}\u0f3b\u0f3d\u169c\u2046\u207e\u208e\u232a"
        "\u2769\u276b\u276d\u276f\u2771\u2773\u2775\u27c6"
        "\u27e7\u27e9\u27eb\u27ed\u27ef\u2984\u2986\u2988"
        "\u298a\u298c\u298e\u2990\u2992\u2994\u2996\u2998"
        "\u29d9\u29db\u29fd\u2e23\u2e25\u2e27\u2e29\u3009"
        "\u300b\u300d\u300f\u3011\u3015\u3017\u3019\u301b"
        "\u301e\u301f\ufd3f\ufe18\ufe36\ufe38\ufe3a\ufe3c"
        "\ufe3e\ufe40\ufe42\ufe44\ufe48\ufe5a\ufe5c\ufe5e"
        "\uff09\uff3d\uff5d\uff60\uff63"
    )
    # This is the \p{Close_Punctuation} from Perl's perluniprops
    CURRENCY_SYM = str(
        "$\xa2\xa3\xa4\xa5\u058f\u060b\u09f2\u09f3\u09fb"
        "\u0af1\u0bf9\u0e3f\u17db\u20a0\u20a1\u20a2\u20a3"
        "\u20a4\u20a5\u20a6\u20a7\u20a8\u20a9\u20aa\u20ab"
        "\u20ac\u20ad\u20ae\u20af\u20b0\u20b1\u20b2\u20b3"
        "\u20b4\u20b5\u20b6\u20b7\u20b8\u20b9\u20ba\ua838"
        "\ufdfc\ufe69\uff04\uffe0\uffe1\uffe5\uffe6"
    )

    # Pad spaces after opening punctuations.
    OPEN_PUNCT_RE = re.compile(f"([{OPEN_PUNCT}])"), r"\1 "
    # Pad spaces before closing punctuations.
    CLOSE_PUNCT_RE = re.compile(f"([{CLOSE_PUNCT}])"), r"\1 "
    # Pad spaces after currency symbols.
    CURRENCY_SYM_RE = re.compile(f"([{CURRENCY_SYM}])"), r"\1 "

    # Use for tokenizing URL-unfriendly characters: [:/?#]
    URL_FOE_1 = re.compile(r":(?!//)"), r" : "  # in perl s{:(?!//)}{ : }g;
    URL_FOE_2 = re.compile(r"\?(?!\S)"), r" ? "  # in perl s{\?(?!\S)}{ ? }g;
    # in perl: m{://} or m{\S+\.\S+/\S+} or s{/}{ / }g;
    URL_FOE_3 = re.compile(r"(:\/\/)[\S+\.\S+\/\S+][\/]"), " / "
    URL_FOE_4 = re.compile(r" /"), r" / "  # s{ /}{ / }g;

    # Left/Right strip, i.e. remove heading/trailing spaces.
    # These strip regexes should NOT be used,
    # instead use str.lstrip(), str.rstrip() or str.strip()
    # (They are kept for reference purposes to the original toktok.pl code)
    LSTRIP = re.compile(r"^ +"), ""
    RSTRIP = re.compile(r"\s+$"), "\n"
    # Merge multiple spaces.
    ONE_SPACE = re.compile(r" {2,}"), " "

    TOKTOK_REGEXES = [
        NON_BREAKING,
        FUNKY_PUNCT_1,
        FUNKY_PUNCT_2,
        URL_FOE_1,
        URL_FOE_2,
        URL_FOE_3,
        URL_FOE_4,
        AMPERCENT,
        TAB,
        PIPE,
        OPEN_PUNCT_RE,
        CLOSE_PUNCT_RE,
        MULTI_COMMAS,
        COMMA_IN_NUM,
        PROB_SINGLE_QUOTES,
        STUPID_QUOTES_1,
        STUPID_QUOTES_2,
        CURRENCY_SYM_RE,
        EN_EM_DASHES,
        MULTI_DASHES,
        MULTI_DOTS,
        FINAL_PERIOD_1,
        FINAL_PERIOD_2,
        ONE_SPACE,
    ]

    def tokenize(self, text, return_str=False):
        text = str(text)  # Converts input string into unicode.
        for regexp, substitution in self.TOKTOK_REGEXES:
            text = regexp.sub(substitution, text)
        # Finally, strips heading and trailing spaces
        # and converts output string into unicode.
        text = str(text.strip())
        return text if return_str else text.split()

# === NexusCore/openenv\Lib\site-packages\openai\types\eval_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from .shared_params.metadata import Metadata
from .graders.python_grader_param import PythonGraderParam
from .graders.score_model_grader_param import ScoreModelGraderParam
from .graders.string_check_grader_param import StringCheckGraderParam
from .responses.response_input_text_param import ResponseInputTextParam
from .graders.text_similarity_grader_param import TextSimilarityGraderParam

__all__ = [
    "EvalCreateParams",
    "DataSourceConfig",
    "DataSourceConfigCustom",
    "DataSourceConfigLogs",
    "DataSourceConfigStoredCompletions",
    "TestingCriterion",
    "TestingCriterionLabelModel",
    "TestingCriterionLabelModelInput",
    "TestingCriterionLabelModelInputSimpleInputMessage",
    "TestingCriterionLabelModelInputEvalItem",
    "TestingCriterionLabelModelInputEvalItemContent",
    "TestingCriterionLabelModelInputEvalItemContentOutputText",
    "TestingCriterionTextSimilarity",
    "TestingCriterionPython",
    "TestingCriterionScoreModel",
]


class EvalCreateParams(TypedDict, total=False):
    data_source_config: Required[DataSourceConfig]
    """The configuration for the data source used for the evaluation runs.

    Dictates the schema of the data used in the evaluation.
    """

    testing_criteria: Required[Iterable[TestingCriterion]]
    """A list of graders for all eval runs in this group.

    Graders can reference variables in the data source using double curly braces
    notation, like `{{item.variable_name}}`. To reference the model's output, use
    the `sample` namespace (ie, `{{sample.output_text}}`).
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    name: str
    """The name of the evaluation."""


class DataSourceConfigCustom(TypedDict, total=False):
    item_schema: Required[Dict[str, object]]
    """The json schema for each row in the data source."""

    type: Required[Literal["custom"]]
    """The type of data source. Always `custom`."""

    include_sample_schema: bool
    """
    Whether the eval should expect you to populate the sample namespace (ie, by
    generating responses off of your data source)
    """


class DataSourceConfigLogs(TypedDict, total=False):
    type: Required[Literal["logs"]]
    """The type of data source. Always `logs`."""

    metadata: Dict[str, object]
    """Metadata filters for the logs data source."""


class DataSourceConfigStoredCompletions(TypedDict, total=False):
    type: Required[Literal["stored_completions"]]
    """The type of data source. Always `stored_completions`."""

    metadata: Dict[str, object]
    """Metadata filters for the stored completions data source."""


DataSourceConfig: TypeAlias = Union[DataSourceConfigCustom, DataSourceConfigLogs, DataSourceConfigStoredCompletions]


class TestingCriterionLabelModelInputSimpleInputMessage(TypedDict, total=False):
    content: Required[str]
    """The content of the message."""

    role: Required[str]
    """The role of the message (e.g. "system", "assistant", "user")."""


class TestingCriterionLabelModelInputEvalItemContentOutputText(TypedDict, total=False):
    text: Required[str]
    """The text output from the model."""

    type: Required[Literal["output_text"]]
    """The type of the output text. Always `output_text`."""


TestingCriterionLabelModelInputEvalItemContent: TypeAlias = Union[
    str, ResponseInputTextParam, TestingCriterionLabelModelInputEvalItemContentOutputText
]


class TestingCriterionLabelModelInputEvalItem(TypedDict, total=False):
    content: Required[TestingCriterionLabelModelInputEvalItemContent]
    """Text inputs to the model - can contain template strings."""

    role: Required[Literal["user", "assistant", "system", "developer"]]
    """The role of the message input.

    One of `user`, `assistant`, `system`, or `developer`.
    """

    type: Literal["message"]
    """The type of the message input. Always `message`."""


TestingCriterionLabelModelInput: TypeAlias = Union[
    TestingCriterionLabelModelInputSimpleInputMessage, TestingCriterionLabelModelInputEvalItem
]


class TestingCriterionLabelModel(TypedDict, total=False):
    input: Required[Iterable[TestingCriterionLabelModelInput]]
    """A list of chat messages forming the prompt or context.

    May include variable references to the `item` namespace, ie {{item.name}}.
    """

    labels: Required[List[str]]
    """The labels to classify to each item in the evaluation."""

    model: Required[str]
    """The model to use for the evaluation. Must support structured outputs."""

    name: Required[str]
    """The name of the grader."""

    passing_labels: Required[List[str]]
    """The labels that indicate a passing result. Must be a subset of labels."""

    type: Required[Literal["label_model"]]
    """The object type, which is always `label_model`."""


class TestingCriterionTextSimilarity(TextSimilarityGraderParam, total=False):
    pass_threshold: Required[float]
    """The threshold for the score."""


class TestingCriterionPython(PythonGraderParam, total=False):
    pass_threshold: float
    """The threshold for the score."""


class TestingCriterionScoreModel(ScoreModelGraderParam, total=False):
    pass_threshold: float
    """The threshold for the score."""


TestingCriterion: TypeAlias = Union[
    TestingCriterionLabelModel,
    StringCheckGraderParam,
    TestingCriterionTextSimilarity,
    TestingCriterionPython,
    TestingCriterionScoreModel,
]

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\clean.py ===
"""
    pygments.lexers.clean
    ~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Clean language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import ExtendedRegexLexer, words, default, include, bygroups
from pygments.token import Comment, Error, Keyword, Literal, Name, Number, \
    Operator, Punctuation, String, Whitespace

__all__ = ['CleanLexer']


class CleanLexer(ExtendedRegexLexer):
    """
    Lexer for the general purpose, state-of-the-art, pure and lazy functional
    programming language Clean.

    .. versionadded: 2.2
    """
    name = 'Clean'
    url = 'http://clean.cs.ru.nl/Clean'
    aliases = ['clean']
    filenames = ['*.icl', '*.dcl']
    version_added = ''

    keywords = (
        'case', 'ccall', 'class', 'code', 'code inline', 'derive', 'export',
        'foreign', 'generic', 'if', 'in', 'infix', 'infixl', 'infixr',
        'instance', 'let', 'of', 'otherwise', 'special', 'stdcall', 'where',
        'with')

    modulewords = ('implementation', 'definition', 'system')

    lowerId = r'[a-z`][\w`]*'
    upperId = r'[A-Z`][\w`]*'
    funnyId = r'[~@#$%\^?!+\-*<>\\/|&=:]+'
    scoreUpperId = r'_' + upperId
    scoreLowerId = r'_' + lowerId
    moduleId = r'[a-zA-Z_][a-zA-Z0-9_.`]+'
    classId = '|'.join([lowerId, upperId, funnyId])

    tokens = {
        'root': [
            include('comments'),
            include('keywords'),
            include('module'),
            include('import'),
            include('whitespace'),
            include('literals'),
            include('operators'),
            include('delimiters'),
            include('names'),
        ],
        'whitespace': [
            (r'\s+', Whitespace),
        ],
        'comments': [
            (r'//.*\n', Comment.Single),
            (r'/\*', Comment.Multiline, 'comments.in'),
            (r'/\*\*', Comment.Special, 'comments.in'),
        ],
        'comments.in': [
            (r'\*\/', Comment.Multiline, '#pop'),
            (r'/\*', Comment.Multiline, '#push'),
            (r'[^*/]+', Comment.Multiline),
            (r'\*(?!/)', Comment.Multiline),
            (r'/', Comment.Multiline),
        ],
        'keywords': [
            (words(keywords, prefix=r'\b', suffix=r'\b'), Keyword),
        ],
        'module': [
            (words(modulewords, prefix=r'\b', suffix=r'\b'), Keyword.Namespace),
            (r'\bmodule\b', Keyword.Namespace, 'module.name'),
        ],
        'module.name': [
            include('whitespace'),
            (moduleId, Name.Class, '#pop'),
        ],
        'import': [
            (r'\b(import)\b(\s*)', bygroups(Keyword, Whitespace), 'import.module'),
            (r'\b(from)\b(\s*)\b(' + moduleId + r')\b(\s*)\b(import)\b',
                bygroups(Keyword, Whitespace, Name.Class, Whitespace, Keyword),
                'import.what'),
        ],
        'import.module': [
            (r'\b(qualified)\b(\s*)', bygroups(Keyword, Whitespace)),
            (r'(\s*)\b(as)\b', bygroups(Whitespace, Keyword), ('#pop', 'import.module.as')),
            (moduleId, Name.Class),
            (r'(\s*)(,)(\s*)', bygroups(Whitespace, Punctuation, Whitespace)),
            (r'\s+', Whitespace),
            default('#pop'),
        ],
        'import.module.as': [
            include('whitespace'),
            (lowerId, Name.Class, '#pop'),
            (upperId, Name.Class, '#pop'),
        ],
        'import.what': [
            (r'\b(class)\b(\s+)(' + classId + r')',
                bygroups(Keyword, Whitespace, Name.Class), 'import.what.class'),
            (r'\b(instance)(\s+)(' + classId + r')(\s+)',
                bygroups(Keyword, Whitespace, Name.Class, Whitespace), 'import.what.instance'),
            (r'(::)(\s*)\b(' + upperId + r')\b',
                bygroups(Punctuation, Whitespace, Name.Class), 'import.what.type'),
            (r'\b(generic)\b(\s+)\b(' + lowerId + '|' + upperId + r')\b',
                bygroups(Keyword, Whitespace, Name)),
            include('names'),
            (r'(,)(\s+)', bygroups(Punctuation, Whitespace)),
            (r'$', Whitespace, '#pop'),
            include('whitespace'),
        ],
        'import.what.class': [
            (r',', Punctuation, '#pop'),
            (r'\(', Punctuation, 'import.what.class.members'),
            (r'$', Whitespace, '#pop:2'),
            include('whitespace'),
        ],
        'import.what.class.members': [
            (r',', Punctuation),
            (r'\.\.', Punctuation),
            (r'\)', Punctuation, '#pop'),
            include('names'),
        ],
        'import.what.instance': [
            (r'[,)]', Punctuation, '#pop'),
            (r'\(', Punctuation, 'import.what.instance'),
            (r'$', Whitespace, '#pop:2'),
            include('whitespace'),
            include('names'),
        ],
        'import.what.type': [
            (r',', Punctuation, '#pop'),
            (r'[({]', Punctuation, 'import.what.type.consesandfields'),
            (r'$', Whitespace, '#pop:2'),
            include('whitespace'),
        ],
        'import.what.type.consesandfields': [
            (r',', Punctuation),
            (r'\.\.', Punctuation),
            (r'[)}]', Punctuation, '#pop'),
            include('names'),
        ],
        'literals': [
            (r'\'([^\'\\]|\\(x[\da-fA-F]+|\d+|.))\'', Literal.Char),
            (r'[+~-]?0[0-7]+\b', Number.Oct),
            (r'[+~-]?\d+\.\d+(E[+-]?\d+)?', Number.Float),
            (r'[+~-]?\d+\b', Number.Integer),
            (r'[+~-]?0x[\da-fA-F]+\b', Number.Hex),
            (r'True|False', Literal),
            (r'"', String.Double, 'literals.stringd'),
        ],
        'literals.stringd': [
            (r'[^\\"\n]+', String.Double),
            (r'"', String.Double, '#pop'),
            (r'\\.', String.Double),
            (r'[$\n]', Error, '#pop'),
        ],
        'operators': [
            (r'[-~@#$%\^?!+*<>\\/|&=:.]+', Operator),
            (r'\b_+\b', Operator),
        ],
        'delimiters': [
            (r'[,;(){}\[\]]', Punctuation),
            (r'(\')([\w`.]+)(\')',
                bygroups(Punctuation, Name.Class, Punctuation)),
        ],
        'names': [
            (lowerId, Name),
            (scoreLowerId, Name),
            (funnyId, Name.Function),
            (upperId, Name.Class),
            (scoreUpperId, Name.Class),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\bindings.py ===
from __future__ import annotations

import traceback

import win32api
import win32con
import win32ui

from . import (  # nopycln: import # Injects fast_readline into the IDLE auto-indent extension
    IDLEenvironment,
)

HANDLER_ARGS_GUESS = 0
HANDLER_ARGS_NATIVE = 1
HANDLER_ARGS_IDLE = 2
HANDLER_ARGS_EXTENSION = 3

next_id = 5000

event_to_commands: dict[str, int] = {}  # dict of event names to IDs
command_to_events: dict[int, str] = {}  # dict of IDs to event names


def assign_command_id(event, id=0):
    global next_id
    if id == 0:
        id = event_to_commands.get(event, 0)
        if id == 0:
            id = next_id
            next_id += 1
        # Only map the ones we allocated - specified ones are assumed to have a handler
        command_to_events[id] = event
    event_to_commands[event] = id
    return id


class SendCommandHandler:
    def __init__(self, cmd):
        self.cmd = cmd

    def __call__(self, *args):
        win32ui.GetMainFrame().SendMessage(win32con.WM_COMMAND, self.cmd)


class Binding:
    def __init__(self, handler, handler_args_type):
        self.handler = handler
        self.handler_args_type = handler_args_type


class BindingsManager:
    def __init__(self, parent_view):
        self.parent_view = parent_view
        self.bindings = {}  # dict of Binding instances.
        self.keymap = {}

    def prepare_configure(self):
        self.keymap = {}

    def complete_configure(self):
        for id in command_to_events:
            self.parent_view.HookCommand(self._OnCommand, id)

    def close(self):
        self.parent_view = self.bindings = self.keymap = None

    def report_error(self, problem):
        try:
            win32ui.SetStatusText(problem, 1)
        except win32ui.error:
            # No status bar!
            print(problem)

    def update_keymap(self, keymap):
        self.keymap.update(keymap)

    def bind(self, event, handler, handler_args_type=HANDLER_ARGS_GUESS, cid=0):
        if handler is None:
            handler = SendCommandHandler(cid)
        self.bindings[event] = self._new_binding(handler, handler_args_type)
        self.bind_command(event, cid)

    def bind_command(self, event, id=0):
        "Binds an event to a Windows control/command ID"
        id = assign_command_id(event, id)
        return id

    def get_command_id(self, event):
        id = event_to_commands.get(event)
        if id is None:
            # See if we even have an event of that name!?
            if event not in self.bindings:
                return None
            id = self.bind_command(event)
        return id

    def _OnCommand(self, id, code):
        event = command_to_events.get(id)
        if event is None:
            self.report_error("No event associated with event ID %d" % id)
            return 1
        return self.fire(event)

    def _new_binding(self, event, handler_args_type):
        return Binding(event, handler_args_type)

    def _get_IDLE_handler(self, ext, handler):
        try:
            instance = self.parent_view.idle.IDLEExtension(ext)
            name = handler.replace("-", "_") + "_event"
            return getattr(instance, name)
        except (ImportError, AttributeError):
            msg = f"Can not find event '{handler}' in IDLE extension '{ext}'"
            self.report_error(msg)
            return None

    def fire(self, event, event_param=None):
        # Fire the specified event.  Result is native Pythonwin result
        # (ie, 1==pass one, 0 or None==handled)

        # First look up the event directly - if there, we are set.
        binding = self.bindings.get(event)
        if binding is None:
            # If possible, find it!
            # A native method name
            handler = getattr(self.parent_view, event + "Event", None)
            if handler is None:
                # Can't decide if I should report an error??
                self.report_error("The event name '%s' can not be found." % event)
                # Either way, just let the default handlers grab it.
                return 1
            binding = self._new_binding(handler, HANDLER_ARGS_NATIVE)
            # Cache it.
            self.bindings[event] = binding

        handler_args_type = binding.handler_args_type
        # Now actually fire it.
        if handler_args_type == HANDLER_ARGS_GUESS:
            # Can't be native, as natives are never added with "guess".
            # Must be extension or IDLE.
            if event[0] == "<":
                handler_args_type = HANDLER_ARGS_IDLE
            else:
                handler_args_type = HANDLER_ARGS_EXTENSION
        try:
            if handler_args_type == HANDLER_ARGS_EXTENSION:
                args = self.parent_view.idle, event_param
            else:
                args = (event_param,)
            rc = binding.handler(*args)
            if handler_args_type == HANDLER_ARGS_IDLE:
                # Convert to our return code.
                if rc in (None, "break"):
                    rc = 0
                else:
                    rc = 1
        except:
            message = "Firing event '%s' failed." % event
            print(message)
            traceback.print_exc()
            self.report_error(message)
            rc = 1  # Let any default handlers have a go!
        return rc

    def fire_key_event(self, msg):
        key = msg[2]
        keyState = 0
        if win32api.GetKeyState(win32con.VK_CONTROL) & 0x8000:
            keyState |= win32con.RIGHT_CTRL_PRESSED | win32con.LEFT_CTRL_PRESSED
        if win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000:
            keyState |= win32con.SHIFT_PRESSED
        if win32api.GetKeyState(win32con.VK_MENU) & 0x8000:
            keyState |= win32con.LEFT_ALT_PRESSED | win32con.RIGHT_ALT_PRESSED
        keyinfo = key, keyState
        # Special hacks for the dead-char key on non-US keyboards.
        # (XXX - which do not work :-(
        event = self.keymap.get(keyinfo)
        if event is None:
            return 1
        return self.fire(event, None)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\requests\__init__.py ===
#   __
#  /__)  _  _     _   _ _/   _
# / (   (- (/ (/ (- _)  /  _)
#          /

"""
Requests HTTP Library
~~~~~~~~~~~~~~~~~~~~~

Requests is an HTTP library, written in Python, for human beings.
Basic GET usage:

   >>> import requests
   >>> r = requests.get('https://www.python.org')
   >>> r.status_code
   200
   >>> b'Python is a programming language' in r.content
   True

... or POST:

   >>> payload = dict(key1='value1', key2='value2')
   >>> r = requests.post('https://httpbin.org/post', data=payload)
   >>> print(r.text)
   {
     ...
     "form": {
       "key1": "value1",
       "key2": "value2"
     },
     ...
   }

The other HTTP methods are supported - see `requests.api`. Full documentation
is at <https://requests.readthedocs.io>.

:copyright: (c) 2017 by Kenneth Reitz.
:license: Apache 2.0, see LICENSE for more details.
"""

import warnings

from pip._vendor import urllib3

from .exceptions import RequestsDependencyWarning

charset_normalizer_version = None
chardet_version = None


def check_compatibility(urllib3_version, chardet_version, charset_normalizer_version):
    urllib3_version = urllib3_version.split(".")
    assert urllib3_version != ["dev"]  # Verify urllib3 isn't installed from git.

    # Sometimes, urllib3 only reports its version as 16.1.
    if len(urllib3_version) == 2:
        urllib3_version.append("0")

    # Check urllib3 for compatibility.
    major, minor, patch = urllib3_version  # noqa: F811
    major, minor, patch = int(major), int(minor), int(patch)
    # urllib3 >= 1.21.1
    assert major >= 1
    if major == 1:
        assert minor >= 21

    # Check charset_normalizer for compatibility.
    if chardet_version:
        major, minor, patch = chardet_version.split(".")[:3]
        major, minor, patch = int(major), int(minor), int(patch)
        # chardet_version >= 3.0.2, < 6.0.0
        assert (3, 0, 2) <= (major, minor, patch) < (6, 0, 0)
    elif charset_normalizer_version:
        major, minor, patch = charset_normalizer_version.split(".")[:3]
        major, minor, patch = int(major), int(minor), int(patch)
        # charset_normalizer >= 2.0.0 < 4.0.0
        assert (2, 0, 0) <= (major, minor, patch) < (4, 0, 0)
    else:
        # pip does not need or use character detection
        pass


def _check_cryptography(cryptography_version):
    # cryptography < 1.3.4
    try:
        cryptography_version = list(map(int, cryptography_version.split(".")))
    except ValueError:
        return

    if cryptography_version < [1, 3, 4]:
        warning = "Old version of cryptography ({}) may cause slowdown.".format(
            cryptography_version
        )
        warnings.warn(warning, RequestsDependencyWarning)


# Check imported dependencies for compatibility.
try:
    check_compatibility(
        urllib3.__version__, chardet_version, charset_normalizer_version
    )
except (AssertionError, ValueError):
    warnings.warn(
        "urllib3 ({}) or chardet ({})/charset_normalizer ({}) doesn't match a supported "
        "version!".format(
            urllib3.__version__, chardet_version, charset_normalizer_version
        ),
        RequestsDependencyWarning,
    )

# Attempt to enable urllib3's fallback for SNI support
# if the standard library doesn't support SNI or the
# 'ssl' library isn't available.
try:
    # Note: This logic prevents upgrading cryptography on Windows, if imported
    #       as part of pip.
    from pip._internal.utils.compat import WINDOWS
    if not WINDOWS:
        raise ImportError("pip internals: don't import cryptography on Windows")
    try:
        import ssl
    except ImportError:
        ssl = None

    if not getattr(ssl, "HAS_SNI", False):
        from pip._vendor.urllib3.contrib import pyopenssl

        pyopenssl.inject_into_urllib3()

        # Check cryptography version
        from cryptography import __version__ as cryptography_version

        _check_cryptography(cryptography_version)
except ImportError:
    pass

# urllib3's DependencyWarnings should be silenced.
from pip._vendor.urllib3.exceptions import DependencyWarning

warnings.simplefilter("ignore", DependencyWarning)

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

from . import packages, utils
from .__version__ import (
    __author__,
    __author_email__,
    __build__,
    __cake__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
)
from .api import delete, get, head, options, patch, post, put, request
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    FileModeWarning,
    HTTPError,
    JSONDecodeError,
    ReadTimeout,
    RequestException,
    Timeout,
    TooManyRedirects,
    URLRequired,
)
from .models import PreparedRequest, Request, Response
from .sessions import Session, session
from .status_codes import codes

logging.getLogger(__name__).addHandler(NullHandler())

# FileModeWarnings go off per the default.
warnings.simplefilter("default", FileModeWarning, append=True)

# === NexusCore/openenv\Lib\site-packages\aiohttp\formdata.py ===
import io
import warnings
from typing import Any, Iterable, List, Optional
from urllib.parse import urlencode

from multidict import MultiDict, MultiDictProxy

from . import hdrs, multipart, payload
from .helpers import guess_filename
from .payload import Payload

__all__ = ("FormData",)


class FormData:
    """Helper class for form body generation.

    Supports multipart/form-data and application/x-www-form-urlencoded.
    """

    def __init__(
        self,
        fields: Iterable[Any] = (),
        quote_fields: bool = True,
        charset: Optional[str] = None,
        *,
        default_to_multipart: bool = False,
    ) -> None:
        self._writer = multipart.MultipartWriter("form-data")
        self._fields: List[Any] = []
        self._is_multipart = default_to_multipart
        self._quote_fields = quote_fields
        self._charset = charset

        if isinstance(fields, dict):
            fields = list(fields.items())
        elif not isinstance(fields, (list, tuple)):
            fields = (fields,)
        self.add_fields(*fields)

    @property
    def is_multipart(self) -> bool:
        return self._is_multipart

    def add_field(
        self,
        name: str,
        value: Any,
        *,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        content_transfer_encoding: Optional[str] = None,
    ) -> None:

        if isinstance(value, io.IOBase):
            self._is_multipart = True
        elif isinstance(value, (bytes, bytearray, memoryview)):
            msg = (
                "In v4, passing bytes will no longer create a file field. "
                "Please explicitly use the filename parameter or pass a BytesIO object."
            )
            if filename is None and content_transfer_encoding is None:
                warnings.warn(msg, DeprecationWarning)
                filename = name

        type_options: MultiDict[str] = MultiDict({"name": name})
        if filename is not None and not isinstance(filename, str):
            raise TypeError("filename must be an instance of str. Got: %s" % filename)
        if filename is None and isinstance(value, io.IOBase):
            filename = guess_filename(value, name)
        if filename is not None:
            type_options["filename"] = filename
            self._is_multipart = True

        headers = {}
        if content_type is not None:
            if not isinstance(content_type, str):
                raise TypeError(
                    "content_type must be an instance of str. Got: %s" % content_type
                )
            headers[hdrs.CONTENT_TYPE] = content_type
            self._is_multipart = True
        if content_transfer_encoding is not None:
            if not isinstance(content_transfer_encoding, str):
                raise TypeError(
                    "content_transfer_encoding must be an instance"
                    " of str. Got: %s" % content_transfer_encoding
                )
            msg = (
                "content_transfer_encoding is deprecated. "
                "To maintain compatibility with v4 please pass a BytesPayload."
            )
            warnings.warn(msg, DeprecationWarning)
            self._is_multipart = True

        self._fields.append((type_options, headers, value))

    def add_fields(self, *fields: Any) -> None:
        to_add = list(fields)

        while to_add:
            rec = to_add.pop(0)

            if isinstance(rec, io.IOBase):
                k = guess_filename(rec, "unknown")
                self.add_field(k, rec)  # type: ignore[arg-type]

            elif isinstance(rec, (MultiDictProxy, MultiDict)):
                to_add.extend(rec.items())

            elif isinstance(rec, (list, tuple)) and len(rec) == 2:
                k, fp = rec
                self.add_field(k, fp)  # type: ignore[arg-type]

            else:
                raise TypeError(
                    "Only io.IOBase, multidict and (name, file) "
                    "pairs allowed, use .add_field() for passing "
                    "more complex parameters, got {!r}".format(rec)
                )

    def _gen_form_urlencoded(self) -> payload.BytesPayload:
        # form data (x-www-form-urlencoded)
        data = []
        for type_options, _, value in self._fields:
            data.append((type_options["name"], value))

        charset = self._charset if self._charset is not None else "utf-8"

        if charset == "utf-8":
            content_type = "application/x-www-form-urlencoded"
        else:
            content_type = "application/x-www-form-urlencoded; charset=%s" % charset

        return payload.BytesPayload(
            urlencode(data, doseq=True, encoding=charset).encode(),
            content_type=content_type,
        )

    def _gen_form_data(self) -> multipart.MultipartWriter:
        """Encode a list of fields using the multipart/form-data MIME format"""
        for dispparams, headers, value in self._fields:
            try:
                if hdrs.CONTENT_TYPE in headers:
                    part = payload.get_payload(
                        value,
                        content_type=headers[hdrs.CONTENT_TYPE],
                        headers=headers,
                        encoding=self._charset,
                    )
                else:
                    part = payload.get_payload(
                        value, headers=headers, encoding=self._charset
                    )
            except Exception as exc:
                raise TypeError(
                    "Can not serialize value type: %r\n "
                    "headers: %r\n value: %r" % (type(value), headers, value)
                ) from exc

            if dispparams:
                part.set_content_disposition(
                    "form-data", quote_fields=self._quote_fields, **dispparams
                )
                # FIXME cgi.FieldStorage doesn't likes body parts with
                # Content-Length which were sent via chunked transfer encoding
                assert part.headers is not None
                part.headers.popall(hdrs.CONTENT_LENGTH, None)

            self._writer.append_payload(part)

        self._fields.clear()
        return self._writer

    def __call__(self) -> Payload:
        if self._is_multipart:
            return self._gen_form_data()
        else:
            return self._gen_form_urlencoded()

# === NexusCore/openenv\Lib\site-packages\astor\tree_walk.py ===
# -*- coding: utf-8 -*-
"""
Part of the astor library for Python AST manipulation.

License: 3-clause BSD

Copyright 2012 (c) Patrick Maupin
Copyright 2013 (c) Berker Peksag

This file contains a TreeWalk class that views a node tree
as a unified whole and allows several modes of traversal.

"""

from .node_util import iter_node


class MetaFlatten(type):
    """This metaclass is used to flatten classes to remove
    class hierarchy.

    This makes it easier to manipulate classes (find
    attributes in a single dict, etc.)

    """
    def __new__(clstype, name, bases, clsdict):
        newbases = (object,)
        newdict = {}
        for base in reversed(bases):
            if base not in newbases:
                newdict.update(vars(base))
        newdict.update(clsdict)
        # These are class-bound, we should let Python recreate them.
        newdict.pop('__dict__', None)
        newdict.pop('__weakref__', None)
        # Delegate the real work to type
        return type.__new__(clstype, name, newbases, newdict)


MetaFlatten = MetaFlatten('MetaFlatten', (object,), {})


class TreeWalk(MetaFlatten):
    """The TreeWalk class can be used as a superclass in order
    to walk an AST or similar tree.

    Unlike other treewalkers, this class can walk a tree either
    recursively or non-recursively.  Subclasses can define
    methods with the following signatures::

        def pre_xxx(self):
            pass

        def post_xxx(self):
            pass

        def init_xxx(self):
            pass

    Where 'xxx' is one of:

      - A class name
      - An attribute member name concatenated with '_name'
        For example, 'pre_targets_name' will process nodes
        that are referenced by the name 'targets' in their
        parent's node.
      - An attribute member name concatenated with '_item'
        For example, 'pre_targets_item'  will process nodes
        that are in a list that is the targets attribute
        of some node.

    pre_xxx will process a node before processing any of its subnodes.
    if the return value from pre_xxx evalates to true, then walk
    will not process any of the subnodes.  Those can be manually
    processed, if desired, by calling self.walk(node) on the subnodes
    before returning True.

    post_xxx will process a node after processing all its subnodes.

    init_xxx methods can decorate the class instance with subclass-specific
    information.  A single init_whatever method could be written, but to
    make it easy to keep initialization with use, any number of init_xxx
    methods can be written.  They will be called in alphabetical order.

    """

    def __init__(self, node=None):
        self.nodestack = []
        self.setup()
        if node is not None:
            self.walk(node)

    def setup(self):
        """All the node-specific handlers are setup at
        object initialization time.

        """
        self.pre_handlers = pre_handlers = {}
        self.post_handlers = post_handlers = {}
        for name in sorted(vars(type(self))):
            if name.startswith('init_'):
                getattr(self, name)()
            elif name.startswith('pre_'):
                pre_handlers[name[4:]] = getattr(self, name)
            elif name.startswith('post_'):
                post_handlers[name[5:]] = getattr(self, name)

    def walk(self, node, name='', list=list, len=len, type=type):
        """Walk the tree starting at a given node.

        Maintain a stack of nodes.

        """
        pre_handlers = self.pre_handlers.get
        post_handlers = self.post_handlers.get
        nodestack = self.nodestack
        emptystack = len(nodestack)
        append, pop = nodestack.append, nodestack.pop
        append([node, name, list(iter_node(node, name + '_item')), -1])
        while len(nodestack) > emptystack:
            node, name, subnodes, index = nodestack[-1]
            if index >= len(subnodes):
                handler = (post_handlers(type(node).__name__) or
                           post_handlers(name + '_name'))
                if handler is None:
                    pop()
                    continue
                self.cur_node = node
                self.cur_name = name
                handler()
                current = nodestack and nodestack[-1]
                popstack = current and current[0] is node
                if popstack and current[-1] >= len(current[-2]):
                    pop()
                continue
            nodestack[-1][-1] = index + 1
            if index < 0:
                handler = (pre_handlers(type(node).__name__) or
                           pre_handlers(name + '_name'))
                if handler is not None:
                    self.cur_node = node
                    self.cur_name = name
                    if handler():
                        pop()
            else:
                node, name = subnodes[index]
                append([node, name, list(iter_node(node, name + '_item')), -1])

    @property
    def parent(self):
        """Return the parent node of the current node."""
        nodestack = self.nodestack
        if len(nodestack) < 2:
            return None
        return nodestack[-2][0]

    @property
    def parent_name(self):
        """Return the parent node and name."""
        nodestack = self.nodestack
        if len(nodestack) < 2:
            return None
        return nodestack[-2][:2]

    def replace(self, new_node):
        """Replace a node after first checking integrity of node stack."""
        cur_node = self.cur_node
        nodestack = self.nodestack
        cur = nodestack.pop()
        prev = nodestack[-1]
        index = prev[-1] - 1
        oldnode, name = prev[-2][index]
        assert cur[0] is cur_node is oldnode, (cur[0], cur_node, prev[-2],
                                               index)
        parent = prev[0]
        if isinstance(parent, list):
            parent[index] = new_node
        else:
            setattr(parent, name, new_node)

# === NexusCore/openenv\Lib\site-packages\pyee\asyncio.py ===
# -*- coding: utf-8 -*-

from asyncio import AbstractEventLoop, ensure_future, Future, iscoroutine, wait
from typing import Any, Callable, cast, Dict, Optional, Set, Tuple

from pyee.base import EventEmitter

Self = Any

__all__ = ["AsyncIOEventEmitter"]


class AsyncIOEventEmitter(EventEmitter):
    """An event emitter class which can run asyncio coroutines in addition to
    synchronous blocking functions. For example:

    ```py
    @ee.on('event')
    async def async_handler(*args, **kwargs):
        await returns_a_future()
    ```

    On emit, the event emitter  will automatically schedule the coroutine using
    `asyncio.ensure_future` and the configured event loop (defaults to
    `asyncio.get_event_loop()`).

    Unlike the case with the EventEmitter, all exceptions raised by
    event handlers are automatically emitted on the `error` event. This is
    important for asyncio coroutines specifically but is also handled for
    synchronous functions for consistency.

    When `loop` is specified, the supplied event loop will be used when
    scheduling work with `ensure_future`. Otherwise, the default asyncio
    event loop is used.

    For asyncio coroutine event handlers, calling emit is non-blocking.
    In other words, you do not have to await any results from emit, and the
    coroutine is scheduled in a fire-and-forget fashion.
    """

    def __init__(self: Self, loop: Optional[AbstractEventLoop] = None) -> None:
        super(AsyncIOEventEmitter, self).__init__()
        self._loop: Optional[AbstractEventLoop] = loop
        self._waiting: Set[Future] = set()

    def emit(
        self: Self,
        event: str,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Emit `event`, passing `*args` and `**kwargs` to each attached
        function or coroutine. Returns `True` if any functions are attached to
        `event`; otherwise returns `False`.

        Example:

        ```py
        ee.emit('data', '00101001')
        ```

        Assuming `data` is an attached function, this will call
        `data('00101001')'`.

        When executing coroutine handlers, their respective futures will be
        stored in a "waiting" state. These futures may be waited on or
        canceled with `wait_for_complete` and `cancel`, respectively; and
        their status may be checked via the `complete` property.
        """
        return super().emit(event, *args, **kwargs)

    def _emit_run(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        try:
            coro: Any = f(*args, **kwargs)
        except Exception as exc:
            self.emit("error", exc)
        else:
            if iscoroutine(coro):
                if self._loop:
                    # ensure_future is *extremely* cranky about the types here,
                    # but this is relatively well-tested and I think the types
                    # are more strict than they should be
                    fut: Any = ensure_future(cast(Any, coro), loop=self._loop)
                else:
                    fut = ensure_future(cast(Any, coro))

            elif isinstance(coro, Future):
                fut = cast(Any, coro)
            else:
                return

            def callback(f: Future) -> None:
                self._waiting.discard(f)

                if f.cancelled():
                    return

                exc: Optional[BaseException] = f.exception()
                if exc:
                    self.emit("error", exc)

            fut.add_done_callback(callback)
            self._waiting.add(fut)

    async def wait_for_complete(self: Self) -> None:
        """Waits for all pending tasks to complete. For example:

        ```py
        @ee.on('event')
        async def async_handler(*args, **kwargs):
            await returns_a_future()

        # Triggers execution of async_handler
        ee.emit('data', '00101001')

        await ee.wait_for_complete()

        # async_handler has completed execution
        ```

        This is useful if you're attempting a graceful shutdown of your
        application and want to ensure all coroutines have completed execution
        beforehand.
        """
        if self._waiting:
            await wait(self._waiting)

    def cancel(self: Self) -> None:
        """Cancel all pending tasks. For example:

        ```py
        @ee.on('event')
        async def async_handler(*args, **kwargs):
            await returns_a_future()

        # Triggers execution of async_handler
        ee.emit('data', '00101001')

        ee.cancel()

        # async_handler execution has been canceled
        ```

        This is useful if you're attempting to shut down your application and
        attempts at a graceful shutdown via `wait_for_complete` have failed.
        """
        for fut in self._waiting:
            if not fut.done() and not fut.cancelled():
                fut.cancel()
        self._waiting.clear()

    @property
    def complete(self: Self) -> bool:
        """When true, there are no pending tasks, and execution is complete.
        For example:

        ```py
        @ee.on('event')
        async def async_handler(*args, **kwargs):
            await returns_a_future()

        # Triggers execution of async_handler
        ee.emit('data', '00101001')

        # async_handler is still running, so this prints False
        print(ee.complete)

        await ee.wait_for_complete()

        # async_handler has completed execution, so this prints True
        print(ee.complete)
        ```
        """
        return not self._waiting

# === NexusCore/openenv\Lib\site-packages\tqdm\gui.py ===
"""
Matplotlib GUI progressbar decorator for iterators.

Usage:
>>> from tqdm.gui import trange, tqdm
>>> for i in trange(10):
...     ...
"""
# future division is important to divide integers and get as
# a result precise floating numbers (instead of truncated int)
import re
from warnings import warn

# to inherit from the tqdm class
from .std import TqdmExperimentalWarning
from .std import tqdm as std_tqdm

# import compatibility functions and utilities

__author__ = {"github.com/": ["casperdcl", "lrq3000"]}
__all__ = ['tqdm_gui', 'tgrange', 'tqdm', 'trange']


class tqdm_gui(std_tqdm):  # pragma: no cover
    """Experimental Matplotlib GUI version of tqdm!"""
    # TODO: @classmethod: write() on GUI?
    def __init__(self, *args, **kwargs):
        from collections import deque

        import matplotlib as mpl
        import matplotlib.pyplot as plt
        kwargs = kwargs.copy()
        kwargs['gui'] = True
        colour = kwargs.pop('colour', 'g')
        super().__init__(*args, **kwargs)

        if self.disable:
            return

        warn("GUI is experimental/alpha", TqdmExperimentalWarning, stacklevel=2)
        self.mpl = mpl
        self.plt = plt

        # Remember if external environment uses toolbars
        self.toolbar = self.mpl.rcParams['toolbar']
        self.mpl.rcParams['toolbar'] = 'None'

        self.mininterval = max(self.mininterval, 0.5)
        self.fig, ax = plt.subplots(figsize=(9, 2.2))
        # self.fig.subplots_adjust(bottom=0.2)
        total = self.__len__()  # avoids TypeError on None #971
        if total is not None:
            self.xdata = []
            self.ydata = []
            self.zdata = []
        else:
            self.xdata = deque([])
            self.ydata = deque([])
            self.zdata = deque([])
        self.line1, = ax.plot(self.xdata, self.ydata, color='b')
        self.line2, = ax.plot(self.xdata, self.zdata, color='k')
        ax.set_ylim(0, 0.001)
        if total is not None:
            ax.set_xlim(0, 100)
            ax.set_xlabel("percent")
            self.fig.legend((self.line1, self.line2), ("cur", "est"),
                            loc='center right')
            # progressbar
            self.hspan = plt.axhspan(0, 0.001, xmin=0, xmax=0, color=colour)
        else:
            # ax.set_xlim(-60, 0)
            ax.set_xlim(0, 60)
            ax.invert_xaxis()
            ax.set_xlabel("seconds")
            ax.legend(("cur", "est"), loc='lower left')
        ax.grid()
        # ax.set_xlabel('seconds')
        ax.set_ylabel((self.unit if self.unit else "it") + "/s")
        if self.unit_scale:
            plt.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
            ax.yaxis.get_offset_text().set_x(-0.15)

        # Remember if external environment is interactive
        self.wasion = plt.isinteractive()
        plt.ion()
        self.ax = ax

    def close(self):
        if self.disable:
            return

        self.disable = True

        with self.get_lock():
            self._instances.remove(self)

        # Restore toolbars
        self.mpl.rcParams['toolbar'] = self.toolbar
        # Return to non-interactive mode
        if not self.wasion:
            self.plt.ioff()
        if self.leave:
            self.display()
        else:
            self.plt.close(self.fig)

    def clear(self, *_, **__):
        pass

    def display(self, *_, **__):
        n = self.n
        cur_t = self._time()
        elapsed = cur_t - self.start_t
        delta_it = n - self.last_print_n
        delta_t = cur_t - self.last_print_t

        # Inline due to multiple calls
        total = self.total
        xdata = self.xdata
        ydata = self.ydata
        zdata = self.zdata
        ax = self.ax
        line1 = self.line1
        line2 = self.line2
        hspan = getattr(self, 'hspan', None)
        # instantaneous rate
        y = delta_it / delta_t
        # overall rate
        z = n / elapsed
        # update line data
        xdata.append(n * 100.0 / total if total else cur_t)
        ydata.append(y)
        zdata.append(z)

        # Discard old values
        # xmin, xmax = ax.get_xlim()
        # if (not total) and elapsed > xmin * 1.1:
        if (not total) and elapsed > 66:
            xdata.popleft()
            ydata.popleft()
            zdata.popleft()

        ymin, ymax = ax.get_ylim()
        if y > ymax or z > ymax:
            ymax = 1.1 * y
            ax.set_ylim(ymin, ymax)
            ax.figure.canvas.draw()

        if total:
            line1.set_data(xdata, ydata)
            line2.set_data(xdata, zdata)
            if hspan:
                hspan.set_xy((0, ymin))
                hspan.set_height(ymax - ymin)
                hspan.set_width(n / total)
        else:
            t_ago = [cur_t - i for i in xdata]
            line1.set_data(t_ago, ydata)
            line2.set_data(t_ago, zdata)

        d = self.format_dict
        # remove {bar}
        d['bar_format'] = (d['bar_format'] or "{l_bar}<bar/>{r_bar}").replace(
            "{bar}", "<bar/>")
        msg = self.format_meter(**d)
        if '<bar/>' in msg:
            msg = "".join(re.split(r'\|?<bar/>\|?', msg, maxsplit=1))
        ax.set_title(msg, fontname="DejaVu Sans Mono", fontsize=11)
        self.plt.pause(1e-9)


def tgrange(*args, **kwargs):
    """Shortcut for `tqdm.gui.tqdm(range(*args), **kwargs)`."""
    return tqdm_gui(range(*args), **kwargs)


# Aliases
tqdm = tqdm_gui
trange = tgrange

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\logfire_logger.py ===
#### What this does ####
#    On success + failure, log events to Logfire

import os
import traceback
import uuid
from enum import Enum
from typing import Any, Dict, NamedTuple

from typing_extensions import LiteralString

from litellm._logging import print_verbose, verbose_logger
from litellm.litellm_core_utils.redact_messages import redact_user_api_key_info


class SpanConfig(NamedTuple):
    message_template: LiteralString
    span_data: Dict[str, Any]


class LogfireLevel(str, Enum):
    INFO = "info"
    ERROR = "error"


class LogfireLogger:
    # Class variables or attributes
    def __init__(self):
        try:
            verbose_logger.debug("in init logfire logger")
            import logfire

            # only setting up logfire if we are sending to logfire
            # in testing, we don't want to send to logfire
            if logfire.DEFAULT_LOGFIRE_INSTANCE.config.send_to_logfire:
                logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
        except Exception as e:
            print_verbose(f"Got exception on init logfire client {str(e)}")
            raise e

    def _get_span_config(self, payload) -> SpanConfig:
        if (
            payload["call_type"] == "completion"
            or payload["call_type"] == "acompletion"
        ):
            return SpanConfig(
                message_template="Chat Completion with {request_data[model]!r}",
                span_data={"request_data": payload},
            )
        elif (
            payload["call_type"] == "embedding" or payload["call_type"] == "aembedding"
        ):
            return SpanConfig(
                message_template="Embedding Creation with {request_data[model]!r}",
                span_data={"request_data": payload},
            )
        elif (
            payload["call_type"] == "image_generation"
            or payload["call_type"] == "aimage_generation"
        ):
            return SpanConfig(
                message_template="Image Generation with {request_data[model]!r}",
                span_data={"request_data": payload},
            )
        else:
            return SpanConfig(
                message_template="Litellm Call with {request_data[model]!r}",
                span_data={"request_data": payload},
            )

    async def _async_log_event(
        self,
        kwargs,
        response_obj,
        start_time,
        end_time,
        print_verbose,
        level: LogfireLevel,
    ):
        self.log_event(
            kwargs=kwargs,
            response_obj=response_obj,
            start_time=start_time,
            end_time=end_time,
            print_verbose=print_verbose,
            level=level,
        )

    def log_event(
        self,
        kwargs,
        start_time,
        end_time,
        print_verbose,
        level: LogfireLevel,
        response_obj,
    ):
        try:
            import logfire

            verbose_logger.debug(
                f"logfire Logging - Enters logging function for model {kwargs}"
            )

            if not response_obj:
                response_obj = {}
            litellm_params = kwargs.get("litellm_params", {})
            metadata = (
                litellm_params.get("metadata", {}) or {}
            )  # if litellm_params['metadata'] == None
            messages = kwargs.get("messages")
            optional_params = kwargs.get("optional_params", {})
            call_type = kwargs.get("call_type", "completion")
            cache_hit = kwargs.get("cache_hit", False)
            usage = response_obj.get("usage", {})
            id = response_obj.get("id", str(uuid.uuid4()))
            try:
                response_time = (end_time - start_time).total_seconds()
            except Exception:
                response_time = None

            # Clean Metadata before logging - never log raw metadata
            # the raw metadata can contain circular references which leads to infinite recursion
            # we clean out all extra litellm metadata params before logging
            clean_metadata = {}
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    # clean litellm metadata before logging
                    if key in [
                        "endpoint",
                        "caching_groups",
                        "previous_models",
                    ]:
                        continue
                    else:
                        clean_metadata[key] = value

            clean_metadata = redact_user_api_key_info(metadata=clean_metadata)

            # Build the initial payload
            payload = {
                "id": id,
                "call_type": call_type,
                "cache_hit": cache_hit,
                "startTime": start_time,
                "endTime": end_time,
                "responseTime (seconds)": response_time,
                "model": kwargs.get("model", ""),
                "user": kwargs.get("user", ""),
                "modelParameters": optional_params,
                "spend": kwargs.get("response_cost", 0),
                "messages": messages,
                "response": response_obj,
                "usage": usage,
                "metadata": clean_metadata,
            }
            logfire_openai = logfire.with_settings(custom_scope_suffix="openai")
            message_template, span_data = self._get_span_config(payload)
            if level == LogfireLevel.INFO:
                logfire_openai.info(
                    message_template,
                    **span_data,
                )
            elif level == LogfireLevel.ERROR:
                logfire_openai.error(
                    message_template,
                    **span_data,
                    _exc_info=True,
                )
            print_verbose(f"\ndd Logger - Logging payload = {payload}")

            print_verbose(
                f"Logfire Layer Logging - final response object: {response_obj}"
            )
        except Exception as e:
            verbose_logger.debug(
                f"Logfire Layer Error - {str(e)}\n{traceback.format_exc()}"
            )
            pass

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\lunary.py ===
#### What this does ####
#    On success + failure, log events to lunary.ai
import importlib
import traceback
from datetime import datetime, timezone

import packaging


# convert to {completion: xx, tokens: xx}
def parse_usage(usage):
    return {
        "completion": usage["completion_tokens"] if "completion_tokens" in usage else 0,
        "prompt": usage["prompt_tokens"] if "prompt_tokens" in usage else 0,
    }


def parse_tool_calls(tool_calls):
    if tool_calls is None:
        return None

    def clean_tool_call(tool_call):
        serialized = {
            "type": tool_call.type,
            "id": tool_call.id,
            "function": {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments,
            },
        }

        return serialized

    return [clean_tool_call(tool_call) for tool_call in tool_calls]


def parse_messages(input):
    if input is None:
        return None

    def clean_message(message):
        # if is string, return as is
        if isinstance(message, str):
            return message

        if "message" in message:
            return clean_message(message["message"])

        serialized = {
            "role": message.get("role"),
            "content": message.get("content"),
        }

        # Only add tool_calls and function_call to res if they are set
        if message.get("tool_calls"):
            serialized["tool_calls"] = parse_tool_calls(message.get("tool_calls"))

        return serialized

    if isinstance(input, list):
        if len(input) == 1:
            return clean_message(input[0])
        else:
            return [clean_message(msg) for msg in input]
    else:
        return clean_message(input)


class LunaryLogger:
    # Class variables or attributes
    def __init__(self):
        try:
            import lunary

            version = importlib.metadata.version("lunary")  # type: ignore
            # if version < 0.1.43 then raise ImportError
            if packaging.version.Version(version) < packaging.version.Version("0.1.43"):  # type: ignore
                print(  # noqa
                    "Lunary version outdated. Required: >= 0.1.43. Upgrade via 'pip install lunary --upgrade'"
                )
                raise ImportError

            self.lunary_client = lunary
        except ImportError:
            print(  # noqa
                "Lunary not installed. Please install it using 'pip install lunary'"
            )  # noqa
            raise ImportError

    def log_event(
        self,
        kwargs,
        type,
        event,
        run_id,
        model,
        print_verbose,
        extra={},
        input=None,
        user_id=None,
        response_obj=None,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        error=None,
    ):
        try:
            print_verbose(f"Lunary Logging - Logging request for model {model}")

            template_id = None
            litellm_params = kwargs.get("litellm_params", {})
            optional_params = kwargs.get("optional_params", {})
            metadata = litellm_params.get("metadata", {}) or {}

            if optional_params:
                extra = {**extra, **optional_params}

            tags = metadata.get("tags", None)

            if extra:
                extra.pop("extra_body", None)
                extra.pop("user", None)
                template_id = extra.pop("extra_headers", {}).get("Template-Id", None)

            # keep only serializable types
            for param, value in extra.items():
                if not isinstance(value, (str, int, bool, float)) and param != "tools":
                    try:
                        extra[param] = str(value)
                    except Exception:
                        pass

            if response_obj:
                usage = (
                    parse_usage(response_obj["usage"])
                    if "usage" in response_obj
                    else None
                )

                output = response_obj["choices"] if "choices" in response_obj else None

            else:
                usage = None
                output = None

            if error:
                error_obj = {"stack": error}
            else:
                error_obj = None

            self.lunary_client.track_event(  # type: ignore
                type,
                "start",
                run_id,
                parent_run_id=metadata.get("parent_run_id", None),
                user_id=user_id,
                name=model,
                input=parse_messages(input),
                timestamp=start_time.astimezone(timezone.utc).isoformat(),
                template_id=template_id,
                metadata=metadata,
                runtime="litellm",
                tags=tags,
                params=extra,
            )

            self.lunary_client.track_event(  # type: ignore
                type,
                event,
                run_id,
                timestamp=end_time.astimezone(timezone.utc).isoformat(),
                runtime="litellm",
                error=error_obj,
                output=parse_messages(output),
                token_usage=usage,
            )

        except Exception:
            print_verbose(f"Lunary Logging Error - {traceback.format_exc()}")
            pass

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\redact_messages.py ===
# +-----------------------------------------------+
# |                                               |
# |           Give Feedback / Get Help            |
# | https://github.com/BerriAI/litellm/issues/new |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import copy
from typing import TYPE_CHECKING, Any, Optional

import litellm
from litellm.integrations.custom_logger import CustomLogger
from litellm.secret_managers.main import str_to_bool
from litellm.types.utils import StandardCallbackDynamicParams

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import (
        Logging as _LiteLLMLoggingObject,
    )

    LiteLLMLoggingObject = _LiteLLMLoggingObject
else:
    LiteLLMLoggingObject = Any


def redact_message_input_output_from_custom_logger(
    litellm_logging_obj: LiteLLMLoggingObject, result, custom_logger: CustomLogger
):
    if (
        hasattr(custom_logger, "message_logging")
        and custom_logger.message_logging is not True
    ):
        return perform_redaction(litellm_logging_obj.model_call_details, result)
    return result


def perform_redaction(model_call_details: dict, result):
    """
    Performs the actual redaction on the logging object and result.
    """
    # Redact model_call_details
    model_call_details["messages"] = [
        {"role": "user", "content": "redacted-by-litellm"}
    ]
    model_call_details["prompt"] = ""
    model_call_details["input"] = ""

    # Redact streaming response
    if (
        model_call_details.get("stream", False) is True
        and "complete_streaming_response" in model_call_details
    ):
        _streaming_response = model_call_details["complete_streaming_response"]
        for choice in _streaming_response.choices:
            if isinstance(choice, litellm.Choices):
                choice.message.content = "redacted-by-litellm"
            elif isinstance(choice, litellm.utils.StreamingChoices):
                choice.delta.content = "redacted-by-litellm"

    # Redact result
    if result is not None and isinstance(result, litellm.ModelResponse):
        _result = copy.deepcopy(result)
        if hasattr(_result, "choices") and _result.choices is not None:
            for choice in _result.choices:
                if isinstance(choice, litellm.Choices):
                    choice.message.content = "redacted-by-litellm"
                elif isinstance(choice, litellm.utils.StreamingChoices):
                    choice.delta.content = "redacted-by-litellm"
        return _result
    else:
        return {"text": "redacted-by-litellm"}


def should_redact_message_logging(model_call_details: dict) -> bool:
    """
    Determine if message logging should be redacted.
    """
    _request_headers = (
        model_call_details.get("litellm_params", {}).get("metadata", {}) or {}
    )

    request_headers = _request_headers.get("headers", {})

    possible_request_headers = [
        "litellm-enable-message-redaction",  # old header. maintain backwards compatibility
        "x-litellm-enable-message-redaction",  # new header
    ]

    is_redaction_enabled_via_header = False
    for header in possible_request_headers:
        if bool(request_headers.get(header, False)):
            is_redaction_enabled_via_header = True
            break

    # check if user opted out of logging message/response to callbacks
    if (
        litellm.turn_off_message_logging is not True
        and is_redaction_enabled_via_header is not True
        and _get_turn_off_message_logging_from_dynamic_params(model_call_details)
        is not True
    ):
        return False

    if request_headers and bool(
        request_headers.get("litellm-disable-message-redaction", False)
    ):
        return False

    # user has OPTED OUT of message redaction
    if _get_turn_off_message_logging_from_dynamic_params(model_call_details) is False:
        return False

    return True


def redact_message_input_output_from_logging(
    model_call_details: dict, result, input: Optional[Any] = None
) -> Any:
    """
    Removes messages, prompts, input, response from logging. This modifies the data in-place
    only redacts when litellm.turn_off_message_logging == True
    """
    if should_redact_message_logging(model_call_details):
        return perform_redaction(model_call_details, result)
    return result


def _get_turn_off_message_logging_from_dynamic_params(
    model_call_details: dict,
) -> Optional[bool]:
    """
    gets the value of `turn_off_message_logging` from the dynamic params, if it exists.

    handles boolean and string values of `turn_off_message_logging`
    """
    standard_callback_dynamic_params: Optional[
        StandardCallbackDynamicParams
    ] = model_call_details.get("standard_callback_dynamic_params", None)
    if standard_callback_dynamic_params:
        _turn_off_message_logging = standard_callback_dynamic_params.get(
            "turn_off_message_logging"
        )
        if isinstance(_turn_off_message_logging, bool):
            return _turn_off_message_logging
        elif isinstance(_turn_off_message_logging, str):
            return str_to_bool(_turn_off_message_logging)
    return None


def redact_user_api_key_info(metadata: dict) -> dict:
    """
    removes any user_api_key_info before passing to logging object, if flag set

    Usage:

    SDK
    ```python
    litellm.redact_user_api_key_info = True
    ```

    PROXY:
    ```yaml
    litellm_settings:
        redact_user_api_key_info: true
    ```
    """
    if litellm.redact_user_api_key_info is not True:
        return metadata

    new_metadata = {}
    for k, v in metadata.items():
        if isinstance(k, str) and k.startswith("user_api_key"):
            pass
        else:
            new_metadata[k] = v

    return new_metadata

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_helpers\team_member_permission_checks.py ===
from typing import List, Optional

from litellm.caching import DualCache
from litellm.proxy._types import (
    KeyManagementRoutes,
    LiteLLM_TeamTableCachedObj,
    LiteLLM_VerificationToken,
    LiteLLMRoutes,
    LitellmUserRoles,
    Member,
    ProxyErrorTypes,
    ProxyException,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.auth_checks import get_team_object
from litellm.proxy.auth.route_checks import RouteChecks
from litellm.proxy.utils import PrismaClient

DEFAULT_TEAM_MEMBER_PERMISSIONS = [
    KeyManagementRoutes.KEY_INFO,
    KeyManagementRoutes.KEY_HEALTH,
]


class TeamMemberPermissionChecks:
    @staticmethod
    def get_permissions_for_team_member(
        team_member_object: Member,
        team_table: LiteLLM_TeamTableCachedObj,
    ) -> List[KeyManagementRoutes]:
        """
        Returns the permissions for a team member
        """
        if team_table.team_member_permissions and isinstance(
            team_table.team_member_permissions, list
        ):
            return [
                KeyManagementRoutes(permission)
                for permission in team_table.team_member_permissions
            ]

        return DEFAULT_TEAM_MEMBER_PERMISSIONS

    @staticmethod
    def _get_list_of_route_enum_as_str(
        route_enum: List[KeyManagementRoutes],
    ) -> List[str]:
        """
        Returns a list of the route enum as a list of strings
        """
        return [route.value for route in route_enum]

    @staticmethod
    async def can_team_member_execute_key_management_endpoint(
        user_api_key_dict: UserAPIKeyAuth,
        route: KeyManagementRoutes,
        prisma_client: PrismaClient,
        user_api_key_cache: DualCache,
        existing_key_row: LiteLLM_VerificationToken,
    ):
        """
        Main handler for checking if a team member can update a key
        """
        from litellm.proxy.management_endpoints.key_management_endpoints import (
            _get_user_in_team,
        )

        # 1. Don't execute these checks if the user role is proxy admin
        if user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value:
            return

        # 2. Check if the operation is being done on a team key
        if existing_key_row.team_id is None:
            return

        # 3. Get Team Object from DB
        team_table = await get_team_object(
            team_id=existing_key_row.team_id,
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
            parent_otel_span=user_api_key_dict.parent_otel_span,
            check_db_only=True,
        )

        # 4. Extract `Member` object from `team_table`
        key_assigned_user_in_team = _get_user_in_team(
            team_table=team_table, user_id=user_api_key_dict.user_id
        )

        # 5. Check if the team member has permissions for the endpoint
        TeamMemberPermissionChecks.does_team_member_have_permissions_for_endpoint(
            team_member_object=key_assigned_user_in_team,
            team_table=team_table,
            route=route,
        )

    @staticmethod
    def does_team_member_have_permissions_for_endpoint(
        team_member_object: Optional[Member],
        team_table: LiteLLM_TeamTableCachedObj,
        route: str,
    ) -> Optional[bool]:
        """
        Raises an exception if the team member does not have permissions for calling the endpoint for a team
        """

        # permission checks only run for non-admin users
        # Non-Admin user trying to access information about a team's key
        if team_member_object is None:
            return False
        if team_member_object.role == "admin":
            return True

        _team_member_permissions = (
            TeamMemberPermissionChecks.get_permissions_for_team_member(
                team_member_object=team_member_object,
                team_table=team_table,
            )
        )
        team_member_permissions = (
            TeamMemberPermissionChecks._get_list_of_route_enum_as_str(
                _team_member_permissions
            )
        )

        if not RouteChecks.check_route_access(
            route=route, allowed_routes=team_member_permissions
        ):
            raise ProxyException(
                message=f"Team member does not have permissions for endpoint: {route}. You only have access to the following endpoints: {team_member_permissions} for team {team_table.team_id}",
                type=ProxyErrorTypes.team_member_permission_error,
                param=route,
                code=401,
            )

        return True

    @staticmethod
    async def user_belongs_to_keys_team(
        user_api_key_dict: UserAPIKeyAuth,
        existing_key_row: LiteLLM_VerificationToken,
    ) -> bool:
        """
        Returns True if the user belongs to the team that the key is assigned to
        """
        from litellm.proxy.management_endpoints.key_management_endpoints import (
            _get_user_in_team,
        )
        from litellm.proxy.proxy_server import prisma_client, user_api_key_cache

        if existing_key_row.team_id is None:
            return False
        team_table = await get_team_object(
            team_id=existing_key_row.team_id,
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
            parent_otel_span=user_api_key_dict.parent_otel_span,
            check_db_only=True,
        )

        # 4. Extract `Member` object from `team_table`
        team_member_object = _get_user_in_team(
            team_table=team_table, user_id=user_api_key_dict.user_id
        )
        return team_member_object is not None

    @staticmethod
    def get_all_available_team_member_permissions() -> List[str]:
        """
        Returns all available team member permissions
        """
        all_available_permissions = []
        for route in LiteLLMRoutes.key_management_routes.value:
            all_available_permissions.append(route.value)
        return all_available_permissions

    @staticmethod
    def default_team_member_permissions() -> List[str]:
        return [route.value for route in DEFAULT_TEAM_MEMBER_PERMISSIONS]

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\nist.py ===
# Natural Language Toolkit: Python port of the mteval-v14.pl tokenizer.
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Liling Tan (ported from ftp://jaguar.ncsl.nist.gov/mt/resources/mteval-v14.pl)
# Contributors: Ozan Caglayan, Wiktor Stribizew
#
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

"""
This is a NLTK port of the tokenizer used in the NIST BLEU evaluation script,
https://github.com/moses-smt/mosesdecoder/blob/master/scripts/generic/mteval-v14.pl#L926
which was also ported into Python in
https://github.com/lium-lst/nmtpy/blob/master/nmtpy/metrics/mtevalbleu.py#L162
"""


import io
import re

from nltk.corpus import perluniprops
from nltk.tokenize.api import TokenizerI
from nltk.tokenize.util import xml_unescape


class NISTTokenizer(TokenizerI):
    """
    This NIST tokenizer is sentence-based instead of the original
    paragraph-based tokenization from mteval-14.pl; The sentence-based
    tokenization is consistent with the other tokenizers available in NLTK.

    >>> from nltk.tokenize.nist import NISTTokenizer
    >>> nist = NISTTokenizer()
    >>> s = "Good muffins cost $3.88 in New York."
    >>> expected_lower = [u'good', u'muffins', u'cost', u'$', u'3.88', u'in', u'new', u'york', u'.']
    >>> expected_cased = [u'Good', u'muffins', u'cost', u'$', u'3.88', u'in', u'New', u'York', u'.']
    >>> nist.tokenize(s, lowercase=False) == expected_cased
    True
    >>> nist.tokenize(s, lowercase=True) == expected_lower  # Lowercased.
    True

    The international_tokenize() is the preferred function when tokenizing
    non-european text, e.g.

    >>> from nltk.tokenize.nist import NISTTokenizer
    >>> nist = NISTTokenizer()

    # Input strings.
    >>> albb = u'Alibaba Group Holding Limited (Chinese: 阿里巴巴集团控股 有限公司) is a Chinese e-commerce company...'
    >>> amz = u'Amazon.com, Inc. (/ˈæməzɒn/) is an American electronic commerce...'
    >>> rkt = u'Rakuten, Inc. (楽天株式会社 Rakuten Kabushiki-gaisha) is a Japanese electronic commerce and Internet company based in Tokyo.'

    # Expected tokens.
    >>> expected_albb = [u'Alibaba', u'Group', u'Holding', u'Limited', u'(', u'Chinese', u':', u'\u963f\u91cc\u5df4\u5df4\u96c6\u56e2\u63a7\u80a1', u'\u6709\u9650\u516c\u53f8', u')']
    >>> expected_amz = [u'Amazon', u'.', u'com', u',', u'Inc', u'.', u'(', u'/', u'\u02c8\xe6', u'm']
    >>> expected_rkt = [u'Rakuten', u',', u'Inc', u'.', u'(', u'\u697d\u5929\u682a\u5f0f\u4f1a\u793e', u'Rakuten', u'Kabushiki', u'-', u'gaisha']

    >>> nist.international_tokenize(albb)[:10] == expected_albb
    True
    >>> nist.international_tokenize(amz)[:10] == expected_amz
    True
    >>> nist.international_tokenize(rkt)[:10] == expected_rkt
    True

    # Doctest for patching issue #1926
    >>> sent = u'this is a foo\u2604sentence.'
    >>> expected_sent = [u'this', u'is', u'a', u'foo', u'\u2604', u'sentence', u'.']
    >>> nist.international_tokenize(sent) == expected_sent
    True
    """

    # Strip "skipped" tags
    STRIP_SKIP = re.compile("<skipped>"), ""
    #  Strip end-of-line hyphenation and join lines
    STRIP_EOL_HYPHEN = re.compile("\u2028"), " "
    # Tokenize punctuation.
    PUNCT = re.compile(r"([\{-\~\[-\` -\&\(-\+\:-\@\/])"), " \\1 "
    # Tokenize period and comma unless preceded by a digit.
    PERIOD_COMMA_PRECEED = re.compile(r"([^0-9])([\.,])"), "\\1 \\2 "
    # Tokenize period and comma unless followed by a digit.
    PERIOD_COMMA_FOLLOW = re.compile(r"([\.,])([^0-9])"), " \\1 \\2"
    # Tokenize dash when preceded by a digit
    DASH_PRECEED_DIGIT = re.compile("([0-9])(-)"), "\\1 \\2 "

    LANG_DEPENDENT_REGEXES = [
        PUNCT,
        PERIOD_COMMA_PRECEED,
        PERIOD_COMMA_FOLLOW,
        DASH_PRECEED_DIGIT,
    ]

    # Perluniprops characters used in NIST tokenizer.
    pup_number = str("".join(set(perluniprops.chars("Number"))))  # i.e. \p{N}
    pup_punct = str("".join(set(perluniprops.chars("Punctuation"))))  # i.e. \p{P}
    pup_symbol = str("".join(set(perluniprops.chars("Symbol"))))  # i.e. \p{S}

    # Python regexes needs to escape some special symbols, see
    # see https://stackoverflow.com/q/45670950/610569
    number_regex = re.sub(r"[]^\\-]", r"\\\g<0>", pup_number)
    punct_regex = re.sub(r"[]^\\-]", r"\\\g<0>", pup_punct)
    symbol_regex = re.sub(r"[]^\\-]", r"\\\g<0>", pup_symbol)

    # Note: In the original perl implementation, \p{Z} and \p{Zl} were used to
    #       (i) strip trailing and heading spaces  and
    #       (ii) de-deuplicate spaces.
    #       In Python, this would do: ' '.join(str.strip().split())
    # Thus, the next two lines were commented out.
    # Line_Separator = str(''.join(perluniprops.chars('Line_Separator'))) # i.e. \p{Zl}
    # Separator = str(''.join(perluniprops.chars('Separator'))) # i.e. \p{Z}

    # Pads non-ascii strings with space.
    NONASCII = re.compile("([\x00-\x7f]+)"), r" \1 "
    #  Tokenize any punctuation unless followed AND preceded by a digit.
    PUNCT_1 = (
        re.compile(f"([{number_regex}])([{punct_regex}])"),
        "\\1 \\2 ",
    )
    PUNCT_2 = (
        re.compile(f"([{punct_regex}])([{number_regex}])"),
        " \\1 \\2",
    )
    # Tokenize symbols
    SYMBOLS = re.compile(f"([{symbol_regex}])"), " \\1 "

    INTERNATIONAL_REGEXES = [NONASCII, PUNCT_1, PUNCT_2, SYMBOLS]

    def lang_independent_sub(self, text):
        """Performs the language independent string substituitions."""
        # It's a strange order of regexes.
        # It'll be better to unescape after STRIP_EOL_HYPHEN
        # but let's keep it close to the original NIST implementation.
        regexp, substitution = self.STRIP_SKIP
        text = regexp.sub(substitution, text)
        text = xml_unescape(text)
        regexp, substitution = self.STRIP_EOL_HYPHEN
        text = regexp.sub(substitution, text)
        return text

    def tokenize(self, text, lowercase=False, western_lang=True, return_str=False):
        text = str(text)
        # Language independent regex.
        text = self.lang_independent_sub(text)
        # Language dependent regex.
        if western_lang:
            # Pad string with whitespace.
            text = " " + text + " "
            if lowercase:
                text = text.lower()
            for regexp, substitution in self.LANG_DEPENDENT_REGEXES:
                text = regexp.sub(substitution, text)
        # Remove contiguous whitespaces.
        text = " ".join(text.split())
        # Finally, strips heading and trailing spaces
        # and converts output string into unicode.
        text = str(text.strip())
        return text if return_str else text.split()

    def international_tokenize(
        self, text, lowercase=False, split_non_ascii=True, return_str=False
    ):
        text = str(text)
        # Different from the 'normal' tokenize(), STRIP_EOL_HYPHEN is applied
        # first before unescaping.
        regexp, substitution = self.STRIP_SKIP
        text = regexp.sub(substitution, text)
        regexp, substitution = self.STRIP_EOL_HYPHEN
        text = regexp.sub(substitution, text)
        text = xml_unescape(text)

        if lowercase:
            text = text.lower()

        for regexp, substitution in self.INTERNATIONAL_REGEXES:
            text = regexp.sub(substitution, text)

        # Make sure that there's only one space only between words.
        # Strip leading and trailing spaces.
        text = " ".join(text.strip().split())
        return text if return_str else text.split()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\requests\__init__.py ===
#   __
#  /__)  _  _     _   _ _/   _
# / (   (- (/ (/ (- _)  /  _)
#          /

"""
Requests HTTP Library
~~~~~~~~~~~~~~~~~~~~~

Requests is an HTTP library, written in Python, for human beings.
Basic GET usage:

   >>> import requests
   >>> r = requests.get('https://www.python.org')
   >>> r.status_code
   200
   >>> b'Python is a programming language' in r.content
   True

... or POST:

   >>> payload = dict(key1='value1', key2='value2')
   >>> r = requests.post('https://httpbin.org/post', data=payload)
   >>> print(r.text)
   {
     ...
     "form": {
       "key1": "value1",
       "key2": "value2"
     },
     ...
   }

The other HTTP methods are supported - see `requests.api`. Full documentation
is at <https://requests.readthedocs.io>.

:copyright: (c) 2017 by Kenneth Reitz.
:license: Apache 2.0, see LICENSE for more details.
"""

import warnings

from pip._vendor import urllib3

from .exceptions import RequestsDependencyWarning

charset_normalizer_version = None
chardet_version = None


def check_compatibility(urllib3_version, chardet_version, charset_normalizer_version):
    urllib3_version = urllib3_version.split(".")
    assert urllib3_version != ["dev"]  # Verify urllib3 isn't installed from git.

    # Sometimes, urllib3 only reports its version as 16.1.
    if len(urllib3_version) == 2:
        urllib3_version.append("0")

    # Check urllib3 for compatibility.
    major, minor, patch = urllib3_version  # noqa: F811
    major, minor, patch = int(major), int(minor), int(patch)
    # urllib3 >= 1.21.1
    assert major >= 1
    if major == 1:
        assert minor >= 21

    # Check charset_normalizer for compatibility.
    if chardet_version:
        major, minor, patch = chardet_version.split(".")[:3]
        major, minor, patch = int(major), int(minor), int(patch)
        # chardet_version >= 3.0.2, < 6.0.0
        assert (3, 0, 2) <= (major, minor, patch) < (6, 0, 0)
    elif charset_normalizer_version:
        major, minor, patch = charset_normalizer_version.split(".")[:3]
        major, minor, patch = int(major), int(minor), int(patch)
        # charset_normalizer >= 2.0.0 < 4.0.0
        assert (2, 0, 0) <= (major, minor, patch) < (4, 0, 0)
    else:
        # pip does not need or use character detection
        pass


def _check_cryptography(cryptography_version):
    # cryptography < 1.3.4
    try:
        cryptography_version = list(map(int, cryptography_version.split(".")))
    except ValueError:
        return

    if cryptography_version < [1, 3, 4]:
        warning = "Old version of cryptography ({}) may cause slowdown.".format(
            cryptography_version
        )
        warnings.warn(warning, RequestsDependencyWarning)


# Check imported dependencies for compatibility.
try:
    check_compatibility(
        urllib3.__version__, chardet_version, charset_normalizer_version
    )
except (AssertionError, ValueError):
    warnings.warn(
        "urllib3 ({}) or chardet ({})/charset_normalizer ({}) doesn't match a supported "
        "version!".format(
            urllib3.__version__, chardet_version, charset_normalizer_version
        ),
        RequestsDependencyWarning,
    )

# Attempt to enable urllib3's fallback for SNI support
# if the standard library doesn't support SNI or the
# 'ssl' library isn't available.
try:
    # Note: This logic prevents upgrading cryptography on Windows, if imported
    #       as part of pip.
    from pip._internal.utils.compat import WINDOWS
    if not WINDOWS:
        raise ImportError("pip internals: don't import cryptography on Windows")
    try:
        import ssl
    except ImportError:
        ssl = None

    if not getattr(ssl, "HAS_SNI", False):
        from pip._vendor.urllib3.contrib import pyopenssl

        pyopenssl.inject_into_urllib3()

        # Check cryptography version
        from cryptography import __version__ as cryptography_version

        _check_cryptography(cryptography_version)
except ImportError:
    pass

# urllib3's DependencyWarnings should be silenced.
from pip._vendor.urllib3.exceptions import DependencyWarning

warnings.simplefilter("ignore", DependencyWarning)

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

from . import packages, utils
from .__version__ import (
    __author__,
    __author_email__,
    __build__,
    __cake__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
)
from .api import delete, get, head, options, patch, post, put, request
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    FileModeWarning,
    HTTPError,
    JSONDecodeError,
    ReadTimeout,
    RequestException,
    Timeout,
    TooManyRedirects,
    URLRequired,
)
from .models import PreparedRequest, Request, Response
from .sessions import Session, session
from .status_codes import codes

logging.getLogger(__name__).addHandler(NullHandler())

# FileModeWarnings go off per the default.
warnings.simplefilter("default", FileModeWarning, append=True)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\formatted_text\base.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Tuple, Union, cast

from prompt_toolkit.mouse_events import MouseEvent

if TYPE_CHECKING:
    from typing_extensions import Protocol

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone

__all__ = [
    "OneStyleAndTextTuple",
    "StyleAndTextTuples",
    "MagicFormattedText",
    "AnyFormattedText",
    "to_formatted_text",
    "is_formatted_text",
    "Template",
    "merge_formatted_text",
    "FormattedText",
]

OneStyleAndTextTuple = Union[
    Tuple[str, str], Tuple[str, str, Callable[[MouseEvent], "NotImplementedOrNone"]]
]

# List of (style, text) tuples.
StyleAndTextTuples = List[OneStyleAndTextTuple]


if TYPE_CHECKING:
    from typing_extensions import TypeGuard

    class MagicFormattedText(Protocol):
        """
        Any object that implements ``__pt_formatted_text__`` represents formatted
        text.
        """

        def __pt_formatted_text__(self) -> StyleAndTextTuples: ...


AnyFormattedText = Union[
    str,
    "MagicFormattedText",
    StyleAndTextTuples,
    # Callable[[], 'AnyFormattedText']  # Recursive definition not supported by mypy.
    Callable[[], Any],
    None,
]


def to_formatted_text(
    value: AnyFormattedText, style: str = "", auto_convert: bool = False
) -> FormattedText:
    """
    Convert the given value (which can be formatted text) into a list of text
    fragments. (Which is the canonical form of formatted text.) The outcome is
    always a `FormattedText` instance, which is a list of (style, text) tuples.

    It can take a plain text string, an `HTML` or `ANSI` object, anything that
    implements `__pt_formatted_text__` or a callable that takes no arguments and
    returns one of those.

    :param style: An additional style string which is applied to all text
        fragments.
    :param auto_convert: If `True`, also accept other types, and convert them
        to a string first.
    """
    result: FormattedText | StyleAndTextTuples

    if value is None:
        result = []
    elif isinstance(value, str):
        result = [("", value)]
    elif isinstance(value, list):
        result = value  # StyleAndTextTuples
    elif hasattr(value, "__pt_formatted_text__"):
        result = cast("MagicFormattedText", value).__pt_formatted_text__()
    elif callable(value):
        return to_formatted_text(value(), style=style)
    elif auto_convert:
        result = [("", f"{value}")]
    else:
        raise ValueError(
            "No formatted text. Expecting a unicode object, "
            f"HTML, ANSI or a FormattedText instance. Got {value!r}"
        )

    # Apply extra style.
    if style:
        result = cast(
            StyleAndTextTuples,
            [(style + " " + item_style, *rest) for item_style, *rest in result],
        )

    # Make sure the result is wrapped in a `FormattedText`. Among other
    # reasons, this is important for `print_formatted_text` to work correctly
    # and distinguish between lists and formatted text.
    if isinstance(result, FormattedText):
        return result
    else:
        return FormattedText(result)


def is_formatted_text(value: object) -> TypeGuard[AnyFormattedText]:
    """
    Check whether the input is valid formatted text (for use in assert
    statements).
    In case of a callable, it doesn't check the return type.
    """
    if callable(value):
        return True
    if isinstance(value, (str, list)):
        return True
    if hasattr(value, "__pt_formatted_text__"):
        return True
    return False


class FormattedText(StyleAndTextTuples):
    """
    A list of ``(style, text)`` tuples.

    (In some situations, this can also be ``(style, text, mouse_handler)``
    tuples.)
    """

    def __pt_formatted_text__(self) -> StyleAndTextTuples:
        return self

    def __repr__(self) -> str:
        return f"FormattedText({super().__repr__()})"


class Template:
    """
    Template for string interpolation with formatted text.

    Example::

        Template(' ... {} ... ').format(HTML(...))

    :param text: Plain text.
    """

    def __init__(self, text: str) -> None:
        assert "{0}" not in text
        self.text = text

    def format(self, *values: AnyFormattedText) -> AnyFormattedText:
        def get_result() -> AnyFormattedText:
            # Split the template in parts.
            parts = self.text.split("{}")
            assert len(parts) - 1 == len(values)

            result = FormattedText()
            for part, val in zip(parts, values):
                result.append(("", part))
                result.extend(to_formatted_text(val))
            result.append(("", parts[-1]))
            return result

        return get_result


def merge_formatted_text(items: Iterable[AnyFormattedText]) -> AnyFormattedText:
    """
    Merge (Concatenate) several pieces of formatted text together.
    """

    def _merge_formatted_text() -> AnyFormattedText:
        result = FormattedText()
        for i in items:
            result.extend(to_formatted_text(i))
        return result

    return _merge_formatted_text

# === NexusCore/openenv\Lib\site-packages\trio\_tests\tools\test_gen_exports.py ===
import ast
import sys
from pathlib import Path

import pytest

from trio._tests.pytest_plugin import skip_if_optional_else_raise

# imports in gen_exports that are not in `install_requires` in setup.py
try:
    import astor  # noqa: F401
    import isort  # noqa: F401
except ImportError as error:
    skip_if_optional_else_raise(error)


from trio._tools.gen_exports import (
    File,
    create_passthrough_args,
    get_public_methods,
    process,
    run_linters,
    run_ruff,
)

from ..._core._tests.tutil import slow

SOURCE = '''from _run import _public
from collections import Counter

class Test:
    @_public
    def public_func(self):
        """With doc string"""

    @ignore_this
    @_public
    @another_decorator
    async def public_async_func(self) -> Counter:
        pass  # no doc string

    def not_public(self):
        pass

    async def not_public_async(self):
        pass
'''

IMPORT_1 = """\
from collections import Counter
"""

IMPORT_2 = """\
from collections import Counter
import os
"""

IMPORT_3 = """\
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections import Counter
"""


def test_get_public_methods() -> None:
    methods = list(get_public_methods(ast.parse(SOURCE)))
    assert {m.name for m in methods} == {"public_func", "public_async_func"}


def test_create_pass_through_args() -> None:
    testcases = [
        ("def f()", "()"),
        ("def f(one)", "(one)"),
        ("def f(one, two)", "(one, two)"),
        ("def f(one, *args)", "(one, *args)"),
        (
            "def f(one, *args, kw1, kw2=None, **kwargs)",
            "(one, *args, kw1=kw1, kw2=kw2, **kwargs)",
        ),
    ]

    for funcdef, expected in testcases:
        func_node = ast.parse(funcdef + ":\n  pass").body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert create_passthrough_args(func_node) == expected


skip_lints = pytest.mark.skipif(
    sys.implementation.name != "cpython",
    reason="gen_exports is internal, black/isort only runs on CPython",
)


@slow
@skip_lints
@pytest.mark.parametrize("imports", [IMPORT_1, IMPORT_2, IMPORT_3])
def test_process(
    tmp_path: Path,
    imports: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    try:
        import black  # noqa: F401
    # there's no dedicated CI run that has astor+isort, but lacks black.
    except ImportError as error:  # pragma: no cover
        skip_if_optional_else_raise(error)

    modpath = tmp_path / "_module.py"
    genpath = tmp_path / "_generated_module.py"
    modpath.write_text(SOURCE, encoding="utf-8")
    file = File(modpath, "runner", platform="linux", imports=imports)
    assert not genpath.exists()
    with pytest.raises(SystemExit) as excinfo:
        process([file], do_test=True)
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Generated sources are outdated. Please regenerate." in captured.out
    with pytest.raises(SystemExit) as excinfo:
        process([file], do_test=False)
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Regenerated sources successfully." in captured.out
    assert genpath.exists()
    process([file], do_test=True)
    # But if we change the lookup path it notices
    with pytest.raises(SystemExit) as excinfo:
        process(
            [File(modpath, "runner.io_manager", platform="linux", imports=imports)],
            do_test=True,
        )
    assert excinfo.value.code == 1
    # Also if the platform is changed.
    with pytest.raises(SystemExit) as excinfo:
        process([File(modpath, "runner", imports=imports)], do_test=True)
    assert excinfo.value.code == 1


@skip_lints
def test_run_ruff(tmp_path: Path) -> None:
    """Test that processing properly fails if ruff does."""
    try:
        import ruff  # noqa: F401
    except ImportError as error:  # pragma: no cover
        skip_if_optional_else_raise(error)

    file = File(tmp_path / "module.py", "module")

    success, _ = run_ruff(file, "class not valid code ><")
    assert not success

    test_function = '''def combine_and(data: list[str]) -> str:
    """Join values of text, and have 'and' with the last one properly."""
    if len(data) >= 2:
        data[-1] = 'and ' + data[-1]
    if len(data) > 2:
        return ', '.join(data)
    return ' '.join(data)'''

    success, response = run_ruff(file, test_function)
    assert success
    assert response == test_function


@skip_lints
def test_lint_failure(tmp_path: Path) -> None:
    """Test that processing properly fails if black or ruff does."""
    try:
        import black  # noqa: F401
        import ruff  # noqa: F401
    except ImportError as error:  # pragma: no cover
        skip_if_optional_else_raise(error)

    file = File(tmp_path / "module.py", "module")

    with pytest.raises(SystemExit):
        run_linters(file, "class not valid code ><")

    with pytest.raises(SystemExit):
        run_linters(file, "import waffle\n;import trio")

# === NexusCore/openenv\Lib\site-packages\win32comext\shell\demos\IFileOperationProgressSink.py ===
# Sample implementation of IFileOperationProgressSink that just prints
# some basic info

import pythoncom
from win32com.server.policy import DesignatedWrapPolicy
from win32com.shell import shell, shellcon

tsf_flags = [(k, v) for k, v in shellcon.__dict__.items() if k.startswith("TSF_")]


def decode_flags(flags):
    if flags == 0:
        return "TSF_NORMAL"
    flag_txt = ""
    for k, v in tsf_flags:
        if flags & v:
            if flag_txt:
                flag_txt += "|" + k
            else:
                flag_txt = k
    return flag_txt


class FileOperationProgressSink(DesignatedWrapPolicy):
    _com_interfaces_ = [shell.IID_IFileOperationProgressSink]
    _public_methods_ = [
        "StartOperations",
        "FinishOperations",
        "PreRenameItem",
        "PostRenameItem",
        "PreMoveItem",
        "PostMoveItem",
        "PreCopyItem",
        "PostCopyItem",
        "PreDeleteItem",
        "PostDeleteItem",
        "PreNewItem",
        "PostNewItem",
        "UpdateProgress",
        "ResetTimer",
        "PauseTimer",
        "ResumeTimer",
    ]

    def __init__(self):
        self._wrap_(self)

    def StartOperations(self):
        print("StartOperations")

    def FinishOperations(self, Result):
        print("FinishOperations: HRESULT ", Result)

    def PreRenameItem(self, Flags, Item, NewName):
        print(
            "PreRenameItem: Renaming "
            + Item.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + " to "
            + NewName
        )

    def PostRenameItem(self, Flags, Item, NewName, hrRename, NewlyCreated):
        if NewlyCreated is not None:
            newfile = NewlyCreated.GetDisplayName(shellcon.SHGDN_FORPARSING)
        else:
            newfile = "not renamed, HRESULT " + str(hrRename)
        print(
            "PostRenameItem: renamed "
            + Item.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + " to "
            + newfile
        )

    def PreMoveItem(self, Flags, Item, DestinationFolder, NewName):
        print(
            "PreMoveItem: Moving "
            + Item.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + " to "
            + DestinationFolder.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + "\\"
            + str(NewName)
        )

    def PostMoveItem(
        self, Flags, Item, DestinationFolder, NewName, hrMove, NewlyCreated
    ):
        if NewlyCreated is not None:
            newfile = NewlyCreated.GetDisplayName(shellcon.SHGDN_FORPARSING)
        else:
            newfile = "not copied, HRESULT " + str(hrMove)
        print(
            "PostMoveItem: Moved "
            + Item.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + " to "
            + newfile
        )

    def PreCopyItem(self, Flags, Item, DestinationFolder, NewName):
        if not NewName:
            NewName = ""
        print(
            "PreCopyItem: Copying "
            + Item.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + " to "
            + DestinationFolder.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + "\\"
            + NewName
        )
        print("Flags: ", decode_flags(Flags))

    def PostCopyItem(
        self, Flags, Item, DestinationFolder, NewName, hrCopy, NewlyCreated
    ):
        if NewlyCreated is not None:
            newfile = NewlyCreated.GetDisplayName(shellcon.SHGDN_FORPARSING)
        else:
            newfile = "not copied, HRESULT " + str(hrCopy)
        print(
            "PostCopyItem: Copied "
            + Item.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + " to "
            + newfile
        )
        print("Flags: ", decode_flags(Flags))

    def PreDeleteItem(self, Flags, Item):
        print(
            "PreDeleteItem: Deleting " + Item.GetDisplayName(shellcon.SHGDN_FORPARSING)
        )

    def PostDeleteItem(self, Flags, Item, hrDelete, NewlyCreated):
        print(
            "PostDeleteItem: Deleted " + Item.GetDisplayName(shellcon.SHGDN_FORPARSING)
        )
        if NewlyCreated:
            print(
                "    Moved to recycle bin - "
                + NewlyCreated.GetDisplayName(shellcon.SHGDN_FORPARSING)
            )

    def PreNewItem(self, Flags, DestinationFolder, NewName):
        print(
            "PreNewItem: Creating "
            + DestinationFolder.GetDisplayName(shellcon.SHGDN_FORPARSING)
            + "\\"
            + NewName
        )

    def PostNewItem(
        self,
        Flags,
        DestinationFolder,
        NewName,
        TemplateName,
        FileAttributes,
        hrNew,
        NewItem,
    ):
        print(
            "PostNewItem: Created " + NewItem.GetDisplayName(shellcon.SHGDN_FORPARSING)
        )

    def UpdateProgress(self, WorkTotal, WorkSoFar):
        print("UpdateProgress: ", WorkSoFar, WorkTotal)

    def ResetTimer(self):
        print("ResetTimer")

    def PauseTimer(self):
        print("PauseTimer")

    def ResumeTimer(self):
        print("ResumeTimer")


def CreateSink():
    return pythoncom.WrapObject(
        FileOperationProgressSink(), shell.IID_IFileOperationProgressSink
    )

# === NexusCore/openenv\Lib\site-packages\PIL\FliImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# FLI/FLC file handling.
#
# History:
#       95-09-01 fl     Created
#       97-01-03 fl     Fixed parser, setup decoder tile
#       98-07-15 fl     Renamed offset attribute to avoid name clash
#
# Copyright (c) Secret Labs AB 1997-98.
# Copyright (c) Fredrik Lundh 1995-97.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import os

from . import Image, ImageFile, ImagePalette
from ._binary import i16le as i16
from ._binary import i32le as i32
from ._binary import o8
from ._util import DeferredError

#
# decoder


def _accept(prefix: bytes) -> bool:
    return (
        len(prefix) >= 6
        and i16(prefix, 4) in [0xAF11, 0xAF12]
        and i16(prefix, 14) in [0, 3]  # flags
    )


##
# Image plugin for the FLI/FLC animation format.  Use the <b>seek</b>
# method to load individual frames.


class FliImageFile(ImageFile.ImageFile):
    format = "FLI"
    format_description = "Autodesk FLI/FLC Animation"
    _close_exclusive_fp_after_loading = False

    def _open(self) -> None:
        # HEAD
        s = self.fp.read(128)
        if not (_accept(s) and s[20:22] == b"\x00\x00"):
            msg = "not an FLI/FLC file"
            raise SyntaxError(msg)

        # frames
        self.n_frames = i16(s, 6)
        self.is_animated = self.n_frames > 1

        # image characteristics
        self._mode = "P"
        self._size = i16(s, 8), i16(s, 10)

        # animation speed
        duration = i32(s, 16)
        magic = i16(s, 4)
        if magic == 0xAF11:
            duration = (duration * 1000) // 70
        self.info["duration"] = duration

        # look for palette
        palette = [(a, a, a) for a in range(256)]

        s = self.fp.read(16)

        self.__offset = 128

        if i16(s, 4) == 0xF100:
            # prefix chunk; ignore it
            self.__offset = self.__offset + i32(s)
            self.fp.seek(self.__offset)
            s = self.fp.read(16)

        if i16(s, 4) == 0xF1FA:
            # look for palette chunk
            number_of_subchunks = i16(s, 6)
            chunk_size: int | None = None
            for _ in range(number_of_subchunks):
                if chunk_size is not None:
                    self.fp.seek(chunk_size - 6, os.SEEK_CUR)
                s = self.fp.read(6)
                chunk_type = i16(s, 4)
                if chunk_type in (4, 11):
                    self._palette(palette, 2 if chunk_type == 11 else 0)
                    break
                chunk_size = i32(s)
                if not chunk_size:
                    break

        self.palette = ImagePalette.raw(
            "RGB", b"".join(o8(r) + o8(g) + o8(b) for (r, g, b) in palette)
        )

        # set things up to decode first frame
        self.__frame = -1
        self._fp = self.fp
        self.__rewind = self.fp.tell()
        self.seek(0)

    def _palette(self, palette: list[tuple[int, int, int]], shift: int) -> None:
        # load palette

        i = 0
        for e in range(i16(self.fp.read(2))):
            s = self.fp.read(2)
            i = i + s[0]
            n = s[1]
            if n == 0:
                n = 256
            s = self.fp.read(n * 3)
            for n in range(0, len(s), 3):
                r = s[n] << shift
                g = s[n + 1] << shift
                b = s[n + 2] << shift
                palette[i] = (r, g, b)
                i += 1

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return
        if frame < self.__frame:
            self._seek(0)

        for f in range(self.__frame + 1, frame + 1):
            self._seek(f)

    def _seek(self, frame: int) -> None:
        if isinstance(self._fp, DeferredError):
            raise self._fp.ex
        if frame == 0:
            self.__frame = -1
            self._fp.seek(self.__rewind)
            self.__offset = 128
        else:
            # ensure that the previous frame was loaded
            self.load()

        if frame != self.__frame + 1:
            msg = f"cannot seek to frame {frame}"
            raise ValueError(msg)
        self.__frame = frame

        # move to next frame
        self.fp = self._fp
        self.fp.seek(self.__offset)

        s = self.fp.read(4)
        if not s:
            msg = "missing frame size"
            raise EOFError(msg)

        framesize = i32(s)

        self.decodermaxblock = framesize
        self.tile = [ImageFile._Tile("fli", (0, 0) + self.size, self.__offset)]

        self.__offset += framesize

    def tell(self) -> int:
        return self.__frame


#
# registry

Image.register_open(FliImageFile.format, FliImageFile, _accept)

Image.register_extensions(FliImageFile.format, [".fli", ".flc"])

# === NexusCore/openenv\Lib\site-packages\pyee\uplift.py ===
# -*- coding: utf-8 -*-

from functools import wraps
from typing import Any, Callable, cast, Dict, Optional, Tuple, Type, TypeVar, Union
import warnings

from typing_extensions import Literal

from pyee.base import EventEmitter

UpliftingEventEmitter = TypeVar("UpliftingEventEmitter", bound=EventEmitter)


EMIT_WRAPPERS: Dict[EventEmitter, Callable[[], None]] = dict()


def unwrap(event_emitter: EventEmitter) -> None:
    """Unwrap an uplifted EventEmitter, returning it to its prior state."""
    if event_emitter in EMIT_WRAPPERS:
        EMIT_WRAPPERS[event_emitter]()


def _wrap(
    left: EventEmitter,
    right: EventEmitter,
    error_handler: Any,
    proxy_new_listener: bool,
) -> None:
    left_emit = left.emit
    left_unwrap: Optional[Callable[[], None]] = EMIT_WRAPPERS.get(left)

    @wraps(left_emit)
    def wrapped_emit(event: str, *args: Any, **kwargs: Any) -> bool:
        left_handled: bool = left._call_handlers(event, args, kwargs)

        # Do it for the right side
        if proxy_new_listener or event != "new_listener":
            right_handled = right._call_handlers(event, args, kwargs)
        else:
            right_handled = False

        handled = left_handled or right_handled

        # Use the error handling on `error_handler` (should either be
        # `left` or `right`)
        if not handled:
            error_handler._emit_handle_potential_error(event, args[0] if args else None)

        return handled

    def _unwrap() -> None:
        warnings.warn(
            DeprecationWarning(
                "Patched ee.unwrap() is deprecated and will be removed in a "
                "future release. Use pyee.uplift.unwrap instead."
            )
        )
        unwrap(left)

    def unwrap_hook() -> None:
        cast(Any, left).emit = left_emit
        if left_unwrap:
            EMIT_WRAPPERS[left] = left_unwrap
        else:
            del EMIT_WRAPPERS[left]
            del left.unwrap  # type: ignore
        cast(Any, left).emit = left_emit

        unwrap(right)

    cast(Any, left).emit = wrapped_emit

    EMIT_WRAPPERS[left] = unwrap_hook
    left.unwrap = _unwrap  # type: ignore


_PROXY_NEW_LISTENER_SETTINGS: Dict[str, Tuple[bool, bool]] = dict(
    forward=(False, True),
    backward=(True, False),
    both=(True, True),
    neither=(False, False),
)


ErrorStrategy = Union[Literal["new"], Literal["underlying"], Literal["neither"]]
ProxyStrategy = Union[
    Literal["forward"], Literal["backward"], Literal["both"], Literal["neither"]
]


def uplift(
    cls: Type[UpliftingEventEmitter],
    underlying: EventEmitter,
    error_handling: ErrorStrategy = "new",
    proxy_new_listener: ProxyStrategy = "forward",
    *args: Any,
    **kwargs: Any,
) -> UpliftingEventEmitter:
    """A helper to create instances of an event emitter `cls` that inherits
    event behavior from an `underlying` event emitter instance.

    This is mostly helpful if you have a simple underlying event emitter
    that you don't have direct control over, but you want to use that
    event emitter in a new context - for example, you may want to `uplift` a
    `EventEmitter` supplied by a third party library into an
    `AsyncIOEventEmitter` so that you may register async event handlers
    in your `asyncio` app but still be able to receive events from the
    underlying event emitter and call the underlying event emitter's existing
    handlers.

    When called, `uplift` instantiates a new instance of `cls`, passing
    along any unrecognized arguments, and overwrites the `emit` method on
    the `underlying` event emitter to also emit events on the new event
    emitter and vice versa. In both cases, they return whether the `emit`
    method was handled by either emitter. Execution order prefers the event
    emitter on which `emit` was called.

    The `unwrap` function may be called on either instance; this will
    unwrap both `emit` methods.

    The `error_handling` flag can be configured to control what happens to
    unhandled errors:

    - 'new': Error handling for the new event emitter is always used and the
      underlying library's non-event-based error handling is inert.
    - 'underlying': Error handling on the underlying event emitter is always
      used and the new event emitter can not implement non-event-based error
      handling.
    - 'neither': Error handling for the new event emitter is used if the
      handler was registered on the new event emitter, and vice versa.

    Tuning this option can be useful depending on how the underlying event
    emitter does error handling. The default is 'new'.

    The `proxy_new_listener` option can be configured to control how
    `new_listener` events are treated:

    - 'forward': `new_listener` events are propagated from the underlying
      event emitter to the new event emitter but not vice versa.
    - 'both': `new_listener` events are propagated as with other events.
    - 'neither': `new_listener` events are only fired on their respective
      event emitters.
    - 'backward': `new_listener` events are propagated from the new event
      emitter to the underlying event emitter, but not vice versa.

    Tuning this option can be useful depending on how the `new_listener`
    event is used by the underlying event emitter, if at all. The default is
    'forward', since `underlying` may not know how to handle certain
    handlers, such as asyncio coroutines.

    Each event emitter tracks its own internal table of handlers.
    `remove_listener`, `remove_all_listeners` and `listeners` all
    work independently. This means you will have to remember which event
    emitter an event handler was added to!

    Note that both the new event emitter returned by `cls` and the
    underlying event emitter should inherit from `EventEmitter`, or at
    least implement the interface for the undocumented `_call_handlers` and
    `_emit_handle_potential_error` methods.
    """

    (
        new_proxy_new_listener,
        underlying_proxy_new_listener,
    ) = _PROXY_NEW_LISTENER_SETTINGS[proxy_new_listener]

    new: UpliftingEventEmitter = cls(*args, **kwargs)

    uplift_error_handlers: Dict[str, Tuple[EventEmitter, EventEmitter]] = dict(
        new=(new, new), underlying=(underlying, underlying), neither=(new, underlying)
    )

    new_error_handler, underlying_error_handler = uplift_error_handlers[error_handling]

    _wrap(new, underlying, new_error_handler, new_proxy_new_listener)
    _wrap(underlying, new, underlying_error_handler, underlying_proxy_new_listener)

    return new

# === NexusCore/openenv\Lib\site-packages\aiohttp\_websocket\writer.py ===
"""WebSocket protocol versions 13 and 8."""

import asyncio
import random
from functools import partial
from typing import Any, Final, Optional, Union

from ..base_protocol import BaseProtocol
from ..client_exceptions import ClientConnectionResetError
from ..compression_utils import ZLibBackend, ZLibCompressor
from .helpers import (
    MASK_LEN,
    MSG_SIZE,
    PACK_CLOSE_CODE,
    PACK_LEN1,
    PACK_LEN2,
    PACK_LEN3,
    PACK_RANDBITS,
    websocket_mask,
)
from .models import WS_DEFLATE_TRAILING, WSMsgType

DEFAULT_LIMIT: Final[int] = 2**16

# For websockets, keeping latency low is extremely important as implementations
# generally expect to be able to send and receive messages quickly.  We use a
# larger chunk size than the default to reduce the number of executor calls
# since the executor is a significant source of latency and overhead when
# the chunks are small. A size of 5KiB was chosen because it is also the
# same value python-zlib-ng choose to use as the threshold to release the GIL.

WEBSOCKET_MAX_SYNC_CHUNK_SIZE = 5 * 1024


class WebSocketWriter:
    """WebSocket writer.

    The writer is responsible for sending messages to the client. It is
    created by the protocol when a connection is established. The writer
    should avoid implementing any application logic and should only be
    concerned with the low-level details of the WebSocket protocol.
    """

    def __init__(
        self,
        protocol: BaseProtocol,
        transport: asyncio.Transport,
        *,
        use_mask: bool = False,
        limit: int = DEFAULT_LIMIT,
        random: random.Random = random.Random(),
        compress: int = 0,
        notakeover: bool = False,
    ) -> None:
        """Initialize a WebSocket writer."""
        self.protocol = protocol
        self.transport = transport
        self.use_mask = use_mask
        self.get_random_bits = partial(random.getrandbits, 32)
        self.compress = compress
        self.notakeover = notakeover
        self._closing = False
        self._limit = limit
        self._output_size = 0
        self._compressobj: Any = None  # actually compressobj

    async def send_frame(
        self, message: bytes, opcode: int, compress: Optional[int] = None
    ) -> None:
        """Send a frame over the websocket with message as its payload."""
        if self._closing and not (opcode & WSMsgType.CLOSE):
            raise ClientConnectionResetError("Cannot write to closing transport")

        # RSV are the reserved bits in the frame header. They are used to
        # indicate that the frame is using an extension.
        # https://datatracker.ietf.org/doc/html/rfc6455#section-5.2
        rsv = 0
        # Only compress larger packets (disabled)
        # Does small packet needs to be compressed?
        # if self.compress and opcode < 8 and len(message) > 124:
        if (compress or self.compress) and opcode < 8:
            # RSV1 (rsv = 0x40) is set for compressed frames
            # https://datatracker.ietf.org/doc/html/rfc7692#section-7.2.3.1
            rsv = 0x40

            if compress:
                # Do not set self._compress if compressing is for this frame
                compressobj = self._make_compress_obj(compress)
            else:  # self.compress
                if not self._compressobj:
                    self._compressobj = self._make_compress_obj(self.compress)
                compressobj = self._compressobj

            message = (
                await compressobj.compress(message)
                + compressobj.flush(
                    ZLibBackend.Z_FULL_FLUSH
                    if self.notakeover
                    else ZLibBackend.Z_SYNC_FLUSH
                )
            ).removesuffix(WS_DEFLATE_TRAILING)
            # Its critical that we do not return control to the event
            # loop until we have finished sending all the compressed
            # data. Otherwise we could end up mixing compressed frames
            # if there are multiple coroutines compressing data.

        msg_length = len(message)

        use_mask = self.use_mask
        mask_bit = 0x80 if use_mask else 0

        # Depending on the message length, the header is assembled differently.
        # The first byte is reserved for the opcode and the RSV bits.
        first_byte = 0x80 | rsv | opcode
        if msg_length < 126:
            header = PACK_LEN1(first_byte, msg_length | mask_bit)
            header_len = 2
        elif msg_length < 65536:
            header = PACK_LEN2(first_byte, 126 | mask_bit, msg_length)
            header_len = 4
        else:
            header = PACK_LEN3(first_byte, 127 | mask_bit, msg_length)
            header_len = 10

        if self.transport.is_closing():
            raise ClientConnectionResetError("Cannot write to closing transport")

        # https://datatracker.ietf.org/doc/html/rfc6455#section-5.3
        # If we are using a mask, we need to generate it randomly
        # and apply it to the message before sending it. A mask is
        # a 32-bit value that is applied to the message using a
        # bitwise XOR operation. It is used to prevent certain types
        # of attacks on the websocket protocol. The mask is only used
        # when aiohttp is acting as a client. Servers do not use a mask.
        if use_mask:
            mask = PACK_RANDBITS(self.get_random_bits())
            message = bytearray(message)
            websocket_mask(mask, message)
            self.transport.write(header + mask + message)
            self._output_size += MASK_LEN
        elif msg_length > MSG_SIZE:
            self.transport.write(header)
            self.transport.write(message)
        else:
            self.transport.write(header + message)

        self._output_size += header_len + msg_length

        # It is safe to return control to the event loop when using compression
        # after this point as we have already sent or buffered all the data.

        # Once we have written output_size up to the limit, we call the
        # drain helper which waits for the transport to be ready to accept
        # more data. This is a flow control mechanism to prevent the buffer
        # from growing too large. The drain helper will return right away
        # if the writer is not paused.
        if self._output_size > self._limit:
            self._output_size = 0
            if self.protocol._paused:
                await self.protocol._drain_helper()

    def _make_compress_obj(self, compress: int) -> ZLibCompressor:
        return ZLibCompressor(
            level=ZLibBackend.Z_BEST_SPEED,
            wbits=-compress,
            max_sync_chunk_size=WEBSOCKET_MAX_SYNC_CHUNK_SIZE,
        )

    async def close(self, code: int = 1000, message: Union[bytes, str] = b"") -> None:
        """Close the websocket, sending the specified code and message."""
        if isinstance(message, str):
            message = message.encode("utf-8")
        try:
            await self.send_frame(
                PACK_CLOSE_CODE(code) + message, opcode=WSMsgType.CLOSE
            )
        finally:
            self._closing = True

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_dont_trace_files.py ===
# Important: Autogenerated file.

# fmt: off
# DO NOT edit manually!
# DO NOT edit manually!

LIB_FILE = 1
PYDEV_FILE = 2

DONT_TRACE_DIRS = {
    '_pydev_bundle': PYDEV_FILE,
    '_pydev_runfiles': PYDEV_FILE,
    '_pydevd_bundle': PYDEV_FILE,
    '_pydevd_frame_eval': PYDEV_FILE,
    '_pydevd_sys_monitoring': PYDEV_FILE,
    'pydev_ipython': LIB_FILE,
    'pydev_sitecustomize': PYDEV_FILE,
    'pydevd_attach_to_process': PYDEV_FILE,
    'pydevd_concurrency_analyser': PYDEV_FILE,
    'pydevd_plugins': PYDEV_FILE,
    'test_pydevd_reload': PYDEV_FILE,
}

LIB_FILES_IN_DONT_TRACE_DIRS = {
    '__init__.py',
    'inputhook.py',
    'inputhookglut.py',
    'inputhookgtk.py',
    'inputhookgtk3.py',
    'inputhookpyglet.py',
    'inputhookqt4.py',
    'inputhookqt5.py',
    'inputhookqt6.py',
    'inputhooktk.py',
    'inputhookwx.py',
    'matplotlibtools.py',
    'qt.py',
    'qt_for_kernel.py',
    'qt_loaders.py',
    'version.py',
}

DONT_TRACE = {
    # commonly used things from the stdlib that we don't want to trace
    'Queue.py':LIB_FILE,
    'queue.py':LIB_FILE,
    'socket.py':LIB_FILE,
    'weakref.py':LIB_FILE,
    '_weakrefset.py':LIB_FILE,
    'linecache.py':LIB_FILE,
    'threading.py':LIB_FILE,
    'dis.py':LIB_FILE,

    # things from pydev that we don't want to trace
    '__main__pydevd_gen_debug_adapter_protocol.py': PYDEV_FILE,
    '_pydev_calltip_util.py': PYDEV_FILE,
    '_pydev_completer.py': PYDEV_FILE,
    '_pydev_execfile.py': PYDEV_FILE,
    '_pydev_filesystem_encoding.py': PYDEV_FILE,
    '_pydev_getopt.py': PYDEV_FILE,
    '_pydev_imports_tipper.py': PYDEV_FILE,
    '_pydev_jy_imports_tipper.py': PYDEV_FILE,
    '_pydev_log.py': PYDEV_FILE,
    '_pydev_saved_modules.py': PYDEV_FILE,
    '_pydev_sys_patch.py': PYDEV_FILE,
    '_pydev_tipper_common.py': PYDEV_FILE,
    '_pydevd_sys_monitoring.py': PYDEV_FILE,
    'django_debug.py': PYDEV_FILE,
    'jinja2_debug.py': PYDEV_FILE,
    'pycompletionserver.py': PYDEV_FILE,
    'pydev_app_engine_debug_startup.py': PYDEV_FILE,
    'pydev_console_utils.py': PYDEV_FILE,
    'pydev_import_hook.py': PYDEV_FILE,
    'pydev_imports.py': PYDEV_FILE,
    'pydev_ipython_console.py': PYDEV_FILE,
    'pydev_ipython_console_011.py': PYDEV_FILE,
    'pydev_is_thread_alive.py': PYDEV_FILE,
    'pydev_localhost.py': PYDEV_FILE,
    'pydev_log.py': PYDEV_FILE,
    'pydev_monkey.py': PYDEV_FILE,
    'pydev_monkey_qt.py': PYDEV_FILE,
    'pydev_override.py': PYDEV_FILE,
    'pydev_run_in_console.py': PYDEV_FILE,
    'pydev_runfiles.py': PYDEV_FILE,
    'pydev_runfiles_coverage.py': PYDEV_FILE,
    'pydev_runfiles_nose.py': PYDEV_FILE,
    'pydev_runfiles_parallel.py': PYDEV_FILE,
    'pydev_runfiles_parallel_client.py': PYDEV_FILE,
    'pydev_runfiles_pytest2.py': PYDEV_FILE,
    'pydev_runfiles_unittest.py': PYDEV_FILE,
    'pydev_runfiles_xml_rpc.py': PYDEV_FILE,
    'pydev_umd.py': PYDEV_FILE,
    'pydev_versioncheck.py': PYDEV_FILE,
    'pydevconsole.py': PYDEV_FILE,
    'pydevconsole_code.py': PYDEV_FILE,
    'pydevd.py': PYDEV_FILE,
    'pydevd_additional_thread_info.py': PYDEV_FILE,
    'pydevd_additional_thread_info_regular.py': PYDEV_FILE,
    'pydevd_api.py': PYDEV_FILE,
    'pydevd_base_schema.py': PYDEV_FILE,
    'pydevd_breakpoints.py': PYDEV_FILE,
    'pydevd_bytecode_utils.py': PYDEV_FILE,
    'pydevd_bytecode_utils_py311.py': PYDEV_FILE,
    'pydevd_code_to_source.py': PYDEV_FILE,
    'pydevd_collect_bytecode_info.py': PYDEV_FILE,
    'pydevd_comm.py': PYDEV_FILE,
    'pydevd_comm_constants.py': PYDEV_FILE,
    'pydevd_command_line_handling.py': PYDEV_FILE,
    'pydevd_concurrency_logger.py': PYDEV_FILE,
    'pydevd_console.py': PYDEV_FILE,
    'pydevd_constants.py': PYDEV_FILE,
    'pydevd_custom_frames.py': PYDEV_FILE,
    'pydevd_cython_wrapper.py': PYDEV_FILE,
    'pydevd_daemon_thread.py': PYDEV_FILE,
    'pydevd_defaults.py': PYDEV_FILE,
    'pydevd_dont_trace.py': PYDEV_FILE,
    'pydevd_dont_trace_files.py': PYDEV_FILE,
    'pydevd_exec2.py': PYDEV_FILE,
    'pydevd_extension_api.py': PYDEV_FILE,
    'pydevd_extension_utils.py': PYDEV_FILE,
    'pydevd_file_utils.py': PYDEV_FILE,
    'pydevd_filtering.py': PYDEV_FILE,
    'pydevd_frame.py': PYDEV_FILE,
    'pydevd_frame_eval_cython_wrapper.py': PYDEV_FILE,
    'pydevd_frame_eval_main.py': PYDEV_FILE,
    'pydevd_frame_tracing.py': PYDEV_FILE,
    'pydevd_frame_utils.py': PYDEV_FILE,
    'pydevd_gevent_integration.py': PYDEV_FILE,
    'pydevd_helpers.py': PYDEV_FILE,
    'pydevd_import_class.py': PYDEV_FILE,
    'pydevd_io.py': PYDEV_FILE,
    'pydevd_json_debug_options.py': PYDEV_FILE,
    'pydevd_line_validation.py': PYDEV_FILE,
    'pydevd_modify_bytecode.py': PYDEV_FILE,
    'pydevd_net_command.py': PYDEV_FILE,
    'pydevd_net_command_factory_json.py': PYDEV_FILE,
    'pydevd_net_command_factory_xml.py': PYDEV_FILE,
    'pydevd_plugin_numpy_types.py': PYDEV_FILE,
    'pydevd_plugin_pandas_types.py': PYDEV_FILE,
    'pydevd_plugin_utils.py': PYDEV_FILE,
    'pydevd_plugins_django_form_str.py': PYDEV_FILE,
    'pydevd_process_net_command.py': PYDEV_FILE,
    'pydevd_process_net_command_json.py': PYDEV_FILE,
    'pydevd_referrers.py': PYDEV_FILE,
    'pydevd_reload.py': PYDEV_FILE,
    'pydevd_resolver.py': PYDEV_FILE,
    'pydevd_runpy.py': PYDEV_FILE,
    'pydevd_safe_repr.py': PYDEV_FILE,
    'pydevd_save_locals.py': PYDEV_FILE,
    'pydevd_schema.py': PYDEV_FILE,
    'pydevd_schema_log.py': PYDEV_FILE,
    'pydevd_signature.py': PYDEV_FILE,
    'pydevd_source_mapping.py': PYDEV_FILE,
    'pydevd_stackless.py': PYDEV_FILE,
    'pydevd_suspended_frames.py': PYDEV_FILE,
    'pydevd_sys_monitoring.py': PYDEV_FILE,
    'pydevd_thread_lifecycle.py': PYDEV_FILE,
    'pydevd_thread_wrappers.py': PYDEV_FILE,
    'pydevd_timeout.py': PYDEV_FILE,
    'pydevd_trace_dispatch.py': PYDEV_FILE,
    'pydevd_trace_dispatch_regular.py': PYDEV_FILE,
    'pydevd_traceproperty.py': PYDEV_FILE,
    'pydevd_tracing.py': PYDEV_FILE,
    'pydevd_utils.py': PYDEV_FILE,
    'pydevd_vars.py': PYDEV_FILE,
    'pydevd_vm_type.py': PYDEV_FILE,
    'pydevd_xml.py': PYDEV_FILE,
}

# if we try to trace io.py it seems it can get halted (see http://bugs.python.org/issue4716)
DONT_TRACE['io.py'] = LIB_FILE

# Don't trace common encodings too
DONT_TRACE['cp1252.py'] = LIB_FILE
DONT_TRACE['utf_8.py'] = LIB_FILE
DONT_TRACE['codecs.py'] = LIB_FILE

# fmt: on