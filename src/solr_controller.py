from __future__ import division
import subprocess
import urllib2
from urllib2 import URLError
import socket
import os
import sys
import signal
import json
import re
import psutil
import time
import Levenshtein

import ConfigParser
reload(sys)
sys.setdefaultencoding("utf-8")

class SolrController:

    ### Constructor
    def __init__(self, outputfiledetail, fuzzyThreshold, inputType='names', verbose=1, search_space='stitch20141111'):
        self.verbosity = verbose
        self.__start_port = '34190'
        self.__stop_port = '-1'
        self.__input_type = inputType
        self.__fuzzyThreshold = fuzzyThreshold
        self.__output_file_detail = outputfiledetail

        # get settings from config file
        self.__readConfig()
        # make sure that search_space is in self.__SUPP_INDICES
        if not search_space in self.__SUPP_INDICES:
            print 'Search space %s is not among the supported indices: %s!' %(search_space, ', '.join(self.__SUPP_INDICES))
            print '(consider updating settings.conf)'
            print 'Exiting'
            exit(1)
        self.__search_space = search_space
        
        # get start and stop port of a running Solr instance if it exists
        solr_ports = self.__getSolrListeningPorts()
        if solr_ports:
            self.__start_port = solr_ports['start_port']
            self.__stop_port = solr_ports['stop_port']
        if solr_ports != None and self.verbosity >= 2:
            print 'Solr start port ............... ' + self.__start_port
            print 'Solr stop port ................ ' + self.__stop_port        

        # attempt to restart the Solr Server
        if not self.isSolrServerReady():
            print 'Trying to (re-)start Solr Server...'
            self.restartSolrServer()

        # check whether search space is loaded and reload it if not
        if not self.isIndexLoaded(self.__search_space):
            print 'Solr Server does not have index ' + self.__search_space + ' loaded\nTrying to reload index...'
            self.loadIndex(self.__search_space)
        elif self.verbosity >= 3:
            print 'Solr Server does already have index ' + self.__search_space + ' loaded'

        # die if Solr / Lucene could NOT be started correctly
        if not (self.isSolrServerReady() and self.isIndexLoaded(self.__search_space)):
            print 'Failed to establish connection to Solr Server.'
            print 'Exiting'
            exit(1)
        # after this we will just assume that Solr / Lucene are running correctly

        if self.verbosity >= 2:
            print 'Solr search space.............. ' + self.__search_space
        self.query_dict = ''
        self.occurence_chemicals = ''
        self.results_exact = ''
        self.results_fuzzy = ''
        self.results_heuristic = ''
        self.results_synonyms = ''


    ### Attempts to start a Solr Server
    def startSolrServer(self):
        # remove write lock files
        self.__removeWriteLocks()
        # get free ports that can be used by Solr
        free_ports = self.__getFreePorts()
        self.__start_port = str(free_ports[0])
        self.__stop_port = str(free_ports[1])
        #self.__start_port = str(8983)
        #self.__stop_port = str(8888)
        
        if self.verbosity >= 2:
            print 'Re-initialized the Solr ports:'
            print 'Solr start port       = ' + self.__start_port
            print 'Solr stop port        = ' + self.__stop_port
        # start Solr
        solr_inst_dir = self.__SOLR_INSTALL_DIR + '/example'
        current_wd = os.getcwd()
        os.chdir(solr_inst_dir)
        # TODO: Error handling doesn't work due to the nohup/stream redirection
        cmd = 'nohup %s -Djetty.port=%s -Xmx%s -DSTOP.PORT=%s -DSTOP.KEY=%s -jar start.jar > output.log 2>&1 &' %(self.__JRE_CMD, self.__start_port, self.__JRE_MEM, self.__stop_port, self.__STOP_KEY)
        if self.verbosity >= 2:
            print 'Starting Solr Server with the following command:\n  ' + cmd
        os.system(cmd)
        time.sleep(20)
        os.chdir(current_wd)


    ### Attempts to stop a running SolrServer
    def stopSolrServer(self):
        solr_pid = self.__getPidOfSolrProcess()
        if solr_pid == -1:
            if self.verbosity >= 1:
                print 'Attempt to kill Solr server failed as Solr does not seem to run currently (no PID found!)'
            return False
        try:
            if self.verbosity >= 1:
                print 'Trying to kill Solr server with PID ' + str(solr_pid) + '...'
            os.kill(solr_pid, signal.SIGKILL)
            if self.verbosity >= 1:
                print 'Successfully killed Solr process (PID = ' + str(solr_pid) + ')'
            return True
        except OSError as e:
            if self.verbosity >= 1:
                print 'Failed to kill Solr process (PID = ' + str(solr_pid) + ')'
            return False


    ### Checks whether a Solr server is running and if so tries to kill it, afterwards attempts to start a Solr server
    def restartSolrServer(self):
        solr_pid = self.__getPidOfSolrProcess()
        if solr_pid == -1:
            return self.startSolrServer()
        else:
            # start a new instance of Solr
            is_solr_killed = self.stopSolrServer()
            if is_solr_killed:
                return self.startSolrServer()
            else:
                return False


    ### Checks whether the Solr Server is running
    def isSolrServerReady(self):
        url = 'http://sam.embl.de:' + str(self.__start_port) + '/solr/#/'
        try:
            response = urllib2.urlopen(url)
            return True
        except URLError as e:
            if self.verbosity >= 1:
                print 'Solr Server (port: ' + str(self.__start_port) + ') does not respond / is not running'
                print '  (' + str(e) + ')'
            return False


    ### Method to check if a search index (core) is loaded and thus ready to be queried
    def isIndexLoaded(self, index):
        if self.__start_port != '-1':
            url = 'http://sam.embl.de:' + self.__start_port + '/solr/admin/cores?action=STATUS'
            try:
                response = urllib2.urlopen(url)
                response_content = response.read()
                indices = [m.start() for m in re.finditer('<lst name="status">', response_content)]
                response_content_loaded_indices = response_content[indices[0]:]
                return(index in response_content_loaded_indices)
            except URLError as e:
                if self.verbosity >= 1:
                    print 'An error occurred when checking the status of index ' + index + ':\n  ' + url + '\n  (' + str(e) + ')'
                return False
        else:
            if self.verbosity >= 1:
                print 'An error occurred when checking the status of index ' + index + ':\n  (Solr Server does not seem to run)'
            return False


    ### Method to load an index if it isn't loaded yet for the current Solr server
    def loadIndex(self, index):
        if self.__start_port != '-1':
            if not self.isIndexLoaded(index):
                try:
                    url = 'http://sam.embl.de:' + self.__start_port + '/solr/admin/cores?action=CREATE&name=' + index + '&config=solrconfig.xml&schema=schema.xml&dataDir=data'
                    if self.verbosity >= 2:
                        print 'Trying to load ' + index + ' on port ' + self.__start_port + '\n  (url: ' + url + ')...'
                    urllib2.urlopen(url)
                    if self.verbosity >= 2:
                        print 'Index ' + index + ' successfully loaded and ready to be queried'
                except URLError as e:
                    if self.verbosity >= 1:
                        print 'Failed to load the index ' + index + ' on port ' + self.__start_port
                        print '  (' + str(e) + ')'
                        print '  (potential issues: index name spelling, Solr ports, issues with building the Solr index)'
            else:
                print 'Index ' + index + ' is already loaded'
        else:
            print 'Failed to load the index ' + index + ' because no Solr server seems to run (failed to get Solr lisntening ports)'

    ### utility function that that transform a cid to the convention CIDxxxxxxxx
    def standardizeCid(self,cid):
        cid = str(cid)
        # TODO
        while(len(cid) < 9):
            cid = '0' + cid
        return 'cid' + cid
                

    ### Main high-level method to perform the chemical name matching
    def matchNames(self, query_file, output_file, approximate_option, exact_option, heuristic_option):
        if self.verbosity >= 2:
            print '\nStarting name matching...'
        # parse chemicals from the file
        # TODO IO error handling
        self.initQueryDict(query_file)
        # perform the chemical matching
        
        if self.__output_file_detail != "null":
            with open(self.__output_file_detail, 'a') as fout:
                print >>fout,"Input chemicals\tFetched CIDs\tFetched chemicals\tScores"
        if exact_option:
            start = time.time()
            self.matchExact()
            end = time.time()
            if self.verbosity >= 2:
                print '    time taken for exact matching:  %.1f sec.' %(end-start) 
        if heuristic_option:
            start = time.time()
            self.matchHeuristic()
            end = time.time()
            if self.verbosity >= 2:        
                print '    time taken for heuristic matching: %.1f sec.' %(end-start) 
        if approximate_option:
            start = time.time()
            self.matchFuzzy()
            end = time.time()
            if self.verbosity >= 2:        
                print '    time taken for fuzzy matching:  %.1f sec.' %(end-start) 
#        if heuristic_option:
#            start = time.time()
#            self.matchHeuristic()
#            end = time.time()
#            if self.verbosity >= 2:        
#                print '    time taken for heuristic matching: %.1f sec.' %(end-start) 

        if self.verbosity >= 2:
            print '\nParsing results...\n'
        best_matches = self.__parseBestMatches()
        with open(output_file, 'w') as fout:
            best_matches_encoded = best_matches.encode('utf-8')
	    print >>fout,"CID fetched\tInput scores\tInput chemicals\tFetched chemicals\tMatch type"
            print >>fout, best_matches_encoded
        assert fout.closed


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
#            if self.verbosity >= 3:
#                print ' Processing query %i (Exact matching) %s' % (i, query_i)
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
        


    ### Method to perform approximate / fuzzy matching on those chemical names
    ### that could not be matched exactly with the above method
    def matchFuzzy(self):
        already_matched = []
        results = self.results_exact.strip() + '\n' + self.results_heuristic.strip()
        #results = self.results_exact.strip() + '\n'
        for l in results.split('\n'):
            if len(l) >= 1:
                l = l.split('\t')
                if not l[5] == 'NA':
                    already_matched.append(l[0])
        # unmatched with the exact matching
        queries = set(self.query_dict.viewkeys()).difference(already_matched)
        #print 'number of matches (exact): %i' %len(already_matched)
        #print 'left unmatched: %i' %len(queries)
        results_list = []
        if self.verbosity >= 0:
            print '\n... Fuzzy matching ... (' + str(len(queries)) + ' unique chemicals)'

        i = 0
        for query_i in queries:
            i = i + 1
            score = self.query_dict[query_i]
            if self.verbosity >= 2:
                perc_done = i / len(queries)
                perc_done = int(perc_done * 100)
                sys.stdout.write('\r    %d%%' %perc_done)
                sys.stdout.flush()
            #if self.verbosity >= 1:
            #    print ' Processing query %i (Fuzzy matching) %s' % (i, query_i)
            # submit query
            raw_result = self.__submitQuery(query_i, 'name_approx')
            raw_results_parsed = self.__parseNameMatches(raw_result, True, score, 'FUZZY_MATCH', query_i)
            # append the results if and only if there is at least one match 
            if raw_results_parsed.split('\n')[0].split('\t')[-1] != 'NA':
                results_list.append(raw_results_parsed)
        if self.verbosity >= 2:
            sys.stdout.write('\n')
            sys.stdout.flush()
        self.results_fuzzy = ''.join(results_list)



    ### Method to match chemicals using a heuristic, which modifies the chemical name
    ### according to predefined rules (using the modChemical function).
    ### For modified chemical names, another fuzzy query is performed
    def matchHeuristic(self):
	#print("in heuristic matching")
        # get the chemicals without previous matches
        results = self.results_exact.strip() + '\n' + self.results_fuzzy.strip()
        already_matched = []
        # TODO there seems to be an issue with empty lines...
        for l in results.split('\n'):
            if len(l) >= 1:
                l = l.split('\t')
                if not l[5] == 'NA':
                    already_matched.append(l[0])
        # unmatched with previous matching attempts (exact & fuzzy)
        queries = set(self.query_dict.viewkeys()).difference(already_matched)
        #print 'number of matches (exact & fuzzy): %i' %len(already_matched)
        #print 'left unmatched: %i' %len(queries)
        results_list = []
        if self.verbosity >= 2:
            print '\n... Heuristic matching ... (' + str(len(queries)) + ' unique chemicals)'
        i = 0
        for query_i in queries:
            i = i + 1
            score = self.query_dict[query_i]
            if self.verbosity >= 2:
                perc_done = i / len(queries)
                perc_done = int(perc_done * 100)
                sys.stdout.write('\r    %d%%' %perc_done)
                sys.stdout.flush()
            #if self.verbosity >= 3:
            #    print ' Processing query %i (Heuristic matching) %s' % (i, query_i)
            # check if we can prepare query (get rid of the garbage name)
            modified_chemical = self.modChemical(query_i)
            # submit query if the chemical name has been modified
            if modified_chemical != query_i:
                #print ' Processing query %i (Heuristic matching) %s, %s' % (i, query_i, modified_chemical)
                raw_result = self.__submitQuery(modified_chemical, 'name_approx')
                res_parsed = self.__parseNameMatches(raw_result, True, score, 'HEURISTIC_MATCH', query_i)
                #print(res_parsed)
                results_list.append(res_parsed)
        if self.verbosity >= 2:
            sys.stdout.write('\n')
            sys.stdout.flush()
        self.results_heuristic = ''.join(results_list)

    ### Method to perform exact matching on a list of chemical names
    def matchExact(self):
        results_list = []
        if self.verbosity >= 2:
            print '... Exact matching ...(' + str(len(self.query_dict)) + ' unique chemicals)'
        i = 0
        for query_i in self.query_dict.viewkeys():
            i = i + 1
            score = self.query_dict[query_i]
            if self.verbosity >= 2:
                perc_done = i / len(self.query_dict)
                perc_done = int(perc_done * 100)
                sys.stdout.write('\r    %d%%' %perc_done)
                sys.stdout.flush()
            #if self.verbosity >= 1:
            #    print ' Processing query %i (Exact matching) %s' % (i, query_i)
            # Get the smile if the query type is INCHI
            if self.__input_type == 'smiles':
                inchi_of_smile = self.getInchiFromSmile(query_i)
#                print("WARNING INCHI: " + query_i + " transformed to : " + self.getInchiFromSmile(query_i))
                raw_result = self.__submitQuery(inchi_of_smile, 'name')
                raw_result = self.__correctThroughProperName(raw_result)
            elif self.__input_type == 'inchis' and "-" in query_i:
                first_part_of_inchi = query_i.split("-")[0]
                #print("WATCH OUT, detected hyphen in inchis. only querying for: " + first_part_of_inchi )
                raw_result = self.__submitQuery(first_part_of_inchi, 'name')
                raw_result = self.__correctThroughProperName(raw_result)
            else:
                raw_result = self.__submitQuery(query_i, 'name')
                if self.__input_type == 'inchis':
                    raw_result = self.__correctThroughProperName(raw_result)
            #print "original name: " + query_i
            #print " "
            results_list.append(self.__parseNameMatches(raw_result, False, score, 'EXACT_MATCH', query_i))
        if self.verbosity >= 2:
            sys.stdout.write('\n')
            sys.stdout.flush()
        self.results_exact = ''.join(results_list)
        
    
    def __correctThroughProperName(self,raw_result):
        results = json.loads(raw_result)
        the_cid = results['response']['docs'][0]['title'][0]
        first_sp = self.__search_space
        self.__search_space = 'cidNameUniqueFull'
        raw_result = self.__submitQuery(the_cid,'title')
        #print('New raw results: ')
        #print(raw_result)
        self.__search_space = first_sp
        return raw_result

    
    
    ### modify chemical names according to some heuristic rules
    def modChemical(self, chemical):
        modified_chemical = chemical
        patterns = ['hcl', 'hydrochloride', 'dihydrohloride',
        'chlorhydrate', 'salt', 'potassium', 'dihydrate',
        'acid', 'oxid', 'chloride', 'alpha','beta', 'cis','trans','D-','L- ','d-','l-']
        found_something = False
        for pattern in patterns:
            modified_chemical = re.sub(pattern, '', chemical)
            if len(modified_chemical) < len(chemical):
                found_something = True
                break;
        if not found_something:
            modified_chemical = re.sub(r'\([^)]*\)', '', chemical)
        return modified_chemical.strip()


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
#		    print self.__input_type
                    if self.__input_type.lower() == "names":
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

    
    ### Method to submit a query for matching to Solr / Lucene
    def __submitQuery(self, query, mode):
        # get rid of non ascii characters
        query = ''.join(c if ord(c) < 128 else '' for c in query)
        # encode query in the format approriate for lucene
        enc_query = ""
        if mode == "name_approx":
#            enc_query = urllib2.quote(mode + ':' + query + '~')
            enc_query = urllib2.quote(mode + ':' + query + '~')
        else:
            enc_query = urllib2.quote(mode + ':\"' + query + '\"')
	if mode == "name_approx":
	    if query.isdigit():
	        enc_query = urllib2.quote(mode + ':' + query)
	        solr_query = ['curl', '-d', 'q=' + enc_query + '+OR+title%3A*' + query  + '&fl=*,score&wt=json&defType=edismax&start=0&rows=200','http://sam.embl.de:' + self.__start_port + '/solr/' + self.__search_space + '/select']
	    else:
	        solr_query = ['curl', '-d', 'q=' + enc_query + '&fl=*,score&wt=json&defType=edismax&start=0&rows=200','http://sam.embl.de:' + self.__start_port + '/solr/' + self.__search_space + '/select']
	else:
            solr_query = ['curl', '-d', 'q=' + enc_query + '&fl=*,score&wt=json&defType=edismax&start=0&rows=200','http://sam.embl.de:' + self.__start_port + '/solr/' + self.__search_space + '/select']
        #print "Solr query (" + mode + ") : "
        #if mode == "name_approx":
        #    print solr_query
        # submit query to Solr / Lucene
        p = subprocess.Popen(solr_query, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        # TODO look att err
        return(out)




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
            if self.__output_file_detail != "null":
                with open(self.__output_file_detail, 'a') as fout:
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
                        with open(self.__output_file_detail, 'a') as fout:
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

    ### Method to reduce the list of matches for chemical names to an optimal one per chemical
    def __parseBestMatches(self):
        if self.verbosity >= 4:
            print('\nParsing best matches...\n')
        results = self.results_exact.rstrip() + '\n' + self.results_fuzzy.rstrip() + '\n' + self.results_heuristic.rstrip()
        results = results.split('\n')
        results = [x for x in results if x != '']
        # sort results before removeing (lower-scoring) duplicates
        results = sorted(results)
        names = []
        user_scores = []
        cids = []
        matched_names = []
        match_scores = []
        match_types = []
        prev_idx = 0
        # list of best matches to be retained
        best_matches = []
        # append sentinel line to results to guarantee correct processing of the last actual entry
        results.append('!!!!!SENTINEL!!!!!\tNA\tNA\tNA\tNA\tNA')
 #       print("PARSING BEST MATCHES")
        for line in results:
            elems = line.split('\t')
            names.append(elems[0])
            user_scores.append(elems[1])
            cids.append(elems[2])
            matched_names.append(elems[3])
            curr_idx = len(names) - 1
            if elems[5] == 'NA':
                elems[5] = 'NO_MATCH'
            match_types.append(elems[5])
            if elems[4] == 'NA':
                elems[4] = '0.0'
            match_scores.append(float(elems[4]))
            if self.verbosity >= 5:
                print('curr_idx: ' + str(curr_idx))
            if not names[prev_idx] == names[curr_idx] or names[curr_idx] == 'SENTINEL':
                if self.verbosity >= 5:
                    print(names[prev_idx] + ' != ' + names[curr_idx] + '  [prev: ' + str(prev_idx) + ' - curr:' + str(curr_idx) + ']')
                if prev_idx + 1 == curr_idx:
                    max_idx = prev_idx
                else:
#                    if self.verbosity >= 1:
#                        print('\nresolving multiple matches:')
#                        for i in range(prev_idx, curr_idx):
#                            print('  '  + names[i] + ' (' + match_types[i] + ') -> ' + matched_names[i] + ': ' + str(match_scores[i]))
                    # determine best scoring match for this chemical
                    #print "DATASTRUCTURE:"
                    #print match_scores  
                    max_score = max(match_scores[prev_idx:curr_idx])
                    max_idx = [i+prev_idx for i, j in enumerate(match_scores[prev_idx:curr_idx]) if j == max_score]
                    # in case of multiple matches with optimal score, arbitrarily return the first of them
                    max_idx = max_idx[0]
                    #if self.verbosity >= 5:
                    #    print('best match:')
                    #    print(names[max_idx] + ' (' + match_types[max_idx] + ') -> ' + matched_names[max_idx] + ': ' + str(match_scores[max_idx]))
                best_matches.append(max_idx)
                if self.verbosity >= 5:
                    print('max_idx: ' + str(max_idx) + '\n')
                prev_idx = curr_idx

        # return a reduced list of best matches with minimal column content
        result = []
        for i in best_matches:
            # parse user scores and re-duplicate entries in the results that resulted from duplicate inputs
            if user_scores[i] == 'NA':
                us = ['NA']
            else:
                us = user_scores[i]
                assert(us[0] == '[' and us[-1] == ']')
                us = us[1:-1]
                us = us.split(',')
                us = [s.strip() for s in us]
            for j in range(len(us)):
                result.append('%s\t%s\t%s\t%s\t%s' %(cids[i], us[j], names[i], matched_names[i], match_types[i]))

        # TODO perhaps restore the origial order of chemicals

        if self.verbosity >= 1:
            match_types = [match_types[i] for i in best_matches]
            cnt_exact = match_types.count('EXACT_MATCH')
            cnt_fuzzy = match_types.count('FUZZY_MATCH')
            cnt_heur = match_types.count('HEURISTIC_MATCH')
            cnt_all = len(match_types)
            print '%i/%i (%.1f%%) exact matches' %(cnt_exact, cnt_all, 100.0*cnt_exact/cnt_all)
            print '%i/%i (%.1f%%) fuzzy matches' %(cnt_fuzzy, cnt_all, 100.0*cnt_fuzzy/cnt_all)
            print '%i/%i (%.1f%%) heuristic matches' %(cnt_heur, cnt_all, 100.0*cnt_heur/cnt_all)
            print '%i/%i (%.1f%%) unmatched' %(cnt_all-cnt_exact-cnt_fuzzy-cnt_heur, cnt_all, 100.0*(cnt_all-cnt_exact-cnt_fuzzy-cnt_heur)/cnt_all)
        return '\n'.join(result)

    ### Auxiliary method to remove the Solr / Lucene lock file from Collection1 and all supported saerch indices
    def __removeWriteLocks(self):
        indices = self.__SUPP_INDICES[:]
        indices.append('collection1')
        for index in indices:
            fn = self.__SOLR_INSTALL_DIR + '/example/solr/' + index + '/data/index/write.lock'
            if os.path.isfile(fn):
                try:
                    retval = os.remove(fn)
                    print 'Removing write locks return value: ' + str(retval)
                    print 'Deleted file: ' + fn
                except OSError:
                    print 'Failed to remove write lock, file: ' + fn
                    # return False if any delete attempt fails
                    return False
        # return True if all files that existed could also be deleted
        return True


    ### Auxiliary method to get two free ports which can be used as Solr start and stop ports
    def __getFreePorts(self):
        sock_start = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_start.bind(('', 0))
        start_port = sock_start.getsockname()[1]
        sock_stop = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_stop.bind(('', 0))
        stop_port = sock_stop.getsockname()[1]
        return([start_port, stop_port])


    ### Auxiliary method to find a running Solr server and determine its listening (start and stop) ports
    def __getSolrListeningPorts(self):
        solr_pid = self.__getPidOfSolrProcess()
        if solr_pid == -1:
            if self.verbosity >= 1:
                print 'Cannot get Solr listening ports because Solr does not appear to be running (no PID bound to it)'
            return None
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=['pid','name','cmdline'])
                if(pinfo['name'] == 'java') and (len(pinfo['cmdline']) == 7) and pinfo['cmdline'][1].startswith('-Djetty.port'):
                    start_port = pinfo['cmdline'][1].split('=')[1]
                    stop_port = pinfo['cmdline'][3].split('=')[1]
                    return {'start_port' : start_port,
                            'stop_port' : stop_port}
            except psutil.NoSuchProcess:
                print 'Cannot get Solr listening ports despite a PID bound to it'
                return None


    ### Auxiliary method to find the process ID of the Solr server with the corresponding listening ports
    def __getPidOfSolrProcess(self):
        solr_cmd = '-Djetty.port'
        if self.__start_port != '-1':
            solr_cmd = '-Djetty.port=' + self.__start_port
        else:
            if self.verbosity >= 2:
                print 'Trying to attach to a running Solr server...'
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=['pid','name','cmdline'])
                if(pinfo['name'] == 'java') and (len(pinfo['cmdline']) == 7) and pinfo['cmdline'][1].startswith(solr_cmd):
                    return pinfo['pid']
            except psutil.NoSuchProcess:
                return -1
        return -1


    ### Auxiliary method to read paramters from the config file
    def __readConfig(self):
        cfg_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../conf/settings.cfg')
        cfg = ConfigParser.ConfigParser()
        cfg.read(cfg_file)
        self.__STOP_KEY = cfg.get('solr', 'stop_key')
        self.__SOLR_INSTALL_DIR = cfg.get('solr', 'solr_install_dir')
        self.__JRE_CMD = cfg.get('solr', 'jre_cmd')
        self.__JRE_MEM = cfg.get('solr', 'jre_mem')
        tmp = cfg.get('solr', 'search_indices')
        self.__SUPP_INDICES = re.findall(r'[[\w\\._-]+', tmp)
        if self.verbosity >= 2:
            print 'Solr stop key ................. ' + self.__STOP_KEY
            print 'Solr installation dir ......... ' + self.__SOLR_INSTALL_DIR
            print 'Solr JRE command .............. ' + self.__JRE_CMD
            print 'Solr JRE memory ............... ' + self.__JRE_MEM
            print 'Solr search indices ........... ' + ', '.join(self.__SUPP_INDICES)
        if self.verbosity >= 3:
            print ''
            os.system('%s -version'%self.__JRE_CMD)
            print ''
