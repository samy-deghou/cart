from __future__ import division
import subprocess
import os
import sys
import json
import re
import Levenshtein

import ConfigParser
from SolrInstance import SolrInstance

reload(sys)
sys.setdefaultencoding("utf-8")

class SolrController:

    ### Constructor
    def __init__(self, outputfiledetail, fuzzyThreshold, inputType='names', verbose=1, search_space='stitch20141111'):
        self.verbosity = verbose
        self.solrInstance = SolrInstance()
        self.input_type = inputType
        self.fuzzyThreshold = fuzzyThreshold
        self.output_file_detail = outputfiledetail

        # get settings from config file
        self.__readConfig()
        # make sure that search_space is in self.__SUPP_INDICES
        if not search_space in self.__SUPP_INDICES:
            print 'Search space %s is not among the supported indices: %s!' %(search_space, ', '.join(self.__SUPP_INDICES))
            print '(consider updating settings.conf)'
            print 'Exiting'
            exit(1)
        self.search_space = search_space

        # attempt to restart the Solr Server
        if not self.solrInstance.isSolrServerReady():
            print 'The solr server does not seem to be running'

        # check whether search space is loaded and reload it if not
        if not self.solrInstance.isIndexLoaded(self.search_space):
            print 'Solr Server does not have index ' + self.search_space + ' loaded\nTrying to reload index...'
        # elif self.verbosity >= 3:
        #     print 'Solr Server does already have index ' + self.search_space + ' loaded'

        # die if Solr / Lucene could NOT be started correctly
        if not (self.solrInstance.isSolrServerReady() and self.solrInstance.isIndexLoaded(self.search_space)):
            print 'Failed to establish connection to Solr Server.'
            print 'Exiting'
            exit(1)
        # after this we will just assume that Solr / Lucene are running correctly




    ### utility function that that transform a cid to the convention CIDxxxxxxxx
    def standardizeCid(self,cid):
        cid = str(cid)
        # TODO
        while(len(cid) < 9):
            cid = '0' + cid
        return 'cid' + cid
                



    ### Method to retrieve synonymous chemical names
    def findSynonyms(self, query_file, output_file, approximate, exact, heuristic):
        if self.verbosity >= 2:
            print '\nStarting synonym retrieval...'
        # parse chemicals from the file
        # TODO IO error handling
        self.initQueryDict(query_file)
        
        self.matchNames(query_file, output_file, approximate, exact, heuristic)
        with open(output_file) as infile:
            for line in infile:
                chemical_name = line.split('\t')[2]
                cid_fetched = line.split('\t')[0]
                self.query_dict[chemical_name] = cid_fetched
        i = 0
        results_list = []
        for query_i in self.query_dict.viewkeys():
            cid = self.query_dict[query_i]
            if self.verbosity >= 2:
                i = i + 1
                perc_done = i / len(self.query_dict)
                perc_done = int(perc_done * 100)
                sys.stdout.write('\r    %d%%' %perc_done)
                sys.stdout.flush()
            # submit query
            raw_result = self.__submitQuery(cid, 'title')
            #print raw_result
            results_list.append(self.__parseSynonyms(raw_result, query_i))
        if self.verbosity >= 2:
            sys.stdout.write('\n')
            sys.stdout.flush()
        # overwrite output file
        f = open(output_file, 'w')
        f.write(''.join(results_list))
        f.close()        


    def getInchiFromSmile(self, smile):
    #smile = "C1CN(CC1NC2=CC=CC3=C2C=CN=C3)CC4=C(C=C(C=C4)Cl)[N+](=O)[O-]"
    #javac -cp .:./cdk-1.5.11.jar ./Main.java
    #java -cp .:./cdk-1.5.11.jar:./ Main "C1CN(CC1NC2=CC=CC3=C2C=CN=C3)CC4=C(C=C(C=C4)Cl)[N+](=O)[O-]"
        smile = smile.strip()
        curDir =  os.path.dirname(os.path.realpath(__file__))
        jarFile = ".:/home/det/galaxy-dist-v2/tools/det/src/cdk-1.5.11.jar:/home/det/galaxy-dist-v2/tools/det/src/"
        ll = ["java","-cp" , jarFile, "Main", smile]
        p1 = subprocess.Popen(ll, stdout=subprocess.PIPE)        
        output_java_program = p1.stdout.read()
	essential_smile = ""
        if not output_java_program.startswith("Problem with parsing the SMILE"):
	    complete_smile = re.split("\n",output_java_program)[-2]
            essential_smile = re.split("-",complete_smile)[0]
	return essential_smile



    
    def __correctThroughProperName(self,raw_result):
        results = json.loads(raw_result)
        the_cid = results['response']['docs'][0]['title'][0]
        first_sp = self.search_space
        self.search_space = 'cidNameUniqueFull'
        raw_result = self.__submitQuery(the_cid,'title')
        #print('New raw results: ')
        #print(raw_result)
        self.search_space = first_sp
        return raw_result

    
    


    ### Method to parse queries from file
    def initQueryDict(self, fn_in):
        self.query_dict = {}
        with open(fn_in) as infile:
            for line in infile:
                if(len(line) > 2):
                    line = re.sub('"', '', line.strip())
                    if line.endswith('\\'):
                        line = line[0:-1]
                    l = line.split('\t')
                    entity_name = l[0]
#		    print self.input_type
                    if self.input_type.lower() == "names":
                        entity_name = entity_name.lower()
                    if len(l) == 1:
                        self.query_dict[entity_name] = 'NA'
                    else:
                        # TODO perhaps make the float conversion of user-scores more fool-proof
                        if entity_name in self.query_dict:
                            self.query_dict[entity_name].append(float(l[1]))
                        else:
                            self.query_dict[entity_name] = [float(l[1])]
        assert infile.closed
        # reset (previous) results
        self.results_exact = ''
        self.results_fuzzy = ''
        self.results_heuristic = ''
        self.results_synonyms = ''

    def __testFun(self,s1,s2):
        if len(s1) < len(s2):
            return self.__testFun(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
                deletions = current_row[j] + 1       # than s2
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    




    ### Method to parse the Solr / Lucene output into a tab-delimited format with the necessary information
    def __parseNameMatches(self, results, fuzzy_option, score, match_type, chem_orig_name = None):
        json_ob = json.loads(results)
        # TODO better error handling
        query = json_ob['responseHeader']['params']['q']
        rlength = json_ob['response']['numFound']
        returned_docs = json_ob['response']['docs']
        res = ''
        if rlength == 0:
            input = ""
            if fuzzy_option:
                input = query.split(":")[1]
                input = input.split("~")[0]
            else:
                input = query.split('\"')[1]
            # substitute chemical name by its original version
            # (used for heuristic search and SMILES/InChis
            # where chemical names are modified before seraching)
            if chem_orig_name is not None:
                input = chem_orig_name
            res = '%s\t%s\tNA\tNA\tNA\tNA\n' %(input, score)                
            return(res)
        if fuzzy_option:
            doc = returned_docs[0]
            input = query.split(":")[1]
            input = input.split("~")[0]
            i = 0
            limit = 0
            if len(returned_docs) >= 5:
                limit = 4
            else:
                limit = len(returned_docs) - 1
            chemm = ""
            if self.output_file_detail != "null":
                with open(self.output_file_detail, 'a') as fout:
                    while i < limit:
                        cidfound = returned_docs[i]['title'][0]
                        namefound = returned_docs[i]['name']
			scorefound = 1 - Levenshtein.distance(str(input),str(namefound))/max(len(input),len(namefound))
                        if not namefound == chemm:
                            print >>fout, input + "\t" +  cidfound + "\t" +  namefound + "\t" + str(scorefound)
                            chemm = namefound
                            i += 1
                        else:
                            i += 1
                            if not limit == len(returned_docs) - 1:
                                limit += 1

            
            # substitute chemical name by its original version
            # (used for heuristic search where chemical names are modified before seraching)
            if chem_orig_name is not None:
                input = chem_orig_name  
            thresholdL = self.__fuzzyThreshold
            totalF = 0
            cc = ""
            for doc in returned_docs:
                l1 = len(input)
                l2 = len(doc['name'])
                m = l1 if l1 > l2 else l2
                prop = 1 - Levenshtein.distance(str(input),str(doc['name'])) / m
                totalF += 1
		if match_type == "FUZZY_MATCH":
                    if prop >= thresholdL:
                        res = '%s%s\t%s\t%s\t%s\t%f\t%s\n' %(res, input, score, doc['title'][0], doc['name'], doc['score'], match_type)
                        with open(self.output_file_detail, 'a') as fout:
                            namefound = doc['name']
                            scorefound = 1 - Levenshtein.distance(str(input),str(namefound))/max(len(input),len(namefound))
                            if cc != input:
                                print >>fout, input + "\t" +  cidfound + "\t" +  namefound + "\t" + str(scorefound)
                                cc = input
		if match_type == "HEURISTIC_MATCH":
		    if prop >= thresholdL:
                        res = '%s%s\t%s\t%s\t%s\t%f\t%s\n' %(res, input, score, doc['title'][0], doc['name'], doc['score'], match_type)
            return(res)
            
        else:
            # substitute chemical name by its original version
            # (used for heuristic search where chemical names are modified before seraching)
            if chem_orig_name is not None:
                input = chem_orig_name
            for doc in returned_docs:
                res = '%s%s\t%s\t%s\t%s\t%f\t%s\n' %(res, input, score, doc['title'][0], doc['name'], doc['score'], match_type)
            return(res)


    ### Method to parse the Solr / Lucene output into a tab-delimited format with the necessary information
    def __parseSynonyms(self, results, chemical_name):
        json_ob = json.loads(results)
        # TODO better error handling
        returned_docs = json_ob['response']['docs']
        res = ''
        for doc in returned_docs:
            res = res + chemical_name + '\t' + doc['name'] + '\t' + doc['title'][0] + '\n'
        return(res)




    ### Auxiliary method to read paramters from the config file
    def __readConfig(self):
        cfg_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../conf/settings.cfg')
        cfg = ConfigParser.ConfigParser()
        cfg.read(cfg_file)
        self.__STOP_KEY = cfg.get('solr', 'stop_key')
        self.__SOLR_INSTALL_DIR = cfg.get('solr', 'solr_install_dir')
        self.__JRE_CMD = cfg.get('solr', 'jre_cmd')
        self.__JRE_MEM = cfg.get('solr', 'jre_mem')
        tmp = cfg.get('solr', 'search_indices')
        self.__SUPP_INDICES = re.findall(r'[[\w\\._-]+', tmp)
        # if self.verbosity >= 2:
        #     print 'Solr stop key ................. ' + self.__STOP_KEY
        #     print 'Solr installation dir ......... ' + self.__SOLR_INSTALL_DIR
        #     print 'Solr JRE command .............. ' + self.__JRE_CMD
        #     print 'Solr JRE memory ............... ' + self.__JRE_MEM
        #     print 'Solr search indices ........... ' + ', '.join(self.__SUPP_INDICES)
        # if self.verbosity >= 3:
        #     print ''
        #     os.system('%s -version'%self.__JRE_CMD)
        #     print ''
