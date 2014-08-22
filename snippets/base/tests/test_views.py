import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test.client import RequestFactory
from django.test.utils import override_settings

from funfactory.helpers import urlparams
from mock import ANY, patch
from nose.tools import eq_, ok_

from snippets.base import views
from snippets.base.models import Client
from snippets.base.tests import (CONTAINS, JSONSnippetFactory, SnippetFactory,
                                 SnippetTemplateFactory, TestCase)


@override_settings(ETAG_CACHE_TIMEOUT=90)
class FetchSnippetsTests(TestCase):
    def setUp(self):
        self.view = views.FetchSnippets()
        self.view.get_client_cache_key = lambda *args: 'client_key'

        self.mock_response = HttpResponse('')

        self.factory = RequestFactory()
        self.mock_request = self.factory.get('/')

        self.view_kwargs = {
            'startpage_version': '4',
            'name': 'Firefox',
            'version': '23.0a1',
            'appbuildid': '20130510041606',
            'build_target': 'Darwin_Universal-gcc3',
            'locale': 'en-US',
            'channel': 'nightly',
            'os_version': 'Darwin 10.8.0',
            'distribution': 'default',
            'distribution_version': 'default_version'
        }

    def test_generate_response(self):
        # Matching snippets.
        snippet_1 = SnippetFactory.create(on_nightly=True)

        # Matching but disabled snippet.
        SnippetFactory.create(on_nightly=True, disabled=True)

        # Snippet that doesn't match.
        SnippetFactory.create(on_nightly=False),

        client = Client('4', 'Firefox', '23.0a1', '20130510041606', 'Darwin_Universal-gcc3',
                        'en-US', 'nightly', 'Darwin%2010.8.0', 'default', 'default_version')
        request = self.factory.get('/')

        with patch.object(views, 'render') as render:
            render.return_value = HttpResponse('asdf')

            response = self.view.generate_response(request, client)
            render.assert_called_with(request, ANY, {
                'snippets': CONTAINS(snippet_1, exclusive=True),
                'client': client,
                'locale': 'en-US',
            })

            eq_(response, render.return_value)
            asdf_sha256 = 'f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b'
            eq_(response['ETag'], asdf_sha256)
            eq_(response['Vary'], 'If-None-Match')

    def test_get_request_match_cache(self):
        """
        If the request has an ETag and it matches the cached ETag,
        return a 304.
        """
        self.view.generate_response = lambda *args: self.mock_response
        self.mock_request.META['HTTP_IF_NONE_MATCH'] = 'etag'

        with patch('snippets.base.views.cache') as cache:
            cache.get.return_value = 'etag'
            response = self.view.get(self.mock_request, **self.view_kwargs)

        ok_(not cache.set.called)
        eq_(response.status_code, 304)
        eq_(response['ETag'], 'etag')

    def test_get_cache_doesnt_match_response(self):
        """
        If the request ETag and cached ETag don't match, and the
        resulting response's ETag doesn't match the cache, the cache
        should be updated.
        """
        self.view.generate_response = lambda *args: self.mock_response
        self.mock_response['ETag'] = 'etag'

        with patch('snippets.base.views.cache') as cache:
            cache.get.return_value = 'other_etag'
            self.view.get(self.mock_request, **self.view_kwargs)

        cache.set.assert_called_with('client_key', 'etag', 90)

    def test_get_cache_empty(self):
        """
        If the cache is empty, it should be updated with the response's
        ETag.
        """
        self.view.generate_response = lambda *args: self.mock_response
        self.mock_response['ETag'] = 'etag'

        with patch('snippets.base.views.cache') as cache:
            cache.get.return_value = None
            self.view.get(self.mock_request, **self.view_kwargs)

        cache.set.assert_called_with('client_key', 'etag', 90)

    def test_get_request_doesnt_match_cache_matches_response(self):
        """
        If the request's ETag doesn't match the cache but it matches
        the response's ETag, return a 304.
        """
        self.view.generate_response = lambda *args: self.mock_response
        self.mock_request.META['HTTP_IF_NONE_MATCH'] = 'etag'
        self.mock_response['ETag'] = 'etag'

        with patch('snippets.base.views.cache') as cache:
            cache.get.return_value = 'other_etag'
            response = self.view.get(self.mock_request, **self.view_kwargs)

        cache.set.assert_called_with('client_key', 'etag', 90)
        eq_(response.status_code, 304)
        eq_(response['ETag'], 'etag')

    def test_get_request_doesnt_match_cache_or_response(self):
        """
        If the request's ETag doesn't match the cache or the response's
        ETag, send the full response.
        """
        self.view.generate_response = lambda *args: self.mock_response
        self.mock_request.META['HTTP_IF_NONE_MATCH'] = 'etag'
        self.mock_response['ETag'] = 'other_etag'

        with patch('snippets.base.views.cache') as cache:
            cache.get.return_value = 'other_etag'
            response = self.view.get(self.mock_request, **self.view_kwargs)

        ok_(not cache.set.called)
        eq_(response, self.mock_response)

    def test_get_request_no_etag(self):
        """If the request has no ETag, send the full response."""
        self.view.generate_response = lambda *args: self.mock_response
        self.mock_response['ETag'] = 'etag'

        with patch('snippets.base.views.cache') as cache:
            cache.get.return_value = 'etag'
            response = self.view.get(self.mock_request, **self.view_kwargs)

        ok_(not cache.set.called)
        eq_(response, self.mock_response)

    @patch('snippets.base.views.Client', wraps=Client)
    def test_client_construction(self, ClientMock):
        """
        Ensure that the client object is constructed correctly from the URL
        arguments.
        """
        params = ('4', 'Firefox', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        self.client.get('/{0}/'.format('/'.join(params)))

        ClientMock.assert_called_with(startpage_version='4',
                                      name='Firefox',
                                      version='23.0a1',
                                      appbuildid='20130510041606',
                                      build_target='Darwin_Universal-gcc3',
                                      locale='en-US',
                                      channel='nightly',
                                      os_version='Darwin 10.8.0',
                                      distribution='default',
                                      distribution_version='default_version')

    @override_settings(SNIPPET_HTTP_MAX_AGE=75)
    def test_cache_headers(self):
        """
        view_snippets should always have Cache-control set to
        'public, max-age={settings.SNIPPET_HTTP_MAX_AGE}' and only Vary
        on If-None-Match, even after middleware is executed.
        """
        params = ('4', 'Firefox', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/{0}/'.format('/'.join(params)))
        eq_(response['Cache-control'], 'public, max-age=75')
        eq_(response['Vary'], 'If-None-Match')


class JSONSnippetsTests(TestCase):
    def test_base(self):
        # Matching snippets.
        snippet_1 = JSONSnippetFactory.create(on_nightly=True, weight=66)

        # Matching but disabled snippet.
        JSONSnippetFactory.create(on_nightly=True, disabled=True)

        # Snippet that doesn't match.
        JSONSnippetFactory.create(on_nightly=False),

        params = ('4', 'Fennec', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/json/{0}/'.format('/'.join(params)))
        data = json.loads(response.content)
        eq_(len(data), 1)
        eq_(data[0]['id'], snippet_1.id)
        eq_(data[0]['weight'], 66)

    @patch('snippets.base.views.Client', wraps=Client)
    def test_client_construction(self, ClientMock):
        """
        Ensure that the client object is constructed correctly from the URL
        arguments.
        """
        params = ('4', 'Fennec', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        self.client.get('/json/{0}/'.format('/'.join(params)))

        ClientMock.assert_called_with(startpage_version='4',
                                      name='Fennec',
                                      version='23.0a1',
                                      appbuildid='20130510041606',
                                      build_target='Darwin_Universal-gcc3',
                                      locale='en-US',
                                      channel='nightly',
                                      os_version='Darwin 10.8.0',
                                      distribution='default',
                                      distribution_version='default_version')

    @override_settings(SNIPPET_HTTP_MAX_AGE=75)
    def test_cache_headers(self):
        """
        view_snippets should always have Cache-control set to
        'public, max-age={settings.SNIPPET_HTTP_MAX_AGE}' and no Vary header,
        even after middleware is executed.
        """
        params = ('1', 'Fennec', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/json/{0}/'.format('/'.join(params)))
        eq_(response['Cache-control'], 'public, max-age=75')
        ok_('Vary' not in response)

    def test_response(self):
        params = ('1', 'Fennec', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/json/{0}/'.format('/'.join(params)))
        eq_(response['Content-Type'], 'application/json')


class PreviewSnippetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@example.com', 'asdf')
        self.client.login(username='admin', password='asdf')

    def _preview_snippet(self, **kwargs):
        return self.client.post(reverse('base.preview'), kwargs)

    def test_invalid_template(self):
        """If template_id is missing or invalid, return a 400 Bad Request."""
        response = self._preview_snippet()
        eq_(response.status_code, 400)

        response = self._preview_snippet(template_id=99999999999999999999)
        eq_(response.status_code, 400)

        response = self._preview_snippet(template_id='')
        eq_(response.status_code, 400)

    def test_invalid_data(self):
        """If data is missing or invalid, return a 400 Bad Request."""
        template = SnippetTemplateFactory.create()
        response = self._preview_snippet(template_id=template.id)
        eq_(response.status_code, 400)

        response = self._preview_snippet(template_id=template.id,
                                         data='{invalid."json]')
        eq_(response.status_code, 400)

    def test_valid_args(self):
        """If template_id and data are both valid, return the preview page."""
        template = SnippetTemplateFactory.create()
        data = '{"a": "b"}'

        response = self._preview_snippet(template_id=template.id, data=data)
        eq_(response.status_code, 200)

        snippet = response.context['snippet']
        eq_(snippet.template, template)
        eq_(snippet.data, data)


class ShowSnippetTests(TestCase):
    def test_valid_snippet(self):
        """Test show of snippet."""
        snippet = SnippetFactory.create()
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': snippet.id}))
        eq_(response.status_code, 200)

    def test_invalid_snippet(self):
        """Test invalid snippet returns 404."""
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': '100'}))
        eq_(response.status_code, 404)

    def test_valid_disabled_snippet_unauthenticated(self):
        """Test disabled snippet returns 404 to unauthenticated users."""
        snippet = SnippetFactory.create(disabled=True)
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': snippet.id}))
        eq_(response.status_code, 404)

    def test_valid_disabled_snippet_authenticated(self):
        """Test disabled snippet returns 200 to authenticated users."""
        snippet = SnippetFactory.create(disabled=True)
        User.objects.create_superuser('admin', 'admin@example.com', 'asdf')
        self.client.login(username='admin', password='asdf')
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': snippet.id}))
        eq_(response.status_code, 200)


@patch('snippets.base.views.SNIPPETS_PER_PAGE', 1)
class IndexSnippetsTests(TestCase):
    def setUp(self):
        for i in range(10):
            SnippetFactory.create()

    def test_base(self):
        response = self.client.get(reverse('base.index'))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 1)

    def test_second_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=2))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 2)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_empty_page_number(self):
        """Test that empty page number returns the last page."""
        response = self.client.get(urlparams(reverse('base.index'), page=20))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 10)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_non_integer_page_number(self):
        """Test that a non integer page number returns the first page."""
        response = self.client.get(urlparams(reverse('base.index'), page='k'))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 1)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_filter(self):
        SnippetFactory.create(on_nightly=True)
        response = self.client.get(urlparams(reverse('base.index'), on_nightly=2))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].paginator.count, 1)

    def test_pagination_range_first_page(self):
        response = self.client.get(reverse('base.index'))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 1)
        eq_(pagination_range[-1], 3)
        eq_(len(pagination_range), 3)

    def test_pagination_range_last_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=10))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 8)
        eq_(pagination_range[-1], 10)
        eq_(len(pagination_range), 3)

    def test_pagination_range_middle_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=5))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 3)
        eq_(pagination_range[-1], 7)
        eq_(len(pagination_range), 5)
