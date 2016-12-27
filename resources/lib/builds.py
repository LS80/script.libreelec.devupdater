#! /usr/bin/python

# This is required to work around the ImportError exception
# "Failed to import _strptime because the import lock is held by another thread."
import _strptime

import time
import re
import os
import urlparse
from datetime import datetime
from urllib2 import unquote

from bs4 import BeautifulSoup, SoupStrainer
import requests
import html2text

import libreelec, config, funcs, log


class BuildURLError(Exception):
    pass


class Build(object):
    """Holds information about a LibreELEC build and defines how to compare them,
       produce a unique hash for dictionary keys, and print them.
    """
    DATETIME_FMT = '%Y%m%d%H%M%S'

    def __init__(self, _datetime, version):
        self._version = version
        if isinstance(_datetime, datetime):
            self._datetime = _datetime
        else:
            try:
                self._datetime = datetime.strptime(_datetime, self.DATETIME_FMT)
            except TypeError:
                # Work around an issue with datetime.strptime when the script
                # is run a second time.
                dt = time.strptime(_datetime, self.DATETIME_FMT)[0:6]
                self._datetime = datetime(*(dt))

    def __eq__(self, other):
        return (self._version, self._datetime) == (other._version, other._datetime)

    def __hash__(self):
        return hash((self._version, self._datetime))

    def __lt__(self, other):
        return self._datetime < other._datetime

    def __gt__(self, other):
        return self._datetime > other._datetime

    def __str__(self):
        return '{} ({})'.format(self.version, self.date)

    def __repr__(self):
        return "{}('{}', '{}')".format("Build",
                                       self._datetime.strftime(self.DATETIME_FMT),
                                       self.version)

    @property
    def date(self):
        return self._datetime.strftime(config.date_fmt)

    @property
    def version(self):
        return self._version


class Release(Build):
    """Subclass of Build for official releases.

       Has additional methods for retrieving datetime information from the git tags.
    """
    DATETIME_FMT = '%Y-%m-%dT%H:%M:%SZ'

    def __init__(self, version):
        self.release_str = version
        self.release_date = self.get_release_date()
        if self.release_date:
            Build.__init__(self, self.release_date, version)
            self.release = [int(p) for p in version.split('.')]

    def __nonzero__(self):
        return self.release_date is not None

    def get_release_date(self):
        url = "https://api.github.com/repos/libreelec/libreelec.tv/git/refs/tags/{version}".format(
            version=self.release_str)
        resp = requests.get(url)
        if resp:
            tag = resp.json()
            url = tag['object']['url']
            commit = requests.get(url).json()
            return commit['committer']['date']
        else:
            return

    def __repr__(self):
        return "{}('{}')".format("Release", self.release_str)


class BuildLinkBase(object):
    """Base class for links to builds"""
    def __init__(self, baseurl, link):
        # Set the absolute URL
        link = link.strip()
        scheme, netloc, path = urlparse.urlparse(link)[:3]
        if not scheme:
            # Construct the full url
            if not baseurl.endswith('/'):
                baseurl += '/'
            self.url = urlparse.urljoin(baseurl, link)
        else:
            if netloc == "www.dropbox.com":
                # Fix Dropbox url
                link = urlparse.urlunparse((scheme, "dl.dropbox.com", path,
                                            None, None, None))
            self.url = link

    def remote_file(self):
        response = requests.get(self.url, stream=True, timeout=config.timeout,
                                headers={'Accept-Encoding': None})
        try:
            self.size = int(response.headers['Content-Length'])
        except KeyError:
            self.size = 0

        # Get the actual filename
        self.filename = unquote(os.path.basename(urlparse.urlparse(response.url).path))

        name, ext = os.path.splitext(self.filename)
        self.tar_name = self.filename if ext == '.tar' else name
        self.compressed = ext == '.bz2'

        return response.raw


class BuildLink(Build, BuildLinkBase):
    """Holds information about a link to a LibreELEC build."""
    def __init__(self, baseurl, link, datetime_str, revision):
        BuildLinkBase.__init__(self, baseurl, link)
        Build.__init__(self, datetime_str, version=revision)


class ReleaseLink(Release, BuildLinkBase):
    """Class for links to LibreELEC release downloads."""
    def __init__(self, baseurl, link, release):
        BuildLinkBase.__init__(self, baseurl, link)
        Release.__init__(self, release)


class BaseExtractor(object):
    """Base class for all extractors."""
    url = None

    def __init__(self, url=None):
        if url is not None:
            self.url = url

    def _response(self):
        response = requests.get(self.url, timeout=config.timeout)
        if not response:
            msg = "Build URL error: status {}".format(response.status_code)
            raise BuildURLError(msg)
        return response

    def _text(self):
        return self._response().text

    def _json(self):
        return self._response().json()

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.url)


class BuildLinkExtractor(BaseExtractor):
    """Base class for extracting build links from a URL"""
    BUILD_RE = (".*{dist}.*-{arch}-(?:\d+\.\d+-|)[a-zA-Z]+-(\d+)"
                "-r\d+[a-z]*-g([0-9a-z]+)\.tar(|\.bz2)")

    def __iter__(self):
        html = self._text()

        self.build_re = re.compile(
            self.BUILD_RE.format(dist=libreelec.OS_RELEASE['NAME'], arch=config.arch),
            re.I)

        soup = BeautifulSoup(html, 'html.parser',
                             parse_only=SoupStrainer('a', href=self.build_re))

        for link in soup.contents:
            l = self._create_link(link)
            if l:
                yield l

    def _create_link(self, link):
        href = link['href']
        return BuildLink(self.url, href, *self.build_re.match(href).groups()[:2])


class ReleaseLinkExtractor(BaseExtractor):
    def __iter__(self):
        base_url = "http://releases.libreelec.tv"
        releases = self._json()[libreelec.release()]['project'][config.arch]['releases']
        for release in releases.itervalues():
            filename = release['file']['name']
            release_name = re.search('-(\d+\.\d+\.\d+).tar', filename).group(1)
            release_link = ReleaseLink(base_url, filename, release_name)
            if release_link:
                yield release_link


class MilhouseBuildLinkExtractor(BuildLinkExtractor):
    BUILD_RE = ("{dist}-{arch}-(?:\d+\.\d+-|)"
                "Milhouse-(\d+)-(?:r|%23)(\d+[a-z]*)-g[0-9a-z]+\.tar(|\.bz2)")


class BuildInfo(object):
    """Class to hold the short summary of a build and the full details."""
    def __init__(self, summary, details=None):
        self.summary = summary
        self.details = details

    def __str__(self):
        return self.summary


class BuildDetailsExtractor(BaseExtractor):
    """Default class for extracting build details which returns an empty string."""
    def get_text(self):
        return ""


class MilhouseBuildDetailsExtractor(BuildDetailsExtractor):
    """Class for extracting the full build details for a Milhouse build.
       from the release post on the Kodi forum.
    """
    def get_text(self):
        soup = BeautifulSoup(self._text(), 'html.parser')
        pid = urlparse.parse_qs(urlparse.urlparse(self.url).query)['pid'][0]
        post_div_id = "pid_{}".format(pid)
        post = soup.find('div', 'post-body', id=post_div_id)

        text_maker = html2text.HTML2Text()
        text_maker.ignore_links = True
        text_maker.ul_item_mark = '-'

        text = text_maker.handle(unicode(post))

        text = re.search(r"(Build Highlights:.*)", text, re.DOTALL).group(1)
        text = re.sub(r"(Build Highlights:)", r"[B]\1[/B]", text)
        text = re.sub(r"(Build Details:)", r"[B]\1[/B]", text)

        return text


class BuildInfoExtractor(BaseExtractor):
    """Default build info extractor class for all build sources which just creates
       an empty dictionary."""
    def get_info(self):
        return {}


class MilhouseBuildInfoExtractor(BuildInfoExtractor):
    """Class for creating a dictionary of BuildInfo objects for Milhouse builds
       keyed on the build version."""
    URL_FMT = "http://forum.kodi.tv/showthread.php?tid={}"
    R = re.compile("#(\d{4}[a-z]?).*?\((.+)\)")

    def _get_info(self, soup):
        for post in soup.find_all('div', 'post-body', limit=3):
            for ul in post('ul'):
                for li in ul('li'):
                    m = self.R.match(li.get_text())
                    if m:
                        url = li.find('a', text="Release post")['href']
                        yield m.group(1), BuildInfo(m.group(2),
                                                    MilhouseBuildDetailsExtractor(url))

    def get_info(self):
        soup = BeautifulSoup(self._text(), 'html.parser')
        return dict(self._get_info(soup))

    @classmethod
    def from_thread_id(cls, thread_id):
        """Create a Milhouse build info extractor from the thread id number."""
        url = cls.URL_FMT.format(thread_id)
        return cls(url)


def get_milhouse_build_info_extractors():
    if config.arch.startswith("RPi"):
        threads = [269814, 298461]
    else:
        threads = [269815, 298462]

    for thread_id in threads:
        yield MilhouseBuildInfoExtractor.from_thread_id(thread_id)


class CommitInfoExtractor(BuildInfoExtractor):
    """Class used by development build sources for extracting the git commit messages
       for a commit hash as the summary. Full build details are set to None."""
    url = "https://api.github.com/repositories/1093060/commits?per_page=100"

    def get_info(self):
        return dict((commit['sha'][:7],
                     BuildInfo(commit['commit']['message'].split('\n\n')[0], None))
                     for commit in self._json())


class BuildsURL(object):
    """Class representing a source of builds."""
    def __init__(self, url=None, subdir=None, extractor=BuildLinkExtractor,
                 info_extractors=[BuildInfoExtractor()]):
        self.url = url
        if subdir:
            self.add_subdir(subdir)

        self._extractor = extractor
        self.info_extractors = info_extractors

    def builds(self):
        return sorted(self._extractor(self.url), reverse=True)

    def __iter__(self):
        return iter(self.builds())

    def latest(self):
        """Return the most recent build or None if no builds are available."""
        builds = self.builds()
        try:
            return builds[0]
        except IndexError:
            return None

    def add_subdir(self, subdir):
        self._add_slash()
        self.url = urlparse.urljoin(self.url, subdir)
        self._add_slash()

    def _add_slash(self):
        if not self.url.endswith('/'):
            self.url += '/'

    def __str__(self):
        return self.url

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.url)


class MilhouseBuildsURL(BuildsURL):
    def __init__(self, subdir="master"):
        self.subdir = subdir
        url = "http://milhouse.libreelec.tv/builds/"
        super(MilhouseBuildsURL, self).__init__(
            url, os.path.join(subdir, config.arch.split('.')[0]),
            MilhouseBuildLinkExtractor, list(get_milhouse_build_info_extractors()))

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.subdir)


def get_installed_build():
    """Return the currently installed build object."""
    if 'MILHOUSE_BUILD' in libreelec.OS_RELEASE:
        DEVEL_RE = "devel-(\d+)-[r#](\d{4}[a-z]?)"
    else:
        DEVEL_RE = "devel-(\d+)-r\d+-g([a-z0-9]+)"

    version = libreelec.OS_RELEASE['VERSION']

    m = re.match(DEVEL_RE, version)
    if m:
        return Build(*m.groups())
    else:
        # A full release is installed.
        return Release(version)


@log.with_logging(msg_error="Unable to create build object from the notify file")
def get_build_from_notify_file():
    selected = funcs.read_notify_file()
    if selected:
        source, build_repr = selected
        return source, eval(build_repr)
