import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.test.client import RequestFactory
from django.test.utils import override_settings

from funfactory.helpers import urlparams
from mock import patch
from nose.tools import eq_, ok_
from waffle.models import Flag

import snippets.base.models
from snippets.base import views
from snippets.base.models import Client
from snippets.base.tests import (JSONSnippetFactory, SnippetFactory,
                                 SnippetTemplateFactory, TestCase)

snippets.base.models.CHANNELS = ('release', 'beta', 'aurora', 'nightly')
snippets.base.models.FIREFOX_STARTPAGE_VERSIONS = ('1', '2', '3', '4')


class FetchRenderSnippetsTests(TestCase):
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

        # Ensure the render-immediately view is used.
        Flag.objects.create(name='serve_pregenerated_snippets', everyone=False)

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

        snippets_json = json.dumps([{
            'id': snippet.id,
            'code': snippet.render(),
            'country': snippet.country,
            'weight': snippet.weight,
        } for snippet in snippets_ok])

        eq_(set(snippets_json), set(response.context['snippets_json']))
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
class JSONIndexSnippetsTests(TestCase):
    def setUp(self):
        for i in range(10):
            JSONSnippetFactory.create()

    def test_base(self):
        response = self.client.get(reverse('base.index_json'))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 1)

    def test_second_page(self):
        response = self.client.get(urlparams(reverse('base.index_json'), page=2))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 2)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_empty_page_number(self):
        """Test that empty page number returns the last page."""
        response = self.client.get(urlparams(reverse('base.index_json'), page=20))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 10)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_non_integer_page_number(self):
        """Test that a non integer page number returns the first page."""
        response = self.client.get(urlparams(reverse('base.index_json'), page='k'))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 1)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_filter(self):
        JSONSnippetFactory.create(on_nightly=True)
        response = self.client.get(urlparams(reverse('base.index_json'), on_nightly=2))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].paginator.count, 1)

    def test_pagination_range_first_page(self):
        response = self.client.get(reverse('base.index_json'))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 1)
        eq_(pagination_range[-1], 3)
        eq_(len(pagination_range), 3)

    def test_pagination_range_last_page(self):
        response = self.client.get(urlparams(reverse('base.index_json'), page=10))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 8)
        eq_(pagination_range[-1], 10)
        eq_(len(pagination_range), 3)

    def test_pagination_range_middle_page(self):
        response = self.client.get(urlparams(reverse('base.index_json'), page=5))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 3)
        eq_(pagination_range[-1], 7)
        eq_(len(pagination_range), 5)


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


class FetchPregeneratedSnippetsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.client_kwargs = {
            'startpage_version': '4',
            'name': 'Firefox',
            'version': '23.0a1',
            'appbuildid': '20130510041606',
            'build_target': 'Darwin_Universal-gcc3',
            'locale': 'en-US',
            'channel': 'nightly',
            'os_version': 'Darwin 10.8.0',
            'distribution': 'default',
            'distribution_version': 'default_version',
        }

    def test_normal(self):
        with patch.object(views, 'SnippetBundle') as SnippetBundle:
            bundle = SnippetBundle.return_value
            bundle.url = '/foo/bar'
            bundle.expired = False
            response = views.fetch_pregenerated_snippets(self.request, **self.client_kwargs)

        eq_(response.status_code, 302)
        eq_(response['Location'], '/foo/bar')

        # Check for correct client.
        eq_(SnippetBundle.call_args[0][0].locale, 'en-US')

        # Do not generate bundle when not expired.
        ok_(not SnippetBundle.return_value.generate.called)

    def test_regenerate(self):
        """If the bundle has expired, re-generate it."""
        with patch.object(views, 'SnippetBundle') as SnippetBundle:
            bundle = SnippetBundle.return_value
            bundle.url = '/foo/bar'
            bundle.expired = True
            response = views.fetch_pregenerated_snippets(self.request, **self.client_kwargs)

        eq_(response.status_code, 302)
        eq_(response['Location'], '/foo/bar')

        # Since the bundle was expired, ensure it was re-generated.
        ok_(SnippetBundle.return_value.generate.called)


class FetchSnippetsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

    def test_flag_off(self):
        Flag.objects.create(name='serve_pregenerated_snippets', everyone=False)

        with patch.object(views, 'fetch_render_snippets') as fetch_render_snippets:
            eq_(views.fetch_snippets(self.request, foo='bar'), fetch_render_snippets.return_value)
            fetch_render_snippets.assert_called_with(self.request, foo='bar')

    def test_flag_on(self):
        Flag.objects.create(name='serve_pregenerated_snippets', everyone=True)

        with patch.object(views, 'fetch_pregenerated_snippets') as fetch_pregenerated_snippets:
            eq_(views.fetch_snippets(self.request, foo='bar'),
                fetch_pregenerated_snippets.return_value)
            fetch_pregenerated_snippets.assert_called_with(self.request, foo='bar')


class ActiveSnippetsViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

    def test_base(self):
        snippets = SnippetFactory.create_batch(2)
        jsonsnippets = JSONSnippetFactory.create_batch(2)
        SnippetFactory.create(disabled=True)
        JSONSnippetFactory.create(disabled=True)
        response = views.ActiveSnippetsView.as_view()(self.request)
        eq_(response.get('content-type'), 'application/json')
        data = json.loads(response.content)
        eq_(set([snippets[0].id, snippets[1].id,
                 jsonsnippets[0].id, jsonsnippets[1].id]),
            set([x['id'] for x in data]))
