from datetime import datetime
from unittest.mock import Mock, patch

from django.http.request import QueryDict
from django.test import Client
from django.urls import reverse

from snippets.base import models
from snippets.base.feed import ASRSnippetFilter, SnippetsFeed
from snippets.base.tests import ASRSnippetFactory, TestCase


class ASRSnippetFilterTests(TestCase):
    def test_base(self):
        snippet1, snippet2 = ASRSnippetFactory.create_batch(2)
        snippet3 = ASRSnippetFactory.create(publish_start=datetime(2019, 1, 1))
        snippet4 = ASRSnippetFactory.create(publish_end=datetime(2019, 2, 2))
        filtr = ASRSnippetFilter(QueryDict(), queryset=models.ASRSnippet.objects.all())
        self.assertEqual(set([snippet1, snippet2, snippet3, snippet4]), set(filtr.qs))

    def test_only_scheduled_true(self):
        snippet1 = ASRSnippetFactory.create(publish_end=datetime(2019, 2, 2))
        snippet2 = ASRSnippetFactory.create(publish_start=datetime(2019, 2, 2))
        snippet3 = ASRSnippetFactory.create(publish_start=datetime(2019, 2, 2),
                                            publish_end=datetime(2019, 2, 3))
        ASRSnippetFactory.create(publish_start=None, publish_end=None)
        filtr = ASRSnippetFilter(QueryDict(query_string='only_scheduled=true'),
                                 queryset=models.ASRSnippet.objects.all())
        self.assertEqual(set([snippet1, snippet2, snippet3]), set(filtr.qs))

    def test_only_scheduled_false(self):
        snippet1 = ASRSnippetFactory.create(publish_start=None, publish_end=None)
        ASRSnippetFactory.create(publish_end=datetime(2019, 2, 2))
        filtr = ASRSnippetFilter(QueryDict(query_string='only_scheduled=false'),
                                 queryset=models.ASRSnippet.objects.all())
        self.assertEqual(set([snippet1]), set(filtr.qs))

    def test_only_scheduled_all(self):
        snippet1, snippet2 = ASRSnippetFactory.create_batch(2)
        snippet3 = ASRSnippetFactory.create(publish_end=datetime(2019, 2, 2))
        filtr = ASRSnippetFilter(QueryDict(query_string='only_scheduled=all'),
                                 queryset=models.ASRSnippet.objects.all())
        self.assertEqual(set([snippet1, snippet2, snippet3]), set(filtr.qs))

    def test_name(self):
        snippet1 = ASRSnippetFactory.create(name='foo bar foo')
        ASRSnippetFactory.create(name='foo lala foo')
        filtr = ASRSnippetFilter(QueryDict(query_string='name=bar'),
                                 queryset=models.ASRSnippet.objects.all())
        self.assertEqual(set([snippet1]), set(filtr.qs))

    def test_locale(self):
        snippet1 = ASRSnippetFactory.create(locale='xx')
        snippet2 = ASRSnippetFactory.create(locale='fr')
        ASRSnippetFactory.create(locale='de')
        filtr = ASRSnippetFilter(QueryDict(query_string='locale=xx,fr'),
                                 queryset=models.ASRSnippet.objects.all())
        self.assertEqual(set([snippet1, snippet2]), set(filtr.qs))


class SnippetsFeedTests(TestCase):
    def test_base(self):
        ASRSnippetFactory.create_batch(2)
        client = Client()
        response = client.get(reverse('ical-feed'), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_item_filtering(self):
        request = Mock()
        request.GET = {}

        with patch('snippets.base.feed.models.ASRSnippet') as ASRSnippetMock:
            with patch('snippets.base.feed.ASRSnippetFilter') as ASRSnippetFilterMock:
                ASRSnippetMock.objects.filter.return_value.order_by.return_value = 'foo'
                SnippetsFeed()(request)
        ASRSnippetMock.objects.filter.assert_called_with(for_qa=False,
                                                         status=models.STATUS_CHOICES['Published'])
        ASRSnippetFilterMock.assert_called_with(request.GET, queryset='foo')
