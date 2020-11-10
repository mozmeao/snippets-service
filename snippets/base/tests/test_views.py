from unittest.mock import DEFAULT, patch

from django.http import Http404
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse

import snippets.base.models
from snippets.base import views
from snippets.base.tests import ASRSnippetFactory, TestCase

snippets.base.models.CHANNELS = ('release', 'beta', 'aurora', 'nightly')


class FetchSnippetsTests(TestCase):
    def test_base(self):
        asrclient_kwargs = dict([
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
                            fetch_snippet_pregen_bundle=DEFAULT) as patches:
            views.fetch_snippets(request, **asrclient_kwargs)
            self.assertTrue(patches['fetch_snippet_pregen_bundle'].called)

        # Old client.
        with patch.multiple('snippets.base.views',
                            fetch_snippet_pregen_bundle=DEFAULT) as patches:
            asrclient_kwargs['startpage_version'] = 5
            self.assertRaises(Http404, views.fetch_snippets, request, **asrclient_kwargs)
            self.assertFalse(patches['fetch_snippet_pregen_bundle'].called)


@override_settings(SITE_URL='http://example.org',
                   MEDIA_BUNDLES_PREGEN_ROOT='/bundles/pregen/',
                   INSTANT_BUNDLE_GENERATION=False)
class FetchSnippetPregenBundleTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.asrclient_kwargs = dict([
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
            'http://example.org/media/bundles/pregen/Firefox/release/el-gr/default.json'
        )
        self.assertEqual(response.url, expected_url)

    @override_settings(CDN_URL='https://cdn.com')
    def test_cdn(self):
        response = views.fetch_snippet_pregen_bundle(self.request, **self.asrclient_kwargs)
        expected_url = (
            'https://cdn.com/media/bundles/pregen/Firefox/release/el-gr/default.json'
        )
        self.assertEqual(response.url, expected_url)

    def test_complicated_channel(self):
        asrclient_kwargs = self.asrclient_kwargs.copy()
        asrclient_kwargs['channel'] = 'nightly-cck-δφια'
        response = views.fetch_snippet_pregen_bundle(self.request, **asrclient_kwargs)
        expected_url = (
            'http://example.org/media/bundles/pregen/Firefox/nightly/el-gr/default.json'
        )
        self.assertEqual(response.url, expected_url)

    def test_other_product(self):
        asrclient_kwargs = self.asrclient_kwargs.copy()
        asrclient_kwargs['name'] = 'Edge'
        response = views.fetch_snippet_pregen_bundle(self.request, **asrclient_kwargs)
        expected_url = (
            'http://example.org/media/bundles/pregen/Firefox/release/el-gr/default.json'
        )
        self.assertEqual(response.url, expected_url)

    def test_distribution(self):
        asrclient_kwargs = self.asrclient_kwargs.copy()
        asrclient_kwargs['distribution'] = 'experiment-foo-bar'
        response = views.fetch_snippet_pregen_bundle(self.request, **asrclient_kwargs)
        expected_url = (
            'http://example.org/media/bundles/pregen/Firefox/release/el-gr/foo-bar.json'
        )
        self.assertEqual(response.url, expected_url)

    @override_settings(INSTANT_BUNDLE_GENERATION=True)
    def test_instant_bundle_generation(self):
        with patch('snippets.base.views.generate_bundles') as generate_bundles_mock:
            generate_bundles_mock.return_value = 'foo=bar'
            response = views.fetch_snippet_pregen_bundle(self.request, **self.asrclient_kwargs)
        generate_bundles_mock.assert_called_with(
            limit_to_channel='release',
            limit_to_locale='el-gr',
            limit_to_distribution_bundle='default',
            save_to_disk=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response.content, b'foo=bar')


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
