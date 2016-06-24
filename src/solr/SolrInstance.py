import urllib2
import os
import signal
import re

__author__ = 'deghou'



class SolrInstance:

    def __init__(self):
        self.solr_server_url = 'http://sam.embl.de'
        self.start_port = '34190'
        self.stop_port = '-1'


    ### Method to check if a search index (core) is loaded and thus ready to be queried
    def isIndexLoaded(self, index):
        if self.start_port != '-1':
            url = self.solr_server_url + ":" + self.start_port + '/solr/admin/cores?action=STATUS'
            try:
                response = urllib2.urlopen(url)
                response_content = response.read()
                indices = [m.start() for m in re.finditer('<lst name="status">', response_content)]
                response_content_loaded_indices = response_content[indices[0]:]
                return(index in response_content_loaded_indices)
            except urllib2.URLError as e:
                if self.verbosity >= 1:
                    print 'An error occurred when checking the status of index ' + index + ':\n  ' + url + '\n  (' + str(e) + ')'
                return False
        else:
            if self.verbosity >= 1:
                print 'An error occurred when checking the status of index ' + index + ':\n  (Solr Server does not seem to run)'
            return False

    ### Checks whether the Solr Server is running
    def isSolrServerReady(self):
        url = self.solr_server_url + ":" + str(self.start_port) + '/solr/#/'
        try:
            response = urllib2.urlopen(url)
            return True
        except urllib2.URLError as e:
            if self.verbosity >= 1:
                print 'Solr Server (port: ' + str(self.start_port) + ') does not respond / is not running'
                print '  (' + str(e) + ')'
            return False
