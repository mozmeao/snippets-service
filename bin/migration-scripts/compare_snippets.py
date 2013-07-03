#!/usr/bin/env python

"""
Compare snippets returned from two snippets servers.

Extract all urls from apache access logs:

  cat access.log | awk '{ print $7 }' > urls

Sort urls by number of occurences:

  cat urls | sort | uniq -c | sort -rn | awk '{ print $2 }' > ranked-urls

Make sure to open with an editor the urls file and remove any urls
that you don't want to be checked, like urls pointing to the admin
panel.

Fetch all urls using curl:

  export SITE_URL='https://snippets.mozilla.com'
  export DEST_DIR='destination_dir_1'

  for url in `cat ranked-urls`; do
    curl $SITE_URL$url -o "$DEST_DIR/`echo -n $url|md5sum|cut -d ' ' -f 1`";
  done


$DEST_DIR must exist.

Repeat for the second snippets server, changing only $SITE_URL and $DEST_DIR.

Once you have data from both servers, run this script to compare them:

 ./compare_snippets.py ranked-urls destination_dir_1 destination_dir_2

"""


import os
import sys
from hashlib import md5

from pyquery import PyQuery as pq


IGNORE_IDS = [2249, 2250, 3727]


def extract_snippet_ids(document):
    ids = []
    for snippet in document('div.snippet_set').find('[data-snippet-id]'):
        snippet_id = int(snippet.attrib['data-snippet-id'])
        if snippet_id not in IGNORE_IDS:
            ids.append(snippet_id)
    return ids


def main():
    if len(sys.argv) != 4:
        print ('Usage:\n\t {0} urlfile '
               'first_data_directory second_data_directory'.format(sys.argv[0]))
        sys.exit(-1)

    urls = sys.argv[1]
    first_dir = sys.argv[2]
    second_dir = sys.argv[3]

    with open(urls, 'r') as f:
        for url in f.xreadlines():
            md5hash = md5(url.strip()).hexdigest()
            document_1 = pq(filename=os.path.join(first_dir, md5hash))
            document_2 = pq(filename=os.path.join(second_dir, md5hash))

            snippets_1 = extract_snippet_ids(document_1)
            snippets_2 = extract_snippet_ids(document_2)

            if sorted(snippets_1) != sorted(snippets_2):
                print 'Error {url} file {file}'.format(url=url, file=md5hash)
                print snippets_1, snippets_2


if __name__ == '__main__':
    main()
