from unittest.mock import Mock, patch

from django.test import Client
from django.urls import reverse

from snippets.base.feed import JobsFeed
from snippets.base.tests import JobFactory, TestCase


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
            with patch('snippets.base.filters.JobFilter') as JobFilterMock:
                JobMock.objects.filter.return_value.order_by.return_value = 'foo'
                JobsFeed()(request)

        JobMock.objects.filter.assert_called()
        JobFilterMock.assert_called_with(request.GET, queryset='foo')
