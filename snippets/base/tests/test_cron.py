from datetime import datetime

from mock import patch, mock_open
from nose.tools import assert_raises, eq_, ok_

from snippets.base import ENGLISH_LANGUAGE_CHOICES
from snippets.base.cron import DoesNotExist, import_v1_data
from snippets.base.models import (ClientMatchRule, Snippet,
                                  SnippetLocale, SnippetTemplate)
from snippets.base.tests import TestCase

class ImportTests(TestCase):
    def test_import_v1(self):
        import_data = """
[
  {
    "pk": 515,
    "model": "homesnippets.clientmatchrule",
    "fields": {
      "description": "0",
      "appbuildid": "1",
      "distribution_version": "2",
      "locale": "3",
      "created": "2011-07-28 01:20:41",
      "startpage_version": "4",
      "modified": "2012-07-25 16:21:01",
      "os_version": "5",
      "version": "6",
      "exclude": false,
      "distribution": "7",
      "build_target": "8",
      "channel": "9",
      "name": "10"
    }
  },
  {
    "pk": 516,
    "model": "homesnippets.clientmatchrule",
    "fields": {
      "description": "20",
      "appbuildid": "21",
      "distribution_version": "22",
      "locale": "23",
      "created": "2011-07-28 01:20:41",
      "startpage_version": "24",
      "modified": "2012-07-25 16:21:01",
      "os_version": "25",
      "version": "26",
      "exclude": false,
      "distribution": "27",
      "build_target": "28",
      "channel": "29",
      "name": "30"
    }
  },
  {
    "pk": 4045,
    "model": "homesnippets.snippet",
    "fields": {
      "body": "0",
      "disabled": false,
      "name": "1",
      "created": "2013-06-10 17:42:45",
      "country": "2",
      "modified": "2013-06-11 17:42:45",
      "priority": 2,
      "pub_start": "2013-06-12 18:40:06",
      "pub_end": "2013-06-30 18:40:11",
      "preview": false,
      "client_match_rules": [
        515
      ]
    }
  }
]"""
        open_name = 'snippets.base.cron.open'
        with patch(open_name, mock_open(read_data=import_data), create=True):
            import_v1_data('foo')

        ok_(SnippetTemplate.objects.get(name='Basic Import Template'))

        eq_(ClientMatchRule.objects.count(), 2)
        cmr = ClientMatchRule.objects.get(description='0')
        eq_(cmr.description, '0')
        eq_(cmr.appbuildid, '1')
        eq_(cmr.distribution_version, '2')
        eq_(cmr.locale, '3')
        eq_(cmr.created, datetime(2011, 7, 28, 1, 20, 41))
        eq_(cmr.startpage_version, '4')
        eq_(cmr.modified, datetime(2012, 7, 25, 16, 21, 01))
        eq_(cmr.os_version, '5')
        eq_(cmr.version, '6')
        eq_(cmr.is_exclusion, False)
        eq_(cmr.distribution, '7')
        eq_(cmr.build_target, '8')
        eq_(cmr.channel, '9')
        eq_(cmr.name, '10')

        snippet = Snippet.objects.get(name='1')
        eq_(snippet.data, '{"data": "0"}')
        eq_(snippet.disabled, False)
        eq_(snippet.name, '1')
        eq_(snippet.created, datetime(2013, 06, 10, 17, 42, 45))
        eq_(snippet.modified, datetime(2013, 06, 11, 17, 42, 45))
        eq_(snippet.priority, 2)
        eq_(snippet.publish_start, datetime(2013, 06, 12, 18, 40, 06))
        eq_(snippet.publish_end, datetime(2013, 06, 30, 18, 40, 11))
        eq_(snippet.client_match_rules.count(), 1)
        eq_(snippet.client_match_rules.all()[0], cmr)
        eq_(snippet.on_release, True)
        eq_(snippet.on_beta, True)
        eq_(snippet.on_aurora, True)
        eq_(snippet.on_nightly, True)
        eq_(snippet.on_startpage_1, True)
        eq_(snippet.on_startpage_2, True)
        eq_(snippet.on_startpage_3, True)
        eq_(snippet.on_startpage_4, True)
        eq_(snippet.on_firefox, True)
        eq_(snippet.on_fennec, True)
        eq_(snippet.id, 4045)
        eq_(snippet.country, '2')

        eq_(SnippetLocale.objects.filter(snippet=snippet).count(),
            len(ENGLISH_LANGUAGE_CHOICES))
        for locale_code, locale_name in ENGLISH_LANGUAGE_CHOICES:
            ok_(SnippetLocale.objects
                .filter(snippet=snippet, locale=locale_code).exists())


    def test_invalid_import(self):
        import_data = """
[
  {
    "pk": 4045,
    "model": "homesnippets.snippet",
    "fields": {
      "body": "0",
      "disabled": false,
      "name": "1",
      "created": "2013-06-10 17:42:45",
      "country": "2",
      "modified": "2013-06-11 17:42:45",
      "priority": 2,
      "pub_start": "2013-06-12 18:40:06",
      "pub_end": "2013-06-30 18:40:11",
      "preview": false,
      "client_match_rules": [
        515
      ]
    }
  }
]"""

        open_name = 'snippets.base.cron.open'
        with patch(open_name, mock_open(read_data=import_data), create=True):
            assert_raises(DoesNotExist, import_v1_data, 'foo')

    def test_import_snippet_without_cmr(self):
        """Imported snippets without Client Match Rules, should get disabled."""

        import_data = """
[
  {
    "pk": 4045,
    "model": "homesnippets.snippet",
    "fields": {
      "body": "0",
      "disabled": false,
      "name": "1",
      "created": "2013-06-10 17:42:45",
      "country": "2",
      "modified": "2013-06-11 17:42:45",
      "priority": 2,
      "pub_start": "2013-06-12 18:40:06",
      "pub_end": "2013-06-30 18:40:11",
      "preview": false,
      "client_match_rules": [
      ]
    }
  }
]"""

        open_name = 'snippets.base.cron.open'
        with patch(open_name, mock_open(read_data=import_data), create=True):
            import_v1_data('foo')

        snippet = Snippet.objects.get(pk=4045)
        eq_(snippet.disabled, True)
