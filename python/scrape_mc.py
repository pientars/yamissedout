import sqlite3
import os.path
import sys
import urllib
from optparse import OptionParser

import requests

import common

from bs4 import BeautifulSoup
from pprint import pprint
from urlparse import urljoin



do_extract_pics = 0

#viable classes
mc_classes = common.valid_classes()

def scrape_mc(cities, db_name, num_pages=1, do_extract_pics=0):
  # Automate a loop later
  for city in cities:
    # The base url for craigslist in New York
    BASE_URL = 'http://'+city+'.craigslist.org/search/mis'
    for i in range(num_pages):
      mc_data = []
      print "---Processing %s Page %d " % (city, i)
      offset = ("?s=" + str(i*100)) if i > 0 else ""
      response = requests.get(BASE_URL + offset)
      soup = BeautifulSoup(response.content)
      missed_connections = soup.find_all('span', {'class':'pl'})
      c = 0
      for missed_connection in missed_connections:
        sys.stdout.write("--Progress: %d%%   \r" % (c) )
        sys.stdout.flush()
        c+=1
        link = missed_connection.find('a').attrs['href']
        url = urljoin(BASE_URL, link)

        features = extract_mc_features(url, city)
        if features:
          mc_data.append(features)
          if (do_extract_pics == 1):
            extract_pics(url)
      # break
      print "---Writing Page " + str(i) + " to Db"
      write_chunk_to_db(mc_data, db_name)

def extract_pics(url, pdir='pics/'):
  response = requests.get(url)
  soup = BeautifulSoup(response.content)
  imgs = soup.findAll("div", {"class":"slide first visible"})
  try:
    os.mkdir(pdir)
  except:
    pass
  for img in imgs:
    imgUrl = img.find('img')['src']
    if not os.path.isfile('pics/' + os.path.basename(imgUrl)):
      print "---Scraping " + str(imgUrl)
      urllib.urlretrieve(imgUrl, 'pics/' + os.path.basename(imgUrl))
    else:
      print "--- " + str(imgUrl) + " already exists"


def extract_mc_features(url, city=""):
  response = requests.get(url)
  soup = BeautifulSoup(response.content)
  post_title = soup.find('h2', {'class':'postingtitle'})
  if post_title:
    mc_data = extract_subject_features(post_title.text.strip())
    mc_data['datetime'] = soup.find('time').attrs['datetime']
    mc_data['raw_subject'] = soup.find('h2', {'class':'postingtitle'}).text.strip().replace("\"", "\'")
    mc_data['body'] = soup.find('section', {'id':'postingbody'}).text.strip().replace("\"", "\'")
    mc_data['url'] = url
    mc_data['city'] = city
    return mc_data
  else:
    print "Skipping over deleted post..."
    return post_title


def extract_subject_features(subject):
  mc_data = {}
  location, new_subject  = get_location(subject)
  mc_data['location'] = location
  split_subject = new_subject.split(' - ')
  mc_data['age'], split_subject = get_age(split_subject)
  mc_data['mc_class'], split_subject = get_class(split_subject)
  mc_data['subject'] = ','.join(split_subject[:])
  mc_data['gender'] = mc_data['mc_class'][0] if mc_data['mc_class'] != 'unknown' else 'unknown'
  return mc_data

def get_location(subj):
  """ Extract the location from the subject line. May do more sophisticated guessing later. """
  if '(' in subj:
    if subj.endswith(')'):
      location = subj[subj.rfind("(")+1:subj.rfind(")")]
      subj = subj[:subj.rfind("(")] +  subj[subj.rfind(")")+1:]
      return location.replace("\"", "\'"), subj.strip()
    else:
      return 'unknown', subj
  else:
    return 'unknown', subj

def get_age(subj):
  str_len = len(subj)
  if subj[str_len - 1].isdigit():
    return int(subj[str_len - 1]), subj[0:str_len-1]
  else:
    return -1, subj

def get_class(subj):
  str_len = len(subj)
  if subj[str_len - 1].strip() in mc_classes:
    return subj[str_len - 1].strip(), subj[0:str_len-1]
  else:
    return 'unknown', subj

def write_database(db_name):
  conn = sqlite3.connect(db_name)
  cursor = conn.cursor()
  cursor.execute("""CREATE TABLE missed_connections (datetime text, raw_subject text, subject text, body text, url text, mc_class text, location text, age real, gender text, city text)""")
  conn.commit()
  conn.close()


def write_chunk_to_db(data, db_name):
  conn = sqlite3.connect(db_name)
  cursor = conn.cursor()
  for row in data:
    cursor.execute("""SELECT subject FROM missed_connections WHERE url = \'%s\' LIMIT 1""" % row["url"])
    if cursor.fetchone() != None:
      print "---Results already in DB, terminating."
      continue; 
    cursor.execute("INSERT INTO missed_connections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row["datetime"], row["raw_subject"], row["subject"], row["body"], row["url"], row["mc_class"], row["location"], str(row["age"]), row["gender"], row["city"]))
    conn.commit()
  conn.close()

def main():
  """main function for standalone usage"""
  usage = "usage: %prog [options] input"
  parser = OptionParser(usage=usage)
  parser.add_option('-n', '--num-pages', default=1, type='int',
                    help='Number of pages to parse BITCH [default: %default]')
  parser.add_option('-e', '--extract-pics', default=False, action='store_true',
                    help='Do you want to download dickpics BITCH')
  parser.add_option('-c', '--cities', default='atlanta',
                    help='Comma-separated list of cities to parse [default: %default]')
  parser.add_option('-d', '--db', default='../db/missed_connections.db',
                    help='DB path [default: %default]')

  (options, args) = parser.parse_args()

  if (len(args) != 0) or (options.num_pages <= 0) or (options.extract_pics not in (0,1)) :
    parser.print_help()
    return 2

  for city in options.cities.split(', '):
    city = city.strip()
    if city not in common.valid_cities() :
      print "City " + city + " is not valid. Choose from:" 
      print '\n'.join(common.valid_cities())
      return 2

  if options.cities.lower() == 'all':
    cities = common.valid_cities()

  else:
    cities = options.cities.split(',')

  # do stuff

  if not os.path.isfile(options.db):
    print "---Constructing Database " 
    write_database(options.db)
  scrape_mc(cities, options.db, num_pages=options.num_pages, do_extract_pics=options.extract_pics)

if __name__ == '__main__':
    sys.exit(main())










