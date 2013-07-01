from mock import patch
from nose.tools import eq_

from snippets.base.managers import SnippetManager
from snippets.base.models import Client, ClientMatchRule, Snippet
from snippets.base.tests import ClientMatchRuleFactory, TestCase


class ClientMatchRuleQuerySetTests(TestCase):
    manager = ClientMatchRule.objects

    @patch.object(ClientMatchRule, 'matches')
    def test_basic(self, match):
        rule1_pass = ClientMatchRuleFactory.create()
        rule2_pass = ClientMatchRuleFactory.create()
        rule3_fail = ClientMatchRuleFactory.create()
        rule4_pass = ClientMatchRuleFactory.create()
        rule5_fail = ClientMatchRuleFactory.create()

        # Return the specified return values in sequence.
        return_values = [True, True, False, True, False]
        match.side_effect = lambda client: return_values.pop(0)

        passed, failed = self.manager.all().evaluate('asdf')
        eq_([rule1_pass, rule2_pass, rule4_pass], passed)
        eq_([rule3_fail, rule5_fail], failed)


@patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
class SnippetManagerTests(TestCase):
    def _assert_client_passes_filters(self, client_attrs, filters):
        params = {'startpage_version': '4',
                  'name': 'Firefox',
                  'version': '23.0a1',
                  'appbuildid': '20130510041606',
                  'build_target': 'Darwin_Universal-gcc3',
                  'locale': 'en-US',
                  'channel': 'release',
                  'os_version': 'Darwin 10.8.0',
                  'distribution': 'default',
                  'distribution_version': 'default_version'}
        params.update(client_attrs)
        client = Client(**params)

        with patch.object(SnippetManager, 'filter') as mock_filter:
            Snippet.objects.match_client(client)
            mock_filter.assert_called_with(**filters)

    def test_match_client(self):
        params = {}
        filters = {
            'on_startpage_4': True,
            'on_release': True,
            'on_firefox': True,
            'locale_set__locale': 'en-us'
        }
        self._assert_client_passes_filters(params, filters)

    def test_match_client_not_matching_channel(self):
        params = {'channel': 'phantom'}
        filters = {
            'on_startpage_4': True,
            'on_firefox': True,
            'locale_set__locale': 'en-us'
        }
        self._assert_client_passes_filters(params, filters)

    def test_match_client_not_matching_startpage(self):
        params = {'startpage_version': '0'}
        filters = {
            'on_release': True,
            'on_firefox': True,
            'locale_set__locale': 'en-us'
        }
        self._assert_client_passes_filters(params, filters)

    def test_match_client_not_matching_name(self):
        params = {'name': 'unicorn'}
        filters = {
            'on_startpage_4': True,
            'on_release': True,
            'locale_set__locale': 'en-us'
        }
        self._assert_client_passes_filters(params, filters)

    def test_match_client_not_matching_locale(self):
        params = {'locale': 'de'}
        filters = {
            'on_startpage_4': True,
            'on_release': True,
            'on_firefox': True
        }
        self._assert_client_passes_filters(params, filters)
