from datetime import datetime

from snippets.base.admin import ASRSnippetAdmin, SnippetAdmin
from snippets.base.admin.filters import ChannelFilter, ScheduledFilter
from snippets.base.models import ASRSnippet, Snippet
from snippets.base.tests import ASRSnippetFactory, SnippetFactory, TargetFactory, TestCase


class ChannelFilterTests(TestCase):
    def test_asrsnippet(self):

        nightly_snippets = ASRSnippetFactory.create_batch(
            2, targets=[TargetFactory(on_release=False, on_nightly=True)])
        ASRSnippetFactory.create_batch(2, targets=[TargetFactory(on_release=False, on_beta=True)])

        filtr = ChannelFilter(None, {'channel': 'on_nightly'}, ASRSnippet, ASRSnippetAdmin)
        result = filtr.queryset(None, ASRSnippet.objects.all())

        self.assertTrue(result.count(), 2)
        self.assertEqual(set(result.all()), set(nightly_snippets))

    def test_snippet(self):
        nightly_snippets = SnippetFactory.create_batch(
            2, on_release=False, on_nightly=True)
        SnippetFactory.create_batch(2, on_release=False, on_beta=True)

        filtr = ChannelFilter(None, {'channel': 'on_nightly'}, Snippet, SnippetAdmin)
        result = filtr.queryset(None, Snippet.objects.all())

        self.assertTrue(result.count(), 2)
        self.assertEqual(set(result.all()), set(nightly_snippets))


class ScheduledFilterTests(TestCase):
    def test_base(self):
        not_scheduled = ASRSnippetFactory.create()
        scheduled1 = ASRSnippetFactory.create(publish_start=datetime(2019, 1, 1))
        scheduled2 = ASRSnippetFactory.create(publish_start=datetime(2019, 1, 1),
                                              publish_end=datetime(2019, 1, 2))

        filtr = ScheduledFilter(None, {'is_scheduled': 'yes'}, ASRSnippet, ASRSnippetAdmin)
        result = filtr.queryset(None, ASRSnippet.objects.all())

        self.assertTrue(result.count(), 2)
        self.assertEqual(set(result.all()), set([scheduled1, scheduled2]))

        filtr = ScheduledFilter(None, {'is_scheduled': 'no'}, ASRSnippet, ASRSnippetAdmin)
        result = filtr.queryset(None, ASRSnippet.objects.all())

        self.assertTrue(result.count(), 1)
        self.assertEqual(set(result.all()), set([not_scheduled]))
