from datetime import datetime
from unittest.mock import Mock, patch

from django.http.request import QueryDict
from django.test import Client
from django.urls import reverse

from snippets.base import models
from snippets.base.feed import JobFilter, JobsFeed
from snippets.base.tests import JobFactory, TestCase


class JobFilterTests(TestCase):
    def test_base(self):
        job1, job2 = JobFactory.create_batch(2)
        job3 = JobFactory.create(publish_start=datetime(2019, 1, 1))
        job4 = JobFactory.create(publish_end=datetime(2019, 2, 2))
        filtr = JobFilter(QueryDict(), queryset=models.Job.objects.all())
        self.assertEqual(set([job1, job2, job3, job4]), set(filtr.qs))

    def test_only_scheduled_true(self):
        job1 = JobFactory.create(publish_end=datetime(2019, 2, 2))
        job2 = JobFactory.create(publish_start=datetime(2019, 2, 2))
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
        job1 = JobFactory.create(snippet__name='foo bar foo')
        JobFactory.create(snippet__name='foo lala foo')
        filtr = JobFilter(QueryDict(query_string='name=bar'),
                          queryset=models.Job.objects.all())
        self.assertEqual(set([job1]), set(filtr.qs))

    def test_locale(self):
        job1 = JobFactory.create(snippet__locale='xx')
        job2 = JobFactory.create(snippet__locale='fr')
        JobFactory.create(snippet__locale='de')
        filtr = JobFilter(QueryDict(query_string='locale=xx,fr'),
                          queryset=models.Job.objects.all())
        self.assertEqual(set([job1, job2]), set(filtr.qs))


class JobsFeedTests(TestCase):
    def test_base(self):
        JobFactory.create_batch(2)
        client = Client()
        response = client.get(reverse('ical-feed'), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_item_filtering(self):
        request = Mock()
        request.GET = {}

        with patch('snippets.base.feed.models.Job') as JobMock:
            with patch('snippets.base.feed.JobFilter') as JobFilterMock:
                JobMock.objects.filter.return_value.order_by.return_value = 'foo'
                JobsFeed()(request)

        JobMock.objects.filter.assert_called()
        JobFilterMock.assert_called_with(request.GET, queryset='foo')
