from snippets.base.admin.adminmodels import JobAdmin
from snippets.base.admin.legacy import SnippetAdmin
from snippets.base.admin.filters import ChannelFilter
from snippets.base.models import Job, Snippet
from snippets.base.tests import JobFactory, SnippetFactory, TargetFactory, TestCase


class ChannelFilterTests(TestCase):
    def test_job(self):
        nightly_snippets = JobFactory.create_batch(
            2, targets=[TargetFactory(on_release=False, on_nightly=True)])
        JobFactory.create_batch(2, targets=[TargetFactory(on_release=False, on_beta=True)])

        filtr = ChannelFilter(None, {'channel': 'on_nightly'}, Job, JobAdmin)
        result = filtr.queryset(None, Job.objects.all())

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
