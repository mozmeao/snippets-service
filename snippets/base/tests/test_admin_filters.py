from snippets.base.admin.adminmodels import JobAdmin
from snippets.base.admin.filters import ChannelFilter
from snippets.base.models import Job
from snippets.base.tests import JobFactory, TargetFactory, TestCase


class ChannelFilterTests(TestCase):
    def test_job(self):
        nightly_snippets = JobFactory.create_batch(
            2, targets=[TargetFactory(on_release=False, on_nightly=True)])
        JobFactory.create_batch(2, targets=[TargetFactory(on_release=False, on_beta=True)])

        filtr = ChannelFilter(None, {'channel': 'on_nightly'}, Job, JobAdmin)
        result = filtr.queryset(None, Job.objects.all())

        self.assertTrue(result.count(), 2)
        self.assertEqual(set(result.all()), set(nightly_snippets))
