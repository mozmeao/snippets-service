import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test.client import RequestFactory
from django.test.utils import override_settings

from funfactory.helpers import urlparams
from mock import patch
from nose.tools import eq_, ok_

import snippets.base.models
from snippets.base import views
from snippets.base.models import Client
from snippets.base.tests import (JSONSnippetFactory, SnippetFactory,
                                 SnippetTemplateFactory, TestCase)

snippets.base.models.CHANNELS = ('release', 'beta', 'aurora', 'nightly')
snippets.base.models.FIREFOX_STARTPAGE_VERSIONS = ('1', '2', '3', '4')


class FetchSnippetsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client_items = [
            ('startpage_version', '4'),
            ('name', 'Firefox'),
            ('version', '23.0a1'),
            ('appbuildid', '20130510041606'),
            ('build_target', 'Darwin_Universal-gcc3'),
            ('locale', 'en-US'),
            ('channel', 'nightly'),
            ('os_version', 'Darwin 10.8.0'),
            ('distribution', 'default'),
            ('distribution_version', 'default_version'),
        ]
        self.client_params = [v[1] for v in self.client_items]
        self.client_kwargs = dict(self.client_items)

    def test_base(self):
        # Matching snippets.
        snippet_1 = SnippetFactory.create(on_nightly=True)

        # Matching but disabled snippet.
        SnippetFactory.create(on_nightly=True, disabled=True)

        # Snippet that doesn't match.
        SnippetFactory.create(on_nightly=False),

        snippets_ok = [snippet_1]
        params = self.client_params
        response = self.client.get('/{0}/'.format('/'.join(params)))

        eq_(set(snippets_ok), set(response.context['snippets']))
        eq_(response.context['locale'], 'en-US')

    @patch('snippets.base.views.Client', wraps=Client)
    def test_client_construction(self, ClientMock):
        """
        Ensure that the client object is constructed correctly from the URL
        arguments.
        """
        params = self.client_params
        self.client.get('/{0}/'.format('/'.join(params)))

        ClientMock.assert_called_with(**self.client_kwargs)

    @override_settings(SNIPPET_HTTP_MAX_AGE=75)
    def test_cache_headers(self):
        """
        fetch_snippets should always have Cache-control set to
        'public, max-age={settings.SNIPPET_HTTP_MAX_AGE}' and a Vary
        header for 'If-None-Match'.
        """
        params = self.client_params
        response = self.client.get('/{0}/'.format('/'.join(params)))
        eq_(response['Cache-control'], 'public, max-age=75')
        eq_(response['Vary'], 'If-None-Match')

    def test_etag(self):
        """
        The response returned by fetch_snippets should have a ETag set
        to the sha256 hash of the response content.
        """
        request = self.factory.get('/')

        with patch.object(views, 'render') as mock_render:
            mock_render.return_value = HttpResponse('asdf')
            response = views.fetch_snippets(request, **self.client_kwargs)

            # sha256 of 'asdf'
            expected = 'f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b'
            eq_(response['ETag'], expected)


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
