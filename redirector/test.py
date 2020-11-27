#!/usr/bin/env python3

from unittest.mock import patch

import main
import redirect


def test_redirect_calculate_redirect_locale_lower():
    assert redirect.calculate_redirect(locale='el-GR', distribution='default')[0] == 'el-gr'


@patch('redirect.CDN_URL', 'https://cdn.example.com')
@patch('redirect.SITE_URL', 'https://www.example.com')
def test_redirect_calculate_redirect_cdn_url():
    full_url = redirect.calculate_redirect(locale='en-US', distribution='default')[2]
    assert full_url == 'https://cdn.example.com/bundles-pregen/Firefox/en-us/default.json'


@patch('redirect.SITE_URL', 'https://www.example.com')
def test_redirect_calculate_redirect_site_url():
    full_url = redirect.calculate_redirect(locale='en-us', distribution='default')[2]
    assert full_url == 'https://www.example.com/bundles-pregen/Firefox/en-us/default.json'


@patch('redirect.SITE_URL', 'https://www.example.com')
def test_redirect_calculate_redirect_experiment():
    full_url = redirect.calculate_redirect(locale='en-us', distribution='experiment-foo-bar')[2]
    assert full_url == 'https://www.example.com/bundles-pregen/Firefox/en-us/foo-bar.json'


@patch('redirect.SITE_URL', 'https://www.example.com')
def test_redirect_calculate_redirect_default_experiment():
    _, distribution, full_url = redirect.calculate_redirect(locale='en-us', distribution='foo-bar')
    assert full_url == 'https://www.example.com/bundles-pregen/Firefox/en-us/default.json'
    assert distribution == 'default'


@patch('main.redirect')
def test_main_index(redirect_mock):
    main.index()
    redirect_mock.assert_called_with('https://snippets.cdn.mozilla.net/')


def test_main_healthz():
    assert main.healthz() == 'OK'


@patch('main.GIT_SHA', 'xxffxx')
def test_main_revision():
    assert main.revision() == 'xxffxx'


@patch('main.SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT', 90)
@patch('main.response')
@patch('main.redirect')
@patch('main.calculate_redirect')
def test_main_redirect_to_bundle(calculate_redirect, redirect_mock, response_mock):
    calculate_redirect.return_value = ('fr', 'default', 'https://www.example.com/bundle.json')
    main.redirect_to_bundle(locale='fr', distribution='default')
    assert redirect_mock.called_with('https://www.example.com/bundle.json')
    response_mock.set_header.assert_called_with('Cache-Control', 'public, max-age=90')
