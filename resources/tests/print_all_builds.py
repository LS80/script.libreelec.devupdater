#! /usr/bin/python

import sys
import os

import requests

sys.path.insert(0, os.path.relpath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the local etc/os-release values to look like a Milhouse LibreELEC
from lib import libreelec
libreelec.OS_RELEASE['NAME'] = 'LibreELEC'
libreelec.OS_RELEASE['VERSION_ID'] = '8.0'
libreelec.OS_RELEASE['VERSION'] = 'devel-20161224210557-#1224-gdc61a12'
libreelec.OS_RELEASE['MILHOUSE_BUILD'] = '161224'

from lib import builds


def main():
    """Test function to print all available builds when executing the module."""

    installed_build = builds.get_installed_build()

    def get_info(build_url):
        info = {}
        for info_extractor in build_url.info_extractors:
            try:
                info.update(info_extractor.get_info())
            except Exception as e:
                print str(e)
        return info

    def print_links(name, build_url):
        info = get_info(build_url)
        print name
        try:
            for link in build_url:
                try:
                    summary = info[link.version]
                except KeyError:
                    summary = ""
                print "\t{:25s} {}".format(str(link) + ' *' * (link > installed_build),
                                           summary)
        except (requests.RequestException, builds.BuildURLError) as e:
            print str(e)
        print

    print "Installed build = {}".format(installed_build)
    print

    urls = builds.sources()

    if len(sys.argv) > 1:
        name = sys.argv[1]
        if name not in urls:
            print '"{}" not in URL list'.format(name)
        else:
            print_links(name, urls[name])
    else:
        for name, build_url in urls.items():
            print_links(name, build_url)


if __name__ == "__main__":
    main()
