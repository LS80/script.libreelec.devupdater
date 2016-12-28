"""Create an ordered dictionary of the sources as BuildsURL objects.
   Only return sources which are relevant for the system architecture
   The GUI will show the sources in the order defined here.
"""
from collections import OrderedDict

from . import builds, milhouse, libreelec

def build_sources():
    sources = OrderedDict()

    sources["Official Releases"] = builds.BuildsURL("http://releases.libreelec.tv/releases.json",
                                                    extractor=builds.ReleaseLinkExtractor)

    sources["Milhouse Builds"] = milhouse.MilhouseBuildsURL()

    if libreelec.debug_system_partition():
        sources["Milhouse Builds (debug)"] = milhouse.MilhouseBuildsURL(subdir="debug")

    return sources
