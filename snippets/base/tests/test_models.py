import copy
import io
import subprocess
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.utils import override_settings
from django.urls import reverse

from PIL import Image
from jinja2 import Markup
from unittest.mock import Mock, patch
from pyquery import PyQuery as pq

from snippets.base.models import (STATUS_CHOICES,
                                  Client,
                                  Icon,
                                  Locale,
                                  Job,
                                  SimpleTemplate,
                                  _generate_filename)
from snippets.base.util import fluent_link_extractor
from snippets.base.tests import (ASRSnippetFactory,
                                 ClientMatchRuleFactory,
                                 DistributionBundleFactory,
                                 IconFactory,
                                 JobFactory,
                                 SearchProviderFactory,
                                 SnippetFactory,
                                 SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory,
                                 TargetFactory,
                                 TestCase,
                                 UserFactory)


class DuplicateSnippetMixInTests(TestCase):
    def _dup_test(self, snippet):
        user = UserFactory.create()
        snippet.client_match_rules.add(*ClientMatchRuleFactory.create_batch(3))
        snippet_copy = snippet.duplicate(user)
        self.assertEqual(snippet_copy.published, False)
        self.assertNotEqual(snippet_copy.id, snippet.id)
        self.assertEqual(snippet_copy.locales.count(), 1)
        self.assertTrue(snippet_copy.locales.all()[0] == snippet.locales.all()[0])
        self.assertEqual(set(snippet_copy.client_match_rules.all()),
                         set(snippet.client_match_rules.all()))

        self.assertNotEqual(snippet_copy.creator, snippet.creator)

    def test_snippet(self):
        snippet = SnippetFactory.create()
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
        pass_rule = ClientMatchRuleFactory(version=r'/[\d\.]+/')
        fail_rule = ClientMatchRuleFactory(version=r'/\D+/')

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
                                        countries=['gr', 'it'])
        snippet.render = Mock()
        snippet.render.return_value = 'rendered'

        snippet.get_client_options = Mock()
        snippet.get_client_options.return_value = {'foo': 'bar'}

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

    @override_settings(SITE_URL='http://example.com')
    def test_get_admin_url(self):
        snippet = SnippetFactory.create()
        self.assertTrue(snippet.get_admin_url().startswith('http://example.com'))
        self.assertTrue(snippet.get_admin_url(full=False).startswith('/'))


class GenerateFilenameTests(TestCase):
    @override_settings(MEDIA_ICONS_ROOT='filesroot/')
    @patch('snippets.base.models.uuid')
    def test_generate_new_filename(self, uuid_mock):
        uuid_mock.uuid4.return_value = 'bar'
        icon = IconFactory(image__filename='upload.png')
        self.assertEqual(icon.image.name, 'filesroot/bar.png')

    @patch('snippets.base.models.uuid')
    def test_generate_filename_different_root(self, uuid_mock):
        uuid_mock.uuid4.return_value = 'bar'
        filename = _generate_filename(None, 'filename.boing', root='new-root')
        self.assertEqual(filename, 'new-root/bar.boing')

    def test_update_icon_generate_new_filename(self):
        icon = IconFactory()
        old_name = icon.image.name

        # Simplest way to test with a new image is to create a new Icon with
        # IconFactory
        new_icon = IconFactory()
        icon.image = File(new_icon.image.file.open())
        icon.save()
        icon.refresh_from_db()
        self.assertNotEqual(icon.image.name, old_name)


class TemplateTests(TestCase):
    def test_process_rendered_data(self):
        data = {
            'foo': '',
            'bar': 'bar',
            'button_url': 'special:about:logins'
        }
        expected_data = {
            'bar': 'bar',
            'links': {},
            'button_action': 'OPEN_ABOUT_PAGE',
            'button_action_args': 'logins',
            'button_entrypoint_name': 'entryPoint',
            'button_entrypoint_value': 'snippet',
        }
        snippet = ASRSnippetFactory()
        with patch('snippets.base.models.util.fluent_link_extractor',
                   wraps=fluent_link_extractor) as fluent_link_extractor_mock:
            processed_data = snippet.template_ng._process_rendered_data(data)

        self.assertTrue(fluent_link_extractor_mock.called)
        self.assertEqual(processed_data, expected_data)

    def test_subtemplate(self):
        snippet = ASRSnippetFactory()
        subtemplate = snippet.template_relation.subtemplate
        self.assertTrue(type(subtemplate) is SimpleTemplate)

        # Test subtemplate when checking from an object that inherits Template
        subtemplate = snippet.template_relation.subtemplate.subtemplate
        self.assertTrue(type(subtemplate) is SimpleTemplate)

    def test_add_utm_params(self):
        snippet = ASRSnippetFactory(
            template_relation__text=('This is a <a href="https://www.example.com/?utm_medium=SI">'
                                     'linked test</a> and <a href="https://example.com">'
                                     'another link</a> without any params'),
            template_relation__button_url='https://www.mozilla.org/foo/bar/?lala=lolo',
        )
        snippet.template_ng.add_utm_params()
        self.assertEqual(
            snippet.template_ng.text,
            ('This is a <a href="https://www.example.com/?utm_medium=SI'
             '&utm_source=desktop-snippet&utm_campaign=[[campaign_slug]]'
             '&utm_term=[[job_id]]&utm_content=[[channels]]">linked test</a> and '
             '<a href="https://example.com/?utm_source=desktop-snippet&utm_medium=snippet'
             '&utm_campaign=[[campaign_slug]]&utm_term=[[job_id]]&utm_content=[[channels]]">'
             'another link</a> without any params')
        )
        self.assertEqual(
            snippet.template_ng.button_url,
            ('https://www.mozilla.org/foo/bar/?lala=lolo&utm_source=desktop-snippet'
             '&utm_medium=snippet&utm_campaign=[[campaign_slug]]&utm_term=[[job_id]]'
             '&utm_content=[[channels]]')
        )


class IconTests(TestCase):
    def _build_in_memory_uploaded_file(self):
        img = Image.new('RGB', (30, 30), color='red')
        fle = io.BytesIO()
        img.save(fle, 'PNG')
        fle.seek(0)
        size = len(fle.read())
        fle.seek(0)
        return InMemoryUploadedFile(fle, 'ImageField', 'foo.png', 'image/png', size, None)

    @override_settings(CDN_URL='http://example.com')
    def test_url_with_cdn_url(self):
        test_file = Icon()
        test_file.image = Mock()
        test_file.image.url = 'foo'
        self.assertEqual(test_file.url, 'http://example.com/foo')

    def test_url_without_cdn_url(self):
        test_file = Icon()
        test_file.image = Mock()
        test_file.image.url = 'foo'
        with patch('snippets.base.models.settings', wraps=settings) as settings_mock:
            delattr(settings_mock, 'CDN_URL')
            settings_mock.SITE_URL = 'http://second-example.com/'
            self.assertEqual(test_file.url, 'http://second-example.com/foo')

    @override_settings(IMAGE_OPTIMIZE=True)
    def test_dont_process_existing_files(self):
        instance = IconFactory.build()
        with patch('snippets.base.models.subprocess.run') as run_mock:
            instance.clean()
        self.assertFalse(run_mock.called)

    @override_settings(IMAGE_OPTIMIZE=False)
    def test_dont_process_when_setting_off(self):
        instance = IconFactory()
        instance.image.file = self._build_in_memory_uploaded_file()
        with patch('snippets.base.models.subprocess.run') as run_mock:
            instance.clean()
        self.assertFalse(run_mock.called)

    @override_settings(IMAGE_OPTIMIZE=True)
    def test_image_optimization(self):
        instance = IconFactory.build()
        instance.image.file = self._build_in_memory_uploaded_file()
        with patch('snippets.base.models.subprocess.run', wraps=subprocess.run) as run_mock:
            instance.clean()
        self.assertTrue(run_mock.called)

    @override_settings(IMAGE_MAX_DIMENSION=0)
    def test_dimensions_check_disabled(self):
        instance = IconFactory.build()
        instance.image.file = self._build_in_memory_uploaded_file()
        self.assertIsNone(instance.clean())

    @override_settings(IMAGE_MAX_DIMENSION=50)
    def test_valid_dimensions(self):
        instance = IconFactory.build()
        instance.image.file = self._build_in_memory_uploaded_file()
        self.assertIsNone(instance.clean())

    @override_settings(IMAGE_MAX_DIMENSION=20)
    def test_invalid_dimensions(self):
        instance = IconFactory.build()
        instance.image.file = self._build_in_memory_uploaded_file()
        try:
            instance.clean()
        except ValidationError as e:
            self.assertEqual(e.message_dict['image'],
                             ['Upload an image at most 20x20. This image is 30x30.'])

    @override_settings(IMAGE_MAX_SIZE=0)
    def test_size_test_disabled(self):
        instance = IconFactory.build()
        instance.image.file = self._build_in_memory_uploaded_file()
        self.assertIsNone(instance.clean())

    @override_settings(IMAGE_MAX_SIZE=40960)
    def test_valid_size(self):
        instance = IconFactory.build()
        instance.image.file = self._build_in_memory_uploaded_file()
        self.assertIsNone(instance.clean())

    @override_settings(IMAGE_MAX_SIZE=1)
    def test_invalid_size(self):
        instance = IconFactory.build()
        instance.image.file = self._build_in_memory_uploaded_file()
        try:
            instance.clean()
        except ValidationError as e:
            self.assertEqual(e.message_dict['image'],
                             ['Upload an image less than 0 KiB. This image is 0 KiB.'])

    def test_valid_image_png(self):
        instance = IconFactory.build()
        instance.image.file = self._build_in_memory_uploaded_file()
        self.assertIsNone(instance.clean())

    def test_invalid_image(self):
        instance = IconFactory.build()
        img = Image.new('RGB', (30, 30), color='red')
        fle = io.BytesIO()
        img.save(fle, 'JPEG')
        fle.seek(0)
        size = len(fle.read())
        fle.seek(0)
        instance.image.file = InMemoryUploadedFile(
            fle, 'ImageField', 'foo.jpeg', 'image/jpeg', size, None)
        try:
            instance.clean()
        except ValidationError as e:
            self.assertEqual(e.message_dict['image'], ['Upload only PNG images.'])


class ASRSnippetTests(TestCase):
    def test_render(self):
        snippet = ASRSnippetFactory.create(
            template_relation__text=('snippet id [[snippet_id]] and with '
                                     'campaign [[campaign_slug]] and '
                                     '<a href="https://example.com/[[snippet_id]]/foo">link</a> in '
                                     '[[channels]] channels'),
        )
        generated_result = snippet.render()
        self.maxDiff = None
        expected_result = {
            'template': snippet.template_ng.code_name,
            'template_version': snippet.template_ng.version,
            'content': {
                'text': ('snippet id {} and with campaign [[campaign_slug]] and '
                         '<link0>link</link0> in [[channels]] channels').format(snippet.id),
                'links': {
                    'link0': {
                        'url': 'https://example.com/{}/foo'.format(snippet.id),
                    }
                },
                'tall': False,
                'icon': snippet.template_ng.icon.url,
                'do_not_autoblock': False,
                'block_button_text': 'Remove this',
            },
        }
        self.assertEqual(generated_result, expected_result)

    def test_render_preview_only(self):
        snippet = ASRSnippetFactory.create(
            template_relation__text=('snippet id *[[snippet_id]]* '
                                     '*[[campaign_slug]]* *[[channels]]* *[[job_id]]*'))
        generated_result = snippet.render(preview=True)
        expected_result = {
            'id': 'preview-{}'.format(snippet.id),
            'template': snippet.template_ng.code_name,
            'template_version': snippet.template_ng.version,
            'content': {
                'do_not_autoblock': True,
                # snippet_id, campaign_slug and channels must be replaced with empty string.
                'text': 'snippet id ** ** ** **',
                'links': {},
                'tall': False,
                'icon': snippet.template_ng.icon.url,
                'block_button_text': 'Remove this',
            }
        }
        self.assertEqual(generated_result, expected_result)

    @override_settings(SITE_URL='http://example.com')
    def test_get_preview_url(self):
        snippet = ASRSnippetFactory.create()
        expected_result = 'about:newtab?theme=light&dir=ltr&endpoint=http://example.com'
        expected_result += reverse('asr-preview', kwargs={'uuid': snippet.uuid})
        self.assertEqual(snippet.get_preview_url(), expected_result)

    @override_settings(SITE_URL='http://example.com',
                       ADMIN_REDIRECT_URL='http://admin.example.com')
    def test_get_preview_url_admin(self):
        snippet = ASRSnippetFactory.create()
        expected_result = 'about:newtab?theme=light&dir=ltr&endpoint=http://admin.example.com'
        expected_result += reverse('asr-preview', kwargs={'uuid': snippet.uuid})
        self.assertEqual(snippet.get_preview_url(), expected_result)

    @override_settings(SITE_URL='http://example.com')
    def test_get_preview_url_dark(self):
        snippet = ASRSnippetFactory.create()
        expected_result = 'about:newtab?theme=dark&dir=ltr&endpoint=http://example.com'
        expected_result += reverse('asr-preview', kwargs={'uuid': snippet.uuid})
        self.assertEqual(snippet.get_preview_url(dark=True), expected_result)

    @override_settings(SITE_URL='http://example.com')
    def test_get_preview_url_rtl(self):
        snippet = ASRSnippetFactory.create()
        snippet.locale.rtl = True
        expected_result = 'about:newtab?theme=dark&dir=rtl&endpoint=http://example.com'
        expected_result += reverse('asr-preview', kwargs={'uuid': snippet.uuid})
        self.assertEqual(snippet.get_preview_url(dark=True), expected_result)

    def test_duplicate(self):
        user = UserFactory.create()
        snippet = ASRSnippetFactory.create(
            status=STATUS_CHOICES['Approved'],
        )
        duplicate_snippet = snippet.duplicate(user)
        snippet.refresh_from_db()

        for attr in ['id', 'creator', 'created', 'modified', 'name', 'uuid']:
            self.assertNotEqual(getattr(snippet, attr), getattr(duplicate_snippet, attr))

        self.assertEqual(duplicate_snippet.status, STATUS_CHOICES['Draft'])
        self.assertNotEqual(snippet.template_ng.pk, duplicate_snippet.template_ng.pk)

    @override_settings(SITE_URL='http://example.com')
    def test_get_admin_url(self):
        snippet = ASRSnippetFactory.create()
        self.assertTrue(snippet.get_admin_url().startswith('http://example.com'))
        self.assertTrue(snippet.get_admin_url(full=False).startswith('/'))

    def test_modified_date_updates_when_template_updates(self):
        snippet = ASRSnippetFactory()
        # Must refresh from db to get the actual datetime stored in db which
        # may be different by milliseconds from the original python datetime.
        snippet.refresh_from_db()
        old_modified = snippet.modified

        template = snippet.template_ng
        template.title = 'foobar'
        template.save()

        snippet.refresh_from_db()
        new_modified = snippet.modified

        self.assertNotEqual(old_modified, new_modified)

    def test_modified_date_updates_when_icon_updates(self):
        snippet = ASRSnippetFactory()
        # Must refresh from db to get the actual datetime stored in db which
        # may be different by milliseconds from the original python datetime.
        snippet.refresh_from_db()
        old_modified = snippet.modified

        template = snippet.template_ng
        template.icon = IconFactory()
        template.save()

        snippet.refresh_from_db()
        new_modified = snippet.modified

        self.assertNotEqual(old_modified, new_modified)

    def test_modified_date_updates_when_campaign_updates(self):
        job = JobFactory()
        snippet = job.snippet
        # Must refresh from db to get the actual datetime stored in db which
        # may be different by milliseconds from the original python datetime.
        snippet.refresh_from_db()
        old_modified = snippet.modified

        campaign = job.campaign
        campaign.name = 'new name'
        campaign.save()

        snippet.refresh_from_db()
        new_modified = snippet.modified

        self.assertNotEqual(old_modified, new_modified)

    def test_modified_date_updates_when_target_updates(self):
        target = TargetFactory()
        job = JobFactory(targets=[target])
        snippet = job.snippet
        # Must refresh from db to get the actual datetime stored in db which
        # may be different by milliseconds from the original python datetime.
        snippet.refresh_from_db()
        old_modified = snippet.modified

        target.name = 'new name'
        target.save()
        snippet.refresh_from_db()
        new_modified = snippet.modified

        self.assertNotEqual(old_modified, new_modified)

    def test_modified_date_updates_when_job_updates(self):
        job = JobFactory()
        snippet = job.snippet
        # Must refresh from db to get the actual datetime stored in db which
        # may be different by milliseconds from the original python datetime.
        snippet.refresh_from_db()
        old_modified = snippet.modified

        job.status = Job.COMPLETED
        job.save()
        snippet.refresh_from_db()
        new_modified = snippet.modified

        self.assertNotEqual(old_modified, new_modified)

    def test_modified_date_updates_when_distribution_bundle_updates(self):
        job = JobFactory()
        distribution_bundle = DistributionBundleFactory()
        distribution_bundle.distributions.add(job.distribution)
        snippet = job.snippet
        # Must refresh from db to get the actual datetime stored in db which
        # may be different by milliseconds from the original python datetime.
        snippet.refresh_from_db()
        old_modified = snippet.modified

        distribution_bundle.code_name = 'bar'
        distribution_bundle.save()

        snippet.refresh_from_db()
        new_modified = snippet.modified
        self.assertNotEqual(old_modified, new_modified)


class LocaleTests(TestCase):
    def test_code_commas_and_case(self):
        locale = Locale(name='foo', code='Bar')
        locale.save()
        self.assertEqual(locale.code, ',bar,')


class JobTests(TestCase):
    def test_channels(self):
        job = JobFactory.create(
            targets=[
                TargetFactory.create(on_release=True),
                TargetFactory.create(on_beta=True, on_nightly=True),
                TargetFactory.create(on_release=False, on_esr=False,
                                     on_aurora=False, on_beta=False, on_nightly=False),
            ])

        self.assertTrue(job.channels, set(['release', 'beta', 'nightly']))

    def test_clean(self):
        job_clean = JobFactory.create(publish_start=datetime.utcnow() + timedelta(days=1),
                                      publish_end=datetime.utcnow() + timedelta(days=2))
        job_clean.clean()

        job_dirty = JobFactory.create(publish_start=datetime.utcnow() + timedelta(days=3),
                                      publish_end=datetime.utcnow() + timedelta(days=2))

        self.assertRaisesMessage(
            ValidationError, 'Publish start must come before publish end.', job_dirty.clean)

    def test_render(self):
        self.maxDiff = None
        job = JobFactory.create(
            weight=10, campaign__slug='demo-campaign',
            targets=[
                TargetFactory(on_release=False, on_beta=False,
                              on_esr=False, on_aurora=False, on_nightly=True,
                              jexl_expr='(la==lo)'),
                TargetFactory(on_release=False, on_beta=True,
                              on_esr=False, on_aurora=False, on_nightly=True),
                TargetFactory(on_release=False, on_beta=True,
                              on_esr=False, on_aurora=False, on_nightly=True,
                              jexl_expr='foo==bar'),
            ]
        )

        snippet_render = {
            'template': 'simple_snippet',
            'template_version': 'xx.xx',
            'content': {
                'block_button_text': 'Block me',
                'text': 'This is text [[job_id]]',
            }
        }
        expected_output = copy.deepcopy(snippet_render)
        expected_output.update({
            'id': str(job.id),
            'weight': 10,
            'campaign': 'demo-campaign',
            'targeting': '(la==lo) && foo==bar',
            'content': {
                'block_button_text': 'Block me',
                'text': f'This is text {job.id}',
            }
        })
        job.snippet.render = Mock()
        job.snippet.render.return_value = snippet_render
        generated_output = job.render()

        self.assertEqual(generated_output, expected_output)

    def test_render_always_eval_to_false(self):
        job = JobFactory.create(
            weight=10, campaign__slug='demo-campaign',
            targets=[
                TargetFactory(on_release=False, on_beta=False,
                              on_esr=False, on_aurora=False, on_nightly=True,
                              jexl_expr='(la==lo)'),
            ]
        )
        job.snippet.render = Mock()
        job.snippet.render.return_value = {}
        generated_output = job.render(always_eval_to_false=True)
        self.assertEqual(generated_output['targeting'], '(la==lo) && false')

    def test_render_client_limits(self):
        # Combined
        job = JobFactory.create(
            client_limit_lifetime=100,
            client_limit_per_hour=10,
            client_limit_per_month=100,
            campaign__slug='demo_campaign',
        )
        expected_output = {
            'id': str(job.id),
            'weight': 100,
            'campaign': 'demo_campaign',
            'targeting': '',
            'frequency': {
                'lifetime': 100,
                'custom': [{'period': 3600000, 'cap': 10}, {'period': 2592000000, 'cap': 100}]
            }
        }
        job.snippet.render = Mock()
        job.snippet.render.return_value = {}
        generated_output = job.render()
        self.assertEqual(generated_output, expected_output)

        # Lifetime limit only
        job = JobFactory.create(
            client_limit_lifetime=100,
            campaign__slug='demo_campaign_1',
        )
        expected_output = {
            'id': str(job.id),
            'weight': 100,
            'campaign': 'demo_campaign_1',
            'targeting': '',
            'frequency': {
                'lifetime': 100,
            }
        }
        job.snippet.render = Mock()
        job.snippet.render.return_value = {}
        generated_output = job.render()
        self.assertEqual(generated_output, expected_output)

        # Custom limits only

        # Lifetime limit only
        job = JobFactory.create(
            client_limit_per_week=9,
            client_limit_per_fortnight=99,
            campaign__slug='demo_campaign_2',
        )
        expected_output = {
            'id': str(job.id),
            'weight': 100,
            'campaign': 'demo_campaign_2',
            'targeting': '',
            'frequency': {
                'custom': [{'period': 604800000, 'cap': 9}, {'period': 1296000000, 'cap': 99}]
            }
        }
        job.snippet.render = Mock()
        job.snippet.render.return_value = {}
        generated_output = job.render()
        self.assertEqual(generated_output, expected_output)

    def test_change_status(self):
        job = JobFactory.create(status=Job.DRAFT)
        with patch('snippets.base.models.slack') as slack_mock:
            with patch('snippets.base.models.LogEntry') as log_entry_mock:
                job.change_status(status=Job.SCHEDULED, user=job.creator, send_slack=True)

        job.refresh_from_db()

        self.assertEqual(job.status, Job.SCHEDULED)
        log_entry_mock.objects.log_action.assert_called()
        slack_mock._send_slack.assert_called()

    def test_change_status_to_completed(self):
        job = JobFactory.create(status=Job.DRAFT)
        with patch('snippets.base.models.datetime') as datetime_mock:
            datetime_mock.utcnow.return_value = datetime(2019, 1, 1, 0, 0)
            job.change_status(status=Job.COMPLETED, user=None, send_slack=False)

        job.refresh_from_db()
        self.assertEqual(job.status, Job.COMPLETED)
        self.assertEqual(job.completed_on, datetime(2019, 1, 1, 0, 0))

    @override_settings(SITE_URL='http://example.com')
    def test_get_admin_url(self):
        job = JobFactory.create()
        self.assertEqual(job.get_admin_url(), f'http://example.com/admin/base/job/{job.id}/change/')
        self.assertEqual(job.get_admin_url(full=False), f'/admin/base/job/{job.id}/change/')

    def test_duplicate(self):
        user = UserFactory.create()
        job = JobFactory.create(
            status=Job.PUBLISHED,
            metric_impressions=500,
            metric_clicks=500,
            metric_blocks=500,
            completed_on=datetime.utcnow()
        )
        duplicate_job = job.duplicate(user)
        job.refresh_from_db()

        for attr in ['id', 'creator', 'created', 'modified', 'uuid']:
            self.assertNotEqual(getattr(job, attr), getattr(duplicate_job, attr))

        self.assertEqual(duplicate_job.status, Job.DRAFT)
        self.assertEqual(duplicate_job.metric_impressions, 0)
        self.assertEqual(duplicate_job.metric_clicks, 0)
        self.assertEqual(duplicate_job.metric_blocks, 0)
        self.assertEqual(duplicate_job.completed_on, None)
