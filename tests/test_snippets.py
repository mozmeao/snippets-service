# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

import pytest
import requests
from bs4 import BeautifulSoup

REQUESTS_TIMEOUT = 20
URL_TEMPLATE = '{}/{}/Firefox/default/default/default/en-US/{}/default/default/default/'

_user_agent_firefox = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'


def _get_redirect(url, user_agent=_user_agent_firefox, locale='en-US'):

    headers = {'user-agent': user_agent,
               'accept-language': locale}

    return requests.get(url, headers=headers, timeout=REQUESTS_TIMEOUT)


def _parse_response(content):
    return BeautifulSoup(content, 'html.parser')


@pytest.mark.parametrize(('version'), ['3', '5'], ids=['legacy', 'activitystream'])
@pytest.mark.parametrize(('channel'), ['aurora', 'beta', 'release'])
def test_response_codes(base_url, version, channel):
    url = URL_TEMPLATE.format(base_url, version, channel)
    r = _get_redirect(url)
    assert r.status_code in (requests.codes.ok, requests.codes.no_content)


@pytest.mark.parametrize(('channel'), ['aurora', 'beta', 'release'])
def test_that_snippets_are_well_formed_xml(base_url, channel):
    url = URL_TEMPLATE.format(base_url, '3', channel)

    r = _get_redirect(url)
    try:
        print(r.content)
        parseString('<div>{}</div>'.format(r.content))
    except ExpatError as e:
        raise AssertionError('Snippets at {0} do not contain well formed '
                             'xml: {1}'.format(url, e))
