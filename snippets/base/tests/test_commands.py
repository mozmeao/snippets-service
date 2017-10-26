from datetime import datetime, timedelta

from mock import Mock

from django.core.management import call_command

from snippets.base.tests import SnippetFactory, TestCase


class DisableSnippetsPastPublishDateTests(TestCase):
    def test_base(self):
        snippet_without_end_date = SnippetFactory(disabled=False)
        snippet_without_end_date.publish_end = None

        snippet_that_has_ended = SnippetFactory(disabled=False)
        snippet_that_has_ended.publish_end = datetime.utcnow()
        snippet_that_has_ended.save()

        snippet_ending_in_the_future = SnippetFactory(disabled=False)
        snippet_ending_in_the_future.publish_end = datetime.utcnow() + timedelta(days=1)
        snippet_ending_in_the_future.save()

        call_command('disable_snippets_past_publish_date', stdout=Mock())

        snippet_without_end_date.refresh_from_db()
        snippet_that_has_ended.refresh_from_db()
        snippet_ending_in_the_future.refresh_from_db()

        self.assertTrue(snippet_that_has_ended.disabled)
        self.assertFalse(snippet_without_end_date.disabled)
        self.assertFalse(snippet_ending_in_the_future.disabled)
