from snippets.base.models import Client, Job
from snippets.base import tests


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
        # Matching snippets.
        snippet_1 = tests.JobFactory.create(
            targets=[
                tests.TargetFactory(on_release=False, on_nightly=True)
            ])
        snippet_2 = tests.JobFactory.create(
            targets=[
                tests.TargetFactory(on_release=False, on_beta=True, on_nightly=True)
            ])
        snippet_3 = tests.JobFactory.create(
            targets=[tests.TargetFactory(on_release=False, on_nightly=True)])

        # Not matching snippets.
        tests.JobFactory.create(targets=[tests.TargetFactory(on_release=False, on_beta=True)])
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
