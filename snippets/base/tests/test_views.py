from collections import OrderedDict
from unittest.mock import DEFAULT, patch

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse


import snippets.base.models
from snippets.base import views
from snippets.base.models import Client
from snippets.base.tests import (ASRSnippetFactory, SnippetFactory,
                                 SnippetTemplateFactory, TestCase)

snippets.base.models.CHANNELS = ('release', 'beta', 'aurora', 'nightly')


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
        self.assertEqual(response.context['client'].startpage_version, 4)
        self.assertTemplateUsed(response, 'base/preview.jinja')

    def test_valid_args_activity_stream(self):
        """If template_id and data are both valid, return the preview page."""
        template = SnippetTemplateFactory.create()
        data = '{"a": "b"}'
        response = self._preview_snippet(template_id=template.id, activity_stream=True, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['client'].startpage_version, 5)
        self.assertTemplateUsed(response, 'base/preview_as.jinja')

    def test_skip_boilerplate(self):
        """If template_id and data are both valid, return the preview page."""
        template = SnippetTemplateFactory.create()
        data = '{"a": "b"}'
        response = self._preview_snippet(template_id=template.id, skip_boilerplate=True,
                                         activity_stream=True, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['client'].startpage_version, 5)
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
        snippet = SnippetFactory.create(published=False)
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': snippet.id}))
        self.assertEqual(response.status_code, 404)

    def test_valid_disabled_snippet_authenticated(self):
        """Test disabled snippet returns 200 to authenticated users."""
        snippet = SnippetFactory.create(published=False)
        User.objects.create_superuser('admin', 'admin@example.com', 'asdf')
        self.client.login(username='admin', password='asdf')
        response = self.client.get(reverse('base.show', kwargs={'snippet_id': snippet.id}))
        self.assertEqual(response.status_code, 200)

    def test_uuid_snippet(self):
        snippet = SnippetFactory.create(published=False)
        response = self.client.get(reverse('base.show_uuid', kwargs={'snippet_id': snippet.uuid}))
        self.assertEqual(response.status_code, 200)


class FetchSnippetsTests(TestCase):
    def test_base(self):
        asrclient_kwargs = OrderedDict([
            ('startpage_version', 6),
            ('name', 'Firefox'),
            ('version', '64.0'),
            ('appbuildid', '20190110041606'),
            ('build_target', 'Darwin_Universal-gcc3'),
            ('locale', 'en-US'),
            ('channel', 'release'),
            ('os_version', 'Darwin 10.8.0'),
            ('distribution', 'default'),
            ('distribution_version', 'default_version'),
        ])
        request = RequestFactory().get('/')

        with patch.multiple('snippets.base.views',
                            fetch_snippet_pregen_bundle=DEFAULT,
                            fetch_snippet_bundle=DEFAULT) as patches:
            with override_settings(USE_PREGEN_BUNDLES=False):
                views.fetch_snippets(request, **asrclient_kwargs)
                self.assertFalse(patches['fetch_snippet_pregen_bundle'].called)
                self.assertTrue(patches['fetch_snippet_bundle'].called)

        with patch.multiple('snippets.base.views',
                            fetch_snippet_pregen_bundle=DEFAULT,
                            fetch_snippet_bundle=DEFAULT) as patches:
            with override_settings(USE_PREGEN_BUNDLES=True):
                views.fetch_snippets(request, **asrclient_kwargs)
                self.assertTrue(patches['fetch_snippet_pregen_bundle'].called)
                self.assertFalse(patches['fetch_snippet_bundle'].called)

        # Pregen Enabled but old client.
        with patch.multiple('snippets.base.views',
                            fetch_snippet_pregen_bundle=DEFAULT,
                            fetch_snippet_bundle=DEFAULT) as patches:
            with override_settings(USE_PREGEN_BUNDLES=True):
                asrclient_kwargs['startpage_version'] = 5
                views.fetch_snippets(request, **asrclient_kwargs)
                self.assertFalse(patches['fetch_snippet_pregen_bundle'].called)
                self.assertTrue(patches['fetch_snippet_bundle'].called)


@override_settings(SITE_URL='http://example.org',
                   MEDIA_BUNDLES_PREGEN_ROOT='/bundles/pregen/')
class FetchSnippetPregenBundleTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.asrclient_kwargs = OrderedDict([
            ('startpage_version', 6),
            ('name', 'Firefox'),
            ('version', '70.0'),
            ('appbuildid', '20190110041606'),
            ('build_target', 'Darwin_Universal-gcc3'),
            ('locale', 'el-GR'),
            ('channel', 'default'),
            ('os_version', 'Darwin 10.8.0'),
            ('distribution', 'other-than-default'),
            ('distribution_version', 'default_version'),
        ])

    def test_base(self):
        response = views.fetch_snippet_pregen_bundle(self.request, **self.asrclient_kwargs)
        expected_url = (
            'http://example.org/media/bundles/pregen/Firefox/release/el-gr/other-than-default.json'
        )
        self.assertEqual(response.url, expected_url)

    @override_settings(CDN_URL='https://cdn.com')
    def test_cdn(self):
        response = views.fetch_snippet_pregen_bundle(self.request, **self.asrclient_kwargs)
        expected_url = (
            'https://cdn.com/media/bundles/pregen/Firefox/release/el-gr/other-than-default.json'
        )
        self.assertEqual(response.url, expected_url)

    def test_complicated_channel(self):
        asrclient_kwargs = self.asrclient_kwargs.copy()
        asrclient_kwargs['channel'] = 'nightly-cck-δφια'
        response = views.fetch_snippet_pregen_bundle(self.request, **asrclient_kwargs)
        expected_url = (
            'http://example.org/media/bundles/pregen/Firefox/nightly/el-gr/other-than-default.json'
        )
        self.assertEqual(response.url, expected_url)

    def test_other_product(self):
        asrclient_kwargs = self.asrclient_kwargs.copy()
        asrclient_kwargs['name'] = 'Edge'
        response = views.fetch_snippet_pregen_bundle(self.request, **asrclient_kwargs)
        expected_url = (
            'http://example.org/media/bundles/pregen/Firefox/release/el-gr/other-than-default.json'
        )
        self.assertEqual(response.url, expected_url)


class FetchSnippetBundleTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.client_kwargs = OrderedDict([
            ('startpage_version', 4),
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
        self.asrclient_kwargs = OrderedDict([
            ('startpage_version', 6),
            ('name', 'Firefox'),
            ('version', '64.0'),
            ('appbuildid', '20190110041606'),
            ('build_target', 'Darwin_Universal-gcc3'),
            ('locale', 'en-US'),
            ('channel', 'release'),
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
            response = views.fetch_snippet_bundle(self.request, **self.client_kwargs)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/foo/bar')

        # Check for correct client.
        self.assertEqual(SnippetBundle.call_args[0][0].locale, 'en-US')

        # Do not generate bundle when not expired.
        self.assertTrue(not SnippetBundle.return_value.generate.called)

    def test_normal_asr(self):
        with patch.object(views, 'ASRSnippetBundle') as ASRSnippetBundle:
            bundle = ASRSnippetBundle.return_value
            bundle.url = '/foo/bar'
            bundle.empty = False
            bundle.cached = True
            response = views.fetch_snippet_bundle(self.request, **self.asrclient_kwargs)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/foo/bar')

        # Check for correct client.
        self.assertEqual(ASRSnippetBundle.call_args[0][0].locale, 'en-US')

        # Do not generate bundle when not expired.
        self.assertTrue(not ASRSnippetBundle.return_value.generate.called)

    def test_regenerate(self):
        """If the bundle has expired, re-generate it."""
        with patch.object(views, 'SnippetBundle') as SnippetBundle:
            bundle = SnippetBundle.return_value
            bundle.url = '/foo/bar'
            bundle.empty = False
            bundle.cached = False
            response = views.fetch_snippet_bundle(self.request, **self.client_kwargs)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/foo/bar')

        # Since the bundle was expired, ensure it was re-generated.
        self.assertTrue(SnippetBundle.return_value.generate.called)

    def test_empty(self):
        """If the bundle is empty return 200 and empty string."""
        with patch.object(views, 'SnippetBundle') as SnippetBundle:
            bundle = SnippetBundle.return_value
            bundle.empty = True
            response = views.fetch_snippet_bundle(self.request, **self.client_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_empty_asr(self):
        """If the bundle is empty return 200 and valid JSON for ASR."""
        with patch.object(views, 'ASRSnippetBundle') as ASRSnippetBundle:
            bundle = ASRSnippetBundle.return_value
            bundle.empty = True
            response = views.fetch_snippet_bundle(self.request, **self.asrclient_kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'{}')
        self.assertEqual(response['content-type'], 'application/json')

    @patch('snippets.base.views.Client', wraps=Client)
    def test_client_construction(self, ClientMock):
        """
        Ensure that the client object is constructed correctly from the URL
        arguments.
        """
        params = self.client_kwargs.values()
        self.client.get('/{0}/'.format('/'.join(['{}'.format(x) for x in params])))
        ClientMock.assert_called_with(**self.client_kwargs)

    @override_settings(SNIPPET_BUNDLE_TIMEOUT=75)
    def test_cache_headers(self):
        """
        fetch_snippets should always have Cache-control set to
        'public, max-age={settings.SNIPPET_BUNDLE_TIMEOUT}'
        """
        params = self.client_kwargs.values()
        response = self.client.get('/{0}/'.format('/'.join(['{}'.format(x) for x in params])))
        cache_headers = [header.strip() for header in response['Cache-control'].split(',')]
        self.assertEqual(set(cache_headers), set(['public', 'max-age=75']))


class PreviewASRSnippetTests(TestCase):
    def test_base(self):
        snippet = ASRSnippetFactory()
        url = reverse('asr-preview', kwargs={'uuid': snippet.uuid})
        with patch('snippets.base.views.ASRSnippet.render') as render_mock:
            render_mock.return_value = 'foo'
            response = self.client.get(url)
        render_mock.assert_called_with(preview=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_404(self):
        url = reverse('asr-preview', kwargs={'uuid': 'foo'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        url = reverse('asr-preview', kwargs={'uuid': '804c062b-844f-4f33-80d3-9915514a14b4'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
