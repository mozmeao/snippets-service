from django.http.request import QueryDict

from snippets.base.models import Snippet
from snippets.base.tests import SnippetFactory, TestCase
from snippets.base.util import (deep_search_and_replace, first,
                                fluent_link_extractor, get_object_or_none, urlparams)


class TestGetObjectOrNone(TestCase):
    def test_does_not_exist(self):
        """Return None if no matching object exists."""
        value = get_object_or_none(Snippet, name='Does not exist')
        self.assertEqual(value, None)

    def test_multiple_objects_returned(self):
        """Return None if multiple objects are returned."""
        SnippetFactory.create(data='{"multiple": 1}')
        SnippetFactory.create(data='{"multiple": 1}')
        value = get_object_or_none(Snippet, data='{"multiple": 1}')
        self.assertEqual(value, None)

    def test_exists(self):
        """If no exceptions occur, return the matched object."""
        video = SnippetFactory.create(name='exists')
        value = get_object_or_none(Snippet, name='exists')
        self.assertEqual(value, video)


class TestFirst(TestCase):
    def test_basic(self):
        items = [(0, 'foo'), (1, 'bar'), (2, 'baz')]
        self.assertEqual(first(items, lambda x: x[0] == 1), (1, 'bar'))

    def test_no_match(self):
        """Return None if the callback never passes for any item."""
        items = [(0, 'foo'), (1, 'bar'), (2, 'baz')]
        self.assertEqual(first(items, lambda x: x[0] == 17), None)


class TestFluentLinkExtractor(TestCase):
    def test_multiple_links_with_metrics(self):
        data = {
            'text': ('We have an <a href="http://example.com">example</a> and another'
                     ' <a href="https://blog.mozvr.com/introducing-hubs-a-new-way-to-'
                     'get-together-online/#utm_source=desktop-snippet&amp;utm_medium='
                     'snippet&amp;utm_campaign=MozillaHubsIntro&amp;utm_term=8460&amp;'
                     'utm_content=REL">link</a> that has more complex format. One link that has '
                     'a <a data-metric="custom-click" href="https://mozilla.org">custom metric</a>'
                     'and yet another that has <a foo="bar">no href attrib</a>'),
            'title': ('And this another variable with <a href="https://snippets.mozilla.org">more '
                      'links</a>'),
            'special_account': 'With <a href="special:accounts">special accounts link</a>.',
            'special_appMenu': 'and another <a href="special:appMenu">special menu link</a>.',
            'nolinks': 'And finally one with no links.',
        }
        final_data = {
            'text': ('We have an <link0>example</link0> and another'
                     ' <link1>link</link1> that has more complex format. One link that has '
                     'a <link2>custom metric</link2>'
                     'and yet another that has <link3>no href attrib</link3>'),
            'title': 'And this another variable with <link4>more links</link4>',
            'special_account': 'With <link5>special accounts link</link5>.',
            'special_appMenu': 'and another <link6>special menu link</link6>.',
            'nolinks': 'And finally one with no links.',
            'links': {
                'link0': {
                    'url': 'http://example.com'
                },
                'link1': {
                    'url': ('https://blog.mozvr.com/introducing-hubs-a-new-way-to-get-together'
                            '-online/#utm_source=desktop-snippet&amp;utm_medium=snippet&amp'
                            ';utm_campaign=MozillaHubsIntro&amp;utm_term=8460&amp;utm_content=REL')
                },
                'link2': {
                    'url': 'https://mozilla.org',
                    'metric': 'custom-click'
                },
                'link3': {
                    'url': ''
                },
                'link4': {
                    'url': 'https://snippets.mozilla.org'
                },
                'link5': {
                    'action': 'SHOW_FIREFOX_ACCOUNTS',
                },
                'link6': {
                    'action': 'OPEN_APPLICATIONS_MENU',
                    'args': 'appMenu',
                },
            }
        }
        generated_data = fluent_link_extractor(
            data, ['text', 'title', 'special_account', 'special_appMenu', 'nolinks'])

        self.assertEqual(final_data['text'], generated_data['text'])
        self.assertEqual(final_data['title'], generated_data['title'])
        self.assertEqual(final_data['nolinks'], generated_data['nolinks'])
        self.assertEqual(final_data['links'], generated_data['links'])


class DeepSearchAndReplaceTests(TestCase):
    def test_base(self):
        data = {
            'text': 'this is the text with [[snippet_id]]',
            'list': [
                'this includes [[snippet_id]]',
                'in a list',
                'multiple [[snippet_id]] times'
            ],
            'links': {
                'link0': {
                    'url': 'http://example.com/foo/?utm_term=[[snippet_id]]&utm_param=foo'
                }
            }
        }
        generated_data = deep_search_and_replace(data, '[[snippet_id]]', '7748')
        expected_data = {
            'text': 'this is the text with 7748',
            'list': [
                'this includes 7748',
                'in a list',
                'multiple 7748 times'
            ],
            'links': {
                'link0': {
                    'url': 'http://example.com/foo/?utm_term=7748&utm_param=foo'
                }
            }
        }
        self.assertEqual(generated_data, expected_data)


class URLParamsTests(TestCase):
    def test_base(self):
        url = 'https://www.example.com/?foo=foo&locale=el&a=5'
        new_url = urlparams(url, query_dict=QueryDict('a=1&b=2'), **{'foo': 'bar', 'la': 'lo'})
        self.assertEqual(new_url, 'https://www.example.com/?foo=bar&locale=el&a=1&b=2&la=lo')

    def test_replace_false(self):
        url = 'https://www.example.com/?foo=foo&locale=el&a=5'
        new_url = urlparams(url, replace=False,
                            query_dict=QueryDict('a=1&b=2'), **{'foo': 'bar', 'la': 'lo'})
        self.assertEqual(new_url, 'https://www.example.com/?foo=foo&locale=el&a=5&b=2&la=lo')

    def test_fragment(self):
        url = 'https://www.example.com'
        new_url = urlparams(url, fragment='boing')
        self.assertEqual(new_url, 'https://www.example.com/#boing')
