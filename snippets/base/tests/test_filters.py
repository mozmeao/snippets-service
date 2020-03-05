from datetime import datetime

from django.http.request import QueryDict

from snippets.base import models
from snippets.base.filters import JobFilter
from snippets.base.tests import JobFactory, TestCase


class JobFilterTests(TestCase):
    def test_base(self):
        job1, job2 = JobFactory.create_batch(2)
        job4 = JobFactory.create(publish_end=datetime(2019, 2, 2))
        job3 = JobFactory.create(publish_start=datetime(2019, 1, 1),
                                 publish_end=datetime(2019, 2, 2))
        filtr = JobFilter(QueryDict(query_string='only_scheduled=all'),
                          queryset=models.Job.objects.all())
        self.assertEqual(set([job1, job2, job3, job4]), set(filtr.qs))

    def test_only_scheduled_true(self):
        job1 = JobFactory.create(publish_end=datetime(2019, 2, 2))
        job2 = JobFactory.create(publish_end=datetime(2019, 2, 2))
        job3 = JobFactory.create(publish_start=datetime(2019, 2, 2),
                                 publish_end=datetime(2019, 2, 3))
        JobFactory.create(publish_start=None, publish_end=None)
        filtr = JobFilter(QueryDict(query_string='only_scheduled=true'),
                          queryset=models.Job.objects.all())
        self.assertEqual(set([job1, job2, job3]), set(filtr.qs))

    def test_only_scheduled_false(self):
        job1 = JobFactory.create(publish_start=None, publish_end=None)
        JobFactory.create(publish_end=datetime(2019, 2, 2))
        filtr = JobFilter(QueryDict(query_string='only_scheduled=false'),
                          queryset=models.Job.objects.all())
        self.assertEqual(set([job1]), set(filtr.qs))

    def test_only_scheduled_all(self):
        job1, job2 = JobFactory.create_batch(2)
        job3 = JobFactory.create(publish_end=datetime(2019, 2, 2))
        filtr = JobFilter(QueryDict(query_string='only_scheduled=all'),
                          queryset=models.Job.objects.all())
        self.assertEqual(set([job1, job2, job3]), set(filtr.qs))

    def test_name(self):
        JobFactory.create(id=2990, snippet__id=20000, snippet__name='foo 1')
        JobFactory.create(id=2991, snippet__id=20001, snippet__name='foo 2')
        job = JobFactory.create(id=2992, snippet__id=20002, snippet__name='bar 1')
        JobFactory.create(id=2993, snippet__name='foo lala foo')
        filtr = JobFilter(
            QueryDict(query_string='only_scheduled=all&name=bar'),
            queryset=models.Job.objects.all()
        )
        self.assertEqual(set([job]), set(filtr.qs))

        # Test search with Job ID
        filtr = JobFilter(
            QueryDict(query_string=f'only_scheduled=all&name={job.id}'),
            queryset=models.Job.objects.all()
        )

        self.assertEqual(set([job]), set(filtr.qs))

        # Test search with Snippet ID
        filtr = JobFilter(
            QueryDict(query_string=f'only_scheduled=all&name={job.snippet.id}'),
            queryset=models.Job.objects.all()
        )
        self.assertEqual(set([job]), set(filtr.qs))

    def test_locale(self):
        job = JobFactory.create(snippet__locale='fr')
        JobFactory.create(snippet__locale='de')
        JobFactory.create(snippet__locale='xx')
        locale = job.snippet.locale
        filtr = JobFilter(QueryDict(query_string=f'only_scheduled=all&locale={locale.id}'),
                          queryset=models.Job.objects.all())
        self.assertEqual(set([job]), set(filtr.qs))
