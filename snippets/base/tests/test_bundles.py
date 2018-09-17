import json

from django.conf import settings
from django.test.utils import override_settings

import brotli
from mock import ANY, Mock, patch

from snippets.base.bundles import ONE_DAY, SnippetBundle
from snippets.base.models import Client
from snippets.base.tests import SnippetFactory, TestCase


class SnippetBundleTests(TestCase):
    def setUp(self):
        self.snippet1, self.snippet2 = SnippetFactory.create_batch(2)

    def _client(self, **kwargs):
        client_kwargs = dict((key, '') for key in Client._fields)
        client_kwargs['startpage_version'] = 4
        client_kwargs.update(kwargs)
        return Client(**client_kwargs)

    def test_key_snippets(self):
        """
        bundle.key must be different between bundles if they have
        different snippets.
        """
        client = self._client()
        bundle1 = SnippetBundle(client)
        bundle1.snippets = [self.snippet1, self.snippet2]
        bundle2 = SnippetBundle(client)
        bundle2.snippets = [self.snippet2]

        self.assertNotEqual(bundle1.key, bundle2.key)

    def test_key_funny_characters(self):
        """
        bundle.key should generate even when client contains strange unicode
        characters
        """
        client = self._client(channel='release-cck- \xe2\x80\x9cubuntu\xe2\x80\x9d')
        SnippetBundle(client).key

    def test_key_startpage_version(self):
        """
        bundle.key must be different between bundles if they have
        different startpage versions.
        """
        client1 = self._client(startpage_version=1)
        client2 = self._client(startpage_version=2)
        bundle1 = SnippetBundle(client1)
        bundle2 = SnippetBundle(client2)

        self.assertNotEqual(bundle1.key, bundle2.key)

    def test_key_locale(self):
        """
        bundle.key must be different between bundles if they have
        different locales.
        """
        client1 = self._client(locale='en-US')
        client2 = self._client(locale='fr')
        bundle1 = SnippetBundle(client1)
        bundle2 = SnippetBundle(client2)

        self.assertNotEqual(bundle1.key, bundle2.key)

    def test_key_equal(self):
        client1 = self._client(locale='en-US', startpage_version=4)
        client2 = self._client(locale='en-US', startpage_version=4)
        bundle1 = SnippetBundle(client1)
        bundle1.snippets = [self.snippet1, self.snippet2]
        bundle2 = SnippetBundle(client2)
        bundle2.snippets = [self.snippet1, self.snippet2]

        self.assertEqual(bundle1.key, bundle2.key)

    def test_key_snippet_modified(self):
        client1 = self._client(locale='en-US', startpage_version=4)
        bundle = SnippetBundle(client1)
        bundle.snippets = [self.snippet1]
        key_1 = bundle.key

        # save snippet, touch modified
        self.snippet1.save()
        bundle = SnippetBundle(client1)
        bundle.snippets = [self.snippet1]
        key_2 = bundle.key
        self.assertNotEqual(key_1, key_2)

    def test_key_template_modified(self):
        client1 = self._client(locale='en-US', startpage_version=4)
        bundle = SnippetBundle(client1)
        bundle.snippets = [self.snippet1]
        key_1 = bundle.key

        # save template, touch modified
        self.snippet1.template.save()
        bundle = SnippetBundle(client1)
        bundle.snippets = [self.snippet1]
        key_2 = bundle.key
        self.assertNotEqual(key_1, key_2)

    def test_key_current_firefox_version(self):
        client1 = self._client(locale='en-US', startpage_version=4)
        bundle = SnippetBundle(client1)
        bundle.snippets = [self.snippet1]
        key_1 = bundle.key

        with patch('snippets.base.util.current_firefox_major_version') as cfmv:
            cfmv.return_value = 'xx'
            bundle = SnippetBundle(client1)
            bundle.snippets = [self.snippet1]
            key_2 = bundle.key
        self.assertNotEqual(key_1, key_2)

    @override_settings(BUNDLE_BROTLI_COMPRESS=True)
    def test_generate(self):
        """
        bundle.generate should render the snippets, save them to the
        filesystem, and mark the bundle as not-expired in the cache.
        """
        bundle = SnippetBundle(self._client(startpage_version=4, locale='fr'))
        bundle.storage = Mock()
        bundle.snippets = [self.snippet1, self.snippet2]

        with patch('snippets.base.bundles.cache') as cache:
            with patch('snippets.base.bundles.render_to_string') as render_to_string:
                with patch('snippets.base.bundles.default_storage') as default_storage:
                    with self.settings(SNIPPET_BUNDLE_TIMEOUT=10):
                        with patch('snippets.base.bundles.brotli', wraps=brotli) as brotli_mock:
                            with patch('snippets.base.util.current_firefox_major_version') as cfmv:
                                cfmv.return_value = '45'
                                render_to_string.return_value = 'rendered snippet'
                                bundle.generate()

        render_to_string.assert_called_with('base/fetch_snippets.jinja', {
            'snippet_ids': [s.id for s in [self.snippet1, self.snippet2]],
            'snippets_json': json.dumps([s.to_dict() for s in [self.snippet1, self.snippet2]]),
            'client': bundle.client,
            'locale': 'fr',
            'settings': settings,
            'current_firefox_major_version': '45',
        })
        default_storage.save.assert_called_with(bundle.filename, ANY)
        cache.set.assert_called_with(bundle.cache_key, True, ONE_DAY)

        # Brotli must not be used in non-AS requests.
        self.assertFalse(brotli_mock.called)

        # Check content of saved file.
        content_file = default_storage.save.call_args[0][1]
        self.assertEqual(content_file.read(), b'rendered snippet')

    @override_settings(BUNDLE_BROTLI_COMPRESS=False)
    def test_generate_activity_stream(self):
        """
        bundle.generate should render the snippets, save them to the
        filesystem, and mark the bundle as not-expired in the cache for
        activity stream!
        """
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
        bundle.storage = Mock()
        bundle.snippets = [self.snippet1, self.snippet2]

        with patch('snippets.base.bundles.cache') as cache:
            with patch('snippets.base.bundles.render_to_string') as render_to_string:
                with patch('snippets.base.bundles.default_storage') as default_storage:
                    with self.settings(SNIPPET_BUNDLE_TIMEOUT=10):
                        with patch('snippets.base.util.current_firefox_major_version') as cfmv:
                            cfmv.return_value = '45'
                            render_to_string.return_value = 'rendered snippet'
                            bundle.generate()

        render_to_string.assert_called_with('base/fetch_snippets_as.jinja', {
            'snippet_ids': [s.id for s in [self.snippet1, self.snippet2]],
            'snippets_json': json.dumps([s.to_dict() for s in [self.snippet1, self.snippet2]]),
            'client': bundle.client,
            'locale': 'fr',
            'settings': settings,
            'current_firefox_major_version': '45',
        })
        default_storage.save.assert_called_with(bundle.filename, ANY)
        cache.set.assert_called_with(bundle.cache_key, True, ONE_DAY)

        # Check content of saved file.
        content_file = default_storage.save.call_args[0][1]
        self.assertEqual(content_file.read(), b'rendered snippet')

    @override_settings(BUNDLE_BROTLI_COMPRESS=False)
    def test_generate_activity_stream_router(self):
        """
        bundle.generate should render the snippets, save them to the
        filesystem, and mark the bundle as not-expired in the cache for
        activity stream!
        """
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=6))
        bundle.storage = Mock()
        bundle.snippets = [self.snippet1, self.snippet2]
        self.snippet1.render_to_as_router = Mock()
        self.snippet1.render_to_as_router.return_value = 'snippet1'
        self.snippet2.render_to_as_router = Mock()
        self.snippet2.render_to_as_router.return_value = 'snippet2'

        with patch('snippets.base.bundles.datetime') as datetime:
            with patch('snippets.base.bundles.cache') as cache:
                with patch('snippets.base.bundles.default_storage') as default_storage:
                    datetime.utcnow.return_value.isoformat.return_value = 'now'
                    bundle.generate()

        self.assertTrue(bundle.filename.endswith('.json'))
        default_storage.save.assert_called_with(bundle.filename, ANY)
        cache.set.assert_called_with(bundle.cache_key, True, ONE_DAY)

        # Check content of saved file.
        content_file = default_storage.save.call_args[0][1]
        content_json = json.load(content_file)
        self.assertEqual(content_json['messages'], ['snippet1', 'snippet2'])
        self.assertEqual(content_json['metadata']['generated_at'], 'now')

    @override_settings(BUNDLE_BROTLI_COMPRESS=True)
    def test_generate_brotli(self):
        """
        bundle.generate should render the snippets, save them to the
        filesystem, and mark the bundle as not-expired in the cache for
        activity stream!
        """
        def _test(client):
            bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
            bundle.storage = Mock()
            bundle.snippets = [self.snippet1, self.snippet2]

            with patch('snippets.base.bundles.cache') as cache:
                with patch('snippets.base.bundles.render_to_string') as render_to_string:
                    with patch('snippets.base.bundles.default_storage') as default_storage:
                        with patch('snippets.base.bundles.brotli', wraps=brotli) as brotli_mock:
                            render_to_string.return_value = 'rendered snippet'
                            bundle.generate()

            brotli_mock.compress.assert_called_with(b'rendered snippet')
            default_storage.save.assert_called_with(bundle.filename, ANY)
            cache.set.assert_called_with(bundle.cache_key, True, ONE_DAY)

            # Check content of saved file.
            content_file = default_storage.save.call_args[0][1]
            self.assertEqual(content_file.content_encoding, 'br')
            self.assertEqual(content_file.read(), b'\x8b\x07\x80rendered snippet\x03')
        _test(self._client(locale='fr', startpage_version=5))
        _test(self._client(locale='fr', startpage_version=6))

    def test_cached_local(self):
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
        with patch('snippets.base.bundles.cache') as cache:
            cache.get.return_value = True
            self.assertTrue(bundle.cached)

    def test_cached_remote(self):
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
        with patch('snippets.base.bundles.cache') as cache:
            cache.get.return_value = False
            with patch('snippets.base.bundles.default_storage') as default_storage:
                default_storage.exists.return_value = True
                self.assertTrue(bundle.cached)
                cache.set.assert_called_with(bundle.cache_key, True, ONE_DAY)

    def test_not_cached(self):
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
        with patch('snippets.base.bundles.cache') as cache:
            cache.get.return_value = False
            with patch('snippets.base.bundles.default_storage') as default_storage:
                default_storage.exists.return_value = False
                self.assertFalse(bundle.cached)

    def test_empty(self):
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
        self.assertTrue(bundle.empty)

        bundle.snippets = [self.snippet1, self.snippet2]
        self.assertFalse(bundle.empty)
