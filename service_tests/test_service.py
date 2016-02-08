#!/usr/bin/env python
import os
import time
from urlparse import urljoin

import pytest
import requests


BASE_URL = os.environ.get('BASE_URL', 'https://snippets.mozilla.com')


@pytest.fixture(scope='module')
def snippets_request():
    url = urljoin(
        BASE_URL,
        '/4/Firefox/32.0.3/20140923175406/Darwin_Universal-gcc3/test-bot-{time}/release/Darwin%2013.3.0/default/default/')
    url = url.format(time=time.time())
    response = requests.get(url, allow_redirects=False)
    return response


@pytest.fixture(scope='module')
def bundle_request(snippets_request):
    response = requests.get(snippets_request.headers['location'], allow_redirects=False)
    return response


@pytest.fixture(scope='module')
def stats_request():
    url = 'https://snippets-stats.mozilla.org/foo.html'
    response = requests.get(url, allow_redirects=False)
    return response


def test_bundle_redirect(snippets_request):
    bundle_url = urljoin(BASE_URL, '/media/bundles/bundle_')
    assert snippets_request.status_code == 302
    assert snippets_request.headers.get('location').startswith(bundle_url)


def test_snippets_cors_headers(snippets_request, bundle_request):
    for req in [snippets_request, bundle_request]:
        assert req.headers.get('access-control-allow-origin') == '*'


def test_caching(snippets_request, bundle_request):
    for req in [snippets_request, bundle_request]:
        assert req.headers.get('x-cache-info', 'caching')
        # Allow time for cache to save.
        time.sleep(1)
        new_req = requests.get(req.url, allow_redirects=False)
        assert req.headers.get('x-cache-info', 'cached')


def test_snippets_stats_cors_headers(stats_request):
    # See bug 965278
    assert stats_request.headers.get('access-control-allow-origin') == 'null'


def test_snippets_stats(stats_request):
    assert stats_request.status_code == 200


def test_bundle_contents(bundle_request):
    assert bundle_request.content.startswith('<div class="snippet_set" id="snippet_set"')
    assert bundle_request.content.endswith('</script></div>')
