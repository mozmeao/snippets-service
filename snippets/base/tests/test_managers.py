from datetime import datetime

from unittest.mock import patch

from snippets.base.models import Client, ClientMatchRule, Job, Snippet
from snippets.base import tests


class ClientMatchRuleQuerySetTests(tests.TestCase):
    manager = ClientMatchRule.objects

    @patch.object(ClientMatchRule, 'matches', autospec=True)
    def test_basic(self, matches):
        rule1_pass = tests.ClientMatchRuleFactory.create()
        rule2_pass = tests.ClientMatchRuleFactory.create()
        rule3_fail = tests.ClientMatchRuleFactory.create()
        rule4_pass = tests.ClientMatchRuleFactory.create()
        rule5_fail = tests.ClientMatchRuleFactory.create()

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


class SnippetQuerySetTests(tests.TestCase):
    manager = Snippet.objects

    def test_filter_by_available(self):
        snippet_match_1 = tests.SnippetFactory.create()
        snippet_match_2 = (tests.SnippetFactory.create(publish_start=datetime(2012, 5, 15, 0, 0)))

        # Snippet that starts later.
        tests.SnippetFactory.create(publish_start=datetime(2012, 7, 1, 0, 0))

        # Snippet that ended.
        tests.SnippetFactory.create(publish_end=datetime(2012, 5, 1, 0, 0))

        with patch('snippets.base.managers.datetime') as datetime_mock:
            datetime_mock.utcnow.return_value = datetime(2012, 6, 1, 0, 0)
            matching_snippets = self.manager.all().filter_by_available()

        self.assertEqual(set([snippet_match_1, snippet_match_2]), set(matching_snippets))


class SnippetManagerTests(tests.TestCase):
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
        client_match_rule_pass_1 = tests.ClientMatchRuleFactory(channel='nightly')
        client_match_rule_pass_2 = tests.ClientMatchRuleFactory(channel='/(beta|nightly)/')
        client_match_rule_fail = tests.ClientMatchRuleFactory(channel='release')

        # Matching snippets.
        snippet_1 = tests.SnippetFactory.create(on_nightly=True,
                                                client_match_rules=[client_match_rule_pass_1])
        snippet_2 = tests.SnippetFactory.create(on_beta=True, on_nightly=True,
                                                client_match_rules=[client_match_rule_pass_2])
        snippet_3 = tests.SnippetFactory.create(on_nightly=True)

        # Not matching snippets.
        tests.SnippetFactory.create(on_beta=True)
        tests.SnippetFactory.create(on_nightly=True,
                                    client_match_rules=[client_match_rule_fail])
        tests.SnippetFactory.create(on_nightly=True,
                                    client_match_rules=[client_match_rule_fail,
                                                        client_match_rule_pass_2])
        client = self._build_client(channel='nightly')
        snippets = Snippet.objects.match_client(client)
        self.assertEqual(set(snippets), set([snippet_1, snippet_2, snippet_3]))

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client(self):
        params = {}
        snippet = tests.SnippetFactory.create(on_release=True, on_startpage_4=True,
                                              locales=['en-us'])
        tests.SnippetFactory.create(on_release=False, on_startpage_4=True,
                                    locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_channel(self):
        params = {'channel': 'phantom'}
        snippet = tests.SnippetFactory.create(on_release=True, on_startpage_4=True,
                                              locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_match_channel_partially(self):
        """
        Client channels like "release-cck-mozilla14" should match
        "release".
        """
        params = {'channel': 'release-cck-mozilla14'}
        snippet = tests.SnippetFactory.create(on_release=True, on_startpage_4=True,
                                              locales=['en-us'])
        tests.SnippetFactory.create(on_release=False, on_startpage_4=True,
                                    locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_startpage(self):
        params = {'startpage_version': '0'}
        snippet = tests.SnippetFactory.create(on_release=True, on_startpage_4=True,
                                              locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_name(self):
        params = {'name': 'unicorn'}
        snippet = tests.SnippetFactory.create()
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_not_matching_locale(self):
        params = {'locale': 'en-US'}
        tests.SnippetFactory.create(on_release=True, on_startpage_4=True, locales=[])
        self._assert_client_matches_snippets(params, [])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_match_locale(self):
        params = {}
        snippet = tests.SnippetFactory.create(on_release=True,
                                              on_startpage_4=True, locales=['en-us'])
        tests.SnippetFactory.create(on_release=True, on_startpage_4=True, locales=['fr'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['es-mx', 'es', 'fr'])
    def test_match_client_multiple_locales(self):
        """
        If there are multiple locales that should match the client's
        locale, include all of them.
        """
        params = {'locale': 'es-mx'}
        snippet_1 = tests.SnippetFactory.create(on_release=True,
                                                on_startpage_4=True, locales=['es'])
        snippet_2 = tests.SnippetFactory.create(on_release=True,
                                                on_startpage_4=True, locales=['es-mx'])
        self._assert_client_matches_snippets(params, [snippet_1, snippet_2])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['es-mx', 'es', 'fr'])
    def test_match_client_multiple_locales_distinct(self):
        """
        If a snippet has multiple locales and a client matches more
        than one of them, the snippet should only be included in the
        queryset once.
        """
        params = {'locale': 'es-mx'}
        snippet = tests.SnippetFactory.create(on_release=True, on_startpage_4=True,
                                              locales=['es', 'es-mx'])
        self._assert_client_matches_snippets(params, [snippet])

    @patch('snippets.base.managers.LANGUAGE_VALUES', ['en-us', 'fr'])
    def test_match_client_invalid_locale(self):
        """
        If client sends invalid locale return snippets with no locales
        specified.
        """
        params = {'locale': 'foo'}
        snippet = tests.SnippetFactory.create(on_release=True, on_startpage_4=True, locales=[])
        tests.SnippetFactory.create(on_release=True, on_startpage_4=True, locales=['en-us'])
        self._assert_client_matches_snippets(params, [snippet])

    def test_default_is_same_as_nightly(self):
        """ Make sure that default channel follows nightly. """
        # Snippets matching nightly (and therefor should match default).
        nightly_snippet = tests.SnippetFactory.create(on_nightly=True)

        # Snippets that don't match nightly
        tests.SnippetFactory.create(on_beta=True)

        nightly_client = self._build_client(channel='nightly')
        nightly_snippets = Snippet.objects.match_client(nightly_client)

        default_client = self._build_client(channel='default')
        default_snippets = Snippet.objects.match_client(default_client)

        # Assert that both the snippets returned from nightly and from default
        # are the same snippets. Just `nightly_snippet` in this case.
        self.assertEqual(set([nightly_snippet]), set(nightly_snippets))
        self.assertEqual(set([nightly_snippet]), set(default_snippets))


class JobManagerTests(tests.TestCase):
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

    def _assert_client_matches_jobs(self, client_attrs, jobs):
        client = self._build_client(**client_attrs)
        matched_jobs = Job.objects.match_client(client)
        self.assertEqual(set(matched_jobs), set(jobs))

    def test_match_client_base(self):
        client_match_rule_pass_1 = tests.ClientMatchRuleFactory(channel='nightly')
        client_match_rule_pass_2 = tests.ClientMatchRuleFactory(channel='/(beta|nightly)/')
        client_match_rule_fail = tests.ClientMatchRuleFactory(channel='release')

        # Matching snippets.
        snippet_1 = tests.JobFactory.create(
            targets=[
                tests.TargetFactory(on_release=False, on_nightly=True,
                                    client_match_rules=[client_match_rule_pass_1])
            ])
        snippet_2 = tests.JobFactory.create(
            targets=[
                tests.TargetFactory(on_release=False, on_beta=True, on_nightly=True,
                                    client_match_rules=[client_match_rule_pass_2])
            ])
        snippet_3 = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=False, on_nightly=True)])

        # Not matching snippets.
        tests.JobFactory.create(targets=[tests.TargetFactory(on_release=False, on_beta=True)])

        tests.JobFactory.create(
            targets=[
                tests.TargetFactory(on_nightly=True, client_match_rules=[client_match_rule_fail])
            ])
        tests.JobFactory.create(
            targets=[
                tests.TargetFactory(
                    on_nightly=True,
                    client_match_rules=[client_match_rule_fail, client_match_rule_pass_2])
            ])
        client = self._build_client(channel='nightly')

        snippets = Job.objects.match_client(client)

        self.assertEqual(set(snippets), set([snippet_1, snippet_2, snippet_3]))

    def test_match_client(self):
        params = {}
        job = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='en-us')
        tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=False, on_startpage_6=True)],
            snippet__locale='en-us')
        self._assert_client_matches_jobs(params, [job])

    def test_match_client_not_matching_channel(self):
        params = {'channel': 'phantom'}
        # When no matching channel, return release jobs
        job = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='en-us')
        # For example don't include Beta
        tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=False, on_beta=True, on_startpage_6=True)],
            snippet__locale='en-us')
        self._assert_client_matches_jobs(params, [job])

    def test_match_client_match_channel_partially(self):
        """
        Client channels like "release-cck-mozilla14" should match
        "release".
        """
        params = {'channel': 'release-cck-mozilla14'}
        job = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='en-us')
        tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=False, on_startpage_6=True)],
            snippet__locale='en-us')
        self._assert_client_matches_jobs(params, [job])

    def test_match_client_not_matching_locale(self):
        params = {'locale': 'en-US'}
        tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='fr')
        self._assert_client_matches_jobs(params, [])

    def test_match_client_match_locale(self):
        params = {}
        job = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='en-us')
        tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='fr')
        self._assert_client_matches_jobs(params, [job])

    def test_match_client_multiple_jobs_for_client_locale(self):
        """
        If there are multiple locales that should match the client's
        locale, include all of them.
        """
        params = {'locale': 'es-mx'}
        job_1 = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='es')
        job_2 = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='es-mx')
        # Don't include Spanish (Spain)
        tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='es-es')
        self._assert_client_matches_jobs(params, [job_1, job_2])

    def test_match_client_locale_without_territory(self):
        params = {'locale': 'es'}
        job_1 = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='es')
        # Don't include Spanish (Spain)
        tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale='es-es')
        self._assert_client_matches_jobs(params, [job_1])

    def test_match_locale_with_multiple_codes(self):
        params = {'locale': 'es-mx'}
        job_1 = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=True, on_startpage_6=True)],
            snippet__locale=',es-ar,es-cl,es-mx,')
        self._assert_client_matches_jobs(params, [job_1])

    def test_default_is_same_as_nightly(self):
        """ Make sure that default channel follows nightly. """
        # Jobs matching nightly (and therefor should match default).
        nightly_job = tests.JobFactory.create(targets=[tests.TargetFactory(on_nightly=True)])

        # Jobs that don't match nightly
        tests.JobFactory.create(targets=[tests.TargetFactory(on_beta=True)])

        nightly_client = self._build_client(channel='nightly')
        nightly_jobs = Job.objects.match_client(nightly_client)

        default_client = self._build_client(channel='default')
        default_jobs = Job.objects.match_client(default_client)

        # Assert that both the jobs returned from nightly and from default
        # are the same jobs. Just `nightly_job` in this case.
        self.assertEqual(set([nightly_job]), set(nightly_jobs))
        self.assertEqual(set([nightly_job]), set(default_jobs))
