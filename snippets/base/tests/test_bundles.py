import json
from unittest.mock import ANY, DEFAULT, Mock, call, patch

from django.db.models import Q
from django.test.utils import override_settings

from snippets.base.bundles import generate_bundles
from snippets.base.models import Distribution, DistributionBundle, Job
from snippets.base.tests import (DistributionBundleFactory, DistributionFactory,
                                 JobFactory, TargetFactory, TestCase)


class GenerateBundlesTests(TestCase):
    def setUp(self):
        self.distribution = DistributionFactory.create(name='Default')
        self.distribution_bundle = DistributionBundleFactory.create(name='Default',
                                                                    code_name='default')
        self.distribution_bundle.distributions.add(self.distribution)

    def test_generate_all(self):
        with patch('snippets.base.bundles.models.Job') as job_mock:
            job_mock.objects.all.return_value = Job.objects.none()
            generate_bundles(stdout=Mock())
        job_mock.objects.all.assert_called()
        job_mock.objects.filter.assert_not_called()

    def test_generate_after_timestamp(self):
        with patch('snippets.base.bundles.models.Job') as job_mock:
            job_mock.objects.filter.return_value = Job.objects.none()
            generate_bundles(timestamp='2019-01-01', stdout=Mock())
        job_mock.objects.all.assert_not_called()
        job_mock.objects.filter.assert_called_with(
            Q(snippet__modified__gte='2019-01-01') |
            Q(distribution__distributionbundle__modified__gte='2019-01-01')
        )

    @override_settings(MEDIA_BUNDLES_PREGEN_ROOT='pregen')
    def test_generation(self):
        target = TargetFactory(
            on_release=True, on_beta=True, on_nightly=False, on_esr=False, on_aurora=False
        )
        # Draft, completed, scheduled or cancelled
        JobFactory(
            status=Job.DRAFT,
            snippet__locale=',en,',
            targets=[target],
        )
        JobFactory(
            status=Job.COMPLETED,
            snippet__locale=',en,',
            targets=[target],
        )
        JobFactory(
            status=Job.SCHEDULED,
            snippet__locale=',en,',
            targets=[target],
        )
        JobFactory(
            status=Job.CANCELED,
            snippet__locale=',en,',
            targets=[target],
        )
        JobFactory(
            status=Job.PUBLISHED,
            snippet__locale=',en,',
            targets=[target],
            distribution__name='not-default',
        )

        # Jobs to be included in the bundle
        published_job_1 = JobFactory(
            status=Job.PUBLISHED,
            snippet__locale=',en,',
            targets=[target],
        )
        published_job_2 = JobFactory(
            status=Job.PUBLISHED,
            snippet__locale=',en,',
            targets=[target],
            distribution__name='other-distribution-part-of-default-bundle',
        )

        # Add Distribution to the Default DistributionBundle
        DistributionBundle.objects.get(name='Default').distributions.add(
            Distribution.objects.get(name='other-distribution-part-of-default-bundle')
        )

        with patch.multiple('snippets.base.bundles',
                            json=DEFAULT,
                            product_details=DEFAULT,
                            default_storage=DEFAULT) as mock:
            mock['json'].dumps.return_value = ''
            mock['product_details'].languages.keys.return_value = ['fr', 'en-us', 'en-au']
            generate_bundles(stdout=Mock())

        self.assertEqual(mock['default_storage'].save.call_count, 4)

        mock['default_storage'].save.assert_has_calls([
            call('pregen/Firefox/release/en-us/default.json', ANY),
            call('pregen/Firefox/release/en-au/default.json', ANY),
            call('pregen/Firefox/beta/en-us/default.json', ANY),
            call('pregen/Firefox/beta/en-au/default.json', ANY),
        ], any_order=True)

        # Check that there's only one job included in the bundle and that it's
        # the correct one.
        self.assertEqual(
            len(mock['json'].dumps.call_args_list[0][0][0]['messages']),
            2
        )
        self.assertEqual(
            set([mock['json'].dumps.call_args_list[0][0][0]['messages'][0]['id'],
                 mock['json'].dumps.call_args_list[0][0][0]['messages'][1]['id']]),
            set([str(published_job_1.id), str(published_job_2.id)])
        )

    @override_settings(
        MEDIA_BUNDLES_PREGEN_ROOT='pregen',
        NIGHTLY_INCLUDES_RELEASE=True,
    )
    def test_nightly_includes_release(self):
        release_job = JobFactory(
            status=Job.PUBLISHED,
            snippet__locale=',en,',
            targets=[
                TargetFactory(
                    on_release=True, on_beta=True, on_nightly=False, on_esr=False, on_aurora=False)
            ]
        )
        nightly_job = JobFactory(
            status=Job.PUBLISHED,
            snippet__locale=',en,',
            targets=[
                TargetFactory(
                    on_release=True, on_beta=False, on_nightly=True, on_esr=False, on_aurora=False)
            ]
        )

        # Beta only job, not to be included
        JobFactory(
            status=Job.PUBLISHED,
            snippet__locale=',en,',
            targets=[
                TargetFactory(
                    on_release=False, on_beta=True, on_nightly=False, on_esr=False, on_aurora=False)
            ]
        )

        with patch.multiple('snippets.base.bundles',
                            json=DEFAULT,
                            product_details=DEFAULT,
                            default_storage=DEFAULT) as mock:
            mock['json'].dumps.return_value = ''
            mock['product_details'].languages.keys.return_value = ['en-us']
            generate_bundles(stdout=Mock())

        # Loop to find the nighlty bundle
        for arg_list in mock['json'].dumps.call_args_list:
            if arg_list[0][0]['metadata']['channel'] == 'nightly':
                self.assertEqual(
                    len(arg_list[0][0]['messages']),
                    2
                )
                self.assertEqual(
                    set([arg_list[0][0]['messages'][0]['id'],
                         arg_list[0][0]['messages'][1]['id']]),
                    set([str(release_job.id), str(nightly_job.id)])
                )
                self.assertEqual(
                    set([arg_list[0][0]['messages'][0]['targeting'],
                         arg_list[0][0]['messages'][1]['targeting']]),
                    set(['', 'false'])
                )

    @override_settings(BUNDLE_BROTLI_COMPRESS=True)
    def test_brotli_called(self):
        with patch('snippets.base.bundles.brotli') as brotli_mock:
            brotli_mock.compress.return_value = ''
            self.test_generation()
        brotli_mock.compress.assert_called()

    @override_settings(BUNDLE_BROTLI_COMPRESS=False)
    def test_no_brotli(self):
        with patch('snippets.base.bundles.brotli') as brotli_mock:
            self.test_generation()
        brotli_mock.compress.assert_not_called()

    @override_settings(MEDIA_BUNDLES_PREGEN_ROOT='pregen')
    def test_delete(self):
        distribution = DistributionFactory()
        distribution_bundle = DistributionBundleFactory(
            code_name='foo',
            enabled=False,
        )
        distribution_bundle.distributions.add(distribution)

        target = TargetFactory(
            on_release=False, on_beta=False, on_nightly=True, on_esr=False, on_aurora=False
        )
        JobFactory(
            status=Job.COMPLETED,
            snippet__locale=',fr,',
            targets=[target],
        )

        # Still published, but belongs to a disabled distribution
        JobFactory(
            status=Job.PUBLISHED,
            snippet__locale=',fr,',
            targets=[target],
            distribution=distribution,
        )

        with patch('snippets.base.bundles.default_storage') as ds_mock:
            # Test that only removes if file exists.
            ds_mock.exists.return_value = True
            generate_bundles(stdout=Mock())

        ds_mock.delete.assert_has_calls([
            call('pregen/Firefox/nightly/fr/default.json'),
            call('pregen/Firefox/nightly/fr/foo.json')
        ])
        ds_mock.save.assert_not_called()

    def test_delete_does_not_exist(self):
        target = TargetFactory(
            on_release=False, on_beta=False, on_nightly=True, on_esr=False, on_aurora=False
        )
        JobFactory(
            status=Job.COMPLETED,
            snippet__locale=',fr,',
            targets=[target],
        )

        with patch('snippets.base.bundles.default_storage') as ds_mock:
            # Test that only removes if file exists.
            ds_mock.exists.return_value = False
            generate_bundles(stdout=Mock())

        ds_mock.delete.assert_not_called()
        ds_mock.save.assert_not_called()

    def test_limit_to_locale_channel_dist(self):
        job = JobFactory(
            status=Job.PUBLISHED,
            snippet__locale=',el,',
        )

        result = json.loads(
            generate_bundles(
                limit_to_locale='el',
                limit_to_channel='release',
                limit_to_distribution_bundle='default',
                save_to_disk=False
            ).read()
        )

        self.assertEqual(result['messages'][0]['id'], str(job.id))
        self.assertEqual(result['metadata']['number_of_snippets'], 1)
        self.assertEqual(result['metadata']['channel'], 'release')
        self.assertEqual(result['metadata']['locale'], 'el')
        self.assertEqual(result['metadata']['distribution_bundle'], 'default')

    def test_limit_to_locale_channel_dist_no_snippets(self):
        result = json.loads(
            generate_bundles(
                limit_to_locale='el',
                limit_to_channel='release',
                limit_to_distribution_bundle='default',
                save_to_disk=False
            ).read()
        )

        self.assertEqual(len(result['messages']), 0)
        self.assertEqual(result['metadata']['number_of_snippets'], 0)
        self.assertEqual(result['metadata']['channel'], 'release')
        self.assertEqual(result['metadata']['locale'], 'el')
        self.assertEqual(result['metadata']['distribution_bundle'], 'default')
