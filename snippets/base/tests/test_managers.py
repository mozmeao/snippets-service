from datetime import datetime

from mock import patch

from snippets.base.models import Client, ClientMatchRule, JSONSnippet, Snippet
from snippets.base.tests import ClientMatchRuleFactory, SnippetFactory, TestCase
from snippets.base.util import first


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
        matches.side_effect = lambda self, client: return_values.get(
            self.id, False)

        passed, failed = self.manager.all().evaluate('asdf')
        self.assertEqual(set([rule1_pass, rule2_pass, rule4_pass]), set(passed))
        self.assertEqual(set([rule3_fail, rule5_fail]), set(failed))


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

        self.assertEqual(set([snippet_match_1, snippet_match_2]), set(matching_snippets))


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

    def _assert_client_matches_snippets(self, client_attrs, snippets):
        client = self._build_client(**client_attrs)
        matched_snippets = Snippet.cached_objects.match_client(client)
        self.assertEqual(set(matched_snippets), set(snippets))

    def test_match_client_base(self):
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
        self.assertEqual(set(snippets), set([snippet_1, snippet_2, snippet_3]))

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client(self):
        params = {}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['en-US'])
        SnippetFactory.create(on_release=False, on_startpage_4=True,
                              locales=['en-US'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_channel(self):
        params = {'channel': 'phantom'}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['en-US'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_match_channel_partially(self):
        """
        Client channels like "release-cck-mozilla14" should match
        "release".
        """
        params = {'channel': 'release-cck-mozilla14'}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['en-US'])
        SnippetFactory.create(on_release=False, on_startpage_4=True,
                              locales=['en-US'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_startpage(self):
        params = {'startpage_version': '0'}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['en-US'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_name(self):
        params = {'name': 'unicorn'}
        snippet = SnippetFactory.create()
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_locale(self):
        params = {'locale': 'en-US'}
        SnippetFactory.create(on_release=True, on_startpage_4=True, locales=[])
        self._assert_client_matches_snippets(params, [])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_match_locale(self):
        params = {}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True, locales=['en-US'])
        SnippetFactory.create(on_release=True, on_startpage_4=True, locales=['fr'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['es-mx', 'es', 'fr'])
    def test_match_client_multiple_locales(self):
        """
        If there are multiple locales that should match the client's
        locale, include all of them.
        """
        params = {'locale': 'es-mx'}
        snippet_1 = SnippetFactory.create(on_release=True, on_startpage_4=True, locales=['es'])
        snippet_2 = SnippetFactory.create(on_release=True, on_startpage_4=True, locales=['es-mx'])
        self._assert_client_matches_snippets(params, [snippet_1, snippet_2])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['es-mx', 'es', 'fr'])
    def test_match_client_multiple_locales_distinct(self):
        """
        If a snippet has multiple locales and a client matches more
        than one of them, the snippet should only be included in the
        queryset once.
        """
        params = {'locale': 'es-mx'}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['es', 'es-mx'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_invalid_locale(self):
        """
        If client sends invalid locale return snippets with no locales
        specified.
        """
        params = {'locale': 'foo'}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True, locales=[])
        SnippetFactory.create(on_release=True, on_startpage_4=True, locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.models.FIREFOX_STARTPAGE_VERSIONS', ['test-firefox'])
    def test_match_client_startpage_firefox(self):

        """
        Test that FIREFOX_STARTPAGE_VERSIONS gets selected when client is
        Firefox.
        """
        client = self._build_client()
        with patch('snippets.base.managers.first', wraps=first) as first_mock:
            Snippet.cached_objects.match_client(client)
        first_mock.assert_called_with(['test-firefox'], client.startpage_version.startswith)

    @patch('snippets.base.models.FENNEC_STARTPAGE_VERSIONS', ['test-fennec'])
    def test_match_client_startpage_fennec(self):
        """
        Test that FENNEC_STARTPAGE_VERSIONS gets selected when client is
        Fennec.
        """
        client = self._build_client(name='fennec')
        with patch('snippets.base.managers.first', wraps=first) as first_mock:
            JSONSnippet.cached_objects.match_client(client)
        first_mock.assert_called_with(['test-fennec'], client.startpage_version.startswith)

    def test_default_is_same_as_nightly(self):
        """ Make sure that default channel follows nightly. """
        # Snippets matching nightly (and therefor should match default).
        nightly_snippet = SnippetFactory.create(on_nightly=True)

        # Snippets that don't match nightly
        SnippetFactory.create(on_beta=True)

        nightly_client = self._build_client(channel='nightly')
        nightly_snippets = Snippet.cached_objects.match_client(nightly_client)

        default_client = self._build_client(channel='default')
        default_snippets = Snippet.cached_objects.match_client(default_client)

        # Assert that both the snippets returned from nightly and from default
        # are the same snippets. Just `nightly_snippet` in this case.
        self.assertEqual(set([nightly_snippet]), set(nightly_snippets))
        self.assertEqual(set([nightly_snippet]), set(default_snippets))
