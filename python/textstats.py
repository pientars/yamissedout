import sys
import os
import sqlite3
import re
import nltk
import pprint
from optparse import OptionParser
from nltk.collocations import *
from nltk.corpus import stopwords

def read_from_db(db_name, num_grams=3, maxrecords=40):
  conn = sqlite3.connect(db_name)
  cursor = conn.cursor()
  cursor.execute("SELECT body FROM missed_connections")
  num = 0
  lines = []
  regex = re.compile('[^a-zA-Z \']')    #all symbols that will be retained

  body = cursor.fetchone()
  while body:
    stmt = body[0].strip()
    stmt = stmt.lower()                 #convert all words to lower-case
    stmt = regex.sub(' ', stmt)         #remove symbols
    lines.append(stmt)             
    body = cursor.fetchone()

  conn.close()

  line = ''.join(lines)
  #entity_extraction(line)              
  tokens = line.split()

  ignored_words = stopwords.words('english')
  word_filter = lambda w: len(w) < 3 or w in ignored_words

  pp = pprint.PrettyPrinter(indent=4)

  cf_bi = nltk.BigramCollocationFinder.from_words(tokens)
  cf_bi.apply_freq_filter(3)
  cf_bi.apply_word_filter(word_filter)
  bi_scorer = nltk.BigramAssocMeasures.likelihood_ratio
  print('Top bi-grams by likelihood, excluding stop-words:')
  best_list = [str(' '.join(tup)) for tup in cf_bi.nbest(bi_scorer, 20)]
  pp.pprint(best_list)
  print('\n')

  cf_tri = nltk.TrigramCollocationFinder.from_words(tokens)
  cf_tri.apply_freq_filter(3)
  cf_tri.apply_word_filter(word_filter)
  tri_scorer = nltk.TrigramAssocMeasures.likelihood_ratio
  print('Top tri-grams by likelihood, excluding stop-words:')
  best_list = [str(' '.join(tup)) for tup in cf_tri.nbest(tri_scorer, 20)]
  pp.pprint(best_list)
  print('\n')

  bgs = nltk.ngrams(tokens,num_grams)
  fdist = nltk.FreqDist(bgs)

  print('Top ' + str(num_grams) + '-grams by frequency:')
  ngram_rank = fdist.most_common(maxrecords)
  for k,v in ngram_rank:
    print '\t', ' '.join([str(i) for i in k]), v

def entity_extraction(document):
  #if this crashes run 'python -m nltk.downloader all'
  sentences = nltk.sent_tokenize(document)
  sentences = [nltk.word_tokenize(sent) for sent in sentences]
  sentences = [nltk.pos_tag(sent) for sent in sentences]
  grammar = "NP: {<DT>?<JJ>*<NN>}"
  cp = nltk.RegexpParser(grammar)
  result = cp.parse(sentences[0])
  print(result)
  exit()

def main():
  """main function for standalone usage"""
  usage = "usage: %prog [options] input"
  parser = OptionParser(usage=usage)
  parser.add_option('-d', '--db-name', default='../db/missed_connections.db', type='string',
                    help='Database name BITCH [default: %default]')
  parser.add_option('-n', '--num-grams', default=3, type='int',
                    help='Number of grams for the n-gram BITCH [default: %default]')
  parser.add_option('-m', '--max-records', default=40, type='int',
                    help='Max number of records to parse from the db BITCH [default: %default]')

  (options, args) = parser.parse_args()
  if (len(args) != 0) or (options.num_grams <= 1) or (options.max_records < 1) :
    parser.print_help()
    return 2

  db_path = options.db_name
  if not os.path.isfile(db_path): 
    print "No missed connections database at " + db_path + "... Run scrape_mc.py first."
  else: 
    read_from_db(db_name=options.db_name, num_grams=options.num_grams, maxrecords=options.max_records)


if __name__ == '__main__':
    sys.exit(main())
