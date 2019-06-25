from datetime import datetime

from unittest.mock import patch

from snippets.base.models import ASRSnippet, Client, ClientMatchRule, Snippet
from snippets.base.tests import (ASRSnippetFactory, ClientMatchRuleFactory, SnippetFactory,
                                 TargetFactory, TestCase)


class ClientMatchRuleQuerySetTests(TestCase):
    manager = ClientMatchRule.objects

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
    manager = Snippet.objects

    def test_filter_by_available(self):
        snippet_match_1 = SnippetFactory.create()
        snippet_match_2 = (SnippetFactory.create(publish_start=datetime(2012, 5, 15, 0, 0)))

        # Snippet that starts later.
        SnippetFactory.create(publish_start=datetime(2012, 7, 1, 0, 0))

        # Snippet that ended.
        SnippetFactory.create(publish_end=datetime(2012, 5, 1, 0, 0))

        with patch('snippets.base.managers.datetime') as datetime_mock:
            datetime_mock.utcnow.return_value = datetime(2012, 6, 1, 0, 0)
            matching_snippets = self.manager.all().filter_by_available()

        self.assertEqual(set([snippet_match_1, snippet_match_2]), set(matching_snippets))


class SnippetManagerTests(TestCase):
    def _build_client(self, **client_attrs):
        params = {'startpage_version': 5,
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
        matched_snippets = Snippet.objects.match_client(client)
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
        snippets = Snippet.objects.match_client(client)
        self.assertEqual(set(snippets), set([snippet_1, snippet_2, snippet_3]))

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client(self):
        params = {}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['en-us'])
        SnippetFactory.create(on_release=False, on_startpage_4=True,
                              locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_channel(self):
        params = {'channel': 'phantom'}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_match_channel_partially(self):
        """
        Client channels like "release-cck-mozilla14" should match
        "release".
        """
        params = {'channel': 'release-cck-mozilla14'}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['en-us'])
        SnippetFactory.create(on_release=False, on_startpage_4=True,
                              locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_startpage(self):
        params = {'startpage_version': '0'}
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True,
                                        locales=['en-us'])
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
        snippet = SnippetFactory.create(on_release=True, on_startpage_4=True, locales=['en-us'])
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

    def test_default_is_same_as_nightly(self):
        """ Make sure that default channel follows nightly. """
        # Snippets matching nightly (and therefor should match default).
        nightly_snippet = SnippetFactory.create(on_nightly=True)

        # Snippets that don't match nightly
        SnippetFactory.create(on_beta=True)

        nightly_client = self._build_client(channel='nightly')
        nightly_snippets = Snippet.objects.match_client(nightly_client)

        default_client = self._build_client(channel='default')
        default_snippets = Snippet.objects.match_client(default_client)

        # Assert that both the snippets returned from nightly and from default
        # are the same snippets. Just `nightly_snippet` in this case.
        self.assertEqual(set([nightly_snippet]), set(nightly_snippets))
        self.assertEqual(set([nightly_snippet]), set(default_snippets))


class ASRSnippetManagerTests(TestCase):
    def _build_client(self, **client_attrs):
        params = {'startpage_version': 6,
                  'name': 'Firefox',
                  'version': '64.0',
                  'appbuildid': '20180510041606',
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
        matched_snippets = ASRSnippet.objects.match_client(client)
        self.assertEqual(set(matched_snippets), set(snippets))

    def test_match_client_base(self):
        client_match_rule_pass_1 = ClientMatchRuleFactory(channel='nightly')
        client_match_rule_pass_2 = ClientMatchRuleFactory(channel='/(beta|nightly)/')
        client_match_rule_fail = ClientMatchRuleFactory(channel='release')

        # Matching snippets.
        snippet_1 = ASRSnippetFactory.create(
            targets=[
                TargetFactory(on_release=False, on_nightly=True,
                              client_match_rules=[client_match_rule_pass_1])
            ])
        snippet_2 = ASRSnippetFactory.create(
            targets=[
                TargetFactory(on_release=False, on_beta=True, on_nightly=True,
                              client_match_rules=[client_match_rule_pass_2])
            ])
        snippet_3 = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=False, on_nightly=True)])

        # Not matching snippets.
        ASRSnippetFactory.create(targets=[TargetFactory(on_release=False, on_beta=True)])

        ASRSnippetFactory.create(
            targets=[
                TargetFactory(on_nightly=True, client_match_rules=[client_match_rule_fail])
            ])
        ASRSnippetFactory.create(
            targets=[
                TargetFactory(on_nightly=True,
                              client_match_rules=[client_match_rule_fail, client_match_rule_pass_2])
            ])
        client = self._build_client(channel='nightly')

        snippets = ASRSnippet.objects.match_client(client)

        self.assertEqual(set(snippets), set([snippet_1, snippet_2, snippet_3]))

    def test_match_client(self):
        params = {}
        snippet = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='en-us')
        ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=False, on_startpage_6=True)],
            locale='en-us')
        self._assert_client_matches_snippets(params, [snippet])

    def test_match_client_not_matching_channel(self):
        params = {'channel': 'phantom'}
        # When no matching channel, return release snippets
        snippet = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='en-us')
        # For example don't include Beta
        ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=False, on_beta=True, on_startpage_6=True)],
            locale='en-us')
        self._assert_client_matches_snippets(params, [snippet])

    def test_match_client_match_channel_partially(self):
        """
        Client channels like "release-cck-mozilla14" should match
        "release".
        """
        params = {'channel': 'release-cck-mozilla14'}
        snippet = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='en-us')
        ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=False, on_startpage_6=True)],
            locale='en-us')
        self._assert_client_matches_snippets(params, [snippet])

    def test_match_client_not_matching_locale(self):
        params = {'locale': 'en-US'}
        ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='fr')
        self._assert_client_matches_snippets(params, [])

    def test_match_client_match_locale(self):
        params = {}
        snippet = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='en-us')
        ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='fr')
        self._assert_client_matches_snippets(params, [snippet])

    def test_match_client_multiple_snippets_for_client_locale(self):
        """
        If there are multiple locales that should match the client's
        locale, include all of them.
        """
        params = {'locale': 'es-mx'}
        snippet_1 = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='es')
        snippet_2 = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='es-mx')
        # Don't include Spanish (Spain)
        ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='es-es')
        self._assert_client_matches_snippets(params, [snippet_1, snippet_2])

    def test_match_client_locale_without_territory(self):
        params = {'locale': 'es'}
        snippet_1 = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='es')
        # Don't include Spanish (Spain)
        ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale='es-es')
        self._assert_client_matches_snippets(params, [snippet_1])

    def test_match_locale_with_multiple_codes(self):
        params = {'locale': 'es-mx'}
        snippet_1 = ASRSnippetFactory.create(
            targets=[TargetFactory(on_release=True, on_startpage_6=True)],
            locale=',es-ar,es-cl,es-mx,')
        self._assert_client_matches_snippets(params, [snippet_1])

    def test_default_is_same_as_nightly(self):
        """ Make sure that default channel follows nightly. """
        # Snippets matching nightly (and therefor should match default).
        nightly_snippet = ASRSnippetFactory.create(targets=[TargetFactory(on_nightly=True)])

        # Snippets that don't match nightly
        ASRSnippetFactory.create(targets=[TargetFactory(on_beta=True)])

        nightly_client = self._build_client(channel='nightly')
        nightly_snippets = ASRSnippet.objects.match_client(nightly_client)

        default_client = self._build_client(channel='default')
        default_snippets = ASRSnippet.objects.match_client(default_client)

        # Assert that both the snippets returned from nightly and from default
        # are the same snippets. Just `nightly_snippet` in this case.
        self.assertEqual(set([nightly_snippet]), set(nightly_snippets))
        self.assertEqual(set([nightly_snippet]), set(default_snippets))
