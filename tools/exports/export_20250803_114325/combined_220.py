
# === NexusCore/openenv\Lib\site-packages\IPython\terminal\ptutils.py ===
"""prompt-toolkit utilities

Everything in this module is a private API,
not to be used outside IPython.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import unicodedata
from wcwidth import wcwidth

from IPython.core.completer import (
    provisionalcompleter, cursor_to_position,
    _deduplicate_completions)
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.patch_stdout import patch_stdout
from IPython.core.getipython import get_ipython


import pygments.lexers as pygments_lexers
import os
import sys
import traceback

_completion_sentinel = object()


def _elide_point(string: str, *, min_elide) -> str:
    """
    If a string is long enough, and has at least 3 dots,
    replace the middle part with ellipses.

    If a string naming a file is long enough, and has at least 3 slashes,
    replace the middle part with ellipses.

    If three consecutive dots, or two consecutive dots are encountered these are
    replaced by the equivalents HORIZONTAL ELLIPSIS or TWO DOT LEADER unicode
    equivalents
    """
    string = string.replace('...','\N{HORIZONTAL ELLIPSIS}')
    string = string.replace('..','\N{TWO DOT LEADER}')
    if len(string) < min_elide:
        return string

    object_parts = string.split('.')
    file_parts = string.split(os.sep)
    if file_parts[-1] == '':
        file_parts.pop()

    if len(object_parts) > 3:
        return "{}.{}\N{HORIZONTAL ELLIPSIS}{}.{}".format(
            object_parts[0],
            object_parts[1][:1],
            object_parts[-2][-1:],
            object_parts[-1],
        )

    elif len(file_parts) > 3:
        return ("{}" + os.sep + "{}\N{HORIZONTAL ELLIPSIS}{}" + os.sep + "{}").format(
            file_parts[0], file_parts[1][:1], file_parts[-2][-1:], file_parts[-1]
        )

    return string


def _elide_typed(string: str, typed: str, *, min_elide: int) -> str:
    """
    Elide the middle of a long string if the beginning has already been typed.
    """

    if len(string) < min_elide:
        return string
    cut_how_much = len(typed)-3
    if cut_how_much < 7:
        return string
    if string.startswith(typed) and len(string)> len(typed):
        return f"{string[:3]}\N{HORIZONTAL ELLIPSIS}{string[cut_how_much:]}"
    return string


def _elide(string: str, typed: str, min_elide) -> str:
    return _elide_typed(
        _elide_point(string, min_elide=min_elide),
        typed, min_elide=min_elide)



def _adjust_completion_text_based_on_context(text, body, offset):
    if text.endswith('=') and len(body) > offset and body[offset] == '=':
        return text[:-1]
    else:
        return text


class IPythonPTCompleter(Completer):
    """Adaptor to provide IPython completions to prompt_toolkit"""
    def __init__(self, ipy_completer=None, shell=None):
        if shell is None and ipy_completer is None:
            raise TypeError("Please pass shell=an InteractiveShell instance.")
        self._ipy_completer = ipy_completer
        self.shell = shell

    @property
    def ipy_completer(self):
        if self._ipy_completer:
            return self._ipy_completer
        else:
            return self.shell.Completer

    def get_completions(self, document, complete_event):
        if not document.current_line.strip():
            return
        # Some bits of our completion system may print stuff (e.g. if a module
        # is imported). This context manager ensures that doesn't interfere with
        # the prompt.

        with patch_stdout(), provisionalcompleter():
            body = document.text
            cursor_row = document.cursor_position_row
            cursor_col = document.cursor_position_col
            cursor_position = document.cursor_position
            offset = cursor_to_position(body, cursor_row, cursor_col)
            try:
                yield from self._get_completions(body, offset, cursor_position, self.ipy_completer)
            except Exception as e:
                try:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_tb)
                except AttributeError:
                    print('Unrecoverable Error in completions')

    def _get_completions(self, body, offset, cursor_position, ipyc):
        """
        Private equivalent of get_completions() use only for unit_testing.
        """
        debug = getattr(ipyc, 'debug', False)
        completions = _deduplicate_completions(
            body, ipyc.completions(body, offset))
        for c in completions:
            if not c.text:
                # Guard against completion machinery giving us an empty string.
                continue
            text = unicodedata.normalize('NFC', c.text)
            # When the first character of the completion has a zero length,
            # then it's probably a decomposed unicode character. E.g. caused by
            # the "\dot" completion. Try to compose again with the previous
            # character.
            if wcwidth(text[0]) == 0:
                if cursor_position + c.start > 0:
                    char_before = body[c.start - 1]
                    fixed_text = unicodedata.normalize(
                        'NFC', char_before + text)

                    # Yield the modified completion instead, if this worked.
                    if wcwidth(text[0:1]) == 1:
                        yield Completion(fixed_text, start_position=c.start - offset - 1)
                        continue

            # TODO: Use Jedi to determine meta_text
            # (Jedi currently has a bug that results in incorrect information.)
            # meta_text = ''
            # yield Completion(m, start_position=start_pos,
            #                  display_meta=meta_text)
            display_text = c.text

            adjusted_text = _adjust_completion_text_based_on_context(
                c.text, body, offset
            )
            min_elide = 30 if self.shell is None else self.shell.min_elide
            if c.type == "function":
                yield Completion(
                    adjusted_text,
                    start_position=c.start - offset,
                    display=_elide(
                        display_text + "()",
                        body[c.start : c.end],
                        min_elide=min_elide,
                    ),
                    display_meta=c.type + c.signature,
                )
            else:
                yield Completion(
                    adjusted_text,
                    start_position=c.start - offset,
                    display=_elide(
                        display_text,
                        body[c.start : c.end],
                        min_elide=min_elide,
                    ),
                    display_meta=c.type,
                )


class IPythonPTLexer(Lexer):
    """
    Wrapper around PythonLexer and BashLexer.
    """
    def __init__(self):
        l = pygments_lexers
        self.python_lexer = PygmentsLexer(l.Python3Lexer)
        self.shell_lexer = PygmentsLexer(l.BashLexer)

        self.magic_lexers = {
            'HTML': PygmentsLexer(l.HtmlLexer),
            'html': PygmentsLexer(l.HtmlLexer),
            'javascript': PygmentsLexer(l.JavascriptLexer),
            'js': PygmentsLexer(l.JavascriptLexer),
            'perl': PygmentsLexer(l.PerlLexer),
            'ruby': PygmentsLexer(l.RubyLexer),
            'latex': PygmentsLexer(l.TexLexer),
        }

    def lex_document(self, document):
        text = document.text.lstrip()

        lexer = self.python_lexer

        if text.startswith('!') or text.startswith('%%bash'):
            lexer = self.shell_lexer

        elif text.startswith('%%'):
            for magic, l in self.magic_lexers.items():
                if text.startswith('%%' + magic):
                    lexer = l
                    break

        return lexer.lex_document(document)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\value\module.py ===
import os
from pathlib import Path
from typing import Optional

from jedi.inference.cache import inference_state_method_cache
from jedi.inference.names import AbstractNameDefinition, ModuleName
from jedi.inference.filters import GlobalNameFilter, ParserTreeFilter, DictFilter, MergedFilter
from jedi.inference import compiled
from jedi.inference.base_value import TreeValue
from jedi.inference.names import SubModuleName
from jedi.inference.helpers import values_from_qualified_names
from jedi.inference.compiled import create_simple_object
from jedi.inference.base_value import ValueSet
from jedi.inference.context import ModuleContext


class _ModuleAttributeName(AbstractNameDefinition):
    """
    For module attributes like __file__, __str__ and so on.
    """
    api_type = 'instance'

    def __init__(self, parent_module, string_name, string_value=None):
        self.parent_context = parent_module
        self.string_name = string_name
        self._string_value = string_value

    def infer(self):
        if self._string_value is not None:
            s = self._string_value
            return ValueSet([
                create_simple_object(self.parent_context.inference_state, s)
            ])
        return compiled.get_string_value_set(self.parent_context.inference_state)


class SubModuleDictMixin:
    @inference_state_method_cache()
    def sub_modules_dict(self):
        """
        Lists modules in the directory of this module (if this module is a
        package).
        """
        names = {}
        if self.is_package():
            mods = self.inference_state.compiled_subprocess.iter_module_names(
                self.py__path__()
            )
            for name in mods:
                # It's obviously a relative import to the current module.
                names[name] = SubModuleName(self.as_context(), name)

        # In the case of an import like `from x.` we don't need to
        # add all the variables, this is only about submodules.
        return names


class ModuleMixin(SubModuleDictMixin):
    _module_name_class = ModuleName

    def get_filters(self, origin_scope=None):
        yield MergedFilter(
            ParserTreeFilter(
                parent_context=self.as_context(),
                origin_scope=origin_scope
            ),
            GlobalNameFilter(self.as_context()),
        )
        yield DictFilter(self.sub_modules_dict())
        yield DictFilter(self._module_attributes_dict())
        yield from self.iter_star_filters()

    def py__class__(self):
        c, = values_from_qualified_names(self.inference_state, 'types', 'ModuleType')
        return c

    def is_module(self):
        return True

    def is_stub(self):
        return False

    @property  # type: ignore[misc]
    @inference_state_method_cache()
    def name(self):
        return self._module_name_class(self, self.string_names[-1])

    @inference_state_method_cache()
    def _module_attributes_dict(self):
        names = ['__package__', '__doc__', '__name__']
        # All the additional module attributes are strings.
        dct = dict((n, _ModuleAttributeName(self, n)) for n in names)
        path = self.py__file__()
        if path is not None:
            dct['__file__'] = _ModuleAttributeName(self, '__file__', str(path))
        return dct

    def iter_star_filters(self):
        for star_module in self.star_imports():
            f = next(star_module.get_filters(), None)
            assert f is not None
            yield f

    # I'm not sure if the star import cache is really that effective anymore
    # with all the other really fast import caches. Recheck. Also we would need
    # to push the star imports into InferenceState.module_cache, if we reenable this.
    @inference_state_method_cache([])
    def star_imports(self):
        from jedi.inference.imports import Importer

        modules = []
        module_context = self.as_context()
        for i in self.tree_node.iter_imports():
            if i.is_star_import():
                new = Importer(
                    self.inference_state,
                    import_path=i.get_paths()[-1],
                    module_context=module_context,
                    level=i.level
                ).follow()

                for module in new:
                    if isinstance(module, ModuleValue):
                        modules += module.star_imports()
                modules += new
        return modules

    def get_qualified_names(self):
        """
        A module doesn't have a qualified name, but it's important to note that
        it's reachable and not `None`. With this information we can add
        qualified names on top for all value children.
        """
        return ()


class ModuleValue(ModuleMixin, TreeValue):
    api_type = 'module'

    def __init__(self, inference_state, module_node, code_lines, file_io=None,
                 string_names=None, is_package=False):
        super().__init__(
            inference_state,
            parent_context=None,
            tree_node=module_node
        )
        self.file_io = file_io
        if file_io is None:
            self._path: Optional[Path] = None
        else:
            self._path = file_io.path
        self.string_names = string_names  # Optional[Tuple[str, ...]]
        self.code_lines = code_lines
        self._is_package = is_package

    def is_stub(self):
        if self._path is not None and self._path.suffix == '.pyi':
            # Currently this is the way how we identify stubs when e.g. goto is
            # used in them. This could be changed if stubs would be identified
            # sooner and used as StubModuleValue.
            return True
        return super().is_stub()

    def py__name__(self):
        if self.string_names is None:
            return None
        return '.'.join(self.string_names)

    def py__file__(self) -> Optional[Path]:
        """
        In contrast to Python's __file__ can be None.
        """
        if self._path is None:
            return None

        return self._path.absolute()

    def is_package(self):
        return self._is_package

    def py__package__(self):
        if self.string_names is None:
            return []

        if self._is_package:
            return self.string_names
        return self.string_names[:-1]

    def py__path__(self):
        """
        In case of a package, this returns Python's __path__ attribute, which
        is a list of paths (strings).
        Returns None if the module is not a package.
        """
        if not self._is_package:
            return None

        # A namespace package is typically auto generated and ~10 lines long.
        first_few_lines = ''.join(self.code_lines[:50])
        # these are strings that need to be used for namespace packages,
        # the first one is ``pkgutil``, the second ``pkg_resources``.
        options = ('declare_namespace(__name__)', 'extend_path(__path__')
        if options[0] in first_few_lines or options[1] in first_few_lines:
            # It is a namespace, now try to find the rest of the
            # modules on sys_path or whatever the search_path is.
            paths = set()
            for s in self.inference_state.get_sys_path():
                other = os.path.join(s, self.name.string_name)
                if os.path.isdir(other):
                    paths.add(other)
            if paths:
                return list(paths)
            # Nested namespace packages will not be supported. Nobody ever
            # asked for it and in Python 3 they are there without using all the
            # crap above.

        # Default to the of this file.
        file = self.py__file__()
        assert file is not None  # Shouldn't be a package in the first place.
        return [os.path.dirname(file)]

    def _as_context(self):
        return ModuleContext(self)

    def __repr__(self):
        return "<%s: %s@%s-%s is_stub=%s>" % (
            self.__class__.__name__, self.py__name__(),
            self.tree_node.start_pos[0], self.tree_node.end_pos[0],
            self.is_stub()
        )

# === NexusCore/openenv\Lib\site-packages\nltk\cluster\kmeans.py ===
# Natural Language Toolkit: K-Means Clusterer
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import copy
import random
import sys

try:
    import numpy
except ImportError:
    pass


from nltk.cluster.util import VectorSpaceClusterer


class KMeansClusterer(VectorSpaceClusterer):
    """
    The K-means clusterer starts with k arbitrary chosen means then allocates
    each vector to the cluster with the closest mean. It then recalculates the
    means of each cluster as the centroid of the vectors in the cluster. This
    process repeats until the cluster memberships stabilise. This is a
    hill-climbing algorithm which may converge to a local maximum. Hence the
    clustering is often repeated with random initial means and the most
    commonly occurring output means are chosen.
    """

    def __init__(
        self,
        num_means,
        distance,
        repeats=1,
        conv_test=1e-6,
        initial_means=None,
        normalise=False,
        svd_dimensions=None,
        rng=None,
        avoid_empty_clusters=False,
    ):
        """
        :param  num_means:  the number of means to use (may use fewer)
        :type   num_means:  int
        :param  distance:   measure of distance between two vectors
        :type   distance:   function taking two vectors and returning a float
        :param  repeats:    number of randomised clustering trials to use
        :type   repeats:    int
        :param  conv_test:  maximum variation in mean differences before
                            deemed convergent
        :type   conv_test:  number
        :param  initial_means: set of k initial means
        :type   initial_means: sequence of vectors
        :param  normalise:  should vectors be normalised to length 1
        :type   normalise:  boolean
        :param svd_dimensions: number of dimensions to use in reducing vector
                               dimensionsionality with SVD
        :type svd_dimensions: int
        :param  rng:        random number generator (or None)
        :type   rng:        Random
        :param avoid_empty_clusters: include current centroid in computation
                                     of next one; avoids undefined behavior
                                     when clusters become empty
        :type avoid_empty_clusters: boolean
        """
        VectorSpaceClusterer.__init__(self, normalise, svd_dimensions)
        self._num_means = num_means
        self._distance = distance
        self._max_difference = conv_test
        assert not initial_means or len(initial_means) == num_means
        self._means = initial_means
        assert repeats >= 1
        assert not (initial_means and repeats > 1)
        self._repeats = repeats
        self._rng = rng if rng else random.Random()
        self._avoid_empty_clusters = avoid_empty_clusters

    def cluster_vectorspace(self, vectors, trace=False):
        if self._means and self._repeats > 1:
            print("Warning: means will be discarded for subsequent trials")

        meanss = []
        for trial in range(self._repeats):
            if trace:
                print("k-means trial", trial)
            if not self._means or trial > 1:
                self._means = self._rng.sample(list(vectors), self._num_means)
            self._cluster_vectorspace(vectors, trace)
            meanss.append(self._means)

        if len(meanss) > 1:
            # sort the means first (so that different cluster numbering won't
            # effect the distance comparison)
            for means in meanss:
                means.sort(key=sum)

            # find the set of means that's minimally different from the others
            min_difference = min_means = None
            for i in range(len(meanss)):
                d = 0
                for j in range(len(meanss)):
                    if i != j:
                        d += self._sum_distances(meanss[i], meanss[j])
                if min_difference is None or d < min_difference:
                    min_difference, min_means = d, meanss[i]

            # use the best means
            self._means = min_means

    def _cluster_vectorspace(self, vectors, trace=False):
        if self._num_means < len(vectors):
            # perform k-means clustering
            converged = False
            while not converged:
                # assign the tokens to clusters based on minimum distance to
                # the cluster means
                clusters = [[] for m in range(self._num_means)]
                for vector in vectors:
                    index = self.classify_vectorspace(vector)
                    clusters[index].append(vector)

                if trace:
                    print("iteration")
                # for i in range(self._num_means):
                # print '  mean', i, 'allocated', len(clusters[i]), 'vectors'

                # recalculate cluster means by computing the centroid of each cluster
                new_means = list(map(self._centroid, clusters, self._means))

                # measure the degree of change from the previous step for convergence
                difference = self._sum_distances(self._means, new_means)
                if difference < self._max_difference:
                    converged = True

                # remember the new means
                self._means = new_means

    def classify_vectorspace(self, vector):
        # finds the closest cluster centroid
        # returns that cluster's index
        best_distance = best_index = None
        for index in range(len(self._means)):
            mean = self._means[index]
            dist = self._distance(vector, mean)
            if best_distance is None or dist < best_distance:
                best_index, best_distance = index, dist
        return best_index

    def num_clusters(self):
        if self._means:
            return len(self._means)
        else:
            return self._num_means

    def means(self):
        """
        The means used for clustering.
        """
        return self._means

    def _sum_distances(self, vectors1, vectors2):
        difference = 0.0
        for u, v in zip(vectors1, vectors2):
            difference += self._distance(u, v)
        return difference

    def _centroid(self, cluster, mean):
        if self._avoid_empty_clusters:
            centroid = copy.copy(mean)
            for vector in cluster:
                centroid += vector
            return centroid / (1 + len(cluster))
        else:
            if not len(cluster):
                sys.stderr.write("Error: no centroid defined for empty cluster.\n")
                sys.stderr.write(
                    "Try setting argument 'avoid_empty_clusters' to True\n"
                )
                assert False
            centroid = copy.copy(cluster[0])
            for vector in cluster[1:]:
                centroid += vector
            return centroid / len(cluster)

    def __repr__(self):
        return "<KMeansClusterer means=%s repeats=%d>" % (self._means, self._repeats)


#################################################################################


def demo():
    # example from figure 14.9, page 517, Manning and Schutze

    from nltk.cluster import KMeansClusterer, euclidean_distance

    vectors = [numpy.array(f) for f in [[2, 1], [1, 3], [4, 7], [6, 7]]]
    means = [[4, 3], [5, 5]]

    clusterer = KMeansClusterer(2, euclidean_distance, initial_means=means)
    clusters = clusterer.cluster(vectors, True, trace=True)

    print("Clustered:", vectors)
    print("As:", clusters)
    print("Means:", clusterer.means())
    print()

    vectors = [numpy.array(f) for f in [[3, 3], [1, 2], [4, 2], [4, 0], [2, 3], [3, 1]]]

    # test k-means using the euclidean distance metric, 2 means and repeat
    # clustering 10 times with random seeds

    clusterer = KMeansClusterer(2, euclidean_distance, repeats=10)
    clusters = clusterer.cluster(vectors, True)
    print("Clustered:", vectors)
    print("As:", clusters)
    print("Means:", clusterer.means())
    print()

    # classify a new vector
    vector = numpy.array([3, 3])
    print("classify(%s):" % vector, end=" ")
    print(clusterer.classify(vector))
    print()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\chromium\webdriver.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from typing import Optional

from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.common.options import ArgOptions
from selenium.webdriver.common.service import Service
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver


class ChromiumDriver(RemoteWebDriver):
    """Controls the WebDriver instance of ChromiumDriver and allows you to
    drive the browser."""

    def __init__(
        self,
        browser_name: Optional[str] = None,
        vendor_prefix: Optional[str] = None,
        options: ArgOptions = ArgOptions(),
        service: Optional[Service] = None,
        keep_alive: bool = True,
    ) -> None:
        """Creates a new WebDriver instance of the ChromiumDriver. Starts the
        service and then creates new WebDriver instance of ChromiumDriver.

        :Args:
         - browser_name - Browser name used when matching capabilities.
         - vendor_prefix - Company prefix to apply to vendor-specific WebDriver extension commands.
         - options - this takes an instance of ChromiumOptions
         - service - Service object for handling the browser driver if you need to pass extra details
         - keep_alive - Whether to configure ChromiumRemoteConnection to use HTTP keep-alive.
        """
        self.service = service

        finder = DriverFinder(self.service, options)
        if finder.get_browser_path():
            options.binary_location = finder.get_browser_path()
            options.browser_version = None

        self.service.path = self.service.env_path() or finder.get_driver_path()
        self.service.start()

        executor = ChromiumRemoteConnection(
            remote_server_addr=self.service.service_url,
            browser_name=browser_name,
            vendor_prefix=vendor_prefix,
            keep_alive=keep_alive,
            ignore_proxy=options._ignore_local_proxy,
        )

        try:
            super().__init__(command_executor=executor, options=options)
        except Exception:
            self.quit()
            raise

        self._is_remote = False

    def launch_app(self, id):
        """Launches Chromium app specified by id."""
        return self.execute("launchApp", {"id": id})

    def get_network_conditions(self):
        """Gets Chromium network emulation settings.

        :Returns:
            A dict.
            For example:     {'latency': 4, 'download_throughput': 2, 'upload_throughput': 2, 'offline': False}
        """
        return self.execute("getNetworkConditions")["value"]

    def set_network_conditions(self, **network_conditions) -> None:
        """Sets Chromium network emulation settings.

        :Args:
         - network_conditions: A dict with conditions specification.

        :Usage:
            ::

                driver.set_network_conditions(
                    offline=False,
                    latency=5,  # additional latency (ms)
                    download_throughput=500 * 1024,  # maximal throughput
                    upload_throughput=500 * 1024,
                )  # maximal throughput

            Note: 'throughput' can be used to set both (for download and upload).
        """
        self.execute("setNetworkConditions", {"network_conditions": network_conditions})

    def delete_network_conditions(self) -> None:
        """Resets Chromium network emulation settings."""
        self.execute("deleteNetworkConditions")

    def set_permissions(self, name: str, value: str) -> None:
        """Sets Applicable Permission.

        :Args:
         - name: The item to set the permission on.
         - value: The value to set on the item

        :Usage:
            ::

                driver.set_permissions("clipboard-read", "denied")
        """
        self.execute("setPermissions", {"descriptor": {"name": name}, "state": value})

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict):
        """Execute Chrome Devtools Protocol command and get returned result The
        command and command args should follow chrome devtools protocol
        domains/commands, refer to link
        https://chromedevtools.github.io/devtools-protocol/

        :Args:
         - cmd: A str, command name
         - cmd_args: A dict, command args. empty dict {} if there is no command args
        :Usage:
            ::

                driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': requestId})
        :Returns:
            A dict, empty dict {} if there is no result to return.
            For example to getResponseBody:
            {'base64Encoded': False, 'body': 'response body string'}
        """
        return super().execute_cdp_cmd(cmd, cmd_args)

    def get_sinks(self) -> list:
        """:Returns: A list of sinks available for Cast."""
        return self.execute("getSinks")["value"]

    def get_issue_message(self):
        """:Returns: An error message when there is any issue in a Cast
        session."""
        return self.execute("getIssueMessage")["value"]

    @property
    def log_types(self):
        """Gets a list of the available log types.

        Example:
        --------
        >>> driver.log_types
        """
        return self.execute(Command.GET_AVAILABLE_LOG_TYPES)["value"]

    def get_log(self, log_type):
        """Gets the log for a given log type.

        Parameters:
        -----------
        log_type : str
            - Type of log that which will be returned

        Example:
        --------
        >>> driver.get_log("browser")
        >>> driver.get_log("driver")
        >>> driver.get_log("client")
        >>> driver.get_log("server")
        """
        return self.execute(Command.GET_LOG, {"type": log_type})["value"]

    def set_sink_to_use(self, sink_name: str) -> dict:
        """Sets a specific sink, using its name, as a Cast session receiver
        target.

        :Args:
         - sink_name: Name of the sink to use as the target.
        """
        return self.execute("setSinkToUse", {"sinkName": sink_name})

    def start_desktop_mirroring(self, sink_name: str) -> dict:
        """Starts a desktop mirroring session on a specific receiver target.

        :Args:
         - sink_name: Name of the sink to use as the target.
        """
        return self.execute("startDesktopMirroring", {"sinkName": sink_name})

    def start_tab_mirroring(self, sink_name: str) -> dict:
        """Starts a tab mirroring session on a specific receiver target.

        :Args:
         - sink_name: Name of the sink to use as the target.
        """
        return self.execute("startTabMirroring", {"sinkName": sink_name})

    def stop_casting(self, sink_name: str) -> dict:
        """Stops the existing Cast session on a specific receiver target.

        :Args:
         - sink_name: Name of the sink to stop the Cast session.
        """
        return self.execute("stopCasting", {"sinkName": sink_name})

    def quit(self) -> None:
        """Closes the browser and shuts down the ChromiumDriver executable."""
        try:
            super().quit()
        except Exception:
            # We don't care about the message because something probably has gone wrong
            pass
        finally:
            self.service.stop()

    def download_file(self, *args, **kwargs):
        raise NotImplementedError

    def get_downloadable_files(self, *args, **kwargs):
        raise NotImplementedError

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\compilers\C\zos.py ===
"""distutils.zosccompiler

Contains the selection of the c & c++ compilers on z/OS. There are several
different c compilers on z/OS, all of them are optional, so the correct
one needs to be chosen based on the users input. This is compatible with
the following compilers:

IBM C/C++ For Open Enterprise Languages on z/OS 2.0
IBM Open XL C/C++ 1.1 for z/OS
IBM XL C/C++ V2.4.1 for z/OS 2.4 and 2.5
IBM z/OS XL C/C++
"""

import os

from ... import sysconfig
from ...errors import DistutilsExecError
from . import unix
from .errors import CompileError

_cc_args = {
    'ibm-openxl': [
        '-m64',
        '-fvisibility=default',
        '-fzos-le-char-mode=ascii',
        '-fno-short-enums',
    ],
    'ibm-xlclang': [
        '-q64',
        '-qexportall',
        '-qascii',
        '-qstrict',
        '-qnocsect',
        '-Wa,asa,goff',
        '-Wa,xplink',
        '-qgonumber',
        '-qenum=int',
        '-Wc,DLL',
    ],
    'ibm-xlc': [
        '-q64',
        '-qexportall',
        '-qascii',
        '-qstrict',
        '-qnocsect',
        '-Wa,asa,goff',
        '-Wa,xplink',
        '-qgonumber',
        '-qenum=int',
        '-Wc,DLL',
        '-qlanglvl=extc99',
    ],
}

_cxx_args = {
    'ibm-openxl': [
        '-m64',
        '-fvisibility=default',
        '-fzos-le-char-mode=ascii',
        '-fno-short-enums',
    ],
    'ibm-xlclang': [
        '-q64',
        '-qexportall',
        '-qascii',
        '-qstrict',
        '-qnocsect',
        '-Wa,asa,goff',
        '-Wa,xplink',
        '-qgonumber',
        '-qenum=int',
        '-Wc,DLL',
    ],
    'ibm-xlc': [
        '-q64',
        '-qexportall',
        '-qascii',
        '-qstrict',
        '-qnocsect',
        '-Wa,asa,goff',
        '-Wa,xplink',
        '-qgonumber',
        '-qenum=int',
        '-Wc,DLL',
        '-qlanglvl=extended0x',
    ],
}

_asm_args = {
    'ibm-openxl': ['-fasm', '-fno-integrated-as', '-Wa,--ASA', '-Wa,--GOFF'],
    'ibm-xlclang': [],
    'ibm-xlc': [],
}

_ld_args = {
    'ibm-openxl': [],
    'ibm-xlclang': ['-Wl,dll', '-q64'],
    'ibm-xlc': ['-Wl,dll', '-q64'],
}


# Python on z/OS is built with no compiler specific options in it's CFLAGS.
# But each compiler requires it's own specific options to build successfully,
# though some of the options are common between them
class Compiler(unix.Compiler):
    src_extensions = ['.c', '.C', '.cc', '.cxx', '.cpp', '.m', '.s']
    _cpp_extensions = ['.cc', '.cpp', '.cxx', '.C']
    _asm_extensions = ['.s']

    def _get_zos_compiler_name(self):
        zos_compiler_names = [
            os.path.basename(binary)
            for envvar in ('CC', 'CXX', 'LDSHARED')
            if (binary := os.environ.get(envvar, None))
        ]
        if len(zos_compiler_names) == 0:
            return 'ibm-openxl'

        zos_compilers = {}
        for compiler in (
            'ibm-clang',
            'ibm-clang64',
            'ibm-clang++',
            'ibm-clang++64',
            'clang',
            'clang++',
            'clang-14',
        ):
            zos_compilers[compiler] = 'ibm-openxl'

        for compiler in ('xlclang', 'xlclang++', 'njsc', 'njsc++'):
            zos_compilers[compiler] = 'ibm-xlclang'

        for compiler in ('xlc', 'xlC', 'xlc++'):
            zos_compilers[compiler] = 'ibm-xlc'

        return zos_compilers.get(zos_compiler_names[0], 'ibm-openxl')

    def __init__(self, verbose=False, dry_run=False, force=False):
        super().__init__(verbose, dry_run, force)
        self.zos_compiler = self._get_zos_compiler_name()
        sysconfig.customize_compiler(self)

    def _compile(self, obj, src, ext, cc_args, extra_postargs, pp_opts):
        local_args = []
        if ext in self._cpp_extensions:
            compiler = self.compiler_cxx
            local_args.extend(_cxx_args[self.zos_compiler])
        elif ext in self._asm_extensions:
            compiler = self.compiler_so
            local_args.extend(_cc_args[self.zos_compiler])
            local_args.extend(_asm_args[self.zos_compiler])
        else:
            compiler = self.compiler_so
            local_args.extend(_cc_args[self.zos_compiler])
        local_args.extend(cc_args)

        try:
            self.spawn(compiler + local_args + [src, '-o', obj] + extra_postargs)
        except DistutilsExecError as msg:
            raise CompileError(msg)

    def runtime_library_dir_option(self, dir):
        return '-L' + dir

    def link(
        self,
        target_desc,
        objects,
        output_filename,
        output_dir=None,
        libraries=None,
        library_dirs=None,
        runtime_library_dirs=None,
        export_symbols=None,
        debug=False,
        extra_preargs=None,
        extra_postargs=None,
        build_temp=None,
        target_lang=None,
    ):
        # For a built module to use functions from cpython, it needs to use Pythons
        # side deck file. The side deck is located beside the libpython3.xx.so
        ldversion = sysconfig.get_config_var('LDVERSION')
        if sysconfig.python_build:
            side_deck_path = os.path.join(
                sysconfig.get_config_var('abs_builddir'),
                f'libpython{ldversion}.x',
            )
        else:
            side_deck_path = os.path.join(
                sysconfig.get_config_var('installed_base'),
                sysconfig.get_config_var('platlibdir'),
                f'libpython{ldversion}.x',
            )

        if os.path.exists(side_deck_path):
            if extra_postargs:
                extra_postargs.append(side_deck_path)
            else:
                extra_postargs = [side_deck_path]

        # Check and replace libraries included side deck files
        if runtime_library_dirs:
            for dir in runtime_library_dirs:
                for library in libraries[:]:
                    library_side_deck = os.path.join(dir, f'{library}.x')
                    if os.path.exists(library_side_deck):
                        libraries.remove(library)
                        extra_postargs.append(library_side_deck)
                        break

        # Any required ld args for the given compiler
        extra_postargs.extend(_ld_args[self.zos_compiler])

        super().link(
            target_desc,
            objects,
            output_filename,
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            export_symbols,
            debug,
            extra_preargs,
            extra_postargs,
            build_temp,
            target_lang,
        )

# === NexusCore/openenv\Lib\site-packages\tornado\test\tcpserver_test.py ===
import socket
import subprocess
import sys
import textwrap
import unittest

from tornado import gen
from tornado.iostream import IOStream
from tornado.log import app_log
from tornado.tcpserver import TCPServer
from tornado.test.util import skipIfNonUnix
from tornado.testing import AsyncTestCase, ExpectLog, bind_unused_port, gen_test

from typing import Tuple


class TCPServerTest(AsyncTestCase):
    @gen_test
    def test_handle_stream_coroutine_logging(self):
        # handle_stream may be a coroutine and any exception in its
        # Future will be logged.
        class TestServer(TCPServer):
            @gen.coroutine
            def handle_stream(self, stream, address):
                yield stream.read_bytes(len(b"hello"))
                stream.close()
                1 / 0

        server = client = None
        try:
            sock, port = bind_unused_port()
            server = TestServer()
            server.add_socket(sock)
            client = IOStream(socket.socket())
            with ExpectLog(app_log, "Exception in callback"):
                yield client.connect(("localhost", port))
                yield client.write(b"hello")
                yield client.read_until_close()
                yield gen.moment
        finally:
            if server is not None:
                server.stop()
            if client is not None:
                client.close()

    @gen_test
    def test_handle_stream_native_coroutine(self):
        # handle_stream may be a native coroutine.

        class TestServer(TCPServer):
            async def handle_stream(self, stream, address):
                stream.write(b"data")
                stream.close()

        sock, port = bind_unused_port()
        server = TestServer()
        server.add_socket(sock)
        client = IOStream(socket.socket())
        yield client.connect(("localhost", port))
        result = yield client.read_until_close()
        self.assertEqual(result, b"data")
        server.stop()
        client.close()

    def test_stop_twice(self):
        sock, port = bind_unused_port()
        server = TCPServer()
        server.add_socket(sock)
        server.stop()
        server.stop()

    @gen_test
    def test_stop_in_callback(self):
        # Issue #2069: calling server.stop() in a loop callback should not
        # raise EBADF when the loop handles other server connection
        # requests in the same loop iteration

        class TestServer(TCPServer):
            @gen.coroutine
            def handle_stream(self, stream, address):
                server.stop()  # type: ignore
                yield stream.read_until_close()

        sock, port = bind_unused_port()
        server = TestServer()
        server.add_socket(sock)
        server_addr = ("localhost", port)
        N = 40
        clients = [IOStream(socket.socket()) for i in range(N)]
        connected_clients = []

        @gen.coroutine
        def connect(c):
            try:
                yield c.connect(server_addr)
            except OSError:
                pass
            else:
                connected_clients.append(c)

        yield [connect(c) for c in clients]

        self.assertGreater(len(connected_clients), 0, "all clients failed connecting")
        try:
            if len(connected_clients) == N:
                # Ideally we'd make the test deterministic, but we're testing
                # for a race condition in combination with the system's TCP stack...
                self.skipTest(
                    "at least one client should fail connecting "
                    "for the test to be meaningful"
                )
        finally:
            for c in connected_clients:
                c.close()

        # Here tearDown() would re-raise the EBADF encountered in the IO loop


@skipIfNonUnix
class TestMultiprocess(unittest.TestCase):
    # These tests verify that the two multiprocess examples from the
    # TCPServer docs work. Both tests start a server with three worker
    # processes, each of which prints its task id to stdout (a single
    # byte, so we don't have to worry about atomicity of the shared
    # stdout stream) and then exits.
    def run_subproc(self, code: str) -> Tuple[str, str]:
        try:
            result = subprocess.run(
                [sys.executable, "-Werror::DeprecationWarning"],
                capture_output=True,
                input=code,
                encoding="utf8",
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Process returned {e.returncode} stdout={e.stdout} stderr={e.stderr}"
            ) from e
        return result.stdout, result.stderr

    def test_listen_single(self):
        # As a sanity check, run the single-process version through this test
        # harness too.
        code = textwrap.dedent(
            """
            import asyncio
            from tornado.tcpserver import TCPServer

            async def main():
                server = TCPServer()
                server.listen(0, address='127.0.0.1')

            asyncio.run(main())
            print('012', end='')
        """
        )
        out, err = self.run_subproc(code)
        self.assertEqual("".join(sorted(out)), "012")
        self.assertEqual(err, "")

    def test_bind_start(self):
        code = textwrap.dedent(
            """
            import warnings

            from tornado.ioloop import IOLoop
            from tornado.process import task_id
            from tornado.tcpserver import TCPServer

            warnings.simplefilter("ignore", DeprecationWarning)

            server = TCPServer()
            server.bind(0, address='127.0.0.1')
            server.start(3)
            IOLoop.current().run_sync(lambda: None)
            print(task_id(), end='')
        """
        )
        out, err = self.run_subproc(code)
        self.assertEqual("".join(sorted(out)), "012")
        self.assertEqual(err, "")

    def test_add_sockets(self):
        code = textwrap.dedent(
            """
            import asyncio
            from tornado.netutil import bind_sockets
            from tornado.process import fork_processes, task_id
            from tornado.ioloop import IOLoop
            from tornado.tcpserver import TCPServer

            sockets = bind_sockets(0, address='127.0.0.1')
            fork_processes(3)
            async def post_fork_main():
                server = TCPServer()
                server.add_sockets(sockets)
            asyncio.run(post_fork_main())
            print(task_id(), end='')
        """
        )
        out, err = self.run_subproc(code)
        self.assertEqual("".join(sorted(out)), "012")
        self.assertEqual(err, "")

    def test_listen_multi_reuse_port(self):
        code = textwrap.dedent(
            """
            import asyncio
            import socket
            from tornado.netutil import bind_sockets
            from tornado.process import task_id, fork_processes
            from tornado.tcpserver import TCPServer

            # Pick an unused port which we will be able to bind to multiple times.
            (sock,) = bind_sockets(0, address='127.0.0.1',
                family=socket.AF_INET, reuse_port=True)
            port = sock.getsockname()[1]

            fork_processes(3)

            async def main():
                server = TCPServer()
                server.listen(port, address='127.0.0.1', reuse_port=True)
            asyncio.run(main())
            print(task_id(), end='')
            """
        )
        out, err = self.run_subproc(code)
        self.assertEqual("".join(sorted(out)), "012")
        self.assertEqual(err, "")

# === NexusCore/openenv\Lib\site-packages\win32\Demos\winprocess.py ===
"""
Windows Process Control

winprocess.run launches a child process and returns the exit code.
Optionally, it can:
  redirect stdin, stdout & stderr to files
  run the command as another user
  limit the process's running time
  control the process window (location, size, window state, desktop)
Works on Windows NT, 2000 & XP. Requires Mark Hammond's win32
extensions.

This code is free for any purpose, with no warranty of any kind.
-- John B. Dell'Aquila <jbd@alum.mit.edu>
"""

import msvcrt
import os

import win32api
import win32con
import win32event
import win32gui
import win32process
import win32security


def logonUser(loginString):
    """
    Login as specified user and return handle.
    loginString:  'Domain\nUser\nPassword'; for local
        login use . or empty string as domain
        e.g. '.\nadministrator\nsecret_password'
    """
    domain, user, passwd = loginString.split("\n")
    return win32security.LogonUser(
        user,
        domain,
        passwd,
        win32con.LOGON32_LOGON_INTERACTIVE,
        win32con.LOGON32_PROVIDER_DEFAULT,
    )


class Process:
    """
    A Windows process.
    """

    def __init__(
        self,
        cmd,
        login=None,
        hStdin=None,
        hStdout=None,
        hStderr=None,
        show=1,
        xy=None,
        xySize=None,
        desktop=None,
    ):
        """
        Create a Windows process.
        cmd:     command to run
        login:   run as user 'Domain\nUser\nPassword'
        hStdin, hStdout, hStderr:
                 handles for process I/O; default is caller's stdin,
                 stdout & stderr
        show:    wShowWindow (0=SW_HIDE, 1=SW_NORMAL, ...)
        xy:      window offset (x, y) of upper left corner in pixels
        xySize:  window size (width, height) in pixels
        desktop: lpDesktop - name of desktop e.g. 'winsta0\\default'
                 None = inherit current desktop
                 '' = create new desktop if necessary

        User calling login requires additional privileges:
          Act as part of the operating system [not needed on Windows XP]
          Increase quotas
          Replace a process level token
        Login string must EITHER be an administrator's account
        (ordinary user can't access current desktop - see Microsoft
        Q165194) OR use desktop='' to run another desktop invisibly
        (may be very slow to startup & finalize).
        """
        si = win32process.STARTUPINFO()
        si.dwFlags = win32con.STARTF_USESTDHANDLES ^ win32con.STARTF_USESHOWWINDOW
        if hStdin is None:
            si.hStdInput = win32api.GetStdHandle(win32api.STD_INPUT_HANDLE)
        else:
            si.hStdInput = hStdin
        if hStdout is None:
            si.hStdOutput = win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE)
        else:
            si.hStdOutput = hStdout
        if hStderr is None:
            si.hStdError = win32api.GetStdHandle(win32api.STD_ERROR_HANDLE)
        else:
            si.hStdError = hStderr
        si.wShowWindow = show
        if xy is not None:
            si.dwX, si.dwY = xy
            si.dwFlags ^= win32con.STARTF_USEPOSITION
        if xySize is not None:
            si.dwXSize, si.dwYSize = xySize
            si.dwFlags ^= win32con.STARTF_USESIZE
        if desktop is not None:
            si.lpDesktop = desktop
        procArgs = (
            None,  # appName
            cmd,  # commandLine
            None,  # processAttributes
            None,  # threadAttributes
            1,  # bInheritHandles
            win32process.CREATE_NEW_CONSOLE,  # dwCreationFlags
            None,  # newEnvironment
            None,  # currentDirectory
            si,
        )  # startupinfo
        if login is not None:
            hUser = logonUser(login)
            win32security.ImpersonateLoggedOnUser(hUser)
            procHandles = win32process.CreateProcessAsUser(hUser, *procArgs)
            win32security.RevertToSelf()
        else:
            procHandles = win32process.CreateProcess(*procArgs)
        self.hProcess, self.hThread, self.PId, self.TId = procHandles

    def wait(self, mSec=None):
        """
        Wait for process to finish or for specified number of
        milliseconds to elapse.
        """
        if mSec is None:
            mSec = win32event.INFINITE
        return win32event.WaitForSingleObject(self.hProcess, mSec)

    def kill(self, gracePeriod=5000):
        """
        Kill process. Try for an orderly shutdown via WM_CLOSE.  If
        still running after gracePeriod (5 sec. default), terminate.
        """
        win32gui.EnumWindows(self.__close__, 0)
        if self.wait(gracePeriod) != win32event.WAIT_OBJECT_0:
            win32process.TerminateProcess(self.hProcess, 0)
            win32api.Sleep(100)  # wait for resources to be released

    def __close__(self, hwnd, dummy):
        """
        EnumWindows callback - sends WM_CLOSE to any window
        owned by this process.
        """
        TId, PId = win32process.GetWindowThreadProcessId(hwnd)
        if PId == self.PId:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

    def exitCode(self):
        """
        Return process exit code.
        """
        return win32process.GetExitCodeProcess(self.hProcess)


def run(cmd, mSec=None, stdin=None, stdout=None, stderr=None, **kw):
    """
    Run cmd as a child process and return exit code.
    mSec:  terminate cmd after specified number of milliseconds
    stdin, stdout, stderr:
           file objects for child I/O (use hStdin etc. to attach
           handles instead of files); default is caller's stdin,
           stdout & stderr;
    kw:    see Process.__init__ for more keyword options
    """
    if stdin is not None:
        kw["hStdin"] = msvcrt.get_osfhandle(stdin.fileno())
    if stdout is not None:
        kw["hStdout"] = msvcrt.get_osfhandle(stdout.fileno())
    if stderr is not None:
        kw["hStderr"] = msvcrt.get_osfhandle(stderr.fileno())
    child = Process(cmd, **kw)
    if child.wait(mSec) != win32event.WAIT_OBJECT_0:
        child.kill()
        raise OSError("process timeout exceeded")
    return child.exitCode()


if __name__ == "__main__":
    # Pipe commands to a shell and display the output in notepad
    print("Testing winprocess.py...")

    import tempfile

    timeoutSeconds = 15
    cmdString = (
        """\
REM      Test of winprocess.py piping commands to a shell.\r
REM      This 'notepad' process will terminate in %d seconds.\r
vol\r
net user\r
_this_is_a_test_of_stderr_\r
"""
        % timeoutSeconds
    )

    cmd_name = tempfile.mktemp()
    out_name = cmd_name + ".txt"
    try:
        cmd = open(cmd_name, "w+b")
        out = open(out_name, "w+b")
        cmd.write(cmdString.encode("mbcs"))
        cmd.seek(0)
        print(
            "CMD.EXE exit code:",
            run("cmd.exe", show=0, stdin=cmd, stdout=out, stderr=out),
        )
        cmd.close()
        print(
            "NOTEPAD exit code:",
            run(
                "notepad.exe %s" % out.name,
                show=win32con.SW_MAXIMIZE,
                mSec=timeoutSeconds * 1000,
            ),
        )
        out.close()
    finally:
        for n in (cmd_name, out_name):
            try:
                os.unlink(cmd_name)
            except OSError:
                pass

# === NexusCore/openenv\Lib\site-packages\jsonschema\protocols.py ===
"""
typing.Protocol classes for jsonschema interfaces.
"""

# for reference material on Protocols, see
#   https://www.python.org/dev/peps/pep-0544/

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

# in order for Sphinx to resolve references accurately from type annotations,
# it needs to see names like `jsonschema.TypeChecker`
# therefore, only import at type-checking time (to avoid circular references),
# but use `jsonschema` for any types which will otherwise not be resolvable
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    import referencing.jsonschema

    from jsonschema import _typing
    from jsonschema.exceptions import ValidationError
    import jsonschema
    import jsonschema.validators

# For code authors working on the validator protocol, these are the three
# use-cases which should be kept in mind:
#
# 1. As a protocol class, it can be used in type annotations to describe the
#    available methods and attributes of a validator
# 2. It is the source of autodoc for the validator documentation
# 3. It is runtime_checkable, meaning that it can be used in isinstance()
#    checks.
#
# Since protocols are not base classes, isinstance() checking is limited in
# its capabilities. See docs on runtime_checkable for detail


@runtime_checkable
class Validator(Protocol):
    """
    The protocol to which all validator classes adhere.

    Arguments:

        schema:

            The schema that the validator object will validate with.
            It is assumed to be valid, and providing
            an invalid schema can lead to undefined behavior. See
            `Validator.check_schema` to validate a schema first.

        registry:

            a schema registry that will be used for looking up JSON references

        resolver:

            a resolver that will be used to resolve :kw:`$ref`
            properties (JSON references). If unprovided, one will be created.

            .. deprecated:: v4.18.0

                `RefResolver <_RefResolver>` has been deprecated in favor of
                `referencing`, and with it, this argument.

        format_checker:

            if provided, a checker which will be used to assert about
            :kw:`format` properties present in the schema. If unprovided,
            *no* format validation is done, and the presence of format
            within schemas is strictly informational. Certain formats
            require additional packages to be installed in order to assert
            against instances. Ensure you've installed `jsonschema` with
            its `extra (optional) dependencies <index:extras>` when
            invoking ``pip``.

    .. deprecated:: v4.12.0

        Subclassing validator classes now explicitly warns this is not part of
        their public API.

    """

    #: An object representing the validator's meta schema (the schema that
    #: describes valid schemas in the given version).
    META_SCHEMA: ClassVar[Mapping]

    #: A mapping of validation keywords (`str`\s) to functions that
    #: validate the keyword with that name. For more information see
    #: `creating-validators`.
    VALIDATORS: ClassVar[Mapping]

    #: A `jsonschema.TypeChecker` that will be used when validating
    #: :kw:`type` keywords in JSON schemas.
    TYPE_CHECKER: ClassVar[jsonschema.TypeChecker]

    #: A `jsonschema.FormatChecker` that will be used when validating
    #: :kw:`format` keywords in JSON schemas.
    FORMAT_CHECKER: ClassVar[jsonschema.FormatChecker]

    #: A function which given a schema returns its ID.
    ID_OF: _typing.id_of

    #: The schema that will be used to validate instances
    schema: Mapping | bool

    def __init__(
        self,
        schema: Mapping | bool,
        registry: referencing.jsonschema.SchemaRegistry,
        format_checker: jsonschema.FormatChecker | None = None,
    ) -> None:
        ...

    @classmethod
    def check_schema(cls, schema: Mapping | bool) -> None:
        """
        Validate the given schema against the validator's `META_SCHEMA`.

        Raises:

            `jsonschema.exceptions.SchemaError`:

                if the schema is invalid

        """

    def is_type(self, instance: Any, type: str) -> bool:
        """
        Check if the instance is of the given (JSON Schema) type.

        Arguments:

            instance:

                the value to check

            type:

                the name of a known (JSON Schema) type

        Returns:

            whether the instance is of the given type

        Raises:

            `jsonschema.exceptions.UnknownType`:

                if ``type`` is not a known type

        """

    def is_valid(self, instance: Any) -> bool:
        """
        Check if the instance is valid under the current `schema`.

        Returns:

            whether the instance is valid or not

        >>> schema = {"maxItems" : 2}
        >>> Draft202012Validator(schema).is_valid([2, 3, 4])
        False

        """

    def iter_errors(self, instance: Any) -> Iterable[ValidationError]:
        r"""
        Lazily yield each of the validation errors in the given instance.

        >>> schema = {
        ...     "type" : "array",
        ...     "items" : {"enum" : [1, 2, 3]},
        ...     "maxItems" : 2,
        ... }
        >>> v = Draft202012Validator(schema)
        >>> for error in sorted(v.iter_errors([2, 3, 4]), key=str):
        ...     print(error.message)
        4 is not one of [1, 2, 3]
        [2, 3, 4] is too long

        .. deprecated:: v4.0.0

            Calling this function with a second schema argument is deprecated.
            Use `Validator.evolve` instead.
        """

    def validate(self, instance: Any) -> None:
        """
        Check if the instance is valid under the current `schema`.

        Raises:

            `jsonschema.exceptions.ValidationError`:

                if the instance is invalid

        >>> schema = {"maxItems" : 2}
        >>> Draft202012Validator(schema).validate([2, 3, 4])
        Traceback (most recent call last):
            ...
        ValidationError: [2, 3, 4] is too long

        """

    def evolve(self, **kwargs) -> Validator:
        """
        Create a new validator like this one, but with given changes.

        Preserves all other attributes, so can be used to e.g. create a
        validator with a different schema but with the same :kw:`$ref`
        resolution behavior.

        >>> validator = Draft202012Validator({})
        >>> validator.evolve(schema={"type": "number"})
        Draft202012Validator(schema={'type': 'number'}, format_checker=None)

        The returned object satisfies the validator protocol, but may not
        be of the same concrete class! In particular this occurs
        when a :kw:`$ref` occurs to a schema with a different
        :kw:`$schema` than this one (i.e. for a different draft).

        >>> validator.evolve(
        ...     schema={"$schema": Draft7Validator.META_SCHEMA["$id"]}
        ... )
        Draft7Validator(schema=..., format_checker=None)
        """

# === NexusCore/openenv\Lib\site-packages\PIL\PcxImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# PCX file handling
#
# This format was originally used by ZSoft's popular PaintBrush
# program for the IBM PC.  It is also supported by many MS-DOS and
# Windows applications, including the Windows PaintBrush program in
# Windows 3.
#
# history:
# 1995-09-01 fl   Created
# 1996-05-20 fl   Fixed RGB support
# 1997-01-03 fl   Fixed 2-bit and 4-bit support
# 1999-02-03 fl   Fixed 8-bit support (broken in 1.0b1)
# 1999-02-07 fl   Added write support
# 2002-06-09 fl   Made 2-bit and 4-bit support a bit more robust
# 2002-07-30 fl   Seek from to current position, not beginning of file
# 2003-06-03 fl   Extract DPI settings (info["dpi"])
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2003 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import io
import logging
from typing import IO

from . import Image, ImageFile, ImagePalette
from ._binary import i16le as i16
from ._binary import o8
from ._binary import o16le as o16

logger = logging.getLogger(__name__)


def _accept(prefix: bytes) -> bool:
    return prefix[0] == 10 and prefix[1] in [0, 2, 3, 5]


##
# Image plugin for Paintbrush images.


class PcxImageFile(ImageFile.ImageFile):
    format = "PCX"
    format_description = "Paintbrush"

    def _open(self) -> None:
        # header
        assert self.fp is not None

        s = self.fp.read(128)
        if not _accept(s):
            msg = "not a PCX file"
            raise SyntaxError(msg)

        # image
        bbox = i16(s, 4), i16(s, 6), i16(s, 8) + 1, i16(s, 10) + 1
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            msg = "bad PCX image size"
            raise SyntaxError(msg)
        logger.debug("BBox: %s %s %s %s", *bbox)

        # format
        version = s[1]
        bits = s[3]
        planes = s[65]
        provided_stride = i16(s, 66)
        logger.debug(
            "PCX version %s, bits %s, planes %s, stride %s",
            version,
            bits,
            planes,
            provided_stride,
        )

        self.info["dpi"] = i16(s, 12), i16(s, 14)

        if bits == 1 and planes == 1:
            mode = rawmode = "1"

        elif bits == 1 and planes in (2, 4):
            mode = "P"
            rawmode = f"P;{planes}L"
            self.palette = ImagePalette.raw("RGB", s[16:64])

        elif version == 5 and bits == 8 and planes == 1:
            mode = rawmode = "L"
            # FIXME: hey, this doesn't work with the incremental loader !!!
            self.fp.seek(-769, io.SEEK_END)
            s = self.fp.read(769)
            if len(s) == 769 and s[0] == 12:
                # check if the palette is linear grayscale
                for i in range(256):
                    if s[i * 3 + 1 : i * 3 + 4] != o8(i) * 3:
                        mode = rawmode = "P"
                        break
                if mode == "P":
                    self.palette = ImagePalette.raw("RGB", s[1:])
            self.fp.seek(128)

        elif version == 5 and bits == 8 and planes == 3:
            mode = "RGB"
            rawmode = "RGB;L"

        else:
            msg = "unknown PCX mode"
            raise OSError(msg)

        self._mode = mode
        self._size = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # Don't trust the passed in stride.
        # Calculate the approximate position for ourselves.
        # CVE-2020-35653
        stride = (self._size[0] * bits + 7) // 8

        # While the specification states that this must be even,
        # not all images follow this
        if provided_stride != stride:
            stride += stride % 2

        bbox = (0, 0) + self.size
        logger.debug("size: %sx%s", *self.size)

        self.tile = [
            ImageFile._Tile("pcx", bbox, self.fp.tell(), (rawmode, planes * stride))
        ]


# --------------------------------------------------------------------
# save PCX files


SAVE = {
    # mode: (version, bits, planes, raw mode)
    "1": (2, 1, 1, "1"),
    "L": (5, 8, 1, "L"),
    "P": (5, 8, 1, "P"),
    "RGB": (5, 8, 3, "RGB;L"),
}


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    try:
        version, bits, planes, rawmode = SAVE[im.mode]
    except KeyError as e:
        msg = f"Cannot save {im.mode} images as PCX"
        raise ValueError(msg) from e

    # bytes per plane
    stride = (im.size[0] * bits + 7) // 8
    # stride should be even
    stride += stride % 2
    # Stride needs to be kept in sync with the PcxEncode.c version.
    # Ideally it should be passed in in the state, but the bytes value
    # gets overwritten.

    logger.debug(
        "PcxImagePlugin._save: xwidth: %d, bits: %d, stride: %d",
        im.size[0],
        bits,
        stride,
    )

    # under windows, we could determine the current screen size with
    # "Image.core.display_mode()[1]", but I think that's overkill...

    screen = im.size

    dpi = 100, 100

    # PCX header
    fp.write(
        o8(10)
        + o8(version)
        + o8(1)
        + o8(bits)
        + o16(0)
        + o16(0)
        + o16(im.size[0] - 1)
        + o16(im.size[1] - 1)
        + o16(dpi[0])
        + o16(dpi[1])
        + b"\0" * 24
        + b"\xff" * 24
        + b"\0"
        + o8(planes)
        + o16(stride)
        + o16(1)
        + o16(screen[0])
        + o16(screen[1])
        + b"\0" * 54
    )

    assert fp.tell() == 128

    ImageFile._save(
        im, fp, [ImageFile._Tile("pcx", (0, 0) + im.size, 0, (rawmode, bits * planes))]
    )

    if im.mode == "P":
        # colour palette
        fp.write(o8(12))
        palette = im.im.getpalette("RGB", "RGB")
        palette += b"\x00" * (768 - len(palette))
        fp.write(palette)  # 768 bytes
    elif im.mode == "L":
        # grayscale palette
        fp.write(o8(12))
        for i in range(256):
            fp.write(o8(i) * 3)


# --------------------------------------------------------------------
# registry


Image.register_open(PcxImageFile.format, PcxImageFile, _accept)
Image.register_save(PcxImageFile.format, _save)

Image.register_extension(PcxImageFile.format, ".pcx")

Image.register_mime(PcxImageFile.format, "image/x-pcx")

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\win32_types.py ===
from __future__ import annotations

from ctypes import Structure, Union, c_char, c_long, c_short, c_ulong
from ctypes.wintypes import BOOL, DWORD, LPVOID, WCHAR, WORD
from typing import TYPE_CHECKING

# Input/Output standard device numbers. Note that these are not handle objects.
# It's the `windll.kernel32.GetStdHandle` system call that turns them into a
# real handle object.
STD_INPUT_HANDLE = c_ulong(-10)
STD_OUTPUT_HANDLE = c_ulong(-11)
STD_ERROR_HANDLE = c_ulong(-12)


class COORD(Structure):
    """
    Struct in wincon.h
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms682119(v=vs.85).aspx
    """

    if TYPE_CHECKING:
        X: int
        Y: int

    _fields_ = [
        ("X", c_short),  # Short
        ("Y", c_short),  # Short
    ]

    def __repr__(self) -> str:
        return "{}(X={!r}, Y={!r}, type_x={!r}, type_y={!r})".format(
            self.__class__.__name__,
            self.X,
            self.Y,
            type(self.X),
            type(self.Y),
        )


class UNICODE_OR_ASCII(Union):
    if TYPE_CHECKING:
        AsciiChar: bytes
        UnicodeChar: str

    _fields_ = [
        ("AsciiChar", c_char),
        ("UnicodeChar", WCHAR),
    ]


class KEY_EVENT_RECORD(Structure):
    """
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms684166(v=vs.85).aspx
    """

    if TYPE_CHECKING:
        KeyDown: int
        RepeatCount: int
        VirtualKeyCode: int
        VirtualScanCode: int
        uChar: UNICODE_OR_ASCII
        ControlKeyState: int

    _fields_ = [
        ("KeyDown", c_long),  # bool
        ("RepeatCount", c_short),  # word
        ("VirtualKeyCode", c_short),  # word
        ("VirtualScanCode", c_short),  # word
        ("uChar", UNICODE_OR_ASCII),  # Unicode or ASCII.
        ("ControlKeyState", c_long),  # double word
    ]


class MOUSE_EVENT_RECORD(Structure):
    """
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms684239(v=vs.85).aspx
    """

    if TYPE_CHECKING:
        MousePosition: COORD
        ButtonState: int
        ControlKeyState: int
        EventFlags: int

    _fields_ = [
        ("MousePosition", COORD),
        ("ButtonState", c_long),  # dword
        ("ControlKeyState", c_long),  # dword
        ("EventFlags", c_long),  # dword
    ]


class WINDOW_BUFFER_SIZE_RECORD(Structure):
    """
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms687093(v=vs.85).aspx
    """

    if TYPE_CHECKING:
        Size: COORD

    _fields_ = [("Size", COORD)]


class MENU_EVENT_RECORD(Structure):
    """
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms684213(v=vs.85).aspx
    """

    if TYPE_CHECKING:
        CommandId: int

    _fields_ = [("CommandId", c_long)]  # uint


class FOCUS_EVENT_RECORD(Structure):
    """
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms683149(v=vs.85).aspx
    """

    if TYPE_CHECKING:
        SetFocus: int

    _fields_ = [("SetFocus", c_long)]  # bool


class EVENT_RECORD(Union):
    if TYPE_CHECKING:
        KeyEvent: KEY_EVENT_RECORD
        MouseEvent: MOUSE_EVENT_RECORD
        WindowBufferSizeEvent: WINDOW_BUFFER_SIZE_RECORD
        MenuEvent: MENU_EVENT_RECORD
        FocusEvent: FOCUS_EVENT_RECORD

    _fields_ = [
        ("KeyEvent", KEY_EVENT_RECORD),
        ("MouseEvent", MOUSE_EVENT_RECORD),
        ("WindowBufferSizeEvent", WINDOW_BUFFER_SIZE_RECORD),
        ("MenuEvent", MENU_EVENT_RECORD),
        ("FocusEvent", FOCUS_EVENT_RECORD),
    ]


class INPUT_RECORD(Structure):
    """
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms683499(v=vs.85).aspx
    """

    if TYPE_CHECKING:
        EventType: int
        Event: EVENT_RECORD

    _fields_ = [("EventType", c_short), ("Event", EVENT_RECORD)]  # word  # Union.


EventTypes = {
    1: "KeyEvent",
    2: "MouseEvent",
    4: "WindowBufferSizeEvent",
    8: "MenuEvent",
    16: "FocusEvent",
}


class SMALL_RECT(Structure):
    """struct in wincon.h."""

    if TYPE_CHECKING:
        Left: int
        Top: int
        Right: int
        Bottom: int

    _fields_ = [
        ("Left", c_short),
        ("Top", c_short),
        ("Right", c_short),
        ("Bottom", c_short),
    ]


class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    """struct in wincon.h."""

    if TYPE_CHECKING:
        dwSize: COORD
        dwCursorPosition: COORD
        wAttributes: int
        srWindow: SMALL_RECT
        dwMaximumWindowSize: COORD

    _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", WORD),
        ("srWindow", SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]

    def __repr__(self) -> str:
        return "CONSOLE_SCREEN_BUFFER_INFO({!r},{!r},{!r},{!r},{!r},{!r},{!r},{!r},{!r},{!r},{!r})".format(
            self.dwSize.Y,
            self.dwSize.X,
            self.dwCursorPosition.Y,
            self.dwCursorPosition.X,
            self.wAttributes,
            self.srWindow.Top,
            self.srWindow.Left,
            self.srWindow.Bottom,
            self.srWindow.Right,
            self.dwMaximumWindowSize.Y,
            self.dwMaximumWindowSize.X,
        )


class SECURITY_ATTRIBUTES(Structure):
    """
    http://msdn.microsoft.com/en-us/library/windows/desktop/aa379560(v=vs.85).aspx
    """

    if TYPE_CHECKING:
        nLength: int
        lpSecurityDescriptor: int
        bInheritHandle: int  # BOOL comes back as 'int'.

    _fields_ = [
        ("nLength", DWORD),
        ("lpSecurityDescriptor", LPVOID),
        ("bInheritHandle", BOOL),
    ]

# === NexusCore/openenv\Lib\site-packages\zmq\error.py ===
"""0MQ Error classes and functions."""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from errno import EINTR


class DraftFDWarning(RuntimeWarning):
    """Warning for using experimental FD on draft sockets.

    .. versionadded:: 27
    """

    def __init__(self, msg=""):
        if not msg:
            msg = (
                "pyzmq's back-fill socket.FD support on thread-safe sockets is experimental, and may be removed."
                " This warning will go away automatically if/when libzmq implements socket.FD on thread-safe sockets."
                " You can suppress this warning with `warnings.simplefilter('ignore', zmq.error.DraftFDWarning)"
            )
        super().__init__(msg)


class ZMQBaseError(Exception):
    """Base exception class for 0MQ errors in Python."""


class ZMQError(ZMQBaseError):
    """Wrap an errno style error.

    Parameters
    ----------
    errno : int
        The ZMQ errno or None.  If None, then ``zmq_errno()`` is called and
        used.
    msg : str
        Description of the error or None.
    """

    errno: int | None = None
    strerror: str

    def __init__(self, errno: int | None = None, msg: str | None = None):
        """Wrap an errno style error.

        Parameters
        ----------
        errno : int
            The ZMQ errno or None.  If None, then ``zmq_errno()`` is called and
            used.
        msg : string
            Description of the error or None.
        """
        from zmq.backend import strerror, zmq_errno

        if errno is None:
            errno = zmq_errno()
        if isinstance(errno, int):
            self.errno = errno
            if msg is None:
                self.strerror = strerror(errno)
            else:
                self.strerror = msg
        else:
            if msg is None:
                self.strerror = str(errno)
            else:
                self.strerror = msg
        # flush signals, because there could be a SIGINT
        # waiting to pounce, resulting in uncaught exceptions.
        # Doing this here means getting SIGINT during a blocking
        # libzmq call will raise a *catchable* KeyboardInterrupt
        # PyErr_CheckSignals()

    def __str__(self) -> str:
        return self.strerror

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{str(self)}')"


class ZMQBindError(ZMQBaseError):
    """An error for ``Socket.bind_to_random_port()``.

    See Also
    --------
    .Socket.bind_to_random_port
    """


class NotDone(ZMQBaseError):
    """Raised when timeout is reached while waiting for 0MQ to finish with a Message

    See Also
    --------
    .MessageTracker.wait : object for tracking when ZeroMQ is done
    """


class ContextTerminated(ZMQError):
    """Wrapper for zmq.ETERM

    .. versionadded:: 13.0
    """

    def __init__(self, errno="ignored", msg="ignored"):
        from zmq import ETERM

        super().__init__(ETERM)


class Again(ZMQError):
    """Wrapper for zmq.EAGAIN

    .. versionadded:: 13.0
    """

    def __init__(self, errno="ignored", msg="ignored"):
        from zmq import EAGAIN

        super().__init__(EAGAIN)


class InterruptedSystemCall(ZMQError, InterruptedError):
    """Wrapper for EINTR

    This exception should be caught internally in pyzmq
    to retry system calls, and not propagate to the user.

    .. versionadded:: 14.7
    """

    errno = EINTR
    strerror: str

    def __init__(self, errno="ignored", msg="ignored"):
        super().__init__(EINTR)

    def __str__(self):
        s = super().__str__()
        return s + ": This call should have been retried. Please report this to pyzmq."


def _check_rc(rc, errno=None, error_without_errno=True):
    """internal utility for checking zmq return condition

    and raising the appropriate Exception class
    """
    if rc == -1:
        if errno is None:
            from zmq.backend import zmq_errno

            errno = zmq_errno()
        if errno == 0 and not error_without_errno:
            return
        from zmq import EAGAIN, ETERM

        if errno == EINTR:
            raise InterruptedSystemCall(errno)
        elif errno == EAGAIN:
            raise Again(errno)
        elif errno == ETERM:
            raise ContextTerminated(errno)
        else:
            raise ZMQError(errno)


_zmq_version_info = None
_zmq_version = None


class ZMQVersionError(NotImplementedError):
    """Raised when a feature is not provided by the linked version of libzmq.

    .. versionadded:: 14.2
    """

    min_version = None

    def __init__(self, min_version: str, msg: str = "Feature"):
        global _zmq_version
        if _zmq_version is None:
            from zmq import zmq_version

            _zmq_version = zmq_version()
        self.msg = msg
        self.min_version = min_version
        self.version = _zmq_version

    def __repr__(self):
        return f"ZMQVersionError('{str(self)}')"

    def __str__(self):
        return f"{self.msg} requires libzmq >= {self.min_version}, have {self.version}"


def _check_version(
    min_version_info: tuple[int] | tuple[int, int] | tuple[int, int, int],
    msg: str = "Feature",
):
    """Check for libzmq

    raises ZMQVersionError if current zmq version is not at least min_version

    min_version_info is a tuple of integers, and will be compared against zmq.zmq_version_info().
    """
    global _zmq_version_info
    if _zmq_version_info is None:
        from zmq import zmq_version_info

        _zmq_version_info = zmq_version_info()
    if _zmq_version_info < min_version_info:
        min_version = ".".join(str(v) for v in min_version_info)
        raise ZMQVersionError(min_version, msg)


__all__ = [
    "DraftFDWarning",
    "ZMQBaseError",
    "ZMQBindError",
    "ZMQError",
    "NotDone",
    "ContextTerminated",
    "InterruptedSystemCall",
    "Again",
    "ZMQVersionError",
]

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\plaintext.py ===
# Natural Language Toolkit: Plaintext Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
#         Nitin Madnani <nmadnani@umiacs.umd.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A reader for corpora that consist of plaintext documents.
"""

import nltk.data
from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *
from nltk.tokenize import *


class PlaintextCorpusReader(CorpusReader):
    """
    Reader for corpora that consist of plaintext documents.  Paragraphs
    are assumed to be split using blank lines.  Sentences and words can
    be tokenized using the default tokenizers, or by custom tokenizers
    specified as parameters to the constructor.

    This corpus reader can be customized (e.g., to skip preface
    sections of specific document formats) by creating a subclass and
    overriding the ``CorpusView`` class variable.
    """

    CorpusView = StreamBackedCorpusView
    """The corpus view class used by this reader.  Subclasses of
       ``PlaintextCorpusReader`` may specify alternative corpus view
       classes (e.g., to skip the preface sections of documents.)"""

    def __init__(
        self,
        root,
        fileids,
        word_tokenizer=WordPunctTokenizer(),
        sent_tokenizer=None,
        para_block_reader=read_blankline_block,
        encoding="utf8",
    ):
        r"""
        Construct a new plaintext corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/usr/local/share/nltk_data/corpora/webtext/'
            >>> reader = PlaintextCorpusReader(root, '.*\.txt') # doctest: +SKIP

        :param root: The root directory for this corpus.
        :param fileids: A list or regexp specifying the fileids in this corpus.
        :param word_tokenizer: Tokenizer for breaking sentences or
            paragraphs into words.
        :param sent_tokenizer: Tokenizer for breaking paragraphs
            into words.
        :param para_block_reader: The block reader used to divide the
            corpus into paragraph blocks.
        """
        CorpusReader.__init__(self, root, fileids, encoding)
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader

    def words(self, fileids=None):
        """
        :return: the given file(s) as a list of words
            and punctuation symbols.
        :rtype: list(str)
        """
        return concat(
            [
                self.CorpusView(path, self._read_word_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

    def sents(self, fileids=None):
        """
        :return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        :rtype: list(list(str))
        """
        if self._sent_tokenizer is None:
            try:
                self._sent_tokenizer = PunktTokenizer()
            except:
                raise ValueError("No sentence tokenizer for this corpus")

        return concat(
            [
                self.CorpusView(path, self._read_sent_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

    def paras(self, fileids=None):
        """
        :return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        :rtype: list(list(list(str)))
        """
        if self._sent_tokenizer is None:
            try:
                self._sent_tokenizer = PunktTokenizer()
            except:
                raise ValueError("No sentence tokenizer for this corpus")

        return concat(
            [
                self.CorpusView(path, self._read_para_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

    def _read_word_block(self, stream):
        words = []
        for i in range(20):  # Read 20 lines at a time.
            words.extend(self._word_tokenizer.tokenize(stream.readline()))
        return words

    def _read_sent_block(self, stream):
        sents = []
        for para in self._para_block_reader(stream):
            sents.extend(
                [
                    self._word_tokenizer.tokenize(sent)
                    for sent in self._sent_tokenizer.tokenize(para)
                ]
            )
        return sents

    def _read_para_block(self, stream):
        paras = []
        for para in self._para_block_reader(stream):
            paras.append(
                [
                    self._word_tokenizer.tokenize(sent)
                    for sent in self._sent_tokenizer.tokenize(para)
                ]
            )
        return paras


class CategorizedPlaintextCorpusReader(CategorizedCorpusReader, PlaintextCorpusReader):
    """
    A reader for plaintext corpora whose documents are divided into
    categories based on their file identifiers.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the corpus reader.  Categorization arguments
        (``cat_pattern``, ``cat_map``, and ``cat_file``) are passed to
        the ``CategorizedCorpusReader`` constructor.  The remaining arguments
        are passed to the ``PlaintextCorpusReader`` constructor.
        """
        CategorizedCorpusReader.__init__(self, kwargs)
        PlaintextCorpusReader.__init__(self, *args, **kwargs)


# FIXME: Is there a better way? How to not hardcode this?
#       Possibly, add a language kwargs to CategorizedPlaintextCorpusReader to
#       override the `sent_tokenizer`.
class PortugueseCategorizedPlaintextCorpusReader(CategorizedPlaintextCorpusReader):
    def __init__(self, *args, **kwargs):
        CategorizedCorpusReader.__init__(self, kwargs)
        kwargs["sent_tokenizer"] = PunktTokenizer("portuguese")


class EuroparlCorpusReader(PlaintextCorpusReader):
    """
    Reader for Europarl corpora that consist of plaintext documents.
    Documents are divided into chapters instead of paragraphs as
    for regular plaintext documents. Chapters are separated using blank
    lines. Everything is inherited from ``PlaintextCorpusReader`` except
    that:

    - Since the corpus is pre-processed and pre-tokenized, the
      word tokenizer should just split the line at whitespaces.
    - For the same reason, the sentence tokenizer should just
      split the paragraph at line breaks.
    - There is a new 'chapters()' method that returns chapters instead
      instead of paragraphs.
    - The 'paras()' method inherited from PlaintextCorpusReader is
      made non-functional to remove any confusion between chapters
      and paragraphs for Europarl.
    """

    def _read_word_block(self, stream):
        words = []
        for i in range(20):  # Read 20 lines at a time.
            words.extend(stream.readline().split())
        return words

    def _read_sent_block(self, stream):
        sents = []
        for para in self._para_block_reader(stream):
            sents.extend([sent.split() for sent in para.splitlines()])
        return sents

    def _read_para_block(self, stream):
        paras = []
        for para in self._para_block_reader(stream):
            paras.append([sent.split() for sent in para.splitlines()])
        return paras

    def chapters(self, fileids=None):
        """
        :return: the given file(s) as a list of
            chapters, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        :rtype: list(list(list(str)))
        """
        return concat(
            [
                self.CorpusView(fileid, self._read_para_block, encoding=enc)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def paras(self, fileids=None):
        raise NotImplementedError(
            "The Europarl corpus reader does not support paragraphs. Please use chapters() instead."
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\firefox\webdriver.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import base64
import os
import warnings
import zipfile
from contextlib import contextmanager
from io import BytesIO
from typing import Optional

from selenium.webdriver.common.driver_finder import DriverFinder
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

from .options import Options
from .remote_connection import FirefoxRemoteConnection
from .service import Service


class WebDriver(RemoteWebDriver):
    """Controls the GeckoDriver and allows you to drive the browser."""

    CONTEXT_CHROME = "chrome"
    CONTEXT_CONTENT = "content"

    def __init__(
        self,
        options: Optional[Options] = None,
        service: Optional[Service] = None,
        keep_alive: bool = True,
    ) -> None:
        """Creates a new instance of the Firefox driver. Starts the service and
        then creates new instance of Firefox driver.

        :Args:
         - options - Instance of ``options.Options``.
         - service - (Optional) service instance for managing the starting and stopping of the driver.
         - keep_alive - Whether to configure remote_connection.RemoteConnection to use HTTP keep-alive.
        """

        self.service = service if service else Service()
        options = options if options else Options()

        finder = DriverFinder(self.service, options)
        if finder.get_browser_path():
            options.binary_location = finder.get_browser_path()
            options.browser_version = None

        self.service.path = self.service.env_path() or finder.get_driver_path()
        self.service.start()

        executor = FirefoxRemoteConnection(
            remote_server_addr=self.service.service_url,
            keep_alive=keep_alive,
            ignore_proxy=options._ignore_local_proxy,
        )

        try:
            super().__init__(command_executor=executor, options=options)
        except Exception:
            self.quit()
            raise

        self._is_remote = False

    def quit(self) -> None:
        """Closes the browser and shuts down the GeckoDriver executable."""
        try:
            super().quit()
        except Exception:
            # We don't care about the message because something probably has gone wrong
            pass
        finally:
            self.service.stop()

    def set_context(self, context) -> None:
        self.execute("SET_CONTEXT", {"context": context})

    @contextmanager
    def context(self, context):
        """Sets the context that Selenium commands are running in using a
        `with` statement. The state of the context on the server is saved
        before entering the block, and restored upon exiting it.

        :param context: Context, may be one of the class properties
            `CONTEXT_CHROME` or `CONTEXT_CONTENT`.

        Usage example::

            with selenium.context(selenium.CONTEXT_CHROME):
                # chrome scope
                ... do stuff ...
        """
        initial_context = self.execute("GET_CONTEXT").pop("value")
        self.set_context(context)
        try:
            yield
        finally:
            self.set_context(initial_context)

    def install_addon(self, path, temporary=False) -> str:
        """Installs Firefox addon.

        Returns identifier of installed addon. This identifier can later
        be used to uninstall addon.

        :param temporary: allows you to load browser extensions temporarily during a session
        :param path: Absolute path to the addon that will be installed.

        :Usage:
            ::

                driver.install_addon("/path/to/firebug.xpi")
        """

        if os.path.isdir(path):
            fp = BytesIO()
            # filter all trailing slash found in path
            path = os.path.normpath(path)
            # account for trailing slash that will be added by os.walk()
            path_root = len(path) + 1
            with zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as zipped:
                for base, _, files in os.walk(path):
                    for fyle in files:
                        filename = os.path.join(base, fyle)
                        zipped.write(filename, filename[path_root:])
            addon = base64.b64encode(fp.getvalue()).decode("UTF-8")
        else:
            with open(path, "rb") as file:
                addon = base64.b64encode(file.read()).decode("UTF-8")

        payload = {"addon": addon, "temporary": temporary}
        return self.execute("INSTALL_ADDON", payload)["value"]

    def uninstall_addon(self, identifier) -> None:
        """Uninstalls Firefox addon using its identifier.

        :Usage:
            ::

                driver.uninstall_addon("addon@foo.com")
        """
        self.execute("UNINSTALL_ADDON", {"id": identifier})

    def get_full_page_screenshot_as_file(self, filename) -> bool:
        """Saves a full document screenshot of the current window to a PNG
        image file. Returns False if there is any IOError, else returns True.
        Use full paths in your filename.

        :Args:
         - filename: The full path you wish to save your screenshot to. This
           should end with a `.png` extension.

        :Usage:
            ::

                driver.get_full_page_screenshot_as_file("/Screenshots/foo.png")
        """
        if not filename.lower().endswith(".png"):
            warnings.warn(
                "name used for saved screenshot does not match file type. It should end with a `.png` extension",
                UserWarning,
            )
        png = self.get_full_page_screenshot_as_png()
        try:
            with open(filename, "wb") as f:
                f.write(png)
        except OSError:
            return False
        finally:
            del png
        return True

    def save_full_page_screenshot(self, filename) -> bool:
        """Saves a full document screenshot of the current window to a PNG
        image file. Returns False if there is any IOError, else returns True.
        Use full paths in your filename.

        :Args:
         - filename: The full path you wish to save your screenshot to. This
           should end with a `.png` extension.

        :Usage:
            ::

                driver.save_full_page_screenshot("/Screenshots/foo.png")
        """
        return self.get_full_page_screenshot_as_file(filename)

    def get_full_page_screenshot_as_png(self) -> bytes:
        """Gets the full document screenshot of the current window as a binary
        data.

        :Usage:
            ::

                driver.get_full_page_screenshot_as_png()
        """
        return base64.b64decode(self.get_full_page_screenshot_as_base64().encode("ascii"))

    def get_full_page_screenshot_as_base64(self) -> str:
        """Gets the full document screenshot of the current window as a base64
        encoded string which is useful in embedded images in HTML.

        :Usage:
            ::

                driver.get_full_page_screenshot_as_base64()
        """
        return self.execute("FULL_PAGE_SCREENSHOT")["value"]

    def download_file(self, *args, **kwargs):
        raise NotImplementedError

    def get_downloadable_files(self, *args, **kwargs):
        raise NotImplementedError

# === NexusCore/openenv\Lib\site-packages\trio\_tests\type_tests\raisesgroup.py ===
from __future__ import annotations

import sys
from typing import Callable, Union

from trio.testing import Matcher, RaisesGroup
from typing_extensions import assert_type

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup

# split into functions to isolate the different scopes


def check_matcher_typevar_default(e: Matcher) -> None:
    assert e.exception_type is not None
    _exc: type[BaseException] = e.exception_type
    # this would previously pass, as the type would be `Any`
    e.exception_type().blah()  # type: ignore


def check_basic_contextmanager() -> None:
    with RaisesGroup(ValueError) as e:
        raise ExceptionGroup("foo", (ValueError(),))
    assert_type(e.value, ExceptionGroup[ValueError])


def check_basic_matches() -> None:
    # check that matches gets rid of the naked ValueError in the union
    exc: ExceptionGroup[ValueError] | ValueError = ExceptionGroup("", (ValueError(),))
    if RaisesGroup(ValueError).matches(exc):
        assert_type(exc, ExceptionGroup[ValueError])

    # also check that BaseExceptionGroup shows up for BaseExceptions
    if RaisesGroup(KeyboardInterrupt).matches(exc):
        assert_type(exc, BaseExceptionGroup[KeyboardInterrupt])


def check_matches_with_different_exception_type() -> None:
    e: BaseExceptionGroup[KeyboardInterrupt] = BaseExceptionGroup(
        "",
        (KeyboardInterrupt(),),
    )

    # note: it might be tempting to have this warn.
    # however, that isn't possible with current typing
    if RaisesGroup(ValueError).matches(e):
        assert_type(e, ExceptionGroup[ValueError])


def check_matcher_init() -> None:
    def check_exc(exc: BaseException) -> bool:
        return isinstance(exc, ValueError)

    # Check various combinations of constructor signatures.
    # At least 1 arg must be provided.
    Matcher()  # type: ignore
    Matcher(ValueError)
    Matcher(ValueError, "regex")
    Matcher(ValueError, "regex", check_exc)
    Matcher(exception_type=ValueError)
    Matcher(match="regex")
    Matcher(check=check_exc)
    Matcher(ValueError, match="regex")
    Matcher(match="regex", check=check_exc)

    def check_filenotfound(exc: FileNotFoundError) -> bool:
        return not exc.filename.endswith(".tmp")

    # If exception_type is provided, that narrows the `check` method's argument.
    Matcher(FileNotFoundError, check=check_filenotfound)
    Matcher(ValueError, check=check_filenotfound)  # type: ignore
    Matcher(check=check_filenotfound)  # type: ignore
    Matcher(FileNotFoundError, match="regex", check=check_filenotfound)


def raisesgroup_check_type_narrowing() -> None:
    """Check type narrowing on the `check` argument to `RaisesGroup`.
    All `type: ignore`s are correctly pointing out type errors.
    """

    def handle_exc(e: BaseExceptionGroup[BaseException]) -> bool:
        return True

    def handle_kbi(e: BaseExceptionGroup[KeyboardInterrupt]) -> bool:
        return True

    def handle_value(e: BaseExceptionGroup[ValueError]) -> bool:
        return True

    RaisesGroup(BaseException, check=handle_exc)
    RaisesGroup(BaseException, check=handle_kbi)  # type: ignore

    RaisesGroup(Exception, check=handle_exc)
    RaisesGroup(Exception, check=handle_value)  # type: ignore

    RaisesGroup(KeyboardInterrupt, check=handle_exc)
    RaisesGroup(KeyboardInterrupt, check=handle_kbi)
    RaisesGroup(KeyboardInterrupt, check=handle_value)  # type: ignore

    RaisesGroup(ValueError, check=handle_exc)
    RaisesGroup(ValueError, check=handle_kbi)  # type: ignore
    RaisesGroup(ValueError, check=handle_value)

    RaisesGroup(ValueError, KeyboardInterrupt, check=handle_exc)
    RaisesGroup(ValueError, KeyboardInterrupt, check=handle_kbi)  # type: ignore
    RaisesGroup(ValueError, KeyboardInterrupt, check=handle_value)  # type: ignore


def raisesgroup_narrow_baseexceptiongroup() -> None:
    """Check type narrowing specifically for the container exceptiongroup."""

    def handle_group(e: ExceptionGroup[Exception]) -> bool:
        return True

    def handle_group_value(e: ExceptionGroup[ValueError]) -> bool:
        return True

    RaisesGroup(ValueError, check=handle_group_value)

    RaisesGroup(Exception, check=handle_group)


def check_matcher_transparent() -> None:
    with RaisesGroup(Matcher(ValueError)) as e:
        ...
    _: BaseExceptionGroup[ValueError] = e.value
    assert_type(e.value, ExceptionGroup[ValueError])


def check_nested_raisesgroups_contextmanager() -> None:
    with RaisesGroup(RaisesGroup(ValueError)) as excinfo:
        raise ExceptionGroup("foo", (ValueError(),))

    _: BaseExceptionGroup[BaseExceptionGroup[ValueError]] = excinfo.value

    assert_type(
        excinfo.value,
        ExceptionGroup[ExceptionGroup[ValueError]],
    )

    assert_type(
        excinfo.value.exceptions[0],
        # this union is because of how typeshed defines .exceptions
        Union[
            ExceptionGroup[ValueError],
            ExceptionGroup[ExceptionGroup[ValueError]],
        ],
    )


def check_nested_raisesgroups_matches() -> None:
    """Check nested RaisesGroups with .matches"""
    exc: ExceptionGroup[ExceptionGroup[ValueError]] = ExceptionGroup(
        "",
        (ExceptionGroup("", (ValueError(),)),),
    )

    if RaisesGroup(RaisesGroup(ValueError)).matches(exc):
        assert_type(exc, ExceptionGroup[ExceptionGroup[ValueError]])


def check_multiple_exceptions_1() -> None:
    a = RaisesGroup(ValueError, ValueError)
    b = RaisesGroup(Matcher(ValueError), Matcher(ValueError))
    c = RaisesGroup(ValueError, Matcher(ValueError))

    d: RaisesGroup[ValueError]
    d = a
    d = b
    d = c
    assert isinstance(d, RaisesGroup)


def check_multiple_exceptions_2() -> None:
    # This previously failed due to lack of covariance in the TypeVar
    a = RaisesGroup(Matcher(ValueError), Matcher(TypeError))
    b = RaisesGroup(Matcher(ValueError), TypeError)
    c = RaisesGroup(ValueError, TypeError)

    d: RaisesGroup[Exception]
    d = a
    d = b
    d = c
    assert isinstance(d, RaisesGroup)


def check_raisesgroup_overloads() -> None:
    # allow_unwrapped=True does not allow:
    # multiple exceptions
    RaisesGroup(ValueError, TypeError, allow_unwrapped=True)  # type: ignore
    # nested RaisesGroup
    RaisesGroup(RaisesGroup(ValueError), allow_unwrapped=True)  # type: ignore
    # specifying match
    RaisesGroup(ValueError, match="foo", allow_unwrapped=True)  # type: ignore
    # specifying check
    RaisesGroup(ValueError, check=bool, allow_unwrapped=True)  # type: ignore
    # allowed variants
    RaisesGroup(ValueError, allow_unwrapped=True)
    RaisesGroup(ValueError, allow_unwrapped=True, flatten_subgroups=True)
    RaisesGroup(Matcher(ValueError), allow_unwrapped=True)

    # flatten_subgroups=True does not allow nested RaisesGroup
    RaisesGroup(RaisesGroup(ValueError), flatten_subgroups=True)  # type: ignore
    # but rest is plenty fine
    RaisesGroup(ValueError, TypeError, flatten_subgroups=True)
    RaisesGroup(ValueError, match="foo", flatten_subgroups=True)
    RaisesGroup(ValueError, check=bool, flatten_subgroups=True)
    RaisesGroup(ValueError, flatten_subgroups=True)
    RaisesGroup(Matcher(ValueError), flatten_subgroups=True)

    # if they're both false we can of course specify nested raisesgroup
    RaisesGroup(RaisesGroup(ValueError))


def check_triple_nested_raisesgroup() -> None:
    with RaisesGroup(RaisesGroup(RaisesGroup(ValueError))) as e:
        assert_type(e.value, ExceptionGroup[ExceptionGroup[ExceptionGroup[ValueError]]])


def check_check_typing() -> None:
    # `BaseExceptiongroup` should perhaps be `ExceptionGroup`, but close enough
    assert_type(
        RaisesGroup(ValueError).check,
        Union[
            Callable[[BaseExceptionGroup[ValueError]], bool],
            None,
        ],
    )

# === NexusCore/openenv\Lib\site-packages\win32\test\test_sspi.py ===
# Some tests of the win32security sspi functions.
# Stolen from Roger's original test_sspi.c, a version of which is in "Demos"
# See also the other SSPI demos.
import unittest

import sspi
import sspicon
import win32api
import win32security
from pywin32_testutil import TestSkipped, testmain


# It is quite likely that the Kerberos tests will fail due to not being
# installed.  The NTLM tests do *not* get the same behaviour as they should
# always be there.
def applyHandlingSkips(func, *args):
    try:
        return func(*args)
    except win32api.error as exc:
        if exc.winerror in [
            sspicon.SEC_E_NO_CREDENTIALS,
            sspicon.SEC_E_NO_AUTHENTICATING_AUTHORITY,
        ]:
            raise TestSkipped(exc)
        raise


class TestSSPI(unittest.TestCase):
    def assertRaisesHRESULT(self, hr, func, *args):
        try:
            func(*args)
            raise AssertionError(f"expecting {hr} failure")
        except win32security.error as exc:
            self.assertEqual(exc.winerror, hr)

    def _doAuth(self, pkg_name):
        sspiclient = sspi.ClientAuth(pkg_name, targetspn=win32api.GetUserName())
        sspiserver = sspi.ServerAuth(pkg_name)

        sec_buffer = None
        err = 1
        while err != 0:
            err, sec_buffer = sspiclient.authorize(sec_buffer)
            err, sec_buffer = sspiserver.authorize(sec_buffer)
        return sspiclient, sspiserver

    def _doTestImpersonate(self, pkg_name):
        # Just for the sake of code exercising!
        sspiclient, sspiserver = self._doAuth(pkg_name)
        sspiserver.ctxt.ImpersonateSecurityContext()
        sspiserver.ctxt.RevertSecurityContext()

    def testImpersonateKerberos(self):
        applyHandlingSkips(self._doTestImpersonate, "Kerberos")

    def testImpersonateNTLM(self):
        self._doTestImpersonate("NTLM")

    def _doTestEncrypt(self, pkg_name):
        sspiclient, sspiserver = self._doAuth(pkg_name)

        pkg_size_info = sspiclient.ctxt.QueryContextAttributes(
            sspicon.SECPKG_ATTR_SIZES
        )
        msg = b"some data to be encrypted ......"

        trailersize = pkg_size_info["SecurityTrailer"]
        encbuf = win32security.PySecBufferDescType()
        encbuf.append(win32security.PySecBufferType(len(msg), sspicon.SECBUFFER_DATA))
        encbuf.append(
            win32security.PySecBufferType(trailersize, sspicon.SECBUFFER_TOKEN)
        )
        encbuf[0].Buffer = msg
        sspiclient.ctxt.EncryptMessage(0, encbuf, 1)
        sspiserver.ctxt.DecryptMessage(encbuf, 1)
        self.assertEqual(msg, encbuf[0].Buffer)
        # and test the higher-level functions
        data_in = b"hello"
        data, sig = sspiclient.encrypt(data_in)
        self.assertEqual(sspiserver.decrypt(data, sig), data_in)

        data, sig = sspiserver.encrypt(data_in)
        self.assertEqual(sspiclient.decrypt(data, sig), data_in)

    def _doTestEncryptStream(self, pkg_name):
        # Test out the SSPI/GSSAPI interop wrapping examples at
        # https://learn.microsoft.com/en-us/windows/win32/secauthn/sspi-kerberos-interoperability-with-gssapi

        sspiclient, sspiserver = self._doAuth(pkg_name)

        pkg_size_info = sspiclient.ctxt.QueryContextAttributes(
            sspicon.SECPKG_ATTR_SIZES
        )
        msg = b"some data to be encrypted ......"

        trailersize = pkg_size_info["SecurityTrailer"]
        blocksize = pkg_size_info["BlockSize"]
        encbuf = win32security.PySecBufferDescType()
        encbuf.append(
            win32security.PySecBufferType(trailersize, sspicon.SECBUFFER_TOKEN)
        )
        encbuf.append(win32security.PySecBufferType(len(msg), sspicon.SECBUFFER_DATA))
        encbuf.append(
            win32security.PySecBufferType(blocksize, sspicon.SECBUFFER_PADDING)
        )
        encbuf[1].Buffer = msg
        sspiclient.ctxt.EncryptMessage(0, encbuf, 1)

        encmsg = encbuf[0].Buffer + encbuf[1].Buffer + encbuf[2].Buffer
        decbuf = win32security.PySecBufferDescType()
        decbuf.append(
            win32security.PySecBufferType(len(encmsg), sspicon.SECBUFFER_STREAM)
        )
        decbuf.append(win32security.PySecBufferType(0, sspicon.SECBUFFER_DATA))
        decbuf[0].Buffer = encmsg

        sspiserver.ctxt.DecryptMessage(decbuf, 1)
        self.assertEqual(msg, decbuf[1].Buffer)

    def testEncryptNTLM(self):
        self._doTestEncrypt("NTLM")

    def testEncryptStreamNTLM(self):
        self._doTestEncryptStream("NTLM")

    def testEncryptKerberos(self):
        applyHandlingSkips(self._doTestEncrypt, "Kerberos")

    def testEncryptStreamKerberos(self):
        applyHandlingSkips(self._doTestEncryptStream, "Kerberos")

    def _doTestSign(self, pkg_name):
        sspiclient, sspiserver = self._doAuth(pkg_name)

        pkg_size_info = sspiclient.ctxt.QueryContextAttributes(
            sspicon.SECPKG_ATTR_SIZES
        )
        msg = b"some data to be encrypted ......"

        sigsize = pkg_size_info["MaxSignature"]
        sigbuf = win32security.PySecBufferDescType()
        sigbuf.append(win32security.PySecBufferType(len(msg), sspicon.SECBUFFER_DATA))
        sigbuf.append(win32security.PySecBufferType(sigsize, sspicon.SECBUFFER_TOKEN))
        sigbuf[0].Buffer = msg
        sspiclient.ctxt.MakeSignature(0, sigbuf, 0)
        sspiserver.ctxt.VerifySignature(sigbuf, 0)
        # and test the higher-level functions
        sspiclient.next_seq_num = 1
        sspiserver.next_seq_num = 1
        data = b"hello"
        key = sspiclient.sign(data)
        sspiserver.verify(data, key)
        key = sspiclient.sign(data)
        self.assertRaisesHRESULT(
            sspicon.SEC_E_MESSAGE_ALTERED, sspiserver.verify, data + data, key
        )

        # and the other way
        key = sspiserver.sign(data)
        sspiclient.verify(data, key)
        key = sspiserver.sign(data)
        self.assertRaisesHRESULT(
            sspicon.SEC_E_MESSAGE_ALTERED, sspiclient.verify, data + data, key
        )

    def testSignNTLM(self):
        self._doTestSign("NTLM")

    def testSignKerberos(self):
        applyHandlingSkips(self._doTestSign, "Kerberos")

    def _testSequenceSign(self):
        # Only Kerberos supports sequence detection.
        sspiclient, sspiserver = self._doAuth("Kerberos")
        key = sspiclient.sign(b"hello")
        sspiclient.sign(b"hello")
        self.assertRaisesHRESULT(
            sspicon.SEC_E_OUT_OF_SEQUENCE, sspiserver.verify, b"hello", key
        )

    def testSequenceSign(self):
        applyHandlingSkips(self._testSequenceSign)

    def _testSequenceEncrypt(self):
        # Only Kerberos supports sequence detection.
        sspiclient, sspiserver = self._doAuth("Kerberos")
        blob, key = sspiclient.encrypt(b"hello")
        blob, key = sspiclient.encrypt(b"hello")
        self.assertRaisesHRESULT(
            sspicon.SEC_E_OUT_OF_SEQUENCE, sspiserver.decrypt, blob, key
        )

    def testSequenceEncrypt(self):
        applyHandlingSkips(self._testSequenceEncrypt)

    def testSecBufferRepr(self):
        desc = win32security.PySecBufferDescType()
        self.assertRegex(
            repr(desc),
            r"PySecBufferDesc\(ulVersion: 0 \| cBuffers: 0 \| pBuffers: 0x[\da-fA-F]{8,16}\)",
        )

        buffer1 = win32security.PySecBufferType(0, sspicon.SECBUFFER_TOKEN)
        self.assertRegex(
            repr(buffer1),
            r"PySecBuffer\(cbBuffer: 0 \| BufferType: 2 \| pvBuffer: 0x[\da-fA-F]{8,16}\)",
        )
        desc.append(buffer1)

        self.assertRegex(
            repr(desc),
            r"PySecBufferDesc\(ulVersion: 0 \| cBuffers: 1 \| pBuffers: 0x[\da-fA-F]{8,16}\)",
        )

        buffer2 = win32security.PySecBufferType(4, sspicon.SECBUFFER_DATA)
        self.assertRegex(
            repr(buffer2),
            r"PySecBuffer\(cbBuffer: 4 \| BufferType: 1 \| pvBuffer: 0x[\da-fA-F]{8,16}\)",
        )
        desc.append(buffer2)

        self.assertRegex(
            repr(desc),
            r"PySecBufferDesc\(ulVersion: 0 \| cBuffers: 2 \| pBuffers: 0x[\da-fA-F]{8,16}\)",
        )


if __name__ == "__main__":
    testmain()

# === NexusCore/openenv\Lib\site-packages\win32com\server\util.py ===
"""General Server side utilities"""

import pythoncom
import winerror

from . import policy
from .exception import COMException


def wrap(ob, iid=None, usePolicy=None, useDispatcher=None):
    """Wraps an object in a PyGDispatch gateway.

    Returns a client side PyI{iid} interface.

    Interface and gateway support must exist for the specified IID, as
    the QueryInterface() method is used.

    """
    if usePolicy is None:
        usePolicy = policy.DefaultPolicy
    if useDispatcher == 1:  # True will also work here.
        import win32com.server.dispatcher

        useDispatcher = win32com.server.dispatcher.DefaultDebugDispatcher
    if useDispatcher is None or useDispatcher == 0:
        ob = usePolicy(ob)
    else:
        ob = useDispatcher(usePolicy, ob)

    # get a PyIDispatch, which interfaces to PyGDispatch
    ob = pythoncom.WrapObject(ob)
    if iid is not None:
        ob = ob.QueryInterface(iid)  # Ask the PyIDispatch if it supports it?
    return ob


def unwrap(ob):
    """Unwraps an interface.

    Given an interface which wraps up a Gateway, return the object behind
    the gateway.
    """
    ob = pythoncom.UnwrapObject(ob)
    # see if the object is a dispatcher
    if hasattr(ob, "policy"):
        ob = ob.policy
    return ob._obj_


class ListEnumerator:
    """A class to expose a Python sequence as an EnumVARIANT.

    Create an instance of this class passing a sequence (list, tuple, or
    any sequence protocol supporting object) and it will automatically
    support the EnumVARIANT interface for the object.

    See also the @NewEnum@ function, which can be used to turn the
    instance into an actual COM server.
    """

    _public_methods_ = ["Next", "Skip", "Reset", "Clone"]

    def __init__(self, data, index=0, iid=pythoncom.IID_IEnumVARIANT):
        self._list_ = data
        self.index = index
        self._iid_ = iid

    def _query_interface_(self, iid):
        if iid == self._iid_:
            return 1

    def Next(self, count):
        result = self._list_[self.index : self.index + count]
        self.Skip(count)
        return result

    def Skip(self, count):
        end = self.index + count
        if end > len(self._list_):
            end = len(self._list_)
        self.index = end

    def Reset(self):
        self.index = 0

    def Clone(self):
        return self._wrap(self.__class__(self._list_, self.index))

    def _wrap(self, ob):
        return wrap(ob)


class ListEnumeratorGateway(ListEnumerator):
    """A List Enumerator which wraps a sequence's items in gateways.

    If a sequence contains items (objects) that have not been wrapped for
    return through the COM layers, then a ListEnumeratorGateway can be
    used to wrap those items before returning them (from the Next() method).

    See also the @ListEnumerator@ class and the @NewEnum@ function.
    """

    def Next(self, count):
        result = self._list_[self.index : self.index + count]
        self.Skip(count)
        return map(self._wrap, result)


def NewEnum(
    seq,
    cls=ListEnumerator,
    iid=pythoncom.IID_IEnumVARIANT,
    usePolicy=None,
    useDispatcher=None,
):
    """Creates a new enumerator COM server.

    This function creates a new COM Server that implements the
    IID_IEnumVARIANT interface.

    A COM server that can enumerate the passed in sequence will be
    created, then wrapped up for return through the COM framework.
    Optionally, a custom COM server for enumeration can be passed
    (the default is @ListEnumerator@), and the specific IEnum
    interface can be specified.
    """
    ob = cls(seq, iid=iid)
    return wrap(ob, iid, usePolicy=usePolicy, useDispatcher=useDispatcher)


class Collection:
    "A collection of VARIANT values."

    _public_methods_ = ["Item", "Count", "Add", "Remove", "Insert"]

    def __init__(self, data=None, readOnly=0):
        if data is None:
            data = []
        self.data = data

        # disable Add/Remove if read-only. note that we adjust _public_methods_
        # on this instance only.
        if readOnly:
            self._public_methods_ = ["Item", "Count"]

    # This method is also used as the "default" method.
    # Thus "print(ob)" will cause this to be called with zero
    # params.  Handle this slightly more elegantly here.
    # Ideally the  policy should handle this.
    def Item(self, *args):
        if len(args) != 1:
            raise COMException(scode=winerror.DISP_E_BADPARAMCOUNT)

        try:
            return self.data[args[0]]
        except IndexError as desc:
            raise COMException(scode=winerror.DISP_E_BADINDEX, desc=str(desc))

    _value_ = Item

    def Count(self):
        return len(self.data)

    def Add(self, value):
        self.data.append(value)

    def Remove(self, index):
        try:
            del self.data[index]
        except IndexError as desc:
            raise COMException(scode=winerror.DISP_E_BADINDEX, desc=str(desc))

    def Insert(self, index, value):
        try:
            index = int(index)
        except (ValueError, TypeError):
            raise COMException(scode=winerror.DISP_E_TYPEMISMATCH)
        self.data.insert(index, value)

    def _NewEnum(self):
        return NewEnum(self.data)


def NewCollection(seq, cls=Collection):
    """Creates a new COM collection object

    This function creates a new COM Server that implements the
    common collection protocols, including enumeration. (_NewEnum)

    A COM server that can enumerate the passed in sequence will be
    created, then wrapped up for return through the COM framework.
    Optionally, a custom COM server for enumeration can be passed
    (the default is @Collection@).
    """
    return pythoncom.WrapObject(
        policy.DefaultPolicy(cls(seq)), pythoncom.IID_IDispatch, pythoncom.IID_IDispatch
    )


class FileStream:
    _public_methods_ = ["Read", "Write", "Clone", "CopyTo", "Seek"]
    _com_interfaces_ = [pythoncom.IID_IStream]

    def __init__(self, file):
        self.file = file

    def Read(self, amount):
        return self.file.read(amount)

    def Write(self, data):
        self.file.write(data)
        return len(data)

    def Clone(self):
        return self._wrap(self.__class__(self.file))

    def CopyTo(self, dest, cb):
        data = self.file.read(cb)
        cbread = len(data)
        dest.Write(data)  ## ??? Write does not currently return the length ???
        return cbread, cbread

    def Seek(self, offset, origin):
        # how convient that the 'origin' values are the same as the CRT :)
        self.file.seek(offset, origin)
        return self.file.tell()

    def _wrap(self, ob):
        return wrap(ob)

# === NexusCore/openenv\Lib\site-packages\win32comext\authorization\demos\EditSecurity.py ===
import os

import pythoncom
import win32api
import win32com.server.policy
import win32con
import win32security
from ntsecuritycon import (
    FILE_ALL_ACCESS,
    FILE_APPEND_DATA,
    FILE_GENERIC_EXECUTE,
    FILE_GENERIC_READ,
    FILE_GENERIC_WRITE,
    FILE_WRITE_DATA,
    READ_CONTROL,
    SI_ACCESS_GENERAL,
    SI_ACCESS_SPECIFIC,
    SI_ADVANCED,
    SI_CONTAINER,
    SI_EDIT_ALL,
    SI_PAGE_TITLE,
    SI_RESET,
    WRITE_DAC,
    WRITE_OWNER,
)
from pythoncom import IID_NULL
from win32com.authorization import authorization
from win32security import CONTAINER_INHERIT_ACE, OBJECT_INHERIT_ACE


class SecurityInformation(win32com.server.policy.DesignatedWrapPolicy):
    _com_interfaces_ = [authorization.IID_ISecurityInformation]
    _public_methods_ = [
        "GetObjectInformation",
        "GetSecurity",
        "SetSecurity",
        "GetAccessRights",
        "GetInheritTypes",
        "MapGeneric",
        "PropertySheetPageCallback",
    ]

    def __init__(self, FileName):
        self.FileName = FileName
        self._wrap_(self)

    def GetObjectInformation(self):
        """Identifies object whose security will be modified, and determines options available
        to the end user"""
        flags = SI_ADVANCED | SI_EDIT_ALL | SI_PAGE_TITLE | SI_RESET
        if os.path.isdir(self.FileName):
            flags |= SI_CONTAINER
        hinstance = 0  ## handle to module containing string resources
        servername = ""  ## name of authenticating server if not local machine
        objectname = os.path.split(self.FileName)[1]
        pagetitle = "Python ACL Editor"
        if os.path.isdir(self.FileName):
            pagetitle += " (dir)"
        else:
            pagetitle += " (file)"
        objecttype = IID_NULL
        return flags, hinstance, servername, objectname, pagetitle, objecttype

    def GetSecurity(self, requestedinfo, bdefault):
        """Requests the existing permissions for object"""
        if bdefault:
            ## This is invoked if the 'Default' button is pressed (only present if SI_RESET is passed
            ## with the flags in GetObjectInfo). Passing an empty SD with a NULL Dacl
            ##  should cause inherited ACL from parent dir or default dacl from user's token to be used
            return win32security.SECURITY_DESCRIPTOR()
        else:
            ## GetFileSecurity sometimes fails to return flags indicating that an ACE is inherited
            return win32security.GetNamedSecurityInfo(
                self.FileName, win32security.SE_FILE_OBJECT, requestedinfo
            )

    def SetSecurity(self, requestedinfo, sd):
        """Applies permissions to the object"""
        owner = sd.GetSecurityDescriptorOwner()
        group = sd.GetSecurityDescriptorGroup()
        dacl = sd.GetSecurityDescriptorDacl()
        sacl = sd.GetSecurityDescriptorSacl()
        win32security.SetNamedSecurityInfo(
            self.FileName,
            win32security.SE_FILE_OBJECT,
            requestedinfo,
            owner,
            group,
            dacl,
            sacl,
        )
        ## should also handle recursive operations here

    def GetAccessRights(self, objecttype, flags):
        """Returns a tuple of (AccessRights, DefaultAccess), where AccessRights is a sequence of tuples representing
        SI_ACCESS structs, containing (guid, access mask, Name, flags). DefaultAccess indicates which of the
        AccessRights will be used initially when a new ACE is added (zero based).
        Flags can contain SI_ACCESS_SPECIFIC,SI_ACCESS_GENERAL,SI_ACCESS_CONTAINER,SI_ACCESS_PROPERTY,
              CONTAINER_INHERIT_ACE,INHERIT_ONLY_ACE,OBJECT_INHERIT_ACE
        """
        ## input flags: SI_ADVANCED,SI_EDIT_AUDITS,SI_EDIT_PROPERTIES indicating which property sheet is requesting the rights
        if (objecttype is not None) and (objecttype != IID_NULL):
            ## Should not be true for file objects.  Usually only used with DS objects that support security for
            ## their properties
            raise NotImplementedError("Object type is not supported")

        if os.path.isdir(self.FileName):
            file_append_data_desc = "Create subfolders"
            file_write_data_desc = "Create Files"
        else:
            file_append_data_desc = "Append data"
            file_write_data_desc = "Write data"

        accessrights = [
            (
                IID_NULL,
                FILE_GENERIC_READ,
                "Generic read",
                SI_ACCESS_GENERAL
                | SI_ACCESS_SPECIFIC
                | OBJECT_INHERIT_ACE
                | CONTAINER_INHERIT_ACE,
            ),
            (
                IID_NULL,
                FILE_GENERIC_WRITE,
                "Generic write",
                SI_ACCESS_GENERAL
                | SI_ACCESS_SPECIFIC
                | OBJECT_INHERIT_ACE
                | CONTAINER_INHERIT_ACE,
            ),
            (
                IID_NULL,
                win32con.DELETE,
                "Delete",
                SI_ACCESS_SPECIFIC | OBJECT_INHERIT_ACE | CONTAINER_INHERIT_ACE,
            ),
            (
                IID_NULL,
                WRITE_OWNER,
                "Change owner",
                SI_ACCESS_SPECIFIC | OBJECT_INHERIT_ACE | CONTAINER_INHERIT_ACE,
            ),
            (
                IID_NULL,
                READ_CONTROL,
                "Read Permissions",
                SI_ACCESS_SPECIFIC | OBJECT_INHERIT_ACE | CONTAINER_INHERIT_ACE,
            ),
            (
                IID_NULL,
                WRITE_DAC,
                "Change permissions",
                SI_ACCESS_SPECIFIC | OBJECT_INHERIT_ACE | CONTAINER_INHERIT_ACE,
            ),
            (
                IID_NULL,
                FILE_APPEND_DATA,
                file_append_data_desc,
                SI_ACCESS_SPECIFIC | OBJECT_INHERIT_ACE | CONTAINER_INHERIT_ACE,
            ),
            (
                IID_NULL,
                FILE_WRITE_DATA,
                file_write_data_desc,
                SI_ACCESS_SPECIFIC | OBJECT_INHERIT_ACE | CONTAINER_INHERIT_ACE,
            ),
        ]
        return (accessrights, 0)

    def MapGeneric(self, guid, aceflags, mask):
        """Converts generic access rights to specific rights.  This implementation uses standard file system rights,
        but you can map them any way that suits your application.
        """
        return win32security.MapGenericMask(
            mask,
            (
                FILE_GENERIC_READ,
                FILE_GENERIC_WRITE,
                FILE_GENERIC_EXECUTE,
                FILE_ALL_ACCESS,
            ),
        )

    def GetInheritTypes(self):
        """Specifies which types of ACE inheritance are supported.
        Returns a sequence of tuples representing SI_INHERIT_TYPE structs, containing
        (object type guid, inheritance flags, display name).  Guid is usually only used with
        Directory Service objects.
        """
        return (
            (IID_NULL, 0, "Only current object"),
            (IID_NULL, OBJECT_INHERIT_ACE, "Files inherit permissions"),
            (IID_NULL, CONTAINER_INHERIT_ACE, "Sub Folders inherit permissions"),
            (
                IID_NULL,
                CONTAINER_INHERIT_ACE | OBJECT_INHERIT_ACE,
                "Files and subfolders",
            ),
        )

    def PropertySheetPageCallback(self, hwnd, msg, pagetype):
        """Invoked each time a property sheet page is created or destroyed."""
        ## page types from SI_PAGE_TYPE enum: SI_PAGE_PERM SI_PAGE_ADVPERM SI_PAGE_AUDIT SI_PAGE_OWNER
        ## msg: PSPCB_CREATE, PSPCB_RELEASE, PSPCB_SI_INITDIALOG
        return None

    def EditSecurity(self, owner_hwnd=0):
        """Creates an ACL editor dialog based on parameters returned by interface methods"""
        isi = pythoncom.WrapObject(
            self, authorization.IID_ISecurityInformation, pythoncom.IID_IUnknown
        )
        authorization.EditSecurity(owner_hwnd, isi)


## folder permissions
temp_dir = win32api.GetTempPath()
dir_name = win32api.GetTempFileName(temp_dir, "isi")[0]
print(dir_name)
os.remove(dir_name)
os.mkdir(dir_name)
si = SecurityInformation(dir_name)
si.EditSecurity()

## file permissions
fname = win32api.GetTempFileName(dir_name, "isi")[0]
si = SecurityInformation(fname)
si.EditSecurity()

# === NexusCore/evaluation\evaluate\multi_turn\gpt_gen_plus_solution_multiround.py ===
import argparse
import os
import torch
from pathlib import Path
from tqdm import tqdm
import logging
from evalplus.data import (get_human_eval_plus, 
    write_jsonl,
    get_human_eval_plus_hash,
    get_mbpp_plus,
    get_mbpp_plus_hash,
)
from utils import sanitize_solution,check_correctness,get_groundtruth,SUCCESS
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS
from copy import deepcopy
from chat_with_gpt import gpt_predict
import json

MAX_TRY = 2

def humaneval_build_instruction(languge: str, question: str):
    return '''You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
Here is the given code to do completion:
```{}
{}
```
Please continue to complete the function with {} programming language. You are not allowed to modify the given code and do the completion only. 

Please return all completed codes in one code block. 
This code block should be in the following format:
```{}
# Your codes here
```

@@ Response
'''.strip().format(languge.lower(), question.strip(),languge.lower(),languge.lower())

mbpp_build_deepseekcoder_instruction='''You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
Here is the given problem and test examples:
{}

Please use the {} programming language to solve this problem.
Please make sure that your code includes the functions from the test samples and that the input and output formats of these functions match the test samples.

Please return all completed codes in one code block. 
This code block should be in the following format:
```{}
# Your codes here
```

@@ Response
'''

def generate_multi_round(problem,expected_output, example, lang,name,flags):
    if flags.dataset=="humaneval":
        prompt = humaneval_build_instruction(lang, example['prompt'])
    elif flags.dataset=="mbpp":
        prompt = mbpp_build_deepseekcoder_instruction.strip().format(example['prompt'],"python","python")
    inputs=[{'role': 'user', 'content': prompt}]
    output = gpt_predict(inputs,model=name)
    solution = {k:v for k,v in example.items()}
    solution["solution"]=output
    sanitized_solution = sanitize_solution(deepcopy(solution),flags.eofs)
    attempt = 1
    judge = False
    modify = False
    code = sanitized_solution["solution"]
    while attempt==1 or sanitized_solution["solution"]!="":
        args = (
            flags.dataset,
            0,
            problem,
            sanitized_solution["solution"],
            expected_output,
            flags.version,
            True,  # fast_check
            example["task_id"]+f'_{attempt}',
            flags.min_time_limit,
            flags.gt_time_limit_factor,
        )
        result = check_correctness(*args)
        if flags.version=="base" and result["base"][0]==SUCCESS:
            code = sanitized_solution["solution"]
            if attempt==2:
                modify = True
            judge = True
            break
        elif flags.version=="plus" and result["plus"][0]==result["base"][0]==SUCCESS:
            code = sanitized_solution["solution"]
            if attempt==2:
                modify = True
            judge = True
            break
        else:
            attempt += 1    
            if attempt > MAX_TRY:
                code = sanitized_solution["solution"]
                break
            execution_feedback=""
            if flags.version=="base":
                execution_feedback=result["base"][2]
            elif flags.version=="plus":
                if result["base"][0]!=SUCCESS:
                    execution_feedback+=result["base"][2]
                    if "The results aren't as expected." in execution_feedback:
                        if result["plus"][0]!=SUCCESS:
                            execution_feedback+="\n"+result["plus"][2]
                else:
                    execution_feedback=result["plus"][2]
            prompt +="""
{}

@@ Instruction
Execution result: 
{}
""".format(solution["solution"],execution_feedback)
            inputs = [{'role': 'user', 'content': prompt}]
            output = gpt_predict(inputs,model=name)
            solution = {k:v for k,v in example.items()}
            solution["solution"]=output 
            sanitized_solution = sanitize_solution(deepcopy(solution),flags.eofs)

    return code,judge,modify


def gen_solution(args):
    a,b = 0,0
    total_modify = 0
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    fail_list=[]
    model_path = args.model
    logging.info(f"model:{model_path}")
    model_name =args.model
    lang = "python"
    os.makedirs(os.path.join(args.output_path,model_name),exist_ok=True)
    output_file = os.path.join(args.output_path,model_name,f"multiround_{args.dataset}_{args.version}_solutions-sanitized.jsonl")
    if not args.resume:
        if os.path.exists(output_file):
            logging.info(f"Old sample jsonl file exists, remove it. {output_file}")
            os.remove(output_file)
    else:
        existing_task_ids = set()
        if os.path.exists(output_file):
            with open(output_file, 'r') as file:
                for line in file:
                    data = json.loads(line)
                    if 'task_id' in data:
                        existing_task_ids.add(data['task_id'])
                        a=data["pass_num"]
                        total_modify=data["total_modify"]
                        b=data["total_num"]-a
                        fail_list=data["fail_list"]
    
    if args.dataset=="humaneval":
        problems = get_human_eval_plus()
        examples = problems.items()
        dataset_hash = get_human_eval_plus_hash()
        expected_outputs = get_groundtruth(problems, dataset_hash, [])
    else:
        problems = get_mbpp_plus()
        examples = problems.items()
        dataset_hash = get_mbpp_plus_hash()
        expected_outputs = get_groundtruth(
                problems,
                dataset_hash,
                MBPP_OUTPUT_NOT_NONE_TASKS,
            )
    logging.info("Read {} examples for evaluation over.".format(len(examples)))
    for task_id,example in tqdm(examples, desc='Generating'):
        if args.resume:
            if task_id in existing_task_ids:
                continue
        problem = problems[task_id]
        expected_output = expected_outputs[task_id]
        code,judge,modify = generate_multi_round(problem,expected_output,example, lang, model_name,args)

        if modify:
            total_modify += 1
        if judge:
            a += 1
        else:
            b += 1
            fail_list.append(task_id)
        result = a/(a+b)
        print ("pass num",a)
        print ("total num",a+b)
        print ('rate: '+str(result))
        print ("judge: ",judge)
        print ('modify: '+str(modify))
        print ("num modify: "+str(total_modify))
        print("fail list",fail_list)
        gen_sample=[dict(task_id=task_id, solution=code, pass_num=a, total_modify=total_modify, total_num=a+b, fail_list=fail_list)]
        write_jsonl(output_file, gen_sample ,append=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, choices=["gpt3.5", "gpt4"])
    parser.add_argument('--output_path', type=str, help="output path", default="./multiround_output")
    parser.add_argument('--log_file', type=str, help="log file name", default="gen_humaneval_plus_solution_singleround.log")
    parser.add_argument("--min-time-limit", default=1, type=float)
    parser.add_argument("--gt-time-limit-factor", default=4.0, type=float)
    parser.add_argument(
        "--version", required=True, type=str, choices=["base", "plus"]
    )
    parser.add_argument(
        "--dataset", required=True, type=str, choices=["humaneval", "mbpp"]
    )
    parser.add_argument('--resume', action="store_true")

    args = parser.parse_args()
    args.eofs=None

    model_name = args.model
    os.makedirs(os.path.join(args.output_path,model_name),exist_ok=True)
    logfile=os.path.join(args.output_path,model_name,args.log_file)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - \n%(message)s')
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - \n%(message)s')
    file_handler.setFormatter(formatter)  
    logging.getLogger().addHandler(file_handler)

    gen_solution(args)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\cache.py ===
import os
import textwrap
from optparse import Values
from typing import Any, List

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, PipError
from pip._internal.utils import filesystem
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import format_size

logger = getLogger(__name__)


class CacheCommand(Command):
    """
    Inspect and manage pip's wheel cache.

    Subcommands:

    - dir: Show the cache directory.
    - info: Show information about the cache.
    - list: List filenames of packages stored in the cache.
    - remove: Remove one or more package from the cache.
    - purge: Remove all items from the cache.

    ``<pattern>`` can be a glob expression or a package name.
    """

    ignore_require_venv = True
    usage = """
        %prog dir
        %prog info
        %prog list [<pattern>] [--format=[human, abspath]]
        %prog remove <pattern>
        %prog purge
    """

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "--format",
            action="store",
            dest="list_format",
            default="human",
            choices=("human", "abspath"),
            help="Select the output format among: human (default) or abspath",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        handlers = {
            "dir": self.get_cache_dir,
            "info": self.get_cache_info,
            "list": self.list_cache_items,
            "remove": self.remove_cache_items,
            "purge": self.purge_cache,
        }

        if not options.cache_dir:
            logger.error("pip cache commands can not function since cache is disabled.")
            return ERROR

        # Determine action
        if not args or args[0] not in handlers:
            logger.error(
                "Need an action (%s) to perform.",
                ", ".join(sorted(handlers)),
            )
            return ERROR

        action = args[0]

        # Error handling happens here, not in the action-handlers.
        try:
            handlers[action](options, args[1:])
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

    def get_cache_dir(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        logger.info(options.cache_dir)

    def get_cache_info(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        num_http_files = len(self._find_http_files(options))
        num_packages = len(self._find_wheels(options, "*"))

        http_cache_location = self._cache_dir(options, "http-v2")
        old_http_cache_location = self._cache_dir(options, "http")
        wheels_cache_location = self._cache_dir(options, "wheels")
        http_cache_size = filesystem.format_size(
            filesystem.directory_size(http_cache_location)
            + filesystem.directory_size(old_http_cache_location)
        )
        wheels_cache_size = filesystem.format_directory_size(wheels_cache_location)

        message = (
            textwrap.dedent(
                """
                    Package index page cache location (pip v23.3+): {http_cache_location}
                    Package index page cache location (older pips): {old_http_cache_location}
                    Package index page cache size: {http_cache_size}
                    Number of HTTP files: {num_http_files}
                    Locally built wheels location: {wheels_cache_location}
                    Locally built wheels size: {wheels_cache_size}
                    Number of locally built wheels: {package_count}
                """  # noqa: E501
            )
            .format(
                http_cache_location=http_cache_location,
                old_http_cache_location=old_http_cache_location,
                http_cache_size=http_cache_size,
                num_http_files=num_http_files,
                wheels_cache_location=wheels_cache_location,
                package_count=num_packages,
                wheels_cache_size=wheels_cache_size,
            )
            .strip()
        )

        logger.info(message)

    def list_cache_items(self, options: Values, args: List[Any]) -> None:
        if len(args) > 1:
            raise CommandError("Too many arguments")

        if args:
            pattern = args[0]
        else:
            pattern = "*"

        files = self._find_wheels(options, pattern)
        if options.list_format == "human":
            self.format_for_human(files)
        else:
            self.format_for_abspath(files)

    def format_for_human(self, files: List[str]) -> None:
        if not files:
            logger.info("No locally built wheels cached.")
            return

        results = []
        for filename in files:
            wheel = os.path.basename(filename)
            size = filesystem.format_file_size(filename)
            results.append(f" - {wheel} ({size})")
        logger.info("Cache contents:\n")
        logger.info("\n".join(sorted(results)))

    def format_for_abspath(self, files: List[str]) -> None:
        if files:
            logger.info("\n".join(sorted(files)))

    def remove_cache_items(self, options: Values, args: List[Any]) -> None:
        if len(args) > 1:
            raise CommandError("Too many arguments")

        if not args:
            raise CommandError("Please provide a pattern")

        files = self._find_wheels(options, args[0])

        no_matching_msg = "No matching packages"
        if args[0] == "*":
            # Only fetch http files if no specific pattern given
            files += self._find_http_files(options)
        else:
            # Add the pattern to the log message
            no_matching_msg += f' for pattern "{args[0]}"'

        if not files:
            logger.warning(no_matching_msg)

        bytes_removed = 0
        for filename in files:
            bytes_removed += os.stat(filename).st_size
            os.unlink(filename)
            logger.verbose("Removed %s", filename)
        logger.info("Files removed: %s (%s)", len(files), format_size(bytes_removed))

    def purge_cache(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        return self.remove_cache_items(options, ["*"])

    def _cache_dir(self, options: Values, subdir: str) -> str:
        return os.path.join(options.cache_dir, subdir)

    def _find_http_files(self, options: Values) -> List[str]:
        old_http_dir = self._cache_dir(options, "http")
        new_http_dir = self._cache_dir(options, "http-v2")
        return filesystem.find_files(old_http_dir, "*") + filesystem.find_files(
            new_http_dir, "*"
        )

    def _find_wheels(self, options: Values, pattern: str) -> List[str]:
        wheel_dir = self._cache_dir(options, "wheels")

        # The wheel filename format, as specified in PEP 427, is:
        #     {distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
        #
        # Additionally, non-alphanumeric values in the distribution are
        # normalized to underscores (_), meaning hyphens can never occur
        # before `-{version}`.
        #
        # Given that information:
        # - If the pattern we're given contains a hyphen (-), the user is
        #   providing at least the version. Thus, we can just append `*.whl`
        #   to match the rest of it.
        # - If the pattern we're given doesn't contain a hyphen (-), the
        #   user is only providing the name. Thus, we append `-*.whl` to
        #   match the hyphen before the version, followed by anything else.
        #
        # PEP 427: https://www.python.org/dev/peps/pep-0427/
        pattern = pattern + ("*.whl" if "-" in pattern else "-*.whl")

        return filesystem.find_files(wheel_dir, pattern)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\metadata\importlib\_dists.py ===
import email.message
import importlib.metadata
import pathlib
import zipfile
from os import PathLike
from typing import (
    Collection,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    Union,
    cast,
)

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.exceptions import InvalidWheel, UnsupportedWheel
from pip._internal.metadata.base import (
    BaseDistribution,
    BaseEntryPoint,
    InfoPath,
    Wheel,
)
from pip._internal.utils.misc import normalize_path
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.wheel import parse_wheel, read_wheel_metadata_file

from ._compat import (
    BasePath,
    get_dist_canonical_name,
    parse_name_and_version_from_info_directory,
)


class WheelDistribution(importlib.metadata.Distribution):
    """An ``importlib.metadata.Distribution`` read from a wheel.

    Although ``importlib.metadata.PathDistribution`` accepts ``zipfile.Path``,
    its implementation is too "lazy" for pip's needs (we can't keep the ZipFile
    handle open for the entire lifetime of the distribution object).

    This implementation eagerly reads the entire metadata directory into the
    memory instead, and operates from that.
    """

    def __init__(
        self,
        files: Mapping[pathlib.PurePosixPath, bytes],
        info_location: pathlib.PurePosixPath,
    ) -> None:
        self._files = files
        self.info_location = info_location

    @classmethod
    def from_zipfile(
        cls,
        zf: zipfile.ZipFile,
        name: str,
        location: str,
    ) -> "WheelDistribution":
        info_dir, _ = parse_wheel(zf, name)
        paths = (
            (name, pathlib.PurePosixPath(name.split("/", 1)[-1]))
            for name in zf.namelist()
            if name.startswith(f"{info_dir}/")
        )
        files = {
            relpath: read_wheel_metadata_file(zf, fullpath)
            for fullpath, relpath in paths
        }
        info_location = pathlib.PurePosixPath(location, info_dir)
        return cls(files, info_location)

    def iterdir(self, path: InfoPath) -> Iterator[pathlib.PurePosixPath]:
        # Only allow iterating through the metadata directory.
        if pathlib.PurePosixPath(str(path)) in self._files:
            return iter(self._files)
        raise FileNotFoundError(path)

    def read_text(self, filename: str) -> Optional[str]:
        try:
            data = self._files[pathlib.PurePosixPath(filename)]
        except KeyError:
            return None
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as e:
            wheel = self.info_location.parent
            error = f"Error decoding metadata for {wheel}: {e} in {filename} file"
            raise UnsupportedWheel(error)
        return text

    def locate_file(self, path: Union[str, "PathLike[str]"]) -> pathlib.Path:
        # This method doesn't make sense for our in-memory wheel, but the API
        # requires us to define it.
        raise NotImplementedError


class Distribution(BaseDistribution):
    def __init__(
        self,
        dist: importlib.metadata.Distribution,
        info_location: Optional[BasePath],
        installed_location: Optional[BasePath],
    ) -> None:
        self._dist = dist
        self._info_location = info_location
        self._installed_location = installed_location

    @classmethod
    def from_directory(cls, directory: str) -> BaseDistribution:
        info_location = pathlib.Path(directory)
        dist = importlib.metadata.Distribution.at(info_location)
        return cls(dist, info_location, info_location.parent)

    @classmethod
    def from_metadata_file_contents(
        cls,
        metadata_contents: bytes,
        filename: str,
        project_name: str,
    ) -> BaseDistribution:
        # Generate temp dir to contain the metadata file, and write the file contents.
        temp_dir = pathlib.Path(
            TempDirectory(kind="metadata", globally_managed=True).path
        )
        metadata_path = temp_dir / "METADATA"
        metadata_path.write_bytes(metadata_contents)
        # Construct dist pointing to the newly created directory.
        dist = importlib.metadata.Distribution.at(metadata_path.parent)
        return cls(dist, metadata_path.parent, None)

    @classmethod
    def from_wheel(cls, wheel: Wheel, name: str) -> BaseDistribution:
        try:
            with wheel.as_zipfile() as zf:
                dist = WheelDistribution.from_zipfile(zf, name, wheel.location)
        except zipfile.BadZipFile as e:
            raise InvalidWheel(wheel.location, name) from e
        return cls(dist, dist.info_location, pathlib.PurePosixPath(wheel.location))

    @property
    def location(self) -> Optional[str]:
        if self._info_location is None:
            return None
        return str(self._info_location.parent)

    @property
    def info_location(self) -> Optional[str]:
        if self._info_location is None:
            return None
        return str(self._info_location)

    @property
    def installed_location(self) -> Optional[str]:
        if self._installed_location is None:
            return None
        return normalize_path(str(self._installed_location))

    @property
    def canonical_name(self) -> NormalizedName:
        return get_dist_canonical_name(self._dist)

    @property
    def version(self) -> Version:
        if version := parse_name_and_version_from_info_directory(self._dist)[1]:
            return parse_version(version)
        return parse_version(self._dist.version)

    @property
    def raw_version(self) -> str:
        return self._dist.version

    def is_file(self, path: InfoPath) -> bool:
        return self._dist.read_text(str(path)) is not None

    def iter_distutils_script_names(self) -> Iterator[str]:
        # A distutils installation is always "flat" (not in e.g. egg form), so
        # if this distribution's info location is NOT a pathlib.Path (but e.g.
        # zipfile.Path), it can never contain any distutils scripts.
        if not isinstance(self._info_location, pathlib.Path):
            return
        for child in self._info_location.joinpath("scripts").iterdir():
            yield child.name

    def read_text(self, path: InfoPath) -> str:
        content = self._dist.read_text(str(path))
        if content is None:
            raise FileNotFoundError(path)
        return content

    def iter_entry_points(self) -> Iterable[BaseEntryPoint]:
        # importlib.metadata's EntryPoint structure satisfies BaseEntryPoint.
        return self._dist.entry_points

    def _metadata_impl(self) -> email.message.Message:
        # From Python 3.10+, importlib.metadata declares PackageMetadata as the
        # return type. This protocol is unfortunately a disaster now and misses
        # a ton of fields that we need, including get() and get_payload(). We
        # rely on the implementation that the object is actually a Message now,
        # until upstream can improve the protocol. (python/cpython#94952)
        return cast(email.message.Message, self._dist.metadata)

    def iter_provided_extras(self) -> Iterable[NormalizedName]:
        return [
            canonicalize_name(extra)
            for extra in self.metadata.get_all("Provides-Extra", [])
        ]

    def iter_dependencies(self, extras: Collection[str] = ()) -> Iterable[Requirement]:
        contexts: Sequence[Dict[str, str]] = [{"extra": e} for e in extras]
        for req_string in self.metadata.get_all("Requires-Dist", []):
            # strip() because email.message.Message.get_all() may return a leading \n
            # in case a long header was wrapped.
            req = get_requirement(req_string.strip())
            if not req.marker:
                yield req
            elif not extras and req.marker.evaluate({"extra": ""}):
                yield req
            elif any(req.marker.evaluate(context) for context in contexts):
                yield req

# === NexusCore/openenv\Lib\site-packages\git\exc.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Exceptions thrown throughout the git package."""

__all__ = [
    # Defined in gitdb.exc:
    "AmbiguousObjectName",
    "BadName",
    "BadObject",
    "BadObjectType",
    "InvalidDBRoot",
    "ODBError",
    "ParseError",
    "UnsupportedOperation",
    # Introduced in this module:
    "GitError",
    "InvalidGitRepositoryError",
    "WorkTreeRepositoryUnsupported",
    "NoSuchPathError",
    "UnsafeProtocolError",
    "UnsafeOptionError",
    "CommandError",
    "GitCommandNotFound",
    "GitCommandError",
    "CheckoutError",
    "CacheError",
    "UnmergedEntriesError",
    "HookExecutionError",
    "RepositoryDirtyError",
]

from gitdb.exc import (
    AmbiguousObjectName,
    BadName,
    BadObject,
    BadObjectType,
    InvalidDBRoot,
    ODBError,
    ParseError,
    UnsupportedOperation,
)

from git.compat import safe_decode
from git.util import remove_password_if_present

# typing ----------------------------------------------------

from typing import List, Sequence, Tuple, TYPE_CHECKING, Union

from git.types import PathLike

if TYPE_CHECKING:
    from git.repo.base import Repo

# ------------------------------------------------------------------


class GitError(Exception):
    """Base class for all package exceptions."""


class InvalidGitRepositoryError(GitError):
    """Thrown if the given repository appears to have an invalid format."""


class WorkTreeRepositoryUnsupported(InvalidGitRepositoryError):
    """Thrown to indicate we can't handle work tree repositories."""


class NoSuchPathError(GitError, OSError):
    """Thrown if a path could not be access by the system."""


class UnsafeProtocolError(GitError):
    """Thrown if unsafe protocols are passed without being explicitly allowed."""


class UnsafeOptionError(GitError):
    """Thrown if unsafe options are passed without being explicitly allowed."""


class CommandError(GitError):
    """Base class for exceptions thrown at every stage of :class:`~subprocess.Popen`
    execution.

    :param command:
        A non-empty list of argv comprising the command-line.
    """

    _msg = "Cmd('%s') failed%s"
    """Format string with 2 ``%s`` for ``<cmdline>`` and the rest.

    For example: ``"'%s' failed%s"``

    Subclasses may override this attribute, provided it is still in this form.
    """

    def __init__(
        self,
        command: Union[List[str], Tuple[str, ...], str],
        status: Union[str, int, None, Exception] = None,
        stderr: Union[bytes, str, None] = None,
        stdout: Union[bytes, str, None] = None,
    ) -> None:
        if not isinstance(command, (tuple, list)):
            command = command.split()
        self.command = remove_password_if_present(command)
        self.status = status
        if status:
            if isinstance(status, Exception):
                status = "%s('%s')" % (type(status).__name__, safe_decode(str(status)))
            else:
                try:
                    status = "exit code(%s)" % int(status)
                except (ValueError, TypeError):
                    s = safe_decode(str(status))
                    status = "'%s'" % s if isinstance(status, str) else s

        self._cmd = safe_decode(self.command[0])
        self._cmdline = " ".join(safe_decode(i) for i in self.command)
        self._cause = status and " due to: %s" % status or "!"
        stdout_decode = safe_decode(stdout)
        stderr_decode = safe_decode(stderr)
        self.stdout = stdout_decode and "\n  stdout: '%s'" % stdout_decode or ""
        self.stderr = stderr_decode and "\n  stderr: '%s'" % stderr_decode or ""

    def __str__(self) -> str:
        return (self._msg + "\n  cmdline: %s%s%s") % (
            self._cmd,
            self._cause,
            self._cmdline,
            self.stdout,
            self.stderr,
        )


class GitCommandNotFound(CommandError):
    """Thrown if we cannot find the ``git`` executable in the :envvar:`PATH` or at the
    path given by the :envvar:`GIT_PYTHON_GIT_EXECUTABLE` environment variable."""

    def __init__(self, command: Union[List[str], Tuple[str], str], cause: Union[str, Exception]) -> None:
        super().__init__(command, cause)
        self._msg = "Cmd('%s') not found%s"


class GitCommandError(CommandError):
    """Thrown if execution of the git command fails with non-zero status code."""

    def __init__(
        self,
        command: Union[List[str], Tuple[str, ...], str],
        status: Union[str, int, None, Exception] = None,
        stderr: Union[bytes, str, None] = None,
        stdout: Union[bytes, str, None] = None,
    ) -> None:
        super().__init__(command, status, stderr, stdout)


class CheckoutError(GitError):
    """Thrown if a file could not be checked out from the index as it contained
    changes.

    The :attr:`failed_files` attribute contains a list of relative paths that failed to
    be checked out as they contained changes that did not exist in the index.

    The :attr:`failed_reasons` attribute contains a string informing about the actual
    cause of the issue.

    The :attr:`valid_files` attribute contains a list of relative paths to files that
    were checked out successfully and hence match the version stored in the index.
    """

    def __init__(
        self,
        message: str,
        failed_files: Sequence[PathLike],
        valid_files: Sequence[PathLike],
        failed_reasons: List[str],
    ) -> None:
        Exception.__init__(self, message)
        self.failed_files = failed_files
        self.failed_reasons = failed_reasons
        self.valid_files = valid_files

    def __str__(self) -> str:
        return Exception.__str__(self) + ":%s" % self.failed_files


class CacheError(GitError):
    """Base for all errors related to the git index, which is called "cache"
    internally."""


class UnmergedEntriesError(CacheError):
    """Thrown if an operation cannot proceed as there are still unmerged
    entries in the cache."""


class HookExecutionError(CommandError):
    """Thrown if a hook exits with a non-zero exit code.

    This provides access to the exit code and the string returned via standard output.
    """

    def __init__(
        self,
        command: Union[List[str], Tuple[str, ...], str],
        status: Union[str, int, None, Exception],
        stderr: Union[bytes, str, None] = None,
        stdout: Union[bytes, str, None] = None,
    ) -> None:
        super().__init__(command, status, stderr, stdout)
        self._msg = "Hook('%s') failed%s"


class RepositoryDirtyError(GitError):
    """Thrown whenever an operation on a repository fails as it has uncommitted changes
    that would be overwritten."""

    def __init__(self, repo: "Repo", message: str) -> None:
        self.repo = repo
        self.message = message

    def __str__(self) -> str:
        return "Operation cannot be performed on %r: %s" % (self.repo, self.message)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_headers.py ===
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
"""Contains utilities to handle headers to send in calls to Huggingface Hub."""

from typing import Dict, Optional, Union

from huggingface_hub.errors import LocalTokenNotFoundError

from .. import constants
from ._auth import get_token
from ._deprecation import _deprecate_arguments
from ._runtime import (
    get_fastai_version,
    get_fastcore_version,
    get_hf_hub_version,
    get_python_version,
    get_tf_version,
    get_torch_version,
    is_fastai_available,
    is_fastcore_available,
    is_tf_available,
    is_torch_available,
)
from ._validators import validate_hf_hub_args


@_deprecate_arguments(
    version="1.0",
    deprecated_args="is_write_action",
    custom_message="This argument is ignored and we let the server handle the permission error instead (if any).",
)
@validate_hf_hub_args
def build_hf_headers(
    *,
    token: Optional[Union[bool, str]] = None,
    library_name: Optional[str] = None,
    library_version: Optional[str] = None,
    user_agent: Union[Dict, str, None] = None,
    headers: Optional[Dict[str, str]] = None,
    is_write_action: bool = False,
) -> Dict[str, str]:
    """
    Build headers dictionary to send in a HF Hub call.

    By default, authorization token is always provided either from argument (explicit
    use) or retrieved from the cache (implicit use). To explicitly avoid sending the
    token to the Hub, set `token=False` or set the `HF_HUB_DISABLE_IMPLICIT_TOKEN`
    environment variable.

    In case of an API call that requires write access, an error is thrown if token is
    `None` or token is an organization token (starting with `"api_org***"`).

    In addition to the auth header, a user-agent is added to provide information about
    the installed packages (versions of python, huggingface_hub, torch, tensorflow,
    fastai and fastcore).

    Args:
        token (`str`, `bool`, *optional*):
            The token to be sent in authorization header for the Hub call:
                - if a string, it is used as the Hugging Face token
                - if `True`, the token is read from the machine (cache or env variable)
                - if `False`, authorization header is not set
                - if `None`, the token is read from the machine only except if
                  `HF_HUB_DISABLE_IMPLICIT_TOKEN` env variable is set.
        library_name (`str`, *optional*):
            The name of the library that is making the HTTP request. Will be added to
            the user-agent header.
        library_version (`str`, *optional*):
            The version of the library that is making the HTTP request. Will be added
            to the user-agent header.
        user_agent (`str`, `dict`, *optional*):
            The user agent info in the form of a dictionary or a single string. It will
            be completed with information about the installed packages.
        headers (`dict`, *optional*):
            Additional headers to include in the request. Those headers take precedence
            over the ones generated by this function.
        is_write_action (`bool`):
            Ignored and deprecated argument.

    Returns:
        A `Dict` of headers to pass in your API call.

    Example:
    ```py
        >>> build_hf_headers(token="hf_***") # explicit token
        {"authorization": "Bearer hf_***", "user-agent": ""}

        >>> build_hf_headers(token=True) # explicitly use cached token
        {"authorization": "Bearer hf_***",...}

        >>> build_hf_headers(token=False) # explicitly don't use cached token
        {"user-agent": ...}

        >>> build_hf_headers() # implicit use of the cached token
        {"authorization": "Bearer hf_***",...}

        # HF_HUB_DISABLE_IMPLICIT_TOKEN=True # to set as env variable
        >>> build_hf_headers() # token is not sent
        {"user-agent": ...}

        >>> build_hf_headers(library_name="transformers", library_version="1.2.3")
        {"authorization": ..., "user-agent": "transformers/1.2.3; hf_hub/0.10.2; python/3.10.4; tensorflow/1.55"}
    ```

    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If organization token is passed and "write" access is required.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If "write" access is required but token is not passed and not saved locally.
        [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
            If `token=True` but token is not saved locally.
    """
    # Get auth token to send
    token_to_send = get_token_to_send(token)

    # Combine headers
    hf_headers = {
        "user-agent": _http_user_agent(
            library_name=library_name,
            library_version=library_version,
            user_agent=user_agent,
        )
    }
    if token_to_send is not None:
        hf_headers["authorization"] = f"Bearer {token_to_send}"
    if headers is not None:
        hf_headers.update(headers)
    return hf_headers


def get_token_to_send(token: Optional[Union[bool, str]]) -> Optional[str]:
    """Select the token to send from either `token` or the cache."""
    # Case token is explicitly provided
    if isinstance(token, str):
        return token

    # Case token is explicitly forbidden
    if token is False:
        return None

    # Token is not provided: we get it from local cache
    cached_token = get_token()

    # Case token is explicitly required
    if token is True:
        if cached_token is None:
            raise LocalTokenNotFoundError(
                "Token is required (`token=True`), but no token found. You"
                " need to provide a token or be logged in to Hugging Face with"
                " `huggingface-cli login` or `huggingface_hub.login`. See"
                " https://huggingface.co/settings/tokens."
            )
        return cached_token

    # Case implicit use of the token is forbidden by env variable
    if constants.HF_HUB_DISABLE_IMPLICIT_TOKEN:
        return None

    # Otherwise: we use the cached token as the user has not explicitly forbidden it
    return cached_token


def _http_user_agent(
    *,
    library_name: Optional[str] = None,
    library_version: Optional[str] = None,
    user_agent: Union[Dict, str, None] = None,
) -> str:
    """Format a user-agent string containing information about the installed packages.

    Args:
        library_name (`str`, *optional*):
            The name of the library that is making the HTTP request.
        library_version (`str`, *optional*):
            The version of the library that is making the HTTP request.
        user_agent (`str`, `dict`, *optional*):
            The user agent info in the form of a dictionary or a single string.

    Returns:
        The formatted user-agent string.
    """
    if library_name is not None:
        ua = f"{library_name}/{library_version}"
    else:
        ua = "unknown/None"
    ua += f"; hf_hub/{get_hf_hub_version()}"
    ua += f"; python/{get_python_version()}"

    if not constants.HF_HUB_DISABLE_TELEMETRY:
        if is_torch_available():
            ua += f"; torch/{get_torch_version()}"
        if is_tf_available():
            ua += f"; tensorflow/{get_tf_version()}"
        if is_fastai_available():
            ua += f"; fastai/{get_fastai_version()}"
        if is_fastcore_available():
            ua += f"; fastcore/{get_fastcore_version()}"

    if isinstance(user_agent, dict):
        ua += "; " + "; ".join(f"{k}/{v}" for k, v in user_agent.items())
    elif isinstance(user_agent, str):
        ua += "; " + user_agent

    # Retrieve user-agent origin headers from environment variable
    origin = constants.HF_HUB_USER_AGENT_ORIGIN
    if origin is not None:
        ua += "; origin/" + origin

    return _deduplicate_user_agent(ua)


def _deduplicate_user_agent(user_agent: str) -> str:
    """Deduplicate redundant information in the generated user-agent."""
    # Split around ";" > Strip whitespaces > Store as dict keys (ensure unicity) > format back as string
    # Order is implicitly preserved by dictionary structure (see https://stackoverflow.com/a/53657523).
    return "; ".join({key.strip(): None for key in user_agent.split(";")}.keys())

# === NexusCore/openenv\Lib\site-packages\litellm\llms\nlp_cloud\chat\transformation.py ===
import json
import time
from typing import TYPE_CHECKING, Any, List, Optional, Union

import httpx

from litellm.litellm_core_utils.prompt_templates.common_utils import (
    convert_content_list_to_str,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.openai import AllMessageValues
from litellm.utils import ModelResponse, Usage

from ..common_utils import NLPCloudError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any


class NLPCloudConfig(BaseConfig):
    """
    Reference: https://docs.nlpcloud.com/#generation

    - `max_length` (int): Optional. The maximum number of tokens that the generated text should contain.

    - `length_no_input` (boolean): Optional. Whether `min_length` and `max_length` should not include the length of the input text.

    - `end_sequence` (string): Optional. A specific token that should be the end of the generated sequence.

    - `remove_end_sequence` (boolean): Optional. Whether to remove the `end_sequence` string from the result.

    - `remove_input` (boolean): Optional. Whether to remove the input text from the result.

    - `bad_words` (list of strings): Optional. List of tokens that are not allowed to be generated.

    - `temperature` (float): Optional. Temperature sampling. It modulates the next token probabilities.

    - `top_p` (float): Optional. Top P sampling. Below 1, only the most probable tokens with probabilities that add up to top_p or higher are kept for generation.

    - `top_k` (int): Optional. Top K sampling. The number of highest probability vocabulary tokens to keep for top k filtering.

    - `repetition_penalty` (float): Optional. Prevents the same word from being repeated too many times.

    - `num_beams` (int): Optional. Number of beams for beam search.

    - `num_return_sequences` (int): Optional. The number of independently computed returned sequences.
    """

    max_length: Optional[int] = None
    length_no_input: Optional[bool] = None
    end_sequence: Optional[str] = None
    remove_end_sequence: Optional[bool] = None
    remove_input: Optional[bool] = None
    bad_words: Optional[list] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    repetition_penalty: Optional[float] = None
    num_beams: Optional[int] = None
    num_return_sequences: Optional[int] = None

    def __init__(
        self,
        max_length: Optional[int] = None,
        length_no_input: Optional[bool] = None,
        end_sequence: Optional[str] = None,
        remove_end_sequence: Optional[bool] = None,
        remove_input: Optional[bool] = None,
        bad_words: Optional[list] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        num_beams: Optional[int] = None,
        num_return_sequences: Optional[int] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

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
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Token {api_key}"
        return headers

    def get_supported_openai_params(self, model: str) -> List:
        return [
            "max_tokens",
            "stream",
            "temperature",
            "top_p",
            "presence_penalty",
            "frequency_penalty",
            "n",
            "stop",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "max_tokens":
                optional_params["max_length"] = value
            if param == "stream":
                optional_params["stream"] = value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["top_p"] = value
            if param == "presence_penalty":
                optional_params["presence_penalty"] = value
            if param == "frequency_penalty":
                optional_params["frequency_penalty"] = value
            if param == "n":
                optional_params["num_return_sequences"] = value
            if param == "stop":
                optional_params["stop_sequences"] = value
        return optional_params

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return NLPCloudError(
            status_code=status_code, message=error_message, headers=headers
        )

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        text = " ".join(convert_content_list_to_str(message) for message in messages)

        data = {
            "text": text,
            **optional_params,
        }

        return data

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LoggingClass,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        ## LOGGING
        logging_obj.post_call(
            input=None,
            api_key=api_key,
            original_response=raw_response.text,
            additional_args={"complete_input_dict": request_data},
        )

        ## RESPONSE OBJECT
        try:
            completion_response = raw_response.json()
        except Exception:
            raise NLPCloudError(
                message=raw_response.text, status_code=raw_response.status_code
            )
        if "error" in completion_response:
            raise NLPCloudError(
                message=completion_response["error"],
                status_code=raw_response.status_code,
            )
        else:
            try:
                if len(completion_response["generated_text"]) > 0:
                    model_response.choices[0].message.content = (  # type: ignore
                        completion_response["generated_text"]
                    )
            except Exception:
                raise NLPCloudError(
                    message=json.dumps(completion_response),
                    status_code=raw_response.status_code,
                )

        ## CALCULATING USAGE - baseten charges on time, not tokens - have some mapping of cost here.
        prompt_tokens = completion_response["nb_input_tokens"]
        completion_tokens = completion_response["nb_generated_tokens"]

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        return model_response

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_hooks\aporia_ai.py ===
# +-------------------------------------------------------------+
#
#           Use AporiaAI for your LLM calls
#
# +-------------------------------------------------------------+
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import os
import sys

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import json
import sys
from typing import Any, List, Literal, Optional

from fastapi import HTTPException

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_guardrail import (
    CustomGuardrail,
    log_guardrail_information,
)
from litellm.litellm_core_utils.logging_utils import (
    convert_litellm_response_object_to_str,
)
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import UserAPIKeyAuth
from litellm.proxy.guardrails.guardrail_helpers import should_proceed_based_on_metadata
from litellm.types.guardrails import GuardrailEventHooks

litellm.set_verbose = True

GUARDRAIL_NAME = "aporia"


class AporiaGuardrail(CustomGuardrail):
    def __init__(
        self, api_key: Optional[str] = None, api_base: Optional[str] = None, **kwargs
    ):
        self.async_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.GuardrailCallback
        )
        self.aporia_api_key = api_key or os.environ["APORIO_API_KEY"]
        self.aporia_api_base = api_base or os.environ["APORIO_API_BASE"]
        super().__init__(**kwargs)

    #### CALL HOOKS - proxy only ####
    def transform_messages(self, messages: List[dict]) -> List[dict]:
        supported_openai_roles = ["system", "user", "assistant"]
        default_role = "other"  # for unsupported roles - e.g. tool
        new_messages = []
        for m in messages:
            if m.get("role", "") in supported_openai_roles:
                new_messages.append(m)
            else:
                new_messages.append(
                    {
                        "role": default_role,
                        **{key: value for key, value in m.items() if key != "role"},
                    }
                )

        return new_messages

    async def prepare_aporia_request(
        self, new_messages: List[dict], response_string: Optional[str] = None
    ) -> dict:
        data: dict[str, Any] = {}
        if new_messages is not None:
            data["messages"] = new_messages
        if response_string is not None:
            data["response"] = response_string

        # Set validation target
        if new_messages and response_string:
            data["validation_target"] = "both"
        elif new_messages:
            data["validation_target"] = "prompt"
        elif response_string:
            data["validation_target"] = "response"

        verbose_proxy_logger.debug("Aporia AI request: %s", data)
        return data

    async def make_aporia_api_request(
        self,
        request_data: dict,
        new_messages: List[dict],
        response_string: Optional[str] = None,
    ):
        data = await self.prepare_aporia_request(
            new_messages=new_messages, response_string=response_string
        )

        data.update(
            self.get_guardrail_dynamic_request_body_params(request_data=request_data)
        )

        _json_data = json.dumps(data)

        """
        export APORIO_API_KEY=<your key>
        curl https://gr-prd-trial.aporia.com/some-id \
            -X POST \
            -H "X-APORIA-API-KEY: $APORIO_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{
                "messages": [
                    {
                    "role": "user",
                    "content": "This is a test prompt"
                    }
                ],
                }
'
        """

        response = await self.async_handler.post(
            url=self.aporia_api_base + "/validate",
            data=_json_data,
            headers={
                "X-APORIA-API-KEY": self.aporia_api_key,
                "Content-Type": "application/json",
            },
        )
        verbose_proxy_logger.debug("Aporia AI response: %s", response.text)
        if response.status_code == 200:
            # check if the response was flagged
            _json_response = response.json()
            action: str = _json_response.get(
                "action"
            )  # possible values are modify, passthrough, block, rephrase
            if action == "block":
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Violated guardrail policy",
                        "aporia_ai_response": _json_response,
                    },
                )

    @log_guardrail_information
    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        response,
    ):
        from litellm.proxy.common_utils.callback_utils import (
            add_guardrail_to_applied_guardrails_header,
        )

        """
        Use this for the post call moderation with Guardrails
        """
        event_type: GuardrailEventHooks = GuardrailEventHooks.post_call
        if self.should_run_guardrail(data=data, event_type=event_type) is not True:
            return

        response_str: Optional[str] = convert_litellm_response_object_to_str(response)
        if response_str is not None:
            await self.make_aporia_api_request(
                request_data=data,
                response_string=response_str,
                new_messages=data.get("messages", []),
            )

            add_guardrail_to_applied_guardrails_header(
                request_data=data, guardrail_name=self.guardrail_name
            )

        pass

    @log_guardrail_information
    async def async_moderation_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        call_type: Literal[
            "completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "responses",
        ],
    ):
        from litellm.proxy.common_utils.callback_utils import (
            add_guardrail_to_applied_guardrails_header,
        )

        event_type: GuardrailEventHooks = GuardrailEventHooks.during_call
        if self.should_run_guardrail(data=data, event_type=event_type) is not True:
            return

        # old implementation - backwards compatibility
        if (
            await should_proceed_based_on_metadata(
                data=data,
                guardrail_name=GUARDRAIL_NAME,
            )
            is False
        ):
            return

        new_messages: Optional[List[dict]] = None
        if "messages" in data and isinstance(data["messages"], list):
            new_messages = self.transform_messages(messages=data["messages"])

        if new_messages is not None:
            await self.make_aporia_api_request(
                request_data=data,
                new_messages=new_messages,
            )
            add_guardrail_to_applied_guardrails_header(
                request_data=data, guardrail_name=self.guardrail_name
            )
        else:
            verbose_proxy_logger.warning(
                "Aporia AI: not running guardrail. No messages in data"
            )
            pass

# === NexusCore/openenv\Lib\site-packages\nltk\metrics\scores.py ===
# Natural Language Toolkit: Evaluation
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import operator
from functools import reduce
from math import fabs
from random import shuffle

try:
    from scipy.stats.stats import betai
except ImportError:
    betai = None

from nltk.util import LazyConcatenation, LazyMap


def accuracy(reference, test):
    """
    Given a list of reference values and a corresponding list of test
    values, return the fraction of corresponding values that are
    equal.  In particular, return the fraction of indices
    ``0<i<=len(test)`` such that ``test[i] == reference[i]``.

    :type reference: list
    :param reference: An ordered list of reference values.
    :type test: list
    :param test: A list of values to compare against the corresponding
        reference values.
    :raise ValueError: If ``reference`` and ``length`` do not have the
        same length.
    """
    if len(reference) != len(test):
        raise ValueError("Lists must have the same length.")
    return sum(x == y for x, y in zip(reference, test)) / len(test)


def precision(reference, test):
    """
    Given a set of reference values and a set of test values, return
    the fraction of test values that appear in the reference set.
    In particular, return card(``reference`` intersection ``test``)/card(``test``).
    If ``test`` is empty, then return None.

    :type reference: set
    :param reference: A set of reference values.
    :type test: set
    :param test: A set of values to compare against the reference set.
    :rtype: float or None
    """
    if not hasattr(reference, "intersection") or not hasattr(test, "intersection"):
        raise TypeError("reference and test should be sets")

    if len(test) == 0:
        return None
    else:
        return len(reference.intersection(test)) / len(test)


def recall(reference, test):
    """
    Given a set of reference values and a set of test values, return
    the fraction of reference values that appear in the test set.
    In particular, return card(``reference`` intersection ``test``)/card(``reference``).
    If ``reference`` is empty, then return None.

    :type reference: set
    :param reference: A set of reference values.
    :type test: set
    :param test: A set of values to compare against the reference set.
    :rtype: float or None
    """
    if not hasattr(reference, "intersection") or not hasattr(test, "intersection"):
        raise TypeError("reference and test should be sets")

    if len(reference) == 0:
        return None
    else:
        return len(reference.intersection(test)) / len(reference)


def f_measure(reference, test, alpha=0.5):
    """
    Given a set of reference values and a set of test values, return
    the f-measure of the test values, when compared against the
    reference values.  The f-measure is the harmonic mean of the
    ``precision`` and ``recall``, weighted by ``alpha``.  In particular,
    given the precision *p* and recall *r* defined by:

    - *p* = card(``reference`` intersection ``test``)/card(``test``)
    - *r* = card(``reference`` intersection ``test``)/card(``reference``)

    The f-measure is:

    - *1/(alpha/p + (1-alpha)/r)*

    If either ``reference`` or ``test`` is empty, then ``f_measure``
    returns None.

    :type reference: set
    :param reference: A set of reference values.
    :type test: set
    :param test: A set of values to compare against the reference set.
    :rtype: float or None
    """
    p = precision(reference, test)
    r = recall(reference, test)
    if p is None or r is None:
        return None
    if p == 0 or r == 0:
        return 0
    return 1.0 / (alpha / p + (1 - alpha) / r)


def log_likelihood(reference, test):
    """
    Given a list of reference values and a corresponding list of test
    probability distributions, return the average log likelihood of
    the reference values, given the probability distributions.

    :param reference: A list of reference values
    :type reference: list
    :param test: A list of probability distributions over values to
        compare against the corresponding reference values.
    :type test: list(ProbDistI)
    """
    if len(reference) != len(test):
        raise ValueError("Lists must have the same length.")

    # Return the average value of dist.logprob(val).
    total_likelihood = sum(dist.logprob(val) for (val, dist) in zip(reference, test))
    return total_likelihood / len(reference)


def approxrand(a, b, **kwargs):
    """
    Returns an approximate significance level between two lists of
    independently generated test values.

    Approximate randomization calculates significance by randomly drawing
    from a sample of the possible permutations. At the limit of the number
    of possible permutations, the significance level is exact. The
    approximate significance level is the sample mean number of times the
    statistic of the permutated lists varies from the actual statistic of
    the unpermuted argument lists.

    :return: a tuple containing an approximate significance level, the count
             of the number of times the pseudo-statistic varied from the
             actual statistic, and the number of shuffles
    :rtype: tuple
    :param a: a list of test values
    :type a: list
    :param b: another list of independently generated test values
    :type b: list
    """
    shuffles = kwargs.get("shuffles", 999)
    # there's no point in trying to shuffle beyond all possible permutations
    shuffles = min(shuffles, reduce(operator.mul, range(1, len(a) + len(b) + 1)))
    stat = kwargs.get("statistic", lambda lst: sum(lst) / len(lst))
    verbose = kwargs.get("verbose", False)

    if verbose:
        print("shuffles: %d" % shuffles)

    actual_stat = fabs(stat(a) - stat(b))

    if verbose:
        print("actual statistic: %f" % actual_stat)
        print("-" * 60)

    c = 1e-100
    lst = LazyConcatenation([a, b])
    indices = list(range(len(a) + len(b)))

    for i in range(shuffles):
        if verbose and i % 10 == 0:
            print("shuffle: %d" % i)

        shuffle(indices)

        pseudo_stat_a = stat(LazyMap(lambda i: lst[i], indices[: len(a)]))
        pseudo_stat_b = stat(LazyMap(lambda i: lst[i], indices[len(a) :]))
        pseudo_stat = fabs(pseudo_stat_a - pseudo_stat_b)

        if pseudo_stat >= actual_stat:
            c += 1

        if verbose and i % 10 == 0:
            print("pseudo-statistic: %f" % pseudo_stat)
            print("significance: %f" % ((c + 1) / (i + 1)))
            print("-" * 60)

    significance = (c + 1) / (shuffles + 1)

    if verbose:
        print("significance: %f" % significance)
        if betai:
            for phi in [0.01, 0.05, 0.10, 0.15, 0.25, 0.50]:
                print(f"prob(phi<={phi:f}): {betai(c, shuffles, phi):f}")

    return (significance, c, shuffles)


def demo():
    print("-" * 75)
    reference = "DET NN VB DET JJ NN NN IN DET NN".split()
    test = "DET VB VB DET NN NN NN IN DET NN".split()
    print("Reference =", reference)
    print("Test    =", test)
    print("Accuracy:", accuracy(reference, test))

    print("-" * 75)
    reference_set = set(reference)
    test_set = set(test)
    print("Reference =", reference_set)
    print("Test =   ", test_set)
    print("Precision:", precision(reference_set, test_set))
    print("   Recall:", recall(reference_set, test_set))
    print("F-Measure:", f_measure(reference_set, test_set))
    print("-" * 75)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\cache.py ===
import os
import textwrap
from optparse import Values
from typing import Any, List

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, PipError
from pip._internal.utils import filesystem
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import format_size

logger = getLogger(__name__)


class CacheCommand(Command):
    """
    Inspect and manage pip's wheel cache.

    Subcommands:

    - dir: Show the cache directory.
    - info: Show information about the cache.
    - list: List filenames of packages stored in the cache.
    - remove: Remove one or more package from the cache.
    - purge: Remove all items from the cache.

    ``<pattern>`` can be a glob expression or a package name.
    """

    ignore_require_venv = True
    usage = """
        %prog dir
        %prog info
        %prog list [<pattern>] [--format=[human, abspath]]
        %prog remove <pattern>
        %prog purge
    """

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "--format",
            action="store",
            dest="list_format",
            default="human",
            choices=("human", "abspath"),
            help="Select the output format among: human (default) or abspath",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        handlers = {
            "dir": self.get_cache_dir,
            "info": self.get_cache_info,
            "list": self.list_cache_items,
            "remove": self.remove_cache_items,
            "purge": self.purge_cache,
        }

        if not options.cache_dir:
            logger.error("pip cache commands can not function since cache is disabled.")
            return ERROR

        # Determine action
        if not args or args[0] not in handlers:
            logger.error(
                "Need an action (%s) to perform.",
                ", ".join(sorted(handlers)),
            )
            return ERROR

        action = args[0]

        # Error handling happens here, not in the action-handlers.
        try:
            handlers[action](options, args[1:])
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

    def get_cache_dir(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        logger.info(options.cache_dir)

    def get_cache_info(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        num_http_files = len(self._find_http_files(options))
        num_packages = len(self._find_wheels(options, "*"))

        http_cache_location = self._cache_dir(options, "http-v2")
        old_http_cache_location = self._cache_dir(options, "http")
        wheels_cache_location = self._cache_dir(options, "wheels")
        http_cache_size = filesystem.format_size(
            filesystem.directory_size(http_cache_location)
            + filesystem.directory_size(old_http_cache_location)
        )
        wheels_cache_size = filesystem.format_directory_size(wheels_cache_location)

        message = (
            textwrap.dedent(
                """
                    Package index page cache location (pip v23.3+): {http_cache_location}
                    Package index page cache location (older pips): {old_http_cache_location}
                    Package index page cache size: {http_cache_size}
                    Number of HTTP files: {num_http_files}
                    Locally built wheels location: {wheels_cache_location}
                    Locally built wheels size: {wheels_cache_size}
                    Number of locally built wheels: {package_count}
                """  # noqa: E501
            )
            .format(
                http_cache_location=http_cache_location,
                old_http_cache_location=old_http_cache_location,
                http_cache_size=http_cache_size,
                num_http_files=num_http_files,
                wheels_cache_location=wheels_cache_location,
                package_count=num_packages,
                wheels_cache_size=wheels_cache_size,
            )
            .strip()
        )

        logger.info(message)

    def list_cache_items(self, options: Values, args: List[Any]) -> None:
        if len(args) > 1:
            raise CommandError("Too many arguments")

        if args:
            pattern = args[0]
        else:
            pattern = "*"

        files = self._find_wheels(options, pattern)
        if options.list_format == "human":
            self.format_for_human(files)
        else:
            self.format_for_abspath(files)

    def format_for_human(self, files: List[str]) -> None:
        if not files:
            logger.info("No locally built wheels cached.")
            return

        results = []
        for filename in files:
            wheel = os.path.basename(filename)
            size = filesystem.format_file_size(filename)
            results.append(f" - {wheel} ({size})")
        logger.info("Cache contents:\n")
        logger.info("\n".join(sorted(results)))

    def format_for_abspath(self, files: List[str]) -> None:
        if files:
            logger.info("\n".join(sorted(files)))

    def remove_cache_items(self, options: Values, args: List[Any]) -> None:
        if len(args) > 1:
            raise CommandError("Too many arguments")

        if not args:
            raise CommandError("Please provide a pattern")

        files = self._find_wheels(options, args[0])

        no_matching_msg = "No matching packages"
        if args[0] == "*":
            # Only fetch http files if no specific pattern given
            files += self._find_http_files(options)
        else:
            # Add the pattern to the log message
            no_matching_msg += f' for pattern "{args[0]}"'

        if not files:
            logger.warning(no_matching_msg)

        bytes_removed = 0
        for filename in files:
            bytes_removed += os.stat(filename).st_size
            os.unlink(filename)
            logger.verbose("Removed %s", filename)
        logger.info("Files removed: %s (%s)", len(files), format_size(bytes_removed))

    def purge_cache(self, options: Values, args: List[Any]) -> None:
        if args:
            raise CommandError("Too many arguments")

        return self.remove_cache_items(options, ["*"])

    def _cache_dir(self, options: Values, subdir: str) -> str:
        return os.path.join(options.cache_dir, subdir)

    def _find_http_files(self, options: Values) -> List[str]:
        old_http_dir = self._cache_dir(options, "http")
        new_http_dir = self._cache_dir(options, "http-v2")
        return filesystem.find_files(old_http_dir, "*") + filesystem.find_files(
            new_http_dir, "*"
        )

    def _find_wheels(self, options: Values, pattern: str) -> List[str]:
        wheel_dir = self._cache_dir(options, "wheels")

        # The wheel filename format, as specified in PEP 427, is:
        #     {distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
        #
        # Additionally, non-alphanumeric values in the distribution are
        # normalized to underscores (_), meaning hyphens can never occur
        # before `-{version}`.
        #
        # Given that information:
        # - If the pattern we're given contains a hyphen (-), the user is
        #   providing at least the version. Thus, we can just append `*.whl`
        #   to match the rest of it.
        # - If the pattern we're given doesn't contain a hyphen (-), the
        #   user is only providing the name. Thus, we append `-*.whl` to
        #   match the hyphen before the version, followed by anything else.
        #
        # PEP 427: https://www.python.org/dev/peps/pep-0427/
        pattern = pattern + ("*.whl" if "-" in pattern else "-*.whl")

        return filesystem.find_files(wheel_dir, pattern)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\metadata\importlib\_dists.py ===
import email.message
import importlib.metadata
import pathlib
import zipfile
from os import PathLike
from typing import (
    Collection,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    Union,
    cast,
)

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.exceptions import InvalidWheel, UnsupportedWheel
from pip._internal.metadata.base import (
    BaseDistribution,
    BaseEntryPoint,
    InfoPath,
    Wheel,
)
from pip._internal.utils.misc import normalize_path
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.wheel import parse_wheel, read_wheel_metadata_file

from ._compat import (
    BasePath,
    get_dist_canonical_name,
    parse_name_and_version_from_info_directory,
)


class WheelDistribution(importlib.metadata.Distribution):
    """An ``importlib.metadata.Distribution`` read from a wheel.

    Although ``importlib.metadata.PathDistribution`` accepts ``zipfile.Path``,
    its implementation is too "lazy" for pip's needs (we can't keep the ZipFile
    handle open for the entire lifetime of the distribution object).

    This implementation eagerly reads the entire metadata directory into the
    memory instead, and operates from that.
    """

    def __init__(
        self,
        files: Mapping[pathlib.PurePosixPath, bytes],
        info_location: pathlib.PurePosixPath,
    ) -> None:
        self._files = files
        self.info_location = info_location

    @classmethod
    def from_zipfile(
        cls,
        zf: zipfile.ZipFile,
        name: str,
        location: str,
    ) -> "WheelDistribution":
        info_dir, _ = parse_wheel(zf, name)
        paths = (
            (name, pathlib.PurePosixPath(name.split("/", 1)[-1]))
            for name in zf.namelist()
            if name.startswith(f"{info_dir}/")
        )
        files = {
            relpath: read_wheel_metadata_file(zf, fullpath)
            for fullpath, relpath in paths
        }
        info_location = pathlib.PurePosixPath(location, info_dir)
        return cls(files, info_location)

    def iterdir(self, path: InfoPath) -> Iterator[pathlib.PurePosixPath]:
        # Only allow iterating through the metadata directory.
        if pathlib.PurePosixPath(str(path)) in self._files:
            return iter(self._files)
        raise FileNotFoundError(path)

    def read_text(self, filename: str) -> Optional[str]:
        try:
            data = self._files[pathlib.PurePosixPath(filename)]
        except KeyError:
            return None
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as e:
            wheel = self.info_location.parent
            error = f"Error decoding metadata for {wheel}: {e} in {filename} file"
            raise UnsupportedWheel(error)
        return text

    def locate_file(self, path: Union[str, "PathLike[str]"]) -> pathlib.Path:
        # This method doesn't make sense for our in-memory wheel, but the API
        # requires us to define it.
        raise NotImplementedError


class Distribution(BaseDistribution):
    def __init__(
        self,
        dist: importlib.metadata.Distribution,
        info_location: Optional[BasePath],
        installed_location: Optional[BasePath],
    ) -> None:
        self._dist = dist
        self._info_location = info_location
        self._installed_location = installed_location

    @classmethod
    def from_directory(cls, directory: str) -> BaseDistribution:
        info_location = pathlib.Path(directory)
        dist = importlib.metadata.Distribution.at(info_location)
        return cls(dist, info_location, info_location.parent)

    @classmethod
    def from_metadata_file_contents(
        cls,
        metadata_contents: bytes,
        filename: str,
        project_name: str,
    ) -> BaseDistribution:
        # Generate temp dir to contain the metadata file, and write the file contents.
        temp_dir = pathlib.Path(
            TempDirectory(kind="metadata", globally_managed=True).path
        )
        metadata_path = temp_dir / "METADATA"
        metadata_path.write_bytes(metadata_contents)
        # Construct dist pointing to the newly created directory.
        dist = importlib.metadata.Distribution.at(metadata_path.parent)
        return cls(dist, metadata_path.parent, None)

    @classmethod
    def from_wheel(cls, wheel: Wheel, name: str) -> BaseDistribution:
        try:
            with wheel.as_zipfile() as zf:
                dist = WheelDistribution.from_zipfile(zf, name, wheel.location)
        except zipfile.BadZipFile as e:
            raise InvalidWheel(wheel.location, name) from e
        return cls(dist, dist.info_location, pathlib.PurePosixPath(wheel.location))

    @property
    def location(self) -> Optional[str]:
        if self._info_location is None:
            return None
        return str(self._info_location.parent)

    @property
    def info_location(self) -> Optional[str]:
        if self._info_location is None:
            return None
        return str(self._info_location)

    @property
    def installed_location(self) -> Optional[str]:
        if self._installed_location is None:
            return None
        return normalize_path(str(self._installed_location))

    @property
    def canonical_name(self) -> NormalizedName:
        return get_dist_canonical_name(self._dist)

    @property
    def version(self) -> Version:
        if version := parse_name_and_version_from_info_directory(self._dist)[1]:
            return parse_version(version)
        return parse_version(self._dist.version)

    @property
    def raw_version(self) -> str:
        return self._dist.version

    def is_file(self, path: InfoPath) -> bool:
        return self._dist.read_text(str(path)) is not None

    def iter_distutils_script_names(self) -> Iterator[str]:
        # A distutils installation is always "flat" (not in e.g. egg form), so
        # if this distribution's info location is NOT a pathlib.Path (but e.g.
        # zipfile.Path), it can never contain any distutils scripts.
        if not isinstance(self._info_location, pathlib.Path):
            return
        for child in self._info_location.joinpath("scripts").iterdir():
            yield child.name

    def read_text(self, path: InfoPath) -> str:
        content = self._dist.read_text(str(path))
        if content is None:
            raise FileNotFoundError(path)
        return content

    def iter_entry_points(self) -> Iterable[BaseEntryPoint]:
        # importlib.metadata's EntryPoint structure satisfies BaseEntryPoint.
        return self._dist.entry_points

    def _metadata_impl(self) -> email.message.Message:
        # From Python 3.10+, importlib.metadata declares PackageMetadata as the
        # return type. This protocol is unfortunately a disaster now and misses
        # a ton of fields that we need, including get() and get_payload(). We
        # rely on the implementation that the object is actually a Message now,
        # until upstream can improve the protocol. (python/cpython#94952)
        return cast(email.message.Message, self._dist.metadata)

    def iter_provided_extras(self) -> Iterable[NormalizedName]:
        return [
            canonicalize_name(extra)
            for extra in self.metadata.get_all("Provides-Extra", [])
        ]

    def iter_dependencies(self, extras: Collection[str] = ()) -> Iterable[Requirement]:
        contexts: Sequence[Dict[str, str]] = [{"extra": e} for e in extras]
        for req_string in self.metadata.get_all("Requires-Dist", []):
            # strip() because email.message.Message.get_all() may return a leading \n
            # in case a long header was wrapped.
            req = get_requirement(req_string.strip())
            if not req.marker:
                yield req
            elif not extras and req.marker.evaluate({"extra": ""}):
                yield req
            elif any(req.marker.evaluate(context) for context in contexts):
                yield req

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_mock_val_ser.py ===
from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any, Callable, Generic, Literal, TypeVar, Union

from pydantic_core import CoreSchema, SchemaSerializer, SchemaValidator

from ..errors import PydanticErrorCodes, PydanticUserError
from ..plugin._schema_validator import PluggableSchemaValidator

if TYPE_CHECKING:
    from ..dataclasses import PydanticDataclass
    from ..main import BaseModel
    from ..type_adapter import TypeAdapter


ValSer = TypeVar('ValSer', bound=Union[SchemaValidator, PluggableSchemaValidator, SchemaSerializer])
T = TypeVar('T')


class MockCoreSchema(Mapping[str, Any]):
    """Mocker for `pydantic_core.CoreSchema` which optionally attempts to
    rebuild the thing it's mocking when one of its methods is accessed and raises an error if that fails.
    """

    __slots__ = '_error_message', '_code', '_attempt_rebuild', '_built_memo'

    def __init__(
        self,
        error_message: str,
        *,
        code: PydanticErrorCodes,
        attempt_rebuild: Callable[[], CoreSchema | None] | None = None,
    ) -> None:
        self._error_message = error_message
        self._code: PydanticErrorCodes = code
        self._attempt_rebuild = attempt_rebuild
        self._built_memo: CoreSchema | None = None

    def __getitem__(self, key: str) -> Any:
        return self._get_built().__getitem__(key)

    def __len__(self) -> int:
        return self._get_built().__len__()

    def __iter__(self) -> Iterator[str]:
        return self._get_built().__iter__()

    def _get_built(self) -> CoreSchema:
        if self._built_memo is not None:
            return self._built_memo

        if self._attempt_rebuild:
            schema = self._attempt_rebuild()
            if schema is not None:
                self._built_memo = schema
                return schema
        raise PydanticUserError(self._error_message, code=self._code)

    def rebuild(self) -> CoreSchema | None:
        self._built_memo = None
        if self._attempt_rebuild:
            schema = self._attempt_rebuild()
            if schema is not None:
                return schema
            else:
                raise PydanticUserError(self._error_message, code=self._code)
        return None


class MockValSer(Generic[ValSer]):
    """Mocker for `pydantic_core.SchemaValidator` or `pydantic_core.SchemaSerializer` which optionally attempts to
    rebuild the thing it's mocking when one of its methods is accessed and raises an error if that fails.
    """

    __slots__ = '_error_message', '_code', '_val_or_ser', '_attempt_rebuild'

    def __init__(
        self,
        error_message: str,
        *,
        code: PydanticErrorCodes,
        val_or_ser: Literal['validator', 'serializer'],
        attempt_rebuild: Callable[[], ValSer | None] | None = None,
    ) -> None:
        self._error_message = error_message
        self._val_or_ser = SchemaValidator if val_or_ser == 'validator' else SchemaSerializer
        self._code: PydanticErrorCodes = code
        self._attempt_rebuild = attempt_rebuild

    def __getattr__(self, item: str) -> None:
        __tracebackhide__ = True
        if self._attempt_rebuild:
            val_ser = self._attempt_rebuild()
            if val_ser is not None:
                return getattr(val_ser, item)

        # raise an AttributeError if `item` doesn't exist
        getattr(self._val_or_ser, item)
        raise PydanticUserError(self._error_message, code=self._code)

    def rebuild(self) -> ValSer | None:
        if self._attempt_rebuild:
            val_ser = self._attempt_rebuild()
            if val_ser is not None:
                return val_ser
            else:
                raise PydanticUserError(self._error_message, code=self._code)
        return None


def set_type_adapter_mocks(adapter: TypeAdapter) -> None:
    """Set `core_schema`, `validator` and `serializer` to mock core types on a type adapter instance.

    Args:
        adapter: The type adapter instance to set the mocks on
    """
    type_repr = str(adapter._type)
    undefined_type_error_message = (
        f'`TypeAdapter[{type_repr}]` is not fully defined; you should define `{type_repr}` and all referenced types,'
        f' then call `.rebuild()` on the instance.'
    )

    def attempt_rebuild_fn(attr_fn: Callable[[TypeAdapter], T]) -> Callable[[], T | None]:
        def handler() -> T | None:
            if adapter.rebuild(raise_errors=False, _parent_namespace_depth=5) is not False:
                return attr_fn(adapter)
            return None

        return handler

    adapter.core_schema = MockCoreSchema(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        attempt_rebuild=attempt_rebuild_fn(lambda ta: ta.core_schema),
    )
    adapter.validator = MockValSer(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        val_or_ser='validator',
        attempt_rebuild=attempt_rebuild_fn(lambda ta: ta.validator),
    )
    adapter.serializer = MockValSer(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        val_or_ser='serializer',
        attempt_rebuild=attempt_rebuild_fn(lambda ta: ta.serializer),
    )


def set_model_mocks(cls: type[BaseModel], undefined_name: str = 'all referenced types') -> None:
    """Set `__pydantic_core_schema__`, `__pydantic_validator__` and `__pydantic_serializer__` to mock core types on a model.

    Args:
        cls: The model class to set the mocks on
        undefined_name: Name of the undefined thing, used in error messages
    """
    undefined_type_error_message = (
        f'`{cls.__name__}` is not fully defined; you should define {undefined_name},'
        f' then call `{cls.__name__}.model_rebuild()`.'
    )

    def attempt_rebuild_fn(attr_fn: Callable[[type[BaseModel]], T]) -> Callable[[], T | None]:
        def handler() -> T | None:
            if cls.model_rebuild(raise_errors=False, _parent_namespace_depth=5) is not False:
                return attr_fn(cls)
            return None

        return handler

    cls.__pydantic_core_schema__ = MockCoreSchema(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        attempt_rebuild=attempt_rebuild_fn(lambda c: c.__pydantic_core_schema__),
    )
    cls.__pydantic_validator__ = MockValSer(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        val_or_ser='validator',
        attempt_rebuild=attempt_rebuild_fn(lambda c: c.__pydantic_validator__),
    )
    cls.__pydantic_serializer__ = MockValSer(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        val_or_ser='serializer',
        attempt_rebuild=attempt_rebuild_fn(lambda c: c.__pydantic_serializer__),
    )


def set_dataclass_mocks(cls: type[PydanticDataclass], undefined_name: str = 'all referenced types') -> None:
    """Set `__pydantic_validator__` and `__pydantic_serializer__` to `MockValSer`s on a dataclass.

    Args:
        cls: The model class to set the mocks on
        undefined_name: Name of the undefined thing, used in error messages
    """
    from ..dataclasses import rebuild_dataclass

    undefined_type_error_message = (
        f'`{cls.__name__}` is not fully defined; you should define {undefined_name},'
        f' then call `pydantic.dataclasses.rebuild_dataclass({cls.__name__})`.'
    )

    def attempt_rebuild_fn(attr_fn: Callable[[type[PydanticDataclass]], T]) -> Callable[[], T | None]:
        def handler() -> T | None:
            if rebuild_dataclass(cls, raise_errors=False, _parent_namespace_depth=5) is not False:
                return attr_fn(cls)
            return None

        return handler

    cls.__pydantic_core_schema__ = MockCoreSchema(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        attempt_rebuild=attempt_rebuild_fn(lambda c: c.__pydantic_core_schema__),
    )
    cls.__pydantic_validator__ = MockValSer(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        val_or_ser='validator',
        attempt_rebuild=attempt_rebuild_fn(lambda c: c.__pydantic_validator__),
    )
    cls.__pydantic_serializer__ = MockValSer(  # pyright: ignore[reportAttributeAccessIssue]
        undefined_type_error_message,
        code='class-not-fully-defined',
        val_or_ser='serializer',
        attempt_rebuild=attempt_rebuild_fn(lambda c: c.__pydantic_serializer__),
    )

# === NexusCore/openenv\Lib\site-packages\urllib3\contrib\socks.py ===
"""
This module contains provisional support for SOCKS proxies from within
urllib3. This module supports SOCKS4, SOCKS4A (an extension of SOCKS4), and
SOCKS5. To enable its functionality, either install PySocks or install this
module with the ``socks`` extra.

The SOCKS implementation supports the full range of urllib3 features. It also
supports the following SOCKS features:

- SOCKS4A (``proxy_url='socks4a://...``)
- SOCKS4 (``proxy_url='socks4://...``)
- SOCKS5 with remote DNS (``proxy_url='socks5h://...``)
- SOCKS5 with local DNS (``proxy_url='socks5://...``)
- Usernames and passwords for the SOCKS proxy

.. note::
   It is recommended to use ``socks5h://`` or ``socks4a://`` schemes in
   your ``proxy_url`` to ensure that DNS resolution is done from the remote
   server instead of client-side when connecting to a domain name.

SOCKS4 supports IPv4 and domain names with the SOCKS4A extension. SOCKS5
supports IPv4, IPv6, and domain names.

When connecting to a SOCKS4 proxy the ``username`` portion of the ``proxy_url``
will be sent as the ``userid`` section of the SOCKS request:

.. code-block:: python

    proxy_url="socks4a://<userid>@proxy-host"

When connecting to a SOCKS5 proxy the ``username`` and ``password`` portion
of the ``proxy_url`` will be sent as the username/password to authenticate
with the proxy:

.. code-block:: python

    proxy_url="socks5h://<username>:<password>@proxy-host"

"""

from __future__ import annotations

try:
    import socks  # type: ignore[import-not-found]
except ImportError:
    import warnings

    from ..exceptions import DependencyWarning

    warnings.warn(
        (
            "SOCKS support in urllib3 requires the installation of optional "
            "dependencies: specifically, PySocks.  For more information, see "
            "https://urllib3.readthedocs.io/en/latest/advanced-usage.html#socks-proxies"
        ),
        DependencyWarning,
    )
    raise

import typing
from socket import timeout as SocketTimeout

from ..connection import HTTPConnection, HTTPSConnection
from ..connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from ..exceptions import ConnectTimeoutError, NewConnectionError
from ..poolmanager import PoolManager
from ..util.url import parse_url

try:
    import ssl
except ImportError:
    ssl = None  # type: ignore[assignment]


class _TYPE_SOCKS_OPTIONS(typing.TypedDict):
    socks_version: int
    proxy_host: str | None
    proxy_port: str | None
    username: str | None
    password: str | None
    rdns: bool


class SOCKSConnection(HTTPConnection):
    """
    A plain-text HTTP connection that connects via a SOCKS proxy.
    """

    def __init__(
        self,
        _socks_options: _TYPE_SOCKS_OPTIONS,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        self._socks_options = _socks_options
        super().__init__(*args, **kwargs)

    def _new_conn(self) -> socks.socksocket:
        """
        Establish a new connection via the SOCKS proxy.
        """
        extra_kw: dict[str, typing.Any] = {}
        if self.source_address:
            extra_kw["source_address"] = self.source_address

        if self.socket_options:
            extra_kw["socket_options"] = self.socket_options

        try:
            conn = socks.create_connection(
                (self.host, self.port),
                proxy_type=self._socks_options["socks_version"],
                proxy_addr=self._socks_options["proxy_host"],
                proxy_port=self._socks_options["proxy_port"],
                proxy_username=self._socks_options["username"],
                proxy_password=self._socks_options["password"],
                proxy_rdns=self._socks_options["rdns"],
                timeout=self.timeout,
                **extra_kw,
            )

        except SocketTimeout as e:
            raise ConnectTimeoutError(
                self,
                f"Connection to {self.host} timed out. (connect timeout={self.timeout})",
            ) from e

        except socks.ProxyError as e:
            # This is fragile as hell, but it seems to be the only way to raise
            # useful errors here.
            if e.socket_err:
                error = e.socket_err
                if isinstance(error, SocketTimeout):
                    raise ConnectTimeoutError(
                        self,
                        f"Connection to {self.host} timed out. (connect timeout={self.timeout})",
                    ) from e
                else:
                    # Adding `from e` messes with coverage somehow, so it's omitted.
                    # See #2386.
                    raise NewConnectionError(
                        self, f"Failed to establish a new connection: {error}"
                    )
            else:
                raise NewConnectionError(
                    self, f"Failed to establish a new connection: {e}"
                ) from e

        except OSError as e:  # Defensive: PySocks should catch all these.
            raise NewConnectionError(
                self, f"Failed to establish a new connection: {e}"
            ) from e

        return conn


# We don't need to duplicate the Verified/Unverified distinction from
# urllib3/connection.py here because the HTTPSConnection will already have been
# correctly set to either the Verified or Unverified form by that module. This
# means the SOCKSHTTPSConnection will automatically be the correct type.
class SOCKSHTTPSConnection(SOCKSConnection, HTTPSConnection):
    pass


class SOCKSHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = SOCKSConnection


class SOCKSHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = SOCKSHTTPSConnection


class SOCKSProxyManager(PoolManager):
    """
    A version of the urllib3 ProxyManager that routes connections via the
    defined SOCKS proxy.
    """

    pool_classes_by_scheme = {
        "http": SOCKSHTTPConnectionPool,
        "https": SOCKSHTTPSConnectionPool,
    }

    def __init__(
        self,
        proxy_url: str,
        username: str | None = None,
        password: str | None = None,
        num_pools: int = 10,
        headers: typing.Mapping[str, str] | None = None,
        **connection_pool_kw: typing.Any,
    ):
        parsed = parse_url(proxy_url)

        if username is None and password is None and parsed.auth is not None:
            split = parsed.auth.split(":")
            if len(split) == 2:
                username, password = split
        if parsed.scheme == "socks5":
            socks_version = socks.PROXY_TYPE_SOCKS5
            rdns = False
        elif parsed.scheme == "socks5h":
            socks_version = socks.PROXY_TYPE_SOCKS5
            rdns = True
        elif parsed.scheme == "socks4":
            socks_version = socks.PROXY_TYPE_SOCKS4
            rdns = False
        elif parsed.scheme == "socks4a":
            socks_version = socks.PROXY_TYPE_SOCKS4
            rdns = True
        else:
            raise ValueError(f"Unable to determine SOCKS version from {proxy_url}")

        self.proxy_url = proxy_url

        socks_options = {
            "socks_version": socks_version,
            "proxy_host": parsed.host,
            "proxy_port": parsed.port,
            "username": username,
            "password": password,
            "rdns": rdns,
        }
        connection_pool_kw["_socks_options"] = socks_options

        super().__init__(num_pools, headers, **connection_pool_kw)

        self.pool_classes_by_scheme = SOCKSProxyManager.pool_classes_by_scheme

# === NexusCore/openenv\Lib\site-packages\yaml\resolver.py ===

__all__ = ['BaseResolver', 'Resolver']

from .error import *
from .nodes import *

import re

class ResolverError(YAMLError):
    pass

class BaseResolver:

    DEFAULT_SCALAR_TAG = 'tag:yaml.org,2002:str'
    DEFAULT_SEQUENCE_TAG = 'tag:yaml.org,2002:seq'
    DEFAULT_MAPPING_TAG = 'tag:yaml.org,2002:map'

    yaml_implicit_resolvers = {}
    yaml_path_resolvers = {}

    def __init__(self):
        self.resolver_exact_paths = []
        self.resolver_prefix_paths = []

    @classmethod
    def add_implicit_resolver(cls, tag, regexp, first):
        if not 'yaml_implicit_resolvers' in cls.__dict__:
            implicit_resolvers = {}
            for key in cls.yaml_implicit_resolvers:
                implicit_resolvers[key] = cls.yaml_implicit_resolvers[key][:]
            cls.yaml_implicit_resolvers = implicit_resolvers
        if first is None:
            first = [None]
        for ch in first:
            cls.yaml_implicit_resolvers.setdefault(ch, []).append((tag, regexp))

    @classmethod
    def add_path_resolver(cls, tag, path, kind=None):
        # Note: `add_path_resolver` is experimental.  The API could be changed.
        # `new_path` is a pattern that is matched against the path from the
        # root to the node that is being considered.  `node_path` elements are
        # tuples `(node_check, index_check)`.  `node_check` is a node class:
        # `ScalarNode`, `SequenceNode`, `MappingNode` or `None`.  `None`
        # matches any kind of a node.  `index_check` could be `None`, a boolean
        # value, a string value, or a number.  `None` and `False` match against
        # any _value_ of sequence and mapping nodes.  `True` matches against
        # any _key_ of a mapping node.  A string `index_check` matches against
        # a mapping value that corresponds to a scalar key which content is
        # equal to the `index_check` value.  An integer `index_check` matches
        # against a sequence value with the index equal to `index_check`.
        if not 'yaml_path_resolvers' in cls.__dict__:
            cls.yaml_path_resolvers = cls.yaml_path_resolvers.copy()
        new_path = []
        for element in path:
            if isinstance(element, (list, tuple)):
                if len(element) == 2:
                    node_check, index_check = element
                elif len(element) == 1:
                    node_check = element[0]
                    index_check = True
                else:
                    raise ResolverError("Invalid path element: %s" % element)
            else:
                node_check = None
                index_check = element
            if node_check is str:
                node_check = ScalarNode
            elif node_check is list:
                node_check = SequenceNode
            elif node_check is dict:
                node_check = MappingNode
            elif node_check not in [ScalarNode, SequenceNode, MappingNode]  \
                    and not isinstance(node_check, str) \
                    and node_check is not None:
                raise ResolverError("Invalid node checker: %s" % node_check)
            if not isinstance(index_check, (str, int))  \
                    and index_check is not None:
                raise ResolverError("Invalid index checker: %s" % index_check)
            new_path.append((node_check, index_check))
        if kind is str:
            kind = ScalarNode
        elif kind is list:
            kind = SequenceNode
        elif kind is dict:
            kind = MappingNode
        elif kind not in [ScalarNode, SequenceNode, MappingNode]    \
                and kind is not None:
            raise ResolverError("Invalid node kind: %s" % kind)
        cls.yaml_path_resolvers[tuple(new_path), kind] = tag

    def descend_resolver(self, current_node, current_index):
        if not self.yaml_path_resolvers:
            return
        exact_paths = {}
        prefix_paths = []
        if current_node:
            depth = len(self.resolver_prefix_paths)
            for path, kind in self.resolver_prefix_paths[-1]:
                if self.check_resolver_prefix(depth, path, kind,
                        current_node, current_index):
                    if len(path) > depth:
                        prefix_paths.append((path, kind))
                    else:
                        exact_paths[kind] = self.yaml_path_resolvers[path, kind]
        else:
            for path, kind in self.yaml_path_resolvers:
                if not path:
                    exact_paths[kind] = self.yaml_path_resolvers[path, kind]
                else:
                    prefix_paths.append((path, kind))
        self.resolver_exact_paths.append(exact_paths)
        self.resolver_prefix_paths.append(prefix_paths)

    def ascend_resolver(self):
        if not self.yaml_path_resolvers:
            return
        self.resolver_exact_paths.pop()
        self.resolver_prefix_paths.pop()

    def check_resolver_prefix(self, depth, path, kind,
            current_node, current_index):
        node_check, index_check = path[depth-1]
        if isinstance(node_check, str):
            if current_node.tag != node_check:
                return
        elif node_check is not None:
            if not isinstance(current_node, node_check):
                return
        if index_check is True and current_index is not None:
            return
        if (index_check is False or index_check is None)    \
                and current_index is None:
            return
        if isinstance(index_check, str):
            if not (isinstance(current_index, ScalarNode)
                    and index_check == current_index.value):
                return
        elif isinstance(index_check, int) and not isinstance(index_check, bool):
            if index_check != current_index:
                return
        return True

    def resolve(self, kind, value, implicit):
        if kind is ScalarNode and implicit[0]:
            if value == '':
                resolvers = self.yaml_implicit_resolvers.get('', [])
            else:
                resolvers = self.yaml_implicit_resolvers.get(value[0], [])
            wildcard_resolvers = self.yaml_implicit_resolvers.get(None, [])
            for tag, regexp in resolvers + wildcard_resolvers:
                if regexp.match(value):
                    return tag
            implicit = implicit[1]
        if self.yaml_path_resolvers:
            exact_paths = self.resolver_exact_paths[-1]
            if kind in exact_paths:
                return exact_paths[kind]
            if None in exact_paths:
                return exact_paths[None]
        if kind is ScalarNode:
            return self.DEFAULT_SCALAR_TAG
        elif kind is SequenceNode:
            return self.DEFAULT_SEQUENCE_TAG
        elif kind is MappingNode:
            return self.DEFAULT_MAPPING_TAG

class Resolver(BaseResolver):
    pass

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:bool',
        re.compile(r'''^(?:yes|Yes|YES|no|No|NO
                    |true|True|TRUE|false|False|FALSE
                    |on|On|ON|off|Off|OFF)$''', re.X),
        list('yYnNtTfFoO'))

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:float',
        re.compile(r'''^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
                    |\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
                    |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*
                    |[-+]?\.(?:inf|Inf|INF)
                    |\.(?:nan|NaN|NAN))$''', re.X),
        list('-+0123456789.'))

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:int',
        re.compile(r'''^(?:[-+]?0b[0-1_]+
                    |[-+]?0[0-7_]+
                    |[-+]?(?:0|[1-9][0-9_]*)
                    |[-+]?0x[0-9a-fA-F_]+
                    |[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$''', re.X),
        list('-+0123456789'))

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:merge',
        re.compile(r'^(?:<<)$'),
        ['<'])

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:null',
        re.compile(r'''^(?: ~
                    |null|Null|NULL
                    | )$''', re.X),
        ['~', 'n', 'N', ''])

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:timestamp',
        re.compile(r'''^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
                    |[0-9][0-9][0-9][0-9] -[0-9][0-9]? -[0-9][0-9]?
                     (?:[Tt]|[ \t]+)[0-9][0-9]?
                     :[0-9][0-9] :[0-9][0-9] (?:\.[0-9]*)?
                     (?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$''', re.X),
        list('0123456789'))

Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:value',
        re.compile(r'^(?:=)$'),
        ['='])

# The following resolver is only for documentation purposes. It cannot work
# because plain scalars cannot start with '!', '&', or '*'.
Resolver.add_implicit_resolver(
        'tag:yaml.org,2002:yaml',
        re.compile(r'^(?:!|&|\*)$'),
        list('!&*'))


# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\create_views.py ===
from typing import Any

from litellm import verbose_logger

_db = Any


async def create_missing_views(db: _db):  # noqa: PLR0915
    """
    --------------------------------------------------
    NOTE: Copy of `litellm/db_scripts/create_views.py`.
    --------------------------------------------------
    Checks if the LiteLLM_VerificationTokenView and MonthlyGlobalSpend exists in the user's db.

    LiteLLM_VerificationTokenView: This view is used for getting the token + team data in user_api_key_auth

    MonthlyGlobalSpend: This view is used for the admin view to see global spend for this month

    If the view doesn't exist, one will be created.
    """
    try:
        # Try to select one row from the view
        await db.query_raw("""SELECT 1 FROM "LiteLLM_VerificationTokenView" LIMIT 1""")
        print("LiteLLM_VerificationTokenView Exists!")  # noqa
    except Exception:
        # If an error occurs, the view does not exist, so create it
        await db.execute_raw(
            """
                CREATE VIEW "LiteLLM_VerificationTokenView" AS
                SELECT 
                v.*, 
                t.spend AS team_spend, 
                t.max_budget AS team_max_budget, 
                t.tpm_limit AS team_tpm_limit, 
                t.rpm_limit AS team_rpm_limit
                FROM "LiteLLM_VerificationToken" v
                LEFT JOIN "LiteLLM_TeamTable" t ON v.team_id = t.team_id;
            """
        )

        print("LiteLLM_VerificationTokenView Created!")  # noqa

    try:
        await db.query_raw("""SELECT 1 FROM "MonthlyGlobalSpend" LIMIT 1""")
        print("MonthlyGlobalSpend Exists!")  # noqa
    except Exception:
        sql_query = """
        CREATE OR REPLACE VIEW "MonthlyGlobalSpend" AS 
        SELECT
        DATE("startTime") AS date, 
        SUM("spend") AS spend 
        FROM 
        "LiteLLM_SpendLogs" 
        WHERE 
        "startTime" >= (CURRENT_DATE - INTERVAL '30 days')
        GROUP BY 
        DATE("startTime");
        """
        await db.execute_raw(query=sql_query)

        print("MonthlyGlobalSpend Created!")  # noqa

    try:
        await db.query_raw("""SELECT 1 FROM "Last30dKeysBySpend" LIMIT 1""")
        print("Last30dKeysBySpend Exists!")  # noqa
    except Exception:
        sql_query = """
        CREATE OR REPLACE VIEW "Last30dKeysBySpend" AS
        SELECT 
        L."api_key", 
        V."key_alias",
        V."key_name",
        SUM(L."spend") AS total_spend
        FROM
        "LiteLLM_SpendLogs" L
        LEFT JOIN 
        "LiteLLM_VerificationToken" V
        ON
        L."api_key" = V."token"
        WHERE
        L."startTime" >= (CURRENT_DATE - INTERVAL '30 days')
        GROUP BY
        L."api_key", V."key_alias", V."key_name"
        ORDER BY
        total_spend DESC;
        """
        await db.execute_raw(query=sql_query)

        print("Last30dKeysBySpend Created!")  # noqa

    try:
        await db.query_raw("""SELECT 1 FROM "Last30dModelsBySpend" LIMIT 1""")
        print("Last30dModelsBySpend Exists!")  # noqa
    except Exception:
        sql_query = """
        CREATE OR REPLACE VIEW "Last30dModelsBySpend" AS
        SELECT
        "model",
        SUM("spend") AS total_spend
        FROM
        "LiteLLM_SpendLogs"
        WHERE
        "startTime" >= (CURRENT_DATE - INTERVAL '30 days')
        AND "model" != ''
        GROUP BY
        "model"
        ORDER BY
        total_spend DESC;
        """
        await db.execute_raw(query=sql_query)

        print("Last30dModelsBySpend Created!")  # noqa
    try:
        await db.query_raw("""SELECT 1 FROM "MonthlyGlobalSpendPerKey" LIMIT 1""")
        print("MonthlyGlobalSpendPerKey Exists!")  # noqa
    except Exception:
        sql_query = """
            CREATE OR REPLACE VIEW "MonthlyGlobalSpendPerKey" AS 
            SELECT
            DATE("startTime") AS date, 
            SUM("spend") AS spend,
            api_key as api_key
            FROM 
            "LiteLLM_SpendLogs" 
            WHERE 
            "startTime" >= (CURRENT_DATE - INTERVAL '30 days')
            GROUP BY 
            DATE("startTime"),
            api_key;
        """
        await db.execute_raw(query=sql_query)

        print("MonthlyGlobalSpendPerKey Created!")  # noqa
    try:
        await db.query_raw(
            """SELECT 1 FROM "MonthlyGlobalSpendPerUserPerKey" LIMIT 1"""
        )
        print("MonthlyGlobalSpendPerUserPerKey Exists!")  # noqa
    except Exception:
        sql_query = """
            CREATE OR REPLACE VIEW "MonthlyGlobalSpendPerUserPerKey" AS 
            SELECT
            DATE("startTime") AS date, 
            SUM("spend") AS spend,
            api_key as api_key,
            "user" as "user"
            FROM 
            "LiteLLM_SpendLogs" 
            WHERE 
            "startTime" >= (CURRENT_DATE - INTERVAL '30 days')
            GROUP BY 
            DATE("startTime"),
            "user",
            api_key;
        """
        await db.execute_raw(query=sql_query)

        print("MonthlyGlobalSpendPerUserPerKey Created!")  # noqa

    try:
        await db.query_raw("""SELECT 1 FROM "DailyTagSpend" LIMIT 1""")
        print("DailyTagSpend Exists!")  # noqa
    except Exception:
        sql_query = """
        CREATE OR REPLACE VIEW "DailyTagSpend" AS
        SELECT
            jsonb_array_elements_text(request_tags) AS individual_request_tag,
            DATE(s."startTime") AS spend_date,
            COUNT(*) AS log_count,
            SUM(spend) AS total_spend
        FROM "LiteLLM_SpendLogs" s
        GROUP BY individual_request_tag, DATE(s."startTime");
        """
        await db.execute_raw(query=sql_query)

        print("DailyTagSpend Created!")  # noqa

    try:
        await db.query_raw("""SELECT 1 FROM "Last30dTopEndUsersSpend" LIMIT 1""")
        print("Last30dTopEndUsersSpend Exists!")  # noqa
    except Exception:
        sql_query = """
        CREATE VIEW "Last30dTopEndUsersSpend" AS
        SELECT end_user, COUNT(*) AS total_events, SUM(spend) AS total_spend
        FROM "LiteLLM_SpendLogs"
        WHERE end_user <> '' AND end_user <> user
        AND "startTime" >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY end_user
        ORDER BY total_spend DESC
        LIMIT 100;
        """
        await db.execute_raw(query=sql_query)

        print("Last30dTopEndUsersSpend Created!")  # noqa

    return


async def should_create_missing_views(db: _db) -> bool:
    """
    Run only on first time startup.

    If SpendLogs table already has values, then don't create views on startup.
    """

    sql_query = """
    SELECT reltuples::BIGINT
    FROM pg_class
    WHERE oid = '"LiteLLM_SpendLogs"'::regclass;
    """

    result = await db.query_raw(query=sql_query)

    verbose_logger.debug("Estimated Row count of LiteLLM_SpendLogs = {}".format(result))
    if (
        result
        and isinstance(result, list)
        and len(result) > 0
        and isinstance(result[0], dict)
        and "reltuples" in result[0]
        and result[0]["reltuples"]
        and (result[0]["reltuples"] == 0 or result[0]["reltuples"] == -1)
    ):
        verbose_logger.debug("Should create views")
        return True

    return False

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\sas.py ===
"""
    pygments.lexers.sas
    ~~~~~~~~~~~~~~~~~~~

    Lexer for SAS.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from pygments.lexer import RegexLexer, include, words
from pygments.token import Comment, Keyword, Name, Number, String, Text, \
    Other, Generic

__all__ = ['SASLexer']


class SASLexer(RegexLexer):
    """
    For SAS files.
    """
    # Syntax from syntax/sas.vim by James Kidd <james.kidd@covance.com>

    name      = 'SAS'
    aliases   = ['sas']
    filenames = ['*.SAS', '*.sas']
    mimetypes = ['text/x-sas', 'text/sas', 'application/x-sas']
    url = 'https://en.wikipedia.org/wiki/SAS_(software)'
    version_added = '2.2'
    flags     = re.IGNORECASE | re.MULTILINE

    builtins_macros = (
        "bquote", "nrbquote", "cmpres", "qcmpres", "compstor", "datatyp",
        "display", "do", "else", "end", "eval", "global", "goto", "if",
        "index", "input", "keydef", "label", "left", "length", "let",
        "local", "lowcase", "macro", "mend", "nrquote",
        "nrstr", "put", "qleft", "qlowcase", "qscan",
        "qsubstr", "qsysfunc", "qtrim", "quote", "qupcase", "scan",
        "str", "substr", "superq", "syscall", "sysevalf", "sysexec",
        "sysfunc", "sysget", "syslput", "sysprod", "sysrc", "sysrput",
        "then", "to", "trim", "unquote", "until", "upcase", "verify",
        "while", "window"
    )

    builtins_conditionals = (
        "do", "if", "then", "else", "end", "until", "while"
    )

    builtins_statements = (
        "abort", "array", "attrib", "by", "call", "cards", "cards4",
        "catname", "continue", "datalines", "datalines4", "delete", "delim",
        "delimiter", "display", "dm", "drop", "endsas", "error", "file",
        "filename", "footnote", "format", "goto", "in", "infile", "informat",
        "input", "keep", "label", "leave", "length", "libname", "link",
        "list", "lostcard", "merge", "missing", "modify", "options", "output",
        "out", "page", "put", "redirect", "remove", "rename", "replace",
        "retain", "return", "select", "set", "skip", "startsas", "stop",
        "title", "update", "waitsas", "where", "window", "x", "systask"
    )

    builtins_sql = (
        "add", "and", "alter", "as", "cascade", "check", "create",
        "delete", "describe", "distinct", "drop", "foreign", "from",
        "group", "having", "index", "insert", "into", "in", "key", "like",
        "message", "modify", "msgtype", "not", "null", "on", "or",
        "order", "primary", "references", "reset", "restrict", "select",
        "set", "table", "unique", "update", "validate", "view", "where"
    )

    builtins_functions = (
        "abs", "addr", "airy", "arcos", "arsin", "atan", "attrc",
        "attrn", "band", "betainv", "blshift", "bnot", "bor",
        "brshift", "bxor", "byte", "cdf", "ceil", "cexist", "cinv",
        "close", "cnonct", "collate", "compbl", "compound",
        "compress", "cos", "cosh", "css", "curobs", "cv", "daccdb",
        "daccdbsl", "daccsl", "daccsyd", "dacctab", "dairy", "date",
        "datejul", "datepart", "datetime", "day", "dclose", "depdb",
        "depdbsl", "depsl", "depsyd",
        "deptab", "dequote", "dhms", "dif", "digamma",
        "dim", "dinfo", "dnum", "dopen", "doptname", "doptnum",
        "dread", "dropnote", "dsname", "erf", "erfc", "exist", "exp",
        "fappend", "fclose", "fcol", "fdelete", "fetch", "fetchobs",
        "fexist", "fget", "fileexist", "filename", "fileref",
        "finfo", "finv", "fipname", "fipnamel", "fipstate", "floor",
        "fnonct", "fnote", "fopen", "foptname", "foptnum", "fpoint",
        "fpos", "fput", "fread", "frewind", "frlen", "fsep", "fuzz",
        "fwrite", "gaminv", "gamma", "getoption", "getvarc", "getvarn",
        "hbound", "hms", "hosthelp", "hour", "ibessel", "index",
        "indexc", "indexw", "input", "inputc", "inputn", "int",
        "intck", "intnx", "intrr", "irr", "jbessel", "juldate",
        "kurtosis", "lag", "lbound", "left", "length", "lgamma",
        "libname", "libref", "log", "log10", "log2", "logpdf", "logpmf",
        "logsdf", "lowcase", "max", "mdy", "mean", "min", "minute",
        "mod", "month", "mopen", "mort", "n", "netpv", "nmiss",
        "normal", "note", "npv", "open", "ordinal", "pathname",
        "pdf", "peek", "peekc", "pmf", "point", "poisson", "poke",
        "probbeta", "probbnml", "probchi", "probf", "probgam",
        "probhypr", "probit", "probnegb", "probnorm", "probt",
        "put", "putc", "putn", "qtr", "quote", "ranbin", "rancau",
        "ranexp", "rangam", "range", "rank", "rannor", "ranpoi",
        "rantbl", "rantri", "ranuni", "repeat", "resolve", "reverse",
        "rewind", "right", "round", "saving", "scan", "sdf", "second",
        "sign", "sin", "sinh", "skewness", "soundex", "spedis",
        "sqrt", "std", "stderr", "stfips", "stname", "stnamel",
        "substr", "sum", "symget", "sysget", "sysmsg", "sysprod",
        "sysrc", "system", "tan", "tanh", "time", "timepart", "tinv",
        "tnonct", "today", "translate", "tranwrd", "trigamma",
        "trim", "trimn", "trunc", "uniform", "upcase", "uss", "var",
        "varfmt", "varinfmt", "varlabel", "varlen", "varname",
        "varnum", "varray", "varrayx", "vartype", "verify", "vformat",
        "vformatd", "vformatdx", "vformatn", "vformatnx", "vformatw",
        "vformatwx", "vformatx", "vinarray", "vinarrayx", "vinformat",
        "vinformatd", "vinformatdx", "vinformatn", "vinformatnx",
        "vinformatw", "vinformatwx", "vinformatx", "vlabel",
        "vlabelx", "vlength", "vlengthx", "vname", "vnamex", "vtype",
        "vtypex", "weekday", "year", "yyq", "zipfips", "zipname",
        "zipnamel", "zipstate"
    )

    tokens = {
        'root': [
            include('comments'),
            include('proc-data'),
            include('cards-datalines'),
            include('logs'),
            include('general'),
            (r'.', Text),
        ],
        # SAS is multi-line regardless, but * is ended by ;
        'comments': [
            (r'^\s*\*.*?;', Comment),
            (r'/\*.*?\*/', Comment),
            (r'^\s*\*(.|\n)*?;', Comment.Multiline),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
        ],
        # Special highlight for proc, data, quit, run
        'proc-data': [
            (r'(^|;)\s*(proc \w+|data|run|quit)[\s;]',
             Keyword.Reserved),
        ],
        # Special highlight cards and datalines
        'cards-datalines': [
            (r'^\s*(datalines|cards)\s*;\s*$', Keyword, 'data'),
        ],
        'data': [
            (r'(.|\n)*^\s*;\s*$', Other, '#pop'),
        ],
        # Special highlight for put NOTE|ERROR|WARNING (order matters)
        'logs': [
            (r'\n?^\s*%?put ', Keyword, 'log-messages'),
        ],
        'log-messages': [
            (r'NOTE(:|-).*', Generic, '#pop'),
            (r'WARNING(:|-).*', Generic.Emph, '#pop'),
            (r'ERROR(:|-).*', Generic.Error, '#pop'),
            include('general'),
        ],
        'general': [
            include('keywords'),
            include('vars-strings'),
            include('special'),
            include('numbers'),
        ],
        # Keywords, statements, functions, macros
        'keywords': [
            (words(builtins_statements,
                   prefix = r'\b',
                   suffix = r'\b'),
             Keyword),
            (words(builtins_sql,
                   prefix = r'\b',
                   suffix = r'\b'),
             Keyword),
            (words(builtins_conditionals,
                   prefix = r'\b',
                   suffix = r'\b'),
             Keyword),
            (words(builtins_macros,
                   prefix = r'%',
                   suffix = r'\b'),
             Name.Builtin),
            (words(builtins_functions,
                   prefix = r'\b',
                   suffix = r'\('),
             Name.Builtin),
        ],
        # Strings and user-defined variables and macros (order matters)
        'vars-strings': [
            (r'&[a-z_]\w{0,31}\.?', Name.Variable),
            (r'%[a-z_]\w{0,31}', Name.Function),
            (r'\'', String, 'string_squote'),
            (r'"', String, 'string_dquote'),
        ],
        'string_squote': [
            ('\'', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            # AFAIK, macro variables are not evaluated in single quotes
            # (r'&', Name.Variable, 'validvar'),
            (r'[^$\'\\]+', String),
            (r'[$\'\\]', String),
        ],
        'string_dquote': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            (r'&', Name.Variable, 'validvar'),
            (r'[^$&"\\]+', String),
            (r'[$"\\]', String),
        ],
        'validvar': [
            (r'[a-z_]\w{0,31}\.?', Name.Variable, '#pop'),
        ],
        # SAS numbers and special variables
        'numbers': [
            (r'\b[+-]?([0-9]+(\.[0-9]+)?|\.[0-9]+|\.)(E[+-]?[0-9]+)?i?\b',
             Number),
        ],
        'special': [
            (r'(null|missing|_all_|_automatic_|_character_|_n_|'
             r'_infile_|_name_|_null_|_numeric_|_user_|_webout_)',
             Keyword.Constant),
        ],
        # 'operators': [
        #     (r'(-|=|<=|>=|<|>|<>|&|!=|'
        #      r'\||\*|\+|\^|/|!|~|~=)', Operator)
        # ],
    }

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\wheelfile.py ===
from __future__ import annotations

import csv
import hashlib
import os.path
import re
import stat
import time
from io import StringIO, TextIOWrapper
from typing import IO, TYPE_CHECKING, Literal
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from wheel.cli import WheelError
from wheel.util import log, urlsafe_b64decode, urlsafe_b64encode

if TYPE_CHECKING:
    from typing import Protocol, Sized, Union

    from typing_extensions import Buffer

    StrPath = Union[str, os.PathLike[str]]

    class SizedBuffer(Sized, Buffer, Protocol): ...


# Non-greedy matching of an optional build number may be too clever (more
# invalid wheel filenames will match). Separate regex for .dist-info?
WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>[^\s-]+?)-(?P<ver>[^\s-]+?))(-(?P<build>\d[^\s-]*))?
     -(?P<pyver>[^\s-]+?)-(?P<abi>[^\s-]+?)-(?P<plat>\S+)\.whl$""",
    re.VERBOSE,
)
MINIMUM_TIMESTAMP = 315532800  # 1980-01-01 00:00:00 UTC


def get_zipinfo_datetime(timestamp: float | None = None):
    # Some applications need reproducible .whl files, but they can't do this without
    # forcing the timestamp of the individual ZipInfo objects. See issue #143.
    timestamp = int(os.environ.get("SOURCE_DATE_EPOCH", timestamp or time.time()))
    timestamp = max(timestamp, MINIMUM_TIMESTAMP)
    return time.gmtime(timestamp)[0:6]


class WheelFile(ZipFile):
    """A ZipFile derivative class that also reads SHA-256 hashes from
    .dist-info/RECORD and checks any read files against those.
    """

    _default_algorithm = hashlib.sha256

    def __init__(
        self,
        file: StrPath,
        mode: Literal["r", "w", "x", "a"] = "r",
        compression: int = ZIP_DEFLATED,
    ):
        basename = os.path.basename(file)
        self.parsed_filename = WHEEL_INFO_RE.match(basename)
        if not basename.endswith(".whl") or self.parsed_filename is None:
            raise WheelError(f"Bad wheel filename {basename!r}")

        ZipFile.__init__(self, file, mode, compression=compression, allowZip64=True)

        self.dist_info_path = "{}.dist-info".format(
            self.parsed_filename.group("namever")
        )
        self.record_path = self.dist_info_path + "/RECORD"
        self._file_hashes: dict[str, tuple[None, None] | tuple[int, bytes]] = {}
        self._file_sizes = {}
        if mode == "r":
            # Ignore RECORD and any embedded wheel signatures
            self._file_hashes[self.record_path] = None, None
            self._file_hashes[self.record_path + ".jws"] = None, None
            self._file_hashes[self.record_path + ".p7s"] = None, None

            # Fill in the expected hashes by reading them from RECORD
            try:
                record = self.open(self.record_path)
            except KeyError:
                raise WheelError(f"Missing {self.record_path} file") from None

            with record:
                for line in csv.reader(
                    TextIOWrapper(record, newline="", encoding="utf-8")
                ):
                    path, hash_sum, size = line
                    if not hash_sum:
                        continue

                    algorithm, hash_sum = hash_sum.split("=")
                    try:
                        hashlib.new(algorithm)
                    except ValueError:
                        raise WheelError(
                            f"Unsupported hash algorithm: {algorithm}"
                        ) from None

                    if algorithm.lower() in {"md5", "sha1"}:
                        raise WheelError(
                            f"Weak hash algorithm ({algorithm}) is not permitted by "
                            f"PEP 427"
                        )

                    self._file_hashes[path] = (
                        algorithm,
                        urlsafe_b64decode(hash_sum.encode("ascii")),
                    )

    def open(
        self,
        name_or_info: str | ZipInfo,
        mode: Literal["r", "w"] = "r",
        pwd: bytes | None = None,
    ) -> IO[bytes]:
        def _update_crc(newdata: bytes) -> None:
            eof = ef._eof
            update_crc_orig(newdata)
            running_hash.update(newdata)
            if eof and running_hash.digest() != expected_hash:
                raise WheelError(f"Hash mismatch for file '{ef_name}'")

        ef_name = (
            name_or_info.filename if isinstance(name_or_info, ZipInfo) else name_or_info
        )
        if (
            mode == "r"
            and not ef_name.endswith("/")
            and ef_name not in self._file_hashes
        ):
            raise WheelError(f"No hash found for file '{ef_name}'")

        ef = ZipFile.open(self, name_or_info, mode, pwd)
        if mode == "r" and not ef_name.endswith("/"):
            algorithm, expected_hash = self._file_hashes[ef_name]
            if expected_hash is not None:
                # Monkey patch the _update_crc method to also check for the hash from
                # RECORD
                running_hash = hashlib.new(algorithm)
                update_crc_orig, ef._update_crc = ef._update_crc, _update_crc

        return ef

    def write_files(self, base_dir: str):
        log.info(f"creating '{self.filename}' and adding '{base_dir}' to it")
        deferred: list[tuple[str, str]] = []
        for root, dirnames, filenames in os.walk(base_dir):
            # Sort the directory names so that `os.walk` will walk them in a
            # defined order on the next iteration.
            dirnames.sort()
            for name in sorted(filenames):
                path = os.path.normpath(os.path.join(root, name))
                if os.path.isfile(path):
                    arcname = os.path.relpath(path, base_dir).replace(os.path.sep, "/")
                    if arcname == self.record_path:
                        pass
                    elif root.endswith(".dist-info"):
                        deferred.append((path, arcname))
                    else:
                        self.write(path, arcname)

        deferred.sort()
        for path, arcname in deferred:
            self.write(path, arcname)

    def write(
        self,
        filename: str,
        arcname: str | None = None,
        compress_type: int | None = None,
    ) -> None:
        with open(filename, "rb") as f:
            st = os.fstat(f.fileno())
            data = f.read()

        zinfo = ZipInfo(
            arcname or filename, date_time=get_zipinfo_datetime(st.st_mtime)
        )
        zinfo.external_attr = (stat.S_IMODE(st.st_mode) | stat.S_IFMT(st.st_mode)) << 16
        zinfo.compress_type = compress_type or self.compression
        self.writestr(zinfo, data, compress_type)

    def writestr(
        self,
        zinfo_or_arcname: str | ZipInfo,
        data: SizedBuffer | str,
        compress_type: int | None = None,
    ):
        if isinstance(zinfo_or_arcname, str):
            zinfo_or_arcname = ZipInfo(
                zinfo_or_arcname, date_time=get_zipinfo_datetime()
            )
            zinfo_or_arcname.compress_type = self.compression
            zinfo_or_arcname.external_attr = (0o664 | stat.S_IFREG) << 16

        if isinstance(data, str):
            data = data.encode("utf-8")

        ZipFile.writestr(self, zinfo_or_arcname, data, compress_type)
        fname = (
            zinfo_or_arcname.filename
            if isinstance(zinfo_or_arcname, ZipInfo)
            else zinfo_or_arcname
        )
        log.info(f"adding '{fname}'")
        if fname != self.record_path:
            hash_ = self._default_algorithm(data)
            self._file_hashes[fname] = (
                hash_.name,
                urlsafe_b64encode(hash_.digest()).decode("ascii"),
            )
            self._file_sizes[fname] = len(data)

    def close(self):
        # Write RECORD
        if self.fp is not None and self.mode == "w" and self._file_hashes:
            data = StringIO()
            writer = csv.writer(data, delimiter=",", quotechar='"', lineterminator="\n")
            writer.writerows(
                (
                    (fname, algorithm + "=" + hash_, self._file_sizes[fname])
                    for fname, (algorithm, hash_) in self._file_hashes.items()
                )
            )
            writer.writerow((format(self.record_path), "", ""))
            self.writestr(self.record_path, data.getvalue())

        ZipFile.close(self)

# === NexusCore/openenv\Lib\site-packages\win32\test\test_win32gui.py ===
# tests for win32gui
import array
import operator
import sys
import unittest

import pywintypes
import win32api
import win32gui


class TestPyGetString(unittest.TestCase):
    def test_get_string(self):
        # test invalid addresses cause a ValueError rather than crash!
        self.assertRaises(ValueError, win32gui.PyGetString, 0)
        self.assertRaises(ValueError, win32gui.PyGetString, 1)
        self.assertRaises(ValueError, win32gui.PyGetString, 1, 1)


class TestPyGetMemory(unittest.TestCase):
    def test_ob(self):
        # Check the PyGetMemory result and a bytes string can be compared
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertEqual(len(got), len(test_data))
        self.assertEqual(bytes(got), test_data)

    def test_memory_index(self):
        # Check we can index into the buffer object returned by PyGetMemory
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertEqual(got[0], 0)

    def test_memory_slice(self):
        # Check we can slice the buffer object returned by PyGetMemory
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertEqual(list(got[0:3]), [0, 1, 2])

    def test_real_view(self):
        # Do the PyGetMemory, then change the original memory, then ensure
        # the initial object we fetched sees the new value.
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertEqual(got[0], 0)
        c[0] = 1
        self.assertEqual(got[0], 1)

    def test_memory_not_writable(self):
        # Check the buffer object fetched by PyGetMemory isn't writable.
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertRaises(TypeError, operator.setitem, got, 0, 1)


class TestEnumWindowsFamily(unittest.TestCase):
    @classmethod
    def enum_callback_sle(cls, handle, data):
        win32api.SetLastError(1)
        return data

    @classmethod
    def enum_callback_exc(cls, handle, data):
        raise ValueError

    @classmethod
    def enum_callback(cls, handle, data):
        return data

    def setUp(self):
        self.default_data_set = (None, -1, 0, 1, True, False)
        self.type_data_set = ("", (), {})

    def test_enumwindows(self):
        win32api.SetLastError(0)
        for data in (0, False):
            self.assertRaises(
                pywintypes.error, win32gui.EnumWindows, self.enum_callback_sle, data
            )
        for data in (None, 1, True):
            self.assertIsNone(win32gui.EnumWindows(self.enum_callback_sle, data))
        win32api.SetLastError(0)
        for data in self.default_data_set:
            self.assertIsNone(win32gui.EnumWindows(self.enum_callback, data))
        for data in self.default_data_set:
            self.assertRaises(
                ValueError, win32gui.EnumWindows, self.enum_callback_exc, data
            )
        for func in (
            self.enum_callback,
            self.enum_callback_sle,
        ):
            for data in self.type_data_set:
                self.assertRaises(TypeError, win32gui.EnumWindows, func, data)
        if sys.version_info >= (3, 10):
            for func in (
                self.enum_callback,
                self.enum_callback_sle,
            ):
                self.assertRaises(
                    TypeError, win32gui.EnumWindows, func, self.enum_callback, 2.718282
                )

    def test_enumchildwindows(self):
        win32api.SetLastError(0)
        for data in self.default_data_set:
            self.assertIsNone(win32gui.EnumChildWindows(None, self.enum_callback, data))
        for data in self.default_data_set:
            self.assertIsNone(
                win32gui.EnumChildWindows(None, self.enum_callback_sle, data)
            )
        win32api.SetLastError(0)
        for data in self.default_data_set:
            self.assertRaises(
                ValueError,
                win32gui.EnumChildWindows,
                None,
                self.enum_callback_exc,
                data,
            )
        for data in self.type_data_set:
            for func in (
                self.enum_callback,
                self.enum_callback_sle,
            ):
                self.assertRaises(
                    TypeError, win32gui.EnumChildWindows, None, func, data
                )
        if sys.version_info >= (3, 10):
            for func in (
                self.enum_callback,
                self.enum_callback_sle,
            ):
                self.assertRaises(
                    TypeError,
                    win32gui.EnumChildWindows,
                    None,
                    func,
                    self.enum_callback,
                    2.718282,
                )

    def test_enumdesktopwindows(self):
        win32api.SetLastError(0)
        desktop = None
        for data in (0, False):
            self.assertRaises(
                pywintypes.error,
                win32gui.EnumDesktopWindows,
                desktop,
                self.enum_callback_sle,
                data,
            )
        for data in (None, 1, True):
            self.assertIsNone(
                win32gui.EnumDesktopWindows(desktop, self.enum_callback_sle, data)
            )
        win32api.SetLastError(0)
        for data in self.default_data_set:
            self.assertIsNone(
                win32gui.EnumDesktopWindows(desktop, self.enum_callback, data)
            )
        for data in self.default_data_set:
            self.assertRaises(
                ValueError,
                win32gui.EnumDesktopWindows,
                desktop,
                self.enum_callback_exc,
                data,
            )
        desktops = (0, None)
        for desktop in desktops:
            for data in self.default_data_set:
                self.assertRaises(
                    ValueError,
                    win32gui.EnumDesktopWindows,
                    desktop,
                    self.enum_callback_exc,
                    data,
                )
        for func in (
            self.enum_callback,
            self.enum_callback_sle,
        ):
            for desktop in desktops:
                for data in self.type_data_set:
                    self.assertRaises(
                        TypeError, win32gui.EnumDesktopWindows, 0, func, data
                    )
        if sys.version_info >= (3, 10):
            for func in (
                self.enum_callback,
                self.enum_callback_sle,
            ):
                for desktop in desktops:
                    self.assertRaises(
                        TypeError, win32gui.EnumDesktopWindows, 0, func, 2.718282
                    )


class TestWindowProperties(unittest.TestCase):
    def setUp(self):
        self.class_functions = (
            win32gui.GetClassName,
            win32gui.RealGetWindowClass,
        )

    def test_classname(self):
        for func in self.class_functions:
            self.assertRaises(pywintypes.error, func, 0)
        wnd = win32gui.GetDesktopWindow()
        for func in self.class_functions:
            self.assertTrue(func(wnd))


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\win32com\test\testPersist.py ===
import os

import pythoncom
import pywintypes
import win32api
import win32com
import win32com.client
import win32com.client.dynamic
import win32com.server.util
import win32timezone
import win32ui
from win32com import storagecon
from win32com.axcontrol import axcontrol
from win32com.test.util import CheckClean

S_OK = 0

now = win32timezone.now()


class LockBytes:
    _public_methods_ = [
        "ReadAt",
        "WriteAt",
        "Flush",
        "SetSize",
        "LockRegion",
        "UnlockRegion",
        "Stat",
    ]
    _com_interfaces_ = [pythoncom.IID_ILockBytes]

    def __init__(self, data=b""):
        self.data = data
        self.ctime = now
        self.mtime = now
        self.atime = now

    def ReadAt(self, offset, cb):
        print("ReadAt")
        result = self.data[offset : offset + cb]
        return result

    def WriteAt(self, offset, data):
        print("WriteAt", offset)
        print("len", len(data))
        print("data:")
        # print(data)
        if len(self.data) >= offset:
            newdata = self.data[0:offset] + data
        print(len(newdata))
        if len(self.data) >= offset + len(data):
            newdata += self.data[offset + len(data) :]
        print(len(newdata))
        self.data = newdata
        return len(data)

    def Flush(self, whatsthis=0):
        print("Flush", whatsthis)
        fname = os.path.join(win32api.GetTempPath(), "persist.doc")
        open(fname, "wb").write(self.data)
        return S_OK

    def SetSize(self, size):
        print("Set Size", size)
        if size > len(self.data):
            self.data += b"\000" * (size - len(self.data))
        else:
            self.data = self.data[0:size]
        return S_OK

    def LockRegion(self, offset, size, locktype):
        print("LockRegion")

    def UnlockRegion(self, offset, size, locktype):
        print("UnlockRegion")

    def Stat(self, statflag):
        print("returning Stat", statflag)
        return (
            "PyMemBytes",
            storagecon.STGTY_LOCKBYTES,
            len(self.data),
            self.mtime,
            self.ctime,
            self.atime,
            storagecon.STGM_DIRECT | storagecon.STGM_READWRITE | storagecon.STGM_CREATE,
            storagecon.STGM_SHARE_EXCLUSIVE,
            "{00020905-0000-0000-C000-000000000046}",
            0,  # statebits ?
            0,
        )


class OleClientSite:
    _public_methods_ = [
        "SaveObject",
        "GetMoniker",
        "GetContainer",
        "ShowObject",
        "OnShowWindow",
        "RequestNewObjectLayout",
    ]
    _com_interfaces_ = [axcontrol.IID_IOleClientSite]

    def __init__(self, data=""):
        self.IPersistStorage = None
        self.IStorage = None

    def SetIPersistStorage(self, IPersistStorage):
        self.IPersistStorage = IPersistStorage

    def SetIStorage(self, IStorage):
        self.IStorage = IStorage

    def SaveObject(self):
        print("SaveObject")
        if self.IPersistStorage is not None and self.IStorage is not None:
            self.IPersistStorage.Save(self.IStorage, 1)
            self.IStorage.Commit(0)
        return S_OK

    def GetMoniker(self, dwAssign, dwWhichMoniker):
        print("GetMoniker", dwAssign, dwWhichMoniker)

    def GetContainer(self):
        print("GetContainer")

    def ShowObject(self):
        print("ShowObject")

    def OnShowWindow(self, fShow):
        print("ShowObject", fShow)

    def RequestNewObjectLayout(self):
        print("RequestNewObjectLayout")


def test():
    # create a LockBytes object and
    # wrap it as a COM object
    #       import win32com.server.dispatcher
    lbcom = win32com.server.util.wrap(
        LockBytes(), pythoncom.IID_ILockBytes
    )  # , useDispatcher=win32com.server.dispatcher.DispatcherWin32trace)

    # create a structured storage on the ILockBytes object
    stcom = pythoncom.StgCreateDocfileOnILockBytes(
        lbcom,
        storagecon.STGM_DIRECT
        | storagecon.STGM_CREATE
        | storagecon.STGM_READWRITE
        | storagecon.STGM_SHARE_EXCLUSIVE,
        0,
    )

    # create our ClientSite
    ocs = OleClientSite()
    # wrap it as a COM object
    ocscom = win32com.server.util.wrap(ocs, axcontrol.IID_IOleClientSite)

    # create a Word OLE Document, connect it to our site and our storage
    oocom = axcontrol.OleCreate(
        "{00020906-0000-0000-C000-000000000046}",
        axcontrol.IID_IOleObject,
        0,
        (0,),
        ocscom,
        stcom,
    )

    mf = win32ui.GetMainFrame()
    hwnd = mf.GetSafeHwnd()

    # Set the host and document name
    # for unknown reason document name becomes hostname, and document name
    # is not set, debugged it, but don't know where the problem is?
    oocom.SetHostNames("OTPython", "This is Cool")

    # activate the OLE document
    oocom.DoVerb(-1, ocscom, 0, hwnd, mf.GetWindowRect())

    # set the hostnames again
    oocom.SetHostNames("OTPython2", "ThisisCool2")

    # get IDispatch of Word
    doc = win32com.client.Dispatch(oocom.QueryInterface(pythoncom.IID_IDispatch))

    # get IPersistStorage of Word
    dpcom = oocom.QueryInterface(pythoncom.IID_IPersistStorage)

    # let our ClientSite know the interfaces
    ocs.SetIPersistStorage(dpcom)
    ocs.SetIStorage(stcom)

    # use IDispatch to do the Office Word test
    # pasted from TestOffice.py

    wrange = doc.Range()
    for i in range(10):
        wrange.InsertAfter("Hello from Python %d\n" % i)
    paras = doc.Paragraphs
    for i in range(len(paras)):
        paras[i]().Font.ColorIndex = i + 1
        paras[i]().Font.Size = 12 + (4 * i)
    # XXX - note that
    # for para in paras:
    #       para().Font...
    # doesn't seem to work - no error, just doesn't work
    # Should check if it works for VB!

    dpcom.Save(stcom, 0)
    dpcom.HandsOffStorage()
    #       oocom.Close(axcontrol.OLECLOSE_NOSAVE) # or OLECLOSE_SAVEIFDIRTY, but it fails???

    # Save the ILockBytes data to "persist2.doc"
    lbcom.Flush()

    # exiting Winword will automatically update the ILockBytes data
    # and flush it to "%TEMP%\persist.doc"
    doc.Application.Quit()


if __name__ == "__main__":
    test()
    pythoncom.CoUninitialize()
    CheckClean()

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\search.py ===
"""
Search operations.

For the key bindings implementation with attached filters, check
`prompt_toolkit.key_binding.bindings.search`. (Use these for new key bindings
instead of calling these function directly.)
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from .application.current import get_app
from .filters import FilterOrBool, is_searching, to_filter
from .key_binding.vi_state import InputMode

if TYPE_CHECKING:
    from prompt_toolkit.layout.controls import BufferControl, SearchBufferControl
    from prompt_toolkit.layout.layout import Layout

__all__ = [
    "SearchDirection",
    "start_search",
    "stop_search",
]


class SearchDirection(Enum):
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"


class SearchState:
    """
    A search 'query', associated with a search field (like a SearchToolbar).

    Every searchable `BufferControl` points to a `search_buffer_control`
    (another `BufferControls`) which represents the search field. The
    `SearchState` attached to that search field is used for storing the current
    search query.

    It is possible to have one searchfield for multiple `BufferControls`. In
    that case, they'll share the same `SearchState`.
    If there are multiple `BufferControls` that display the same `Buffer`, then
    they can have a different `SearchState` each (if they have a different
    search control).
    """

    __slots__ = ("text", "direction", "ignore_case")

    def __init__(
        self,
        text: str = "",
        direction: SearchDirection = SearchDirection.FORWARD,
        ignore_case: FilterOrBool = False,
    ) -> None:
        self.text = text
        self.direction = direction
        self.ignore_case = to_filter(ignore_case)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.text!r}, direction={self.direction!r}, ignore_case={self.ignore_case!r})"

    def __invert__(self) -> SearchState:
        """
        Create a new SearchState where backwards becomes forwards and the other
        way around.
        """
        if self.direction == SearchDirection.BACKWARD:
            direction = SearchDirection.FORWARD
        else:
            direction = SearchDirection.BACKWARD

        return SearchState(
            text=self.text, direction=direction, ignore_case=self.ignore_case
        )


def start_search(
    buffer_control: BufferControl | None = None,
    direction: SearchDirection = SearchDirection.FORWARD,
) -> None:
    """
    Start search through the given `buffer_control` using the
    `search_buffer_control`.

    :param buffer_control: Start search for this `BufferControl`. If not given,
        search through the current control.
    """
    from prompt_toolkit.layout.controls import BufferControl

    assert buffer_control is None or isinstance(buffer_control, BufferControl)

    layout = get_app().layout

    # When no control is given, use the current control if that's a BufferControl.
    if buffer_control is None:
        if not isinstance(layout.current_control, BufferControl):
            return
        buffer_control = layout.current_control

    # Only if this control is searchable.
    search_buffer_control = buffer_control.search_buffer_control

    if search_buffer_control:
        buffer_control.search_state.direction = direction

        # Make sure to focus the search BufferControl
        layout.focus(search_buffer_control)

        # Remember search link.
        layout.search_links[search_buffer_control] = buffer_control

        # If we're in Vi mode, make sure to go into insert mode.
        get_app().vi_state.input_mode = InputMode.INSERT


def stop_search(buffer_control: BufferControl | None = None) -> None:
    """
    Stop search through the given `buffer_control`.
    """
    layout = get_app().layout

    if buffer_control is None:
        buffer_control = layout.search_target_buffer_control
        if buffer_control is None:
            # (Should not happen, but possible when `stop_search` is called
            # when we're not searching.)
            return
        search_buffer_control = buffer_control.search_buffer_control
    else:
        assert buffer_control in layout.search_links.values()
        search_buffer_control = _get_reverse_search_links(layout)[buffer_control]

    # Focus the original buffer again.
    layout.focus(buffer_control)

    if search_buffer_control is not None:
        # Remove the search link.
        del layout.search_links[search_buffer_control]

        # Reset content of search control.
        search_buffer_control.buffer.reset()

    # If we're in Vi mode, go back to navigation mode.
    get_app().vi_state.input_mode = InputMode.NAVIGATION


def do_incremental_search(direction: SearchDirection, count: int = 1) -> None:
    """
    Apply search, but keep search buffer focused.
    """
    assert is_searching()

    layout = get_app().layout

    # Only search if the current control is a `BufferControl`.
    from prompt_toolkit.layout.controls import BufferControl

    search_control = layout.current_control
    if not isinstance(search_control, BufferControl):
        return

    prev_control = layout.search_target_buffer_control
    if prev_control is None:
        return
    search_state = prev_control.search_state

    # Update search_state.
    direction_changed = search_state.direction != direction

    search_state.text = search_control.buffer.text
    search_state.direction = direction

    # Apply search to current buffer.
    if not direction_changed:
        prev_control.buffer.apply_search(
            search_state, include_current_position=False, count=count
        )


def accept_search() -> None:
    """
    Accept current search query. Focus original `BufferControl` again.
    """
    layout = get_app().layout

    search_control = layout.current_control
    target_buffer_control = layout.search_target_buffer_control

    from prompt_toolkit.layout.controls import BufferControl

    if not isinstance(search_control, BufferControl):
        return
    if target_buffer_control is None:
        return

    search_state = target_buffer_control.search_state

    # Update search state.
    if search_control.buffer.text:
        search_state.text = search_control.buffer.text

    # Apply search.
    target_buffer_control.buffer.apply_search(
        search_state, include_current_position=True
    )

    # Add query to history of search line.
    search_control.buffer.append_to_history()

    # Stop search and focus previous control again.
    stop_search(target_buffer_control)


def _get_reverse_search_links(
    layout: Layout,
) -> dict[BufferControl, SearchBufferControl]:
    """
    Return mapping from BufferControl to SearchBufferControl.
    """
    return {
        buffer_control: search_buffer_control
        for search_buffer_control, buffer_control in layout.search_links.items()
    }

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_validators.py ===
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
"""Contains utilities to validate argument values in `huggingface_hub`."""

import inspect
import re
import warnings
from functools import wraps
from itertools import chain
from typing import Any, Dict

from huggingface_hub.errors import HFValidationError

from ._typing import CallableT


REPO_ID_REGEX = re.compile(
    r"""
    ^
    (\b[\w\-.]+\b/)? # optional namespace (username or organization)
    \b               # starts with a word boundary
    [\w\-.]{1,96}    # repo_name: alphanumeric + . _ -
    \b               # ends with a word boundary
    $
    """,
    flags=re.VERBOSE,
)


def validate_hf_hub_args(fn: CallableT) -> CallableT:
    """Validate values received as argument for any public method of `huggingface_hub`.

    The goal of this decorator is to harmonize validation of arguments reused
    everywhere. By default, all defined validators are tested.

    Validators:
        - [`~utils.validate_repo_id`]: `repo_id` must be `"repo_name"`
          or `"namespace/repo_name"`. Namespace is a username or an organization.
        - [`~utils.smoothly_deprecate_use_auth_token`]: Use `token` instead of
          `use_auth_token` (only if `use_auth_token` is not expected by the decorated
          function - in practice, always the case in `huggingface_hub`).

    Example:
    ```py
    >>> from huggingface_hub.utils import validate_hf_hub_args

    >>> @validate_hf_hub_args
    ... def my_cool_method(repo_id: str):
    ...     print(repo_id)

    >>> my_cool_method(repo_id="valid_repo_id")
    valid_repo_id

    >>> my_cool_method("other..repo..id")
    huggingface_hub.utils._validators.HFValidationError: Cannot have -- or .. in repo_id: 'other..repo..id'.

    >>> my_cool_method(repo_id="other..repo..id")
    huggingface_hub.utils._validators.HFValidationError: Cannot have -- or .. in repo_id: 'other..repo..id'.

    >>> @validate_hf_hub_args
    ... def my_cool_auth_method(token: str):
    ...     print(token)

    >>> my_cool_auth_method(token="a token")
    "a token"

    >>> my_cool_auth_method(use_auth_token="a use_auth_token")
    "a use_auth_token"

    >>> my_cool_auth_method(token="a token", use_auth_token="a use_auth_token")
    UserWarning: Both `token` and `use_auth_token` are passed (...)
    "a token"
    ```

    Raises:
        [`~utils.HFValidationError`]:
            If an input is not valid.
    """
    # TODO: add an argument to opt-out validation for specific argument?
    signature = inspect.signature(fn)

    # Should the validator switch `use_auth_token` values to `token`? In practice, always
    # True in `huggingface_hub`. Might not be the case in a downstream library.
    check_use_auth_token = "use_auth_token" not in signature.parameters and "token" in signature.parameters

    @wraps(fn)
    def _inner_fn(*args, **kwargs):
        has_token = False
        for arg_name, arg_value in chain(
            zip(signature.parameters, args),  # Args values
            kwargs.items(),  # Kwargs values
        ):
            if arg_name in ["repo_id", "from_id", "to_id"]:
                validate_repo_id(arg_value)

            elif arg_name == "token" and arg_value is not None:
                has_token = True

        if check_use_auth_token:
            kwargs = smoothly_deprecate_use_auth_token(fn_name=fn.__name__, has_token=has_token, kwargs=kwargs)

        return fn(*args, **kwargs)

    return _inner_fn  # type: ignore


def validate_repo_id(repo_id: str) -> None:
    """Validate `repo_id` is valid.

    This is not meant to replace the proper validation made on the Hub but rather to
    avoid local inconsistencies whenever possible (example: passing `repo_type` in the
    `repo_id` is forbidden).

    Rules:
    - Between 1 and 96 characters.
    - Either "repo_name" or "namespace/repo_name"
    - [a-zA-Z0-9] or "-", "_", "."
    - "--" and ".." are forbidden

    Valid: `"foo"`, `"foo/bar"`, `"123"`, `"Foo-BAR_foo.bar123"`

    Not valid: `"datasets/foo/bar"`, `".repo_id"`, `"foo--bar"`, `"foo.git"`

    Example:
    ```py
    >>> from huggingface_hub.utils import validate_repo_id
    >>> validate_repo_id(repo_id="valid_repo_id")
    >>> validate_repo_id(repo_id="other..repo..id")
    huggingface_hub.utils._validators.HFValidationError: Cannot have -- or .. in repo_id: 'other..repo..id'.
    ```

    Discussed in https://github.com/huggingface/huggingface_hub/issues/1008.
    In moon-landing (internal repository):
    - https://github.com/huggingface/moon-landing/blob/main/server/lib/Names.ts#L27
    - https://github.com/huggingface/moon-landing/blob/main/server/views/components/NewRepoForm/NewRepoForm.svelte#L138
    """
    if not isinstance(repo_id, str):
        # Typically, a Path is not a repo_id
        raise HFValidationError(f"Repo id must be a string, not {type(repo_id)}: '{repo_id}'.")

    if repo_id.count("/") > 1:
        raise HFValidationError(
            "Repo id must be in the form 'repo_name' or 'namespace/repo_name':"
            f" '{repo_id}'. Use `repo_type` argument if needed."
        )

    if not REPO_ID_REGEX.match(repo_id):
        raise HFValidationError(
            "Repo id must use alphanumeric chars or '-', '_', '.', '--' and '..' are"
            " forbidden, '-' and '.' cannot start or end the name, max length is 96:"
            f" '{repo_id}'."
        )

    if "--" in repo_id or ".." in repo_id:
        raise HFValidationError(f"Cannot have -- or .. in repo_id: '{repo_id}'.")

    if repo_id.endswith(".git"):
        raise HFValidationError(f"Repo_id cannot end by '.git': '{repo_id}'.")


def smoothly_deprecate_use_auth_token(fn_name: str, has_token: bool, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Smoothly deprecate `use_auth_token` in the `huggingface_hub` codebase.

    The long-term goal is to remove any mention of `use_auth_token` in the codebase in
    favor of a unique and less verbose `token` argument. This will be done a few steps:

    0. Step 0: methods that require a read-access to the Hub use the `use_auth_token`
       argument (`str`, `bool` or `None`). Methods requiring write-access have a `token`
       argument (`str`, `None`). This implicit rule exists to be able to not send the
       token when not necessary (`use_auth_token=False`) even if logged in.

    1. Step 1: we want to harmonize everything and use `token` everywhere (supporting
       `token=False` for read-only methods). In order not to break existing code, if
       `use_auth_token` is passed to a function, the `use_auth_token` value is passed
       as `token` instead, without any warning.
       a. Corner case: if both `use_auth_token` and `token` values are passed, a warning
          is thrown and the `use_auth_token` value is ignored.

    2. Step 2: Once it is release, we should push downstream libraries to switch from
       `use_auth_token` to `token` as much as possible, but without throwing a warning
       (e.g. manually create issues on the corresponding repos).

    3. Step 3: After a transitional period (6 months e.g. until April 2023?), we update
       `huggingface_hub` to throw a warning on `use_auth_token`. Hopefully, very few
       users will be impacted as it would have already been fixed.
       In addition, unit tests in `huggingface_hub` must be adapted to expect warnings
       to be thrown (but still use `use_auth_token` as before).

    4. Step 4: After a normal deprecation cycle (3 releases ?), remove this validator.
       `use_auth_token` will definitely not be supported.
       In addition, we update unit tests in `huggingface_hub` to use `token` everywhere.

    This has been discussed in:
    - https://github.com/huggingface/huggingface_hub/issues/1094.
    - https://github.com/huggingface/huggingface_hub/pull/928
    - (related) https://github.com/huggingface/huggingface_hub/pull/1064
    """
    new_kwargs = kwargs.copy()  # do not mutate input !

    use_auth_token = new_kwargs.pop("use_auth_token", None)  # remove from kwargs
    if use_auth_token is not None:
        if has_token:
            warnings.warn(
                "Both `token` and `use_auth_token` are passed to"
                f" `{fn_name}` with non-None values. `token` is now the"
                " preferred argument to pass a User Access Token."
                " `use_auth_token` value will be ignored."
            )
        else:
            # `token` argument is not passed and a non-None value is passed in
            # `use_auth_token` => use `use_auth_token` value as `token` kwarg.
            new_kwargs["token"] = use_auth_token

    return new_kwargs

# === NexusCore/openenv\Lib\site-packages\litellm\llms\custom_httpx\aiohttp_transport.py ===
import asyncio
import contextlib
import typing
from typing import Callable, Dict, Union

import aiohttp
import aiohttp.client_exceptions
import aiohttp.http_exceptions
import httpx
from aiohttp.client import ClientResponse, ClientSession

from litellm._logging import verbose_logger

AIOHTTP_EXC_MAP: Dict = {
    # Order matters here, most specific exception first
    # Timeout related exceptions
    aiohttp.ServerTimeoutError: httpx.TimeoutException,
    aiohttp.ConnectionTimeoutError: httpx.ConnectTimeout,
    aiohttp.SocketTimeoutError: httpx.ReadTimeout,
    # Proxy related exceptions
    aiohttp.ClientProxyConnectionError: httpx.ProxyError,
    # SSL related exceptions
    aiohttp.ClientConnectorCertificateError: httpx.ProtocolError,
    aiohttp.ClientSSLError: httpx.ProtocolError,
    aiohttp.ServerFingerprintMismatch: httpx.ProtocolError,
    # Network related exceptions
    aiohttp.ClientConnectorError: httpx.ConnectError,
    aiohttp.ClientOSError: httpx.ConnectError,
    aiohttp.ClientPayloadError: httpx.ReadError,
    # Connection disconnection exceptions
    aiohttp.ServerDisconnectedError: httpx.ReadError,
    # Response related exceptions
    aiohttp.ClientConnectionError: httpx.NetworkError,
    aiohttp.ClientPayloadError: httpx.ReadError,
    aiohttp.ContentTypeError: httpx.ReadError,
    aiohttp.TooManyRedirects: httpx.TooManyRedirects,
    # URL related exceptions
    aiohttp.InvalidURL: httpx.InvalidURL,
    # Base exceptions
    aiohttp.ClientError: httpx.RequestError,
}

# Add client_exceptions module exceptions
try:
    import aiohttp.client_exceptions

    AIOHTTP_EXC_MAP[aiohttp.client_exceptions.ClientPayloadError] = httpx.ReadError
except ImportError:
    pass


@contextlib.contextmanager
def map_aiohttp_exceptions() -> typing.Iterator[None]:
    try:
        yield
    except Exception as exc:
        mapped_exc = None

        for from_exc, to_exc in AIOHTTP_EXC_MAP.items():
            if not isinstance(exc, from_exc):  # type: ignore
                continue
            if mapped_exc is None or issubclass(to_exc, mapped_exc):
                mapped_exc = to_exc

        if mapped_exc is None:  # pragma: no cover
            raise

        message = str(exc)
        raise mapped_exc(message) from exc


class AiohttpResponseStream(httpx.AsyncByteStream):
    CHUNK_SIZE = 1024 * 16

    def __init__(self, aiohttp_response: ClientResponse) -> None:
        self._aiohttp_response = aiohttp_response

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        try:
            async for chunk in self._aiohttp_response.content.iter_chunked(
                self.CHUNK_SIZE
            ):
                yield chunk
        except (
            aiohttp.ClientPayloadError,
            aiohttp.client_exceptions.ClientPayloadError,
        ) as e:
            # Handle incomplete transfers more gracefully
            # Log the error but don't re-raise if we've already yielded some data
            verbose_logger.debug(f"Transfer incomplete, but continuing: {e}")
            # If the error is due to incomplete transfer encoding, we can still
            # return what we've received so far, similar to how httpx handles it
            return
        except aiohttp.http_exceptions.TransferEncodingError as e:
            # Handle transfer encoding errors gracefully
            verbose_logger.debug(f"Transfer encoding error, but continuing: {e}")
            return
        except Exception:
            # For other exceptions, use the normal mapping
            with map_aiohttp_exceptions():
                raise

    async def aclose(self) -> None:
        with map_aiohttp_exceptions():
            await self._aiohttp_response.__aexit__(None, None, None)


class AiohttpTransport(httpx.AsyncBaseTransport):
    def __init__(
        self, client: Union[ClientSession, Callable[[], ClientSession]]
    ) -> None:
        self.client = client

    async def aclose(self) -> None:
        if isinstance(self.client, ClientSession):
            await self.client.close()


class LiteLLMAiohttpTransport(AiohttpTransport):
    """
    LiteLLM wrapper around AiohttpTransport to handle %-encodings in URLs
    and event loop lifecycle issues in CI/CD environments

    Credit to: https://github.com/karpetrosyan/httpx-aiohttp for this implementation
    """

    def __init__(self, client: Union[ClientSession, Callable[[], ClientSession]]):
        self.client = client
        super().__init__(client=client)
        # Store the client factory for recreating sessions when needed
        if callable(client):
            self._client_factory = client

    def _get_valid_client_session(self) -> ClientSession:
        """
        Helper to get a valid ClientSession for the current event loop.

        This handles the case where the session was created in a different
        event loop that may have been closed (common in CI/CD environments).
        """
        from aiohttp.client import ClientSession

        # If we don't have a client or it's not a ClientSession, create one
        if not isinstance(self.client, ClientSession):
            if hasattr(self, "_client_factory") and callable(self._client_factory):
                self.client = self._client_factory()
            else:
                self.client = ClientSession()
            return self.client

        # Check if the existing session is still valid for the current event loop
        try:
            session_loop = getattr(self.client, "_loop", None)
            current_loop = asyncio.get_running_loop()

            # If session is from a different or closed loop, recreate it
            if (
                session_loop is None
                or session_loop != current_loop
                or session_loop.is_closed()
            ):
                # Clean up the old session
                try:
                    # Note: not awaiting close() here as it might be from a different loop
                    # The session will be garbage collected
                    pass
                except Exception as e:
                    verbose_logger.debug(f"Error closing old session: {e}")
                    pass

                # Create a new session in the current event loop
                if hasattr(self, "_client_factory") and callable(self._client_factory):
                    self.client = self._client_factory()
                else:
                    self.client = ClientSession()

        except (RuntimeError, AttributeError):
            # If we can't check the loop or session is invalid, recreate it
            if hasattr(self, "_client_factory") and callable(self._client_factory):
                self.client = self._client_factory()
            else:
                self.client = ClientSession()

        return self.client

    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        from aiohttp import ClientTimeout
        from yarl import URL as YarlURL

        timeout = request.extensions.get("timeout", {})
        sni_hostname = request.extensions.get("sni_hostname")

        # Use helper to ensure we have a valid session for the current event loop
        client_session = self._get_valid_client_session()

        with map_aiohttp_exceptions():
            try:
                data = request.content
            except httpx.RequestNotRead:
                data = request.stream  # type: ignore
                request.headers.pop("transfer-encoding", None)  # handled by aiohttp

            response = await client_session.request(
                method=request.method,
                url=YarlURL(str(request.url), encoded=True),
                headers=request.headers,
                data=data,
                allow_redirects=False,
                auto_decompress=False,
                timeout=ClientTimeout(
                    sock_connect=timeout.get("connect"),
                    sock_read=timeout.get("read"),
                    connect=timeout.get("pool"),
                ),
                server_hostname=sni_hostname,
            ).__aenter__()

        return httpx.Response(
            status_code=response.status,
            headers=response.headers,
            content=AiohttpResponseStream(response),
            request=request,
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\firefox\firefox_binary.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


import os
import time
from platform import system
from subprocess import DEVNULL, STDOUT, Popen

from typing_extensions import deprecated

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common import utils


@deprecated("Use binary_location property in Firefox Options to set location")
class FirefoxBinary:
    NO_FOCUS_LIBRARY_NAME = "x_ignore_nofocus.so"

    def __init__(self, firefox_path=None, log_file=None):
        """Creates a new instance of Firefox binary.

        :Args:
         - firefox_path - Path to the Firefox executable. By default, it will be detected from the standard locations.
         - log_file - A file object to redirect the firefox process output to. It can be sys.stdout.
                      Please note that with parallel run the output won't be synchronous.
                      By default, it will be redirected to /dev/null.
        """
        self._start_cmd = firefox_path
        # We used to default to subprocess.PIPE instead of /dev/null, but after
        # a while the pipe would fill up and Firefox would freeze.
        self._log_file = log_file or DEVNULL
        self.command_line = None
        self.platform = system().lower()
        if not self._start_cmd:
            self._start_cmd = self._get_firefox_start_cmd()
        if not self._start_cmd.strip():
            raise WebDriverException(
                "Failed to find firefox binary. You can set it by specifying "
                "the path to 'firefox_binary':\n\nfrom "
                "selenium.webdriver.firefox.firefox_binary import "
                "FirefoxBinary\n\nbinary = "
                "FirefoxBinary('/path/to/binary')\ndriver = "
                "webdriver.Firefox(firefox_binary=binary)"
            )
        # Rather than modifying the environment of the calling Python process
        # copy it and modify as needed.
        self._firefox_env = os.environ.copy()
        self._firefox_env["MOZ_CRASHREPORTER_DISABLE"] = "1"
        self._firefox_env["MOZ_NO_REMOTE"] = "1"
        self._firefox_env["NO_EM_RESTART"] = "1"

    def add_command_line_options(self, *args):
        self.command_line = args

    def launch_browser(self, profile, timeout=30):
        """Launches the browser for the given profile name.

        It is assumed the profile already exists.
        """
        self.profile = profile

        self._start_from_profile_path(self.profile.path)
        self._wait_until_connectable(timeout=timeout)

    def kill(self):
        """Kill the browser.

        This is useful when the browser is stuck.
        """
        if self.process:
            self.process.kill()
            self.process.wait()

    def _start_from_profile_path(self, path):
        self._firefox_env["XRE_PROFILE_PATH"] = path

        if self.platform == "linux":
            self._modify_link_library_path()
        command = [self._start_cmd, "-foreground"]
        if self.command_line:
            for cli in self.command_line:
                command.append(cli)
        self.process = Popen(command, stdout=self._log_file, stderr=STDOUT, env=self._firefox_env)

    def _wait_until_connectable(self, timeout=30):
        """Blocks until the extension is connectable in the firefox."""
        count = 0
        while not utils.is_connectable(self.profile.port):
            if self.process.poll():
                # Browser has exited
                raise WebDriverException(
                    "The browser appears to have exited "
                    "before we could connect. If you specified a log_file in "
                    "the FirefoxBinary constructor, check it for details."
                )
            if count >= timeout:
                self.kill()
                raise WebDriverException(
                    "Can't load the profile. Possible firefox version mismatch. "
                    "You must use GeckoDriver instead for Firefox 48+. Profile "
                    f"Dir: {self.profile.path} If you specified a log_file in the "
                    "FirefoxBinary constructor, check it for details."
                )
            count += 1
            time.sleep(1)
        return True

    def _find_exe_in_registry(self):
        try:
            from _winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, OpenKey, QueryValue
        except ImportError:
            from winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, OpenKey, QueryValue
        import shlex

        keys = (
            r"SOFTWARE\Classes\FirefoxHTML\shell\open\command",
            r"SOFTWARE\Classes\Applications\firefox.exe\shell\open\command",
        )
        command = ""
        for path in keys:
            try:
                key = OpenKey(HKEY_LOCAL_MACHINE, path)
                command = QueryValue(key, "")
                break
            except OSError:
                try:
                    key = OpenKey(HKEY_CURRENT_USER, path)
                    command = QueryValue(key, "")
                    break
                except OSError:
                    pass
        else:
            return ""

        if not command:
            return ""

        return shlex.split(command)[0]

    def _get_firefox_start_cmd(self):
        """Return the command to start firefox."""
        start_cmd = ""
        if self.platform == "darwin":  # small darwin due to lower() in self.platform
            ffname = "firefox"
            start_cmd = self.which(ffname)
            # use hardcoded path if nothing else was found by which()
            if not start_cmd:
                start_cmd = "/Applications/Firefox.app/Contents/MacOS/firefox"
            # fallback to homebrew installation for mac users
            if not os.path.exists(start_cmd):
                start_cmd = os.path.expanduser("~") + start_cmd
        elif self.platform == "windows":  # same
            start_cmd = self._find_exe_in_registry() or self._default_windows_location()
        elif self.platform == "java" and os.name == "nt":
            start_cmd = self._default_windows_location()
        else:
            for ffname in ["firefox", "iceweasel"]:
                start_cmd = self.which(ffname)
                if start_cmd:
                    break
            else:
                # couldn't find firefox on the system path
                raise RuntimeError(
                    "Could not find firefox in your system PATH."
                    " Please specify the firefox binary location or install firefox"
                )
        return start_cmd

    def _default_windows_location(self):
        program_files = [
            os.getenv("PROGRAMFILES", r"C:\Program Files"),
            os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        ]
        for path in program_files:
            binary_path = os.path.join(path, r"Mozilla Firefox\firefox.exe")
            if os.access(binary_path, os.X_OK):
                return binary_path
        return ""

    def _modify_link_library_path(self):
        existing_ld_lib_path = os.environ.get("LD_LIBRARY_PATH", "")

        new_ld_lib_path = self._extract_and_check(self.profile, "x86", "amd64")

        new_ld_lib_path += existing_ld_lib_path

        self._firefox_env["LD_LIBRARY_PATH"] = new_ld_lib_path
        self._firefox_env["LD_PRELOAD"] = self.NO_FOCUS_LIBRARY_NAME

    def _extract_and_check(self, profile, x86, amd64):
        paths = [x86, amd64]
        built_path = ""
        for path in paths:
            library_path = os.path.join(profile.path, path)
            if not os.path.exists(library_path):
                os.makedirs(library_path)
            import shutil

            shutil.copy(os.path.join(os.path.dirname(__file__), path, self.NO_FOCUS_LIBRARY_NAME), library_path)
            built_path += library_path + ":"

        return built_path

    def which(self, fname):
        """Returns the fully qualified path by searching Path of the given
        name."""
        for pe in os.environ["PATH"].split(os.pathsep):
            checkname = os.path.join(pe, fname)
            if os.access(checkname, os.X_OK) and not os.path.isdir(checkname):
                return checkname
        return None

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\control.py ===
import sys
import time
from typing import TYPE_CHECKING, Callable, Dict, Iterable, List, Union

if sys.version_info >= (3, 8):
    from typing import Final
else:
    from pip._vendor.typing_extensions import Final  # pragma: no cover

from .segment import ControlCode, ControlType, Segment

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderResult

STRIP_CONTROL_CODES: Final = [
    7,  # Bell
    8,  # Backspace
    11,  # Vertical tab
    12,  # Form feed
    13,  # Carriage return
]
_CONTROL_STRIP_TRANSLATE: Final = {
    _codepoint: None for _codepoint in STRIP_CONTROL_CODES
}

CONTROL_ESCAPE: Final = {
    7: "\\a",
    8: "\\b",
    11: "\\v",
    12: "\\f",
    13: "\\r",
}

CONTROL_CODES_FORMAT: Dict[int, Callable[..., str]] = {
    ControlType.BELL: lambda: "\x07",
    ControlType.CARRIAGE_RETURN: lambda: "\r",
    ControlType.HOME: lambda: "\x1b[H",
    ControlType.CLEAR: lambda: "\x1b[2J",
    ControlType.ENABLE_ALT_SCREEN: lambda: "\x1b[?1049h",
    ControlType.DISABLE_ALT_SCREEN: lambda: "\x1b[?1049l",
    ControlType.SHOW_CURSOR: lambda: "\x1b[?25h",
    ControlType.HIDE_CURSOR: lambda: "\x1b[?25l",
    ControlType.CURSOR_UP: lambda param: f"\x1b[{param}A",
    ControlType.CURSOR_DOWN: lambda param: f"\x1b[{param}B",
    ControlType.CURSOR_FORWARD: lambda param: f"\x1b[{param}C",
    ControlType.CURSOR_BACKWARD: lambda param: f"\x1b[{param}D",
    ControlType.CURSOR_MOVE_TO_COLUMN: lambda param: f"\x1b[{param+1}G",
    ControlType.ERASE_IN_LINE: lambda param: f"\x1b[{param}K",
    ControlType.CURSOR_MOVE_TO: lambda x, y: f"\x1b[{y+1};{x+1}H",
    ControlType.SET_WINDOW_TITLE: lambda title: f"\x1b]0;{title}\x07",
}


class Control:
    """A renderable that inserts a control code (non printable but may move cursor).

    Args:
        *codes (str): Positional arguments are either a :class:`~rich.segment.ControlType` enum or a
            tuple of ControlType and an integer parameter
    """

    __slots__ = ["segment"]

    def __init__(self, *codes: Union[ControlType, ControlCode]) -> None:
        control_codes: List[ControlCode] = [
            (code,) if isinstance(code, ControlType) else code for code in codes
        ]
        _format_map = CONTROL_CODES_FORMAT
        rendered_codes = "".join(
            _format_map[code](*parameters) for code, *parameters in control_codes
        )
        self.segment = Segment(rendered_codes, None, control_codes)

    @classmethod
    def bell(cls) -> "Control":
        """Ring the 'bell'."""
        return cls(ControlType.BELL)

    @classmethod
    def home(cls) -> "Control":
        """Move cursor to 'home' position."""
        return cls(ControlType.HOME)

    @classmethod
    def move(cls, x: int = 0, y: int = 0) -> "Control":
        """Move cursor relative to current position.

        Args:
            x (int): X offset.
            y (int): Y offset.

        Returns:
            ~Control: Control object.

        """

        def get_codes() -> Iterable[ControlCode]:
            control = ControlType
            if x:
                yield (
                    control.CURSOR_FORWARD if x > 0 else control.CURSOR_BACKWARD,
                    abs(x),
                )
            if y:
                yield (
                    control.CURSOR_DOWN if y > 0 else control.CURSOR_UP,
                    abs(y),
                )

        control = cls(*get_codes())
        return control

    @classmethod
    def move_to_column(cls, x: int, y: int = 0) -> "Control":
        """Move to the given column, optionally add offset to row.

        Returns:
            x (int): absolute x (column)
            y (int): optional y offset (row)

        Returns:
            ~Control: Control object.
        """

        return (
            cls(
                (ControlType.CURSOR_MOVE_TO_COLUMN, x),
                (
                    ControlType.CURSOR_DOWN if y > 0 else ControlType.CURSOR_UP,
                    abs(y),
                ),
            )
            if y
            else cls((ControlType.CURSOR_MOVE_TO_COLUMN, x))
        )

    @classmethod
    def move_to(cls, x: int, y: int) -> "Control":
        """Move cursor to absolute position.

        Args:
            x (int): x offset (column)
            y (int): y offset (row)

        Returns:
            ~Control: Control object.
        """
        return cls((ControlType.CURSOR_MOVE_TO, x, y))

    @classmethod
    def clear(cls) -> "Control":
        """Clear the screen."""
        return cls(ControlType.CLEAR)

    @classmethod
    def show_cursor(cls, show: bool) -> "Control":
        """Show or hide the cursor."""
        return cls(ControlType.SHOW_CURSOR if show else ControlType.HIDE_CURSOR)

    @classmethod
    def alt_screen(cls, enable: bool) -> "Control":
        """Enable or disable alt screen."""
        if enable:
            return cls(ControlType.ENABLE_ALT_SCREEN, ControlType.HOME)
        else:
            return cls(ControlType.DISABLE_ALT_SCREEN)

    @classmethod
    def title(cls, title: str) -> "Control":
        """Set the terminal window title

        Args:
            title (str): The new terminal window title
        """
        return cls((ControlType.SET_WINDOW_TITLE, title))

    def __str__(self) -> str:
        return self.segment.text

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.segment.text:
            yield self.segment


def strip_control_codes(
    text: str, _translate_table: Dict[int, None] = _CONTROL_STRIP_TRANSLATE
) -> str:
    """Remove control codes from text.

    Args:
        text (str): A string possibly contain control codes.

    Returns:
        str: String with control codes removed.
    """
    return text.translate(_translate_table)


def escape_control_codes(
    text: str,
    _translate_table: Dict[int, str] = CONTROL_ESCAPE,
) -> str:
    """Replace control codes with their "escaped" equivalent in the given text.
    (e.g. "\b" becomes "\\b")

    Args:
        text (str): A string possibly containing control codes.

    Returns:
        str: String with control codes replaced with their escaped version.
    """
    return text.translate(_translate_table)


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Console

    console = Console()
    console.print("Look at the title of your terminal window ^")
    # console.print(Control((ControlType.SET_WINDOW_TITLE, "Hello, world!")))
    for i in range(10):
        console.set_window_title("🚀 Loading" + "." * i)
        time.sleep(0.5)

# === NexusCore/openenv\Lib\site-packages\matplotlib\hatch.py ===
"""Contains classes for generating hatch patterns."""

import numpy as np

from matplotlib import _api
from matplotlib.path import Path


class HatchPatternBase:
    """The base class for a hatch pattern."""
    pass


class HorizontalHatch(HatchPatternBase):
    def __init__(self, hatch, density):
        self.num_lines = int((hatch.count('-') + hatch.count('+')) * density)
        self.num_vertices = self.num_lines * 2

    def set_vertices_and_codes(self, vertices, codes):
        steps, stepsize = np.linspace(0.0, 1.0, self.num_lines, False,
                                      retstep=True)
        steps += stepsize / 2.
        vertices[0::2, 0] = 0.0
        vertices[0::2, 1] = steps
        vertices[1::2, 0] = 1.0
        vertices[1::2, 1] = steps
        codes[0::2] = Path.MOVETO
        codes[1::2] = Path.LINETO


class VerticalHatch(HatchPatternBase):
    def __init__(self, hatch, density):
        self.num_lines = int((hatch.count('|') + hatch.count('+')) * density)
        self.num_vertices = self.num_lines * 2

    def set_vertices_and_codes(self, vertices, codes):
        steps, stepsize = np.linspace(0.0, 1.0, self.num_lines, False,
                                      retstep=True)
        steps += stepsize / 2.
        vertices[0::2, 0] = steps
        vertices[0::2, 1] = 0.0
        vertices[1::2, 0] = steps
        vertices[1::2, 1] = 1.0
        codes[0::2] = Path.MOVETO
        codes[1::2] = Path.LINETO


class NorthEastHatch(HatchPatternBase):
    def __init__(self, hatch, density):
        self.num_lines = int(
            (hatch.count('/') + hatch.count('x') + hatch.count('X')) * density)
        if self.num_lines:
            self.num_vertices = (self.num_lines + 1) * 2
        else:
            self.num_vertices = 0

    def set_vertices_and_codes(self, vertices, codes):
        steps = np.linspace(-0.5, 0.5, self.num_lines + 1)
        vertices[0::2, 0] = 0.0 + steps
        vertices[0::2, 1] = 0.0 - steps
        vertices[1::2, 0] = 1.0 + steps
        vertices[1::2, 1] = 1.0 - steps
        codes[0::2] = Path.MOVETO
        codes[1::2] = Path.LINETO


class SouthEastHatch(HatchPatternBase):
    def __init__(self, hatch, density):
        self.num_lines = int(
            (hatch.count('\\') + hatch.count('x') + hatch.count('X'))
            * density)
        if self.num_lines:
            self.num_vertices = (self.num_lines + 1) * 2
        else:
            self.num_vertices = 0

    def set_vertices_and_codes(self, vertices, codes):
        steps = np.linspace(-0.5, 0.5, self.num_lines + 1)
        vertices[0::2, 0] = 0.0 + steps
        vertices[0::2, 1] = 1.0 + steps
        vertices[1::2, 0] = 1.0 + steps
        vertices[1::2, 1] = 0.0 + steps
        codes[0::2] = Path.MOVETO
        codes[1::2] = Path.LINETO


class Shapes(HatchPatternBase):
    filled = False

    def __init__(self, hatch, density):
        if self.num_rows == 0:
            self.num_shapes = 0
            self.num_vertices = 0
        else:
            self.num_shapes = ((self.num_rows // 2 + 1) * (self.num_rows + 1) +
                               (self.num_rows // 2) * self.num_rows)
            self.num_vertices = (self.num_shapes *
                                 len(self.shape_vertices) *
                                 (1 if self.filled else 2))

    def set_vertices_and_codes(self, vertices, codes):
        offset = 1.0 / self.num_rows
        shape_vertices = self.shape_vertices * offset * self.size
        shape_codes = self.shape_codes
        if not self.filled:
            shape_vertices = np.concatenate(  # Forward, then backward.
                [shape_vertices, shape_vertices[::-1] * 0.9])
            shape_codes = np.concatenate([shape_codes, shape_codes])
        vertices_parts = []
        codes_parts = []
        for row in range(self.num_rows + 1):
            if row % 2 == 0:
                cols = np.linspace(0, 1, self.num_rows + 1)
            else:
                cols = np.linspace(offset / 2, 1 - offset / 2, self.num_rows)
            row_pos = row * offset
            for col_pos in cols:
                vertices_parts.append(shape_vertices + [col_pos, row_pos])
                codes_parts.append(shape_codes)
        np.concatenate(vertices_parts, out=vertices)
        np.concatenate(codes_parts, out=codes)


class Circles(Shapes):
    def __init__(self, hatch, density):
        path = Path.unit_circle()
        self.shape_vertices = path.vertices
        self.shape_codes = path.codes
        super().__init__(hatch, density)


class SmallCircles(Circles):
    size = 0.2

    def __init__(self, hatch, density):
        self.num_rows = (hatch.count('o')) * density
        super().__init__(hatch, density)


class LargeCircles(Circles):
    size = 0.35

    def __init__(self, hatch, density):
        self.num_rows = (hatch.count('O')) * density
        super().__init__(hatch, density)


class SmallFilledCircles(Circles):
    size = 0.1
    filled = True

    def __init__(self, hatch, density):
        self.num_rows = (hatch.count('.')) * density
        super().__init__(hatch, density)


class Stars(Shapes):
    size = 1.0 / 3.0
    filled = True

    def __init__(self, hatch, density):
        self.num_rows = (hatch.count('*')) * density
        path = Path.unit_regular_star(5)
        self.shape_vertices = path.vertices
        self.shape_codes = np.full(len(self.shape_vertices), Path.LINETO,
                                   dtype=Path.code_type)
        self.shape_codes[0] = Path.MOVETO
        super().__init__(hatch, density)

_hatch_types = [
    HorizontalHatch,
    VerticalHatch,
    NorthEastHatch,
    SouthEastHatch,
    SmallCircles,
    LargeCircles,
    SmallFilledCircles,
    Stars
    ]


def _validate_hatch_pattern(hatch):
    valid_hatch_patterns = set(r'-+|/\xXoO.*')
    if hatch is not None:
        invalids = set(hatch).difference(valid_hatch_patterns)
        if invalids:
            valid = ''.join(sorted(valid_hatch_patterns))
            invalids = ''.join(sorted(invalids))
            _api.warn_deprecated(
                '3.4',
                removal='3.11',  # one release after custom hatches (#20690)
                message=f'hatch must consist of a string of "{valid}" or '
                        'None, but found the following invalid values '
                        f'"{invalids}". Passing invalid values is deprecated '
                        'since %(since)s and will become an error in %(removal)s.'
            )


def get_path(hatchpattern, density=6):
    """
    Given a hatch specifier, *hatchpattern*, generates Path to render
    the hatch in a unit square.  *density* is the number of lines per
    unit square.
    """
    density = int(density)

    patterns = [hatch_type(hatchpattern, density)
                for hatch_type in _hatch_types]
    num_vertices = sum([pattern.num_vertices for pattern in patterns])

    if num_vertices == 0:
        return Path(np.empty((0, 2)))

    vertices = np.empty((num_vertices, 2))
    codes = np.empty(num_vertices, Path.code_type)

    cursor = 0
    for pattern in patterns:
        if pattern.num_vertices != 0:
            vertices_chunk = vertices[cursor:cursor + pattern.num_vertices]
            codes_chunk = codes[cursor:cursor + pattern.num_vertices]
            pattern.set_vertices_and_codes(vertices_chunk, codes_chunk)
            cursor += pattern.num_vertices

    return Path(vertices, codes)

# === NexusCore/openenv\Lib\site-packages\proto\datetime_helpers.py ===
# Copyright 2017 Google LLC
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

"""Helpers for :mod:`datetime`."""

import calendar
import datetime
import re

from google.protobuf import timestamp_pb2


_UTC_EPOCH = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

_RFC3339_MICROS = "%Y-%m-%dT%H:%M:%S.%fZ"
_RFC3339_NO_FRACTION = "%Y-%m-%dT%H:%M:%S"
# datetime.strptime cannot handle nanosecond precision:  parse w/ regex
_RFC3339_NANOS = re.compile(
    r"""
    (?P<no_fraction>
        \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}  # YYYY-MM-DDTHH:MM:SS
    )
    (                                        # Optional decimal part
     \.                                      # decimal point
     (?P<nanos>\d{1,9})                      # nanoseconds, maybe truncated
    )?
    Z                                        # Zulu
""",
    re.VERBOSE,
)


def _from_microseconds(value):
    """Convert timestamp in microseconds since the unix epoch to datetime.

    Args:
        value (float): The timestamp to convert, in microseconds.

    Returns:
        datetime.datetime: The datetime object equivalent to the timestamp in
            UTC.
    """
    return _UTC_EPOCH + datetime.timedelta(microseconds=value)


def _to_rfc3339(value, ignore_zone=True):
    """Convert a datetime to an RFC3339 timestamp string.

    Args:
        value (datetime.datetime):
            The datetime object to be converted to a string.
        ignore_zone (bool): If True, then the timezone (if any) of the
            datetime object is ignored and the datetime is treated as UTC.

    Returns:
        str: The RFC3339 formatted string representing the datetime.
    """
    if not ignore_zone and value.tzinfo is not None:
        # Convert to UTC and remove the time zone info.
        value = value.replace(tzinfo=None) - value.utcoffset()

    return value.strftime(_RFC3339_MICROS)


class DatetimeWithNanoseconds(datetime.datetime):
    """Track nanosecond in addition to normal datetime attrs.

    Nanosecond can be passed only as a keyword argument.
    """

    __slots__ = ("_nanosecond",)

    # pylint: disable=arguments-differ
    def __new__(cls, *args, **kw):
        nanos = kw.pop("nanosecond", 0)
        if nanos > 0:
            if "microsecond" in kw:
                raise TypeError("Specify only one of 'microsecond' or 'nanosecond'")
            kw["microsecond"] = nanos // 1000
        inst = datetime.datetime.__new__(cls, *args, **kw)
        inst._nanosecond = nanos or 0
        return inst

    # pylint: disable=arguments-differ
    def replace(self, *args, **kw):
        """Return a date with the same value, except for those parameters given
        new values by whichever keyword arguments are specified. For example,
        if d == date(2002, 12, 31), then
        d.replace(day=26) == date(2002, 12, 26).
        NOTE: nanosecond and microsecond are mutually exclusive arguments.
        """

        ms_provided = "microsecond" in kw
        ns_provided = "nanosecond" in kw
        provided_ns = kw.pop("nanosecond", 0)

        prev_nanos = self.nanosecond

        if ms_provided and ns_provided:
            raise TypeError("Specify only one of 'microsecond' or 'nanosecond'")

        if ns_provided:
            # if nanos were provided, manipulate microsecond kw arg to super
            kw["microsecond"] = provided_ns // 1000
        inst = super().replace(*args, **kw)

        if ms_provided:
            # ms were provided, nanos are invalid, build from ms
            inst._nanosecond = inst.microsecond * 1000
        elif ns_provided:
            # ns were provided, replace nanoseconds to match after calling super
            inst._nanosecond = provided_ns
        else:
            # if neither ms or ns were provided, passthru previous nanos.
            inst._nanosecond = prev_nanos

        return inst

    @property
    def nanosecond(self):
        """Read-only: nanosecond precision."""
        return self._nanosecond or self.microsecond * 1000

    def rfc3339(self):
        """Return an RFC3339-compliant timestamp.

        Returns:
            (str): Timestamp string according to RFC3339 spec.
        """
        if self._nanosecond == 0:
            return _to_rfc3339(self)
        nanos = str(self._nanosecond).rjust(9, "0").rstrip("0")
        return "{}.{}Z".format(self.strftime(_RFC3339_NO_FRACTION), nanos)

    @classmethod
    def from_rfc3339(cls, stamp):
        """Parse RFC3339-compliant timestamp, preserving nanoseconds.

        Args:
            stamp (str): RFC3339 stamp, with up to nanosecond precision

        Returns:
            :class:`DatetimeWithNanoseconds`:
                an instance matching the timestamp string

        Raises:
            ValueError: if `stamp` does not match the expected format
        """
        with_nanos = _RFC3339_NANOS.match(stamp)
        if with_nanos is None:
            raise ValueError(
                "Timestamp: {}, does not match pattern: {}".format(
                    stamp, _RFC3339_NANOS.pattern
                )
            )
        bare = datetime.datetime.strptime(
            with_nanos.group("no_fraction"), _RFC3339_NO_FRACTION
        )
        fraction = with_nanos.group("nanos")
        if fraction is None:
            nanos = 0
        else:
            scale = 9 - len(fraction)
            nanos = int(fraction) * (10**scale)
        return cls(
            bare.year,
            bare.month,
            bare.day,
            bare.hour,
            bare.minute,
            bare.second,
            nanosecond=nanos,
            tzinfo=datetime.timezone.utc,
        )

    def timestamp_pb(self):
        """Return a timestamp message.

        Returns:
            (:class:`~google.protobuf.timestamp_pb2.Timestamp`): Timestamp message
        """
        inst = (
            self
            if self.tzinfo is not None
            else self.replace(tzinfo=datetime.timezone.utc)
        )
        delta = inst - _UTC_EPOCH
        seconds = int(delta.total_seconds())
        nanos = self._nanosecond or self.microsecond * 1000
        return timestamp_pb2.Timestamp(seconds=seconds, nanos=nanos)

    @classmethod
    def from_timestamp_pb(cls, stamp):
        """Parse RFC3339-compliant timestamp, preserving nanoseconds.

        Args:
            stamp (:class:`~google.protobuf.timestamp_pb2.Timestamp`): timestamp message

        Returns:
            :class:`DatetimeWithNanoseconds`:
                an instance matching the timestamp message
        """
        microseconds = int(stamp.seconds * 1e6)
        bare = _from_microseconds(microseconds)
        return cls(
            bare.year,
            bare.month,
            bare.day,
            bare.hour,
            bare.minute,
            bare.second,
            nanosecond=stamp.nanos,
            tzinfo=datetime.timezone.utc,
        )

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc2560.py ===
#
# This file is part of pyasn1-modules software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# OCSP request/response syntax
#
# Derived from a minimal OCSP library (RFC2560) code written by
# Bud P. Bruegger <bud@ancitel.it>
# Copyright: Ancitel, S.p.a,  Rome, Italy
# License: BSD
#

#
# current limitations:
# * request and response works only for a single certificate
# * only some values are parsed out of the response
# * the request does't set a nonce nor signature
# * there is no signature validation of the response
# * dates are left as strings in GeneralizedTime format -- datetime.datetime
# would be nicer
#
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc2459


# Start of OCSP module definitions

# This should be in directory Authentication Framework (X.509) module

class CRLReason(univ.Enumerated):
    namedValues = namedval.NamedValues(
        ('unspecified', 0),
        ('keyCompromise', 1),
        ('cACompromise', 2),
        ('affiliationChanged', 3),
        ('superseded', 4),
        ('cessationOfOperation', 5),
        ('certificateHold', 6),
        ('removeFromCRL', 8),
        ('privilegeWithdrawn', 9),
        ('aACompromise', 10)
    )


# end of directory Authentication Framework (X.509) module

# This should be in PKIX Certificate Extensions module

class GeneralName(univ.OctetString):
    pass


# end of PKIX Certificate Extensions module

id_kp_OCSPSigning = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 3, 9))
id_pkix_ocsp = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 48, 1))
id_pkix_ocsp_basic = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 48, 1, 1))
id_pkix_ocsp_nonce = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 48, 1, 2))
id_pkix_ocsp_crl = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 48, 1, 3))
id_pkix_ocsp_response = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 48, 1, 4))
id_pkix_ocsp_nocheck = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 48, 1, 5))
id_pkix_ocsp_archive_cutoff = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 48, 1, 6))
id_pkix_ocsp_service_locator = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 48, 1, 7))


class AcceptableResponses(univ.SequenceOf):
    componentType = univ.ObjectIdentifier()


class ArchiveCutoff(useful.GeneralizedTime):
    pass


class UnknownInfo(univ.Null):
    pass


class RevokedInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('revocationTime', useful.GeneralizedTime()),
        namedtype.OptionalNamedType('revocationReason', CRLReason().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class CertID(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('hashAlgorithm', rfc2459.AlgorithmIdentifier()),
        namedtype.NamedType('issuerNameHash', univ.OctetString()),
        namedtype.NamedType('issuerKeyHash', univ.OctetString()),
        namedtype.NamedType('serialNumber', rfc2459.CertificateSerialNumber())
    )


class CertStatus(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('good',
                            univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('revoked',
                            RevokedInfo().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('unknown',
                            UnknownInfo().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class SingleResponse(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certID', CertID()),
        namedtype.NamedType('certStatus', CertStatus()),
        namedtype.NamedType('thisUpdate', useful.GeneralizedTime()),
        namedtype.OptionalNamedType('nextUpdate', useful.GeneralizedTime().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('singleExtensions', rfc2459.Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class KeyHash(univ.OctetString):
    pass


class ResponderID(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('byName',
                            rfc2459.Name().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('byKey',
                            KeyHash().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class Version(univ.Integer):
    namedValues = namedval.NamedValues(('v1', 0))


class ResponseData(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.DefaultedNamedType('version', Version('v1').subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('responderID', ResponderID()),
        namedtype.NamedType('producedAt', useful.GeneralizedTime()),
        namedtype.NamedType('responses', univ.SequenceOf(componentType=SingleResponse())),
        namedtype.OptionalNamedType('responseExtensions', rfc2459.Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class BasicOCSPResponse(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('tbsResponseData', ResponseData()),
        namedtype.NamedType('signatureAlgorithm', rfc2459.AlgorithmIdentifier()),
        namedtype.NamedType('signature', univ.BitString()),
        namedtype.OptionalNamedType('certs', univ.SequenceOf(componentType=rfc2459.Certificate()).subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class ResponseBytes(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('responseType', univ.ObjectIdentifier()),
        namedtype.NamedType('response', univ.OctetString())
    )


class OCSPResponseStatus(univ.Enumerated):
    namedValues = namedval.NamedValues(
        ('successful', 0),
        ('malformedRequest', 1),
        ('internalError', 2),
        ('tryLater', 3),
        ('undefinedStatus', 4),  # should never occur
        ('sigRequired', 5),
        ('unauthorized', 6)
    )


class OCSPResponse(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('responseStatus', OCSPResponseStatus()),
        namedtype.OptionalNamedType('responseBytes', ResponseBytes().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class Request(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('reqCert', CertID()),
        namedtype.OptionalNamedType('singleRequestExtensions', rfc2459.Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class Signature(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('signatureAlgorithm', rfc2459.AlgorithmIdentifier()),
        namedtype.NamedType('signature', univ.BitString()),
        namedtype.OptionalNamedType('certs', univ.SequenceOf(componentType=rfc2459.Certificate()).subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class TBSRequest(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.DefaultedNamedType('version', Version('v1').subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('requestorName', GeneralName().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('requestList', univ.SequenceOf(componentType=Request())),
        namedtype.OptionalNamedType('requestExtensions', rfc2459.Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class OCSPRequest(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('tbsRequest', TBSRequest()),
        namedtype.OptionalNamedType('optionalSignature', Signature().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )

# === NexusCore/openenv\Lib\site-packages\rich\control.py ===
import sys
import time
from typing import TYPE_CHECKING, Callable, Dict, Iterable, List, Union

if sys.version_info >= (3, 8):
    from typing import Final
else:
    from typing_extensions import Final  # pragma: no cover

from .segment import ControlCode, ControlType, Segment

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderResult

STRIP_CONTROL_CODES: Final = [
    7,  # Bell
    8,  # Backspace
    11,  # Vertical tab
    12,  # Form feed
    13,  # Carriage return
]
_CONTROL_STRIP_TRANSLATE: Final = {
    _codepoint: None for _codepoint in STRIP_CONTROL_CODES
}

CONTROL_ESCAPE: Final = {
    7: "\\a",
    8: "\\b",
    11: "\\v",
    12: "\\f",
    13: "\\r",
}

CONTROL_CODES_FORMAT: Dict[int, Callable[..., str]] = {
    ControlType.BELL: lambda: "\x07",
    ControlType.CARRIAGE_RETURN: lambda: "\r",
    ControlType.HOME: lambda: "\x1b[H",
    ControlType.CLEAR: lambda: "\x1b[2J",
    ControlType.ENABLE_ALT_SCREEN: lambda: "\x1b[?1049h",
    ControlType.DISABLE_ALT_SCREEN: lambda: "\x1b[?1049l",
    ControlType.SHOW_CURSOR: lambda: "\x1b[?25h",
    ControlType.HIDE_CURSOR: lambda: "\x1b[?25l",
    ControlType.CURSOR_UP: lambda param: f"\x1b[{param}A",
    ControlType.CURSOR_DOWN: lambda param: f"\x1b[{param}B",
    ControlType.CURSOR_FORWARD: lambda param: f"\x1b[{param}C",
    ControlType.CURSOR_BACKWARD: lambda param: f"\x1b[{param}D",
    ControlType.CURSOR_MOVE_TO_COLUMN: lambda param: f"\x1b[{param+1}G",
    ControlType.ERASE_IN_LINE: lambda param: f"\x1b[{param}K",
    ControlType.CURSOR_MOVE_TO: lambda x, y: f"\x1b[{y+1};{x+1}H",
    ControlType.SET_WINDOW_TITLE: lambda title: f"\x1b]0;{title}\x07",
}


class Control:
    """A renderable that inserts a control code (non printable but may move cursor).

    Args:
        *codes (str): Positional arguments are either a :class:`~rich.segment.ControlType` enum or a
            tuple of ControlType and an integer parameter
    """

    __slots__ = ["segment"]

    def __init__(self, *codes: Union[ControlType, ControlCode]) -> None:
        control_codes: List[ControlCode] = [
            (code,) if isinstance(code, ControlType) else code for code in codes
        ]
        _format_map = CONTROL_CODES_FORMAT
        rendered_codes = "".join(
            _format_map[code](*parameters) for code, *parameters in control_codes
        )
        self.segment = Segment(rendered_codes, None, control_codes)

    @classmethod
    def bell(cls) -> "Control":
        """Ring the 'bell'."""
        return cls(ControlType.BELL)

    @classmethod
    def home(cls) -> "Control":
        """Move cursor to 'home' position."""
        return cls(ControlType.HOME)

    @classmethod
    def move(cls, x: int = 0, y: int = 0) -> "Control":
        """Move cursor relative to current position.

        Args:
            x (int): X offset.
            y (int): Y offset.

        Returns:
            ~Control: Control object.

        """

        def get_codes() -> Iterable[ControlCode]:
            control = ControlType
            if x:
                yield (
                    control.CURSOR_FORWARD if x > 0 else control.CURSOR_BACKWARD,
                    abs(x),
                )
            if y:
                yield (
                    control.CURSOR_DOWN if y > 0 else control.CURSOR_UP,
                    abs(y),
                )

        control = cls(*get_codes())
        return control

    @classmethod
    def move_to_column(cls, x: int, y: int = 0) -> "Control":
        """Move to the given column, optionally add offset to row.

        Returns:
            x (int): absolute x (column)
            y (int): optional y offset (row)

        Returns:
            ~Control: Control object.
        """

        return (
            cls(
                (ControlType.CURSOR_MOVE_TO_COLUMN, x),
                (
                    ControlType.CURSOR_DOWN if y > 0 else ControlType.CURSOR_UP,
                    abs(y),
                ),
            )
            if y
            else cls((ControlType.CURSOR_MOVE_TO_COLUMN, x))
        )

    @classmethod
    def move_to(cls, x: int, y: int) -> "Control":
        """Move cursor to absolute position.

        Args:
            x (int): x offset (column)
            y (int): y offset (row)

        Returns:
            ~Control: Control object.
        """
        return cls((ControlType.CURSOR_MOVE_TO, x, y))

    @classmethod
    def clear(cls) -> "Control":
        """Clear the screen."""
        return cls(ControlType.CLEAR)

    @classmethod
    def show_cursor(cls, show: bool) -> "Control":
        """Show or hide the cursor."""
        return cls(ControlType.SHOW_CURSOR if show else ControlType.HIDE_CURSOR)

    @classmethod
    def alt_screen(cls, enable: bool) -> "Control":
        """Enable or disable alt screen."""
        if enable:
            return cls(ControlType.ENABLE_ALT_SCREEN, ControlType.HOME)
        else:
            return cls(ControlType.DISABLE_ALT_SCREEN)

    @classmethod
    def title(cls, title: str) -> "Control":
        """Set the terminal window title

        Args:
            title (str): The new terminal window title
        """
        return cls((ControlType.SET_WINDOW_TITLE, title))

    def __str__(self) -> str:
        return self.segment.text

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.segment.text:
            yield self.segment


def strip_control_codes(
    text: str, _translate_table: Dict[int, None] = _CONTROL_STRIP_TRANSLATE
) -> str:
    """Remove control codes from text.

    Args:
        text (str): A string possibly contain control codes.

    Returns:
        str: String with control codes removed.
    """
    return text.translate(_translate_table)


def escape_control_codes(
    text: str,
    _translate_table: Dict[int, str] = CONTROL_ESCAPE,
) -> str:
    """Replace control codes with their "escaped" equivalent in the given text.
    (e.g. "\b" becomes "\\b")

    Args:
        text (str): A string possibly containing control codes.

    Returns:
        str: String with control codes replaced with their escaped version.
    """
    return text.translate(_translate_table)


if __name__ == "__main__":  # pragma: no cover
    from rich.console import Console

    console = Console()
    console.print("Look at the title of your terminal window ^")
    # console.print(Control((ControlType.SET_WINDOW_TITLE, "Hello, world!")))
    for i in range(10):
        console.set_window_title("🚀 Loading" + "." * i)
        time.sleep(0.5)