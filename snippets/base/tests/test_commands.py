from datetime import datetime, timedelta

from unittest.mock import Mock

from django.core.management import call_command

from snippets.base import models
from snippets.base.tests import JobFactory, SnippetFactory, TestCase


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
