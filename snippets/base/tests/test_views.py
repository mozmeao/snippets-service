import json
from collections import OrderedDict

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.test.utils import override_settings

from mock import patch

import snippets.base.models
from snippets.base import views
from snippets.base.models import Client
from snippets.base.templatetags.helpers import urlparams
from snippets.base.tests import (JSONSnippetFactory, SnippetFactory,
                                 SnippetTemplateFactory, TestCase)

snippets.base.models.CHANNELS = ('release', 'beta', 'aurora', 'nightly')
snippets.base.models.FIREFOX_STARTPAGE_VERSIONS = ('1', '2', '3', '4')


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
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], snippet_1.id)
        self.assertEqual(data[0]['weight'], 66)

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

    @override_settings(SNIPPET_BUNDLE_TIMEOUT=75)
    def test_cache_headers(self):
        """
        view_snippets should always have Cache-control set to
        'public, max-age={settings.SNIPPET_BUNDLE_TIMEOUT}'
        even after middleware is executed.
        """
        params = ('1', 'Fennec', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/json/{0}/'.format('/'.join(params)))
        cache_headers = [header.strip() for header in response['Cache-control'].split(',')]
        self.assertEqual(set(cache_headers), set(['public', 'max-age=75']))
        self.assertTrue('Vary' not in response)

    def test_response(self):
        params = ('1', 'Fennec', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/json/{0}/'.format('/'.join(params)))
        self.assertEqual(response['Content-Type'], 'application/json')


class PreviewSnippetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@example.com', 'asdf')
        self.client.login(username='admin', password='asdf')

    def _preview_snippet(self, **kwargs):
        return self.client.post(reverse('base.preview'), kwargs)

    def test_invalid_template(self):
        """If template_id is missing or invalid, return a 400 Bad Request."""
        response = self._preview_snippet()
        self.assertEqual(response.status_code, 400)

        response = self._preview_snippet(template_id=9999999999999)
        self.assertEqual(response.status_code, 400)

        response = self._preview_snippet(template_id='')
        self.assertEqual(response.status_code, 400)

    def test_invalid_data(self):
        """If data is missing or invalid, return a 400 Bad Request."""
        template = SnippetTemplateFactory.create()
        response = self._preview_snippet(template_id=template.id)
        self.assertEqual(response.status_code, 400)

        response = self._preview_snippet(template_id=template.id,
                                         data='{invalid."json]')
        self.assertEqual(response.status_code, 400)

    def test_valid_args(self):
        """If template_id and data are both valid, return the preview page."""
        template = SnippetTemplateFactory.create()
        data = '{"a": "b"}'
        response = self._preview_snippet(template_id=template.id, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['client'].startpage_version, '4')
        self.assertTemplateUsed(response, 'base/preview.jinja')

    def test_valid_args_activity_stream(self):
        """If template_id and data are both valid, return the preview page."""
        template = SnippetTemplateFactory.create()
        data = '{"a": "b"}'
        response = self._preview_snippet(template_id=template.id, activity_stream=True, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['client'].startpage_version, '5')
        self.assertTemplateUsed(response, 'base/preview_as.jinja')

    def test_skip_boilerplate(self):
        """If template_id and data are both valid, return the preview page."""
        template = SnippetTemplateFactory.create()
        data = '{"a": "b"}'
        response = self._preview_snippet(template_id=template.id, skip_boilerplate=True,
                                         activity_stream=True, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['client'].startpage_version, '5')
        self.assertTemplateUsed(response, 'base/preview_without_shell.jinja')


class ShowSnippetTests(TestCase):
    def test_valid_snippet(self):
        """Test show of snippet."""
        snippet = SnippetFactory.create()
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': snippet.id}))
        self.assertEqual(response.status_code, 200)

    def test_invalid_snippet(self):
        """Test invalid snippet returns 404."""
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': '100'}))
        self.assertEqual(response.status_code, 404)

    def test_valid_disabled_snippet_unauthenticated(self):
        """Test disabled snippet returns 404 to unauthenticated users."""
        snippet = SnippetFactory.create(disabled=True)
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': snippet.id}))
        self.assertEqual(response.status_code, 404)

    def test_valid_disabled_snippet_authenticated(self):
        """Test disabled snippet returns 200 to authenticated users."""
        snippet = SnippetFactory.create(disabled=True)
        User.objects.create_superuser('admin', 'admin@example.com', 'asdf')
        self.client.login(username='admin', password='asdf')
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': snippet.id}))
        self.assertEqual(response.status_code, 200)

    def test_uuid_snippet(self):
        snippet = SnippetFactory.create(disabled=True)
        response = self.client.get(reverse('base.show_uuid', kwargs={'snippet_id': snippet.uuid}))
        self.assertEqual(response.status_code, 200)


@override_settings(SNIPPETS_PER_PAGE=1)
class JSONIndexSnippetsTests(TestCase):
    def setUp(self):
        for i in range(10):
            JSONSnippetFactory.create()

    def test_base(self):
        response = self.client.get(reverse('base.index_json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].number, 1)

    def test_second_page(self):
        response = self.client.get(urlparams(reverse('base.index_json'), page=2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].number, 2)
        self.assertEqual(response.context['snippets'].paginator.num_pages, 10)

    def test_empty_page_number(self):
        """Test that empty page number returns the last page."""
        response = self.client.get(urlparams(reverse('base.index_json'), page=20))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].number, 10)
        self.assertEqual(response.context['snippets'].paginator.num_pages, 10)

    def test_non_integer_page_number(self):
        """Test that a non integer page number returns the first page."""
        response = self.client.get(urlparams(reverse('base.index_json'), page='k'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].number, 1)
        self.assertEqual(response.context['snippets'].paginator.num_pages, 10)

    def test_filter(self):
        JSONSnippetFactory.create(on_nightly=True)
        response = self.client.get(urlparams(reverse('base.index_json'), on_nightly=2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].paginator.count, 1)

    def test_pagination_range_first_page(self):
        response = self.client.get(reverse('base.index_json'))
        pagination_range = response.context['pagination_range']
        self.assertEqual(pagination_range[0], 1)
        self.assertEqual(pagination_range[-1], 3)
        self.assertEqual(len(pagination_range), 3)

    def test_pagination_range_last_page(self):
        response = self.client.get(urlparams(reverse('base.index_json'), page=10))
        pagination_range = response.context['pagination_range']
        self.assertEqual(pagination_range[0], 8)
        self.assertEqual(pagination_range[-1], 10)
        self.assertEqual(len(pagination_range), 3)

    def test_pagination_range_middle_page(self):
        response = self.client.get(urlparams(reverse('base.index_json'), page=5))
        pagination_range = response.context['pagination_range']
        self.assertEqual(pagination_range[0], 3)
        self.assertEqual(pagination_range[-1], 7)
        self.assertEqual(len(pagination_range), 5)


@override_settings(SNIPPETS_PER_PAGE=1)
class IndexSnippetsTests(TestCase):
    def setUp(self):
        for i in range(10):
            SnippetFactory.create()

    def test_base(self):
        response = self.client.get(reverse('base.index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].number, 1)

    def test_second_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].number, 2)
        self.assertEqual(response.context['snippets'].paginator.num_pages, 10)

    def test_empty_page_number(self):
        """Test that empty page number returns the last page."""
        response = self.client.get(urlparams(reverse('base.index'), page=20))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].number, 10)
        self.assertEqual(response.context['snippets'].paginator.num_pages, 10)

    def test_non_integer_page_number(self):
        """Test that a non integer page number returns the first page."""
        response = self.client.get(urlparams(reverse('base.index'), page='k'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].number, 1)
        self.assertEqual(response.context['snippets'].paginator.num_pages, 10)

    def test_filter(self):
        SnippetFactory.create(on_nightly=True)
        response = self.client.get(urlparams(reverse('base.index'), on_nightly=2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['snippets'].paginator.count, 1)

    def test_pagination_range_first_page(self):
        response = self.client.get(reverse('base.index'))
        pagination_range = response.context['pagination_range']
        self.assertEqual(pagination_range[0], 1)
        self.assertEqual(pagination_range[-1], 3)
        self.assertEqual(len(pagination_range), 3)

    def test_pagination_range_last_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=10))
        pagination_range = response.context['pagination_range']
        self.assertEqual(pagination_range[0], 8)
        self.assertEqual(pagination_range[-1], 10)
        self.assertEqual(len(pagination_range), 3)

    def test_pagination_range_middle_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=5))
        pagination_range = response.context['pagination_range']
        self.assertEqual(pagination_range[0], 3)
        self.assertEqual(pagination_range[-1], 7)
        self.assertEqual(len(pagination_range), 5)


class FetchSnippetsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.client_kwargs = OrderedDict([
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
        ])

    def test_normal(self):
        with patch.object(views, 'SnippetBundle') as SnippetBundle:
            bundle = SnippetBundle.return_value
            bundle.url = '/foo/bar'
            bundle.empty = False
            bundle.cached = True
            response = views.fetch_snippets(self.request, **self.client_kwargs)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/foo/bar')

        # Check for correct client.
        self.assertEqual(SnippetBundle.call_args[0][0].locale, 'en-US')

        # Do not generate bundle when not expired.
        self.assertTrue(not SnippetBundle.return_value.generate.called)

    def test_regenerate(self):
        """If the bundle has expired, re-generate it."""
        with patch.object(views, 'SnippetBundle') as SnippetBundle:
            bundle = SnippetBundle.return_value
            bundle.url = '/foo/bar'
            bundle.empty = False
            bundle.cached = False
            response = views.fetch_snippets(self.request, **self.client_kwargs)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/foo/bar')

        # Since the bundle was expired, ensure it was re-generated.
        self.assertTrue(SnippetBundle.return_value.generate.called)

    def test_empty(self):
        """If the bundle is empty return 204. """
        with patch.object(views, 'SnippetBundle') as SnippetBundle:
            bundle = SnippetBundle.return_value
            bundle.empty = True
            response = views.fetch_snippets(self.request, **self.client_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '')

    @patch('snippets.base.views.Client', wraps=Client)
    def test_client_construction(self, ClientMock):
        """
        Ensure that the client object is constructed correctly from the URL
        arguments.
        """
        self.client.get('/{0}/'.format('/'.join(self.client_kwargs.values())))

        ClientMock.assert_called_with(**self.client_kwargs)

    @override_settings(SNIPPET_BUNDLE_TIMEOUT=75)
    def test_cache_headers(self):
        """
        fetch_snippets should always have Cache-control set to
        'public, max-age={settings.SNIPPET_BUNDLE_TIMEOUT}'
        """
        params = self.client_kwargs.values()
        response = self.client.get('/{0}/'.format('/'.join(params)))
        cache_headers = [header.strip() for header in response['Cache-control'].split(',')]
        self.assertEqual(set(cache_headers), set(['public', 'max-age=75']))


class HealthzViewTests(TestCase):
    def test_ok(self):
        SnippetFactory.create()
        response = self.client.get(reverse('base.healthz'))
        self.assertEqual(response.status_code, 200)

    def test_fail(self):
        with self.assertRaises(AssertionError):
            self.client.get(reverse('base.healthz'))
