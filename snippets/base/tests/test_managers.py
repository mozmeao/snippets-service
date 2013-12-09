from datetime import datetime

from mock import patch
from nose.tools import eq_

from snippets.base.managers import SnippetQuerySet
from snippets.base.models import Client, ClientMatchRule, Snippet, SnippetLocale
from snippets.base.tests import ClientMatchRuleFactory, SnippetFactory, TestCase


class ClientMatchRuleQuerySetTests(TestCase):
    manager = ClientMatchRule.cached_objects

    @patch.object(ClientMatchRule, 'matches', autospec=True)
    def test_basic(self, matches):
        rule1_pass = ClientMatchRuleFactory.create()
        rule2_pass = ClientMatchRuleFactory.create()
        rule3_fail = ClientMatchRuleFactory.create()
        rule4_pass = ClientMatchRuleFactory.create()
        rule5_fail = ClientMatchRuleFactory.create()

        return_values = {
            rule1_pass.id: True,
            rule2_pass.id: True,
            rule3_fail.id: False,
            rule4_pass.id: True,
            rule5_fail.id: False,
        }
        matches.side_effect = lambda self, client: return_values.get(self.id, False)

        passed, failed = self.manager.all().evaluate('asdf')
        eq_(set([rule1_pass, rule2_pass, rule4_pass]), set(passed))
        eq_(set([rule3_fail, rule5_fail]), set(failed))


class SnippetQuerySetTests(TestCase):
    manager = Snippet.cached_objects

    def test_filter_by_available(self):
        snippet_match_1 = SnippetFactory.create()
        snippet_match_2 = (SnippetFactory.create(publish_start=datetime(2012, 05, 15, 0, 0)))

        # Snippet that starts later.
        SnippetFactory.create(publish_start=datetime(2012, 07, 01, 0, 0))

        # Snippet that ended.
        SnippetFactory.create(publish_end=datetime(2012, 05, 01, 0, 0))

        with patch('snippets.base.managers.datetime') as datetime_mock:
            datetime_mock.utcnow.return_value = datetime(2012, 06, 01, 0, 0)
            matching_snippets = self.manager.all().filter_by_available()

        eq_(set([snippet_match_1, snippet_match_2]), set(matching_snippets))


class SnippetManagerTests(TestCase):
    def _build_client(self, **client_attrs):
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
        return Client(**params)

    def _assert_client_passes_filters(self, client_attrs, filters):
        client = self._build_client(**client_attrs)
        with patch.object(SnippetQuerySet, 'filter') as mock_filter:
            mock_filter().distinct().return_value = []
            Snippet.cached_objects.match_client(client)
            mock_filter.assert_called_with(**filters)

    def test_base(self):
        client_match_rule_pass_1 = ClientMatchRuleFactory(channel='nightly')
        client_match_rule_pass_2 = ClientMatchRuleFactory(channel='/(beta|nightly)/')
        client_match_rule_fail = ClientMatchRuleFactory(channel='release')

        # Matching snippets.
        snippet_1 = SnippetFactory.create(on_nightly=True,
                                          client_match_rules=[client_match_rule_pass_1])
        snippet_2 = SnippetFactory.create(on_beta=True, on_nightly=True,
                                          client_match_rules=[client_match_rule_pass_2])
        snippet_3 = SnippetFactory.create(on_nightly=True)

        # Not matching snippets.
        SnippetFactory.create(on_beta=True)
        SnippetFactory.create(on_nightly=True,
                              client_match_rules=[client_match_rule_fail])
        SnippetFactory.create(on_nightly=True,
                              client_match_rules=[client_match_rule_fail,
                                                  client_match_rule_pass_2])
        client = self._build_client(channel='nightly')
        snippets = Snippet.cached_objects.match_client(client)
        eq_(set(snippets), set([snippet_1, snippet_2, snippet_3]))

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client(self):
        params = {}
        filters = {
            'on_startpage_4': True,
            'on_release': True,
            'locale_set__locale__in': ['en-us']
        }
        self._assert_client_passes_filters(params, filters)

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_channel(self):
        params = {'channel': 'phantom'}
        filters = {
            'on_startpage_4': True,
            'locale_set__locale__in': ['en-us']
        }
        self._assert_client_passes_filters(params, filters)

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_startpage(self):
        params = {'startpage_version': '0'}
        filters = {
            'on_release': True,
            'locale_set__locale__in': ['en-us']
        }
        self._assert_client_passes_filters(params, filters)

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_name(self):
        params = {'name': 'unicorn'}
        filters = {
            'on_startpage_4': True,
            'on_release': True,
            'locale_set__locale__in': ['en-us']
        }
        self._assert_client_passes_filters(params, filters)

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_locale(self):
        params = {'locale': 'de'}
        filters = {
            'on_startpage_4': True,
            'on_release': True,
            'locale_set__isnull': True,
        }
        self._assert_client_passes_filters(params, filters)

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['es-mx', 'es', 'fr'])
    def test_match_client_multiple_locales(self):
        """
        If there are multiple locales that should match the client's
        locale, include all of them.
        """
        params = {'locale': 'es-MX'}
        filters = {
            'on_startpage_4': True,
            'on_release': True,
            'locale_set__locale__in': ['es-mx', 'es']
        }
        self._assert_client_passes_filters(params, filters)

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['es-mx', 'es', 'fr'])
    def test_match_client_multiple_locale_matches(self):
        """
        If a snippet has multiple locales and a client matches more
        than one of them, the snippet should only be included in the
        queryset once.
        """
        es_mx = SnippetLocale(locale='es-mx')
        es = SnippetLocale(locale='es')
        snippet = SnippetFactory.create(locale_set=[es_mx, es])

        client = self._build_client(locale='es-MX')
        snippets = Snippet.cached_objects.match_client(client)

        # Filter out any snippets that aren't the one we made, and ensure there's only one.
        eq_(len([s for s in snippets if s.pk == snippet.pk]), 1)

    @patch('snippets.base.models.FIREFOX_STARTPAGE_VERSIONS', ['test'])
    def test_startpage_firefox(self):
        """
        Test that FIREFOX_STARTPAGE_VERSIONS gets selected when client is
        Firefox.
        """
        params = {'name': 'FirefoX', 'startpage_version': 'test'}
        filters = {
            'on_startpage_test': True,
            'on_release': True,
            'locale_set__locale__in': ['en-us']
        }
        self._assert_client_passes_filters(params, filters)

    @patch('snippets.base.models.FENNEC_STARTPAGE_VERSIONS', ['test'])
    def test_startpage_fennec(self):
        """
        Test that FENNEC_STARTPAGE_VERSIONS gets selected when client is
        Fennec.
        """
        params = {'name': 'fennec', 'startpage_version': 'test'}
        filters = {
            'on_startpage_test': True,
            'on_release': True,
            'locale_set__locale__in': ['en-us']
        }
        self._assert_client_passes_filters(params, filters)
