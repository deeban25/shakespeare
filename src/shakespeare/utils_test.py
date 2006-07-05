import unittest
import os

import shakespeare.utils

def test_suite():
    suites = [
        unittest.makeSuite(UtilsTest),
        ]
    return unittest.TestSuite(suites)

class UtilsTest(unittest.TestCase):

    def setUp(self):
        self.url = 'http://www.gutenberg.org/dirs/GUTINDEX.ALL'
        self.cachePath = shakespeare.conf().get('misc', 'cachedir')

    def test_get_local_path(self):
        exp = os.path.join(self.cachePath, 'www.gutenberg.org/dirs/GUTINDEX.ALL') 
        out = shakespeare.utils.get_local_path(self.url)
        self.assertEqual(exp, out)

    def test_get_local_path_2(self):
        exp = os.path.join(self.cachePath, 'www.gutenberg.org/dirs/cleanedGUTINDEX.ALL') 
        out = shakespeare.utils.get_local_path(self.url, 'cleaned')
        self.assertEqual(exp, out)

    def test_download_url(self):
        url2 = 'http://project.knowledgeforge.net/shakespeare/svn/trunk/AUTHORS.txt'
        shakespeare.utils.download_url(url2, overwrite=True)
