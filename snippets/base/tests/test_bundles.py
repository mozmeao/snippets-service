import json

from unittest.mock import ANY, DEFAULT, Mock, patch

from django.test.utils import override_settings

from snippets.base.bundles import ONE_DAY, ASRSnippetBundle
from snippets.base.models import Client
from snippets.base.tests import JobFactory, TestCase


class ASRSnippetBundleTests(TestCase):
    def setUp(self):
        self.job1, self.job2 = JobFactory.create_batch(2)

    def _client(self, **kwargs):
        client_kwargs = dict((key, '') for key in Client._fields)
        client_kwargs['startpage_version'] = 4
        client_kwargs.update(kwargs)
        return Client(**client_kwargs)

    def test_empty(self):
        client = self._client(locale='en-US')
        bundle = ASRSnippetBundle(client)
        self.assertFalse(bundle.empty)

        client = self._client(locale='it')
        bundle = ASRSnippetBundle(client)
        self.assertTrue(bundle.empty)

    def test_key_jobs(self):
        """
        bundle.key must be different between bundles if they have
        different Jobs.
        """
        client = self._client()
        bundle1 = ASRSnippetBundle(client)
        bundle1.jobs = [self.job1, self.job2]
        bundle2 = ASRSnippetBundle(client)
        bundle2.jobs = [self.job2]

        self.assertNotEqual(bundle1.key, bundle2.key)

    def test_key_funny_characters(self):
        """
        bundle.key should generate even when client contains strange unicode
        characters
        """
        client = self._client(channel='release-cck- \xe2\x80\x9cubuntu\xe2\x80\x9d')
        ASRSnippetBundle(client).key

    def test_key_startpage_version(self):
        """
        bundle.key must be different between bundles if they have
        different startpage versions.
        """
        client1 = self._client(startpage_version=1)
        client2 = self._client(startpage_version=2)
        bundle1 = ASRSnippetBundle(client1)
        bundle2 = ASRSnippetBundle(client2)

        self.assertNotEqual(bundle1.key, bundle2.key)

    def test_key_locale(self):
        """
        bundle.key must be different between bundles if they have
        different locales.
        """
        client1 = self._client(locale='en-US')
        client2 = self._client(locale='fr')
        bundle1 = ASRSnippetBundle(client1)
        bundle2 = ASRSnippetBundle(client2)

        self.assertNotEqual(bundle1.key, bundle2.key)

    def test_key_equal(self):
        client1 = self._client(locale='en-US', startpage_version=4)
        client2 = self._client(locale='en-US', startpage_version=4)
        bundle1 = ASRSnippetBundle(client1)
        bundle1.jobs = [self.job1, self.job2]
        bundle2 = ASRSnippetBundle(client2)
        bundle2.jobs = [self.job1, self.job2]

        self.assertEqual(bundle1.key, bundle2.key)

    def test_key_snippet_modified(self):
        client1 = self._client(locale='en-US', startpage_version=4)
        bundle = ASRSnippetBundle(client1)
        bundle.jobs = [self.job1]
        key_1 = bundle.key

        # save snippet, touch modified
        self.job1.snippet.save()
        bundle = ASRSnippetBundle(client1)
        bundle.jobs = [self.job1]
        key_2 = bundle.key
        self.assertNotEqual(key_1, key_2)

    @override_settings(BUNDLE_BROTLI_COMPRESS=False)
    def test_generate(self):
        """
        bundle.generate should render the snippets, save them to the
        filesystem, and mark the bundle as not-expired in the cache for
        activity stream router!
        """
        bundle = ASRSnippetBundle(self._client(locale='fr', startpage_version=6))
        bundle.storage = Mock()
        bundle.jobs = [self.job1, self.job2]
        self.job1.render = Mock()
        self.job1.render.return_value = 'job1'
        self.job2.render = Mock()
        self.job2.render.return_value = 'job2'

        datetime_mock = Mock()
        datetime_mock.utcnow.return_value.isoformat.return_value = 'now'
        with patch.multiple('snippets.base.bundles',
                            datetime=datetime_mock,
                            cache=DEFAULT, default_storage=DEFAULT) as mocks:
            bundle.generate()

        self.assertTrue(bundle.filename.endswith('.json'))
        mocks['default_storage'].save.assert_called_with(bundle.filename, ANY)
        mocks['cache'].set.assert_called_with(bundle.cache_key, True, ONE_DAY)

        # Check content of saved file.
        content_file = mocks['default_storage'].save.call_args[0][1]
        content_json = json.load(content_file)
        self.assertEqual(content_json['messages'], ['job1', 'job2'])
        self.assertEqual(content_json['metadata']['generated_at'], 'now')
