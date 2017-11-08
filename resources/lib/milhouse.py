#! /usr/bin/python

import re
import os
import urlparse

from bs4 import BeautifulSoup
import html2text

from . import builds, config


class MilhouseBuildLinkExtractor(builds.BuildLinkExtractor):
    BUILD_RE = (r"{dist}-{arch}-(?:\d+\.\d+-|)"
                r"Milhouse-(\d+)-(?:r|%23)(\d+[a-z]*)-g[0-9a-z]+\.tar(|\.bz2)")


class MilhouseBuildDetailsExtractor(builds.BuildDetailsExtractor):
    """Class for extracting the full build details for a Milhouse build.
       from the release post on the Kodi forum.
    """
    def get_text(self):
        soup = BeautifulSoup(self._text(), 'html5lib')
        pid = urlparse.parse_qs(urlparse.urlparse(self.url).query)['pid'][0]
        post_div_id = "pid_{}".format(pid)
        post = soup.find('div', 'post_body', id=post_div_id)

        text_maker = html2text.HTML2Text()
        text_maker.ignore_links = True
        text_maker.ul_item_mark = '-'

        text = text_maker.handle(unicode(post))

        text = re.search(r"(Build Highlights:.*)", text, re.DOTALL).group(1)
        text = re.sub(r"(Build Highlights:)", r"[B]\1[/B]", text)
        text = re.sub(r"(Build Details:)", r"[B]\1[/B]", text)

        return text


class MilhouseBuildInfoExtractor(builds.BuildInfoExtractor):
    """Class for creating a dictionary of BuildInfo objects for Milhouse builds
       keyed on the build version."""
    URL_FMT = "http://forum.kodi.tv/showthread.php?tid={}"
    R = re.compile(r"#(\d{4}[a-z]?).*?\((.+)\)")

    def _get_info(self, soup):
        for post in soup('div', 'post_body', limit=3):
            for ul in post('ul'):
                for li in ul('li'):
                    m = self.R.match(li.get_text())
                    if m:
                        url = li.find('a', text="Release post")['href']
                        yield (m.group(1),
                               builds.BuildInfo(m.group(2),
                                                MilhouseBuildDetailsExtractor(url)))

    def get_info(self):
        soup = BeautifulSoup(self._text(), 'html5lib')
        return dict(self._get_info(soup))

    @classmethod
    def from_thread_id(cls, thread_id):
        """Create a Milhouse build info extractor from the thread id number."""
        url = cls.URL_FMT.format(thread_id)
        return cls(url)


def milhouse_build_info_extractors():
    if config.arch.startswith("RPi"):
        threads = [269814, 298461]
    else:
        threads = [269815, 298462]

    for thread_id in threads:
        yield MilhouseBuildInfoExtractor.from_thread_id(thread_id)


class MilhouseBuildsURL(builds.BuildsURL):
    def __init__(self, subdir="master"):
        self.subdir = subdir
        url = "http://milhouse.libreelec.tv/builds/"
        super(MilhouseBuildsURL, self).__init__(
            url, os.path.join(subdir, config.arch.split('.')[0]),
            MilhouseBuildLinkExtractor, list(milhouse_build_info_extractors()))

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.subdir)
