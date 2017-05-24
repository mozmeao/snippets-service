# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import re
from urlparse import urlparse
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

import pytest
from bs4 import BeautifulSoup
import requests


REQUESTS_TIMEOUT = 20


class TestSnippets:

    test_data = [
        ('/3/Firefox/default/default/default/en-US/release/default/default/default/'),
        ('/3/Firefox/default/default/default/en-US/aurora/default/default/default/'),
        ('/3/Firefox/default/default/default/en-US/beta/default/default/default/')]

    _user_agent_firefox = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:10.0.1) Gecko/20100101 Firefox/10.0.1'

    def _get_redirect(self, url, user_agent=_user_agent_firefox, locale='en-US'):

        headers = {'user-agent': user_agent,
                   'accept-language': locale}

        # verify=False ignores invalid certificate
        return requests.get(url, headers=headers, verify=False, timeout=REQUESTS_TIMEOUT)

    def assert_valid_url(self, url, path, user_agent=_user_agent_firefox, locale='en-US'):
        """Checks if a URL returns a 200 OK response."""

        # Only check http and https links
        if not urlparse(url).scheme.startswith('http'):
            return True

        headers = {'user-agent': user_agent,
                   'accept-language': locale}

        # HEAD doesn't return page body.
        try:
            r = requests.get(url, headers=headers, timeout=REQUESTS_TIMEOUT,
                             allow_redirects=True, verify=False)
        except requests.exceptions.RequestException as e:
            raise AssertionError('Error connecting to {0} in {1}: {2}'.format(
                url, path, e))
        assert requests.codes.ok == r.status_code, \
            'Bad URL {0} found in {1}'.format(url, path)
        return True

    def _parse_response(self, content):
        return BeautifulSoup(content)

    @pytest.mark.parametrize(('path'), test_data)
    def test_snippet_set_present(self, base_url, path):
        full_url = base_url + path

        r = self._get_redirect(full_url)
        assert requests.codes.ok == r.status_code, full_url

        soup = self._parse_response(r.content)
        snippet_script = soup.find('script', type="text/javascript").text
        snippet_json_string = re.search("JSON.parse\('(.+)'\)", snippet_script).groups()[0]
        snippet_set = json.loads(snippet_json_string.replace('%u', r'\u').decode('unicode-escape'))

        assert isinstance(snippet_set, list), 'No snippet set found'

    @pytest.mark.parametrize(('path'), test_data)
    def test_all_links(self, base_url, path):
        full_url = base_url + path

        soup = self._parse_response(self._get_redirect(full_url).content)
        snippet_links = soup.select("a")

        for link in snippet_links:
            self.assert_valid_url(link['href'], path)

    @pytest.mark.parametrize(('path'), test_data)
    def test_that_snippets_are_well_formed_xml(self, base_url, path):
        full_url = base_url + path

        r = self._get_redirect(full_url)
        try:
            parseString('<div>{}</div>'.format(r.content))
        except ExpatError as e:
            raise AssertionError('Snippets at {0} do not contain well formed '
                                 'xml: {1}'.format(full_url, e))
