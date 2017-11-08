# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import re
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

import pytest
from bs4 import BeautifulSoup
import requests


REQUESTS_TIMEOUT = 20


class TestSnippets:

    URL_TEMPLATE = '{}/{}/Firefox/default/default/default/en-US/{}/default/default/default/'

    _user_agent_firefox = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:10.0.1) Gecko/20100101 Firefox/10.0.1'

    def _get_redirect(self, url, user_agent=_user_agent_firefox, locale='en-US'):

        headers = {'user-agent': user_agent,
                   'accept-language': locale}

        # verify=False ignores invalid certificate
        return requests.get(url, headers=headers, verify=False, timeout=REQUESTS_TIMEOUT)

    def _parse_response(self, content):
        return BeautifulSoup(content, 'html.parser')

    @pytest.mark.parametrize(('version'), ['3', '5'])
    @pytest.mark.parametrize(('channel'), ['aurora', 'beta', 'release'])
    def test_response_codes(self, base_url, version, channel):
        url = self.URL_TEMPLATE.format(base_url, version, channel)
        r = self._get_redirect(url)
        assert r.status_code in (requests.codes.ok, requests.codes.no_content)

    @pytest.mark.parametrize(('channel'), [
        'aurora',
        'beta',
        pytest.param('release', marks=pytest.mark.xfail(
            'mozilla' in pytest.config.getoption('base_url'),
            reason='Activity Stream will be available after Firefox 57'))])
    def test_activity_stream(self, base_url, channel):
        url = self.URL_TEMPLATE.format(base_url, '5', channel)
        soup = self._parse_response(self._get_redirect(url).content)
        script = soup.find('script', type='application/javascript').text
        snippet_json_string = re.search('JSON\.parse\("(.+)"\)', script).groups()[0]
        snippet_set = json.loads(snippet_json_string.replace('%u', r'\u').decode('unicode-escape'))
        assert isinstance(snippet_set, list), 'No snippet set found'

    def test_legacy(self, base_url):
        url = self.URL_TEMPLATE.format(base_url, '3', 'release')
        soup = self._parse_response(self._get_redirect(url).content)
        script = soup.find('script', type='text/javascript').text
        snippet_json_string = re.search("JSON\.parse\('(.+)'\)", script).groups()[0]
        snippet_set = json.loads(snippet_json_string.replace('%u', r'\u').decode('unicode-escape'))
        assert isinstance(snippet_set, list), 'No snippet set found'

    @pytest.mark.parametrize(('channel'), ['aurora', 'beta', 'release'])
    def test_that_snippets_are_well_formed_xml(self, base_url, channel):
        url = self.URL_TEMPLATE.format(base_url, '3', channel)

        r = self._get_redirect(url)
        try:
            print(r.content)
            parseString('<div>{}</div>'.format(r.content))
        except ExpatError as e:
            raise AssertionError('Snippets at {0} do not contain well formed '
                                 'xml: {1}'.format(url, e))
