import sys
import json

sys.path.append('solr')
sys.path.append('controllers')

from solr_controller import SolrController
from NameMatchingController import NameMatchingController

__author__ = 'deghou'

import unittest

class TestNameMatching(unittest.TestCase):

    def test_exact_matching(self):
        sc = SolrController("",False)
        nmc = NameMatchingController()
        nmc.solrController = sc
        results_json = nmc.submitQuery("ibuprofen", 'name')
        json_object = json.loads(results_json)
        self.assertTrue(json_object['response']['numFound'] > 0)


    def test_exact_matching(self):
        sc = SolrController("",False)
        nmc = NameMatchingController()
        nmc.solrController = sc
        results_json = nmc.submitQuery("ibuprofen", 'name_approx')
        json_object = json.loads(results_json)
        self.assertTrue(json_object['response']['numFound'] > 0)




if __name__ == '__main__':
    unittest.main()