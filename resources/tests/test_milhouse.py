import os
import sys
import re
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from resources.lib import milhouse, builds


class TestMilhouseBuildInfoExtractor(unittest.TestCase):
    def setUp(self):
        self.build_info = milhouse.MilhouseBuildInfoExtractor.from_thread_id(298461).get_info()

    def test_not_empty(self):
        self.assertGreater(len(self.build_info), 0)

    def test_keys_and_values(self):
        for k, v in self.build_info.iteritems():
            self.assertRegexpMatches(k, r'\d{4}')
            self.assertIsInstance(v, builds.BuildInfo)


class TestMilhouseBuildDetailsExtractor(unittest.TestCase):
    def setUp(self):
        self.text = milhouse.MilhouseBuildDetailsExtractor(
            'http://forum.kodi.tv/showthread.php?tid=298461&pid=2664601#pid2664601').get_text()

    def test_expected_contents(self):
        self.assertRegexpMatches(self.text, r'^\[B\]Build Highlights:\[/B\]')
        self.assertRegexpMatches(self.text, r'\n\[B\]Build Details:\[/B\]')


if __name__ == '__main__':
    unittest.main()
