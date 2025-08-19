
# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\locators.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#

import gzip
from io import BytesIO
import json
import logging
import os
import posixpath
import re
try:
    import threading
except ImportError:  # pragma: no cover
    import dummy_threading as threading
import zlib

from . import DistlibException
from .compat import (urljoin, urlparse, urlunparse, url2pathname, pathname2url, queue, quote, unescape, build_opener,
                     HTTPRedirectHandler as BaseRedirectHandler, text_type, Request, HTTPError, URLError)
from .database import Distribution, DistributionPath, make_dist
from .metadata import Metadata, MetadataInvalidError
from .util import (cached_property, ensure_slash, split_filename, get_project_data, parse_requirement,
                   parse_name_and_version, ServerProxy, normalize_name)
from .version import get_scheme, UnsupportedVersionError
from .wheel import Wheel, is_compatible

logger = logging.getLogger(__name__)

HASHER_HASH = re.compile(r'^(\w+)=([a-f0-9]+)')
CHARSET = re.compile(r';\s*charset\s*=\s*(.*)\s*$', re.I)
HTML_CONTENT_TYPE = re.compile('text/html|application/x(ht)?ml')
DEFAULT_INDEX = 'https://pypi.org/pypi'


def get_all_distribution_names(url=None):
    """
    Return all distribution names known by an index.
    :param url: The URL of the index.
    :return: A list of all known distribution names.
    """
    if url is None:
        url = DEFAULT_INDEX
    client = ServerProxy(url, timeout=3.0)
    try:
        return client.list_packages()
    finally:
        client('close')()


class RedirectHandler(BaseRedirectHandler):
    """
    A class to work around a bug in some Python 3.2.x releases.
    """

    # There's a bug in the base version for some 3.2.x
    # (e.g. 3.2.2 on Ubuntu Oneiric). If a Location header
    # returns e.g. /abc, it bails because it says the scheme ''
    # is bogus, when actually it should use the request's
    # URL for the scheme. See Python issue #13696.
    def http_error_302(self, req, fp, code, msg, headers):
        # Some servers (incorrectly) return multiple Location headers
        # (so probably same goes for URI).  Use first header.
        newurl = None
        for key in ('location', 'uri'):
            if key in headers:
                newurl = headers[key]
                break
        if newurl is None:  # pragma: no cover
            return
        urlparts = urlparse(newurl)
        if urlparts.scheme == '':
            newurl = urljoin(req.get_full_url(), newurl)
            if hasattr(headers, 'replace_header'):
                headers.replace_header(key, newurl)
            else:
                headers[key] = newurl
        return BaseRedirectHandler.http_error_302(self, req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_302


class Locator(object):
    """
    A base class for locators - things that locate distributions.
    """
    source_extensions = ('.tar.gz', '.tar.bz2', '.tar', '.zip', '.tgz', '.tbz')
    binary_extensions = ('.egg', '.exe', '.whl')
    excluded_extensions = ('.pdf', )

    # A list of tags indicating which wheels you want to match. The default
    # value of None matches against the tags compatible with the running
    # Python. If you want to match other values, set wheel_tags on a locator
    # instance to a list of tuples (pyver, abi, arch) which you want to match.
    wheel_tags = None

    downloadable_extensions = source_extensions + ('.whl', )

    def __init__(self, scheme='default'):
        """
        Initialise an instance.
        :param scheme: Because locators look for most recent versions, they
                       need to know the version scheme to use. This specifies
                       the current PEP-recommended scheme - use ``'legacy'``
                       if you need to support existing distributions on PyPI.
        """
        self._cache = {}
        self.scheme = scheme
        # Because of bugs in some of the handlers on some of the platforms,
        # we use our own opener rather than just using urlopen.
        self.opener = build_opener(RedirectHandler())
        # If get_project() is called from locate(), the matcher instance
        # is set from the requirement passed to locate(). See issue #18 for
        # why this can be useful to know.
        self.matcher = None
        self.errors = queue.Queue()

    def get_errors(self):
        """
        Return any errors which have occurred.
        """
        result = []
        while not self.errors.empty():  # pragma: no cover
            try:
                e = self.errors.get(False)
                result.append(e)
            except self.errors.Empty:
                continue
            self.errors.task_done()
        return result

    def clear_errors(self):
        """
        Clear any errors which may have been logged.
        """
        # Just get the errors and throw them away
        self.get_errors()

    def clear_cache(self):
        self._cache.clear()

    def _get_scheme(self):
        return self._scheme

    def _set_scheme(self, value):
        self._scheme = value

    scheme = property(_get_scheme, _set_scheme)

    def _get_project(self, name):
        """
        For a given project, get a dictionary mapping available versions to Distribution
        instances.

        This should be implemented in subclasses.

        If called from a locate() request, self.matcher will be set to a
        matcher for the requirement to satisfy, otherwise it will be None.
        """
        raise NotImplementedError('Please implement in the subclass')

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        raise NotImplementedError('Please implement in the subclass')

    def get_project(self, name):
        """
        For a given project, get a dictionary mapping available versions to Distribution
        instances.

        This calls _get_project to do all the work, and just implements a caching layer on top.
        """
        if self._cache is None:  # pragma: no cover
            result = self._get_project(name)
        elif name in self._cache:
            result = self._cache[name]
        else:
            self.clear_errors()
            result = self._get_project(name)
            self._cache[name] = result
        return result

    def score_url(self, url):
        """
        Give an url a score which can be used to choose preferred URLs
        for a given project release.
        """
        t = urlparse(url)
        basename = posixpath.basename(t.path)
        compatible = True
        is_wheel = basename.endswith('.whl')
        is_downloadable = basename.endswith(self.downloadable_extensions)
        if is_wheel:
            compatible = is_compatible(Wheel(basename), self.wheel_tags)
        return (t.scheme == 'https', 'pypi.org' in t.netloc, is_downloadable, is_wheel, compatible, basename)

    def prefer_url(self, url1, url2):
        """
        Choose one of two URLs where both are candidates for distribution
        archives for the same version of a distribution (for example,
        .tar.gz vs. zip).

        The current implementation favours https:// URLs over http://, archives
        from PyPI over those from other locations, wheel compatibility (if a
        wheel) and then the archive name.
        """
        result = url2
        if url1:
            s1 = self.score_url(url1)
            s2 = self.score_url(url2)
            if s1 > s2:
                result = url1
            if result != url2:
                logger.debug('Not replacing %r with %r', url1, url2)
            else:
                logger.debug('Replacing %r with %r', url1, url2)
        return result

    def split_filename(self, filename, project_name):
        """
        Attempt to split a filename in project name, version and Python version.
        """
        return split_filename(filename, project_name)

    def convert_url_to_download_info(self, url, project_name):
        """
        See if a URL is a candidate for a download URL for a project (the URL
        has typically been scraped from an HTML page).

        If it is, a dictionary is returned with keys "name", "version",
        "filename" and "url"; otherwise, None is returned.
        """

        def same_project(name1, name2):
            return normalize_name(name1) == normalize_name(name2)

        result = None
        scheme, netloc, path, params, query, frag = urlparse(url)
        if frag.lower().startswith('egg='):  # pragma: no cover
            logger.debug('%s: version hint in fragment: %r', project_name, frag)
        m = HASHER_HASH.match(frag)
        if m:
            algo, digest = m.groups()
        else:
            algo, digest = None, None
        origpath = path
        if path and path[-1] == '/':  # pragma: no cover
            path = path[:-1]
        if path.endswith('.whl'):
            try:
                wheel = Wheel(path)
                if not is_compatible(wheel, self.wheel_tags):
                    logger.debug('Wheel not compatible: %s', path)
                else:
                    if project_name is None:
                        include = True
                    else:
                        include = same_project(wheel.name, project_name)
                    if include:
                        result = {
                            'name': wheel.name,
                            'version': wheel.version,
                            'filename': wheel.filename,
                            'url': urlunparse((scheme, netloc, origpath, params, query, '')),
                            'python-version': ', '.join(['.'.join(list(v[2:])) for v in wheel.pyver]),
                        }
            except Exception:  # pragma: no cover
                logger.warning('invalid path for wheel: %s', path)
        elif not path.endswith(self.downloadable_extensions):  # pragma: no cover
            logger.debug('Not downloadable: %s', path)
        else:  # downloadable extension
            path = filename = posixpath.basename(path)
            for ext in self.downloadable_extensions:
                if path.endswith(ext):
                    path = path[:-len(ext)]
                    t = self.split_filename(path, project_name)
                    if not t:  # pragma: no cover
                        logger.debug('No match for project/version: %s', path)
                    else:
                        name, version, pyver = t
                        if not project_name or same_project(project_name, name):
                            result = {
                                'name': name,
                                'version': version,
                                'filename': filename,
                                'url': urlunparse((scheme, netloc, origpath, params, query, '')),
                            }
                            if pyver:  # pragma: no cover
                                result['python-version'] = pyver
                    break
        if result and algo:
            result['%s_digest' % algo] = digest
        return result

    def _get_digest(self, info):
        """
        Get a digest from a dictionary by looking at a "digests" dictionary
        or keys of the form 'algo_digest'.

        Returns a 2-tuple (algo, digest) if found, else None. Currently
        looks only for SHA256, then MD5.
        """
        result = None
        if 'digests' in info:
            digests = info['digests']
            for algo in ('sha256', 'md5'):
                if algo in digests:
                    result = (algo, digests[algo])
                    break
        if not result:
            for algo in ('sha256', 'md5'):
                key = '%s_digest' % algo
                if key in info:
                    result = (algo, info[key])
                    break
        return result

    def _update_version_data(self, result, info):
        """
        Update a result dictionary (the final result from _get_project) with a
        dictionary for a specific version, which typically holds information
        gleaned from a filename or URL for an archive for the distribution.
        """
        name = info.pop('name')
        version = info.pop('version')
        if version in result:
            dist = result[version]
            md = dist.metadata
        else:
            dist = make_dist(name, version, scheme=self.scheme)
            md = dist.metadata
        dist.digest = digest = self._get_digest(info)
        url = info['url']
        result['digests'][url] = digest
        if md.source_url != info['url']:
            md.source_url = self.prefer_url(md.source_url, url)
            result['urls'].setdefault(version, set()).add(url)
        dist.locator = self
        result[version] = dist

    def locate(self, requirement, prereleases=False):
        """
        Find the most recent distribution which matches the given
        requirement.

        :param requirement: A requirement of the form 'foo (1.0)' or perhaps
                            'foo (>= 1.0, < 2.0, != 1.3)'
        :param prereleases: If ``True``, allow pre-release versions
                            to be located. Otherwise, pre-release versions
                            are not returned.
        :return: A :class:`Distribution` instance, or ``None`` if no such
                 distribution could be located.
        """
        result = None
        r = parse_requirement(requirement)
        if r is None:  # pragma: no cover
            raise DistlibException('Not a valid requirement: %r' % requirement)
        scheme = get_scheme(self.scheme)
        self.matcher = matcher = scheme.matcher(r.requirement)
        logger.debug('matcher: %s (%s)', matcher, type(matcher).__name__)
        versions = self.get_project(r.name)
        if len(versions) > 2:  # urls and digests keys are present
            # sometimes, versions are invalid
            slist = []
            vcls = matcher.version_class
            for k in versions:
                if k in ('urls', 'digests'):
                    continue
                try:
                    if not matcher.match(k):
                        pass  # logger.debug('%s did not match %r', matcher, k)
                    else:
                        if prereleases or not vcls(k).is_prerelease:
                            slist.append(k)
                except Exception:  # pragma: no cover
                    logger.warning('error matching %s with %r', matcher, k)
                    pass  # slist.append(k)
            if len(slist) > 1:
                slist = sorted(slist, key=scheme.key)
            if slist:
                logger.debug('sorted list: %s', slist)
                version = slist[-1]
                result = versions[version]
        if result:
            if r.extras:
                result.extras = r.extras
            result.download_urls = versions.get('urls', {}).get(version, set())
            d = {}
            sd = versions.get('digests', {})
            for url in result.download_urls:
                if url in sd:  # pragma: no cover
                    d[url] = sd[url]
            result.digests = d
        self.matcher = None
        return result


class PyPIRPCLocator(Locator):
    """
    This locator uses XML-RPC to locate distributions. It therefore
    cannot be used with simple mirrors (that only mirror file content).
    """

    def __init__(self, url, **kwargs):
        """
        Initialise an instance.

        :param url: The URL to use for XML-RPC.
        :param kwargs: Passed to the superclass constructor.
        """
        super(PyPIRPCLocator, self).__init__(**kwargs)
        self.base_url = url
        self.client = ServerProxy(url, timeout=3.0)

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        return set(self.client.list_packages())

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        versions = self.client.package_releases(name, True)
        for v in versions:
            urls = self.client.release_urls(name, v)
            data = self.client.release_data(name, v)
            metadata = Metadata(scheme=self.scheme)
            metadata.name = data['name']
            metadata.version = data['version']
            metadata.license = data.get('license')
            metadata.keywords = data.get('keywords', [])
            metadata.summary = data.get('summary')
            dist = Distribution(metadata)
            if urls:
                info = urls[0]
                metadata.source_url = info['url']
                dist.digest = self._get_digest(info)
                dist.locator = self
                result[v] = dist
                for info in urls:
                    url = info['url']
                    digest = self._get_digest(info)
                    result['urls'].setdefault(v, set()).add(url)
                    result['digests'][url] = digest
        return result


class PyPIJSONLocator(Locator):
    """
    This locator uses PyPI's JSON interface. It's very limited in functionality
    and probably not worth using.
    """

    def __init__(self, url, **kwargs):
        super(PyPIJSONLocator, self).__init__(**kwargs)
        self.base_url = ensure_slash(url)

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        raise NotImplementedError('Not available from this locator')

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        url = urljoin(self.base_url, '%s/json' % quote(name))
        try:
            resp = self.opener.open(url)
            data = resp.read().decode()  # for now
            d = json.loads(data)
            md = Metadata(scheme=self.scheme)
            data = d['info']
            md.name = data['name']
            md.version = data['version']
            md.license = data.get('license')
            md.keywords = data.get('keywords', [])
            md.summary = data.get('summary')
            dist = Distribution(md)
            dist.locator = self
            # urls = d['urls']
            result[md.version] = dist
            for info in d['urls']:
                url = info['url']
                dist.download_urls.add(url)
                dist.digests[url] = self._get_digest(info)
                result['urls'].setdefault(md.version, set()).add(url)
                result['digests'][url] = self._get_digest(info)
            # Now get other releases
            for version, infos in d['releases'].items():
                if version == md.version:
                    continue  # already done
                omd = Metadata(scheme=self.scheme)
                omd.name = md.name
                omd.version = version
                odist = Distribution(omd)
                odist.locator = self
                result[version] = odist
                for info in infos:
                    url = info['url']
                    odist.download_urls.add(url)
                    odist.digests[url] = self._get_digest(info)
                    result['urls'].setdefault(version, set()).add(url)
                    result['digests'][url] = self._get_digest(info)


#            for info in urls:
#                md.source_url = info['url']
#                dist.digest = self._get_digest(info)
#                dist.locator = self
#                for info in urls:
#                    url = info['url']
#                    result['urls'].setdefault(md.version, set()).add(url)
#                    result['digests'][url] = self._get_digest(info)
        except Exception as e:
            self.errors.put(text_type(e))
            logger.exception('JSON fetch failed: %s', e)
        return result


class Page(object):
    """
    This class represents a scraped HTML page.
    """
    # The following slightly hairy-looking regex just looks for the contents of
    # an anchor link, which has an attribute "href" either immediately preceded
    # or immediately followed by a "rel" attribute. The attribute values can be
    # declared with double quotes, single quotes or no quotes - which leads to
    # the length of the expression.
    _href = re.compile(
        """
(rel\\s*=\\s*(?:"(?P<rel1>[^"]*)"|'(?P<rel2>[^']*)'|(?P<rel3>[^>\\s\n]*))\\s+)?
href\\s*=\\s*(?:"(?P<url1>[^"]*)"|'(?P<url2>[^']*)'|(?P<url3>[^>\\s\n]*))
(\\s+rel\\s*=\\s*(?:"(?P<rel4>[^"]*)"|'(?P<rel5>[^']*)'|(?P<rel6>[^>\\s\n]*)))?
""", re.I | re.S | re.X)
    _base = re.compile(r"""<base\s+href\s*=\s*['"]?([^'">]+)""", re.I | re.S)

    def __init__(self, data, url):
        """
        Initialise an instance with the Unicode page contents and the URL they
        came from.
        """
        self.data = data
        self.base_url = self.url = url
        m = self._base.search(self.data)
        if m:
            self.base_url = m.group(1)

    _clean_re = re.compile(r'[^a-z0-9$&+,/:;=?@.#%_\\|-]', re.I)

    @cached_property
    def links(self):
        """
        Return the URLs of all the links on a page together with information
        about their "rel" attribute, for determining which ones to treat as
        downloads and which ones to queue for further scraping.
        """

        def clean(url):
            "Tidy up an URL."
            scheme, netloc, path, params, query, frag = urlparse(url)
            return urlunparse((scheme, netloc, quote(path), params, query, frag))

        result = set()
        for match in self._href.finditer(self.data):
            d = match.groupdict('')
            rel = (d['rel1'] or d['rel2'] or d['rel3'] or d['rel4'] or d['rel5'] or d['rel6'])
            url = d['url1'] or d['url2'] or d['url3']
            url = urljoin(self.base_url, url)
            url = unescape(url)
            url = self._clean_re.sub(lambda m: '%%%2x' % ord(m.group(0)), url)
            result.add((url, rel))
        # We sort the result, hoping to bring the most recent versions
        # to the front
        result = sorted(result, key=lambda t: t[0], reverse=True)
        return result


class SimpleScrapingLocator(Locator):
    """
    A locator which scrapes HTML pages to locate downloads for a distribution.
    This runs multiple threads to do the I/O; performance is at least as good
    as pip's PackageFinder, which works in an analogous fashion.
    """

    # These are used to deal with various Content-Encoding schemes.
    decoders = {
        'deflate': zlib.decompress,
        'gzip': lambda b: gzip.GzipFile(fileobj=BytesIO(b)).read(),
        'none': lambda b: b,
    }

    def __init__(self, url, timeout=None, num_workers=10, **kwargs):
        """
        Initialise an instance.
        :param url: The root URL to use for scraping.
        :param timeout: The timeout, in seconds, to be applied to requests.
                        This defaults to ``None`` (no timeout specified).
        :param num_workers: The number of worker threads you want to do I/O,
                            This defaults to 10.
        :param kwargs: Passed to the superclass.
        """
        super(SimpleScrapingLocator, self).__init__(**kwargs)
        self.base_url = ensure_slash(url)
        self.timeout = timeout
        self._page_cache = {}
        self._seen = set()
        self._to_fetch = queue.Queue()
        self._bad_hosts = set()
        self.skip_externals = False
        self.num_workers = num_workers
        self._lock = threading.RLock()
        # See issue #45: we need to be resilient when the locator is used
        # in a thread, e.g. with concurrent.futures. We can't use self._lock
        # as it is for coordinating our internal threads - the ones created
        # in _prepare_threads.
        self._gplock = threading.RLock()
        self.platform_check = False  # See issue #112

    def _prepare_threads(self):
        """
        Threads are created only when get_project is called, and terminate
        before it returns. They are there primarily to parallelise I/O (i.e.
        fetching web pages).
        """
        self._threads = []
        for i in range(self.num_workers):
            t = threading.Thread(target=self._fetch)
            t.daemon = True
            t.start()
            self._threads.append(t)

    def _wait_threads(self):
        """
        Tell all the threads to terminate (by sending a sentinel value) and
        wait for them to do so.
        """
        # Note that you need two loops, since you can't say which
        # thread will get each sentinel
        for t in self._threads:
            self._to_fetch.put(None)  # sentinel
        for t in self._threads:
            t.join()
        self._threads = []

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        with self._gplock:
            self.result = result
            self.project_name = name
            url = urljoin(self.base_url, '%s/' % quote(name))
            self._seen.clear()
            self._page_cache.clear()
            self._prepare_threads()
            try:
                logger.debug('Queueing %s', url)
                self._to_fetch.put(url)
                self._to_fetch.join()
            finally:
                self._wait_threads()
            del self.result
        return result

    platform_dependent = re.compile(r'\b(linux_(i\d86|x86_64|arm\w+)|'
                                    r'win(32|_amd64)|macosx_?\d+)\b', re.I)

    def _is_platform_dependent(self, url):
        """
        Does an URL refer to a platform-specific download?
        """
        return self.platform_dependent.search(url)

    def _process_download(self, url):
        """
        See if an URL is a suitable download for a project.

        If it is, register information in the result dictionary (for
        _get_project) about the specific version it's for.

        Note that the return value isn't actually used other than as a boolean
        value.
        """
        if self.platform_check and self._is_platform_dependent(url):
            info = None
        else:
            info = self.convert_url_to_download_info(url, self.project_name)
        logger.debug('process_download: %s -> %s', url, info)
        if info:
            with self._lock:  # needed because self.result is shared
                self._update_version_data(self.result, info)
        return info

    def _should_queue(self, link, referrer, rel):
        """
        Determine whether a link URL from a referring page and with a
        particular "rel" attribute should be queued for scraping.
        """
        scheme, netloc, path, _, _, _ = urlparse(link)
        if path.endswith(self.source_extensions + self.binary_extensions + self.excluded_extensions):
            result = False
        elif self.skip_externals and not link.startswith(self.base_url):
            result = False
        elif not referrer.startswith(self.base_url):
            result = False
        elif rel not in ('homepage', 'download'):
            result = False
        elif scheme not in ('http', 'https', 'ftp'):
            result = False
        elif self._is_platform_dependent(link):
            result = False
        else:
            host = netloc.split(':', 1)[0]
            if host.lower() == 'localhost':
                result = False
            else:
                result = True
        logger.debug('should_queue: %s (%s) from %s -> %s', link, rel, referrer, result)
        return result

    def _fetch(self):
        """
        Get a URL to fetch from the work queue, get the HTML page, examine its
        links for download candidates and candidates for further scraping.

        This is a handy method to run in a thread.
        """
        while True:
            url = self._to_fetch.get()
            try:
                if url:
                    page = self.get_page(url)
                    if page is None:  # e.g. after an error
                        continue
                    for link, rel in page.links:
                        if link not in self._seen:
                            try:
                                self._seen.add(link)
                                if (not self._process_download(link) and self._should_queue(link, url, rel)):
                                    logger.debug('Queueing %s from %s', link, url)
                                    self._to_fetch.put(link)
                            except MetadataInvalidError:  # e.g. invalid versions
                                pass
            except Exception as e:  # pragma: no cover
                self.errors.put(text_type(e))
            finally:
                # always do this, to avoid hangs :-)
                self._to_fetch.task_done()
            if not url:
                # logger.debug('Sentinel seen, quitting.')
                break

    def get_page(self, url):
        """
        Get the HTML for an URL, possibly from an in-memory cache.

        XXX TODO Note: this cache is never actually cleared. It's assumed that
        the data won't get stale over the lifetime of a locator instance (not
        necessarily true for the default_locator).
        """
        # http://peak.telecommunity.com/DevCenter/EasyInstall#package-index-api
        scheme, netloc, path, _, _, _ = urlparse(url)
        if scheme == 'file' and os.path.isdir(url2pathname(path)):
            url = urljoin(ensure_slash(url), 'index.html')

        if url in self._page_cache:
            result = self._page_cache[url]
            logger.debug('Returning %s from cache: %s', url, result)
        else:
            host = netloc.split(':', 1)[0]
            result = None
            if host in self._bad_hosts:
                logger.debug('Skipping %s due to bad host %s', url, host)
            else:
                req = Request(url, headers={'Accept-encoding': 'identity'})
                try:
                    logger.debug('Fetching %s', url)
                    resp = self.opener.open(req, timeout=self.timeout)
                    logger.debug('Fetched %s', url)
                    headers = resp.info()
                    content_type = headers.get('Content-Type', '')
                    if HTML_CONTENT_TYPE.match(content_type):
                        final_url = resp.geturl()
                        data = resp.read()
                        encoding = headers.get('Content-Encoding')
                        if encoding:
                            decoder = self.decoders[encoding]  # fail if not found
                            data = decoder(data)
                        encoding = 'utf-8'
                        m = CHARSET.search(content_type)
                        if m:
                            encoding = m.group(1)
                        try:
                            data = data.decode(encoding)
                        except UnicodeError:  # pragma: no cover
                            data = data.decode('latin-1')  # fallback
                        result = Page(data, final_url)
                        self._page_cache[final_url] = result
                except HTTPError as e:
                    if e.code != 404:
                        logger.exception('Fetch failed: %s: %s', url, e)
                except URLError as e:  # pragma: no cover
                    logger.exception('Fetch failed: %s: %s', url, e)
                    with self._lock:
                        self._bad_hosts.add(host)
                except Exception as e:  # pragma: no cover
                    logger.exception('Fetch failed: %s: %s', url, e)
                finally:
                    self._page_cache[url] = result  # even if None (failure)
        return result

    _distname_re = re.compile('<a href=[^>]*>([^<]+)<')

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        result = set()
        page = self.get_page(self.base_url)
        if not page:
            raise DistlibException('Unable to get %s' % self.base_url)
        for match in self._distname_re.finditer(page.data):
            result.add(match.group(1))
        return result


class DirectoryLocator(Locator):
    """
    This class locates distributions in a directory tree.
    """

    def __init__(self, path, **kwargs):
        """
        Initialise an instance.
        :param path: The root of the directory tree to search.
        :param kwargs: Passed to the superclass constructor,
                       except for:
                       * recursive - if True (the default), subdirectories are
                         recursed into. If False, only the top-level directory
                         is searched,
        """
        self.recursive = kwargs.pop('recursive', True)
        super(DirectoryLocator, self).__init__(**kwargs)
        path = os.path.abspath(path)
        if not os.path.isdir(path):  # pragma: no cover
            raise DistlibException('Not a directory: %r' % path)
        self.base_dir = path

    def should_include(self, filename, parent):
        """
        Should a filename be considered as a candidate for a distribution
        archive? As well as the filename, the directory which contains it
        is provided, though not used by the current implementation.
        """
        return filename.endswith(self.downloadable_extensions)

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        for root, dirs, files in os.walk(self.base_dir):
            for fn in files:
                if self.should_include(fn, root):
                    fn = os.path.join(root, fn)
                    url = urlunparse(('file', '', pathname2url(os.path.abspath(fn)), '', '', ''))
                    info = self.convert_url_to_download_info(url, name)
                    if info:
                        self._update_version_data(result, info)
            if not self.recursive:
                break
        return result

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        result = set()
        for root, dirs, files in os.walk(self.base_dir):
            for fn in files:
                if self.should_include(fn, root):
                    fn = os.path.join(root, fn)
                    url = urlunparse(('file', '', pathname2url(os.path.abspath(fn)), '', '', ''))
                    info = self.convert_url_to_download_info(url, None)
                    if info:
                        result.add(info['name'])
            if not self.recursive:
                break
        return result


class JSONLocator(Locator):
    """
    This locator uses special extended metadata (not available on PyPI) and is
    the basis of performant dependency resolution in distlib. Other locators
    require archive downloads before dependencies can be determined! As you
    might imagine, that can be slow.
    """

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        raise NotImplementedError('Not available from this locator')

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        data = get_project_data(name)
        if data:
            for info in data.get('files', []):
                if info['ptype'] != 'sdist' or info['pyversion'] != 'source':
                    continue
                # We don't store summary in project metadata as it makes
                # the data bigger for no benefit during dependency
                # resolution
                dist = make_dist(data['name'],
                                 info['version'],
                                 summary=data.get('summary', 'Placeholder for summary'),
                                 scheme=self.scheme)
                md = dist.metadata
                md.source_url = info['url']
                # TODO SHA256 digest
                if 'digest' in info and info['digest']:
                    dist.digest = ('md5', info['digest'])
                md.dependencies = info.get('requirements', {})
                dist.exports = info.get('exports', {})
                result[dist.version] = dist
                result['urls'].setdefault(dist.version, set()).add(info['url'])
        return result


class DistPathLocator(Locator):
    """
    This locator finds installed distributions in a path. It can be useful for
    adding to an :class:`AggregatingLocator`.
    """

    def __init__(self, distpath, **kwargs):
        """
        Initialise an instance.

        :param distpath: A :class:`DistributionPath` instance to search.
        """
        super(DistPathLocator, self).__init__(**kwargs)
        assert isinstance(distpath, DistributionPath)
        self.distpath = distpath

    def _get_project(self, name):
        dist = self.distpath.get_distribution(name)
        if dist is None:
            result = {'urls': {}, 'digests': {}}
        else:
            result = {
                dist.version: dist,
                'urls': {
                    dist.version: set([dist.source_url])
                },
                'digests': {
                    dist.version: set([None])
                }
            }
        return result


class AggregatingLocator(Locator):
    """
    This class allows you to chain and/or merge a list of locators.
    """

    def __init__(self, *locators, **kwargs):
        """
        Initialise an instance.

        :param locators: The list of locators to search.
        :param kwargs: Passed to the superclass constructor,
                       except for:
                       * merge - if False (the default), the first successful
                         search from any of the locators is returned. If True,
                         the results from all locators are merged (this can be
                         slow).
        """
        self.merge = kwargs.pop('merge', False)
        self.locators = locators
        super(AggregatingLocator, self).__init__(**kwargs)

    def clear_cache(self):
        super(AggregatingLocator, self).clear_cache()
        for locator in self.locators:
            locator.clear_cache()

    def _set_scheme(self, value):
        self._scheme = value
        for locator in self.locators:
            locator.scheme = value

    scheme = property(Locator.scheme.fget, _set_scheme)

    def _get_project(self, name):
        result = {}
        for locator in self.locators:
            d = locator.get_project(name)
            if d:
                if self.merge:
                    files = result.get('urls', {})
                    digests = result.get('digests', {})
                    # next line could overwrite result['urls'], result['digests']
                    result.update(d)
                    df = result.get('urls')
                    if files and df:
                        for k, v in files.items():
                            if k in df:
                                df[k] |= v
                            else:
                                df[k] = v
                    dd = result.get('digests')
                    if digests and dd:
                        dd.update(digests)
                else:
                    # See issue #18. If any dists are found and we're looking
                    # for specific constraints, we only return something if
                    # a match is found. For example, if a DirectoryLocator
                    # returns just foo (1.0) while we're looking for
                    # foo (>= 2.0), we'll pretend there was nothing there so
                    # that subsequent locators can be queried. Otherwise we
                    # would just return foo (1.0) which would then lead to a
                    # failure to find foo (>= 2.0), because other locators
                    # weren't searched. Note that this only matters when
                    # merge=False.
                    if self.matcher is None:
                        found = True
                    else:
                        found = False
                        for k in d:
                            if self.matcher.match(k):
                                found = True
                                break
                    if found:
                        result = d
                        break
        return result

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        result = set()
        for locator in self.locators:
            try:
                result |= locator.get_distribution_names()
            except NotImplementedError:
                pass
        return result


# We use a legacy scheme simply because most of the dists on PyPI use legacy
# versions which don't conform to PEP 440.
default_locator = AggregatingLocator(
    # JSONLocator(), # don't use as PEP 426 is withdrawn
    SimpleScrapingLocator('https://pypi.org/simple/', timeout=3.0),
    scheme='legacy')

locate = default_locator.locate


class DependencyFinder(object):
    """
    Locate dependencies for distributions.
    """

    def __init__(self, locator=None):
        """
        Initialise an instance, using the specified locator
        to locate distributions.
        """
        self.locator = locator or default_locator
        self.scheme = get_scheme(self.locator.scheme)

    def add_distribution(self, dist):
        """
        Add a distribution to the finder. This will update internal information
        about who provides what.
        :param dist: The distribution to add.
        """
        logger.debug('adding distribution %s', dist)
        name = dist.key
        self.dists_by_name[name] = dist
        self.dists[(name, dist.version)] = dist
        for p in dist.provides:
            name, version = parse_name_and_version(p)
            logger.debug('Add to provided: %s, %s, %s', name, version, dist)
            self.provided.setdefault(name, set()).add((version, dist))

    def remove_distribution(self, dist):
        """
        Remove a distribution from the finder. This will update internal
        information about who provides what.
        :param dist: The distribution to remove.
        """
        logger.debug('removing distribution %s', dist)
        name = dist.key
        del self.dists_by_name[name]
        del self.dists[(name, dist.version)]
        for p in dist.provides:
            name, version = parse_name_and_version(p)
            logger.debug('Remove from provided: %s, %s, %s', name, version, dist)
            s = self.provided[name]
            s.remove((version, dist))
            if not s:
                del self.provided[name]

    def get_matcher(self, reqt):
        """
        Get a version matcher for a requirement.
        :param reqt: The requirement
        :type reqt: str
        :return: A version matcher (an instance of
                 :class:`distlib.version.Matcher`).
        """
        try:
            matcher = self.scheme.matcher(reqt)
        except UnsupportedVersionError:  # pragma: no cover
            # XXX compat-mode if cannot read the version
            name = reqt.split()[0]
            matcher = self.scheme.matcher(name)
        return matcher

    def find_providers(self, reqt):
        """
        Find the distributions which can fulfill a requirement.

        :param reqt: The requirement.
         :type reqt: str
        :return: A set of distribution which can fulfill the requirement.
        """
        matcher = self.get_matcher(reqt)
        name = matcher.key  # case-insensitive
        result = set()
        provided = self.provided
        if name in provided:
            for version, provider in provided[name]:
                try:
                    match = matcher.match(version)
                except UnsupportedVersionError:
                    match = False

                if match:
                    result.add(provider)
                    break
        return result

    def try_to_replace(self, provider, other, problems):
        """
        Attempt to replace one provider with another. This is typically used
        when resolving dependencies from multiple sources, e.g. A requires
        (B >= 1.0) while C requires (B >= 1.1).

        For successful replacement, ``provider`` must meet all the requirements
        which ``other`` fulfills.

        :param provider: The provider we are trying to replace with.
        :param other: The provider we're trying to replace.
        :param problems: If False is returned, this will contain what
                         problems prevented replacement. This is currently
                         a tuple of the literal string 'cantreplace',
                         ``provider``, ``other``  and the set of requirements
                         that ``provider`` couldn't fulfill.
        :return: True if we can replace ``other`` with ``provider``, else
                 False.
        """
        rlist = self.reqts[other]
        unmatched = set()
        for s in rlist:
            matcher = self.get_matcher(s)
            if not matcher.match(provider.version):
                unmatched.add(s)
        if unmatched:
            # can't replace other with provider
            problems.add(('cantreplace', provider, other, frozenset(unmatched)))
            result = False
        else:
            # can replace other with provider
            self.remove_distribution(other)
            del self.reqts[other]
            for s in rlist:
                self.reqts.setdefault(provider, set()).add(s)
            self.add_distribution(provider)
            result = True
        return result

    def find(self, requirement, meta_extras=None, prereleases=False):
        """
        Find a distribution and all distributions it depends on.

        :param requirement: The requirement specifying the distribution to
                            find, or a Distribution instance.
        :param meta_extras: A list of meta extras such as :test:, :build: and
                            so on.
        :param prereleases: If ``True``, allow pre-release versions to be
                            returned - otherwise, don't return prereleases
                            unless they're all that's available.

        Return a set of :class:`Distribution` instances and a set of
        problems.

        The distributions returned should be such that they have the
        :attr:`required` attribute set to ``True`` if they were
        from the ``requirement`` passed to ``find()``, and they have the
        :attr:`build_time_dependency` attribute set to ``True`` unless they
        are post-installation dependencies of the ``requirement``.

        The problems should be a tuple consisting of the string
        ``'unsatisfied'`` and the requirement which couldn't be satisfied
        by any distribution known to the locator.
        """

        self.provided = {}
        self.dists = {}
        self.dists_by_name = {}
        self.reqts = {}

        meta_extras = set(meta_extras or [])
        if ':*:' in meta_extras:
            meta_extras.remove(':*:')
            # :meta: and :run: are implicitly included
            meta_extras |= set([':test:', ':build:', ':dev:'])

        if isinstance(requirement, Distribution):
            dist = odist = requirement
            logger.debug('passed %s as requirement', odist)
        else:
            dist = odist = self.locator.locate(requirement, prereleases=prereleases)
            if dist is None:
                raise DistlibException('Unable to locate %r' % requirement)
            logger.debug('located %s', odist)
        dist.requested = True
        problems = set()
        todo = set([dist])
        install_dists = set([odist])
        while todo:
            dist = todo.pop()
            name = dist.key  # case-insensitive
            if name not in self.dists_by_name:
                self.add_distribution(dist)
            else:
                # import pdb; pdb.set_trace()
                other = self.dists_by_name[name]
                if other != dist:
                    self.try_to_replace(dist, other, problems)

            ireqts = dist.run_requires | dist.meta_requires
            sreqts = dist.build_requires
            ereqts = set()
            if meta_extras and dist in install_dists:
                for key in ('test', 'build', 'dev'):
                    e = ':%s:' % key
                    if e in meta_extras:
                        ereqts |= getattr(dist, '%s_requires' % key)
            all_reqts = ireqts | sreqts | ereqts
            for r in all_reqts:
                providers = self.find_providers(r)
                if not providers:
                    logger.debug('No providers found for %r', r)
                    provider = self.locator.locate(r, prereleases=prereleases)
                    # If no provider is found and we didn't consider
                    # prereleases, consider them now.
                    if provider is None and not prereleases:
                        provider = self.locator.locate(r, prereleases=True)
                    if provider is None:
                        logger.debug('Cannot satisfy %r', r)
                        problems.add(('unsatisfied', r))
                    else:
                        n, v = provider.key, provider.version
                        if (n, v) not in self.dists:
                            todo.add(provider)
                        providers.add(provider)
                        if r in ireqts and dist in install_dists:
                            install_dists.add(provider)
                            logger.debug('Adding %s to install_dists', provider.name_and_version)
                for p in providers:
                    name = p.key
                    if name not in self.dists_by_name:
                        self.reqts.setdefault(p, set()).add(r)
                    else:
                        other = self.dists_by_name[name]
                        if other != p:
                            # see if other can be replaced by p
                            self.try_to_replace(p, other, problems)

        dists = set(self.dists.values())
        for dist in dists:
            dist.build_time_dependency = dist not in install_dists
            if dist.build_time_dependency:
                logger.debug('%s is a build-time dependency only.', dist.name_and_version)
        logger.debug('find done for %s', odist)
        return dists, problems

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\locators.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#

import gzip
from io import BytesIO
import json
import logging
import os
import posixpath
import re
try:
    import threading
except ImportError:  # pragma: no cover
    import dummy_threading as threading
import zlib

from . import DistlibException
from .compat import (urljoin, urlparse, urlunparse, url2pathname, pathname2url, queue, quote, unescape, build_opener,
                     HTTPRedirectHandler as BaseRedirectHandler, text_type, Request, HTTPError, URLError)
from .database import Distribution, DistributionPath, make_dist
from .metadata import Metadata, MetadataInvalidError
from .util import (cached_property, ensure_slash, split_filename, get_project_data, parse_requirement,
                   parse_name_and_version, ServerProxy, normalize_name)
from .version import get_scheme, UnsupportedVersionError
from .wheel import Wheel, is_compatible

logger = logging.getLogger(__name__)

HASHER_HASH = re.compile(r'^(\w+)=([a-f0-9]+)')
CHARSET = re.compile(r';\s*charset\s*=\s*(.*)\s*$', re.I)
HTML_CONTENT_TYPE = re.compile('text/html|application/x(ht)?ml')
DEFAULT_INDEX = 'https://pypi.org/pypi'


def get_all_distribution_names(url=None):
    """
    Return all distribution names known by an index.
    :param url: The URL of the index.
    :return: A list of all known distribution names.
    """
    if url is None:
        url = DEFAULT_INDEX
    client = ServerProxy(url, timeout=3.0)
    try:
        return client.list_packages()
    finally:
        client('close')()


class RedirectHandler(BaseRedirectHandler):
    """
    A class to work around a bug in some Python 3.2.x releases.
    """

    # There's a bug in the base version for some 3.2.x
    # (e.g. 3.2.2 on Ubuntu Oneiric). If a Location header
    # returns e.g. /abc, it bails because it says the scheme ''
    # is bogus, when actually it should use the request's
    # URL for the scheme. See Python issue #13696.
    def http_error_302(self, req, fp, code, msg, headers):
        # Some servers (incorrectly) return multiple Location headers
        # (so probably same goes for URI).  Use first header.
        newurl = None
        for key in ('location', 'uri'):
            if key in headers:
                newurl = headers[key]
                break
        if newurl is None:  # pragma: no cover
            return
        urlparts = urlparse(newurl)
        if urlparts.scheme == '':
            newurl = urljoin(req.get_full_url(), newurl)
            if hasattr(headers, 'replace_header'):
                headers.replace_header(key, newurl)
            else:
                headers[key] = newurl
        return BaseRedirectHandler.http_error_302(self, req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_302


class Locator(object):
    """
    A base class for locators - things that locate distributions.
    """
    source_extensions = ('.tar.gz', '.tar.bz2', '.tar', '.zip', '.tgz', '.tbz')
    binary_extensions = ('.egg', '.exe', '.whl')
    excluded_extensions = ('.pdf', )

    # A list of tags indicating which wheels you want to match. The default
    # value of None matches against the tags compatible with the running
    # Python. If you want to match other values, set wheel_tags on a locator
    # instance to a list of tuples (pyver, abi, arch) which you want to match.
    wheel_tags = None

    downloadable_extensions = source_extensions + ('.whl', )

    def __init__(self, scheme='default'):
        """
        Initialise an instance.
        :param scheme: Because locators look for most recent versions, they
                       need to know the version scheme to use. This specifies
                       the current PEP-recommended scheme - use ``'legacy'``
                       if you need to support existing distributions on PyPI.
        """
        self._cache = {}
        self.scheme = scheme
        # Because of bugs in some of the handlers on some of the platforms,
        # we use our own opener rather than just using urlopen.
        self.opener = build_opener(RedirectHandler())
        # If get_project() is called from locate(), the matcher instance
        # is set from the requirement passed to locate(). See issue #18 for
        # why this can be useful to know.
        self.matcher = None
        self.errors = queue.Queue()

    def get_errors(self):
        """
        Return any errors which have occurred.
        """
        result = []
        while not self.errors.empty():  # pragma: no cover
            try:
                e = self.errors.get(False)
                result.append(e)
            except self.errors.Empty:
                continue
            self.errors.task_done()
        return result

    def clear_errors(self):
        """
        Clear any errors which may have been logged.
        """
        # Just get the errors and throw them away
        self.get_errors()

    def clear_cache(self):
        self._cache.clear()

    def _get_scheme(self):
        return self._scheme

    def _set_scheme(self, value):
        self._scheme = value

    scheme = property(_get_scheme, _set_scheme)

    def _get_project(self, name):
        """
        For a given project, get a dictionary mapping available versions to Distribution
        instances.

        This should be implemented in subclasses.

        If called from a locate() request, self.matcher will be set to a
        matcher for the requirement to satisfy, otherwise it will be None.
        """
        raise NotImplementedError('Please implement in the subclass')

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        raise NotImplementedError('Please implement in the subclass')

    def get_project(self, name):
        """
        For a given project, get a dictionary mapping available versions to Distribution
        instances.

        This calls _get_project to do all the work, and just implements a caching layer on top.
        """
        if self._cache is None:  # pragma: no cover
            result = self._get_project(name)
        elif name in self._cache:
            result = self._cache[name]
        else:
            self.clear_errors()
            result = self._get_project(name)
            self._cache[name] = result
        return result

    def score_url(self, url):
        """
        Give an url a score which can be used to choose preferred URLs
        for a given project release.
        """
        t = urlparse(url)
        basename = posixpath.basename(t.path)
        compatible = True
        is_wheel = basename.endswith('.whl')
        is_downloadable = basename.endswith(self.downloadable_extensions)
        if is_wheel:
            compatible = is_compatible(Wheel(basename), self.wheel_tags)
        return (t.scheme == 'https', 'pypi.org' in t.netloc, is_downloadable, is_wheel, compatible, basename)

    def prefer_url(self, url1, url2):
        """
        Choose one of two URLs where both are candidates for distribution
        archives for the same version of a distribution (for example,
        .tar.gz vs. zip).

        The current implementation favours https:// URLs over http://, archives
        from PyPI over those from other locations, wheel compatibility (if a
        wheel) and then the archive name.
        """
        result = url2
        if url1:
            s1 = self.score_url(url1)
            s2 = self.score_url(url2)
            if s1 > s2:
                result = url1
            if result != url2:
                logger.debug('Not replacing %r with %r', url1, url2)
            else:
                logger.debug('Replacing %r with %r', url1, url2)
        return result

    def split_filename(self, filename, project_name):
        """
        Attempt to split a filename in project name, version and Python version.
        """
        return split_filename(filename, project_name)

    def convert_url_to_download_info(self, url, project_name):
        """
        See if a URL is a candidate for a download URL for a project (the URL
        has typically been scraped from an HTML page).

        If it is, a dictionary is returned with keys "name", "version",
        "filename" and "url"; otherwise, None is returned.
        """

        def same_project(name1, name2):
            return normalize_name(name1) == normalize_name(name2)

        result = None
        scheme, netloc, path, params, query, frag = urlparse(url)
        if frag.lower().startswith('egg='):  # pragma: no cover
            logger.debug('%s: version hint in fragment: %r', project_name, frag)
        m = HASHER_HASH.match(frag)
        if m:
            algo, digest = m.groups()
        else:
            algo, digest = None, None
        origpath = path
        if path and path[-1] == '/':  # pragma: no cover
            path = path[:-1]
        if path.endswith('.whl'):
            try:
                wheel = Wheel(path)
                if not is_compatible(wheel, self.wheel_tags):
                    logger.debug('Wheel not compatible: %s', path)
                else:
                    if project_name is None:
                        include = True
                    else:
                        include = same_project(wheel.name, project_name)
                    if include:
                        result = {
                            'name': wheel.name,
                            'version': wheel.version,
                            'filename': wheel.filename,
                            'url': urlunparse((scheme, netloc, origpath, params, query, '')),
                            'python-version': ', '.join(['.'.join(list(v[2:])) for v in wheel.pyver]),
                        }
            except Exception:  # pragma: no cover
                logger.warning('invalid path for wheel: %s', path)
        elif not path.endswith(self.downloadable_extensions):  # pragma: no cover
            logger.debug('Not downloadable: %s', path)
        else:  # downloadable extension
            path = filename = posixpath.basename(path)
            for ext in self.downloadable_extensions:
                if path.endswith(ext):
                    path = path[:-len(ext)]
                    t = self.split_filename(path, project_name)
                    if not t:  # pragma: no cover
                        logger.debug('No match for project/version: %s', path)
                    else:
                        name, version, pyver = t
                        if not project_name or same_project(project_name, name):
                            result = {
                                'name': name,
                                'version': version,
                                'filename': filename,
                                'url': urlunparse((scheme, netloc, origpath, params, query, '')),
                            }
                            if pyver:  # pragma: no cover
                                result['python-version'] = pyver
                    break
        if result and algo:
            result['%s_digest' % algo] = digest
        return result

    def _get_digest(self, info):
        """
        Get a digest from a dictionary by looking at a "digests" dictionary
        or keys of the form 'algo_digest'.

        Returns a 2-tuple (algo, digest) if found, else None. Currently
        looks only for SHA256, then MD5.
        """
        result = None
        if 'digests' in info:
            digests = info['digests']
            for algo in ('sha256', 'md5'):
                if algo in digests:
                    result = (algo, digests[algo])
                    break
        if not result:
            for algo in ('sha256', 'md5'):
                key = '%s_digest' % algo
                if key in info:
                    result = (algo, info[key])
                    break
        return result

    def _update_version_data(self, result, info):
        """
        Update a result dictionary (the final result from _get_project) with a
        dictionary for a specific version, which typically holds information
        gleaned from a filename or URL for an archive for the distribution.
        """
        name = info.pop('name')
        version = info.pop('version')
        if version in result:
            dist = result[version]
            md = dist.metadata
        else:
            dist = make_dist(name, version, scheme=self.scheme)
            md = dist.metadata
        dist.digest = digest = self._get_digest(info)
        url = info['url']
        result['digests'][url] = digest
        if md.source_url != info['url']:
            md.source_url = self.prefer_url(md.source_url, url)
            result['urls'].setdefault(version, set()).add(url)
        dist.locator = self
        result[version] = dist

    def locate(self, requirement, prereleases=False):
        """
        Find the most recent distribution which matches the given
        requirement.

        :param requirement: A requirement of the form 'foo (1.0)' or perhaps
                            'foo (>= 1.0, < 2.0, != 1.3)'
        :param prereleases: If ``True``, allow pre-release versions
                            to be located. Otherwise, pre-release versions
                            are not returned.
        :return: A :class:`Distribution` instance, or ``None`` if no such
                 distribution could be located.
        """
        result = None
        r = parse_requirement(requirement)
        if r is None:  # pragma: no cover
            raise DistlibException('Not a valid requirement: %r' % requirement)
        scheme = get_scheme(self.scheme)
        self.matcher = matcher = scheme.matcher(r.requirement)
        logger.debug('matcher: %s (%s)', matcher, type(matcher).__name__)
        versions = self.get_project(r.name)
        if len(versions) > 2:  # urls and digests keys are present
            # sometimes, versions are invalid
            slist = []
            vcls = matcher.version_class
            for k in versions:
                if k in ('urls', 'digests'):
                    continue
                try:
                    if not matcher.match(k):
                        pass  # logger.debug('%s did not match %r', matcher, k)
                    else:
                        if prereleases or not vcls(k).is_prerelease:
                            slist.append(k)
                except Exception:  # pragma: no cover
                    logger.warning('error matching %s with %r', matcher, k)
                    pass  # slist.append(k)
            if len(slist) > 1:
                slist = sorted(slist, key=scheme.key)
            if slist:
                logger.debug('sorted list: %s', slist)
                version = slist[-1]
                result = versions[version]
        if result:
            if r.extras:
                result.extras = r.extras
            result.download_urls = versions.get('urls', {}).get(version, set())
            d = {}
            sd = versions.get('digests', {})
            for url in result.download_urls:
                if url in sd:  # pragma: no cover
                    d[url] = sd[url]
            result.digests = d
        self.matcher = None
        return result


class PyPIRPCLocator(Locator):
    """
    This locator uses XML-RPC to locate distributions. It therefore
    cannot be used with simple mirrors (that only mirror file content).
    """

    def __init__(self, url, **kwargs):
        """
        Initialise an instance.

        :param url: The URL to use for XML-RPC.
        :param kwargs: Passed to the superclass constructor.
        """
        super(PyPIRPCLocator, self).__init__(**kwargs)
        self.base_url = url
        self.client = ServerProxy(url, timeout=3.0)

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        return set(self.client.list_packages())

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        versions = self.client.package_releases(name, True)
        for v in versions:
            urls = self.client.release_urls(name, v)
            data = self.client.release_data(name, v)
            metadata = Metadata(scheme=self.scheme)
            metadata.name = data['name']
            metadata.version = data['version']
            metadata.license = data.get('license')
            metadata.keywords = data.get('keywords', [])
            metadata.summary = data.get('summary')
            dist = Distribution(metadata)
            if urls:
                info = urls[0]
                metadata.source_url = info['url']
                dist.digest = self._get_digest(info)
                dist.locator = self
                result[v] = dist
                for info in urls:
                    url = info['url']
                    digest = self._get_digest(info)
                    result['urls'].setdefault(v, set()).add(url)
                    result['digests'][url] = digest
        return result


class PyPIJSONLocator(Locator):
    """
    This locator uses PyPI's JSON interface. It's very limited in functionality
    and probably not worth using.
    """

    def __init__(self, url, **kwargs):
        super(PyPIJSONLocator, self).__init__(**kwargs)
        self.base_url = ensure_slash(url)

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        raise NotImplementedError('Not available from this locator')

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        url = urljoin(self.base_url, '%s/json' % quote(name))
        try:
            resp = self.opener.open(url)
            data = resp.read().decode()  # for now
            d = json.loads(data)
            md = Metadata(scheme=self.scheme)
            data = d['info']
            md.name = data['name']
            md.version = data['version']
            md.license = data.get('license')
            md.keywords = data.get('keywords', [])
            md.summary = data.get('summary')
            dist = Distribution(md)
            dist.locator = self
            # urls = d['urls']
            result[md.version] = dist
            for info in d['urls']:
                url = info['url']
                dist.download_urls.add(url)
                dist.digests[url] = self._get_digest(info)
                result['urls'].setdefault(md.version, set()).add(url)
                result['digests'][url] = self._get_digest(info)
            # Now get other releases
            for version, infos in d['releases'].items():
                if version == md.version:
                    continue  # already done
                omd = Metadata(scheme=self.scheme)
                omd.name = md.name
                omd.version = version
                odist = Distribution(omd)
                odist.locator = self
                result[version] = odist
                for info in infos:
                    url = info['url']
                    odist.download_urls.add(url)
                    odist.digests[url] = self._get_digest(info)
                    result['urls'].setdefault(version, set()).add(url)
                    result['digests'][url] = self._get_digest(info)


#            for info in urls:
#                md.source_url = info['url']
#                dist.digest = self._get_digest(info)
#                dist.locator = self
#                for info in urls:
#                    url = info['url']
#                    result['urls'].setdefault(md.version, set()).add(url)
#                    result['digests'][url] = self._get_digest(info)
        except Exception as e:
            self.errors.put(text_type(e))
            logger.exception('JSON fetch failed: %s', e)
        return result


class Page(object):
    """
    This class represents a scraped HTML page.
    """
    # The following slightly hairy-looking regex just looks for the contents of
    # an anchor link, which has an attribute "href" either immediately preceded
    # or immediately followed by a "rel" attribute. The attribute values can be
    # declared with double quotes, single quotes or no quotes - which leads to
    # the length of the expression.
    _href = re.compile(
        """
(rel\\s*=\\s*(?:"(?P<rel1>[^"]*)"|'(?P<rel2>[^']*)'|(?P<rel3>[^>\\s\n]*))\\s+)?
href\\s*=\\s*(?:"(?P<url1>[^"]*)"|'(?P<url2>[^']*)'|(?P<url3>[^>\\s\n]*))
(\\s+rel\\s*=\\s*(?:"(?P<rel4>[^"]*)"|'(?P<rel5>[^']*)'|(?P<rel6>[^>\\s\n]*)))?
""", re.I | re.S | re.X)
    _base = re.compile(r"""<base\s+href\s*=\s*['"]?([^'">]+)""", re.I | re.S)

    def __init__(self, data, url):
        """
        Initialise an instance with the Unicode page contents and the URL they
        came from.
        """
        self.data = data
        self.base_url = self.url = url
        m = self._base.search(self.data)
        if m:
            self.base_url = m.group(1)

    _clean_re = re.compile(r'[^a-z0-9$&+,/:;=?@.#%_\\|-]', re.I)

    @cached_property
    def links(self):
        """
        Return the URLs of all the links on a page together with information
        about their "rel" attribute, for determining which ones to treat as
        downloads and which ones to queue for further scraping.
        """

        def clean(url):
            "Tidy up an URL."
            scheme, netloc, path, params, query, frag = urlparse(url)
            return urlunparse((scheme, netloc, quote(path), params, query, frag))

        result = set()
        for match in self._href.finditer(self.data):
            d = match.groupdict('')
            rel = (d['rel1'] or d['rel2'] or d['rel3'] or d['rel4'] or d['rel5'] or d['rel6'])
            url = d['url1'] or d['url2'] or d['url3']
            url = urljoin(self.base_url, url)
            url = unescape(url)
            url = self._clean_re.sub(lambda m: '%%%2x' % ord(m.group(0)), url)
            result.add((url, rel))
        # We sort the result, hoping to bring the most recent versions
        # to the front
        result = sorted(result, key=lambda t: t[0], reverse=True)
        return result


class SimpleScrapingLocator(Locator):
    """
    A locator which scrapes HTML pages to locate downloads for a distribution.
    This runs multiple threads to do the I/O; performance is at least as good
    as pip's PackageFinder, which works in an analogous fashion.
    """

    # These are used to deal with various Content-Encoding schemes.
    decoders = {
        'deflate': zlib.decompress,
        'gzip': lambda b: gzip.GzipFile(fileobj=BytesIO(b)).read(),
        'none': lambda b: b,
    }

    def __init__(self, url, timeout=None, num_workers=10, **kwargs):
        """
        Initialise an instance.
        :param url: The root URL to use for scraping.
        :param timeout: The timeout, in seconds, to be applied to requests.
                        This defaults to ``None`` (no timeout specified).
        :param num_workers: The number of worker threads you want to do I/O,
                            This defaults to 10.
        :param kwargs: Passed to the superclass.
        """
        super(SimpleScrapingLocator, self).__init__(**kwargs)
        self.base_url = ensure_slash(url)
        self.timeout = timeout
        self._page_cache = {}
        self._seen = set()
        self._to_fetch = queue.Queue()
        self._bad_hosts = set()
        self.skip_externals = False
        self.num_workers = num_workers
        self._lock = threading.RLock()
        # See issue #45: we need to be resilient when the locator is used
        # in a thread, e.g. with concurrent.futures. We can't use self._lock
        # as it is for coordinating our internal threads - the ones created
        # in _prepare_threads.
        self._gplock = threading.RLock()
        self.platform_check = False  # See issue #112

    def _prepare_threads(self):
        """
        Threads are created only when get_project is called, and terminate
        before it returns. They are there primarily to parallelise I/O (i.e.
        fetching web pages).
        """
        self._threads = []
        for i in range(self.num_workers):
            t = threading.Thread(target=self._fetch)
            t.daemon = True
            t.start()
            self._threads.append(t)

    def _wait_threads(self):
        """
        Tell all the threads to terminate (by sending a sentinel value) and
        wait for them to do so.
        """
        # Note that you need two loops, since you can't say which
        # thread will get each sentinel
        for t in self._threads:
            self._to_fetch.put(None)  # sentinel
        for t in self._threads:
            t.join()
        self._threads = []

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        with self._gplock:
            self.result = result
            self.project_name = name
            url = urljoin(self.base_url, '%s/' % quote(name))
            self._seen.clear()
            self._page_cache.clear()
            self._prepare_threads()
            try:
                logger.debug('Queueing %s', url)
                self._to_fetch.put(url)
                self._to_fetch.join()
            finally:
                self._wait_threads()
            del self.result
        return result

    platform_dependent = re.compile(r'\b(linux_(i\d86|x86_64|arm\w+)|'
                                    r'win(32|_amd64)|macosx_?\d+)\b', re.I)

    def _is_platform_dependent(self, url):
        """
        Does an URL refer to a platform-specific download?
        """
        return self.platform_dependent.search(url)

    def _process_download(self, url):
        """
        See if an URL is a suitable download for a project.

        If it is, register information in the result dictionary (for
        _get_project) about the specific version it's for.

        Note that the return value isn't actually used other than as a boolean
        value.
        """
        if self.platform_check and self._is_platform_dependent(url):
            info = None
        else:
            info = self.convert_url_to_download_info(url, self.project_name)
        logger.debug('process_download: %s -> %s', url, info)
        if info:
            with self._lock:  # needed because self.result is shared
                self._update_version_data(self.result, info)
        return info

    def _should_queue(self, link, referrer, rel):
        """
        Determine whether a link URL from a referring page and with a
        particular "rel" attribute should be queued for scraping.
        """
        scheme, netloc, path, _, _, _ = urlparse(link)
        if path.endswith(self.source_extensions + self.binary_extensions + self.excluded_extensions):
            result = False
        elif self.skip_externals and not link.startswith(self.base_url):
            result = False
        elif not referrer.startswith(self.base_url):
            result = False
        elif rel not in ('homepage', 'download'):
            result = False
        elif scheme not in ('http', 'https', 'ftp'):
            result = False
        elif self._is_platform_dependent(link):
            result = False
        else:
            host = netloc.split(':', 1)[0]
            if host.lower() == 'localhost':
                result = False
            else:
                result = True
        logger.debug('should_queue: %s (%s) from %s -> %s', link, rel, referrer, result)
        return result

    def _fetch(self):
        """
        Get a URL to fetch from the work queue, get the HTML page, examine its
        links for download candidates and candidates for further scraping.

        This is a handy method to run in a thread.
        """
        while True:
            url = self._to_fetch.get()
            try:
                if url:
                    page = self.get_page(url)
                    if page is None:  # e.g. after an error
                        continue
                    for link, rel in page.links:
                        if link not in self._seen:
                            try:
                                self._seen.add(link)
                                if (not self._process_download(link) and self._should_queue(link, url, rel)):
                                    logger.debug('Queueing %s from %s', link, url)
                                    self._to_fetch.put(link)
                            except MetadataInvalidError:  # e.g. invalid versions
                                pass
            except Exception as e:  # pragma: no cover
                self.errors.put(text_type(e))
            finally:
                # always do this, to avoid hangs :-)
                self._to_fetch.task_done()
            if not url:
                # logger.debug('Sentinel seen, quitting.')
                break

    def get_page(self, url):
        """
        Get the HTML for an URL, possibly from an in-memory cache.

        XXX TODO Note: this cache is never actually cleared. It's assumed that
        the data won't get stale over the lifetime of a locator instance (not
        necessarily true for the default_locator).
        """
        # http://peak.telecommunity.com/DevCenter/EasyInstall#package-index-api
        scheme, netloc, path, _, _, _ = urlparse(url)
        if scheme == 'file' and os.path.isdir(url2pathname(path)):
            url = urljoin(ensure_slash(url), 'index.html')

        if url in self._page_cache:
            result = self._page_cache[url]
            logger.debug('Returning %s from cache: %s', url, result)
        else:
            host = netloc.split(':', 1)[0]
            result = None
            if host in self._bad_hosts:
                logger.debug('Skipping %s due to bad host %s', url, host)
            else:
                req = Request(url, headers={'Accept-encoding': 'identity'})
                try:
                    logger.debug('Fetching %s', url)
                    resp = self.opener.open(req, timeout=self.timeout)
                    logger.debug('Fetched %s', url)
                    headers = resp.info()
                    content_type = headers.get('Content-Type', '')
                    if HTML_CONTENT_TYPE.match(content_type):
                        final_url = resp.geturl()
                        data = resp.read()
                        encoding = headers.get('Content-Encoding')
                        if encoding:
                            decoder = self.decoders[encoding]  # fail if not found
                            data = decoder(data)
                        encoding = 'utf-8'
                        m = CHARSET.search(content_type)
                        if m:
                            encoding = m.group(1)
                        try:
                            data = data.decode(encoding)
                        except UnicodeError:  # pragma: no cover
                            data = data.decode('latin-1')  # fallback
                        result = Page(data, final_url)
                        self._page_cache[final_url] = result
                except HTTPError as e:
                    if e.code != 404:
                        logger.exception('Fetch failed: %s: %s', url, e)
                except URLError as e:  # pragma: no cover
                    logger.exception('Fetch failed: %s: %s', url, e)
                    with self._lock:
                        self._bad_hosts.add(host)
                except Exception as e:  # pragma: no cover
                    logger.exception('Fetch failed: %s: %s', url, e)
                finally:
                    self._page_cache[url] = result  # even if None (failure)
        return result

    _distname_re = re.compile('<a href=[^>]*>([^<]+)<')

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        result = set()
        page = self.get_page(self.base_url)
        if not page:
            raise DistlibException('Unable to get %s' % self.base_url)
        for match in self._distname_re.finditer(page.data):
            result.add(match.group(1))
        return result


class DirectoryLocator(Locator):
    """
    This class locates distributions in a directory tree.
    """

    def __init__(self, path, **kwargs):
        """
        Initialise an instance.
        :param path: The root of the directory tree to search.
        :param kwargs: Passed to the superclass constructor,
                       except for:
                       * recursive - if True (the default), subdirectories are
                         recursed into. If False, only the top-level directory
                         is searched,
        """
        self.recursive = kwargs.pop('recursive', True)
        super(DirectoryLocator, self).__init__(**kwargs)
        path = os.path.abspath(path)
        if not os.path.isdir(path):  # pragma: no cover
            raise DistlibException('Not a directory: %r' % path)
        self.base_dir = path

    def should_include(self, filename, parent):
        """
        Should a filename be considered as a candidate for a distribution
        archive? As well as the filename, the directory which contains it
        is provided, though not used by the current implementation.
        """
        return filename.endswith(self.downloadable_extensions)

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        for root, dirs, files in os.walk(self.base_dir):
            for fn in files:
                if self.should_include(fn, root):
                    fn = os.path.join(root, fn)
                    url = urlunparse(('file', '', pathname2url(os.path.abspath(fn)), '', '', ''))
                    info = self.convert_url_to_download_info(url, name)
                    if info:
                        self._update_version_data(result, info)
            if not self.recursive:
                break
        return result

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        result = set()
        for root, dirs, files in os.walk(self.base_dir):
            for fn in files:
                if self.should_include(fn, root):
                    fn = os.path.join(root, fn)
                    url = urlunparse(('file', '', pathname2url(os.path.abspath(fn)), '', '', ''))
                    info = self.convert_url_to_download_info(url, None)
                    if info:
                        result.add(info['name'])
            if not self.recursive:
                break
        return result


class JSONLocator(Locator):
    """
    This locator uses special extended metadata (not available on PyPI) and is
    the basis of performant dependency resolution in distlib. Other locators
    require archive downloads before dependencies can be determined! As you
    might imagine, that can be slow.
    """

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        raise NotImplementedError('Not available from this locator')

    def _get_project(self, name):
        result = {'urls': {}, 'digests': {}}
        data = get_project_data(name)
        if data:
            for info in data.get('files', []):
                if info['ptype'] != 'sdist' or info['pyversion'] != 'source':
                    continue
                # We don't store summary in project metadata as it makes
                # the data bigger for no benefit during dependency
                # resolution
                dist = make_dist(data['name'],
                                 info['version'],
                                 summary=data.get('summary', 'Placeholder for summary'),
                                 scheme=self.scheme)
                md = dist.metadata
                md.source_url = info['url']
                # TODO SHA256 digest
                if 'digest' in info and info['digest']:
                    dist.digest = ('md5', info['digest'])
                md.dependencies = info.get('requirements', {})
                dist.exports = info.get('exports', {})
                result[dist.version] = dist
                result['urls'].setdefault(dist.version, set()).add(info['url'])
        return result


class DistPathLocator(Locator):
    """
    This locator finds installed distributions in a path. It can be useful for
    adding to an :class:`AggregatingLocator`.
    """

    def __init__(self, distpath, **kwargs):
        """
        Initialise an instance.

        :param distpath: A :class:`DistributionPath` instance to search.
        """
        super(DistPathLocator, self).__init__(**kwargs)
        assert isinstance(distpath, DistributionPath)
        self.distpath = distpath

    def _get_project(self, name):
        dist = self.distpath.get_distribution(name)
        if dist is None:
            result = {'urls': {}, 'digests': {}}
        else:
            result = {
                dist.version: dist,
                'urls': {
                    dist.version: set([dist.source_url])
                },
                'digests': {
                    dist.version: set([None])
                }
            }
        return result


class AggregatingLocator(Locator):
    """
    This class allows you to chain and/or merge a list of locators.
    """

    def __init__(self, *locators, **kwargs):
        """
        Initialise an instance.

        :param locators: The list of locators to search.
        :param kwargs: Passed to the superclass constructor,
                       except for:
                       * merge - if False (the default), the first successful
                         search from any of the locators is returned. If True,
                         the results from all locators are merged (this can be
                         slow).
        """
        self.merge = kwargs.pop('merge', False)
        self.locators = locators
        super(AggregatingLocator, self).__init__(**kwargs)

    def clear_cache(self):
        super(AggregatingLocator, self).clear_cache()
        for locator in self.locators:
            locator.clear_cache()

    def _set_scheme(self, value):
        self._scheme = value
        for locator in self.locators:
            locator.scheme = value

    scheme = property(Locator.scheme.fget, _set_scheme)

    def _get_project(self, name):
        result = {}
        for locator in self.locators:
            d = locator.get_project(name)
            if d:
                if self.merge:
                    files = result.get('urls', {})
                    digests = result.get('digests', {})
                    # next line could overwrite result['urls'], result['digests']
                    result.update(d)
                    df = result.get('urls')
                    if files and df:
                        for k, v in files.items():
                            if k in df:
                                df[k] |= v
                            else:
                                df[k] = v
                    dd = result.get('digests')
                    if digests and dd:
                        dd.update(digests)
                else:
                    # See issue #18. If any dists are found and we're looking
                    # for specific constraints, we only return something if
                    # a match is found. For example, if a DirectoryLocator
                    # returns just foo (1.0) while we're looking for
                    # foo (>= 2.0), we'll pretend there was nothing there so
                    # that subsequent locators can be queried. Otherwise we
                    # would just return foo (1.0) which would then lead to a
                    # failure to find foo (>= 2.0), because other locators
                    # weren't searched. Note that this only matters when
                    # merge=False.
                    if self.matcher is None:
                        found = True
                    else:
                        found = False
                        for k in d:
                            if self.matcher.match(k):
                                found = True
                                break
                    if found:
                        result = d
                        break
        return result

    def get_distribution_names(self):
        """
        Return all the distribution names known to this locator.
        """
        result = set()
        for locator in self.locators:
            try:
                result |= locator.get_distribution_names()
            except NotImplementedError:
                pass
        return result


# We use a legacy scheme simply because most of the dists on PyPI use legacy
# versions which don't conform to PEP 440.
default_locator = AggregatingLocator(
    # JSONLocator(), # don't use as PEP 426 is withdrawn
    SimpleScrapingLocator('https://pypi.org/simple/', timeout=3.0),
    scheme='legacy')

locate = default_locator.locate


class DependencyFinder(object):
    """
    Locate dependencies for distributions.
    """

    def __init__(self, locator=None):
        """
        Initialise an instance, using the specified locator
        to locate distributions.
        """
        self.locator = locator or default_locator
        self.scheme = get_scheme(self.locator.scheme)

    def add_distribution(self, dist):
        """
        Add a distribution to the finder. This will update internal information
        about who provides what.
        :param dist: The distribution to add.
        """
        logger.debug('adding distribution %s', dist)
        name = dist.key
        self.dists_by_name[name] = dist
        self.dists[(name, dist.version)] = dist
        for p in dist.provides:
            name, version = parse_name_and_version(p)
            logger.debug('Add to provided: %s, %s, %s', name, version, dist)
            self.provided.setdefault(name, set()).add((version, dist))

    def remove_distribution(self, dist):
        """
        Remove a distribution from the finder. This will update internal
        information about who provides what.
        :param dist: The distribution to remove.
        """
        logger.debug('removing distribution %s', dist)
        name = dist.key
        del self.dists_by_name[name]
        del self.dists[(name, dist.version)]
        for p in dist.provides:
            name, version = parse_name_and_version(p)
            logger.debug('Remove from provided: %s, %s, %s', name, version, dist)
            s = self.provided[name]
            s.remove((version, dist))
            if not s:
                del self.provided[name]

    def get_matcher(self, reqt):
        """
        Get a version matcher for a requirement.
        :param reqt: The requirement
        :type reqt: str
        :return: A version matcher (an instance of
                 :class:`distlib.version.Matcher`).
        """
        try:
            matcher = self.scheme.matcher(reqt)
        except UnsupportedVersionError:  # pragma: no cover
            # XXX compat-mode if cannot read the version
            name = reqt.split()[0]
            matcher = self.scheme.matcher(name)
        return matcher

    def find_providers(self, reqt):
        """
        Find the distributions which can fulfill a requirement.

        :param reqt: The requirement.
         :type reqt: str
        :return: A set of distribution which can fulfill the requirement.
        """
        matcher = self.get_matcher(reqt)
        name = matcher.key  # case-insensitive
        result = set()
        provided = self.provided
        if name in provided:
            for version, provider in provided[name]:
                try:
                    match = matcher.match(version)
                except UnsupportedVersionError:
                    match = False

                if match:
                    result.add(provider)
                    break
        return result

    def try_to_replace(self, provider, other, problems):
        """
        Attempt to replace one provider with another. This is typically used
        when resolving dependencies from multiple sources, e.g. A requires
        (B >= 1.0) while C requires (B >= 1.1).

        For successful replacement, ``provider`` must meet all the requirements
        which ``other`` fulfills.

        :param provider: The provider we are trying to replace with.
        :param other: The provider we're trying to replace.
        :param problems: If False is returned, this will contain what
                         problems prevented replacement. This is currently
                         a tuple of the literal string 'cantreplace',
                         ``provider``, ``other``  and the set of requirements
                         that ``provider`` couldn't fulfill.
        :return: True if we can replace ``other`` with ``provider``, else
                 False.
        """
        rlist = self.reqts[other]
        unmatched = set()
        for s in rlist:
            matcher = self.get_matcher(s)
            if not matcher.match(provider.version):
                unmatched.add(s)
        if unmatched:
            # can't replace other with provider
            problems.add(('cantreplace', provider, other, frozenset(unmatched)))
            result = False
        else:
            # can replace other with provider
            self.remove_distribution(other)
            del self.reqts[other]
            for s in rlist:
                self.reqts.setdefault(provider, set()).add(s)
            self.add_distribution(provider)
            result = True
        return result

    def find(self, requirement, meta_extras=None, prereleases=False):
        """
        Find a distribution and all distributions it depends on.

        :param requirement: The requirement specifying the distribution to
                            find, or a Distribution instance.
        :param meta_extras: A list of meta extras such as :test:, :build: and
                            so on.
        :param prereleases: If ``True``, allow pre-release versions to be
                            returned - otherwise, don't return prereleases
                            unless they're all that's available.

        Return a set of :class:`Distribution` instances and a set of
        problems.

        The distributions returned should be such that they have the
        :attr:`required` attribute set to ``True`` if they were
        from the ``requirement`` passed to ``find()``, and they have the
        :attr:`build_time_dependency` attribute set to ``True`` unless they
        are post-installation dependencies of the ``requirement``.

        The problems should be a tuple consisting of the string
        ``'unsatisfied'`` and the requirement which couldn't be satisfied
        by any distribution known to the locator.
        """

        self.provided = {}
        self.dists = {}
        self.dists_by_name = {}
        self.reqts = {}

        meta_extras = set(meta_extras or [])
        if ':*:' in meta_extras:
            meta_extras.remove(':*:')
            # :meta: and :run: are implicitly included
            meta_extras |= set([':test:', ':build:', ':dev:'])

        if isinstance(requirement, Distribution):
            dist = odist = requirement
            logger.debug('passed %s as requirement', odist)
        else:
            dist = odist = self.locator.locate(requirement, prereleases=prereleases)
            if dist is None:
                raise DistlibException('Unable to locate %r' % requirement)
            logger.debug('located %s', odist)
        dist.requested = True
        problems = set()
        todo = set([dist])
        install_dists = set([odist])
        while todo:
            dist = todo.pop()
            name = dist.key  # case-insensitive
            if name not in self.dists_by_name:
                self.add_distribution(dist)
            else:
                # import pdb; pdb.set_trace()
                other = self.dists_by_name[name]
                if other != dist:
                    self.try_to_replace(dist, other, problems)

            ireqts = dist.run_requires | dist.meta_requires
            sreqts = dist.build_requires
            ereqts = set()
            if meta_extras and dist in install_dists:
                for key in ('test', 'build', 'dev'):
                    e = ':%s:' % key
                    if e in meta_extras:
                        ereqts |= getattr(dist, '%s_requires' % key)
            all_reqts = ireqts | sreqts | ereqts
            for r in all_reqts:
                providers = self.find_providers(r)
                if not providers:
                    logger.debug('No providers found for %r', r)
                    provider = self.locator.locate(r, prereleases=prereleases)
                    # If no provider is found and we didn't consider
                    # prereleases, consider them now.
                    if provider is None and not prereleases:
                        provider = self.locator.locate(r, prereleases=True)
                    if provider is None:
                        logger.debug('Cannot satisfy %r', r)
                        problems.add(('unsatisfied', r))
                    else:
                        n, v = provider.key, provider.version
                        if (n, v) not in self.dists:
                            todo.add(provider)
                        providers.add(provider)
                        if r in ireqts and dist in install_dists:
                            install_dists.add(provider)
                            logger.debug('Adding %s to install_dists', provider.name_and_version)
                for p in providers:
                    name = p.key
                    if name not in self.dists_by_name:
                        self.reqts.setdefault(p, set()).add(r)
                    else:
                        other = self.dists_by_name[name]
                        if other != p:
                            # see if other can be replaced by p
                            self.try_to_replace(p, other, problems)

        dists = set(self.dists.values())
        for dist in dists:
            dist.build_time_dependency = dist not in install_dists
            if dist.build_time_dependency:
                logger.debug('%s is a build-time dependency only.', dist.name_and_version)
        logger.debug('find done for %s', odist)
        return dists, problems

# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\client\framework.py ===
"""AXScript Client Framework

This module provides a core framework for an ActiveX Scripting client.
Derived classes actually implement the AX Client itself, including the
scoping rules, etc.

There are classes defined for the engine itself, and for ScriptItems
"""

from __future__ import annotations

import re
import sys
from typing import NoReturn

import pythoncom  # Need simple connection point support
import win32api
import win32com.client.connect
import win32com.server.util
import winerror
from win32com.axscript import axscript
from win32com.server.exception import COMException, IsCOMServerException

from . import error  # axscript.client.error


def RemoveCR(text):
    # No longer just "RemoveCR" - should be renamed to
    # FixNewlines, or something.  Idea is to fix arbitary newlines into
    # something Python can compile...
    return re.sub(r"(\r\n)|\r|(\n\r)", "\n", text)


SCRIPTTEXT_FORCEEXECUTION = -2147483648  # 0x80000000
SCRIPTTEXT_ISEXPRESSION = 0x00000020
SCRIPTTEXT_ISPERSISTENT = 0x00000040


state_map = {
    axscript.SCRIPTSTATE_UNINITIALIZED: "SCRIPTSTATE_UNINITIALIZED",
    axscript.SCRIPTSTATE_INITIALIZED: "SCRIPTSTATE_INITIALIZED",
    axscript.SCRIPTSTATE_STARTED: "SCRIPTSTATE_STARTED",
    axscript.SCRIPTSTATE_CONNECTED: "SCRIPTSTATE_CONNECTED",
    axscript.SCRIPTSTATE_DISCONNECTED: "SCRIPTSTATE_DISCONNECTED",
    axscript.SCRIPTSTATE_CLOSED: "SCRIPTSTATE_CLOSED",
}


def profile(fn, *args):
    import profile

    prof = profile.Profile()
    try:
        # roll on 1.6 :-)
        # 		return prof.runcall(fn, *args)
        return prof.runcall(*(fn,) + args)
    finally:
        import pstats

        # Damn - really want to send this to Excel!
        #      width, list = pstats.Stats(prof).strip_dirs().get_print_list([])
        pstats.Stats(prof).strip_dirs().sort_stats("time").print_stats()


class SafeOutput:
    softspace = 1

    def __init__(self, redir=None):
        if redir is None:
            redir = sys.stdout
        self.redir = redir

    def write(self, message):
        try:
            self.redir.write(message)
        except:
            win32api.OutputDebugString(message)

    def flush(self):
        pass

    def close(self):
        pass


# Make sure we have a valid sys.stdout/stderr, otherwise out
# print and trace statements may raise an exception
def MakeValidSysOuts():
    if not isinstance(sys.stdout, SafeOutput):
        sys.stdout = sys.stderr = SafeOutput()
        # and for the sake of working around something I can't understand...
        # prevent keyboard interrupts from killing IIS
        import signal

        def noOp(a, b):
            # it would be nice to get to the bottom of this, so a warning to
            # the debug console can't hurt.
            print("WARNING: Ignoring keyboard interrupt from ActiveScripting engine")

        # If someone else has already redirected, then assume they know what they are doing!
        if signal.getsignal(signal.SIGINT) == signal.default_int_handler:
            try:
                signal.signal(signal.SIGINT, noOp)
            except ValueError:
                # Not the main thread - can't do much.
                pass


def trace(*args):
    """A function used instead of "print" for debugging output."""
    for arg in args:
        print(arg, end=" ")
    print()


def RaiseAssert(scode, desc) -> NoReturn:
    """A debugging function that raises an exception considered an "Assertion"."""
    print("**************** ASSERTION FAILED *******************")
    print(desc)
    raise COMException(desc, scode)


class AXScriptCodeBlock:
    """An object which represents a chunk of code in an AX Script"""

    def __init__(
        self,
        name: str,
        codeText: str,
        sourceContextCookie: int,
        startLineNumber: int,
        flags,
    ):
        self.name = name
        self.codeText = codeText
        self.codeObject = None
        self.sourceContextCookie = sourceContextCookie
        self.startLineNumber = startLineNumber
        self.flags = flags
        self.beenExecuted = 0

    def GetFileName(self):
        # Gets the "file name" for Python - uses <...> so Python doesn't think
        # it is a real file.
        return "<%s>" % self.name

    def GetDisplayName(self):
        return self.name

    def GetLineNo(self, no: int):
        pos = -1
        for i in range(no - 1):
            pos = self.codeText.find("\n", pos + 1)
            if pos == -1:
                pos = len(self.codeText)
        epos = self.codeText.find("\n", pos + 1)
        if epos == -1:
            epos = len(self.codeText)
        return self.codeText[pos + 1 : epos].strip()


class Event:
    """A single event for a ActiveX named object."""

    def __init__(self):
        self.name = "<None>"

    def __repr__(self):
        return "<%s at %d: %s>" % (self.__class__.__name__, id(self), self.name)

    def Reset(self):
        pass

    def Close(self):
        pass

    def Build(self, typeinfo, funcdesc):
        self.dispid = funcdesc[0]
        self.name = typeinfo.GetNames(self.dispid)[0]


# print("Event.Build() - Event Name is ", self.name)


class EventSink:
    """A set of events against an item.  Note this is a COM client for connection points."""

    _public_methods_: list[str] = []

    def __init__(self, myItem, coDispatch):
        self.events = {}
        self.connection = None
        self.coDispatch = coDispatch
        self.myScriptItem = myItem
        self.myInvokeMethod = myItem.GetEngine().ProcessScriptItemEvent
        self.iid = None

    def Reset(self):
        self.Disconnect()

    def Close(self):
        self.iid = None
        self.myScriptItem = None
        self.myInvokeMethod = None
        self.coDispatch = None
        for event in self.events.values():
            event.Reset()
        self.events = {}
        self.Disconnect()

    # COM Connection point methods.
    def _query_interface_(self, iid):
        if iid == self.iid:
            return win32com.server.util.wrap(self)

    def _invoke_(self, dispid, lcid, wFlags, args):
        try:
            event = self.events[dispid]
        except:
            raise COMException(scode=winerror.DISP_E_MEMBERNOTFOUND)
        # print("Invoke for ", event, "on", self.myScriptItem, " - calling",  self.myInvokeMethod)
        return self.myInvokeMethod(self.myScriptItem, event, lcid, wFlags, args)

    def GetSourceTypeInfo(self, typeinfo):
        """Gets the typeinfo for the Source Events for the passed typeinfo"""
        attr = typeinfo.GetTypeAttr()
        cFuncs = attr[6]
        typeKind = attr[5]
        if typeKind not in [pythoncom.TKIND_COCLASS, pythoncom.TKIND_INTERFACE]:
            RaiseAssert(
                winerror.E_UNEXPECTED, "The typeKind of the object is unexpected"
            )
        cImplType = attr[8]
        for i in range(cImplType):
            # Look for the [source, default] interface on the coclass
            # that isn't marked as restricted.
            flags = typeinfo.GetImplTypeFlags(i)
            flagsNeeded = (
                pythoncom.IMPLTYPEFLAG_FDEFAULT | pythoncom.IMPLTYPEFLAG_FSOURCE
            )
            if (flags & (flagsNeeded | pythoncom.IMPLTYPEFLAG_FRESTRICTED)) == (
                flagsNeeded
            ):
                # Get the handle to the implemented interface.
                href = typeinfo.GetRefTypeOfImplType(i)
                return typeinfo.GetRefTypeInfo(href)

    def BuildEvents(self):
        # See if it is an extender object.
        try:
            mainTypeInfo = self.coDispatch.QueryInterface(
                axscript.IID_IProvideMultipleClassInfo
            )
            isMulti = 1
            numTypeInfos = mainTypeInfo.GetMultiTypeInfoCount()
        except pythoncom.com_error:
            isMulti = 0
            numTypeInfos = 1
            try:
                mainTypeInfo = self.coDispatch.QueryInterface(
                    pythoncom.IID_IProvideClassInfo
                )
            except pythoncom.com_error:
                numTypeInfos = 0
        # Create an event handler for the item.
        for item in range(numTypeInfos):
            if isMulti:
                typeinfo, flags = mainTypeInfo.GetInfoOfIndex(
                    item, axscript.MULTICLASSINFO_GETTYPEINFO
                )
            else:
                typeinfo = mainTypeInfo.GetClassInfo()
            sourceType = self.GetSourceTypeInfo(typeinfo)
            cFuncs = 0
            if sourceType:
                attr = sourceType.GetTypeAttr()
                self.iid = attr[0]
                cFuncs = attr[6]
                for i in range(cFuncs):
                    funcdesc = sourceType.GetFuncDesc(i)
                    event = Event()
                    event.Build(sourceType, funcdesc)
                    self.events[event.dispid] = event

    def Connect(self):
        if self.connection is not None or self.iid is None:
            return
        # 		trace("Connect for sink item", self.myScriptItem.name, "with IID",str(self.iid))
        self.connection = win32com.client.connect.SimpleConnection(
            self.coDispatch, self, self.iid
        )

    def Disconnect(self):
        if self.connection:
            try:
                self.connection.Disconnect()
            except pythoncom.com_error:
                pass  # Ignore disconnection errors.
            self.connection = None


class ScriptItem:
    """An item (or subitem) that is exposed to the ActiveX script"""

    def __init__(self, parentItem, name, dispatch, flags):
        self.parentItem = parentItem
        self.dispatch = dispatch
        self.name = name
        self.flags = flags
        self.eventSink = None
        self.subItems = {}
        self.createdConnections = 0
        self.isRegistered = 0

    # 		trace("Creating ScriptItem", name, "of parent", parentItem,"with dispatch", dispatch)

    def __repr__(self):
        flagsDesc = ""
        if self.flags is not None and self.flags & axscript.SCRIPTITEM_GLOBALMEMBERS:
            flagsDesc = "/Global"
        return "<%s at %d: %s%s>" % (
            self.__class__.__name__,
            id(self),
            self.name,
            flagsDesc,
        )

    def _dump_(self, level):
        flagDescs = []
        if self.flags is not None and self.flags & axscript.SCRIPTITEM_GLOBALMEMBERS:
            flagDescs.append("GLOBAL!")
        if self.flags is None or self.flags & axscript.SCRIPTITEM_ISVISIBLE == 0:
            flagDescs.append("NOT VISIBLE")
        if self.flags is not None and self.flags & axscript.SCRIPTITEM_ISSOURCE:
            flagDescs.append("EVENT SINK")
        if self.flags is not None and self.flags & axscript.SCRIPTITEM_CODEONLY:
            flagDescs.append("CODE ONLY")
        print(" " * level, "Name=", self.name, ", flags=", "/".join(flagDescs), self)
        for subItem in self.subItems.values():
            subItem._dump_(level + 1)

    def Reset(self):
        self.Disconnect()
        if self.eventSink:
            self.eventSink.Reset()
        self.isRegistered = 0
        for subItem in self.subItems.values():
            subItem.Reset()

    def Close(self):
        self.Reset()
        self.dispatch = None
        self.parentItem = None
        if self.eventSink:
            self.eventSink.Close()
            self.eventSink = None
        for subItem in self.subItems.values():
            subItem.Close()
        self.subItems = []
        self.createdConnections = 0

    def Register(self):
        if self.isRegistered:
            return
        # Get the type info to use to build this item.
        # if not self.dispatch:
        #     id = self.parentItem.dispatch.GetIDsOfNames(self.name)
        #     print("DispID of me is", id)
        #     result = self.parentItem.dispatch.Invoke(id, 0, pythoncom.DISPATCH_PROPERTYGET,1)
        #     if isinstance(result, pythoncom.TypeIIDs[pythoncom.IID_IDispatch]):
        #         self.dispatch = result
        #     else:
        #         print("*** No dispatch")
        #         return
        #     print("**** Made dispatch")
        self.isRegistered = 1
        # Register the sub-items.
        for item in self.subItems.values():
            if not item.isRegistered:
                item.Register()

    def IsGlobal(self):
        return self.flags & axscript.SCRIPTITEM_GLOBALMEMBERS

    def IsVisible(self):
        return (
            self.flags & (axscript.SCRIPTITEM_ISVISIBLE | axscript.SCRIPTITEM_ISSOURCE)
        ) != 0

    def GetEngine(self):
        item = self
        while item.parentItem.__class__ == self.__class__:
            item = item.parentItem
        return item.parentItem

    def _GetFullItemName(self):
        ret = self.name
        if self.parentItem:
            try:
                ret = self.parentItem._GetFullItemName() + "." + ret
            except AttributeError:
                pass
        return ret

    def GetSubItemClass(self):
        return self.__class__

    def GetSubItem(self, name):
        return self.subItems[name.lower()]

    def GetCreateSubItem(self, parentItem, name, dispatch, flags):
        keyName = name.lower()
        try:
            rc = self.subItems[keyName]
            # No changes allowed to existing flags.
            if not rc.flags is None and not flags is None and rc.flags != flags:
                raise COMException(scode=winerror.E_INVALIDARG)
            # Existing item must not have a dispatch.
            if not rc.dispatch is None and not dispatch is None:
                raise COMException(scode=winerror.E_INVALIDARG)
            rc.flags = flags  # Setup the real flags.
            rc.dispatch = dispatch
        except KeyError:
            rc = self.subItems[keyName] = self.GetSubItemClass()(
                parentItem, name, dispatch, flags
            )
        return rc

    # 		if self.dispatch is None:
    # 			RaiseAssert(winerror.E_UNEXPECTED, "??")

    def CreateConnections(self):
        # Create (but do not connect to) the connection points.
        if self.createdConnections:
            return
        self.createdConnections = 1
        # Nothing to do unless this is an event source
        # This flags means self, _and_ children, are connectable.
        if self.flags & axscript.SCRIPTITEM_ISSOURCE:
            self.BuildEvents()
            self.FindBuildSubItemEvents()

    def Connect(self):
        # Connect to the already created connection points.
        if self.eventSink:
            self.eventSink.Connect()
        for subItem in self.subItems.values():
            subItem.Connect()

    def Disconnect(self):
        # Disconnect from the connection points.
        if self.eventSink:
            self.eventSink.Disconnect()
        for subItem in self.subItems.values():
            subItem.Disconnect()

    def BuildEvents(self):
        if self.eventSink is not None or self.dispatch is None:
            RaiseAssert(
                winerror.E_UNEXPECTED,
                "Item already has built events, or no dispatch available?",
            )

        # 		trace("BuildEvents for named item", self._GetFullItemName())
        self.eventSink = EventSink(self, self.dispatch)
        self.eventSink.BuildEvents()

    def FindBuildSubItemEvents(self):
        # Called during connection to event source.  Seeks out and connects to
        # all children.  As per the AX spec, this is not recursive
        # (ie, children sub-items are not seeked)
        try:
            multiTypeInfo = self.dispatch.QueryInterface(
                axscript.IID_IProvideMultipleClassInfo
            )
            numTypeInfos = multiTypeInfo.GetMultiTypeInfoCount()
        except pythoncom.com_error:
            return
        for item in range(numTypeInfos):
            typeinfo, flags = multiTypeInfo.GetInfoOfIndex(
                item, axscript.MULTICLASSINFO_GETTYPEINFO
            )
            defaultType = self.GetDefaultSourceTypeInfo(typeinfo)
            index = 0
            while 1:
                try:
                    fdesc = defaultType.GetFuncDesc(index)
                except pythoncom.com_error:
                    break  # No more funcs
                index += 1
                dispid = fdesc[0]
                funckind = fdesc[3]
                invkind = fdesc[4]
                elemdesc = fdesc[8]
                funcflags = fdesc[9]
                try:
                    isSubObject = (
                        not (funcflags & pythoncom.FUNCFLAG_FRESTRICTED)
                        and funckind == pythoncom.FUNC_DISPATCH
                        and invkind == pythoncom.INVOKE_PROPERTYGET
                        and elemdesc[0][0] == pythoncom.VT_PTR
                        and elemdesc[0][1][0] == pythoncom.VT_USERDEFINED
                    )
                except:
                    isSubObject = 0
                if isSubObject:
                    try:
                        # We found a sub-object.
                        names = typeinfo.GetNames(dispid)
                        result = self.dispatch.Invoke(
                            dispid, 0x0, pythoncom.DISPATCH_PROPERTYGET, 1
                        )
                        # IE has an interesting problem - there are lots of synonyms for the same object.  Eg
                        # in a simple form, "window.top", "window.window", "window.parent", "window.self"
                        # all refer to the same object.  Our event implementation code does not differentiate
                        # eg, "window_onload" will fire for *all* objects named "window".  Thus,
                        # "window" and "window.window" will fire the same event handler :(
                        # One option would be to check if the sub-object is indeed the
                        # parent object - however, this would stop "top_onload" from firing,
                        # as no event handler for "top" would work.
                        # I think we simply need to connect to a *single* event handler.
                        # As use in IE is deprecated, I am not solving this now.
                        if isinstance(
                            result, pythoncom.TypeIIDs[pythoncom.IID_IDispatch]
                        ):
                            name = names[0]
                            subObj = self.GetCreateSubItem(
                                self, name, result, axscript.SCRIPTITEM_ISVISIBLE
                            )
                            # print(
                            #     "subobj",
                            #     name,
                            #     "flags are",
                            #     subObj.flags,
                            #     "mydisp=",
                            #     self.dispatch,
                            #     "result disp=",
                            #     result,
                            #     "compare=",
                            #     self.dispatch == result,
                            # )
                            subObj.BuildEvents()
                            subObj.Register()
                    except pythoncom.com_error:
                        pass

    def GetDefaultSourceTypeInfo(self, typeinfo):
        """Gets the typeinfo for the Default Dispatch for the passed typeinfo"""
        attr = typeinfo.GetTypeAttr()
        cFuncs = attr[6]
        typeKind = attr[5]
        if typeKind not in [pythoncom.TKIND_COCLASS, pythoncom.TKIND_INTERFACE]:
            RaiseAssert(
                winerror.E_UNEXPECTED, "The typeKind of the object is unexpected"
            )
        cImplType = attr[8]
        for i in range(cImplType):
            # Look for the [source, default] interface on the coclass
            # that isn't marked as restricted.
            flags = typeinfo.GetImplTypeFlags(i)
            if (
                flags
                & (
                    pythoncom.IMPLTYPEFLAG_FDEFAULT
                    | pythoncom.IMPLTYPEFLAG_FSOURCE
                    | pythoncom.IMPLTYPEFLAG_FRESTRICTED
                )
            ) == pythoncom.IMPLTYPEFLAG_FDEFAULT:
                # Get the handle to the implemented interface.
                href = typeinfo.GetRefTypeOfImplType(i)
                defTypeInfo = typeinfo.GetRefTypeInfo(href)
                attr = defTypeInfo.GetTypeAttr()
                typeKind = attr[5]
                typeFlags = attr[11]
                if (
                    typeKind == pythoncom.TKIND_INTERFACE
                    and typeFlags & pythoncom.TYPEFLAG_FDUAL
                ):
                    # Get corresponding Disp interface
                    # -1 is a special value which does this for us.
                    href = typeinfo.GetRefTypeOfImplType(-1)
                    return defTypeInfo.GetRefTypeInfo(href)
                else:
                    return defTypeInfo


IActiveScriptMethods = [
    "SetScriptSite",
    "GetScriptSite",
    "SetScriptState",
    "GetScriptState",
    "Close",
    "AddNamedItem",
    "AddTypeLib",
    "GetScriptDispatch",
    "GetCurrentScriptThreadID",
    "GetScriptThreadID",
    "GetScriptThreadState",
    "InterruptScriptThread",
    "Clone",
]
IActiveScriptParseMethods = ["InitNew", "AddScriptlet", "ParseScriptText"]
IObjectSafetyMethods = ["GetInterfaceSafetyOptions", "SetInterfaceSafetyOptions"]

# ActiveScriptParseProcedure is a new interface with IIS4/IE4.
IActiveScriptParseProcedureMethods = ["ParseProcedureText"]


class COMScript:
    """An ActiveX Scripting engine base class.

    This class implements the required COM interfaces for ActiveX scripting.
    """

    _public_methods_ = (
        IActiveScriptMethods
        + IActiveScriptParseMethods
        + IObjectSafetyMethods
        + IActiveScriptParseProcedureMethods
    )
    _com_interfaces_ = [
        axscript.IID_IActiveScript,
        axscript.IID_IActiveScriptParse,
        axscript.IID_IObjectSafety,
    ]  # , axscript.IID_IActiveScriptParseProcedure]

    def __init__(self):
        # Make sure we can print/trace wihout an exception!
        MakeValidSysOuts()
        # 		trace("AXScriptEngine object created", self)
        self.baseThreadId = -1
        self.debugManager = None
        self.threadState = axscript.SCRIPTTHREADSTATE_NOTINSCRIPT
        self.scriptState = axscript.SCRIPTSTATE_UNINITIALIZED
        self.scriptSite = None
        self.safetyOptions = 0
        self.lcid = 0
        self.subItems = {}
        self.scriptCodeBlocks: dict[str, AXScriptCodeBlock] = {}

    def _query_interface_(self, iid):
        if self.debugManager:
            return self.debugManager._query_interface_for_debugger_(iid)
        # 		trace("ScriptEngine QI - unknown IID", iid)
        return 0

    # IActiveScriptParse
    def InitNew(self):
        if self.scriptSite is not None:
            self.SetScriptState(axscript.SCRIPTSTATE_INITIALIZED)

    def AddScriptlet(
        self,
        defaultName,
        code,
        itemName,
        subItemName,
        eventName,
        delimiter,
        sourceContextCookie,
        startLineNumber,
    ):
        # 		trace ("AddScriptlet", defaultName, code, itemName, subItemName, eventName, delimiter, sourceContextCookie, startLineNumber)
        self.DoAddScriptlet(
            defaultName,
            code,
            itemName,
            subItemName,
            eventName,
            delimiter,
            sourceContextCookie,
            startLineNumber,
        )

    def ParseScriptText(
        self,
        code,
        itemName,
        context,
        delimiter,
        sourceContextCookie,
        startLineNumber,
        flags,
        bWantResult,
    ):
        # 		trace ("ParseScriptText", code[:20],"...", itemName, context, delimiter, sourceContextCookie, startLineNumber, flags, bWantResult)
        if (
            bWantResult
            or self.scriptState == axscript.SCRIPTSTATE_STARTED
            or self.scriptState == axscript.SCRIPTSTATE_CONNECTED
            or self.scriptState == axscript.SCRIPTSTATE_DISCONNECTED
        ):
            flags |= SCRIPTTEXT_FORCEEXECUTION
        else:
            flags &= ~SCRIPTTEXT_FORCEEXECUTION

        if flags & SCRIPTTEXT_FORCEEXECUTION:
            # About to execute the code.
            self.RegisterNewNamedItems()
        return self.DoParseScriptText(
            code, sourceContextCookie, startLineNumber, bWantResult, flags
        )

    #
    # IActiveScriptParseProcedure
    def ParseProcedureText(
        self,
        code,
        formalParams,
        procName,
        itemName,
        unkContext,
        delimiter,
        contextCookie,
        startingLineNumber,
        flags,
    ):
        trace(
            "ParseProcedureText",
            code,
            formalParams,
            procName,
            itemName,
            unkContext,
            delimiter,
            contextCookie,
            startingLineNumber,
            flags,
        )
        # NOTE - this is never called, as we have disabled this interface.
        # Problem is, once enabled all even code comes via here, rather than AddScriptlet.
        # However, the "procName" is always an empty string - ie, itemName is the object whose event we are handling,
        # but no idea what the specific event is!?
        # Problem is disabling this block is that AddScriptlet is _not_ passed
        # <SCRIPT for="whatever" event="onClick" language="Python">
        # (but even for those blocks, the "onClick" information is still missing!?!?!?)

        # 		self.DoAddScriptlet(None, code, itemName, subItemName, eventName, delimiter,sourceContextCookie, startLineNumber)
        return None

    #
    # IActiveScript
    def SetScriptSite(self, site):
        # We should still work with an existing site (or so MSXML believes :)
        self.scriptSite = site
        if self.debugManager is not None:
            self.debugManager.Close()
        import traceback

        try:
            import win32com.axdebug.axdebug  # see if the core exists.

            from . import debug

            self.debugManager = debug.DebugManager(self)
        except pythoncom.com_error:
            # COM errors will occur if the debugger interface has never been
            # seen on the target system
            trace("Debugging interfaces not available - debugging is disabled..")
            self.debugManager = None
        except ImportError:
            trace(
                "Debugging extensions (axdebug) module does not exist - debugging is disabled.."
            )
            self.debugManager = None
        except:
            traceback.print_exc()
            trace(
                "*** Debugger Manager could not initialize - {}: {}".format(
                    sys.exc_info()[0], sys.exc_info()[1]
                )
            )
            self.debugManager = None

        try:
            self.lcid = site.GetLCID()
        except pythoncom.com_error:
            self.lcid = win32api.GetUserDefaultLCID()
        self.Reset()

    def GetScriptSite(self, iid):
        if self.scriptSite is None:
            raise COMException(scode=winerror.S_FALSE)
        return self.scriptSite.QueryInterface(iid)

    def SetScriptState(self, state):
        # print(f"SetScriptState with {state_map.get(state)} - currentstate = {state_map.get(self.scriptState)}"
        if state == self.scriptState:
            return
        # If closed, allow no other state transitions
        if self.scriptState == axscript.SCRIPTSTATE_CLOSED:
            raise COMException(scode=winerror.E_INVALIDARG)

        if state == axscript.SCRIPTSTATE_INITIALIZED:
            # Re-initialize - shutdown then reset.
            if self.scriptState in [
                axscript.SCRIPTSTATE_CONNECTED,
                axscript.SCRIPTSTATE_STARTED,
            ]:
                self.Stop()
        elif state == axscript.SCRIPTSTATE_STARTED:
            if self.scriptState == axscript.SCRIPTSTATE_CONNECTED:
                self.Disconnect()
            if self.scriptState == axscript.SCRIPTSTATE_DISCONNECTED:
                self.Reset()
            self.Run()
            self.ChangeScriptState(axscript.SCRIPTSTATE_STARTED)
        elif state == axscript.SCRIPTSTATE_CONNECTED:
            if self.scriptState in [
                axscript.SCRIPTSTATE_UNINITIALIZED,
                axscript.SCRIPTSTATE_INITIALIZED,
            ]:
                self.ChangeScriptState(
                    axscript.SCRIPTSTATE_STARTED
                )  # report transition through started
                self.Run()
            if self.scriptState == axscript.SCRIPTSTATE_STARTED:
                self.Connect()
                self.ChangeScriptState(state)
        elif state == axscript.SCRIPTSTATE_DISCONNECTED:
            if self.scriptState == axscript.SCRIPTSTATE_CONNECTED:
                self.Disconnect()
        elif state == axscript.SCRIPTSTATE_CLOSED:
            self.Close()
        elif state == axscript.SCRIPTSTATE_UNINITIALIZED:
            if self.scriptState == axscript.SCRIPTSTATE_STARTED:
                self.Stop()
            if self.scriptState == axscript.SCRIPTSTATE_CONNECTED:
                self.Disconnect()
            if self.scriptState == axscript.SCRIPTSTATE_DISCONNECTED:
                self.Reset()
            self.ChangeScriptState(state)
        else:
            raise COMException(scode=winerror.E_INVALIDARG)

    def GetScriptState(self):
        return self.scriptState

    def Close(self):
        # 		trace("Close")
        if self.scriptState in [
            axscript.SCRIPTSTATE_CONNECTED,
            axscript.SCRIPTSTATE_DISCONNECTED,
        ]:
            self.Stop()
        if self.scriptState in [
            axscript.SCRIPTSTATE_CONNECTED,
            axscript.SCRIPTSTATE_DISCONNECTED,
            axscript.SCRIPTSTATE_INITIALIZED,
            axscript.SCRIPTSTATE_STARTED,
        ]:
            pass  # engine.close??
        if self.scriptState in [
            axscript.SCRIPTSTATE_UNINITIALIZED,
            axscript.SCRIPTSTATE_CONNECTED,
            axscript.SCRIPTSTATE_DISCONNECTED,
            axscript.SCRIPTSTATE_INITIALIZED,
            axscript.SCRIPTSTATE_STARTED,
        ]:
            self.ChangeScriptState(axscript.SCRIPTSTATE_CLOSED)
            # Completely reset all named items (including persistent)
            for item in self.subItems.values():
                item.Close()
            self.subItems = {}
            self.baseThreadId = -1
        if self.debugManager:
            self.debugManager.Close()
            self.debugManager = None
        self.scriptSite = None
        self.scriptCodeBlocks = {}
        self.persistLoaded = 0

    def AddNamedItem(self, name, flags):
        if self.scriptSite is None:
            raise COMException(scode=winerror.E_INVALIDARG)
        try:
            unknown = self.scriptSite.GetItemInfo(name, axscript.SCRIPTINFO_IUNKNOWN)[0]
            dispatch = unknown.QueryInterface(pythoncom.IID_IDispatch)
        except pythoncom.com_error:
            raise COMException(
                scode=winerror.E_NOINTERFACE,
                desc="Object has no dispatch interface available.",
            )
        newItem = self.subItems[name] = self.GetNamedItemClass()(
            self, name, dispatch, flags
        )
        if newItem.IsGlobal():
            newItem.CreateConnections()

    def GetScriptDispatch(self, name):
        # Base classes should override.
        raise COMException(scode=winerror.E_NOTIMPL)

    def GetCurrentScriptThreadID(self):
        return self.baseThreadId

    def GetScriptThreadID(self, win32ThreadId):
        if self.baseThreadId == -1:
            raise COMException(scode=winerror.E_UNEXPECTED)
        if self.baseThreadId != win32ThreadId:
            raise COMException(scode=winerror.E_INVALIDARG)
        return self.baseThreadId

    def GetScriptThreadState(self, scriptThreadId):
        if self.baseThreadId == -1:
            raise COMException(scode=winerror.E_UNEXPECTED)
        if scriptThreadId != self.baseThreadId:
            raise COMException(scode=winerror.E_INVALIDARG)
        return self.threadState

    def AddTypeLib(self, uuid, major, minor, flags):
        # Get the win32com gencache to register this library.
        from win32com.client import gencache

        gencache.EnsureModule(uuid, self.lcid, major, minor, bForDemand=1)

    # This is never called by the C++ framework - it does magic.
    # See PyGActiveScript.cpp
    # def InterruptScriptThread(self, stidThread, exc_info, flags):
    # 	raise COMException("Not Implemented", scode=winerror.E_NOTIMPL)

    def Clone(self):
        raise COMException("Not Implemented", scode=winerror.E_NOTIMPL)

    #
    # IObjectSafety

    # Note that IE seems to insist we say we support all the flags, even tho
    # we don't accept them all.  If unknown flags come in, they are ignored, and never
    # reflected in GetInterfaceSafetyOptions and the QIs obviously fail, but still IE
    # allows our engine to initialize.
    def SetInterfaceSafetyOptions(self, iid, optionsMask, enabledOptions):
        # 		trace ("SetInterfaceSafetyOptions", iid, optionsMask, enabledOptions)
        if optionsMask & enabledOptions == 0:
            return

        # See comments above.
        # 		if (optionsMask & enabledOptions & \
        # 			~(axscript.INTERFACESAFE_FOR_UNTRUSTED_DATA | axscript.INTERFACESAFE_FOR_UNTRUSTED_CALLER)):
        # 			# request for options we don't understand
        # 			RaiseAssert(scode=winerror.E_FAIL, desc="Unknown safety options")

        if iid in [
            pythoncom.IID_IPersist,
            pythoncom.IID_IPersistStream,
            pythoncom.IID_IPersistStreamInit,
            axscript.IID_IActiveScript,
            axscript.IID_IActiveScriptParse,
        ]:
            supported = self._GetSupportedInterfaceSafetyOptions()
            self.safetyOptions = supported & optionsMask & enabledOptions
        else:
            raise COMException(scode=winerror.E_NOINTERFACE)

    def _GetSupportedInterfaceSafetyOptions(self):
        return 0

    def GetInterfaceSafetyOptions(self, iid):
        if iid in [
            pythoncom.IID_IPersist,
            pythoncom.IID_IPersistStream,
            pythoncom.IID_IPersistStreamInit,
            axscript.IID_IActiveScript,
            axscript.IID_IActiveScriptParse,
        ]:
            supported = self._GetSupportedInterfaceSafetyOptions()
            return supported, self.safetyOptions
        else:
            raise COMException(scode=winerror.E_NOINTERFACE)

    #
    # Other helpers.
    def ExecutePendingScripts(self):
        self.RegisterNewNamedItems()
        self.DoExecutePendingScripts()

    def ProcessScriptItemEvent(self, item, event, lcid, wFlags, args):
        # 		trace("ProcessScriptItemEvent", item, event, lcid, wFlags, args)
        self.RegisterNewNamedItems()
        return self.DoProcessScriptItemEvent(item, event, lcid, wFlags, args)

    def _DumpNamedItems_(self):
        for item in self.subItems.values():
            item._dump_(0)

    def ResetNamedItems(self):
        # Due to the way we work, we re-create persistent ones.
        existing = self.subItems
        self.subItems = {}
        for item in existing.values():
            item.Close()
            if item.flags & axscript.SCRIPTITEM_ISPERSISTENT:
                self.AddNamedItem(item.name, item.flags)

    def GetCurrentSafetyOptions(self):
        return self.safetyOptions

    def ProcessNewNamedItemsConnections(self):
        # Process all sub-items.
        for item in self.subItems.values():
            if not item.createdConnections:  # Fast-track!
                item.CreateConnections()

    def RegisterNewNamedItems(self):
        # Register all sub-items.
        for item in self.subItems.values():
            if not item.isRegistered:  # Fast-track!
                self.RegisterNamedItem(item)

    def RegisterNamedItem(self, item):
        item.Register()

    def CheckConnectedOrDisconnected(self):
        if self.scriptState in [
            axscript.SCRIPTSTATE_CONNECTED,
            axscript.SCRIPTSTATE_DISCONNECTED,
        ]:
            return
        RaiseAssert(
            winerror.E_UNEXPECTED,
            "Not connected or disconnected - %d" % self.scriptState,
        )

    def Connect(self):
        self.ProcessNewNamedItemsConnections()
        self.RegisterNewNamedItems()
        self.ConnectEventHandlers()

    def Run(self):
        # 		trace("AXScript running...")
        if (
            self.scriptState != axscript.SCRIPTSTATE_INITIALIZED
            and self.scriptState != axscript.SCRIPTSTATE_STARTED
        ):
            raise COMException(scode=winerror.E_UNEXPECTED)
        # 		self._DumpNamedItems_()
        self.ExecutePendingScripts()
        self.DoRun()

    def Stop(self):
        # Stop all executing scripts, and disconnect.
        if self.scriptState == axscript.SCRIPTSTATE_CONNECTED:
            self.Disconnect()
        # Reset back to initialized.
        self.Reset()

    def Disconnect(self):
        self.CheckConnectedOrDisconnected()
        try:
            self.DisconnectEventHandlers()
        except pythoncom.com_error:
            # Ignore errors when disconnecting.
            pass

        self.ChangeScriptState(axscript.SCRIPTSTATE_DISCONNECTED)

    def ConnectEventHandlers(self):
        # 		trace ("Connecting to event handlers")
        for item in self.subItems.values():
            item.Connect()
        self.ChangeScriptState(axscript.SCRIPTSTATE_CONNECTED)

    def DisconnectEventHandlers(self):
        # 		trace ("Disconnecting from event handlers")
        for item in self.subItems.values():
            item.Disconnect()

    def Reset(self):
        # Keeping persistent engine state, reset back an initialized state
        self.ResetNamedItems()
        self.ChangeScriptState(axscript.SCRIPTSTATE_INITIALIZED)

    def ChangeScriptState(self, state):
        # print(f"  ChangeScriptState with {state_map.get(state)} - currentstate = {state_map.get(self.scriptState)}")
        self.DisableInterrupts()
        try:
            self.scriptState = state
            try:
                if self.scriptSite:
                    self.scriptSite.OnStateChange(state)
            except pythoncom.com_error as xxx_todo_changeme:
                (hr, desc, exc, arg) = xxx_todo_changeme.args
        finally:
            self.EnableInterrupts()

    # This stack frame is debugged - therefore we do as little as possible in it.
    def _ApplyInScriptedSection(self, fn, args):
        if self.debugManager:
            self.debugManager.OnEnterScript()
            if self.debugManager.adb.appDebugger:
                return self.debugManager.adb.runcall(fn, *args)
            else:
                return fn(*args)
        else:
            return fn(*args)

    def ApplyInScriptedSection(self, codeBlock: AXScriptCodeBlock | None, fn, args):
        self.BeginScriptedSection()
        try:
            try:
                # print("ApplyInSS", codeBlock, fn, args)
                return self._ApplyInScriptedSection(fn, args)
            finally:
                if self.debugManager:
                    self.debugManager.OnLeaveScript()
                self.EndScriptedSection()
        except:
            self.HandleException(codeBlock)

    # This stack frame is debugged - therefore we do as little as possible in it.
    def _CompileInScriptedSection(self, code, name, type):
        if self.debugManager:
            self.debugManager.OnEnterScript()
        return compile(code, name, type)

    def CompileInScriptedSection(
        self, codeBlock: AXScriptCodeBlock, type, realCode=None
    ):
        if codeBlock.codeObject is not None:  # already compiled
            return 1
        if realCode is None:
            code = codeBlock.codeText
        else:
            code = realCode
        name = codeBlock.GetFileName()
        self.BeginScriptedSection()
        try:
            try:
                codeObject = self._CompileInScriptedSection(RemoveCR(code), name, type)
                codeBlock.codeObject = codeObject
                return 1
            finally:
                if self.debugManager:
                    self.debugManager.OnLeaveScript()
                self.EndScriptedSection()
        except:
            self.HandleException(codeBlock)

    # This stack frame is debugged - therefore we do as little as possible in it.
    def _ExecInScriptedSection(self, codeObject, globals, locals=None):
        if self.debugManager:
            self.debugManager.OnEnterScript()
            if self.debugManager.adb.appDebugger:
                return self.debugManager.adb.run(codeObject, globals, locals)
            else:
                exec(codeObject, globals, locals)
        else:
            exec(codeObject, globals, locals)

    def ExecInScriptedSection(self, codeBlock: AXScriptCodeBlock, globals, locals=None):
        if locals is None:
            locals = globals
        assert (
            not codeBlock.beenExecuted
        ), "This code block should not have been executed"
        codeBlock.beenExecuted = 1
        self.BeginScriptedSection()
        try:
            try:
                self._ExecInScriptedSection(codeBlock.codeObject, globals, locals)
            finally:
                if self.debugManager:
                    self.debugManager.OnLeaveScript()
                self.EndScriptedSection()
        except:
            self.HandleException(codeBlock)

    def _EvalInScriptedSection(self, codeBlock, globals, locals=None):
        if self.debugManager:
            self.debugManager.OnEnterScript()
            if self.debugManager.adb.appDebugger:
                return self.debugManager.adb.runeval(codeBlock, globals, locals)
            else:
                return eval(codeBlock, globals, locals)
        else:
            return eval(codeBlock, globals, locals)

    def EvalInScriptedSection(self, codeBlock, globals, locals=None):
        if locals is None:
            locals = globals
        assert (
            not codeBlock.beenExecuted
        ), "This code block should not have been executed"
        codeBlock.beenExecuted = 1
        self.BeginScriptedSection()
        try:
            try:
                return self._EvalInScriptedSection(
                    codeBlock.codeObject, globals, locals
                )
            finally:
                if self.debugManager:
                    self.debugManager.OnLeaveScript()
                self.EndScriptedSection()
        except:
            self.HandleException(codeBlock)

    def HandleException(self, codeBlock: AXScriptCodeBlock | None) -> NoReturn:
        """Never returns - raises a ComException"""
        exc_type, exc_value, *_ = sys.exc_info()
        # If a SERVER exception, re-raise it.  If a client side COM error, it is
        # likely to have originated from the script code itself, and therefore
        # needs to be reported like any other exception.
        if IsCOMServerException(exc_type):
            # Ensure the traceback doesn't cause a cycle.
            raise
        # It could be an error by another script.
        if (
            isinstance(exc_value, pythoncom.com_error)
            and exc_value.hresult == axscript.SCRIPT_E_REPORTED
        ):
            # Ensure the traceback doesn't cause a cycle.
            raise COMException(scode=exc_value.hresult)

        exception = error.AXScriptException(self, codeBlock, exc_value=exc_value)

        # Ensure the traceback doesn't cause a cycle.
        result_exception = error.ProcessAXScriptException(
            self.scriptSite, self.debugManager, exception
        )
        if result_exception is not None:
            try:
                self.scriptSite.OnScriptTerminate(None, result_exception)
            except pythoncom.com_error:
                pass  # Ignore errors telling engine we stopped.
            # reset ourselves to 'connected' so further events continue to fire.
            self.SetScriptState(axscript.SCRIPTSTATE_CONNECTED)
            raise result_exception
        # I think that in some cases this should just return - but the code
        # that could return None above is disabled, so it never happens.
        RaiseAssert(
            winerror.E_UNEXPECTED, "Don't have an exception to raise to the caller!"
        )

    def BeginScriptedSection(self):
        if self.scriptSite is None:
            raise COMException(scode=winerror.E_UNEXPECTED)
        self.scriptSite.OnEnterScript()

    def EndScriptedSection(self):
        if self.scriptSite is None:
            raise COMException(scode=winerror.E_UNEXPECTED)
        self.scriptSite.OnLeaveScript()

    def DisableInterrupts(self):
        pass

    def EnableInterrupts(self):
        pass

    def GetNamedItem(self, name):
        try:
            return self.subItems[name]
        except KeyError:
            raise COMException(scode=winerror.E_INVALIDARG)

    def GetNamedItemClass(self):
        return ScriptItem

    def _AddScriptCodeBlock(self, codeBlock):
        self.scriptCodeBlocks[codeBlock.GetFileName()] = codeBlock
        if self.debugManager:
            self.debugManager.AddScriptBlock(codeBlock)


if __name__ == "__main__":
    print("This is a framework class - please use pyscript.py etc")


def dumptypeinfo(typeinfo):
    return
    attr = typeinfo.GetTypeAttr()
    # Loop over all methods
    print("Methods")
    for j in range(attr[6]):
        fdesc = list(typeinfo.GetFuncDesc(j))
        id = fdesc[0]
        try:
            names = typeinfo.GetNames(id)
        except pythoncom.ole_error:
            names = None
        doc = typeinfo.GetDocumentation(id)

        print(" ", names, "has attr", fdesc)

    # Loop over all variables (ie, properties)
    print("Variables")
    for j in range(attr[7]):
        fdesc = list(typeinfo.GetVarDesc(j))
        names = typeinfo.GetNames(id)
        print(" ", names, "has attr", fdesc)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\descriptor.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Descriptors essentially contain exactly the information found in a .proto
file, in types that make this information accessible in Python.
"""

__author__ = 'robinson@google.com (Will Robinson)'

import threading
import warnings

from google.protobuf.internal import api_implementation

_USE_C_DESCRIPTORS = False
if api_implementation.Type() != 'python':
  # Used by MakeDescriptor in cpp mode
  import binascii
  import os
  # pylint: disable=protected-access
  _message = api_implementation._c_module
  # TODO: Remove this import after fix api_implementation
  if _message is None:
    from google.protobuf.pyext import _message
  _USE_C_DESCRIPTORS = True


class Error(Exception):
  """Base error for this module."""


class TypeTransformationError(Error):
  """Error transforming between python proto type and corresponding C++ type."""


if _USE_C_DESCRIPTORS:
  # This metaclass allows to override the behavior of code like
  #     isinstance(my_descriptor, FieldDescriptor)
  # and make it return True when the descriptor is an instance of the extension
  # type written in C++.
  class DescriptorMetaclass(type):

    def __instancecheck__(cls, obj):
      if super(DescriptorMetaclass, cls).__instancecheck__(obj):
        return True
      if isinstance(obj, cls._C_DESCRIPTOR_CLASS):
        return True
      return False
else:
  # The standard metaclass; nothing changes.
  DescriptorMetaclass = type


class _Lock(object):
  """Wrapper class of threading.Lock(), which is allowed by 'with'."""

  def __new__(cls):
    self = object.__new__(cls)
    self._lock = threading.Lock()  # pylint: disable=protected-access
    return self

  def __enter__(self):
    self._lock.acquire()

  def __exit__(self, exc_type, exc_value, exc_tb):
    self._lock.release()


_lock = threading.Lock()


def _Deprecated(name):
  if _Deprecated.count > 0:
    _Deprecated.count -= 1
    warnings.warn(
        'Call to deprecated create function %s(). Note: Create unlinked '
        'descriptors is going to go away. Please use get/find descriptors from '
        'generated code or query the descriptor_pool.'
        % name,
        category=DeprecationWarning, stacklevel=3)


# Deprecated warnings will print 100 times at most which should be enough for
# users to notice and do not cause timeout.
_Deprecated.count = 100


_internal_create_key = object()


class DescriptorBase(metaclass=DescriptorMetaclass):

  """Descriptors base class.

  This class is the base of all descriptor classes. It provides common options
  related functionality.

  Attributes:
    has_options:  True if the descriptor has non-default options.  Usually it is
      not necessary to read this -- just call GetOptions() which will happily
      return the default instance.  However, it's sometimes useful for
      efficiency, and also useful inside the protobuf implementation to avoid
      some bootstrapping issues.
    file (FileDescriptor): Reference to file info.
  """

  if _USE_C_DESCRIPTORS:
    # The class, or tuple of classes, that are considered as "virtual
    # subclasses" of this descriptor class.
    _C_DESCRIPTOR_CLASS = ()

  def __init__(self, file, options, serialized_options, options_class_name):
    """Initialize the descriptor given its options message and the name of the
    class of the options message. The name of the class is required in case
    the options message is None and has to be created.
    """
    self.file = file
    self._options = options
    self._options_class_name = options_class_name
    self._serialized_options = serialized_options

    # Does this descriptor have non-default options?
    self.has_options = (self._options is not None) or (
        self._serialized_options is not None
    )

  def _SetOptions(self, options, options_class_name):
    """Sets the descriptor's options

    This function is used in generated proto2 files to update descriptor
    options. It must not be used outside proto2.
    """
    self._options = options
    self._options_class_name = options_class_name

    # Does this descriptor have non-default options?
    self.has_options = options is not None

  def GetOptions(self):
    """Retrieves descriptor options.

    This method returns the options set or creates the default options for the
    descriptor.
    """
    if self._options:
      return self._options

    from google.protobuf import descriptor_pb2
    try:
      options_class = getattr(descriptor_pb2,
                              self._options_class_name)
    except AttributeError:
      raise RuntimeError('Unknown options class name %s!' %
                         (self._options_class_name))

    if self._serialized_options is None:
      with _lock:
        self._options = options_class()
    else:
      options = _ParseOptions(options_class(), self._serialized_options)
      with _lock:
        self._options = options

    return self._options


class _NestedDescriptorBase(DescriptorBase):
  """Common class for descriptors that can be nested."""

  def __init__(self, options, options_class_name, name, full_name,
               file, containing_type, serialized_start=None,
               serialized_end=None, serialized_options=None):
    """Constructor.

    Args:
      options: Protocol message options or None to use default message options.
      options_class_name (str): The class name of the above options.
      name (str): Name of this protocol message type.
      full_name (str): Fully-qualified name of this protocol message type, which
        will include protocol "package" name and the name of any enclosing
        types.
      containing_type: if provided, this is a nested descriptor, with this
        descriptor as parent, otherwise None.
      serialized_start: The start index (inclusive) in block in the
        file.serialized_pb that describes this descriptor.
      serialized_end: The end index (exclusive) in block in the
        file.serialized_pb that describes this descriptor.
      serialized_options: Protocol message serialized options or None.
    """
    super(_NestedDescriptorBase, self).__init__(
        file, options, serialized_options, options_class_name
    )

    self.name = name
    # TODO: Add function to calculate full_name instead of having it in
    #             memory?
    self.full_name = full_name
    self.containing_type = containing_type

    self._serialized_start = serialized_start
    self._serialized_end = serialized_end

  def CopyToProto(self, proto):
    """Copies this to the matching proto in descriptor_pb2.

    Args:
      proto: An empty proto instance from descriptor_pb2.

    Raises:
      Error: If self couldn't be serialized, due to to few constructor
        arguments.
    """
    if (self.file is not None and
        self._serialized_start is not None and
        self._serialized_end is not None):
      proto.ParseFromString(self.file.serialized_pb[
          self._serialized_start:self._serialized_end])
    else:
      raise Error('Descriptor does not contain serialization.')


class Descriptor(_NestedDescriptorBase):

  """Descriptor for a protocol message type.

  Attributes:
      name (str): Name of this protocol message type.
      full_name (str): Fully-qualified name of this protocol message type,
          which will include protocol "package" name and the name of any
          enclosing types.
      containing_type (Descriptor): Reference to the descriptor of the type
          containing us, or None if this is top-level.
      fields (list[FieldDescriptor]): Field descriptors for all fields in
          this type.
      fields_by_number (dict(int, FieldDescriptor)): Same
          :class:`FieldDescriptor` objects as in :attr:`fields`, but indexed
          by "number" attribute in each FieldDescriptor.
      fields_by_name (dict(str, FieldDescriptor)): Same
          :class:`FieldDescriptor` objects as in :attr:`fields`, but indexed by
          "name" attribute in each :class:`FieldDescriptor`.
      nested_types (list[Descriptor]): Descriptor references
          for all protocol message types nested within this one.
      nested_types_by_name (dict(str, Descriptor)): Same Descriptor
          objects as in :attr:`nested_types`, but indexed by "name" attribute
          in each Descriptor.
      enum_types (list[EnumDescriptor]): :class:`EnumDescriptor` references
          for all enums contained within this type.
      enum_types_by_name (dict(str, EnumDescriptor)): Same
          :class:`EnumDescriptor` objects as in :attr:`enum_types`, but
          indexed by "name" attribute in each EnumDescriptor.
      enum_values_by_name (dict(str, EnumValueDescriptor)): Dict mapping
          from enum value name to :class:`EnumValueDescriptor` for that value.
      extensions (list[FieldDescriptor]): All extensions defined directly
          within this message type (NOT within a nested type).
      extensions_by_name (dict(str, FieldDescriptor)): Same FieldDescriptor
          objects as :attr:`extensions`, but indexed by "name" attribute of each
          FieldDescriptor.
      is_extendable (bool):  Does this type define any extension ranges?
      oneofs (list[OneofDescriptor]): The list of descriptors for oneof fields
          in this message.
      oneofs_by_name (dict(str, OneofDescriptor)): Same objects as in
          :attr:`oneofs`, but indexed by "name" attribute.
      file (FileDescriptor): Reference to file descriptor.
      is_map_entry: If the message type is a map entry.

  """

  if _USE_C_DESCRIPTORS:
    _C_DESCRIPTOR_CLASS = _message.Descriptor

    def __new__(
        cls,
        name=None,
        full_name=None,
        filename=None,
        containing_type=None,
        fields=None,
        nested_types=None,
        enum_types=None,
        extensions=None,
        options=None,
        serialized_options=None,
        is_extendable=True,
        extension_ranges=None,
        oneofs=None,
        file=None,  # pylint: disable=redefined-builtin
        serialized_start=None,
        serialized_end=None,
        syntax=None,
        is_map_entry=False,
        create_key=None):
      _message.Message._CheckCalledFromGeneratedFile()
      return _message.default_pool.FindMessageTypeByName(full_name)

  # NOTE: The file argument redefining a builtin is nothing we can
  # fix right now since we don't know how many clients already rely on the
  # name of the argument.
  def __init__(self, name, full_name, filename, containing_type, fields,
               nested_types, enum_types, extensions, options=None,
               serialized_options=None,
               is_extendable=True, extension_ranges=None, oneofs=None,
               file=None, serialized_start=None, serialized_end=None,  # pylint: disable=redefined-builtin
               syntax=None, is_map_entry=False, create_key=None):
    """Arguments to __init__() are as described in the description
    of Descriptor fields above.

    Note that filename is an obsolete argument, that is not used anymore.
    Please use file.name to access this as an attribute.
    """
    if create_key is not _internal_create_key:
      _Deprecated('Descriptor')

    super(Descriptor, self).__init__(
        options, 'MessageOptions', name, full_name, file,
        containing_type, serialized_start=serialized_start,
        serialized_end=serialized_end, serialized_options=serialized_options)

    # We have fields in addition to fields_by_name and fields_by_number,
    # so that:
    #   1. Clients can index fields by "order in which they're listed."
    #   2. Clients can easily iterate over all fields with the terse
    #      syntax: for f in descriptor.fields: ...
    self.fields = fields
    for field in self.fields:
      field.containing_type = self
    self.fields_by_number = dict((f.number, f) for f in fields)
    self.fields_by_name = dict((f.name, f) for f in fields)
    self._fields_by_camelcase_name = None

    self.nested_types = nested_types
    for nested_type in nested_types:
      nested_type.containing_type = self
    self.nested_types_by_name = dict((t.name, t) for t in nested_types)

    self.enum_types = enum_types
    for enum_type in self.enum_types:
      enum_type.containing_type = self
    self.enum_types_by_name = dict((t.name, t) for t in enum_types)
    self.enum_values_by_name = dict(
        (v.name, v) for t in enum_types for v in t.values)

    self.extensions = extensions
    for extension in self.extensions:
      extension.extension_scope = self
    self.extensions_by_name = dict((f.name, f) for f in extensions)
    self.is_extendable = is_extendable
    self.extension_ranges = extension_ranges
    self.oneofs = oneofs if oneofs is not None else []
    self.oneofs_by_name = dict((o.name, o) for o in self.oneofs)
    for oneof in self.oneofs:
      oneof.containing_type = self
    self._deprecated_syntax = syntax or "proto2"
    self._is_map_entry = is_map_entry

  @property
  def syntax(self):
    warnings.warn(
      'descriptor.syntax is deprecated. It will be removed'
      ' soon. Most usages are checking field descriptors. Consider to use'
      ' has_presence, is_packed on field descriptors.'
    )
    return self._deprecated_syntax

  @property
  def fields_by_camelcase_name(self):
    """Same FieldDescriptor objects as in :attr:`fields`, but indexed by
    :attr:`FieldDescriptor.camelcase_name`.
    """
    if self._fields_by_camelcase_name is None:
      self._fields_by_camelcase_name = dict(
          (f.camelcase_name, f) for f in self.fields)
    return self._fields_by_camelcase_name

  def EnumValueName(self, enum, value):
    """Returns the string name of an enum value.

    This is just a small helper method to simplify a common operation.

    Args:
      enum: string name of the Enum.
      value: int, value of the enum.

    Returns:
      string name of the enum value.

    Raises:
      KeyError if either the Enum doesn't exist or the value is not a valid
        value for the enum.
    """
    return self.enum_types_by_name[enum].values_by_number[value].name

  def CopyToProto(self, proto):
    """Copies this to a descriptor_pb2.DescriptorProto.

    Args:
      proto: An empty descriptor_pb2.DescriptorProto.
    """
    # This function is overridden to give a better doc comment.
    super(Descriptor, self).CopyToProto(proto)


# TODO: We should have aggressive checking here,
# for example:
#   * If you specify a repeated field, you should not be allowed
#     to specify a default value.
#   * [Other examples here as needed].
#
# TODO: for this and other *Descriptor classes, we
# might also want to lock things down aggressively (e.g.,
# prevent clients from setting the attributes).  Having
# stronger invariants here in general will reduce the number
# of runtime checks we must do in reflection.py...
class FieldDescriptor(DescriptorBase):

  """Descriptor for a single field in a .proto file.

  Attributes:
    name (str): Name of this field, exactly as it appears in .proto.
    full_name (str): Name of this field, including containing scope.  This is
      particularly relevant for extensions.
    index (int): Dense, 0-indexed index giving the order that this
      field textually appears within its message in the .proto file.
    number (int): Tag number declared for this field in the .proto file.

    type (int): (One of the TYPE_* constants below) Declared type.
    cpp_type (int): (One of the CPPTYPE_* constants below) C++ type used to
      represent this field.

    label (int): (One of the LABEL_* constants below) Tells whether this
      field is optional, required, or repeated.
    has_default_value (bool): True if this field has a default value defined,
      otherwise false.
    default_value (Varies): Default value of this field.  Only
      meaningful for non-repeated scalar fields.  Repeated fields
      should always set this to [], and non-repeated composite
      fields should always set this to None.

    containing_type (Descriptor): Descriptor of the protocol message
      type that contains this field.  Set by the Descriptor constructor
      if we're passed into one.
      Somewhat confusingly, for extension fields, this is the
      descriptor of the EXTENDED message, not the descriptor
      of the message containing this field.  (See is_extension and
      extension_scope below).
    message_type (Descriptor): If a composite field, a descriptor
      of the message type contained in this field.  Otherwise, this is None.
    enum_type (EnumDescriptor): If this field contains an enum, a
      descriptor of that enum.  Otherwise, this is None.

    is_extension: True iff this describes an extension field.
    extension_scope (Descriptor): Only meaningful if is_extension is True.
      Gives the message that immediately contains this extension field.
      Will be None iff we're a top-level (file-level) extension field.

    options (descriptor_pb2.FieldOptions): Protocol message field options or
      None to use default field options.

    containing_oneof (OneofDescriptor): If the field is a member of a oneof
      union, contains its descriptor. Otherwise, None.

    file (FileDescriptor): Reference to file descriptor.
  """

  # Must be consistent with C++ FieldDescriptor::Type enum in
  # descriptor.h.
  #
  # TODO: Find a way to eliminate this repetition.
  TYPE_DOUBLE         = 1
  TYPE_FLOAT          = 2
  TYPE_INT64          = 3
  TYPE_UINT64         = 4
  TYPE_INT32          = 5
  TYPE_FIXED64        = 6
  TYPE_FIXED32        = 7
  TYPE_BOOL           = 8
  TYPE_STRING         = 9
  TYPE_GROUP          = 10
  TYPE_MESSAGE        = 11
  TYPE_BYTES          = 12
  TYPE_UINT32         = 13
  TYPE_ENUM           = 14
  TYPE_SFIXED32       = 15
  TYPE_SFIXED64       = 16
  TYPE_SINT32         = 17
  TYPE_SINT64         = 18
  MAX_TYPE            = 18

  # Must be consistent with C++ FieldDescriptor::CppType enum in
  # descriptor.h.
  #
  # TODO: Find a way to eliminate this repetition.
  CPPTYPE_INT32       = 1
  CPPTYPE_INT64       = 2
  CPPTYPE_UINT32      = 3
  CPPTYPE_UINT64      = 4
  CPPTYPE_DOUBLE      = 5
  CPPTYPE_FLOAT       = 6
  CPPTYPE_BOOL        = 7
  CPPTYPE_ENUM        = 8
  CPPTYPE_STRING      = 9
  CPPTYPE_MESSAGE     = 10
  MAX_CPPTYPE         = 10

  _PYTHON_TO_CPP_PROTO_TYPE_MAP = {
      TYPE_DOUBLE: CPPTYPE_DOUBLE,
      TYPE_FLOAT: CPPTYPE_FLOAT,
      TYPE_ENUM: CPPTYPE_ENUM,
      TYPE_INT64: CPPTYPE_INT64,
      TYPE_SINT64: CPPTYPE_INT64,
      TYPE_SFIXED64: CPPTYPE_INT64,
      TYPE_UINT64: CPPTYPE_UINT64,
      TYPE_FIXED64: CPPTYPE_UINT64,
      TYPE_INT32: CPPTYPE_INT32,
      TYPE_SFIXED32: CPPTYPE_INT32,
      TYPE_SINT32: CPPTYPE_INT32,
      TYPE_UINT32: CPPTYPE_UINT32,
      TYPE_FIXED32: CPPTYPE_UINT32,
      TYPE_BYTES: CPPTYPE_STRING,
      TYPE_STRING: CPPTYPE_STRING,
      TYPE_BOOL: CPPTYPE_BOOL,
      TYPE_MESSAGE: CPPTYPE_MESSAGE,
      TYPE_GROUP: CPPTYPE_MESSAGE
      }

  # Must be consistent with C++ FieldDescriptor::Label enum in
  # descriptor.h.
  #
  # TODO: Find a way to eliminate this repetition.
  LABEL_OPTIONAL      = 1
  LABEL_REQUIRED      = 2
  LABEL_REPEATED      = 3
  MAX_LABEL           = 3

  # Must be consistent with C++ constants kMaxNumber, kFirstReservedNumber,
  # and kLastReservedNumber in descriptor.h
  MAX_FIELD_NUMBER = (1 << 29) - 1
  FIRST_RESERVED_FIELD_NUMBER = 19000
  LAST_RESERVED_FIELD_NUMBER = 19999

  if _USE_C_DESCRIPTORS:
    _C_DESCRIPTOR_CLASS = _message.FieldDescriptor

    def __new__(cls, name, full_name, index, number, type, cpp_type, label,
                default_value, message_type, enum_type, containing_type,
                is_extension, extension_scope, options=None,
                serialized_options=None,
                has_default_value=True, containing_oneof=None, json_name=None,
                file=None, create_key=None):  # pylint: disable=redefined-builtin
      _message.Message._CheckCalledFromGeneratedFile()
      if is_extension:
        return _message.default_pool.FindExtensionByName(full_name)
      else:
        return _message.default_pool.FindFieldByName(full_name)

  def __init__(self, name, full_name, index, number, type, cpp_type, label,
               default_value, message_type, enum_type, containing_type,
               is_extension, extension_scope, options=None,
               serialized_options=None,
               has_default_value=True, containing_oneof=None, json_name=None,
               file=None, create_key=None):  # pylint: disable=redefined-builtin
    """The arguments are as described in the description of FieldDescriptor
    attributes above.

    Note that containing_type may be None, and may be set later if necessary
    (to deal with circular references between message types, for example).
    Likewise for extension_scope.
    """
    if create_key is not _internal_create_key:
      _Deprecated('FieldDescriptor')

    super(FieldDescriptor, self).__init__(
        file, options, serialized_options, 'FieldOptions'
    )
    self.name = name
    self.full_name = full_name
    self._camelcase_name = None
    if json_name is None:
      self.json_name = _ToJsonName(name)
    else:
      self.json_name = json_name
    self.index = index
    self.number = number
    self.type = type
    self.cpp_type = cpp_type
    self.label = label
    self.has_default_value = has_default_value
    self.default_value = default_value
    self.containing_type = containing_type
    self.message_type = message_type
    self.enum_type = enum_type
    self.is_extension = is_extension
    self.extension_scope = extension_scope
    self.containing_oneof = containing_oneof
    if api_implementation.Type() == 'python':
      self._cdescriptor = None
    else:
      if is_extension:
        self._cdescriptor = _message.default_pool.FindExtensionByName(full_name)
      else:
        self._cdescriptor = _message.default_pool.FindFieldByName(full_name)

  @property
  def camelcase_name(self):
    """Camelcase name of this field.

    Returns:
      str: the name in CamelCase.
    """
    if self._camelcase_name is None:
      self._camelcase_name = _ToCamelCase(self.name)
    return self._camelcase_name

  @property
  def has_presence(self):
    """Whether the field distinguishes between unpopulated and default values.

    Raises:
      RuntimeError: singular field that is not linked with message nor file.
    """
    if self.label == FieldDescriptor.LABEL_REPEATED:
      return False
    if (self.cpp_type == FieldDescriptor.CPPTYPE_MESSAGE or
        self.containing_oneof):
      return True
    # self.containing_type is used here instead of self.file for legacy
    # compatibility. FieldDescriptor.file was added in cl/153110619
    # Some old/generated code didn't link file to FieldDescriptor.
    # TODO: remove syntax usage b/240619313
    return self.containing_type._deprecated_syntax == 'proto2'

  @property
  def is_packed(self):
    """Returns if the field is packed."""
    if self.label != FieldDescriptor.LABEL_REPEATED:
      return False
    field_type = self.type
    if (field_type == FieldDescriptor.TYPE_STRING or
        field_type == FieldDescriptor.TYPE_GROUP or
        field_type == FieldDescriptor.TYPE_MESSAGE or
        field_type == FieldDescriptor.TYPE_BYTES):
      return False
    if self.containing_type._deprecated_syntax == 'proto2':
      return self.has_options and self.GetOptions().packed
    else:
      return (not self.has_options or
              not self.GetOptions().HasField('packed') or
              self.GetOptions().packed)

  @staticmethod
  def ProtoTypeToCppProtoType(proto_type):
    """Converts from a Python proto type to a C++ Proto Type.

    The Python ProtocolBuffer classes specify both the 'Python' datatype and the
    'C++' datatype - and they're not the same. This helper method should
    translate from one to another.

    Args:
      proto_type: the Python proto type (descriptor.FieldDescriptor.TYPE_*)
    Returns:
      int: descriptor.FieldDescriptor.CPPTYPE_*, the C++ type.
    Raises:
      TypeTransformationError: when the Python proto type isn't known.
    """
    try:
      return FieldDescriptor._PYTHON_TO_CPP_PROTO_TYPE_MAP[proto_type]
    except KeyError:
      raise TypeTransformationError('Unknown proto_type: %s' % proto_type)


class EnumDescriptor(_NestedDescriptorBase):

  """Descriptor for an enum defined in a .proto file.

  Attributes:
    name (str): Name of the enum type.
    full_name (str): Full name of the type, including package name
      and any enclosing type(s).

    values (list[EnumValueDescriptor]): List of the values
      in this enum.
    values_by_name (dict(str, EnumValueDescriptor)): Same as :attr:`values`,
      but indexed by the "name" field of each EnumValueDescriptor.
    values_by_number (dict(int, EnumValueDescriptor)): Same as :attr:`values`,
      but indexed by the "number" field of each EnumValueDescriptor.
    containing_type (Descriptor): Descriptor of the immediate containing
      type of this enum, or None if this is an enum defined at the
      top level in a .proto file.  Set by Descriptor's constructor
      if we're passed into one.
    file (FileDescriptor): Reference to file descriptor.
    options (descriptor_pb2.EnumOptions): Enum options message or
      None to use default enum options.
  """

  if _USE_C_DESCRIPTORS:
    _C_DESCRIPTOR_CLASS = _message.EnumDescriptor

    def __new__(cls, name, full_name, filename, values,
                containing_type=None, options=None,
                serialized_options=None, file=None,  # pylint: disable=redefined-builtin
                serialized_start=None, serialized_end=None, create_key=None):
      _message.Message._CheckCalledFromGeneratedFile()
      return _message.default_pool.FindEnumTypeByName(full_name)

  def __init__(self, name, full_name, filename, values,
               containing_type=None, options=None,
               serialized_options=None, file=None,  # pylint: disable=redefined-builtin
               serialized_start=None, serialized_end=None, create_key=None):
    """Arguments are as described in the attribute description above.

    Note that filename is an obsolete argument, that is not used anymore.
    Please use file.name to access this as an attribute.
    """
    if create_key is not _internal_create_key:
      _Deprecated('EnumDescriptor')

    super(EnumDescriptor, self).__init__(
        options, 'EnumOptions', name, full_name, file,
        containing_type, serialized_start=serialized_start,
        serialized_end=serialized_end, serialized_options=serialized_options)

    self.values = values
    for value in self.values:
      value.file = file
      value.type = self
    self.values_by_name = dict((v.name, v) for v in values)
    # Values are reversed to ensure that the first alias is retained.
    self.values_by_number = dict((v.number, v) for v in reversed(values))

  @property
  def is_closed(self):
    """Returns true whether this is a "closed" enum.

    This means that it:
    - Has a fixed set of values, rather than being equivalent to an int32.
    - Encountering values not in this set causes them to be treated as unknown
      fields.
    - The first value (i.e., the default) may be nonzero.

    WARNING: Some runtimes currently have a quirk where non-closed enums are
    treated as closed when used as the type of fields defined in a
    `syntax = proto2;` file. This quirk is not present in all runtimes; as of
    writing, we know that:

    - C++, Java, and C++-based Python share this quirk.
    - UPB and UPB-based Python do not.
    - PHP and Ruby treat all enums as open regardless of declaration.

    Care should be taken when using this function to respect the target
    runtime's enum handling quirks.
    """
    return self.file._deprecated_syntax == 'proto2'

  def CopyToProto(self, proto):
    """Copies this to a descriptor_pb2.EnumDescriptorProto.

    Args:
      proto (descriptor_pb2.EnumDescriptorProto): An empty descriptor proto.
    """
    # This function is overridden to give a better doc comment.
    super(EnumDescriptor, self).CopyToProto(proto)


class EnumValueDescriptor(DescriptorBase):

  """Descriptor for a single value within an enum.

  Attributes:
    name (str): Name of this value.
    index (int): Dense, 0-indexed index giving the order that this
      value appears textually within its enum in the .proto file.
    number (int): Actual number assigned to this enum value.
    type (EnumDescriptor): :class:`EnumDescriptor` to which this value
      belongs.  Set by :class:`EnumDescriptor`'s constructor if we're
      passed into one.
    options (descriptor_pb2.EnumValueOptions): Enum value options message or
      None to use default enum value options options.
  """

  if _USE_C_DESCRIPTORS:
    _C_DESCRIPTOR_CLASS = _message.EnumValueDescriptor

    def __new__(cls, name, index, number,
                type=None,  # pylint: disable=redefined-builtin
                options=None, serialized_options=None, create_key=None):
      _message.Message._CheckCalledFromGeneratedFile()
      # There is no way we can build a complete EnumValueDescriptor with the
      # given parameters (the name of the Enum is not known, for example).
      # Fortunately generated files just pass it to the EnumDescriptor()
      # constructor, which will ignore it, so returning None is good enough.
      return None

  def __init__(self, name, index, number,
               type=None,  # pylint: disable=redefined-builtin
               options=None, serialized_options=None, create_key=None):
    """Arguments are as described in the attribute description above."""
    if create_key is not _internal_create_key:
      _Deprecated('EnumValueDescriptor')

    super(EnumValueDescriptor, self).__init__(
        type.file if type else None,
        options,
        serialized_options,
        'EnumValueOptions',
    )
    self.name = name
    self.index = index
    self.number = number
    self.type = type


class OneofDescriptor(DescriptorBase):
  """Descriptor for a oneof field.

  Attributes:
    name (str): Name of the oneof field.
    full_name (str): Full name of the oneof field, including package name.
    index (int): 0-based index giving the order of the oneof field inside
      its containing type.
    containing_type (Descriptor): :class:`Descriptor` of the protocol message
      type that contains this field.  Set by the :class:`Descriptor` constructor
      if we're passed into one.
    fields (list[FieldDescriptor]): The list of field descriptors this
      oneof can contain.
  """

  if _USE_C_DESCRIPTORS:
    _C_DESCRIPTOR_CLASS = _message.OneofDescriptor

    def __new__(
        cls, name, full_name, index, containing_type, fields, options=None,
        serialized_options=None, create_key=None):
      _message.Message._CheckCalledFromGeneratedFile()
      return _message.default_pool.FindOneofByName(full_name)

  def __init__(
      self, name, full_name, index, containing_type, fields, options=None,
      serialized_options=None, create_key=None):
    """Arguments are as described in the attribute description above."""
    if create_key is not _internal_create_key:
      _Deprecated('OneofDescriptor')

    super(OneofDescriptor, self).__init__(
        containing_type.file if containing_type else None,
        options,
        serialized_options,
        'OneofOptions',
    )
    self.name = name
    self.full_name = full_name
    self.index = index
    self.containing_type = containing_type
    self.fields = fields


class ServiceDescriptor(_NestedDescriptorBase):

  """Descriptor for a service.

  Attributes:
    name (str): Name of the service.
    full_name (str): Full name of the service, including package name.
    index (int): 0-indexed index giving the order that this services
      definition appears within the .proto file.
    methods (list[MethodDescriptor]): List of methods provided by this
      service.
    methods_by_name (dict(str, MethodDescriptor)): Same
      :class:`MethodDescriptor` objects as in :attr:`methods_by_name`, but
      indexed by "name" attribute in each :class:`MethodDescriptor`.
    options (descriptor_pb2.ServiceOptions): Service options message or
      None to use default service options.
    file (FileDescriptor): Reference to file info.
  """

  if _USE_C_DESCRIPTORS:
    _C_DESCRIPTOR_CLASS = _message.ServiceDescriptor

    def __new__(
        cls,
        name=None,
        full_name=None,
        index=None,
        methods=None,
        options=None,
        serialized_options=None,
        file=None,  # pylint: disable=redefined-builtin
        serialized_start=None,
        serialized_end=None,
        create_key=None):
      _message.Message._CheckCalledFromGeneratedFile()  # pylint: disable=protected-access
      return _message.default_pool.FindServiceByName(full_name)

  def __init__(self, name, full_name, index, methods, options=None,
               serialized_options=None, file=None,  # pylint: disable=redefined-builtin
               serialized_start=None, serialized_end=None, create_key=None):
    if create_key is not _internal_create_key:
      _Deprecated('ServiceDescriptor')

    super(ServiceDescriptor, self).__init__(
        options, 'ServiceOptions', name, full_name, file,
        None, serialized_start=serialized_start,
        serialized_end=serialized_end, serialized_options=serialized_options)
    self.index = index
    self.methods = methods
    self.methods_by_name = dict((m.name, m) for m in methods)
    # Set the containing service for each method in this service.
    for method in self.methods:
      method.file = self.file
      method.containing_service = self

  def FindMethodByName(self, name):
    """Searches for the specified method, and returns its descriptor.

    Args:
      name (str): Name of the method.

    Returns:
      MethodDescriptor: The descriptor for the requested method.

    Raises:
      KeyError: if the method cannot be found in the service.
    """
    return self.methods_by_name[name]

  def CopyToProto(self, proto):
    """Copies this to a descriptor_pb2.ServiceDescriptorProto.

    Args:
      proto (descriptor_pb2.ServiceDescriptorProto): An empty descriptor proto.
    """
    # This function is overridden to give a better doc comment.
    super(ServiceDescriptor, self).CopyToProto(proto)


class MethodDescriptor(DescriptorBase):

  """Descriptor for a method in a service.

  Attributes:
    name (str): Name of the method within the service.
    full_name (str): Full name of method.
    index (int): 0-indexed index of the method inside the service.
    containing_service (ServiceDescriptor): The service that contains this
      method.
    input_type (Descriptor): The descriptor of the message that this method
      accepts.
    output_type (Descriptor): The descriptor of the message that this method
      returns.
    client_streaming (bool): Whether this method uses client streaming.
    server_streaming (bool): Whether this method uses server streaming.
    options (descriptor_pb2.MethodOptions or None): Method options message, or
      None to use default method options.
  """

  if _USE_C_DESCRIPTORS:
    _C_DESCRIPTOR_CLASS = _message.MethodDescriptor

    def __new__(cls,
                name,
                full_name,
                index,
                containing_service,
                input_type,
                output_type,
                client_streaming=False,
                server_streaming=False,
                options=None,
                serialized_options=None,
                create_key=None):
      _message.Message._CheckCalledFromGeneratedFile()  # pylint: disable=protected-access
      return _message.default_pool.FindMethodByName(full_name)

  def __init__(self,
               name,
               full_name,
               index,
               containing_service,
               input_type,
               output_type,
               client_streaming=False,
               server_streaming=False,
               options=None,
               serialized_options=None,
               create_key=None):
    """The arguments are as described in the description of MethodDescriptor
    attributes above.

    Note that containing_service may be None, and may be set later if necessary.
    """
    if create_key is not _internal_create_key:
      _Deprecated('MethodDescriptor')

    super(MethodDescriptor, self).__init__(
        containing_service.file if containing_service else None,
        options,
        serialized_options,
        'MethodOptions',
    )
    self.name = name
    self.full_name = full_name
    self.index = index
    self.containing_service = containing_service
    self.input_type = input_type
    self.output_type = output_type
    self.client_streaming = client_streaming
    self.server_streaming = server_streaming

  def CopyToProto(self, proto):
    """Copies this to a descriptor_pb2.MethodDescriptorProto.

    Args:
      proto (descriptor_pb2.MethodDescriptorProto): An empty descriptor proto.

    Raises:
      Error: If self couldn't be serialized, due to too few constructor
        arguments.
    """
    if self.containing_service is not None:
      from google.protobuf import descriptor_pb2
      service_proto = descriptor_pb2.ServiceDescriptorProto()
      self.containing_service.CopyToProto(service_proto)
      proto.CopyFrom(service_proto.method[self.index])
    else:
      raise Error('Descriptor does not contain a service.')


class FileDescriptor(DescriptorBase):
  """Descriptor for a file. Mimics the descriptor_pb2.FileDescriptorProto.

  Note that :attr:`enum_types_by_name`, :attr:`extensions_by_name`, and
  :attr:`dependencies` fields are only set by the
  :py:mod:`google.protobuf.message_factory` module, and not by the generated
  proto code.

  Attributes:
    name (str): Name of file, relative to root of source tree.
    package (str): Name of the package
    syntax (str): string indicating syntax of the file (can be "proto2" or
      "proto3")
    serialized_pb (bytes): Byte string of serialized
      :class:`descriptor_pb2.FileDescriptorProto`.
    dependencies (list[FileDescriptor]): List of other :class:`FileDescriptor`
      objects this :class:`FileDescriptor` depends on.
    public_dependencies (list[FileDescriptor]): A subset of
      :attr:`dependencies`, which were declared as "public".
    message_types_by_name (dict(str, Descriptor)): Mapping from message names
      to their :class:`Descriptor`.
    enum_types_by_name (dict(str, EnumDescriptor)): Mapping from enum names to
      their :class:`EnumDescriptor`.
    extensions_by_name (dict(str, FieldDescriptor)): Mapping from extension
      names declared at file scope to their :class:`FieldDescriptor`.
    services_by_name (dict(str, ServiceDescriptor)): Mapping from services'
      names to their :class:`ServiceDescriptor`.
    pool (DescriptorPool): The pool this descriptor belongs to.  When not
      passed to the constructor, the global default pool is used.
  """

  if _USE_C_DESCRIPTORS:
    _C_DESCRIPTOR_CLASS = _message.FileDescriptor

    def __new__(cls, name, package, options=None,
                serialized_options=None, serialized_pb=None,
                dependencies=None, public_dependencies=None,
                syntax=None, pool=None, create_key=None):
      # FileDescriptor() is called from various places, not only from generated
      # files, to register dynamic proto files and messages.
      # pylint: disable=g-explicit-bool-comparison
      if serialized_pb:
        return _message.default_pool.AddSerializedFile(serialized_pb)
      else:
        return super(FileDescriptor, cls).__new__(cls)

  def __init__(self, name, package, options=None,
               serialized_options=None, serialized_pb=None,
               dependencies=None, public_dependencies=None,
               syntax=None, pool=None, create_key=None):
    """Constructor."""
    if create_key is not _internal_create_key:
      _Deprecated('FileDescriptor')

    super(FileDescriptor, self).__init__(
        None, options, serialized_options, 'FileOptions'
    )

    if pool is None:
      from google.protobuf import descriptor_pool
      pool = descriptor_pool.Default()
    self.pool = pool
    self.message_types_by_name = {}
    self.name = name
    self.package = package
    self._deprecated_syntax = syntax or "proto2"
    self.serialized_pb = serialized_pb

    self.enum_types_by_name = {}
    self.extensions_by_name = {}
    self.services_by_name = {}
    self.dependencies = (dependencies or [])
    self.public_dependencies = (public_dependencies or [])

  @property
  def syntax(self):
    warnings.warn(
      'descriptor.syntax is deprecated. It will be removed'
      ' soon. Most usages are checking field descriptors. Consider to use'
      ' has_presence, is_packed on field descriptors.'
    )
    return self._deprecated_syntax

  def CopyToProto(self, proto):
    """Copies this to a descriptor_pb2.FileDescriptorProto.

    Args:
      proto: An empty descriptor_pb2.FileDescriptorProto.
    """
    proto.ParseFromString(self.serialized_pb)


def _ParseOptions(message, string):
  """Parses serialized options.

  This helper function is used to parse serialized options in generated
  proto2 files. It must not be used outside proto2.
  """
  message.ParseFromString(string)
  return message


def _ToCamelCase(name):
  """Converts name to camel-case and returns it."""
  capitalize_next = False
  result = []

  for c in name:
    if c == '_':
      if result:
        capitalize_next = True
    elif capitalize_next:
      result.append(c.upper())
      capitalize_next = False
    else:
      result += c

  # Lower-case the first letter.
  if result and result[0].isupper():
    result[0] = result[0].lower()
  return ''.join(result)


def _OptionsOrNone(descriptor_proto):
  """Returns the value of the field `options`, or None if it is not set."""
  if descriptor_proto.HasField('options'):
    return descriptor_proto.options
  else:
    return None


def _ToJsonName(name):
  """Converts name to Json name and returns it."""
  capitalize_next = False
  result = []

  for c in name:
    if c == '_':
      capitalize_next = True
    elif capitalize_next:
      result.append(c.upper())
      capitalize_next = False
    else:
      result += c

  return ''.join(result)


def MakeDescriptor(desc_proto, package='', build_file_if_cpp=True,
                   syntax=None):
  """Make a protobuf Descriptor given a DescriptorProto protobuf.

  Handles nested descriptors. Note that this is limited to the scope of defining
  a message inside of another message. Composite fields can currently only be
  resolved if the message is defined in the same scope as the field.

  Args:
    desc_proto: The descriptor_pb2.DescriptorProto protobuf message.
    package: Optional package name for the new message Descriptor (string).
    build_file_if_cpp: Update the C++ descriptor pool if api matches.
                       Set to False on recursion, so no duplicates are created.
    syntax: The syntax/semantics that should be used.  Set to "proto3" to get
            proto3 field presence semantics.
  Returns:
    A Descriptor for protobuf messages.
  """
  if api_implementation.Type() != 'python' and build_file_if_cpp:
    # The C++ implementation requires all descriptors to be backed by the same
    # definition in the C++ descriptor pool. To do this, we build a
    # FileDescriptorProto with the same definition as this descriptor and build
    # it into the pool.
    from google.protobuf import descriptor_pb2
    file_descriptor_proto = descriptor_pb2.FileDescriptorProto()
    file_descriptor_proto.message_type.add().MergeFrom(desc_proto)

    # Generate a random name for this proto file to prevent conflicts with any
    # imported ones. We need to specify a file name so the descriptor pool
    # accepts our FileDescriptorProto, but it is not important what that file
    # name is actually set to.
    proto_name = binascii.hexlify(os.urandom(16)).decode('ascii')

    if package:
      file_descriptor_proto.name = os.path.join(package.replace('.', '/'),
                                                proto_name + '.proto')
      file_descriptor_proto.package = package
    else:
      file_descriptor_proto.name = proto_name + '.proto'

    _message.default_pool.Add(file_descriptor_proto)
    result = _message.default_pool.FindFileByName(file_descriptor_proto.name)

    if _USE_C_DESCRIPTORS:
      return result.message_types_by_name[desc_proto.name]

  full_message_name = [desc_proto.name]
  if package: full_message_name.insert(0, package)

  # Create Descriptors for enum types
  enum_types = {}
  for enum_proto in desc_proto.enum_type:
    full_name = '.'.join(full_message_name + [enum_proto.name])
    enum_desc = EnumDescriptor(
        enum_proto.name, full_name, None, [
            EnumValueDescriptor(enum_val.name, ii, enum_val.number,
                                create_key=_internal_create_key)
            for ii, enum_val in enumerate(enum_proto.value)],
        create_key=_internal_create_key)
    enum_types[full_name] = enum_desc

  # Create Descriptors for nested types
  nested_types = {}
  for nested_proto in desc_proto.nested_type:
    full_name = '.'.join(full_message_name + [nested_proto.name])
    # Nested types are just those defined inside of the message, not all types
    # used by fields in the message, so no loops are possible here.
    nested_desc = MakeDescriptor(nested_proto,
                                 package='.'.join(full_message_name),
                                 build_file_if_cpp=False,
                                 syntax=syntax)
    nested_types[full_name] = nested_desc

  fields = []
  for field_proto in desc_proto.field:
    full_name = '.'.join(full_message_name + [field_proto.name])
    enum_desc = None
    nested_desc = None
    if field_proto.json_name:
      json_name = field_proto.json_name
    else:
      json_name = None
    if field_proto.HasField('type_name'):
      type_name = field_proto.type_name
      full_type_name = '.'.join(full_message_name +
                                [type_name[type_name.rfind('.')+1:]])
      if full_type_name in nested_types:
        nested_desc = nested_types[full_type_name]
      elif full_type_name in enum_types:
        enum_desc = enum_types[full_type_name]
      # Else type_name references a non-local type, which isn't implemented
    field = FieldDescriptor(
        field_proto.name, full_name, field_proto.number - 1,
        field_proto.number, field_proto.type,
        FieldDescriptor.ProtoTypeToCppProtoType(field_proto.type),
        field_proto.label, None, nested_desc, enum_desc, None, False, None,
        options=_OptionsOrNone(field_proto), has_default_value=False,
        json_name=json_name, create_key=_internal_create_key)
    fields.append(field)

  desc_name = '.'.join(full_message_name)
  return Descriptor(desc_proto.name, desc_name, None, None, fields,
                    list(nested_types.values()), list(enum_types.values()), [],
                    options=_OptionsOrNone(desc_proto),
                    create_key=_internal_create_key)

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_memmapping.py ===
import faulthandler
import gc
import itertools
import mmap
import os
import pickle
import platform
import subprocess
import sys
import threading
from time import sleep

import pytest

import joblib._memmapping_reducer as jmr
from joblib._memmapping_reducer import (
    ArrayMemmapForwardReducer,
    _get_backing_memmap,
    _get_temp_dir,
    _strided_from_memmap,
    _WeakArrayKeyMap,
    has_shareable_memory,
)
from joblib.backports import make_memmap
from joblib.executor import _TestingMemmappingExecutor as TestExecutor
from joblib.parallel import Parallel, delayed
from joblib.pool import MemmappingPool
from joblib.test.common import (
    IS_GIL_DISABLED,
    np,
    with_dev_shm,
    with_multiprocessing,
    with_numpy,
)
from joblib.testing import parametrize, raises, skipif


def setup_module():
    faulthandler.dump_traceback_later(timeout=300, exit=True)


def teardown_module():
    faulthandler.cancel_dump_traceback_later()


def check_memmap_and_send_back(array):
    assert _get_backing_memmap(array) is not None
    return array


def check_array(args):
    """Dummy helper function to be executed in subprocesses

    Check that the provided array has the expected values in the provided
    range.

    """
    data, position, expected = args
    np.testing.assert_array_equal(data[position], expected)


def inplace_double(args):
    """Dummy helper function to be executed in subprocesses


    Check that the input array has the right values in the provided range
    and perform an inplace modification to double the values in the range by
    two.

    """
    data, position, expected = args
    assert data[position] == expected
    data[position] *= 2
    np.testing.assert_array_equal(data[position], 2 * expected)


@with_numpy
@with_multiprocessing
def test_memmap_based_array_reducing(tmpdir):
    """Check that it is possible to reduce a memmap backed array"""
    assert_array_equal = np.testing.assert_array_equal
    filename = tmpdir.join("test.mmap").strpath

    # Create a file larger than what will be used by a
    buffer = np.memmap(filename, dtype=np.float64, shape=500, mode="w+")

    # Fill the original buffer with negative markers to detect over of
    # underflow in case of test failures
    buffer[:] = -1.0 * np.arange(buffer.shape[0], dtype=buffer.dtype)
    buffer.flush()

    # Memmap a 2D fortran array on a offsetted subsection of the previous
    # buffer
    a = np.memmap(
        filename, dtype=np.float64, shape=(3, 5, 4), mode="r+", order="F", offset=4
    )
    a[:] = np.arange(60).reshape(a.shape)

    # Build various views that share the buffer with the original memmap

    # b is an memmap sliced view on an memmap instance
    b = a[1:-1, 2:-1, 2:4]

    # b2 is a memmap 2d with memmap 1d as base
    # non-regression test for https://github.com/joblib/joblib/issues/1703
    b2 = buffer.reshape(10, 50)

    # c and d are array views
    c = np.asarray(b)
    d = c.T

    # Array reducer with auto dumping disabled
    reducer = ArrayMemmapForwardReducer(None, tmpdir.strpath, "c", True)

    def reconstruct_array_or_memmap(x):
        cons, args = reducer(x)
        return cons(*args)

    # Reconstruct original memmap
    a_reconstructed = reconstruct_array_or_memmap(a)
    assert has_shareable_memory(a_reconstructed)
    assert isinstance(a_reconstructed, np.memmap)
    assert_array_equal(a_reconstructed, a)

    # Reconstruct strided memmap view
    b_reconstructed = reconstruct_array_or_memmap(b)
    assert has_shareable_memory(b_reconstructed)
    assert_array_equal(b_reconstructed, b)

    # Reconstruct memmap 2d with memmap 1d as base
    b2_reconstructed = reconstruct_array_or_memmap(b2)
    assert has_shareable_memory(b2_reconstructed)
    assert_array_equal(b2_reconstructed, b2)

    # Reconstruct arrays views on memmap base
    c_reconstructed = reconstruct_array_or_memmap(c)
    assert not isinstance(c_reconstructed, np.memmap)
    assert has_shareable_memory(c_reconstructed)
    assert_array_equal(c_reconstructed, c)

    d_reconstructed = reconstruct_array_or_memmap(d)
    assert not isinstance(d_reconstructed, np.memmap)
    assert has_shareable_memory(d_reconstructed)
    assert_array_equal(d_reconstructed, d)

    # Test graceful degradation on fake memmap instances with in-memory
    # buffers
    a3 = a * 3
    assert not has_shareable_memory(a3)
    a3_reconstructed = reconstruct_array_or_memmap(a3)
    assert not has_shareable_memory(a3_reconstructed)
    assert not isinstance(a3_reconstructed, np.memmap)
    assert_array_equal(a3_reconstructed, a * 3)

    # Test graceful degradation on arrays derived from fake memmap instances
    b3 = np.asarray(a3)
    assert not has_shareable_memory(b3)

    b3_reconstructed = reconstruct_array_or_memmap(b3)
    assert isinstance(b3_reconstructed, np.ndarray)
    assert not has_shareable_memory(b3_reconstructed)
    assert_array_equal(b3_reconstructed, b3)


@with_numpy
@with_multiprocessing
@skipif(
    sys.platform != "win32", reason="PermissionError only easily triggerable on Windows"
)
def test_resource_tracker_retries_when_permissionerror(tmpdir):
    # Test resource_tracker retry mechanism when unlinking memmaps.  See more
    # thorough information in the ``unlink_file`` documentation of joblib.
    filename = tmpdir.join("test.mmap").strpath
    cmd = """if 1:
    import os
    import numpy as np
    import time
    from joblib.externals.loky.backend import resource_tracker
    resource_tracker.VERBOSE = 1

    # Start the resource tracker
    resource_tracker.ensure_running()
    time.sleep(1)

    # Create a file containing numpy data
    memmap = np.memmap(r"{filename}", dtype=np.float64, shape=10, mode='w+')
    memmap[:] = np.arange(10).astype(np.int8).data
    memmap.flush()
    assert os.path.exists(r"{filename}")
    del memmap

    # Create a np.memmap backed by this file
    memmap = np.memmap(r"{filename}", dtype=np.float64, shape=10, mode='w+')
    resource_tracker.register(r"{filename}", "file")

    # Ask the resource_tracker to delete the file backing the np.memmap , this
    # should raise PermissionError that the resource_tracker will log.
    resource_tracker.maybe_unlink(r"{filename}", "file")

    # Wait for the resource_tracker to process the maybe_unlink before cleaning
    # up the memmap
    time.sleep(2)
    """.format(filename=filename)
    p = subprocess.Popen(
        [sys.executable, "-c", cmd], stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )
    p.wait()
    out, err = p.communicate()
    assert p.returncode == 0, err.decode()
    assert out == b""
    msg = "tried to unlink {}, got PermissionError".format(filename)
    assert msg in err.decode()


@with_numpy
@with_multiprocessing
def test_high_dimension_memmap_array_reducing(tmpdir):
    assert_array_equal = np.testing.assert_array_equal

    filename = tmpdir.join("test.mmap").strpath

    # Create a high dimensional memmap
    a = np.memmap(filename, dtype=np.float64, shape=(100, 15, 15, 3), mode="w+")
    a[:] = np.arange(100 * 15 * 15 * 3).reshape(a.shape)

    # Create some slices/indices at various dimensions
    b = a[0:10]
    c = a[:, 5:10]
    d = a[:, :, :, 0]
    e = a[1:3:4]

    # Array reducer with auto dumping disabled
    reducer = ArrayMemmapForwardReducer(None, tmpdir.strpath, "c", True)

    def reconstruct_array_or_memmap(x):
        cons, args = reducer(x)
        return cons(*args)

    a_reconstructed = reconstruct_array_or_memmap(a)
    assert has_shareable_memory(a_reconstructed)
    assert isinstance(a_reconstructed, np.memmap)
    assert_array_equal(a_reconstructed, a)

    b_reconstructed = reconstruct_array_or_memmap(b)
    assert has_shareable_memory(b_reconstructed)
    assert_array_equal(b_reconstructed, b)

    c_reconstructed = reconstruct_array_or_memmap(c)
    assert has_shareable_memory(c_reconstructed)
    assert_array_equal(c_reconstructed, c)

    d_reconstructed = reconstruct_array_or_memmap(d)
    assert has_shareable_memory(d_reconstructed)
    assert_array_equal(d_reconstructed, d)

    e_reconstructed = reconstruct_array_or_memmap(e)
    assert has_shareable_memory(e_reconstructed)
    assert_array_equal(e_reconstructed, e)


@with_numpy
def test__strided_from_memmap(tmpdir):
    fname = tmpdir.join("test.mmap").strpath
    size = 5 * mmap.ALLOCATIONGRANULARITY
    offset = mmap.ALLOCATIONGRANULARITY + 1
    # This line creates the mmap file that is reused later
    memmap_obj = np.memmap(fname, mode="w+", shape=size + offset)
    # filename, dtype, mode, offset, order, shape, strides, total_buffer_len
    memmap_obj = _strided_from_memmap(
        fname,
        dtype="uint8",
        mode="r",
        offset=offset,
        order="C",
        shape=size,
        strides=None,
        total_buffer_len=None,
        unlink_on_gc_collect=False,
    )
    assert isinstance(memmap_obj, np.memmap)
    assert memmap_obj.offset == offset
    memmap_backed_obj = _strided_from_memmap(
        fname,
        dtype="uint8",
        mode="r",
        offset=offset,
        order="C",
        shape=(size // 2,),
        strides=(2,),
        total_buffer_len=size,
        unlink_on_gc_collect=False,
    )
    assert _get_backing_memmap(memmap_backed_obj).offset == offset


@with_numpy
@with_multiprocessing
@parametrize(
    "factory",
    [MemmappingPool, TestExecutor.get_memmapping_executor],
    ids=["multiprocessing", "loky"],
)
def test_pool_with_memmap(factory, tmpdir):
    """Check that subprocess can access and update shared memory memmap"""
    assert_array_equal = np.testing.assert_array_equal

    # Fork the subprocess before allocating the objects to be passed
    pool_temp_folder = tmpdir.mkdir("pool").strpath
    p = factory(10, max_nbytes=2, temp_folder=pool_temp_folder)
    try:
        filename = tmpdir.join("test.mmap").strpath
        a = np.memmap(filename, dtype=np.float32, shape=(3, 5), mode="w+")
        a.fill(1.0)

        p.map(
            inplace_double,
            [(a, (i, j), 1.0) for i in range(a.shape[0]) for j in range(a.shape[1])],
        )

        assert_array_equal(a, 2 * np.ones(a.shape))

        # Open a copy-on-write view on the previous data
        b = np.memmap(filename, dtype=np.float32, shape=(5, 3), mode="c")

        p.map(
            inplace_double,
            [(b, (i, j), 2.0) for i in range(b.shape[0]) for j in range(b.shape[1])],
        )

        # Passing memmap instances to the pool should not trigger the creation
        # of new files on the FS
        assert os.listdir(pool_temp_folder) == []

        # the original data is untouched
        assert_array_equal(a, 2 * np.ones(a.shape))
        assert_array_equal(b, 2 * np.ones(b.shape))

        # readonly maps can be read but not updated
        c = np.memmap(filename, dtype=np.float32, shape=(10,), mode="r", offset=5 * 4)

        with raises(AssertionError):
            p.map(check_array, [(c, i, 3.0) for i in range(c.shape[0])])

        # depending on the version of numpy one can either get a RuntimeError
        # or a ValueError
        with raises((RuntimeError, ValueError)):
            p.map(inplace_double, [(c, i, 2.0) for i in range(c.shape[0])])
    finally:
        # Clean all filehandlers held by the pool
        p.terminate()
        del p


@with_numpy
@with_multiprocessing
@parametrize(
    "factory",
    [MemmappingPool, TestExecutor.get_memmapping_executor],
    ids=["multiprocessing", "loky"],
)
def test_pool_with_memmap_array_view(factory, tmpdir):
    """Check that subprocess can access and update shared memory array"""
    assert_array_equal = np.testing.assert_array_equal

    # Fork the subprocess before allocating the objects to be passed
    pool_temp_folder = tmpdir.mkdir("pool").strpath
    p = factory(10, max_nbytes=2, temp_folder=pool_temp_folder)
    try:
        filename = tmpdir.join("test.mmap").strpath
        a = np.memmap(filename, dtype=np.float32, shape=(3, 5), mode="w+")
        a.fill(1.0)

        # Create an ndarray view on the memmap instance
        a_view = np.asarray(a)
        assert not isinstance(a_view, np.memmap)
        assert has_shareable_memory(a_view)

        p.map(
            inplace_double,
            [
                (a_view, (i, j), 1.0)
                for i in range(a.shape[0])
                for j in range(a.shape[1])
            ],
        )

        # Both a and the a_view have been updated
        assert_array_equal(a, 2 * np.ones(a.shape))
        assert_array_equal(a_view, 2 * np.ones(a.shape))

        # Passing memmap array view to the pool should not trigger the
        # creation of new files on the FS
        assert os.listdir(pool_temp_folder) == []

    finally:
        p.terminate()
        del p


@with_numpy
@with_multiprocessing
@parametrize("backend", ["multiprocessing", "loky"])
def test_permission_error_windows_reference_cycle(backend):
    # Non regression test for:
    # https://github.com/joblib/joblib/issues/806
    #
    # The issue happens when trying to delete a memory mapped file that has
    # not yet been closed by one of the worker processes.
    cmd = """if 1:
        import numpy as np
        from joblib import Parallel, delayed


        data = np.random.rand(int(2e6)).reshape((int(1e6), 2))

        # Build a complex cyclic reference that is likely to delay garbage
        # collection of the memmapped array in the worker processes.
        first_list = current_list = [data]
        for i in range(10):
            current_list = [current_list]
        first_list.append(current_list)

        if __name__ == "__main__":
            results = Parallel(n_jobs=2, backend="{b}")(
                delayed(len)(current_list) for i in range(10))
            assert results == [1] * 10
    """.format(b=backend)
    p = subprocess.Popen(
        [sys.executable, "-c", cmd], stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )
    p.wait()
    out, err = p.communicate()
    assert p.returncode == 0, out.decode() + "\n\n" + err.decode()


@with_numpy
@with_multiprocessing
@parametrize("backend", ["multiprocessing", "loky"])
def test_permission_error_windows_memmap_sent_to_parent(backend):
    # Second non-regression test for:
    # https://github.com/joblib/joblib/issues/806
    # previously, child process would not convert temporary memmaps to numpy
    # arrays when sending the data back to the parent process. This would lead
    # to permission errors on windows when deleting joblib's temporary folder,
    # as the memmaped files handles would still opened in the parent process.
    cmd = """if 1:
        import os
        import time

        import numpy as np

        from joblib import Parallel, delayed
        from testutils import return_slice_of_data

        data = np.ones(int(2e6))

        if __name__ == '__main__':
            # warm-up call to launch the workers and start the resource_tracker
            _ = Parallel(n_jobs=2, verbose=5, backend='{b}')(
                delayed(id)(i) for i in range(20))

            time.sleep(0.5)

            slice_of_data = Parallel(n_jobs=2, verbose=5, backend='{b}')(
                delayed(return_slice_of_data)(data, 0, 20) for _ in range(10))
    """.format(b=backend)

    for _ in range(3):
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(__file__)
        p = subprocess.Popen(
            [sys.executable, "-c", cmd],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=env,
        )
        p.wait()
        out, err = p.communicate()
        assert p.returncode == 0, err
        assert out == b""
        assert b"resource_tracker" not in err


@with_numpy
@with_multiprocessing
@parametrize("backend", ["multiprocessing", "loky"])
def test_parallel_isolated_temp_folders(backend):
    # Test that consecutive Parallel call use isolated subfolders, even
    # for the loky backend that reuses its executor instance across calls.
    array = np.arange(int(1e2))
    [filename_1] = Parallel(n_jobs=2, backend=backend, max_nbytes=10)(
        delayed(getattr)(array, "filename") for _ in range(1)
    )
    [filename_2] = Parallel(n_jobs=2, backend=backend, max_nbytes=10)(
        delayed(getattr)(array, "filename") for _ in range(1)
    )
    assert os.path.dirname(filename_2) != os.path.dirname(filename_1)


@with_numpy
@with_multiprocessing
@parametrize("backend", ["multiprocessing", "loky"])
def test_managed_backend_reuse_temp_folder(backend):
    # Test that calls to a managed parallel object reuse the same memmaps.
    array = np.arange(int(1e2))
    with Parallel(n_jobs=2, backend=backend, max_nbytes=10) as p:
        [filename_1] = p(delayed(getattr)(array, "filename") for _ in range(1))
        [filename_2] = p(delayed(getattr)(array, "filename") for _ in range(1))
    assert os.path.dirname(filename_2) == os.path.dirname(filename_1)


@with_numpy
@with_multiprocessing
def test_memmapping_temp_folder_thread_safety():
    # Concurrent calls to Parallel with the loky backend will use the same
    # executor, and thus the same reducers. Make sure that those reducers use
    # different temporary folders depending on which Parallel objects called
    # them, which is necessary to limit potential race conditions during the
    # garbage collection of temporary memmaps.
    array = np.arange(int(1e2))

    temp_dirs_thread_1 = set()
    temp_dirs_thread_2 = set()

    def concurrent_get_filename(array, temp_dirs):
        with Parallel(backend="loky", n_jobs=2, max_nbytes=10) as p:
            for i in range(10):
                [filename] = p(delayed(getattr)(array, "filename") for _ in range(1))
                temp_dirs.add(os.path.dirname(filename))

    t1 = threading.Thread(
        target=concurrent_get_filename, args=(array, temp_dirs_thread_1)
    )
    t2 = threading.Thread(
        target=concurrent_get_filename, args=(array, temp_dirs_thread_2)
    )

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    assert len(temp_dirs_thread_1) == 1
    assert len(temp_dirs_thread_2) == 1

    assert temp_dirs_thread_1 != temp_dirs_thread_2


@with_numpy
@with_multiprocessing
def test_multithreaded_parallel_termination_resource_tracker_silent():
    # test that concurrent termination attempts of a same executor does not
    # emit any spurious error from the resource_tracker. We test various
    # situations making 0, 1 or both parallel call sending a task that will
    # make the worker (and thus the whole Parallel call) error out.
    cmd = """if 1:
        import os
        import numpy as np
        from joblib import Parallel, delayed
        from joblib.externals.loky.backend import resource_tracker
        from concurrent.futures import ThreadPoolExecutor, wait

        resource_tracker.VERBOSE = 0

        array = np.arange(int(1e2))

        temp_dirs_thread_1 = set()
        temp_dirs_thread_2 = set()


        def raise_error(array):
            raise ValueError


        def parallel_get_filename(array, temp_dirs):
            with Parallel(backend="loky", n_jobs=2, max_nbytes=10) as p:
                for i in range(10):
                    [filename] = p(
                        delayed(getattr)(array, "filename") for _ in range(1)
                    )
                    temp_dirs.add(os.path.dirname(filename))


        def parallel_raise(array, temp_dirs):
            with Parallel(backend="loky", n_jobs=2, max_nbytes=10) as p:
                for i in range(10):
                    [filename] = p(
                        delayed(raise_error)(array) for _ in range(1)
                    )
                    temp_dirs.add(os.path.dirname(filename))


        executor = ThreadPoolExecutor(max_workers=2)

        # both function calls will use the same loky executor, but with a
        # different Parallel object.
        future_1 = executor.submit({f1}, array, temp_dirs_thread_1)
        future_2 = executor.submit({f2}, array, temp_dirs_thread_2)

        # Wait for both threads to terminate their backend
        wait([future_1, future_2])

        future_1.result()
        future_2.result()
    """
    functions_and_returncodes = [
        ("parallel_get_filename", "parallel_get_filename", 0),
        ("parallel_get_filename", "parallel_raise", 1),
        ("parallel_raise", "parallel_raise", 1),
    ]

    for f1, f2, returncode in functions_and_returncodes:
        p = subprocess.Popen(
            [sys.executable, "-c", cmd.format(f1=f1, f2=f2)],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        p.wait()
        _, err = p.communicate()
        assert p.returncode == returncode, err.decode()
        assert b"resource_tracker" not in err, err.decode()


@with_numpy
@with_multiprocessing
@parametrize("backend", ["multiprocessing", "loky"])
def test_many_parallel_calls_on_same_object(backend):
    # After #966 got merged, consecutive Parallel objects were sharing temp
    # folder, which would lead to race conditions happening during the
    # temporary resources management with the resource_tracker. This is a
    # non-regression test that makes sure that consecutive Parallel operations
    # on the same object do not error out.
    cmd = """if 1:
        import os
        import time

        import numpy as np

        from joblib import Parallel, delayed
        from testutils import return_slice_of_data

        data = np.ones(100)

        if __name__ == '__main__':
            for i in range(5):
                slice_of_data = Parallel(
                    n_jobs=2, max_nbytes=1, backend='{b}')(
                        delayed(return_slice_of_data)(data, 0, 20)
                        for _ in range(10)
                    )
    """.format(b=backend)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(__file__)
    p = subprocess.Popen(
        [sys.executable, "-c", cmd],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env=env,
    )
    p.wait()
    out, err = p.communicate()
    assert p.returncode == 0, err.decode()
    assert out == b"", out.decode()
    assert b"resource_tracker" not in err


@with_numpy
@with_multiprocessing
@parametrize("backend", ["multiprocessing", "loky"])
def test_memmap_returned_as_regular_array(backend):
    data = np.ones(int(1e3))
    # Check that child processes send temporary memmaps back as numpy arrays.
    [result] = Parallel(n_jobs=2, backend=backend, max_nbytes=100)(
        delayed(check_memmap_and_send_back)(data) for _ in range(1)
    )
    assert _get_backing_memmap(result) is None


@with_numpy
@with_multiprocessing
@parametrize("backend", ["multiprocessing", "loky"])
def test_resource_tracker_silent_when_reference_cycles(backend):
    # There is a variety of reasons that can make joblib with loky backend
    # output noisy warnings when a reference cycle is preventing a memmap from
    # being garbage collected. Especially, joblib's main process finalizer
    # deletes the temporary folder if it was not done before, which can
    # interact badly with the resource_tracker. We don't risk leaking any
    # resources, but this will likely make joblib output a lot of low-level
    # confusing messages.
    #
    # This test makes sure that the resource_tracker is silent when a reference
    # has been collected concurrently on non-Windows platforms.
    #
    # Note that the script in ``cmd`` is the exact same script as in
    # test_permission_error_windows_reference_cycle.
    if backend == "loky" and sys.platform.startswith("win"):
        # XXX: on Windows, reference cycles can delay timely garbage collection
        # and make it impossible to properly delete the temporary folder in the
        # main process because of permission errors.
        pytest.xfail(
            "The temporary folder cannot be deleted on Windows in the "
            "presence of a reference cycle"
        )

    cmd = """if 1:
        import numpy as np
        from joblib import Parallel, delayed


        data = np.random.rand(int(2e6)).reshape((int(1e6), 2))

        # Build a complex cyclic reference that is likely to delay garbage
        # collection of the memmapped array in the worker processes.
        first_list = current_list = [data]
        for i in range(10):
            current_list = [current_list]
        first_list.append(current_list)

        if __name__ == "__main__":
            results = Parallel(n_jobs=2, backend="{b}")(
                delayed(len)(current_list) for i in range(10))
            assert results == [1] * 10
    """.format(b=backend)
    p = subprocess.Popen(
        [sys.executable, "-c", cmd], stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )
    p.wait()
    out, err = p.communicate()
    out = out.decode()
    err = err.decode()
    assert p.returncode == 0, out + "\n\n" + err
    assert "resource_tracker" not in err, err


@with_numpy
@with_multiprocessing
@parametrize(
    "factory",
    [MemmappingPool, TestExecutor.get_memmapping_executor],
    ids=["multiprocessing", "loky"],
)
def test_memmapping_pool_for_large_arrays(factory, tmpdir):
    """Check that large arrays are not copied in memory"""

    # Check that the tempfolder is empty
    assert os.listdir(tmpdir.strpath) == []

    # Build an array reducers that automatically dump large array content
    # to filesystem backed memmap instances to avoid memory explosion
    p = factory(3, max_nbytes=40, temp_folder=tmpdir.strpath, verbose=2)
    try:
        # The temporary folder for the pool is not provisioned in advance
        assert os.listdir(tmpdir.strpath) == []
        assert not os.path.exists(p._temp_folder)

        small = np.ones(5, dtype=np.float32)
        assert small.nbytes == 20
        p.map(check_array, [(small, i, 1.0) for i in range(small.shape[0])])

        # Memory has been copied, the pool filesystem folder is unused
        assert os.listdir(tmpdir.strpath) == []

        # Try with a file larger than the memmap threshold of 40 bytes
        large = np.ones(100, dtype=np.float64)
        assert large.nbytes == 800
        p.map(check_array, [(large, i, 1.0) for i in range(large.shape[0])])

        # The data has been dumped in a temp folder for subprocess to share it
        # without per-child memory copies
        assert os.path.isdir(p._temp_folder)
        dumped_filenames = os.listdir(p._temp_folder)
        assert len(dumped_filenames) == 1

        # Check that memory mapping is not triggered for arrays with
        # dtype='object'
        objects = np.array(["abc"] * 100, dtype="object")
        results = p.map(has_shareable_memory, [objects])
        assert not results[0]

    finally:
        # check FS garbage upon pool termination
        p.terminate()
        for i in range(10):
            sleep(0.1)
            if not os.path.exists(p._temp_folder):
                break
        else:  # pragma: no cover
            raise AssertionError(
                "temporary folder {} was not deleted".format(p._temp_folder)
            )
        del p


@with_numpy
@with_multiprocessing
@parametrize(
    "backend",
    [
        pytest.param(
            "multiprocessing",
            marks=pytest.mark.xfail(
                reason="https://github.com/joblib/joblib/issues/1086"
            ),
        ),
        "loky",
    ],
)
def test_child_raises_parent_exits_cleanly(backend):
    # When a task executed by a child process raises an error, the parent
    # process's backend is notified, and calls abort_everything.
    # In loky, abort_everything itself calls shutdown(kill_workers=True) which
    # sends SIGKILL to the worker, preventing it from running the finalizers
    # supposed to signal the resource_tracker when the worker is done using
    # objects relying on a shared resource (e.g np.memmaps). Because this
    # behavior is prone to :
    # - cause a resource leak
    # - make the resource tracker emit noisy resource warnings
    # we explicitly test that, when the said situation occurs:
    # - no resources are actually leaked
    # - the temporary resources are deleted as soon as possible (typically, at
    #   the end of the failing Parallel call)
    # - the resource_tracker does not emit any warnings.
    cmd = """if 1:
        import os
        from pathlib import Path
        from time import sleep

        import numpy as np
        from joblib import Parallel, delayed
        from testutils import print_filename_and_raise

        data = np.random.rand(1000)

        def get_temp_folder(parallel_obj, backend):
            if "{b}" == "loky":
                return Path(parallel_obj._backend._workers._temp_folder)
            else:
                return Path(parallel_obj._backend._pool._temp_folder)


        if __name__ == "__main__":
            try:
                with Parallel(n_jobs=2, backend="{b}", max_nbytes=100) as p:
                    temp_folder = get_temp_folder(p, "{b}")
                    p(delayed(print_filename_and_raise)(data)
                              for i in range(1))
            except ValueError as e:
                # the temporary folder should be deleted by the end of this
                # call but apparently on some file systems, this takes
                # some time to be visible.
                #
                # We attempt to write into the temporary folder to test for
                # its existence and we wait for a maximum of 10 seconds.
                for i in range(100):
                    try:
                        with open(temp_folder / "some_file.txt", "w") as f:
                            f.write("some content")
                    except FileNotFoundError:
                        # temp_folder has been deleted, all is fine
                        break

                    # ... else, wait a bit and try again
                    sleep(.1)
                else:
                    raise AssertionError(
                        str(temp_folder) + " was not deleted"
                    ) from e
    """.format(b=backend)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(__file__)
    p = subprocess.Popen(
        [sys.executable, "-c", cmd],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env=env,
    )
    p.wait()
    out, err = p.communicate()
    out, err = out.decode(), err.decode()
    filename = out.split("\n")[0]
    assert p.returncode == 0, err or out
    assert err == ""  # no resource_tracker warnings.
    assert not os.path.exists(filename)


@with_numpy
@with_multiprocessing
@parametrize(
    "factory",
    [MemmappingPool, TestExecutor.get_memmapping_executor],
    ids=["multiprocessing", "loky"],
)
def test_memmapping_pool_for_large_arrays_disabled(factory, tmpdir):
    """Check that large arrays memmapping can be disabled"""
    # Set max_nbytes to None to disable the auto memmapping feature
    p = factory(3, max_nbytes=None, temp_folder=tmpdir.strpath)
    try:
        # Check that the tempfolder is empty
        assert os.listdir(tmpdir.strpath) == []

        # Try with a file largish than the memmap threshold of 40 bytes
        large = np.ones(100, dtype=np.float64)
        assert large.nbytes == 800
        p.map(check_array, [(large, i, 1.0) for i in range(large.shape[0])])

        # Check that the tempfolder is still empty
        assert os.listdir(tmpdir.strpath) == []

    finally:
        # Cleanup open file descriptors
        p.terminate()
        del p


@with_numpy
@with_multiprocessing
@with_dev_shm
@parametrize(
    "factory",
    [MemmappingPool, TestExecutor.get_memmapping_executor],
    ids=["multiprocessing", "loky"],
)
def test_memmapping_on_large_enough_dev_shm(factory):
    """Check that memmapping uses /dev/shm when possible"""
    orig_size = jmr.SYSTEM_SHARED_MEM_FS_MIN_SIZE
    try:
        # Make joblib believe that it can use /dev/shm even when running on a
        # CI container where the size of the /dev/shm is not very large (that
        # is at least 32 MB instead of 2 GB by default).
        jmr.SYSTEM_SHARED_MEM_FS_MIN_SIZE = int(32e6)
        p = factory(3, max_nbytes=10)
        try:
            # Check that the pool has correctly detected the presence of the
            # shared memory filesystem.
            pool_temp_folder = p._temp_folder
            folder_prefix = "/dev/shm/joblib_memmapping_folder_"
            assert pool_temp_folder.startswith(folder_prefix)
            assert os.path.exists(pool_temp_folder)

            # Try with a file larger than the memmap threshold of 10 bytes
            a = np.ones(100, dtype=np.float64)
            assert a.nbytes == 800
            p.map(id, [a] * 10)
            # a should have been memmapped to the pool temp folder: the joblib
            # pickling procedure generate one .pkl file:
            assert len(os.listdir(pool_temp_folder)) == 1

            # create a new array with content that is different from 'a' so
            # that it is mapped to a different file in the temporary folder of
            # the pool.
            b = np.ones(100, dtype=np.float64) * 2
            assert b.nbytes == 800
            p.map(id, [b] * 10)
            # A copy of both a and b are now stored in the shared memory folder
            assert len(os.listdir(pool_temp_folder)) == 2
        finally:
            # Cleanup open file descriptors
            p.terminate()
            del p

        for i in range(100):
            # The temp folder is cleaned up upon pool termination
            if not os.path.exists(pool_temp_folder):
                break
            sleep(0.1)
        else:  # pragma: no cover
            raise AssertionError("temporary folder of pool was not deleted")
    finally:
        jmr.SYSTEM_SHARED_MEM_FS_MIN_SIZE = orig_size


@with_numpy
@with_multiprocessing
@with_dev_shm
@parametrize(
    "factory",
    [MemmappingPool, TestExecutor.get_memmapping_executor],
    ids=["multiprocessing", "loky"],
)
def test_memmapping_on_too_small_dev_shm(factory):
    orig_size = jmr.SYSTEM_SHARED_MEM_FS_MIN_SIZE
    try:
        # Make joblib believe that it cannot use /dev/shm unless there is
        # 42 exabytes of available shared memory in /dev/shm
        jmr.SYSTEM_SHARED_MEM_FS_MIN_SIZE = int(42e18)

        p = factory(3, max_nbytes=10)
        try:
            # Check that the pool has correctly detected the presence of the
            # shared memory filesystem.
            pool_temp_folder = p._temp_folder
            assert not pool_temp_folder.startswith("/dev/shm")
        finally:
            # Cleanup open file descriptors
            p.terminate()
            del p

        # The temp folder is cleaned up upon pool termination
        assert not os.path.exists(pool_temp_folder)
    finally:
        jmr.SYSTEM_SHARED_MEM_FS_MIN_SIZE = orig_size


@with_numpy
@with_multiprocessing
@parametrize(
    "factory",
    [MemmappingPool, TestExecutor.get_memmapping_executor],
    ids=["multiprocessing", "loky"],
)
def test_memmapping_pool_for_large_arrays_in_return(factory, tmpdir):
    """Check that large arrays are not copied in memory in return"""
    assert_array_equal = np.testing.assert_array_equal

    # Build an array reducers that automatically dump large array content
    # but check that the returned datastructure are regular arrays to avoid
    # passing a memmap array pointing to a pool controlled temp folder that
    # might be confusing to the user

    # The MemmappingPool user can always return numpy.memmap object explicitly
    # to avoid memory copy
    p = factory(3, max_nbytes=10, temp_folder=tmpdir.strpath)
    try:
        res = p.apply_async(np.ones, args=(1000,))
        large = res.get()
        assert not has_shareable_memory(large)
        assert_array_equal(large, np.ones(1000))
    finally:
        p.terminate()
        del p


def _worker_multiply(a, n_times):
    """Multiplication function to be executed by subprocess"""
    assert has_shareable_memory(a)
    return a * n_times


@with_numpy
@with_multiprocessing
@parametrize(
    "factory",
    [MemmappingPool, TestExecutor.get_memmapping_executor],
    ids=["multiprocessing", "loky"],
)
def test_workaround_against_bad_memmap_with_copied_buffers(factory, tmpdir):
    """Check that memmaps with a bad buffer are returned as regular arrays

    Unary operations and ufuncs on memmap instances return a new memmap
    instance with an in-memory buffer (probably a numpy bug).
    """
    assert_array_equal = np.testing.assert_array_equal

    p = factory(3, max_nbytes=10, temp_folder=tmpdir.strpath)
    try:
        # Send a complex, large-ish view on a array that will be converted to
        # a memmap in the worker process
        a = np.asarray(np.arange(6000).reshape((1000, 2, 3)), order="F")[:, :1, :]

        # Call a non-inplace multiply operation on the worker and memmap and
        # send it back to the parent.
        b = p.apply_async(_worker_multiply, args=(a, 3)).get()
        assert not has_shareable_memory(b)
        assert_array_equal(b, 3 * a)
    finally:
        p.terminate()
        del p


def identity(arg):
    return arg


@with_numpy
@with_multiprocessing
@parametrize(
    "factory,retry_no",
    list(
        itertools.product(
            [MemmappingPool, TestExecutor.get_memmapping_executor], range(3)
        )
    ),
    ids=[
        "{}, {}".format(x, y)
        for x, y in itertools.product(["multiprocessing", "loky"], map(str, range(3)))
    ],
)
def test_pool_memmap_with_big_offset(factory, retry_no, tmpdir):
    # Test that numpy memmap offset is set correctly if greater than
    # mmap.ALLOCATIONGRANULARITY, see
    # https://github.com/joblib/joblib/issues/451 and
    # https://github.com/numpy/numpy/pull/8443 for more details.
    fname = tmpdir.join("test.mmap").strpath
    size = 5 * mmap.ALLOCATIONGRANULARITY
    offset = mmap.ALLOCATIONGRANULARITY + 1
    obj = make_memmap(fname, mode="w+", shape=size, dtype="uint8", offset=offset)

    p = factory(2, temp_folder=tmpdir.strpath)
    result = p.apply_async(identity, args=(obj,)).get()
    assert isinstance(result, np.memmap)
    assert result.offset == offset
    np.testing.assert_array_equal(obj, result)
    p.terminate()


def test_pool_get_temp_dir(tmpdir):
    pool_folder_name = "test.tmpdir"
    pool_folder, shared_mem = _get_temp_dir(pool_folder_name, tmpdir.strpath)
    assert shared_mem is False
    assert pool_folder == tmpdir.join("test.tmpdir").strpath

    pool_folder, shared_mem = _get_temp_dir(pool_folder_name, temp_folder=None)
    if sys.platform.startswith("win"):
        assert shared_mem is False
    assert pool_folder.endswith(pool_folder_name)


def test_pool_get_temp_dir_no_statvfs(tmpdir, monkeypatch):
    """Check that _get_temp_dir works when os.statvfs is not defined

    Regression test for #902
    """
    pool_folder_name = "test.tmpdir"
    import joblib._memmapping_reducer

    if hasattr(joblib._memmapping_reducer.os, "statvfs"):
        # We are on Unix, since Windows doesn't have this function
        monkeypatch.delattr(joblib._memmapping_reducer.os, "statvfs")

    pool_folder, shared_mem = _get_temp_dir(pool_folder_name, temp_folder=None)
    if sys.platform.startswith("win"):
        assert shared_mem is False
    assert pool_folder.endswith(pool_folder_name)


@with_numpy
@skipif(
    sys.platform == "win32", reason="This test fails with a PermissionError on Windows"
)
@parametrize("mmap_mode", ["r+", "w+"])
def test_numpy_arrays_use_different_memory(mmap_mode):
    def func(arr, value):
        arr[:] = value
        return arr

    arrays = [np.zeros((10, 10), dtype="float64") for i in range(10)]

    results = Parallel(mmap_mode=mmap_mode, max_nbytes=0, n_jobs=2)(
        delayed(func)(arr, i) for i, arr in enumerate(arrays)
    )

    for i, arr in enumerate(results):
        np.testing.assert_array_equal(arr, i)


@with_numpy
def test_weak_array_key_map():
    def assert_empty_after_gc_collect(container, retries=100):
        for i in range(retries):
            if len(container) == 0:
                return
            gc.collect()
            sleep(0.1)
        assert len(container) == 0

    a = np.ones(42)
    m = _WeakArrayKeyMap()
    m.set(a, "a")
    assert m.get(a) == "a"

    b = a
    assert m.get(b) == "a"
    m.set(b, "b")
    assert m.get(a) == "b"

    del a
    gc.collect()
    assert len(m._data) == 1
    assert m.get(b) == "b"

    del b
    assert_empty_after_gc_collect(m._data)

    c = np.ones(42)
    m.set(c, "c")
    assert len(m._data) == 1
    assert m.get(c) == "c"

    with raises(KeyError):
        m.get(np.ones(42))

    del c
    assert_empty_after_gc_collect(m._data)

    # Check that creating and dropping numpy arrays with potentially the same
    # object id will not cause the map to get confused.
    def get_set_get_collect(m, i):
        a = np.ones(42)
        with raises(KeyError):
            m.get(a)
        m.set(a, i)
        assert m.get(a) == i
        return id(a)

    unique_ids = set([get_set_get_collect(m, i) for i in range(1000)])
    if platform.python_implementation() == "CPython":
        # On CPython (at least) the same id is often reused many times for the
        # temporary arrays created under the local scope of the
        # get_set_get_collect function without causing any spurious lookups /
        # insertions in the map. Apparently on free-threaded Python, the id is
        # not reused as often.
        max_len_unique_ids = 400 if IS_GIL_DISABLED else 100
        assert len(unique_ids) < max_len_unique_ids


def test_weak_array_key_map_no_pickling():
    m = _WeakArrayKeyMap()
    with raises(pickle.PicklingError):
        pickle.dumps(m)


@with_numpy
@with_multiprocessing
def test_direct_mmap(tmpdir):
    testfile = str(tmpdir.join("arr.dat"))
    a = np.arange(10, dtype="uint8")
    a.tofile(testfile)

    def _read_array():
        with open(testfile) as fd:
            mm = mmap.mmap(fd.fileno(), 0, access=mmap.ACCESS_READ, offset=0)
        return np.ndarray((10,), dtype=np.uint8, buffer=mm, offset=0)

    def func(x):
        return x**2

    arr = _read_array()

    # this gives the reference result of the function with an array
    ref = Parallel(n_jobs=2)(delayed(func)(x) for x in [a])

    # now test that it works with the mmap array
    results = Parallel(n_jobs=2)(delayed(func)(x) for x in [arr])
    np.testing.assert_array_equal(results, ref)

    # also test that a mmap array read in the subprocess is correctly returned
    results = Parallel(n_jobs=2)(delayed(_read_array)() for _ in range(1))
    np.testing.assert_array_equal(results[0], arr)


@with_numpy
@with_multiprocessing
def test_parallel_memmap2d_as_memmap_1d_base(tmpdir):
    # non-regression test for https://github.com/joblib/joblib/issues/1703,
    # where 2D arrays backed by 1D memmap had un-wanted order changes.
    testfile = str(tmpdir.join("arr2.dat"))
    a = np.arange(10, dtype="uint8").reshape(5, 2)
    a.tofile(testfile)

    def _read_array():
        mm = np.memmap(testfile)
        return mm.reshape(5, 2)

    def func(x):
        return x**2

    arr = _read_array()

    # this gives the reference result of the function with an array
    ref = Parallel(n_jobs=2)(delayed(func)(x) for x in [a])

    # now test that it works with a view on a 1D mmap array
    results = Parallel(n_jobs=2)(delayed(func)(x) for x in [arr])
    assert not results[0].flags["F_CONTIGUOUS"]
    np.testing.assert_array_equal(results, ref)

    # also test that returned memmap arrays are correctly ordered
    results = Parallel(n_jobs=2)(delayed(_read_array)() for _ in range(1))
    np.testing.assert_array_equal(results[0], a)

# === NexusCore/openenv\Lib\site-packages\pyreadline3\modes\vi.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006-2020 Michael Graz. <mgraz@plan10.com>
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************


import os

import pyreadline3.lineeditor.lineobj as lineobj
from pyreadline3.logger import log

from . import basemode


class ViMode(basemode.BaseMode):
    mode = "vi"

    def __init__(self, rlobj):
        super().__init__(rlobj)

        self.__vi_insert_mode = None

    def __repr__(self):
        return "<ViMode>"

    def process_keyevent(self, keyinfo):
        def nop(e):
            pass

        keytuple = keyinfo.tuple()

        # Process exit keys. Only exit on empty line
        if keytuple in self.exit_dispatch:
            if lineobj.EndOfLine(self.l_buffer) == 0:
                raise EOFError

        dispatch_func = self.key_dispatch.get(keytuple, self.vi_key)
        log("readline from keyboard:%s->%s" % (keytuple, dispatch_func))
        r = None
        if dispatch_func:
            r = dispatch_func(keyinfo)
            self.l_buffer.push_undo()

        self.previous_func = dispatch_func
        if r:
            self._update_line()
            return True
        return False

    # Methods below here are bindable emacs functions

    def init_editing_mode(self, e):  # (M-C-j)
        """Initialize vi editingmode"""
        self.show_all_if_ambiguous = "on"
        self.key_dispatch = {}
        self.__vi_insert_mode = None
        self._vi_command = None
        self._vi_command_edit = None
        self._vi_key_find_char = None
        self._vi_key_find_direction = True
        self._vi_yank_buffer = None
        self._vi_multiplier1 = ""
        self._vi_multiplier2 = ""
        self._vi_undo_stack = []
        self._vi_undo_cursor = -1
        self._vi_current = None
        self._vi_search_text = ""
        self._vi_search_position = 0
        self.vi_save_line()
        self.vi_set_insert_mode(True)
        # make ' ' to ~ self insert
        for c in range(ord(" "), 127):
            self._bind_key("%s" % chr(c), self.vi_key)
        self._bind_key("BackSpace", self.vi_backspace)
        self._bind_key("Escape", self.vi_escape)
        self._bind_key("Return", self.vi_accept_line)

        self._bind_key("Left", self.backward_char)
        self._bind_key("Right", self.forward_char)
        self._bind_key("Home", self.beginning_of_line)
        self._bind_key("End", self.end_of_line)
        self._bind_key("Delete", self.delete_char)

        self._bind_key("Control-d", self.vi_eof)
        self._bind_key("Control-z", self.vi_eof)
        self._bind_key("Control-r", self.vi_redo)
        self._bind_key("Up", self.vi_arrow_up)
        self._bind_key("Control-p", self.vi_up)
        self._bind_key("Down", self.vi_arrow_down)
        self._bind_key("Control-n", self.vi_down)
        self._bind_key("Tab", self.vi_complete)

    #        self._bind_key('Control-e', self.emacs)

    def vi_key(self, e):
        if not self._vi_command:
            self._vi_command = ViCommand(self)
        elif self._vi_command.is_end:
            if self._vi_command.is_edit:
                self._vi_command_edit = self._vi_command
            self._vi_command = ViCommand(self)
        self._vi_command.add_char(e.char)

    def vi_error(self):
        self._bell()

    def vi_get_is_insert_mode(self):
        return self.__vi_insert_mode

    vi_is_insert_mode = property(vi_get_is_insert_mode)

    def vi_escape(self, e):
        if self.vi_is_insert_mode:
            if self._vi_command:
                self._vi_command.add_char(e.char)
            else:
                self._vi_command = ViCommand(self)
            self.vi_set_insert_mode(False)
            self.l_buffer.point = lineobj.PrevChar
        elif self._vi_command and self._vi_command.is_replace_one:
            self._vi_command.add_char(e.char)
        else:
            self.vi_error()

    def vi_backspace(self, e):
        if self._vi_command:
            self._vi_command.add_char(e.char)
        else:
            self._vi_do_backspace(self._vi_command)

    def _vi_do_backspace(self, vi_cmd):
        if self.vi_is_insert_mode or (self._vi_command and self._vi_command.is_search):
            if self.l_buffer.point > 0:
                self.l_buffer.point -= 1
                if self.l_buffer.overwrite:
                    try:
                        prev = self._vi_undo_stack[self._vi_undo_cursor][1][
                            self.l_buffer.point
                        ]
                        self.l_buffer.line_buffer[self.l_buffer.point] = prev
                    except IndexError:
                        del self.l_buffer.line_buffer[self.l_buffer.point]
                else:
                    self.vi_save_line()
                    del self.l_buffer.line_buffer[self.l_buffer.point]

    def vi_accept_line(self, e):
        if self._vi_command and self._vi_command.is_search:
            self._vi_command.do_search()
            return False
        self._vi_command = None
        self.vi_set_insert_mode(True)
        self._vi_undo_stack = []
        self._vi_undo_cursor = -1
        self._vi_current = None
        if self.l_buffer.line_buffer:
            self.add_history(self.l_buffer.copy())
        return self.accept_line(e)

    def vi_eof(self, e):
        raise EOFError

    def vi_set_insert_mode(self, value):
        if self.__vi_insert_mode == value:
            return
        self.__vi_insert_mode = value
        if value:
            self.vi_save_line()
            self.cursor_size = 25
        else:
            self.cursor_size = 100

    def vi_undo_restart(self):
        tpl_undo = (
            self.l_buffer.point,
            self.l_buffer.line_buffer[:],
        )
        self._vi_undo_stack = [tpl_undo]
        self._vi_undo_cursor = 0

    def vi_save_line(self):
        if self._vi_undo_stack and self._vi_undo_cursor >= 0:
            del self._vi_undo_stack[self._vi_undo_cursor + 1 :]
        # tpl_undo = (self.l_buffer.point, self.l_buffer[:], )
        tpl_undo = (
            self.l_buffer.point,
            self.l_buffer.line_buffer[:],
        )
        if (
            not self._vi_undo_stack
            or self._vi_undo_stack[self._vi_undo_cursor][1] != tpl_undo[1]
        ):
            self._vi_undo_stack.append(tpl_undo)
            self._vi_undo_cursor += 1

    def vi_undo_prepare(self):
        if self._vi_undo_cursor == len(self._vi_undo_stack) - 1:
            self.vi_save_line()

    def vi_undo(self, do_pop=True):
        self.vi_undo_prepare()
        if not self._vi_undo_stack or self._vi_undo_cursor <= 0:
            self.vi_error()
            return
        self._vi_undo_cursor -= 1
        self.vi_undo_assign()

    def vi_undo_all(self):
        self.vi_undo_prepare()
        if self._vi_undo_cursor > 0:
            self._vi_undo_cursor = 0
            self.vi_undo_assign()
        else:
            self.vi_error()

    def vi_undo_assign(self):
        tpl_undo = self._vi_undo_stack[self._vi_undo_cursor]
        self.l_buffer.line_buffer = tpl_undo[1][:]
        self.l_buffer.point = tpl_undo[0]

    def vi_redo(self, e):
        if self._vi_undo_cursor >= len(self._vi_undo_stack) - 1:
            self.vi_error()
            return
        self._vi_undo_cursor += 1
        self.vi_undo_assign()

    def vi_search(self, rng):
        for i in rng:
            line_history = self._history.history[i]
            pos = line_history.get_line_text().find(self._vi_search_text)
            if pos >= 0:
                self._vi_search_position = i
                self._history.history_cursor = i
                self.l_buffer.line_buffer = list(line_history.line_buffer)
                self.l_buffer.point = pos
                self.vi_undo_restart()
                return True
        self._bell()
        return False

    def vi_search_first(self):
        text = "".join(self.l_buffer.line_buffer[1:])
        if text:
            self._vi_search_text = text
            self._vi_search_position = len(self._history.history) - 1
        elif self._vi_search_text:
            self._vi_search_position -= 1
        else:
            self.vi_error()
            self.vi_undo()
            return
        if not self.vi_search(list(range(self._vi_search_position, -1, -1))):
            # Here: search text not found
            self.vi_undo()

    def vi_search_again_backward(self):
        self.vi_search(list(range(self._vi_search_position - 1, -1, -1)))

    def vi_search_again_forward(self):
        self.vi_search(
            list(range(self._vi_search_position + 1, len(self._history.history)))
        )

    def vi_up(self, e):
        if self._history.history_cursor == len(self._history.history):
            self._vi_current = self.l_buffer.line_buffer[:]
        # self._history.previous_history (e)
        self._history.previous_history(self.l_buffer)
        if self.vi_is_insert_mode:
            self.end_of_line(e)
        else:
            self.beginning_of_line(e)
        self.vi_undo_restart()

    def vi_down(self, e):
        if self._history.history_cursor >= len(self._history.history):
            self.vi_error()
            return
        if self._history.history_cursor < len(self._history.history) - 1:
            # self._history.next_history (e)
            self._history.next_history(self.l_buffer)
            if self.vi_is_insert_mode:
                self.end_of_line(e)
            else:
                self.beginning_of_line(e)
            self.vi_undo_restart()
        elif self._vi_current is not None:
            self._history.history_cursor = len(self._history.history)
            self.l_buffer.line_buffer = self._vi_current
            self.end_of_line(e)
            if not self.vi_is_insert_mode and self.l_buffer.point > 0:
                self.l_buffer.point -= 1
            self._vi_current = None
        else:
            self.vi_error()
            return

    def vi_arrow_up(self, e):
        self.vi_set_insert_mode(True)
        self.vi_up(e)
        self.vi_save_line()

    def vi_arrow_down(self, e):
        self.vi_set_insert_mode(True)
        self.vi_down(e)
        self.vi_save_line()

    def vi_complete(self, e):
        text = self.l_buffer.get_line_text()
        if text and not text.isspace():
            return self.complete(e)
        else:
            return self.vi_key(e)


# vi input states
# sequence of possible states are in the order below
_VI_BEGIN = "vi_begin"
_VI_MULTI1 = "vi_multi1"
_VI_ACTION = "vi_action"
_VI_MULTI2 = "vi_multi2"
_VI_MOTION = "vi_motion"
_VI_MOTION_ARGUMENT = "vi_motion_argument"
_VI_REPLACE_ONE = "vi_replace_one"
_VI_TEXT = "vi_text"
_VI_SEARCH = "vi_search"
_VI_END = "vi_end"

# vi helper class


class ViCommand:
    def __init__(self, readline):
        self.readline = readline
        self.lst_char = []
        self.state = _VI_BEGIN
        self.action = self.movement
        self.motion = None
        self.motion_argument = None
        self.text = None
        self.pos_motion = None
        self.is_edit = False
        self.is_overwrite = False
        self.is_error = False
        self.is_star = False
        self.delete_left = 0
        self.delete_right = 0
        self.readline._vi_multiplier1 = ""
        self.readline._vi_multiplier2 = ""
        self.set_override_multiplier(0)
        self.skip_multipler = False
        self.tabstop = 4
        self.dct_fcn = {
            ord("$"): self.key_dollar,
            ord("^"): self.key_hat,
            ord(";"): self.key_semicolon,
            ord(","): self.key_comma,
            ord("%"): self.key_percent,
            ord("."): self.key_dot,
            ord("/"): self.key_slash,
            ord("*"): self.key_star,
            ord("|"): self.key_bar,
            ord("~"): self.key_tilde,
            8: self.key_backspace,
        }

    def add_char(self, char):
        self.lst_char.append(char)
        if self.state == _VI_BEGIN and self.readline.vi_is_insert_mode:
            self.readline.vi_save_line()
            self.state = _VI_TEXT
        if self.state == _VI_SEARCH:
            if char == "\x08":  # backspace
                self.key_backspace(char)
            else:
                self.set_text(char)
            return
        if self.state == _VI_TEXT:
            if char == "\x1b":  # escape
                self.escape(char)
            elif char == "\x09":  # tab
                ts = self.tabstop
                ws = " " * (ts - (self.readline.l_buffer.point % ts))
                self.set_text(ws)
            elif char == "\x08":  # backspace
                self.key_backspace(char)
            else:
                self.set_text(char)
            return
        if self.state == _VI_MOTION_ARGUMENT:
            self.set_motion_argument(char)
            return
        if self.state == _VI_REPLACE_ONE:
            self.replace_one(char)
            return
        try:
            fcn_instance = self.dct_fcn[ord(char)]
        except BaseException:
            fcn_instance = getattr(self, "key_%s" % char, None)
        if fcn_instance:
            fcn_instance(char)
            return
        if char.isdigit():
            self.key_digit(char)
            return
        # Here: could not process key
        self.error()

    def set_text(self, text):
        if self.text is None:
            self.text = text
        else:
            self.text += text
        self.set_buffer(text)

    def set_buffer(self, text):
        for char in text:
            if not self.char_isprint(char):
                continue
            #             self.readline.l_buffer.insert_text(char)
            #             continue
            #             #overwrite in l_buffer obj
            if self.is_overwrite:
                if self.readline.l_buffer.point < len(
                    self.readline.l_buffer.line_buffer
                ):
                    # self.readline.l_buffer[self.l_buffer.point]=char
                    self.readline.l_buffer.line_buffer[self.readline.l_buffer.point] = (
                        char
                    )
                else:
                    # self.readline.l_buffer.insert_text(char)
                    self.readline.l_buffer.line_buffer.append(char)
            else:
                # self.readline.l_buffer.insert_text(char)
                self.readline.l_buffer.line_buffer.insert(
                    self.readline.l_buffer.point, char
                )
            self.readline.l_buffer.point += 1

    def replace_one(self, char):
        if char == "\x1b":  # escape
            self.end()
            return
        self.is_edit = True
        self.readline.vi_save_line()
        times = self.get_multiplier()
        cursor = self.readline.l_buffer.point
        self.readline.l_buffer.line_buffer[cursor : cursor + times] = char * times
        if times > 1:
            self.readline.l_buffer.point += times - 1
        self.end()

    def char_isprint(self, char):
        return ord(char) >= ord(" ") and ord(char) <= ord("~")

    def key_dollar(self, char):
        self.motion = self.motion_end_in_line
        self.delete_right = 1
        self.state = _VI_MOTION
        self.apply()

    def key_hat(self, char):
        self.motion = self.motion_beginning_of_line
        self.state = _VI_MOTION
        self.apply()

    def key_0(self, char):
        if self.state in [_VI_BEGIN, _VI_ACTION]:
            self.key_hat(char)
        else:
            self.key_digit(char)

    def key_digit(self, char):
        if self.state in [_VI_BEGIN, _VI_MULTI1]:
            self.readline._vi_multiplier1 += char
            self.readline._vi_multiplier2 = ""
            self.state = _VI_MULTI1
        elif self.state in [_VI_ACTION, _VI_MULTI2]:
            self.readline._vi_multiplier2 += char
            self.state = _VI_MULTI2

    def key_w(self, char):
        if self.action == self.change:
            self.key_e(char)
            return
        self.motion = self.motion_word_short
        self.state = _VI_MOTION
        self.apply()

    def key_W(self, char):
        if self.action == self.change:
            self.key_E(char)
            return
        self.motion = self.motion_word_long
        self.state = _VI_MOTION
        self.apply()

    def key_e(self, char):
        self.motion = self.motion_end_short
        self.state = _VI_MOTION
        self.delete_right = 1
        self.apply()

    def key_E(self, char):
        self.motion = self.motion_end_long
        self.state = _VI_MOTION
        self.delete_right = 1
        self.apply()

    def key_b(self, char):
        self.motion = self.motion_back_short
        self.state = _VI_MOTION
        self.apply()

    def key_B(self, char):
        self.motion = self.motion_back_long
        self.state = _VI_MOTION
        self.apply()

    def key_f(self, char):
        self.readline._vi_key_find_direction = True
        self.motion = self.motion_find_char_forward
        self.delete_right = 1
        self.state = _VI_MOTION_ARGUMENT

    def key_F(self, char):
        self.readline._vi_key_find_direction = False
        self.motion = self.motion_find_char_backward
        self.delete_left = 1
        self.state = _VI_MOTION_ARGUMENT

    def key_t(self, char):
        self.motion = self.motion_to_char_forward
        self.delete_right = 1
        self.state = _VI_MOTION_ARGUMENT

    def key_T(self, char):
        self.motion = self.motion_to_char_backward
        self.state = _VI_MOTION_ARGUMENT

    def key_j(self, char):
        self.readline.vi_down(ViEvent(char))
        self.state = _VI_END

    def key_k(self, char):
        self.readline.vi_up(ViEvent(char))
        self.state = _VI_END

    def key_semicolon(self, char):
        if self.readline._vi_key_find_char is None:
            self.error()
            return
        if self.readline._vi_key_find_direction:
            self.motion = self.motion_find_char_forward
        else:
            self.motion = self.motion_find_char_backward
        self.set_motion_argument(self.readline._vi_key_find_char)

    def key_comma(self, char):
        if self.readline._vi_key_find_char is None:
            self.error()
            return
        if self.readline._vi_key_find_direction:
            self.motion = self.motion_find_char_backward
        else:
            self.motion = self.motion_find_char_forward
        self.set_motion_argument(self.readline._vi_key_find_char)

    def key_percent(self, char):
        """find matching <([{}])>"""
        self.motion = self.motion_matching
        self.delete_right = 1
        self.state = _VI_MOTION
        self.apply()

    def key_dot(self, char):
        vi_cmd_edit = self.readline._vi_command_edit
        if not vi_cmd_edit:
            return
        if vi_cmd_edit.is_star:
            self.key_star(char)
            return
        if self.has_multiplier():
            count = self.get_multiplier()
        else:
            count = 0
        # Create the ViCommand object after getting multiplier from self
        # Side effect of the ViCommand creation is resetting of global
        # multipliers
        vi_cmd = ViCommand(self.readline)
        if count >= 1:
            vi_cmd.set_override_multiplier(count)
            vi_cmd_edit.set_override_multiplier(count)
        elif vi_cmd_edit.override_multiplier:
            vi_cmd.set_override_multiplier(vi_cmd_edit.override_multiplier)
        for char in vi_cmd_edit.lst_char:
            vi_cmd.add_char(char)
        if vi_cmd_edit.is_overwrite and self.readline.l_buffer.point > 0:
            self.readline.l_buffer.point -= 1
        self.readline.vi_set_insert_mode(False)
        self.end()

    def key_slash(self, char):
        self.readline.vi_save_line()
        self.readline.l_buffer.line_buffer = ["/"]
        self.readline.l_buffer.point = 1
        self.state = _VI_SEARCH

    def key_star(self, char):
        self.is_star = True
        self.is_edit = True
        self.readline.vi_save_line()
        completions = self.readline._get_completions()
        if completions:
            text = " ".join(completions) + " "
            self.readline.l_buffer.line_buffer[
                self.readline.begidx : self.readline.endidx + 1
            ] = list(text)
            prefix_len = self.readline.endidx - self.readline.begidx
            self.readline.l_buffer.point += len(text) - prefix_len
            self.readline.vi_set_insert_mode(True)
        else:
            self.error()
        self.state = _VI_TEXT

    def key_bar(self, char):
        self.motion = self.motion_column
        self.state = _VI_MOTION
        self.apply()

    def key_tilde(self, char):
        self.is_edit = True
        self.readline.vi_save_line()
        for i in range(self.get_multiplier()):
            try:
                c = self.readline.l_buffer.line_buffer[self.readline.l_buffer.point]
                if c.isupper():
                    self.readline.l_buffer.line_buffer[self.readline.l_buffer.point] = (
                        c.lower()
                    )
                elif c.islower():
                    self.readline.l_buffer.line_buffer[self.readline.l_buffer.point] = (
                        c.upper()
                    )
                self.readline.l_buffer.point += 1
            except IndexError:
                break
        self.end()

    def key_h(self, char):
        self.motion = self.motion_left
        self.state = _VI_MOTION
        self.apply()

    def key_backspace(self, char):
        if self.state in [_VI_TEXT, _VI_SEARCH]:
            if self.text and len(self.text):
                self.text = self.text[:-1]
                try:
                    # Remove backspaces for potential dot command
                    self.lst_char.pop()
                    self.lst_char.pop()
                except IndexError:
                    pass
        else:
            self.key_h(char)
        self.readline._vi_do_backspace(self)
        if self.state == _VI_SEARCH and not (self.readline.l_buffer.line_buffer):
            self.state = _VI_BEGIN

    def key_l(self, char):
        self.motion = self.motion_right
        self.state = _VI_MOTION
        self.apply()

    def key_i(self, char):
        self.is_edit = True
        self.state = _VI_TEXT
        self.readline.vi_set_insert_mode(True)

    def key_I(self, char):
        self.is_edit = True
        self.state = _VI_TEXT
        self.readline.vi_set_insert_mode(True)
        self.readline.l_buffer.point = 0

    def key_a(self, char):
        self.is_edit = True
        self.state = _VI_TEXT
        self.readline.vi_set_insert_mode(True)
        if len(self.readline.l_buffer.line_buffer):
            self.readline.l_buffer.point += 1

    def key_A(self, char):
        self.is_edit = True
        self.state = _VI_TEXT
        self.readline.vi_set_insert_mode(True)
        self.readline.l_buffer.point = len(self.readline.l_buffer.line_buffer)

    def key_d(self, char):
        self.is_edit = True
        self.state = _VI_ACTION
        self.action = self.delete

    def key_D(self, char):
        self.is_edit = True
        self.state = _VI_ACTION
        self.action = self.delete_end_of_line
        self.apply()

    def key_x(self, char):
        self.is_edit = True
        self.state = _VI_ACTION
        self.action = self.delete_char
        self.apply()

    def key_X(self, char):
        self.is_edit = True
        self.state = _VI_ACTION
        self.action = self.delete_prev_char
        self.apply()

    def key_s(self, char):
        self.is_edit = True
        i1 = self.readline.l_buffer.point
        i2 = self.readline.l_buffer.point + self.get_multiplier()
        self.skip_multipler = True
        self.readline.vi_set_insert_mode(True)
        del self.readline.l_buffer.line_buffer[i1:i2]
        self.state = _VI_TEXT

    def key_S(self, char):
        self.is_edit = True
        self.readline.vi_set_insert_mode(True)
        self.readline.l_buffer.line_buffer = []
        self.readline.l_buffer.point = 0
        self.state = _VI_TEXT

    def key_c(self, char):
        self.is_edit = True
        self.state = _VI_ACTION
        self.action = self.change

    def key_C(self, char):
        self.is_edit = True
        self.readline.vi_set_insert_mode(True)
        del self.readline.l_buffer.line_buffer[self.readline.l_buffer.point :]
        self.state = _VI_TEXT

    def key_r(self, char):
        self.state = _VI_REPLACE_ONE

    def key_R(self, char):
        self.is_edit = True
        self.is_overwrite = True
        self.readline.l_buffer.overwrite = True
        self.readline.vi_set_insert_mode(True)
        self.state = _VI_TEXT

    def key_y(self, char):
        self._state = _VI_ACTION
        self.action = self.yank

    def key_Y(self, char):
        self.readline._vi_yank_buffer = self.readline.l_buffer.get_line_text()
        self.end()

    def key_p(self, char):
        if not self.readline._vi_yank_buffer:
            return
        self.is_edit = True
        self.readline.vi_save_line()
        self.readline.l_buffer.point += 1
        self.readline.l_buffer.insert_text(
            self.readline._vi_yank_buffer * self.get_multiplier()
        )
        self.readline.l_buffer.point -= 1
        self.state = _VI_END

    def key_P(self, char):
        if not self.readline._vi_yank_buffer:
            return
        self.is_edit = True
        self.readline.vi_save_line()
        self.readline.l_buffer.insert_text(
            self.readline._vi_yank_buffer * self.get_multiplier()
        )
        self.readline.l_buffer.point -= 1
        self.state = _VI_END

    def key_u(self, char):
        self.readline.vi_undo()
        self.state = _VI_END

    def key_U(self, char):
        self.readline.vi_undo_all()
        self.state = _VI_END

    def key_v(self, char):
        editor = ViExternalEditor(self.readline.l_buffer.line_buffer)
        self.readline.l_buffer.line_buffer = list(editor.result)
        self.readline.l_buffer.point = 0
        self.is_edit = True
        self.state = _VI_END

    def error(self):
        self.readline._bell()
        self.is_error = True

    def state_is_end(self):
        return self.state == _VI_END

    is_end = property(state_is_end)

    def state_is_search(self):
        return self.state == _VI_SEARCH

    is_search = property(state_is_search)

    def state_is_replace_one(self):
        return self.state == _VI_REPLACE_ONE

    is_replace_one = property(state_is_replace_one)

    def do_search(self):
        self.readline.vi_search_first()
        self.state = _VI_END

    def key_n(self, char):
        self.readline.vi_search_again_backward()
        self.state = _VI_END

    def key_N(self, char):
        self.readline.vi_search_again_forward()
        self.state = _VI_END

    def motion_beginning_of_line(self, line, index=0, count=1, **kw):
        return 0

    def motion_end_in_line(self, line, index=0, count=1, **kw):
        return max(0, len(self.readline.l_buffer.line_buffer) - 1)

    def motion_word_short(self, line, index=0, count=1, **kw):
        return vi_pos_word_short(line, index, count)

    def motion_word_long(self, line, index=0, count=1, **kw):
        return vi_pos_word_long(line, index, count)

    def motion_end_short(self, line, index=0, count=1, **kw):
        return vi_pos_end_short(line, index, count)

    def motion_end_long(self, line, index=0, count=1, **kw):
        return vi_pos_end_long(line, index, count)

    def motion_back_short(self, line, index=0, count=1, **kw):
        return vi_pos_back_short(line, index, count)

    def motion_back_long(self, line, index=0, count=1, **kw):
        return vi_pos_back_long(line, index, count)

    def motion_find_char_forward(self, line, index=0, count=1, char=None):
        self.readline._vi_key_find_char = char
        return vi_pos_find_char_forward(line, char, index, count)

    def motion_find_char_backward(self, line, index=0, count=1, char=None):
        self.readline._vi_key_find_char = char
        return vi_pos_find_char_backward(line, char, index, count)

    def motion_to_char_forward(self, line, index=0, count=1, char=None):
        return vi_pos_to_char_forward(line, char, index, count)

    def motion_to_char_backward(self, line, index=0, count=1, char=None):
        return vi_pos_to_char_backward(line, char, index, count)

    def motion_left(self, line, index=0, count=1, char=None):
        return max(0, index - count)

    def motion_right(self, line, index=0, count=1, char=None):
        return min(len(line), index + count)

    def motion_matching(self, line, index=0, count=1, char=None):
        return vi_pos_matching(line, index)

    def motion_column(self, line, index=0, count=1, char=None):
        return max(0, count - 1)

    def has_multiplier(self):
        return (
            self.override_multiplier
            or self.readline._vi_multiplier1
            or self.readline._vi_multiplier2
        )

    def get_multiplier(self):
        if self.override_multiplier:
            return int(self.override_multiplier)
        if self.readline._vi_multiplier1 == "":
            m1 = 1
        else:
            m1 = int(self.readline._vi_multiplier1)
        if self.readline._vi_multiplier2 == "":
            m2 = 1
        else:
            m2 = int(self.readline._vi_multiplier2)
        return m1 * m2

    def set_override_multiplier(self, count):
        self.override_multiplier = count

    def apply(self):
        if self.motion:
            self.pos_motion = self.motion(
                self.readline.l_buffer.line_buffer,
                self.readline.l_buffer.point,
                self.get_multiplier(),
                char=self.motion_argument,
            )
            if self.pos_motion < 0:
                self.error()
                return
        self.action()
        if self.state != _VI_TEXT:
            self.end()

    def movement(self):
        if self.pos_motion <= len(self.readline.l_buffer.line_buffer):
            self.readline.l_buffer.point = self.pos_motion
        else:
            self.readline.l_buffer.point = len(self.readline.l_buffer.line_buffer) - 1

    def yank(self):
        if self.pos_motion > self.readline.l_buffer.point:
            s = self.readline.l_buffer.line_buffer[
                self.readline.l_buffer.point : self.pos_motion + self.delete_right
            ]
        else:
            index = max(0, self.pos_motion - self.delete_left)
            s = self.readline.l_buffer.line_buffer[
                index : self.readline.l_buffer.point + self.delete_right
            ]
        self.readline._vi_yank_buffer = s

    def delete(self):
        self.readline.vi_save_line()
        self.yank()
        #         point=lineobj.Point(self.readline.l_buffer)
        #         pm=self.pos_motion
        #         del self.readline.l_buffer[point:pm]
        #         return
        if self.pos_motion > self.readline.l_buffer.point:
            del self.readline.l_buffer.line_buffer[
                self.readline.l_buffer.point : self.pos_motion + self.delete_right
            ]
            if self.readline.l_buffer.point > len(self.readline.l_buffer.line_buffer):
                self.readline.l_buffer.point = len(self.readline.l_buffer.line_buffer)
        else:
            index = max(0, self.pos_motion - self.delete_left)
            del self.readline.l_buffer.line_buffer[
                index : self.readline.l_buffer.point + self.delete_right
            ]
            self.readline.l_buffer.point = index

    def delete_end_of_line(self):
        self.readline.vi_save_line()
        # del self.readline.l_buffer [self.readline.l_buffer.point : ]
        line_text = self.readline.l_buffer.get_line_text()
        line_text = line_text[: self.readline.l_buffer.point]
        self.readline.l_buffer.set_line(line_text)
        if self.readline.l_buffer.point > 0:
            self.readline.l_buffer.point -= 1

    def delete_char(self):
        #         point=lineobj.Point(self.readline.l_buffer)
        #         del self.readline.l_buffer[point:point+self.get_multiplier ()]
        #         return
        self.pos_motion = self.readline.l_buffer.point + self.get_multiplier()
        self.delete()
        end = max(0, len(self.readline.l_buffer) - 1)
        if self.readline.l_buffer.point > end:
            self.readline.l_buffer.point = end

    def delete_prev_char(self):
        self.pos_motion = self.readline.l_buffer.point - self.get_multiplier()
        self.delete()

    def change(self):
        self.readline.vi_set_insert_mode(True)
        self.delete()
        self.skip_multipler = True
        self.state = _VI_TEXT

    def escape(self, char):
        if self.state == _VI_TEXT:
            if not self.skip_multipler:
                times = self.get_multiplier()
                if times > 1 and self.text:
                    extra = self.text * (times - 1)
                    self.set_buffer(extra)
        self.state = _VI_END

    def set_motion_argument(self, char):
        self.motion_argument = char
        self.apply()

    def end(self):
        self.state = _VI_END
        if self.readline.l_buffer.point >= len(self.readline.l_buffer.line_buffer):
            self.readline.l_buffer.point = max(
                0, len(self.readline.l_buffer.line_buffer) - 1
            )


class ViExternalEditor:
    def __init__(self, line):
        if isinstance(line, type([])):
            line = "".join(line)
        file_tmp = self.get_tempfile()
        fp_tmp = self.file_open(file_tmp, "w")
        fp_tmp.write(line)
        fp_tmp.close()
        self.run_editor(file_tmp)
        fp_tmp = self.file_open(file_tmp, "r")
        self.result = fp_tmp.read()
        fp_tmp.close()
        self.file_remove(file_tmp)

    def get_tempfile(self):
        import tempfile

        return tempfile.mktemp(prefix="readline-", suffix=".py")

    def file_open(self, filename, mode):
        return open(filename, mode)

    def file_remove(self, filename):
        os.remove(filename)

    def get_editor(self):
        try:
            return os.environ["EDITOR"]
        except KeyError:
            return "notepad"  # ouch

    def run_editor(self, filename):
        cmd = "%s %s" % (
            self.get_editor(),
            filename,
        )
        self.run_command(cmd)

    def run_command(self, command):
        os.system(command)


class ViEvent:
    def __init__(self, char):
        self.char = char


# vi standalone functions


def vi_is_word(char):
    log(
        "xx vi_is_word: type(%s), %s"
        % (
            type(char),
            char,
        )
    )
    return char.isalpha() or char.isdigit() or char == "_"


def vi_is_space(char):
    return char.isspace()


def vi_is_word_or_space(char):
    return vi_is_word(char) or vi_is_space(char)


def vi_pos_word_short(line, index=0, count=1):
    try:
        for i in range(count):
            in_word = vi_is_word(line[index])
            if not in_word:
                while not vi_is_word(line[index]):
                    index += 1
            else:
                while vi_is_word(line[index]):
                    index += 1
            while vi_is_space(line[index]):
                index += 1
        return index
    except IndexError:
        return len(line)


def vi_pos_word_long(line, index=0, count=1):
    try:
        for i in range(count):
            in_space = vi_is_space(line[index])
            if not in_space:
                while not vi_is_space(line[index]):
                    index += 1
            while vi_is_space(line[index]):
                index += 1
        return index
    except IndexError:
        return len(line)


def vi_pos_end_short(line, index=0, count=1):
    try:
        for i in range(count):
            index += 1
            while vi_is_space(line[index]):
                index += 1
            in_word = vi_is_word(line[index])
            if not in_word:
                while not vi_is_word_or_space(line[index]):
                    index += 1
            else:
                while vi_is_word(line[index]):
                    index += 1
        return index - 1
    except IndexError:
        return max(0, len(line) - 1)


def vi_pos_end_long(line, index=0, count=1):
    try:
        for i in range(count):
            index += 1
            while vi_is_space(line[index]):
                index += 1
            while not vi_is_space(line[index]):
                index += 1
        return index - 1
    except IndexError:
        return max(0, len(line) - 1)


class vi_list(list):
    """This is a list that cannot have a negative index"""

    def __getitem__(self, key):
        try:
            if int(key) < 0:
                raise IndexError
        except ValueError:
            pass
        return list.__getitem__(self, key)


def vi_pos_back_short(line, index=0, count=1):
    line = vi_list(line)
    try:
        for i in range(count):
            index -= 1
            while vi_is_space(line[index]):
                index -= 1
            in_word = vi_is_word(line[index])
            if in_word:
                while vi_is_word(line[index]):
                    index -= 1
            else:
                while not vi_is_word_or_space(line[index]):
                    index -= 1
        return index + 1
    except IndexError:
        return 0


def vi_pos_back_long(line, index=0, count=1):
    line = vi_list(line)
    try:
        for i in range(count):
            index -= 1
            while vi_is_space(line[index]):
                index -= 1
            while not vi_is_space(line[index]):
                index -= 1
        return index + 1
    except IndexError:
        return 0


def vi_pos_find_char_forward(line, char, index=0, count=1):
    try:
        for i in range(count):
            index += 1
            while line[index] != char:
                index += 1
        return index
    except IndexError:
        return -1


def vi_pos_find_char_backward(line, char, index=0, count=1):
    try:
        for i in range(count):
            index -= 1
            while True:
                if index < 0:
                    return -1
                if line[index] == char:
                    break
                index -= 1
        return index
    except IndexError:
        return -1


def vi_pos_to_char_forward(line, char, index=0, count=1):
    index = vi_pos_find_char_forward(line, char, index, count)
    if index > 0:
        return index - 1
    return index


def vi_pos_to_char_backward(line, char, index=0, count=1):
    index = vi_pos_find_char_backward(line, char, index, count)
    if index >= 0:
        return index + 1
    return index


_vi_dct_matching = {
    "<": (">", +1),
    ">": ("<", -1),
    "(": (")", +1),
    ")": ("(", -1),
    "[": ("]", +1),
    "]": ("[", -1),
    "{": ("}", +1),
    "}": ("{", -1),
}


def vi_pos_matching(line, index=0):
    """find matching <([{}])>"""
    anchor = None
    target = None
    delta = 1
    count = 0
    try:
        while True:
            if anchor is None:
                # first find anchor
                try:
                    target, delta = _vi_dct_matching[line[index]]
                    anchor = line[index]
                    count = 1
                except KeyError:
                    index += 1
                    continue
            else:
                # Here the anchor has been found
                # Need to get corresponding target
                if index < 0:
                    return -1
                if line[index] == anchor:
                    count += 1
                elif line[index] == target:
                    count -= 1
                    if count == 0:
                        return index
            index += delta
    except IndexError:
        return -1

# === NexusCore/openenv\Lib\site-packages\urllib3\response.py ===
from __future__ import annotations

import collections
import io
import json as _json
import logging
import re
import socket
import sys
import typing
import warnings
import zlib
from contextlib import contextmanager
from http.client import HTTPMessage as _HttplibHTTPMessage
from http.client import HTTPResponse as _HttplibHTTPResponse
from socket import timeout as SocketTimeout

if typing.TYPE_CHECKING:
    from ._base_connection import BaseHTTPConnection

try:
    try:
        import brotlicffi as brotli  # type: ignore[import-not-found]
    except ImportError:
        import brotli  # type: ignore[import-not-found]
except ImportError:
    brotli = None

try:
    import zstandard as zstd
except (AttributeError, ImportError, ValueError):  # Defensive:
    HAS_ZSTD = False
else:
    # The package 'zstandard' added the 'eof' property starting
    # in v0.18.0 which we require to ensure a complete and
    # valid zstd stream was fed into the ZstdDecoder.
    # See: https://github.com/urllib3/urllib3/pull/2624
    _zstd_version = tuple(
        map(int, re.search(r"^([0-9]+)\.([0-9]+)", zstd.__version__).groups())  # type: ignore[union-attr]
    )
    if _zstd_version < (0, 18):  # Defensive:
        HAS_ZSTD = False
    else:
        HAS_ZSTD = True

from . import util
from ._base_connection import _TYPE_BODY
from ._collections import HTTPHeaderDict
from .connection import BaseSSLError, HTTPConnection, HTTPException
from .exceptions import (
    BodyNotHttplibCompatible,
    DecodeError,
    HTTPError,
    IncompleteRead,
    InvalidChunkLength,
    InvalidHeader,
    ProtocolError,
    ReadTimeoutError,
    ResponseNotChunked,
    SSLError,
)
from .util.response import is_fp_closed, is_response_to_head
from .util.retry import Retry

if typing.TYPE_CHECKING:
    from .connectionpool import HTTPConnectionPool

log = logging.getLogger(__name__)


class ContentDecoder:
    def decompress(self, data: bytes) -> bytes:
        raise NotImplementedError()

    def flush(self) -> bytes:
        raise NotImplementedError()


class DeflateDecoder(ContentDecoder):
    def __init__(self) -> None:
        self._first_try = True
        self._data = b""
        self._obj = zlib.decompressobj()

    def decompress(self, data: bytes) -> bytes:
        if not data:
            return data

        if not self._first_try:
            return self._obj.decompress(data)

        self._data += data
        try:
            decompressed = self._obj.decompress(data)
            if decompressed:
                self._first_try = False
                self._data = None  # type: ignore[assignment]
            return decompressed
        except zlib.error:
            self._first_try = False
            self._obj = zlib.decompressobj(-zlib.MAX_WBITS)
            try:
                return self.decompress(self._data)
            finally:
                self._data = None  # type: ignore[assignment]

    def flush(self) -> bytes:
        return self._obj.flush()


class GzipDecoderState:
    FIRST_MEMBER = 0
    OTHER_MEMBERS = 1
    SWALLOW_DATA = 2


class GzipDecoder(ContentDecoder):
    def __init__(self) -> None:
        self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self._state = GzipDecoderState.FIRST_MEMBER

    def decompress(self, data: bytes) -> bytes:
        ret = bytearray()
        if self._state == GzipDecoderState.SWALLOW_DATA or not data:
            return bytes(ret)
        while True:
            try:
                ret += self._obj.decompress(data)
            except zlib.error:
                previous_state = self._state
                # Ignore data after the first error
                self._state = GzipDecoderState.SWALLOW_DATA
                if previous_state == GzipDecoderState.OTHER_MEMBERS:
                    # Allow trailing garbage acceptable in other gzip clients
                    return bytes(ret)
                raise
            data = self._obj.unused_data
            if not data:
                return bytes(ret)
            self._state = GzipDecoderState.OTHER_MEMBERS
            self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)

    def flush(self) -> bytes:
        return self._obj.flush()


if brotli is not None:

    class BrotliDecoder(ContentDecoder):
        # Supports both 'brotlipy' and 'Brotli' packages
        # since they share an import name. The top branches
        # are for 'brotlipy' and bottom branches for 'Brotli'
        def __init__(self) -> None:
            self._obj = brotli.Decompressor()
            if hasattr(self._obj, "decompress"):
                setattr(self, "decompress", self._obj.decompress)
            else:
                setattr(self, "decompress", self._obj.process)

        def flush(self) -> bytes:
            if hasattr(self._obj, "flush"):
                return self._obj.flush()  # type: ignore[no-any-return]
            return b""


if HAS_ZSTD:

    class ZstdDecoder(ContentDecoder):
        def __init__(self) -> None:
            self._obj = zstd.ZstdDecompressor().decompressobj()

        def decompress(self, data: bytes) -> bytes:
            if not data:
                return b""
            data_parts = [self._obj.decompress(data)]
            while self._obj.eof and self._obj.unused_data:
                unused_data = self._obj.unused_data
                self._obj = zstd.ZstdDecompressor().decompressobj()
                data_parts.append(self._obj.decompress(unused_data))
            return b"".join(data_parts)

        def flush(self) -> bytes:
            ret = self._obj.flush()  # note: this is a no-op
            if not self._obj.eof:
                raise DecodeError("Zstandard data is incomplete")
            return ret


class MultiDecoder(ContentDecoder):
    """
    From RFC7231:
        If one or more encodings have been applied to a representation, the
        sender that applied the encodings MUST generate a Content-Encoding
        header field that lists the content codings in the order in which
        they were applied.
    """

    def __init__(self, modes: str) -> None:
        self._decoders = [_get_decoder(m.strip()) for m in modes.split(",")]

    def flush(self) -> bytes:
        return self._decoders[0].flush()

    def decompress(self, data: bytes) -> bytes:
        for d in reversed(self._decoders):
            data = d.decompress(data)
        return data


def _get_decoder(mode: str) -> ContentDecoder:
    if "," in mode:
        return MultiDecoder(mode)

    # According to RFC 9110 section 8.4.1.3, recipients should
    # consider x-gzip equivalent to gzip
    if mode in ("gzip", "x-gzip"):
        return GzipDecoder()

    if brotli is not None and mode == "br":
        return BrotliDecoder()

    if HAS_ZSTD and mode == "zstd":
        return ZstdDecoder()

    return DeflateDecoder()


class BytesQueueBuffer:
    """Memory-efficient bytes buffer

    To return decoded data in read() and still follow the BufferedIOBase API, we need a
    buffer to always return the correct amount of bytes.

    This buffer should be filled using calls to put()

    Our maximum memory usage is determined by the sum of the size of:

     * self.buffer, which contains the full data
     * the largest chunk that we will copy in get()

    The worst case scenario is a single chunk, in which case we'll make a full copy of
    the data inside get().
    """

    def __init__(self) -> None:
        self.buffer: typing.Deque[bytes] = collections.deque()
        self._size: int = 0

    def __len__(self) -> int:
        return self._size

    def put(self, data: bytes) -> None:
        self.buffer.append(data)
        self._size += len(data)

    def get(self, n: int) -> bytes:
        if n == 0:
            return b""
        elif not self.buffer:
            raise RuntimeError("buffer is empty")
        elif n < 0:
            raise ValueError("n should be > 0")

        fetched = 0
        ret = io.BytesIO()
        while fetched < n:
            remaining = n - fetched
            chunk = self.buffer.popleft()
            chunk_length = len(chunk)
            if remaining < chunk_length:
                left_chunk, right_chunk = chunk[:remaining], chunk[remaining:]
                ret.write(left_chunk)
                self.buffer.appendleft(right_chunk)
                self._size -= remaining
                break
            else:
                ret.write(chunk)
                self._size -= chunk_length
            fetched += chunk_length

            if not self.buffer:
                break

        return ret.getvalue()

    def get_all(self) -> bytes:
        buffer = self.buffer
        if not buffer:
            assert self._size == 0
            return b""
        if len(buffer) == 1:
            result = buffer.pop()
        else:
            ret = io.BytesIO()
            ret.writelines(buffer.popleft() for _ in range(len(buffer)))
            result = ret.getvalue()
        self._size = 0
        return result


class BaseHTTPResponse(io.IOBase):
    CONTENT_DECODERS = ["gzip", "x-gzip", "deflate"]
    if brotli is not None:
        CONTENT_DECODERS += ["br"]
    if HAS_ZSTD:
        CONTENT_DECODERS += ["zstd"]
    REDIRECT_STATUSES = [301, 302, 303, 307, 308]

    DECODER_ERROR_CLASSES: tuple[type[Exception], ...] = (IOError, zlib.error)
    if brotli is not None:
        DECODER_ERROR_CLASSES += (brotli.error,)

    if HAS_ZSTD:
        DECODER_ERROR_CLASSES += (zstd.ZstdError,)

    def __init__(
        self,
        *,
        headers: typing.Mapping[str, str] | typing.Mapping[bytes, bytes] | None = None,
        status: int,
        version: int,
        version_string: str,
        reason: str | None,
        decode_content: bool,
        request_url: str | None,
        retries: Retry | None = None,
    ) -> None:
        if isinstance(headers, HTTPHeaderDict):
            self.headers = headers
        else:
            self.headers = HTTPHeaderDict(headers)  # type: ignore[arg-type]
        self.status = status
        self.version = version
        self.version_string = version_string
        self.reason = reason
        self.decode_content = decode_content
        self._has_decoded_content = False
        self._request_url: str | None = request_url
        self.retries = retries

        self.chunked = False
        tr_enc = self.headers.get("transfer-encoding", "").lower()
        # Don't incur the penalty of creating a list and then discarding it
        encodings = (enc.strip() for enc in tr_enc.split(","))
        if "chunked" in encodings:
            self.chunked = True

        self._decoder: ContentDecoder | None = None
        self.length_remaining: int | None

    def get_redirect_location(self) -> str | None | typing.Literal[False]:
        """
        Should we redirect and where to?

        :returns: Truthy redirect location string if we got a redirect status
            code and valid location. ``None`` if redirect status and no
            location. ``False`` if not a redirect status code.
        """
        if self.status in self.REDIRECT_STATUSES:
            return self.headers.get("location")
        return False

    @property
    def data(self) -> bytes:
        raise NotImplementedError()

    def json(self) -> typing.Any:
        """
        Deserializes the body of the HTTP response as a Python object.

        The body of the HTTP response must be encoded using UTF-8, as per
        `RFC 8529 Section 8.1 <https://www.rfc-editor.org/rfc/rfc8259#section-8.1>`_.

        To use a custom JSON decoder pass the result of :attr:`HTTPResponse.data` to
        your custom decoder instead.

        If the body of the HTTP response is not decodable to UTF-8, a
        `UnicodeDecodeError` will be raised. If the body of the HTTP response is not a
        valid JSON document, a `json.JSONDecodeError` will be raised.

        Read more :ref:`here <json_content>`.

        :returns: The body of the HTTP response as a Python object.
        """
        data = self.data.decode("utf-8")
        return _json.loads(data)

    @property
    def url(self) -> str | None:
        raise NotImplementedError()

    @url.setter
    def url(self, url: str | None) -> None:
        raise NotImplementedError()

    @property
    def connection(self) -> BaseHTTPConnection | None:
        raise NotImplementedError()

    @property
    def retries(self) -> Retry | None:
        return self._retries

    @retries.setter
    def retries(self, retries: Retry | None) -> None:
        # Override the request_url if retries has a redirect location.
        if retries is not None and retries.history:
            self.url = retries.history[-1].redirect_location
        self._retries = retries

    def stream(
        self, amt: int | None = 2**16, decode_content: bool | None = None
    ) -> typing.Iterator[bytes]:
        raise NotImplementedError()

    def read(
        self,
        amt: int | None = None,
        decode_content: bool | None = None,
        cache_content: bool = False,
    ) -> bytes:
        raise NotImplementedError()

    def read1(
        self,
        amt: int | None = None,
        decode_content: bool | None = None,
    ) -> bytes:
        raise NotImplementedError()

    def read_chunked(
        self,
        amt: int | None = None,
        decode_content: bool | None = None,
    ) -> typing.Iterator[bytes]:
        raise NotImplementedError()

    def release_conn(self) -> None:
        raise NotImplementedError()

    def drain_conn(self) -> None:
        raise NotImplementedError()

    def shutdown(self) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()

    def _init_decoder(self) -> None:
        """
        Set-up the _decoder attribute if necessary.
        """
        # Note: content-encoding value should be case-insensitive, per RFC 7230
        # Section 3.2
        content_encoding = self.headers.get("content-encoding", "").lower()
        if self._decoder is None:
            if content_encoding in self.CONTENT_DECODERS:
                self._decoder = _get_decoder(content_encoding)
            elif "," in content_encoding:
                encodings = [
                    e.strip()
                    for e in content_encoding.split(",")
                    if e.strip() in self.CONTENT_DECODERS
                ]
                if encodings:
                    self._decoder = _get_decoder(content_encoding)

    def _decode(
        self, data: bytes, decode_content: bool | None, flush_decoder: bool
    ) -> bytes:
        """
        Decode the data passed in and potentially flush the decoder.
        """
        if not decode_content:
            if self._has_decoded_content:
                raise RuntimeError(
                    "Calling read(decode_content=False) is not supported after "
                    "read(decode_content=True) was called."
                )
            return data

        try:
            if self._decoder:
                data = self._decoder.decompress(data)
                self._has_decoded_content = True
        except self.DECODER_ERROR_CLASSES as e:
            content_encoding = self.headers.get("content-encoding", "").lower()
            raise DecodeError(
                "Received response with content-encoding: %s, but "
                "failed to decode it." % content_encoding,
                e,
            ) from e
        if flush_decoder:
            data += self._flush_decoder()

        return data

    def _flush_decoder(self) -> bytes:
        """
        Flushes the decoder. Should only be called if the decoder is actually
        being used.
        """
        if self._decoder:
            return self._decoder.decompress(b"") + self._decoder.flush()
        return b""

    # Compatibility methods for `io` module
    def readinto(self, b: bytearray) -> int:
        temp = self.read(len(b))
        if len(temp) == 0:
            return 0
        else:
            b[: len(temp)] = temp
            return len(temp)

    # Compatibility methods for http.client.HTTPResponse
    def getheaders(self) -> HTTPHeaderDict:
        warnings.warn(
            "HTTPResponse.getheaders() is deprecated and will be removed "
            "in urllib3 v2.1.0. Instead access HTTPResponse.headers directly.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.headers

    def getheader(self, name: str, default: str | None = None) -> str | None:
        warnings.warn(
            "HTTPResponse.getheader() is deprecated and will be removed "
            "in urllib3 v2.1.0. Instead use HTTPResponse.headers.get(name, default).",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.headers.get(name, default)

    # Compatibility method for http.cookiejar
    def info(self) -> HTTPHeaderDict:
        return self.headers

    def geturl(self) -> str | None:
        return self.url


class HTTPResponse(BaseHTTPResponse):
    """
    HTTP Response container.

    Backwards-compatible with :class:`http.client.HTTPResponse` but the response ``body`` is
    loaded and decoded on-demand when the ``data`` property is accessed.  This
    class is also compatible with the Python standard library's :mod:`io`
    module, and can hence be treated as a readable object in the context of that
    framework.

    Extra parameters for behaviour not present in :class:`http.client.HTTPResponse`:

    :param preload_content:
        If True, the response's body will be preloaded during construction.

    :param decode_content:
        If True, will attempt to decode the body based on the
        'content-encoding' header.

    :param original_response:
        When this HTTPResponse wrapper is generated from an :class:`http.client.HTTPResponse`
        object, it's convenient to include the original for debug purposes. It's
        otherwise unused.

    :param retries:
        The retries contains the last :class:`~urllib3.util.retry.Retry` that
        was used during the request.

    :param enforce_content_length:
        Enforce content length checking. Body returned by server must match
        value of Content-Length header, if present. Otherwise, raise error.
    """

    def __init__(
        self,
        body: _TYPE_BODY = "",
        headers: typing.Mapping[str, str] | typing.Mapping[bytes, bytes] | None = None,
        status: int = 0,
        version: int = 0,
        version_string: str = "HTTP/?",
        reason: str | None = None,
        preload_content: bool = True,
        decode_content: bool = True,
        original_response: _HttplibHTTPResponse | None = None,
        pool: HTTPConnectionPool | None = None,
        connection: HTTPConnection | None = None,
        msg: _HttplibHTTPMessage | None = None,
        retries: Retry | None = None,
        enforce_content_length: bool = True,
        request_method: str | None = None,
        request_url: str | None = None,
        auto_close: bool = True,
        sock_shutdown: typing.Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(
            headers=headers,
            status=status,
            version=version,
            version_string=version_string,
            reason=reason,
            decode_content=decode_content,
            request_url=request_url,
            retries=retries,
        )

        self.enforce_content_length = enforce_content_length
        self.auto_close = auto_close

        self._body = None
        self._fp: _HttplibHTTPResponse | None = None
        self._original_response = original_response
        self._fp_bytes_read = 0
        self.msg = msg

        if body and isinstance(body, (str, bytes)):
            self._body = body

        self._pool = pool
        self._connection = connection

        if hasattr(body, "read"):
            self._fp = body  # type: ignore[assignment]
        self._sock_shutdown = sock_shutdown

        # Are we using the chunked-style of transfer encoding?
        self.chunk_left: int | None = None

        # Determine length of response
        self.length_remaining = self._init_length(request_method)

        # Used to return the correct amount of bytes for partial read()s
        self._decoded_buffer = BytesQueueBuffer()

        # If requested, preload the body.
        if preload_content and not self._body:
            self._body = self.read(decode_content=decode_content)

    def release_conn(self) -> None:
        if not self._pool or not self._connection:
            return None

        self._pool._put_conn(self._connection)
        self._connection = None

    def drain_conn(self) -> None:
        """
        Read and discard any remaining HTTP response data in the response connection.

        Unread data in the HTTPResponse connection blocks the connection from being released back to the pool.
        """
        try:
            self.read()
        except (HTTPError, OSError, BaseSSLError, HTTPException):
            pass

    @property
    def data(self) -> bytes:
        # For backwards-compat with earlier urllib3 0.4 and earlier.
        if self._body:
            return self._body  # type: ignore[return-value]

        if self._fp:
            return self.read(cache_content=True)

        return None  # type: ignore[return-value]

    @property
    def connection(self) -> HTTPConnection | None:
        return self._connection

    def isclosed(self) -> bool:
        return is_fp_closed(self._fp)

    def tell(self) -> int:
        """
        Obtain the number of bytes pulled over the wire so far. May differ from
        the amount of content returned by :meth:``urllib3.response.HTTPResponse.read``
        if bytes are encoded on the wire (e.g, compressed).
        """
        return self._fp_bytes_read

    def _init_length(self, request_method: str | None) -> int | None:
        """
        Set initial length value for Response content if available.
        """
        length: int | None
        content_length: str | None = self.headers.get("content-length")

        if content_length is not None:
            if self.chunked:
                # This Response will fail with an IncompleteRead if it can't be
                # received as chunked. This method falls back to attempt reading
                # the response before raising an exception.
                log.warning(
                    "Received response with both Content-Length and "
                    "Transfer-Encoding set. This is expressly forbidden "
                    "by RFC 7230 sec 3.3.2. Ignoring Content-Length and "
                    "attempting to process response as Transfer-Encoding: "
                    "chunked."
                )
                return None

            try:
                # RFC 7230 section 3.3.2 specifies multiple content lengths can
                # be sent in a single Content-Length header
                # (e.g. Content-Length: 42, 42). This line ensures the values
                # are all valid ints and that as long as the `set` length is 1,
                # all values are the same. Otherwise, the header is invalid.
                lengths = {int(val) for val in content_length.split(",")}
                if len(lengths) > 1:
                    raise InvalidHeader(
                        "Content-Length contained multiple "
                        "unmatching values (%s)" % content_length
                    )
                length = lengths.pop()
            except ValueError:
                length = None
            else:
                if length < 0:
                    length = None

        else:  # if content_length is None
            length = None

        # Convert status to int for comparison
        # In some cases, httplib returns a status of "_UNKNOWN"
        try:
            status = int(self.status)
        except ValueError:
            status = 0

        # Check for responses that shouldn't include a body
        if status in (204, 304) or 100 <= status < 200 or request_method == "HEAD":
            length = 0

        return length

    @contextmanager
    def _error_catcher(self) -> typing.Generator[None]:
        """
        Catch low-level python exceptions, instead re-raising urllib3
        variants, so that low-level exceptions are not leaked in the
        high-level api.

        On exit, release the connection back to the pool.
        """
        clean_exit = False

        try:
            try:
                yield

            except SocketTimeout as e:
                # FIXME: Ideally we'd like to include the url in the ReadTimeoutError but
                # there is yet no clean way to get at it from this context.
                raise ReadTimeoutError(self._pool, None, "Read timed out.") from e  # type: ignore[arg-type]

            except BaseSSLError as e:
                # FIXME: Is there a better way to differentiate between SSLErrors?
                if "read operation timed out" not in str(e):
                    # SSL errors related to framing/MAC get wrapped and reraised here
                    raise SSLError(e) from e

                raise ReadTimeoutError(self._pool, None, "Read timed out.") from e  # type: ignore[arg-type]

            except IncompleteRead as e:
                if (
                    e.expected is not None
                    and e.partial is not None
                    and e.expected == -e.partial
                ):
                    arg = "Response may not contain content."
                else:
                    arg = f"Connection broken: {e!r}"
                raise ProtocolError(arg, e) from e

            except (HTTPException, OSError) as e:
                raise ProtocolError(f"Connection broken: {e!r}", e) from e

            # If no exception is thrown, we should avoid cleaning up
            # unnecessarily.
            clean_exit = True
        finally:
            # If we didn't terminate cleanly, we need to throw away our
            # connection.
            if not clean_exit:
                # The response may not be closed but we're not going to use it
                # anymore so close it now to ensure that the connection is
                # released back to the pool.
                if self._original_response:
                    self._original_response.close()

                # Closing the response may not actually be sufficient to close
                # everything, so if we have a hold of the connection close that
                # too.
                if self._connection:
                    self._connection.close()

            # If we hold the original response but it's closed now, we should
            # return the connection back to the pool.
            if self._original_response and self._original_response.isclosed():
                self.release_conn()

    def _fp_read(
        self,
        amt: int | None = None,
        *,
        read1: bool = False,
    ) -> bytes:
        """
        Read a response with the thought that reading the number of bytes
        larger than can fit in a 32-bit int at a time via SSL in some
        known cases leads to an overflow error that has to be prevented
        if `amt` or `self.length_remaining` indicate that a problem may
        happen.

        The known cases:
          * CPython < 3.9.7 because of a bug
            https://github.com/urllib3/urllib3/issues/2513#issuecomment-1152559900.
          * urllib3 injected with pyOpenSSL-backed SSL-support.
          * CPython < 3.10 only when `amt` does not fit 32-bit int.
        """
        assert self._fp
        c_int_max = 2**31 - 1
        if (
            (amt and amt > c_int_max)
            or (
                amt is None
                and self.length_remaining
                and self.length_remaining > c_int_max
            )
        ) and (util.IS_PYOPENSSL or sys.version_info < (3, 10)):
            if read1:
                return self._fp.read1(c_int_max)
            buffer = io.BytesIO()
            # Besides `max_chunk_amt` being a maximum chunk size, it
            # affects memory overhead of reading a response by this
            # method in CPython.
            # `c_int_max` equal to 2 GiB - 1 byte is the actual maximum
            # chunk size that does not lead to an overflow error, but
            # 256 MiB is a compromise.
            max_chunk_amt = 2**28
            while amt is None or amt != 0:
                if amt is not None:
                    chunk_amt = min(amt, max_chunk_amt)
                    amt -= chunk_amt
                else:
                    chunk_amt = max_chunk_amt
                data = self._fp.read(chunk_amt)
                if not data:
                    break
                buffer.write(data)
                del data  # to reduce peak memory usage by `max_chunk_amt`.
            return buffer.getvalue()
        elif read1:
            return self._fp.read1(amt) if amt is not None else self._fp.read1()
        else:
            # StringIO doesn't like amt=None
            return self._fp.read(amt) if amt is not None else self._fp.read()

    def _raw_read(
        self,
        amt: int | None = None,
        *,
        read1: bool = False,
    ) -> bytes:
        """
        Reads `amt` of bytes from the socket.
        """
        if self._fp is None:
            return None  # type: ignore[return-value]

        fp_closed = getattr(self._fp, "closed", False)

        with self._error_catcher():
            data = self._fp_read(amt, read1=read1) if not fp_closed else b""
            if amt is not None and amt != 0 and not data:
                # Platform-specific: Buggy versions of Python.
                # Close the connection when no data is returned
                #
                # This is redundant to what httplib/http.client _should_
                # already do.  However, versions of python released before
                # December 15, 2012 (http://bugs.python.org/issue16298) do
                # not properly close the connection in all cases. There is
                # no harm in redundantly calling close.
                self._fp.close()
                if (
                    self.enforce_content_length
                    and self.length_remaining is not None
                    and self.length_remaining != 0
                ):
                    # This is an edge case that httplib failed to cover due
                    # to concerns of backward compatibility. We're
                    # addressing it here to make sure IncompleteRead is
                    # raised during streaming, so all calls with incorrect
                    # Content-Length are caught.
                    raise IncompleteRead(self._fp_bytes_read, self.length_remaining)
            elif read1 and (
                (amt != 0 and not data) or self.length_remaining == len(data)
            ):
                # All data has been read, but `self._fp.read1` in
                # CPython 3.12 and older doesn't always close
                # `http.client.HTTPResponse`, so we close it here.
                # See https://github.com/python/cpython/issues/113199
                self._fp.close()

        if data:
            self._fp_bytes_read += len(data)
            if self.length_remaining is not None:
                self.length_remaining -= len(data)
        return data

    def read(
        self,
        amt: int | None = None,
        decode_content: bool | None = None,
        cache_content: bool = False,
    ) -> bytes:
        """
        Similar to :meth:`http.client.HTTPResponse.read`, but with two additional
        parameters: ``decode_content`` and ``cache_content``.

        :param amt:
            How much of the content to read. If specified, caching is skipped
            because it doesn't make sense to cache partial content as the full
            response.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.

        :param cache_content:
            If True, will save the returned data such that the same result is
            returned despite of the state of the underlying file object. This
            is useful if you want the ``.data`` property to continue working
            after having ``.read()`` the file object. (Overridden if ``amt`` is
            set.)
        """
        self._init_decoder()
        if decode_content is None:
            decode_content = self.decode_content

        if amt and amt < 0:
            # Negative numbers and `None` should be treated the same.
            amt = None
        elif amt is not None:
            cache_content = False

            if len(self._decoded_buffer) >= amt:
                return self._decoded_buffer.get(amt)

        data = self._raw_read(amt)

        flush_decoder = amt is None or (amt != 0 and not data)

        if not data and len(self._decoded_buffer) == 0:
            return data

        if amt is None:
            data = self._decode(data, decode_content, flush_decoder)
            if cache_content:
                self._body = data
        else:
            # do not waste memory on buffer when not decoding
            if not decode_content:
                if self._has_decoded_content:
                    raise RuntimeError(
                        "Calling read(decode_content=False) is not supported after "
                        "read(decode_content=True) was called."
                    )
                return data

            decoded_data = self._decode(data, decode_content, flush_decoder)
            self._decoded_buffer.put(decoded_data)

            while len(self._decoded_buffer) < amt and data:
                # TODO make sure to initially read enough data to get past the headers
                # For example, the GZ file header takes 10 bytes, we don't want to read
                # it one byte at a time
                data = self._raw_read(amt)
                decoded_data = self._decode(data, decode_content, flush_decoder)
                self._decoded_buffer.put(decoded_data)
            data = self._decoded_buffer.get(amt)

        return data

    def read1(
        self,
        amt: int | None = None,
        decode_content: bool | None = None,
    ) -> bytes:
        """
        Similar to ``http.client.HTTPResponse.read1`` and documented
        in :meth:`io.BufferedReader.read1`, but with an additional parameter:
        ``decode_content``.

        :param amt:
            How much of the content to read.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.
        """
        if decode_content is None:
            decode_content = self.decode_content
        if amt and amt < 0:
            # Negative numbers and `None` should be treated the same.
            amt = None
        # try and respond without going to the network
        if self._has_decoded_content:
            if not decode_content:
                raise RuntimeError(
                    "Calling read1(decode_content=False) is not supported after "
                    "read1(decode_content=True) was called."
                )
            if len(self._decoded_buffer) > 0:
                if amt is None:
                    return self._decoded_buffer.get_all()
                return self._decoded_buffer.get(amt)
        if amt == 0:
            return b""

        # FIXME, this method's type doesn't say returning None is possible
        data = self._raw_read(amt, read1=True)
        if not decode_content or data is None:
            return data

        self._init_decoder()
        while True:
            flush_decoder = not data
            decoded_data = self._decode(data, decode_content, flush_decoder)
            self._decoded_buffer.put(decoded_data)
            if decoded_data or flush_decoder:
                break
            data = self._raw_read(8192, read1=True)

        if amt is None:
            return self._decoded_buffer.get_all()
        return self._decoded_buffer.get(amt)

    def stream(
        self, amt: int | None = 2**16, decode_content: bool | None = None
    ) -> typing.Generator[bytes]:
        """
        A generator wrapper for the read() method. A call will block until
        ``amt`` bytes have been read from the connection or until the
        connection is closed.

        :param amt:
            How much of the content to read. The generator will return up to
            much data per iteration, but may return less. This is particularly
            likely when using compressed data. However, the empty string will
            never be returned.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.
        """
        if self.chunked and self.supports_chunked_reads():
            yield from self.read_chunked(amt, decode_content=decode_content)
        else:
            while not is_fp_closed(self._fp) or len(self._decoded_buffer) > 0:
                data = self.read(amt=amt, decode_content=decode_content)

                if data:
                    yield data

    # Overrides from io.IOBase
    def readable(self) -> bool:
        return True

    def shutdown(self) -> None:
        if not self._sock_shutdown:
            raise ValueError("Cannot shutdown socket as self._sock_shutdown is not set")
        self._sock_shutdown(socket.SHUT_RD)

    def close(self) -> None:
        self._sock_shutdown = None

        if not self.closed and self._fp:
            self._fp.close()

        if self._connection:
            self._connection.close()

        if not self.auto_close:
            io.IOBase.close(self)

    @property
    def closed(self) -> bool:
        if not self.auto_close:
            return io.IOBase.closed.__get__(self)  # type: ignore[no-any-return]
        elif self._fp is None:
            return True
        elif hasattr(self._fp, "isclosed"):
            return self._fp.isclosed()
        elif hasattr(self._fp, "closed"):
            return self._fp.closed
        else:
            return True

    def fileno(self) -> int:
        if self._fp is None:
            raise OSError("HTTPResponse has no file to get a fileno from")
        elif hasattr(self._fp, "fileno"):
            return self._fp.fileno()
        else:
            raise OSError(
                "The file-like object this HTTPResponse is wrapped "
                "around has no file descriptor"
            )

    def flush(self) -> None:
        if (
            self._fp is not None
            and hasattr(self._fp, "flush")
            and not getattr(self._fp, "closed", False)
        ):
            return self._fp.flush()

    def supports_chunked_reads(self) -> bool:
        """
        Checks if the underlying file-like object looks like a
        :class:`http.client.HTTPResponse` object. We do this by testing for
        the fp attribute. If it is present we assume it returns raw chunks as
        processed by read_chunked().
        """
        return hasattr(self._fp, "fp")

    def _update_chunk_length(self) -> None:
        # First, we'll figure out length of a chunk and then
        # we'll try to read it from socket.
        if self.chunk_left is not None:
            return None
        line = self._fp.fp.readline()  # type: ignore[union-attr]
        line = line.split(b";", 1)[0]
        try:
            self.chunk_left = int(line, 16)
        except ValueError:
            self.close()
            if line:
                # Invalid chunked protocol response, abort.
                raise InvalidChunkLength(self, line) from None
            else:
                # Truncated at start of next chunk
                raise ProtocolError("Response ended prematurely") from None

    def _handle_chunk(self, amt: int | None) -> bytes:
        returned_chunk = None
        if amt is None:
            chunk = self._fp._safe_read(self.chunk_left)  # type: ignore[union-attr]
            returned_chunk = chunk
            self._fp._safe_read(2)  # type: ignore[union-attr] # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
        elif self.chunk_left is not None and amt < self.chunk_left:
            value = self._fp._safe_read(amt)  # type: ignore[union-attr]
            self.chunk_left = self.chunk_left - amt
            returned_chunk = value
        elif amt == self.chunk_left:
            value = self._fp._safe_read(amt)  # type: ignore[union-attr]
            self._fp._safe_read(2)  # type: ignore[union-attr] # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
            returned_chunk = value
        else:  # amt > self.chunk_left
            returned_chunk = self._fp._safe_read(self.chunk_left)  # type: ignore[union-attr]
            self._fp._safe_read(2)  # type: ignore[union-attr] # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
        return returned_chunk  # type: ignore[no-any-return]

    def read_chunked(
        self, amt: int | None = None, decode_content: bool | None = None
    ) -> typing.Generator[bytes]:
        """
        Similar to :meth:`HTTPResponse.read`, but with an additional
        parameter: ``decode_content``.

        :param amt:
            How much of the content to read. If specified, caching is skipped
            because it doesn't make sense to cache partial content as the full
            response.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.
        """
        self._init_decoder()
        # FIXME: Rewrite this method and make it a class with a better structured logic.
        if not self.chunked:
            raise ResponseNotChunked(
                "Response is not chunked. "
                "Header 'transfer-encoding: chunked' is missing."
            )
        if not self.supports_chunked_reads():
            raise BodyNotHttplibCompatible(
                "Body should be http.client.HTTPResponse like. "
                "It should have have an fp attribute which returns raw chunks."
            )

        with self._error_catcher():
            # Don't bother reading the body of a HEAD request.
            if self._original_response and is_response_to_head(self._original_response):
                self._original_response.close()
                return None

            # If a response is already read and closed
            # then return immediately.
            if self._fp.fp is None:  # type: ignore[union-attr]
                return None

            if amt and amt < 0:
                # Negative numbers and `None` should be treated the same,
                # but httplib handles only `None` correctly.
                amt = None

            while True:
                self._update_chunk_length()
                if self.chunk_left == 0:
                    break
                chunk = self._handle_chunk(amt)
                decoded = self._decode(
                    chunk, decode_content=decode_content, flush_decoder=False
                )
                if decoded:
                    yield decoded

            if decode_content:
                # On CPython and PyPy, we should never need to flush the
                # decoder. However, on Jython we *might* need to, so
                # lets defensively do it anyway.
                decoded = self._flush_decoder()
                if decoded:  # Platform-specific: Jython.
                    yield decoded

            # Chunk content ends with \r\n: discard it.
            while self._fp is not None:
                line = self._fp.fp.readline()
                if not line:
                    # Some sites may not end with '\r\n'.
                    break
                if line == b"\r\n":
                    break

            # We read everything; close the "file".
            if self._original_response:
                self._original_response.close()

    @property
    def url(self) -> str | None:
        """
        Returns the URL that was the source of this response.
        If the request that generated this response redirected, this method
        will return the final redirect location.
        """
        return self._request_url

    @url.setter
    def url(self, url: str) -> None:
        self._request_url = url

    def __iter__(self) -> typing.Iterator[bytes]:
        buffer: list[bytes] = []
        for chunk in self.stream(decode_content=True):
            if b"\n" in chunk:
                chunks = chunk.split(b"\n")
                yield b"".join(buffer) + chunks[0] + b"\n"
                for x in chunks[1:-1]:
                    yield x + b"\n"
                if chunks[-1]:
                    buffer = [chunks[-1]]
                else:
                    buffer = []
            else:
                buffer.append(chunk)
        if buffer:
            yield b"".join(buffer)

# === NexusCore/openenv\Lib\site-packages\IPython\sphinxext\ipython_directive.py ===
# -*- coding: utf-8 -*-
"""
Sphinx directive to support embedded IPython code.

IPython provides an extension for `Sphinx <http://www.sphinx-doc.org/>`_ to
highlight and run code.

This directive allows pasting of entire interactive IPython sessions, prompts
and all, and their code will actually get re-executed at doc build time, with
all prompts renumbered sequentially. It also allows you to input code as a pure
python input by giving the argument python to the directive. The output looks
like an interactive ipython section.

Here is an example of how the IPython directive can
**run** python code, at build time.

.. ipython::

   In [1]: 1+1

   In [1]: import datetime
      ...: datetime.date.fromisoformat('2022-02-22')

It supports IPython construct that plain
Python does not understand (like magics):

.. ipython::

   In [0]: import time

   In [0]: %pdoc time.sleep

This will also support top-level async when using IPython 7.0+

.. ipython::

   In [2]: import asyncio
      ...: print('before')
      ...: await asyncio.sleep(1)
      ...: print('after')


The namespace will persist across multiple code chucks, Let's define a variable:

.. ipython::

   In [0]: who = "World"

And now say hello:

.. ipython::

   In [0]: print('Hello,', who)

If the current section raises an exception, you can add the ``:okexcept:`` flag
to the current block, otherwise the build will fail.

.. ipython::
   :okexcept:

   In [1]: 1/0

IPython Sphinx directive module
===============================

To enable this directive, simply list it in your Sphinx ``conf.py`` file
(making sure the directory where you placed it is visible to sphinx, as is
needed for all Sphinx directives). For example, to enable syntax highlighting
and the IPython directive::

    extensions = ['IPython.sphinxext.ipython_console_highlighting',
                  'IPython.sphinxext.ipython_directive']

The IPython directive outputs code-blocks with the language 'ipython'. So
if you do not have the syntax highlighting extension enabled as well, then
all rendered code-blocks will be uncolored. By default this directive assumes
that your prompts are unchanged IPython ones, but this can be customized.
The configurable options that can be placed in conf.py are:

ipython_savefig_dir:
    The directory in which to save the figures. This is relative to the
    Sphinx source directory. The default is `html_static_path`.
ipython_rgxin:
    The compiled regular expression to denote the start of IPython input
    lines. The default is ``re.compile('In \\[(\\d+)\\]:\\s?(.*)\\s*')``. You
    shouldn't need to change this.
ipython_warning_is_error: [default to True]
    Fail the build if something unexpected happen, for example if a block raise
    an exception but does not have the `:okexcept:` flag. The exact behavior of
    what is considered strict, may change between the sphinx directive version.
ipython_rgxout:
    The compiled regular expression to denote the start of IPython output
    lines. The default is ``re.compile('Out\\[(\\d+)\\]:\\s?(.*)\\s*')``. You
    shouldn't need to change this.
ipython_promptin:
    The string to represent the IPython input prompt in the generated ReST.
    The default is ``'In [%d]:'``. This expects that the line numbers are used
    in the prompt.
ipython_promptout:
    The string to represent the IPython prompt in the generated ReST. The
    default is ``'Out [%d]:'``. This expects that the line numbers are used
    in the prompt.
ipython_mplbackend:
    The string which specifies if the embedded Sphinx shell should import
    Matplotlib and set the backend. The value specifies a backend that is
    passed to `matplotlib.use()` before any lines in `ipython_execlines` are
    executed. If not specified in conf.py, then the default value of 'agg' is
    used. To use the IPython directive without matplotlib as a dependency, set
    the value to `None`. It may end up that matplotlib is still imported
    if the user specifies so in `ipython_execlines` or makes use of the
    @savefig pseudo decorator.
ipython_execlines:
    A list of strings to be exec'd in the embedded Sphinx shell. Typical
    usage is to make certain packages always available. Set this to an empty
    list if you wish to have no imports always available. If specified in
    ``conf.py`` as `None`, then it has the effect of making no imports available.
    If omitted from conf.py altogether, then the default value of
    ['import numpy as np', 'import matplotlib.pyplot as plt'] is used.
ipython_holdcount
    When the @suppress pseudo-decorator is used, the execution count can be
    incremented or not. The default behavior is to hold the execution count,
    corresponding to a value of `True`. Set this to `False` to increment
    the execution count after each suppressed command.

As an example, to use the IPython directive when `matplotlib` is not available,
one sets the backend to `None`::

    ipython_mplbackend = None

An example usage of the directive is:

.. code-block:: rst

    .. ipython::

        In [1]: x = 1

        In [2]: y = x**2

        In [3]: print(y)

See http://matplotlib.org/sampledoc/ipython_directive.html for additional
documentation.

Pseudo-Decorators
=================

Note: Only one decorator is supported per input. If more than one decorator
is specified, then only the last one is used.

In addition to the Pseudo-Decorators/options described at the above link,
several enhancements have been made. The directive will emit a message to the
console at build-time if code-execution resulted in an exception or warning.
You can suppress these on a per-block basis by specifying the :okexcept:
or :okwarning: options:

.. code-block:: rst

    .. ipython::
        :okexcept:
        :okwarning:

        In [1]: 1/0
        In [2]: # raise warning.

To Do
=====

- Turn the ad-hoc test() function into a real test suite.
- Break up ipython-specific functionality from matplotlib stuff into better
  separated code.

"""

# Authors
# =======
#
# - John D Hunter: original author.
# - Fernando Perez: refactoring, documentation, cleanups, port to 0.11.
# - VáclavŠmilauer <eudoxos-AT-arcig.cz>: Prompt generalizations.
# - Skipper Seabold, refactoring, cleanups, pure python addition

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import atexit
import errno
import os
import pathlib
import re
import sys
import tempfile
import ast
import warnings
import shutil
from io import StringIO
from typing import Any, Dict, Set

# Third-party
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive
from sphinx.util import logging

# Our own
from traitlets.config import Config
from IPython import InteractiveShell
from IPython.core.profiledir import ProfileDir

use_matplotlib = False
try:
    import matplotlib
    use_matplotlib = True
except Exception:
    pass

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------
# for tokenizing blocks
COMMENT, INPUT, OUTPUT =  range(3)

PSEUDO_DECORATORS = ["suppress", "verbatim", "savefig", "doctest"]

#-----------------------------------------------------------------------------
# Functions and class declarations
#-----------------------------------------------------------------------------

def block_parser(part, rgxin, rgxout, fmtin, fmtout):
    """
    part is a string of ipython text, comprised of at most one
    input, one output, comments, and blank lines.  The block parser
    parses the text into a list of::

      blocks = [ (TOKEN0, data0), (TOKEN1, data1), ...]

    where TOKEN is one of [COMMENT | INPUT | OUTPUT ] and
    data is, depending on the type of token::

      COMMENT : the comment string

      INPUT: the (DECORATOR, INPUT_LINE, REST) where
         DECORATOR: the input decorator (or None)
         INPUT_LINE: the input as string (possibly multi-line)
         REST : any stdout generated by the input line (not OUTPUT)

      OUTPUT: the output string, possibly multi-line

    """
    block = []
    lines = part.split('\n')
    N = len(lines)
    i = 0
    decorator = None
    while 1:

        if i==N:
            # nothing left to parse -- the last line
            break

        line = lines[i]
        i += 1
        line_stripped = line.strip()
        if line_stripped.startswith('#'):
            block.append((COMMENT, line))
            continue

        if any(
            line_stripped.startswith("@" + pseudo_decorator)
            for pseudo_decorator in PSEUDO_DECORATORS
        ):
            if decorator:
                raise RuntimeError(
                    "Applying multiple pseudo-decorators on one line is not supported"
                )
            else:
                decorator = line_stripped
                continue

        # does this look like an input line?
        matchin = rgxin.match(line)
        if matchin:
            lineno, inputline = int(matchin.group(1)), matchin.group(2)

            # the ....: continuation string
            continuation = '   %s:'%''.join(['.']*(len(str(lineno))+2))
            Nc = len(continuation)
            # input lines can continue on for more than one line, if
            # we have a '\' line continuation char or a function call
            # echo line 'print'.  The input line can only be
            # terminated by the end of the block or an output line, so
            # we parse out the rest of the input line if it is
            # multiline as well as any echo text

            rest = []
            while i<N:

                # look ahead; if the next line is blank, or a comment, or
                # an output line, we're done

                nextline = lines[i]
                matchout = rgxout.match(nextline)
                # print("nextline=%s, continuation=%s, starts=%s"%(nextline, continuation, nextline.startswith(continuation)))
                if matchout or nextline.startswith('#'):
                    break
                elif nextline.startswith(continuation):
                    # The default ipython_rgx* treat the space following the colon as optional.
                    # However, If the space is there we must consume it or code
                    # employing the cython_magic extension will fail to execute.
                    #
                    # This works with the default ipython_rgx* patterns,
                    # If you modify them, YMMV.
                    nextline = nextline[Nc:]
                    if nextline and nextline[0] == ' ':
                        nextline = nextline[1:]

                    inputline += '\n' +  nextline
                else:
                    rest.append(nextline)
                i+= 1

            block.append((INPUT, (decorator, inputline, '\n'.join(rest))))
            continue

        # if it looks like an output line grab all the text to the end
        # of the block
        matchout = rgxout.match(line)
        if matchout:
            lineno, output = int(matchout.group(1)), matchout.group(2)
            if i<N-1:
                output = '\n'.join([output] + lines[i:])

            block.append((OUTPUT, output))
            break

    return block


class EmbeddedSphinxShell:
    """An embedded IPython instance to run inside Sphinx"""

    def __init__(self, exec_lines=None):

        self.cout = StringIO()

        if exec_lines is None:
            exec_lines = []

        # Create config object for IPython
        config = Config()
        config.HistoryManager.hist_file = ':memory:'
        config.InteractiveShell.autocall = False
        config.InteractiveShell.autoindent = False
        config.InteractiveShell.colors = "nocolor"

        # create a profile so instance history isn't saved
        tmp_profile_dir = tempfile.mkdtemp(prefix='profile_')
        profname = 'auto_profile_sphinx_build'
        pdir = os.path.join(tmp_profile_dir,profname)
        profile = ProfileDir.create_profile_dir(pdir)

        # Create and initialize global ipython, but don't start its mainloop.
        # This will persist across different EmbeddedSphinxShell instances.
        IP = InteractiveShell.instance(config=config, profile_dir=profile)
        atexit.register(self.cleanup)

        # Store a few parts of IPython we'll need.
        self.IP = IP
        self.user_ns = self.IP.user_ns
        self.user_global_ns = self.IP.user_global_ns

        self.input = ''
        self.output = ''
        self.tmp_profile_dir = tmp_profile_dir

        self.is_verbatim = False
        self.is_doctest = False
        self.is_suppress = False

        # Optionally, provide more detailed information to shell.
        # this is assigned by the SetUp method of IPythonDirective
        # to point at itself.
        #
        # So, you can access handy things at self.directive.state
        self.directive = None

        # on the first call to the savefig decorator, we'll import
        # pyplot as plt so we can make a call to the plt.gcf().savefig
        self._pyplot_imported = False

        # Prepopulate the namespace.
        for line in exec_lines:
            self.process_input_line(line, store_history=False)

    def cleanup(self):
        shutil.rmtree(self.tmp_profile_dir, ignore_errors=True)

    def clear_cout(self):
        self.cout.seek(0)
        self.cout.truncate(0)

    def process_input_line(self, line, store_history):
        return self.process_input_lines([line], store_history=store_history)

    def process_input_lines(self, lines, store_history=True):
        """process the input, capturing stdout"""
        stdout = sys.stdout
        source_raw = '\n'.join(lines)
        try:
            sys.stdout = self.cout
            self.IP.run_cell(source_raw, store_history=store_history)
        finally:
            sys.stdout = stdout

    def process_image(self, decorator):
        """
        # build out an image directive like
        # .. image:: somefile.png
        #    :width 4in
        #
        # from an input like
        # savefig somefile.png width=4in
        """
        savefig_dir = self.savefig_dir
        source_dir = self.source_dir
        saveargs = decorator.split(' ')
        filename = saveargs[1]
        # insert relative path to image file in source
        # as absolute path for Sphinx
        # sphinx expects a posix path, even on Windows
        path = pathlib.Path(savefig_dir, filename)
        outfile = '/' + path.relative_to(source_dir).as_posix()

        imagerows = ['.. image:: %s' % outfile]

        for kwarg in saveargs[2:]:
            arg, val = kwarg.split('=')
            arg = arg.strip()
            val = val.strip()
            imagerows.append('   :%s: %s'%(arg, val))

        image_file = os.path.basename(outfile) # only return file name
        image_directive = '\n'.join(imagerows)
        return image_file, image_directive

    # Callbacks for each type of token
    def process_input(self, data, input_prompt, lineno):
        """
        Process data block for INPUT token.

        """
        decorator, input, rest = data
        image_file = None
        image_directive = None

        is_verbatim = decorator=='@verbatim' or self.is_verbatim
        is_doctest = (decorator is not None and \
                     decorator.startswith('@doctest')) or self.is_doctest
        is_suppress = decorator=='@suppress' or self.is_suppress
        is_okexcept = decorator=='@okexcept' or self.is_okexcept
        is_okwarning = decorator=='@okwarning' or self.is_okwarning
        is_savefig = decorator is not None and \
                     decorator.startswith('@savefig')

        input_lines = input.split('\n')
        if len(input_lines) > 1:
            if input_lines[-1] != "":
                input_lines.append('') # make sure there's a blank line
                                       # so splitter buffer gets reset

        continuation = '   %s:'%''.join(['.']*(len(str(lineno))+2))

        if is_savefig:
            image_file, image_directive = self.process_image(decorator)

        ret = []
        is_semicolon = False

        # Hold the execution count, if requested to do so.
        if is_suppress and self.hold_count:
            store_history = False
        else:
            store_history = True

        # Note: catch_warnings is not thread safe
        with warnings.catch_warnings(record=True) as ws:
            if input_lines[0].endswith(';'):
                is_semicolon = True
            #for i, line in enumerate(input_lines):

            # process the first input line
            if is_verbatim:
                self.process_input_lines([''])
                self.IP.execution_count += 1 # increment it anyway
            else:
                # only submit the line in non-verbatim mode
                self.process_input_lines(input_lines, store_history=store_history)

        if not is_suppress:
            for i, line in enumerate(input_lines):
                if i == 0:
                    formatted_line = '%s %s'%(input_prompt, line)
                else:
                    formatted_line = '%s %s'%(continuation, line)
                ret.append(formatted_line)

        if not is_suppress and len(rest.strip()) and is_verbatim:
            # The "rest" is the standard output of the input. This needs to be
            # added when in verbatim mode. If there is no "rest", then we don't
            # add it, as the new line will be added by the processed output.
            ret.append(rest)

        # Fetch the processed output. (This is not the submitted output.)
        self.cout.seek(0)
        processed_output = self.cout.read()
        if not is_suppress and not is_semicolon:
            #
            # In IPythonDirective.run, the elements of `ret` are eventually
            # combined such that '' entries correspond to newlines. So if
            # `processed_output` is equal to '', then the adding it to `ret`
            # ensures that there is a blank line between consecutive inputs
            # that have no outputs, as in:
            #
            #    In [1]: x = 4
            #
            #    In [2]: x = 5
            #
            # When there is processed output, it has a '\n' at the tail end. So
            # adding the output to `ret` will provide the necessary spacing
            # between consecutive input/output blocks, as in:
            #
            #   In [1]: x
            #   Out[1]: 5
            #
            #   In [2]: x
            #   Out[2]: 5
            #
            # When there is stdout from the input, it also has a '\n' at the
            # tail end, and so this ensures proper spacing as well. E.g.:
            #
            #   In [1]: print(x)
            #   5
            #
            #   In [2]: x = 5
            #
            # When in verbatim mode, `processed_output` is empty (because
            # nothing was passed to IP. Sometimes the submitted code block has
            # an Out[] portion and sometimes it does not. When it does not, we
            # need to ensure proper spacing, so we have to add '' to `ret`.
            # However, if there is an Out[] in the submitted code, then we do
            # not want to add a newline as `process_output` has stuff to add.
            # The difficulty is that `process_input` doesn't know if
            # `process_output` will be called---so it doesn't know if there is
            # Out[] in the code block. The requires that we include a hack in
            # `process_block`. See the comments there.
            #
            ret.append(processed_output)
        elif is_semicolon:
            # Make sure there is a newline after the semicolon.
            ret.append('')

        # context information
        filename = "Unknown"
        lineno = 0
        if self.directive.state:
            filename = self.directive.state.document.current_source
            lineno = self.directive.state.document.current_line

        # Use sphinx logger for warnings
        logger = logging.getLogger(__name__)

        # output any exceptions raised during execution to stdout
        # unless :okexcept: has been specified.
        if not is_okexcept and (
            ("Traceback" in processed_output) or ("SyntaxError" in processed_output)
        ):
            s = "\n>>>" + ("-" * 73) + "\n"
            s += "Exception in %s at block ending on line %s\n" % (filename, lineno)
            s += "Specify :okexcept: as an option in the ipython:: block to suppress this message\n"
            s += processed_output + "\n"
            s += "<<<" + ("-" * 73)
            logger.warning(s)
            if self.warning_is_error:
                raise RuntimeError(
                    "Unexpected exception in `{}` line {}".format(filename, lineno)
                )

        # output any warning raised during execution to stdout
        # unless :okwarning: has been specified.
        if not is_okwarning:
            for w in ws:
                s = "\n>>>" + ("-" * 73) + "\n"
                s += "Warning in %s at block ending on line %s\n" % (filename, lineno)
                s += "Specify :okwarning: as an option in the ipython:: block to suppress this message\n"
                s += ("-" * 76) + "\n"
                s += warnings.formatwarning(
                    w.message, w.category, w.filename, w.lineno, w.line
                )
                s += "<<<" + ("-" * 73)
                logger.warning(s)
                if self.warning_is_error:
                    raise RuntimeError(
                        "Unexpected warning in `{}` line {}".format(filename, lineno)
                    )

        self.clear_cout()
        return (ret, input_lines, processed_output,
                is_doctest, decorator, image_file, image_directive)


    def process_output(self, data, output_prompt, input_lines, output,
                       is_doctest, decorator, image_file):
        """
        Process data block for OUTPUT token.

        """
        # Recall: `data` is the submitted output, and `output` is the processed
        # output from `input_lines`.

        TAB = ' ' * 4

        if is_doctest and output is not None:

            found = output # This is the processed output
            found = found.strip()
            submitted = data.strip()

            if self.directive is None:
                source = 'Unavailable'
                content = 'Unavailable'
            else:
                source = self.directive.state.document.current_source
                content = self.directive.content
                # Add tabs and join into a single string.
                content = '\n'.join([TAB + line for line in content])

            # Make sure the output contains the output prompt.
            ind = found.find(output_prompt)
            if ind < 0:
                e = ('output does not contain output prompt\n\n'
                     'Document source: {0}\n\n'
                     'Raw content: \n{1}\n\n'
                     'Input line(s):\n{TAB}{2}\n\n'
                     'Output line(s):\n{TAB}{3}\n\n')
                e = e.format(source, content, '\n'.join(input_lines),
                             repr(found), TAB=TAB)
                raise RuntimeError(e)
            found = found[len(output_prompt):].strip()

            # Handle the actual doctest comparison.
            if decorator.strip() == '@doctest':
                # Standard doctest
                if found != submitted:
                    e = ('doctest failure\n\n'
                         'Document source: {0}\n\n'
                         'Raw content: \n{1}\n\n'
                         'On input line(s):\n{TAB}{2}\n\n'
                         'we found output:\n{TAB}{3}\n\n'
                         'instead of the expected:\n{TAB}{4}\n\n')
                    e = e.format(source, content, '\n'.join(input_lines),
                                 repr(found), repr(submitted), TAB=TAB)
                    raise RuntimeError(e)
            else:
                self.custom_doctest(decorator, input_lines, found, submitted)

        # When in verbatim mode, this holds additional submitted output
        # to be written in the final Sphinx output.
        # https://github.com/ipython/ipython/issues/5776
        out_data = []

        is_verbatim = decorator=='@verbatim' or self.is_verbatim
        if is_verbatim and data.strip():
            # Note that `ret` in `process_block` has '' as its last element if
            # the code block was in verbatim mode. So if there is no submitted
            # output, then we will have proper spacing only if we do not add
            # an additional '' to `out_data`. This is why we condition on
            # `and data.strip()`.

            # The submitted output has no output prompt. If we want the
            # prompt and the code to appear, we need to join them now
            # instead of adding them separately---as this would create an
            # undesired newline. How we do this ultimately depends on the
            # format of the output regex. I'll do what works for the default
            # prompt for now, and we might have to adjust if it doesn't work
            # in other cases. Finally, the submitted output does not have
            # a trailing newline, so we must add it manually.
            out_data.append("{0} {1}\n".format(output_prompt, data))

        return out_data

    def process_comment(self, data):
        """Process data fPblock for COMMENT token."""
        if not self.is_suppress:
            return [data]

    def save_image(self, image_file):
        """
        Saves the image file to disk.
        """
        self.ensure_pyplot()
        command = 'plt.gcf().savefig("%s")'%image_file
        # print('SAVEFIG', command)  # dbg
        self.process_input_line('bookmark ipy_thisdir', store_history=False)
        self.process_input_line('cd -b ipy_savedir', store_history=False)
        self.process_input_line(command, store_history=False)
        self.process_input_line('cd -b ipy_thisdir', store_history=False)
        self.process_input_line('bookmark -d ipy_thisdir', store_history=False)
        self.clear_cout()

    def process_block(self, block):
        """
        process block from the block_parser and return a list of processed lines
        """
        ret = []
        output = None
        input_lines = None
        lineno = self.IP.execution_count

        input_prompt = self.promptin % lineno
        output_prompt = self.promptout % lineno
        image_file = None
        image_directive = None

        found_input = False
        for token, data in block:
            if token == COMMENT:
                out_data = self.process_comment(data)
            elif token == INPUT:
                found_input = True
                (out_data, input_lines, output, is_doctest,
                 decorator, image_file, image_directive) = \
                          self.process_input(data, input_prompt, lineno)
            elif token == OUTPUT:
                if not found_input:

                    TAB = ' ' * 4
                    linenumber = 0
                    source = 'Unavailable'
                    content = 'Unavailable'
                    if self.directive:
                        linenumber = self.directive.state.document.current_line
                        source = self.directive.state.document.current_source
                        content = self.directive.content
                        # Add tabs and join into a single string.
                        content = '\n'.join([TAB + line for line in content])

                    e = ('\n\nInvalid block: Block contains an output prompt '
                         'without an input prompt.\n\n'
                         'Document source: {0}\n\n'
                         'Content begins at line {1}: \n\n{2}\n\n'
                         'Problematic block within content: \n\n{TAB}{3}\n\n')
                    e = e.format(source, linenumber, content, block, TAB=TAB)

                    # Write, rather than include in exception, since Sphinx
                    # will truncate tracebacks.
                    sys.stdout.write(e)
                    raise RuntimeError('An invalid block was detected.')
                out_data = \
                    self.process_output(data, output_prompt, input_lines,
                                        output, is_doctest, decorator,
                                        image_file)
                if out_data:
                    # Then there was user submitted output in verbatim mode.
                    # We need to remove the last element of `ret` that was
                    # added in `process_input`, as it is '' and would introduce
                    # an undesirable newline.
                    assert(ret[-1] == '')
                    del ret[-1]

            if out_data:
                ret.extend(out_data)

        # save the image files
        if image_file is not None:
            self.save_image(image_file)

        return ret, image_directive

    def ensure_pyplot(self):
        """
        Ensures that pyplot has been imported into the embedded IPython shell.

        Also, makes sure to set the backend appropriately if not set already.

        """
        # We are here if the @figure pseudo decorator was used. Thus, it's
        # possible that we could be here even if python_mplbackend were set to
        # `None`. That's also strange and perhaps worthy of raising an
        # exception, but for now, we just set the backend to 'agg'.

        if not self._pyplot_imported:
            if 'matplotlib.backends' not in sys.modules:
                # Then ipython_matplotlib was set to None but there was a
                # call to the @figure decorator (and ipython_execlines did
                # not set a backend).
                #raise Exception("No backend was set, but @figure was used!")
                import matplotlib
                matplotlib.use('agg')

            # Always import pyplot into embedded shell.
            self.process_input_line('import matplotlib.pyplot as plt',
                                    store_history=False)
            self._pyplot_imported = True

    def process_pure_python(self, content):
        """
        content is a list of strings. it is unedited directive content

        This runs it line by line in the InteractiveShell, prepends
        prompts as needed capturing stderr and stdout, then returns
        the content as a list as if it were ipython code
        """
        output = []
        savefig = False # keep up with this to clear figure
        multiline = False # to handle line continuation
        multiline_start = None
        fmtin = self.promptin

        ct = 0

        for lineno, line in enumerate(content):

            line_stripped = line.strip()
            if not len(line):
                output.append(line)
                continue

            # handle pseudo-decorators, whilst ensuring real python decorators are treated as input
            if any(
                line_stripped.startswith("@" + pseudo_decorator)
                for pseudo_decorator in PSEUDO_DECORATORS
            ):
                output.extend([line])
                if 'savefig' in line:
                    savefig = True # and need to clear figure
                continue

            # handle comments
            if line_stripped.startswith('#'):
                output.extend([line])
                continue

            # deal with lines checking for multiline
            continuation  = u'   %s:'% ''.join(['.']*(len(str(ct))+2))
            if not multiline:
                modified = u"%s %s" % (fmtin % ct, line_stripped)
                output.append(modified)
                ct += 1
                try:
                    ast.parse(line_stripped)
                    output.append(u'')
                except Exception: # on a multiline
                    multiline = True
                    multiline_start = lineno
            else: # still on a multiline
                modified = u'%s %s' % (continuation, line)
                output.append(modified)

                # if the next line is indented, it should be part of multiline
                if len(content) > lineno + 1:
                    nextline = content[lineno + 1]
                    if len(nextline) - len(nextline.lstrip()) > 3:
                        continue
                try:
                    mod = ast.parse(
                            '\n'.join(content[multiline_start:lineno+1]))
                    if isinstance(mod.body[0], ast.FunctionDef):
                        # check to see if we have the whole function
                        for element in mod.body[0].body:
                            if isinstance(element, ast.Return):
                                multiline = False
                    else:
                        output.append(u'')
                        multiline = False
                except Exception:
                    pass

            if savefig: # clear figure if plotted
                self.ensure_pyplot()
                self.process_input_line('plt.clf()', store_history=False)
                self.clear_cout()
                savefig = False

        return output

    def custom_doctest(self, decorator, input_lines, found, submitted):
        """
        Perform a specialized doctest.

        """
        from .custom_doctests import doctests

        args = decorator.split()
        doctest_type = args[1]
        if doctest_type in doctests:
            doctests[doctest_type](self, args, input_lines, found, submitted)
        else:
            e = "Invalid option to @doctest: {0}".format(doctest_type)
            raise Exception(e)


class IPythonDirective(Directive):

    has_content: bool = True
    required_arguments: int = 0
    optional_arguments: int = 4  # python, suppress, verbatim, doctest
    final_argumuent_whitespace: bool = True
    option_spec: Dict[str, Any] = {
        "python": directives.unchanged,
        "suppress": directives.flag,
        "verbatim": directives.flag,
        "doctest": directives.flag,
        "okexcept": directives.flag,
        "okwarning": directives.flag,
    }

    shell = None

    seen_docs: Set = set()

    def get_config_options(self):
        # contains sphinx configuration variables
        config = self.state.document.settings.env.config

        # get config variables to set figure output directory
        savefig_dir = config.ipython_savefig_dir
        source_dir = self.state.document.settings.env.srcdir
        savefig_dir = os.path.join(source_dir, savefig_dir)

        # get regex and prompt stuff
        rgxin      = config.ipython_rgxin
        rgxout     = config.ipython_rgxout
        warning_is_error= config.ipython_warning_is_error
        promptin   = config.ipython_promptin
        promptout  = config.ipython_promptout
        mplbackend = config.ipython_mplbackend
        exec_lines = config.ipython_execlines
        hold_count = config.ipython_holdcount

        return (savefig_dir, source_dir, rgxin, rgxout,
                promptin, promptout, mplbackend, exec_lines, hold_count, warning_is_error)

    def setup(self):
        # Get configuration values.
        (savefig_dir, source_dir, rgxin, rgxout, promptin, promptout,
         mplbackend, exec_lines, hold_count, warning_is_error) = self.get_config_options()

        try:
            os.makedirs(savefig_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        if self.shell is None:
            # We will be here many times.  However, when the
            # EmbeddedSphinxShell is created, its interactive shell member
            # is the same for each instance.

            if mplbackend and 'matplotlib.backends' not in sys.modules and use_matplotlib:
                import matplotlib
                matplotlib.use(mplbackend)

            # Must be called after (potentially) importing matplotlib and
            # setting its backend since exec_lines might import pylab.
            self.shell = EmbeddedSphinxShell(exec_lines)

            # Store IPython directive to enable better error messages
            self.shell.directive = self

        # reset the execution count if we haven't processed this doc
        #NOTE: this may be borked if there are multiple seen_doc tmp files
        #check time stamp?
        if self.state.document.current_source not in self.seen_docs:
            self.shell.IP.history_manager.reset()
            self.shell.IP.execution_count = 1
            self.seen_docs.add(self.state.document.current_source)

        # and attach to shell so we don't have to pass them around
        self.shell.rgxin = rgxin
        self.shell.rgxout = rgxout
        self.shell.promptin = promptin
        self.shell.promptout = promptout
        self.shell.savefig_dir = savefig_dir
        self.shell.source_dir = source_dir
        self.shell.hold_count = hold_count
        self.shell.warning_is_error = warning_is_error

        # setup bookmark for saving figures directory
        self.shell.process_input_line(
            'bookmark ipy_savedir "%s"' % savefig_dir, store_history=False
        )
        self.shell.clear_cout()

        return rgxin, rgxout, promptin, promptout

    def teardown(self):
        # delete last bookmark
        self.shell.process_input_line('bookmark -d ipy_savedir',
                                      store_history=False)
        self.shell.clear_cout()

    def run(self):
        debug = False

        #TODO, any reason block_parser can't be a method of embeddable shell
        # then we wouldn't have to carry these around
        rgxin, rgxout, promptin, promptout = self.setup()

        options = self.options
        self.shell.is_suppress = 'suppress' in options
        self.shell.is_doctest = 'doctest' in options
        self.shell.is_verbatim = 'verbatim' in options
        self.shell.is_okexcept = 'okexcept' in options
        self.shell.is_okwarning = 'okwarning' in options

        # handle pure python code
        if 'python' in self.arguments:
            content = self.content
            self.content = self.shell.process_pure_python(content)

        # parts consists of all text within the ipython-block.
        # Each part is an input/output block.
        parts = '\n'.join(self.content).split('\n\n')

        lines = ['.. code-block:: ipython', '']
        figures = []

        # Use sphinx logger for warnings
        logger = logging.getLogger(__name__)

        for part in parts:
            block = block_parser(part, rgxin, rgxout, promptin, promptout)
            if len(block):
                rows, figure = self.shell.process_block(block)
                for row in rows:
                    lines.extend(['   {0}'.format(line)
                                  for line in row.split('\n')])

                if figure is not None:
                    figures.append(figure)
            else:
                message = 'Code input with no code at {}, line {}'\
                            .format(
                                self.state.document.current_source,
                                self.state.document.current_line)
                if self.shell.warning_is_error:
                    raise RuntimeError(message)
                else:
                    logger.warning(message)

        for figure in figures:
            lines.append('')
            lines.extend(figure.split('\n'))
            lines.append('')

        if len(lines) > 2:
            if debug:
                print('\n'.join(lines))
            else:
                # This has to do with input, not output. But if we comment
                # these lines out, then no IPython code will appear in the
                # final output.
                self.state_machine.insert_input(
                    lines, self.state_machine.input_lines.source(0))

        # cleanup
        self.teardown()

        return []

# Enable as a proper Sphinx directive
def setup(app):
    setup.app = app

    app.add_directive('ipython', IPythonDirective)
    app.add_config_value('ipython_savefig_dir', 'savefig', 'env')
    app.add_config_value('ipython_warning_is_error', True, 'env')
    app.add_config_value('ipython_rgxin',
                         re.compile(r'In \[(\d+)\]:\s?(.*)\s*'), 'env')
    app.add_config_value('ipython_rgxout',
                         re.compile(r'Out\[(\d+)\]:\s?(.*)\s*'), 'env')
    app.add_config_value('ipython_promptin', 'In [%d]:', 'env')
    app.add_config_value('ipython_promptout', 'Out[%d]:', 'env')

    # We could just let matplotlib pick whatever is specified as the default
    # backend in the matplotlibrc file, but this would cause issues if the
    # backend didn't work in headless environments. For this reason, 'agg'
    # is a good default backend choice.
    app.add_config_value('ipython_mplbackend', 'agg', 'env')

    # If the user sets this config value to `None`, then EmbeddedSphinxShell's
    # __init__ method will treat it as [].
    execlines = ['import numpy as np']
    if use_matplotlib:
        execlines.append('import matplotlib.pyplot as plt')
    app.add_config_value('ipython_execlines', execlines, 'env')

    app.add_config_value('ipython_holdcount', True, 'env')

    metadata = {'parallel_read_safe': True, 'parallel_write_safe': True}
    return metadata

# Simple smoke test, needs to be converted to a proper automatic test.
def test():

    examples = [
        r"""
In [9]: pwd
Out[9]: '/home/jdhunter/py4science/book'

In [10]: cd bookdata/
/home/jdhunter/py4science/book/bookdata

In [2]: from pylab import *

In [2]: ion()

In [3]: im = imread('stinkbug.png')

@savefig mystinkbug.png width=4in
In [4]: imshow(im)
Out[4]: <matplotlib.image.AxesImage object at 0x39ea850>

""",
        r"""

In [1]: x = 'hello world'

# string methods can be
# used to alter the string
@doctest
In [2]: x.upper()
Out[2]: 'HELLO WORLD'

@verbatim
In [3]: x.st<TAB>
x.startswith  x.strip
""",
    r"""

In [130]: url = 'http://ichart.finance.yahoo.com/table.csv?s=CROX\
   .....: &d=9&e=22&f=2009&g=d&a=1&br=8&c=2006&ignore=.csv'

In [131]: print url.split('&')
['http://ichart.finance.yahoo.com/table.csv?s=CROX', 'd=9', 'e=22', 'f=2009', 'g=d', 'a=1', 'b=8', 'c=2006', 'ignore=.csv']

In [60]: import urllib

""",
    r"""\

In [133]: import numpy.random

@suppress
In [134]: numpy.random.seed(2358)

@doctest
In [135]: numpy.random.rand(10,2)
Out[135]:
array([[ 0.64524308,  0.59943846],
       [ 0.47102322,  0.8715456 ],
       [ 0.29370834,  0.74776844],
       [ 0.99539577,  0.1313423 ],
       [ 0.16250302,  0.21103583],
       [ 0.81626524,  0.1312433 ],
       [ 0.67338089,  0.72302393],
       [ 0.7566368 ,  0.07033696],
       [ 0.22591016,  0.77731835],
       [ 0.0072729 ,  0.34273127]])

""",

    r"""
In [106]: print x
jdh

In [109]: for i in range(10):
   .....:     print i
   .....:
   .....:
0
1
2
3
4
5
6
7
8
9
""",

        r"""

In [144]: from pylab import *

In [145]: ion()

# use a semicolon to suppress the output
@savefig test_hist.png width=4in
In [151]: hist(np.random.randn(10000), 100);


@savefig test_plot.png width=4in
In [151]: plot(np.random.randn(10000), 'o');
   """,

        r"""
# use a semicolon to suppress the output
In [151]: plt.clf()

@savefig plot_simple.png width=4in
In [151]: plot([1,2,3])

@savefig hist_simple.png width=4in
In [151]: hist(np.random.randn(10000), 100);

""",
     r"""
# update the current fig
In [151]: ylabel('number')

In [152]: title('normal distribution')


@savefig hist_with_text.png
In [153]: grid(True)

@doctest float
In [154]: 0.1 + 0.2
Out[154]: 0.3

@doctest float
In [155]: np.arange(16).reshape(4,4)
Out[155]:
array([[ 0,  1,  2,  3],
       [ 4,  5,  6,  7],
       [ 8,  9, 10, 11],
       [12, 13, 14, 15]])

In [1]: x = np.arange(16, dtype=float).reshape(4,4)

In [2]: x[0,0] = np.inf

In [3]: x[0,1] = np.nan

@doctest float
In [4]: x
Out[4]:
array([[ inf,  nan,   2.,   3.],
       [  4.,   5.,   6.,   7.],
       [  8.,   9.,  10.,  11.],
       [ 12.,  13.,  14.,  15.]])


        """,
        ]
    # skip local-file depending first example:
    examples = examples[1:]

    #ipython_directive.DEBUG = True  # dbg
    #options = dict(suppress=True)  # dbg
    options = {}
    for example in examples:
        content = example.split('\n')
        IPythonDirective('debug', arguments=None, options=options,
                          content=content, lineno=0,
                          content_offset=None, block_text=None,
                          state=None, state_machine=None,
                          )

# Run test suite as a script
if __name__=='__main__':
    if not os.path.isdir('_static'):
        os.mkdir('_static')
    test()
    print('All OK? Check figures in _static/')