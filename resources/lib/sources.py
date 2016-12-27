"""Create an ordered dictionary of the sources as BuildsURL objects.
   Only return sources which are relevant for the system architecture
   The GUI will show the sources in the order defined here.
"""
from collections import OrderedDict

import builds, libreelec

def build_sources():
    sources = OrderedDict()

    sources["Official Releases"] = builds.BuildsURL("http://releases.libreelec.tv/releases.json",
                                                    extractor=builds.ReleaseLinkExtractor)

    sources["Milhouse Builds"] = builds.MilhouseBuildsURL()

    if libreelec.debug_system_partition():
        sources["Milhouse Builds (debug)"] = builds.MilhouseBuildsURL(subdir="debug")

    return sources
