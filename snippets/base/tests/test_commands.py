from datetime import datetime, timedelta

from mock import Mock

from django.core.management import call_command

from snippets.base.models import STATUS_CHOICES
from snippets.base.tests import ASRSnippetFactory, SnippetFactory, TestCase


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

        asrsnippet_without_end_date = ASRSnippetFactory(
            status=STATUS_CHOICES['Published'],
            publish_end=None)
        asrsnippet_that_has_ended = ASRSnippetFactory(
            status=STATUS_CHOICES['Published'],
            publish_end=datetime.utcnow())
        asrsnippet_ending_in_the_future = ASRSnippetFactory(
            status=STATUS_CHOICES['Published'],
            publish_end=datetime.utcnow() + timedelta(days=1))

        call_command('disable_snippets_past_publish_date', stdout=Mock())

        asrsnippet_without_end_date.refresh_from_db()
        asrsnippet_that_has_ended.refresh_from_db()
        asrsnippet_ending_in_the_future.refresh_from_db()

        self.assertEqual(asrsnippet_that_has_ended.status, STATUS_CHOICES['Approved'])
        self.assertEqual(asrsnippet_without_end_date.status, STATUS_CHOICES['Published'])
        self.assertEqual(asrsnippet_ending_in_the_future.status, STATUS_CHOICES['Published'])
