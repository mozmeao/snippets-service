from django.conf import settings
from django.core.exceptions import ValidationError
from django.test.utils import override_settings

from mock import MagicMock, Mock, patch
from nose.tools import assert_raises, eq_, ok_
from pyquery import PyQuery as pq

from snippets.base.models import Client, UploadedFile, validate_xml
from snippets.base.tests import (ClientMatchRuleFactory, UploadedFileFactory,
                                 SnippetFactory,
                                 SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory,
                                 TestCase)


class ClientMatchRuleTests(TestCase):
    def _client(self, **kwargs):
        client_kwargs = dict((key, '') for key in Client._fields)
        client_kwargs.update(kwargs)
        return Client(**client_kwargs)

    def test_string_match(self):
        client = self._client(channel='aurora')
        pass_rule = ClientMatchRuleFactory(channel='aurora')
        fail_rule = ClientMatchRuleFactory(channel='nightly')

        ok_(pass_rule.matches(client))
        ok_(not fail_rule.matches(client))

    def test_regex_match(self):
        client = self._client(version='15.2.4')
        pass_rule = ClientMatchRuleFactory(version='/[\d\.]+/')
        fail_rule = ClientMatchRuleFactory(version='/\D+/')

        ok_(pass_rule.matches(client))
        ok_(not fail_rule.matches(client))

    def test_multi_match(self):
        client = self._client(version='1.0', locale='en-US')
        pass_rule = ClientMatchRuleFactory(version='1.0', locale='en-US')
        fail_rule = ClientMatchRuleFactory(version='1.0', locale='fr')

        ok_(pass_rule.matches(client))
        ok_(not fail_rule.matches(client))

    def test_empty_match(self):
        client = self._client(version='1.0', locale='fr')
        rule = ClientMatchRuleFactory()

        ok_(rule.matches(client))

    def test_exclusion_rule_match(self):
        client = self._client(channel='aurora')
        fail_rule = ClientMatchRuleFactory(channel='aurora', is_exclusion=True)
        pass_rule = ClientMatchRuleFactory(channel='nightly',
                                           is_exclusion=True)

        ok_(pass_rule.matches(client))
        ok_(not fail_rule.matches(client))


class XMLValidatorTests(TestCase):
    def test_valid_xml(self):
        valid_xml = '{"foo": "<b>foobar</b>"}'
        eq_(validate_xml(valid_xml), valid_xml)

    def test_invalid_xml(self):
        invalid_xml = '{"foo": "<b><i>foobar<i></b>"}'
        assert_raises(ValidationError, validate_xml, invalid_xml)

    def test_unicode(self):
        unicode_xml = '{"foo": "<b>\u03c6\u03bf\u03bf</b>"}'
        eq_(validate_xml(unicode_xml), unicode_xml)

    def test_non_string_values(self):
        """
        If a value isn't a string, skip over it and continue validating.
        """
        valid_xml = '{"foo": "<b>Bar</b>", "baz": true}'
        eq_(validate_xml(valid_xml), valid_xml)


class SnippetTemplateTests(TestCase):
    def test_render(self):
        template = SnippetTemplateFactory(code='<p>{{myvar}}</p>')
        eq_(template.render({'myvar': 'foo'}), '<p>foo</p>')

    def test_render_snippet_id(self):
        """If the template context doesn't have a snippet_id entry, add one set to 0."""
        template = SnippetTemplateFactory(code='<p>{{ snippet_id }}</p>')
        eq_(template.render({'myvar': 'foo'}), '<p>0</p>')

    @patch('snippets.base.models.hashlib.sha1')
    @patch('snippets.base.models.jingo.env.from_string')
    def test_render_not_cached(self, mock_from_string, mock_sha1):
        """If the template isn't in the cache, add it."""
        template = SnippetTemplateFactory(code='asdf')
        mock_cache = {}

        with patch('snippets.base.models.template_cache', mock_cache):
            result = template.render({})

        jinja_template = mock_from_string.return_value
        cache_key = mock_sha1.return_value.hexdigest.return_value
        eq_(mock_cache, {cache_key: jinja_template})

        mock_sha1.assert_called_with('asdf')
        mock_from_string.assert_called_with('asdf')
        jinja_template.render.assert_called_with({'snippet_id': 0})
        eq_(result, jinja_template.render.return_value)

    @patch('snippets.base.models.hashlib.sha1')
    @patch('snippets.base.models.jingo.env.from_string')
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

        mock_sha1.assert_called_with('asdf')
        ok_(not mock_from_string.called)
        jinja_template.render.assert_called_with({'snippet_id': 0})
        eq_(result, jinja_template.render.return_value)


class SnippetTests(TestCase):
    def test_render(self):
        template = SnippetTemplateFactory.create()
        template.render = Mock()
        template.render.return_value = '<a href="asdf">qwer</a>'

        data = '{"url": "asdf", "text": "qwer"}'
        snippet = SnippetFactory.create(template=template, data=data,
                                        country='us', weight=60,
                                        exclude_from_yahoo=True)

        expected = ('<div data-snippet-id="{0}" data-weight="60" class="snippet-metadata" '
                    'data-country="us" data-exclude-from-yahoo="True">'
                    '<a href="asdf">qwer</a></div>'.format(snippet.id))
        eq_(snippet.render().strip(), expected)
        template.render.assert_called_with({
            'url': 'asdf',
            'text': 'qwer',
            'snippet_id': snippet.id
        })

    def test_render_no_country(self):
        """
        If the snippet isn't geolocated, don't include the data-country
        attribute.
        """
        template = SnippetTemplateFactory.create()
        template.render = Mock()
        template.render.return_value = '<a href="asdf">qwer</a>'

        data = '{"url": "asdf", "text": "qwer"}'
        snippet = SnippetFactory.create(template=template, data=data)

        expected = ('<div data-snippet-id="{0}" data-weight="100" class="snippet-metadata">'
                    '<a href="asdf">qwer</a></div>'
                    .format(snippet.id))
        eq_(snippet.render().strip(), expected)

    def test_render_unicode(self):
        variable = SnippetTemplateVariableFactory(name='data')
        template = SnippetTemplateFactory.create(code='{{ data }}',
                                                 variable_set=[variable])
        snippet = SnippetFactory(template=template,
                                 data='{"data": "\u03c6\u03bf\u03bf"}')
        output = snippet.render()
        eq_(pq(output)[0].text, u'\u03c6\u03bf\u03bf')

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
        substring "<snippet_id>" replaced with the ID of the snippet.
        """
        snippet = SnippetFactory.build(template__code='<p>{{ code }}</p>',
                                       data='{"code": "snippet id <snippet_id>", "foo": true}')
        snippet.template.render = Mock()
        snippet.render()
        snippet.template.render.assert_called_with({'code': 'snippet id 0', 'snippet_id': 0,
                                                    'foo': True})


class UploadedFileTests(TestCase):

    @override_settings(CDN_URL='http://example.com')
    def test_url_with_cdn_url(self):
        test_file = UploadedFile()
        test_file.file = Mock()
        test_file.file.url = 'foo'
        eq_(test_file.url, 'http://example.com/foo')

    @override_settings(CDN_URL='http://example.com/error/')
    def test_url_without_cdn_url(self):
        test_file = UploadedFileFactory.build()
        test_file.file = Mock()
        test_file.file.url = 'bar'
        with patch('snippets.base.models.settings', wraps=settings) as settings_mock:
            delattr(settings_mock, 'CDN_URL')
            settings_mock.SITE_URL = 'http://example.com/foo/'
            eq_(test_file.url, 'http://example.com/foo/bar')

    @patch('snippets.base.models.uuid')
    def test_generate_new_filename(self, uuid_mock):
        uuid_mock.uuid4.return_value = 'bar'
        file = UploadedFileFactory.build()
        UploadedFile.FILES_ROOT = 'filesroot'
        filename = UploadedFile._generate_filename(file, 'filename.boing')
        eq_(filename, 'filesroot/bar.boing')

    def test_generate_filename_existing_entry(self):
        obj = UploadedFileFactory.build()
        obj.file.name = 'bar.png'
        obj.save()
        filename = UploadedFile._generate_filename(obj, 'new_filename.boing')
        eq_(filename, 'bar.png')

    def test_snippets(self):
        instance = UploadedFileFactory.build()
        instance.file = MagicMock()
        instance.file.url = '/media/foo.png'
        snippets = SnippetFactory.create_batch(2, data='lalala {0} foobar'.format(instance.url))
        template = SnippetTemplateFactory.create(code='<foo>{0}</foo>'.format(instance.url))
        more_snippets = SnippetFactory.create_batch(3, template=template)
        eq_(set(instance.snippets), set(list(snippets) + list(more_snippets)))

