import time
import sys
import re
import urllib2
import subprocess
import Levenshtein
import json

__author__ = 'deghou'



class NameMatchingController:


    def __init__(self):
        self.query_dict = ''
        self.occurence_chemicals = ''
        self.results_exact = ''
        self.results_fuzzy = ''
        self.results_heuristic = ''
        self.results_synonyms = ''
        self.solrController = ''


### Main high-level method to perform the chemical name matching
    def matchNames(self, query_file, output_file, approximate_option, exact_option, heuristic_option):
        if self.solrController.verbosity >= 2:
            print '\nStarting name matching...'
        # parse chemicals from the file
        # TODO IO error handling
        self.initQueryDict(query_file)
        # perform the chemical matching

        if self.solrController.output_file_detail != "null":
            with open(self.solrController.output_file_detail, 'a') as fout:
                print >>fout,"Input chemicals\tFetched CIDs\tFetched chemicals\tScores"
        if exact_option:
            start = time.time()
            self.matchExact()
            end = time.time()
            if self.solrController.verbosity >= 2:
                print '    time taken for exact matching:  %.1f sec.' %(end-start)
        if heuristic_option:
            start = time.time()
            self.matchHeuristic()
            end = time.time()
            if self.solrController.verbosity >= 2:
                print '    time taken for heuristic matching: %.1f sec.' %(end-start)
        if approximate_option:
            start = time.time()
            self.matchFuzzy()
            end = time.time()
            if self.solrController.verbosity >= 2:
                print '    time taken for fuzzy matching:  %.1f sec.' %(end-start)
        if self.solrController.verbosity >= 2:
            print '\nParsing results...\n'
        best_matches = self.__parseBestMatches()
        with open(output_file, 'w') as fout:
            best_matches_encoded = best_matches.encode('utf-8')
            print >>fout,"CID fetched\tInput scores\tInput chemicals\tFetched chemicals\tMatch type"
            print >>fout, best_matches_encoded
        assert fout.closed


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
        if self.solrController.verbosity >= 2:
            print '\n... Heuristic matching ... (' + str(len(queries)) + ' unique chemicals)'
        i = 0
        for query_i in queries:
            i = i + 1
            score = self.query_dict[query_i]
            if self.solrController.verbosity >= 2:
                perc_done = i / len(queries)
                perc_done = int(perc_done * 100)
                sys.stdout.write('\r    %d%%' %perc_done)
                sys.stdout.flush()
            # check if we can prepare query (get rid of the garbage name)
            modified_chemical = self.modChemical(query_i)
            # submit query if the chemical name has been modified
            if modified_chemical != query_i:
                #print ' Processing query %i (Heuristic matching) %s, %s' % (i, query_i, modified_chemical)
                raw_result = self.__submitQuery(modified_chemical, 'name_approx')
                res_parsed = self.__parseNameMatches(raw_result, True, score, 'HEURISTIC_MATCH', query_i)
                #print(res_parsed)
                results_list.append(res_parsed)
        if self.solrController.verbosity >= 2:
            sys.stdout.write('\n')
            sys.stdout.flush()
        self.results_heuristic = ''.join(results_list)

    ### Method to perform exact matching on a list of chemical names
    def matchExact(self):
        results_list = []
        if self.solrController.verbosity >= 2:
            print '... Exact matching ...(' + str(len(self.query_dict)) + ' unique chemicals)'
        i = 0
        for query_i in self.query_dict.viewkeys():
            i = i + 1
            score = self.query_dict[query_i]
            if self.solrController.verbosity >= 2:
                perc_done = i / len(self.query_dict)
                perc_done = int(perc_done * 100)
                sys.stdout.write('\r    %d%%' %perc_done)
                sys.stdout.flush()
            #if self.solrController.verbosity >= 1:
            #    print ' Processing query %i (Exact matching) %s' % (i, query_i)
            # Get the smile if the query type is INCHI
            if self.solrController.input_type == 'smiles':
                inchi_of_smile = self.getInchiFromSmile(query_i)
                #                print("WARNING INCHI: " + query_i + " transformed to : " + self.getInchiFromSmile(query_i))
                raw_result = self.__submitQuery(inchi_of_smile, 'name')
                raw_result = self.__correctThroughProperName(raw_result)
            elif self.solrController.input_type == 'inchis' and "-" in query_i:
                first_part_of_inchi = query_i.split("-")[0]
                #print("WATCH OUT, detected hyphen in inchis. only querying for: " + first_part_of_inchi )
                raw_result = self.__submitQuery(first_part_of_inchi, 'name')
                raw_result = self.__correctThroughProperName(raw_result)
            else:
                raw_result = self.__submitQuery(query_i, 'name')
                if self.solrController.input_type == 'inchis':
                    raw_result = self.__correctThroughProperName(raw_result)
            #print "original name: " + query_i
            #print " "
            results_list.append(self.__parseNameMatches(raw_result, False, score, 'EXACT_MATCH', query_i))
        if self.solrController.verbosity >= 2:
            sys.stdout.write('\n')
            sys.stdout.flush()
        self.results_exact = ''.join(results_list)


    ### Method to perform approximate / fuzzy matching on those chemical names
    ### that could not be matched exactly with the above method
    def matchFuzzy(self):
        already_matched = []
        results = self.results_exact.strip() + '\n' + self.results_heuristic.strip()
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
        if self.solrController.verbosity >= 0:
            print '\n... Fuzzy matching ... (' + str(len(queries)) + ' unique chemicals)'

        i = 0
        for query_i in queries:
            i = i + 1
            score = self.query_dict[query_i]
            if self.solrController.verbosity >= 2:
                perc_done = i / len(queries)
                perc_done = int(perc_done * 100)
                sys.stdout.write('\r    %d%%' %perc_done)
                sys.stdout.flush()
            #if self.solrController.verbosity >= 1:
            #    print ' Processing query %i (Fuzzy matching) %s' % (i, query_i)
            # submit query
            raw_result = self.__submitQuery(query_i, 'name_approx')
            raw_results_parsed = self.__parseNameMatches(raw_result, True, score, 'FUZZY_MATCH', query_i)
            # append the results if and only if there is at least one match
            if raw_results_parsed.split('\n')[0].split('\t')[-1] != 'NA':
                results_list.append(raw_results_parsed)
        if self.solrController.verbosity >= 2:
            sys.stdout.write('\n')
            sys.stdout.flush()
        self.results_fuzzy = ''.join(results_list)


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
            if self.solrController.output_file_detail != "null":
                with open(self.solrController.output_file_detail, 'a') as fout:
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
            thresholdL = self.solrController.fuzzyThreshold
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
                        with open(self.solrController.output_file_detail, 'a') as fout:
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
                    #		    print self.solrController.input_type
                    if self.solrController.input_type.lower() == "names":
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


    def __parseBestMatches(self):
        if self.solrController.verbosity >= 4:
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
            if self.solrController.verbosity >= 5:
                print('curr_idx: ' + str(curr_idx))
            if not names[prev_idx] == names[curr_idx] or names[curr_idx] == 'SENTINEL':
                if self.solrController.verbosity >= 5:
                    print(names[prev_idx] + ' != ' + names[curr_idx] + '  [prev: ' + str(prev_idx) + ' - curr:' + str(curr_idx) + ']')
                if prev_idx + 1 == curr_idx:
                    max_idx = prev_idx
                else:
                    #                    if self.solrController.verbosity >= 1:
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
                    #if self.solrController.verbosity >= 5:
                    #    print('best match:')
                    #    print(names[max_idx] + ' (' + match_types[max_idx] + ') -> ' + matched_names[max_idx] + ': ' + str(match_scores[max_idx]))
                best_matches.append(max_idx)
                if self.solrController.verbosity >= 5:
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

        if self.solrController.verbosity >= 1:
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
                solr_query = ['curl', '-d', 'q=' + enc_query + '+OR+title%3A*' + query  + '&fl=*,score&wt=json&defType=edismax&start=0&rows=200','http://sam.embl.de:' + self.solrController.solrInstance.start_port + '/solr/' + self.solrController.search_space + '/select']
            else:
                solr_query = ['curl', '-d', 'q=' + enc_query + '&fl=*,score&wt=json&defType=edismax&start=0&rows=200','http://sam.embl.de:' + self.solrController.solrInstance.start_port + '/solr/' + self.solrController.search_space + '/select']
        else:
            solr_query = ['curl', '-d', 'q=' + enc_query + '&fl=*,score&wt=json&defType=edismax&start=0&rows=200','http://sam.embl.de:' + self.solrController.solrInstance.start_port + '/solr/' + self.solrController.search_space + '/select']
        # submit query to Solr / Lucene
        p = subprocess.Popen(solr_query, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        # TODO look att err
        return(out)
