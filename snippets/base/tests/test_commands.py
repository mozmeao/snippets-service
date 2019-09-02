from datetime import datetime, timedelta

from unittest.mock import ANY, DEFAULT, Mock, call, patch

from django.core.management import call_command
from django.test.utils import override_settings

from snippets.base import models
from snippets.base.tests import JobFactory, SnippetFactory, TargetFactory, TestCase


class DisableSnippetsPastPublishDateTests(TestCase):
    def test_base(self):
        snippet_without_end_date = SnippetFactory(published=True, publish_end=None)
        snippet_that_has_ended = SnippetFactory(published=True, publish_end=datetime.utcnow())
        snippet_ending_in_the_future = SnippetFactory(
            published=True, publish_end=datetime.utcnow() + timedelta(days=1))

        call_command('disable_snippets_past_publish_date', stdout=Mock())

        snippet_without_end_date.refresh_from_db()
        snippet_that_has_ended.refresh_from_db()
        snippet_ending_in_the_future.refresh_from_db()

        self.assertFalse(snippet_that_has_ended.published)
        self.assertTrue(snippet_without_end_date.published)
        self.assertTrue(snippet_ending_in_the_future.published)


class UpdateJobsTests(TestCase):
    def test_base(self):
        job_without_end_date = JobFactory(
            status=models.Job.PUBLISHED,
            publish_end=None)
        job_that_has_ended = JobFactory(
            status=models.Job.PUBLISHED,
            publish_end=datetime.utcnow())
        job_ending_in_the_future = JobFactory(
            status=models.Job.PUBLISHED,
            publish_end=datetime.utcnow() + timedelta(days=1))
        job_scheduled_ready_to_go = JobFactory(
            status=models.Job.SCHEDULED,
            publish_start=datetime.utcnow())
        job_scheduled_in_the_future = JobFactory(
            status=models.Job.SCHEDULED,
            publish_start=datetime.utcnow() + timedelta(days=1))
        job_cancelled = JobFactory(status=models.Job.CANCELED)
        job_completed = JobFactory(status=models.Job.COMPLETED)

        call_command('update_jobs', stdout=Mock())

        job_without_end_date.refresh_from_db()
        job_that_has_ended.refresh_from_db()
        job_ending_in_the_future.refresh_from_db()
        job_scheduled_ready_to_go.refresh_from_db()
        job_scheduled_in_the_future.refresh_from_db()
        job_cancelled.refresh_from_db()
        job_completed.refresh_from_db()

        self.assertEqual(job_without_end_date.status, models.Job.PUBLISHED)
        self.assertEqual(job_that_has_ended.status, models.Job.COMPLETED)
        self.assertEqual(job_ending_in_the_future.status, models.Job.PUBLISHED)
        self.assertEqual(job_scheduled_ready_to_go.status, models.Job.PUBLISHED)
        self.assertEqual(job_scheduled_in_the_future.status, models.Job.SCHEDULED)
        self.assertEqual(job_cancelled.status, models.Job.CANCELED)
        self.assertEqual(job_completed.status, models.Job.COMPLETED)


class GenerateBundles(TestCase):
    def test_generate_all(self):
        with patch('snippets.base.management.commands.generate_bundles.Job') as job_mock:
            job_mock.objects.all.return_value = []
            call_command('generate_bundles', stdout=Mock())
        job_mock.objects.all.assert_called()
        job_mock.objects.filter.assert_not_called()

    def test_generate_after_timestamp(self):
        with patch('snippets.base.management.commands.generate_bundles.Job') as job_mock:
            job_mock.objects.filter.return_value = []
            call_command('generate_bundles', timestamp='2019-01-01', stdout=Mock())
        job_mock.objects.all.assert_not_called()
        job_mock.objects.filter.assert_called_with(snippet__modified__gte='2019-01-01')

    @override_settings(MEDIA_BUNDLES_PREGEN_ROOT='pregen')
    def test_generation(self):
        target = TargetFactory(
            on_release=True, on_beta=True, on_nightly=False, on_esr=False, on_aurora=False
        )
        # Draft, completed, scheduled or cancelled
        JobFactory(
            status=models.Job.DRAFT,
            snippet__locale=',en,',
            targets=[target],
        )
        JobFactory(
            status=models.Job.COMPLETED,
            snippet__locale=',en,',
            targets=[target],
        )
        JobFactory(
            status=models.Job.SCHEDULED,
            snippet__locale=',en,',
            targets=[target],
        )
        JobFactory(
            status=models.Job.CANCELED,
            snippet__locale=',en,',
            targets=[target],
        )
        # Job to be included in the bundle
        published_job = JobFactory(
            status=models.Job.PUBLISHED,
            snippet__locale=',en,',
            targets=[target],
        )

        with patch.multiple('snippets.base.management.commands.generate_bundles',
                            json=DEFAULT,
                            product_details=DEFAULT,
                            default_storage=DEFAULT) as mock:
            mock['json'].dumps.return_value = ''
            mock['product_details'].languages.keys.return_value = ['fr', 'en-us', 'en-au']
            call_command('generate_bundles', stdout=Mock())

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
            1
        )
        self.assertEqual(
            mock['json'].dumps.call_args_list[0][0][0]['messages'][0]['id'],
            str(published_job.id)
        )

    @override_settings(BUNDLE_BROTLI_COMPRESS=True)
    def test_brotli_called(self):
        with patch('snippets.base.management.commands.generate_bundles.brotli') as brotli_mock:
            brotli_mock.compress.return_value = ''
            self.test_generation()
        brotli_mock.compress.assert_called()

    @override_settings(BUNDLE_BROTLI_COMPRESS=False)
    def test_no_brotli(self):
        with patch('snippets.base.management.commands.generate_bundles.brotli') as brotli_mock:
            self.test_generation()
        brotli_mock.compress.assert_not_called()

    @override_settings(MEDIA_BUNDLES_PREGEN_ROOT='pregen')
    def test_delete(self):
        target = TargetFactory(
            on_release=False, on_beta=False, on_nightly=True, on_esr=False, on_aurora=False
        )
        JobFactory(
            status=models.Job.COMPLETED,
            snippet__locale=',fr,',
            targets=[target],
        )

        with patch('snippets.base.management.commands.generate_bundles.default_storage') as ds_mock:
            # Test that only removes if file exists.
            ds_mock.exists.return_value = True
            call_command('generate_bundles', stdout=Mock())

        ds_mock.delete.assert_called_once_with(
            'pregen/Firefox/nightly/fr/default.json'
        )
        ds_mock.save.assert_not_called()

    def test_delete_does_not_exist(self):
        target = TargetFactory(
            on_release=False, on_beta=False, on_nightly=True, on_esr=False, on_aurora=False
        )
        JobFactory(
            status=models.Job.COMPLETED,
            snippet__locale=',fr,',
            targets=[target],
        )

        with patch('snippets.base.management.commands.generate_bundles.default_storage') as ds_mock:
            # Test that only removes if file exists.
            ds_mock.exists.return_value = False
            call_command('generate_bundles', stdout=Mock())

        ds_mock.delete.assert_not_called()
        ds_mock.save.assert_not_called()
