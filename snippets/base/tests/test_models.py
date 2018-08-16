import json
from datetime import datetime

from django.conf import settings
from django.test.utils import override_settings

import brotli
from jinja2 import Markup
from mock import ANY, MagicMock, Mock, patch
from pyquery import PyQuery as pq

from snippets.base.models import (ONE_DAY, Client, SnippetBundle, UploadedFile,
                                  _generate_filename)
from snippets.base.tests import (ClientMatchRuleFactory,
                                 JSONSnippetFactory,
                                 SearchProviderFactory,
                                 SnippetFactory,
                                 SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory,
                                 TestCase,
                                 UploadedFileFactory)


class DuplicateSnippetMixInTests(TestCase):
    def _dup_test(self, snippet):
        snippet.client_match_rules.add(*ClientMatchRuleFactory.create_batch(3))
        snippet_copy = snippet.duplicate()
        self.assertEqual(snippet_copy.published, False)
        self.assertTrue(snippet_copy.id != snippet.id)
        self.assertEqual(snippet_copy.locales.count(), 1)
        self.assertTrue(snippet_copy.locales.all()[0] == snippet.locales.all()[0])
        self.assertEqual(set(snippet_copy.client_match_rules.all()),
                         set(snippet.client_match_rules.all()))

    def test_snippet(self):
        snippet = SnippetFactory.create()
        self._dup_test(snippet)

    def test_json_snippet(self):
        snippet = JSONSnippetFactory.create()
        self._dup_test(snippet)


class ClientMatchRuleTests(TestCase):
    def _client(self, **kwargs):
        client_kwargs = dict((key, '') for key in Client._fields)
        client_kwargs.update(kwargs)
        return Client(**client_kwargs)

    def test_string_match(self):
        client = self._client(channel='aurora')
        pass_rule = ClientMatchRuleFactory(channel='aurora')
        fail_rule = ClientMatchRuleFactory(channel='nightly')

        self.assertTrue(pass_rule.matches(client))
        self.assertTrue(not fail_rule.matches(client))

    def test_regex_match(self):
        client = self._client(version='15.2.4')
        pass_rule = ClientMatchRuleFactory(version='/[\d\.]+/')
        fail_rule = ClientMatchRuleFactory(version='/\D+/')

        self.assertTrue(pass_rule.matches(client))
        self.assertTrue(not fail_rule.matches(client))

    def test_multi_match(self):
        client = self._client(version='1.0', locale='en-US')
        pass_rule = ClientMatchRuleFactory(version='1.0', locale='en-US')
        fail_rule = ClientMatchRuleFactory(version='1.0', locale='fr')

        self.assertTrue(pass_rule.matches(client))
        self.assertTrue(not fail_rule.matches(client))

    def test_empty_match(self):
        client = self._client(version='1.0', locale='fr')
        rule = ClientMatchRuleFactory()

        self.assertTrue(rule.matches(client))

    def test_exclusion_rule_match(self):
        client = self._client(channel='aurora')
        fail_rule = ClientMatchRuleFactory(channel='aurora', is_exclusion=True)
        pass_rule = ClientMatchRuleFactory(channel='nightly',
                                           is_exclusion=True)

        self.assertTrue(pass_rule.matches(client))
        self.assertTrue(not fail_rule.matches(client))


class SnippetTemplateTests(TestCase):
    def test_render(self):
        template = SnippetTemplateFactory(code='<p>{{myvar}}</p>')
        self.assertEqual(template.render({'myvar': 'foo'}), '<p>foo</p>')

    def test_render_snippet_id(self):
        """If the template context doesn't have a snippet_id entry, add one set to 0."""
        template = SnippetTemplateFactory(code='<p>{{ snippet_id }}</p>')
        self.assertEqual(template.render({'myvar': 'foo'}), '<p>0</p>')

    @patch('snippets.base.models.hashlib.sha1')
    @patch('snippets.base.models.JINJA_ENV.from_string')
    def test_render_not_cached(self, mock_from_string, mock_sha1):
        """If the template isn't in the cache, add it."""
        template = SnippetTemplateFactory(code='asdf')
        mock_cache = {}

        with patch('snippets.base.models.template_cache', mock_cache):
            result = template.render({})

        jinja_template = mock_from_string.return_value
        cache_key = mock_sha1.return_value.hexdigest.return_value
        self.assertEqual(mock_cache, {cache_key: jinja_template})

        mock_sha1.assert_called_with(b'asdf')
        mock_from_string.assert_called_with('asdf')
        jinja_template.render.assert_called_with({'snippet_id': 0})
        self.assertEqual(result, jinja_template.render.return_value)

    @patch('snippets.base.models.hashlib.sha1')
    @patch('snippets.base.models.JINJA_ENV.from_string')
    def test_render_cached(self, mock_from_string, mock_sha1):
        """
        If the template is in the cache, use the cached version instead
        of bothering to compile it.
        """
        template = SnippetTemplateFactory(code='asdf')
        cache_key = mock_sha1.return_value.hexdigest.return_value
        jinja_template = Mock()
        mock_cache = {cache_key: jinja_template}

        with patch('snippets.base.models.template_cache', mock_cache):
            result = template.render({})

        mock_sha1.assert_called_with(b'asdf')
        self.assertTrue(not mock_from_string.called)
        jinja_template.render.assert_called_with({'snippet_id': 0})
        self.assertEqual(result, jinja_template.render.return_value)


class SnippetTests(TestCase):
    def test_to_dict(self):
        snippet = SnippetFactory.create(weight=60, campaign='foo-campaign',
                                        countries=['gr', 'it'], client_options={'foo': 'bar'})
        snippet.render = Mock()
        snippet.render.return_value = 'rendered'

        data = {
            'code': 'rendered',
            'client_options': {'foo': 'bar'},
            'campaign': 'foo-campaign',
            'weight': 60,
            'countries': ['gr', 'it'],
            'exclude_from_search_engines': [],
            'id': snippet.id,
            'name': snippet.name,
        }
        self.assertEqual(data, snippet.to_dict())

    def test_render(self):
        template = SnippetTemplateFactory.create()
        template.render = Mock()
        template.render.return_value = '<a href="asdf">qwer</a>'

        data = '{"url": "asdf", "text": "qwer"}'
        snippet = SnippetFactory.create(template=template, data=data,
                                        countries=['us'], weight=60)

        expected = ('<div data-snippet-id="{id}" data-weight="60" data-campaign="" '
                    'class="snippet-metadata" data-countries="us">'
                    '<a href="asdf">qwer</a></div>'.format(id=snippet.id))
        self.assertEqual(snippet.render().strip(), expected)
        template.render.assert_called_with({
            'url': 'asdf',
            'text': 'qwer',
            'snippet_id': snippet.id
        })

    def test_render_campaign(self):
        template = SnippetTemplateFactory.create()
        template.render = Mock()
        template.render.return_value = '<a href="asdf">qwer</a>'

        data = '{"url": "asdf", "text": "qwer"}'
        snippet = SnippetFactory.create(template=template, data=data, campaign='foo')

        expected = Markup('<div data-snippet-id="{id}" data-weight="100" '
                          'data-campaign="foo" class="snippet-metadata">'
                          '<a href="asdf">qwer</a></div>'.format(id=snippet.id))
        self.assertEqual(snippet.render().strip(), expected)

    def test_render_no_country(self):
        """
        If the snippet isn't geolocated, don't include the data-countries
        attribute.
        """
        template = SnippetTemplateFactory.create()
        template.render = Mock()
        template.render.return_value = '<a href="asdf">qwer</a>'

        data = '{"url": "asdf", "text": "qwer"}'
        snippet = SnippetFactory.create(template=template, data=data)

        expected = Markup('<div data-snippet-id="{0}" data-weight="100" '
                          'data-campaign="" class="snippet-metadata">'
                          '<a href="asdf">qwer</a></div>'
                          .format(snippet.id))
        self.assertEqual(snippet.render().strip(), expected)

    def test_render_multiple_countries(self):
        """
        Include multiple countries in data-countries
        """
        template = SnippetTemplateFactory.create()
        template.render = Mock()
        template.render.return_value = '<a href="asdf">qwer</a>'

        data = '{"url": "asdf", "text": "qwer"}'
        snippet = SnippetFactory.create(template=template, data=data, countries=['us', 'el'])

        expected = Markup(
            '<div data-snippet-id="{0}" data-weight="100" data-campaign="" '
            'class="snippet-metadata" data-countries="el,us">'
            '<a href="asdf">qwer</a></div>'.format(snippet.id))
        self.assertEqual(snippet.render().strip(), expected)

    def test_render_exclude_search_engines(self):
        """
        If the snippet must get excluded from search engines,
        include the data-exclude-from-search-engines attribute.
        """
        template = SnippetTemplateFactory.create()
        template.render = Mock()
        template.render.return_value = '<a href="asdf">qwer</a>'

        data = '{"url": "asdf", "text": "qwer"}'
        snippet = SnippetFactory.create(template=template, data=data)
        search_providers = SearchProviderFactory.create_batch(2)
        snippet.exclude_from_search_providers.add(*search_providers)

        engines = ','.join(map(lambda x: x.identifier, search_providers))
        expected = Markup(
            '<div data-snippet-id="{id}" data-weight="100" data-campaign="" '
            'class="snippet-metadata" data-exclude-from-search-engines="{engines}">'
            '<a href="asdf">qwer</a></div>'.format(id=snippet.id, engines=engines))
        self.assertEqual(snippet.render().strip(), expected)

    def test_render_unicode(self):
        variable = SnippetTemplateVariableFactory(name='data')
        template = SnippetTemplateFactory.create(code='{{ data }}',
                                                 variable_set=[variable])
        snippet = SnippetFactory(template=template, data='{"data": "φοο"}')
        output = snippet.render()
        self.assertEqual(pq(output)[0].text, '\u03c6\u03bf\u03bf')

    def test_render_snippet_id(self):
        """Include the snippet ID in the template context when rendering."""
        snippet = SnippetFactory.create(template__code='<p>{{ snippet_id }}</p>')
        snippet.template.render = Mock()
        snippet.render()
        snippet.template.render.assert_called_with({'snippet_id': snippet.id})

    def test_render_no_snippet_id(self):
        """
        If a snippet that hasn't been saved to the database yet is
        rendered, the snippet ID should be set to 0.
        """
        snippet = SnippetFactory.build(template__code='<p>{{ snippet_id }}</p>')
        snippet.template.render = Mock()
        snippet.render()
        snippet.template.render.assert_called_with({'snippet_id': 0})

    def test_render_data_with_snippet_id(self):
        """
        Any strings included in the template context should have the
        substring "[[snippet_id]]" replaced with the ID of the snippet.
        """
        snippet = SnippetFactory.create(
            template__code='<p>{{ code }}</p>',
            data='{"code": "snippet id [[snippet_id]]", "foo": true}')
        snippet.template.render = Mock()
        snippet.render()
        snippet.template.render.assert_called_with({'code': 'snippet id {0}'.format(snippet.id),
                                                    'snippet_id': snippet.id,
                                                    'foo': True})

    def test_render_to_as_router(self):
        """

        """
        snippet = SnippetFactory.create(
            template__code='<p>{{ text }} {{ foo }}</p>',
            data='{"text": "snippet id [[snippet_id]]", "foo": "bar"}')
        generated_result = snippet.render_to_as_router()
        expected_result = {
            'id': str(snippet.id),
            'template': snippet.template.code_name,
            'template_version': snippet.template.version,
            'campaign': snippet.campaign,
            'content': {
                'text': 'snippet id {}'.format(snippet.id),
                'foo': 'bar',
                'links': {},
            }
        }
        self.assertEqual(generated_result, expected_result)

        # Check start date include
        snippet.publish_start = datetime(2018, 4, 11, 0, 0)
        snippet.publish_end = None
        generated_result = snippet.render_to_as_router()
        self.assertEqual(generated_result['publish_start'], 1523404800)
        self.assertTrue('publish_end' not in generated_result)

        # Check end date include
        snippet.publish_start = None
        snippet.publish_end = datetime(2018, 3, 23, 0, 0)
        generated_result = snippet.render_to_as_router()
        self.assertEqual(generated_result['publish_end'], 1521763200)
        self.assertTrue('publish_start' not in generated_result)


class UploadedFileTests(TestCase):

    @override_settings(CDN_URL='http://example.com')
    def test_url_with_cdn_url(self):
        test_file = UploadedFile()
        test_file.file = Mock()
        test_file.file.url = 'foo'
        self.assertEqual(test_file.url, 'http://example.com/foo')

    @override_settings(CDN_URL='http://example.com/error/')
    def test_url_without_cdn_url(self):
        test_file = UploadedFileFactory.build()
        test_file.file = Mock()
        test_file.file.url = 'bar'
        with patch('snippets.base.models.settings', wraps=settings) as settings_mock:
            delattr(settings_mock, 'CDN_URL')
            settings_mock.SITE_URL = 'http://example.com/foo/'
            self.assertEqual(test_file.url, 'http://example.com/foo/bar')

    @override_settings(MEDIA_FILES_ROOT='filesroot/')
    @patch('snippets.base.models.uuid')
    def test_generate_new_filename(self, uuid_mock):
        uuid_mock.uuid4.return_value = 'bar'
        file = UploadedFileFactory.build()
        filename = _generate_filename(file, 'filename.boing')
        self.assertEqual(filename, 'filesroot/bar.boing')

    def test_generate_filename_existing_entry(self):
        obj = UploadedFileFactory.build()
        obj.file.name = 'bar.png'
        obj.save()
        filename = _generate_filename(obj, 'new_filename.boing')
        self.assertEqual(filename, 'bar.png')

    def test_snippets(self):
        instance = UploadedFileFactory.build()
        instance.file = MagicMock()
        instance.file.url = '/media/foo.png'
        snippets = SnippetFactory.create_batch(2, data='lalala {0} foobar'.format(instance.url))
        template = SnippetTemplateFactory.create(code='<foo>{0}</foo>'.format(instance.url))
        more_snippets = SnippetFactory.create_batch(3, template=template)
        self.assertEqual(set(instance.snippets), set(list(snippets) + list(more_snippets)))


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

        with patch('snippets.base.models.cache') as cache:
            with patch('snippets.base.models.render_to_string') as render_to_string:
                with patch('snippets.base.models.default_storage') as default_storage:
                    with self.settings(SNIPPET_BUNDLE_TIMEOUT=10):
                        with patch('snippets.base.models.brotli', wraps=brotli) as brotli_mock:
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

        with patch('snippets.base.models.cache') as cache:
            with patch('snippets.base.models.render_to_string') as render_to_string:
                with patch('snippets.base.models.default_storage') as default_storage:
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

        with patch('snippets.base.models.datetime') as datetime:
            with patch('snippets.base.models.cache') as cache:
                with patch('snippets.base.models.default_storage') as default_storage:
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

            with patch('snippets.base.models.cache') as cache:
                with patch('snippets.base.models.render_to_string') as render_to_string:
                    with patch('snippets.base.models.default_storage') as default_storage:
                        with patch('snippets.base.models.brotli', wraps=brotli) as brotli_mock:
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
        with patch('snippets.base.models.cache') as cache:
            cache.get.return_value = True
            self.assertTrue(bundle.cached)

    def test_cached_remote(self):
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
        with patch('snippets.base.models.cache') as cache:
            cache.get.return_value = False
            with patch('snippets.base.models.default_storage') as default_storage:
                default_storage.exists.return_value = True
                self.assertTrue(bundle.cached)
                cache.set.assert_called_with(bundle.cache_key, True, ONE_DAY)

    def test_not_cached(self):
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
        with patch('snippets.base.models.cache') as cache:
            cache.get.return_value = False
            with patch('snippets.base.models.default_storage') as default_storage:
                default_storage.exists.return_value = False
                self.assertFalse(bundle.cached)

    def test_empty(self):
        bundle = SnippetBundle(self._client(locale='fr', startpage_version=5))
        self.assertTrue(bundle.empty)

        bundle.snippets = [self.snippet1, self.snippet2]
        self.assertFalse(bundle.empty)
