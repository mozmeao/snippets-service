import copy
import io
import subprocess
from datetime import datetime, timedelta

from PIL import Image
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.deletion import ProtectedError
from django.test.utils import override_settings
from django.urls import reverse

from snippets.base.models import (STATUS_CHOICES,
                                  Icon,
                                  Locale,
                                  Job,
                                  SimpleTemplate,
                                  _generate_filename)
from snippets.base.util import fluent_link_extractor
from snippets.base.tests import (ASRSnippetFactory,
                                 DistributionBundleFactory,
                                 IconFactory,
                                 JobFactory,
                                 TargetFactory,
                                 TestCase,
                                 UserFactory)


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

    def test_can_be_deleted(self):
        job = JobFactory(status=Job.PUBLISHED)
        icon = job.snippet.template_ng.icon
        self.assertRaises(ProtectedError, icon.delete)

        job.change_status(status=Job.COMPLETED)
        icon.delete()
        job.refresh_from_db()

        self.assertEqual(job.snippet.template_ng.icon, None)


class ASRSnippetTests(TestCase):
    def test_render(self):
        snippet = ASRSnippetFactory.create(
            template_relation__text=('snippet id [[snippet_id]] and with '
                                     'campaign [[campaign_slug]] and '
                                     '<a href="https://example.com/[[snippet_id]]/foo">link</a> in '
                                     '[[channels]] channels'),
        )
        snippet.template_ng.TARGETING = 'true'
        generated_result = snippet.render()
        expected_result = {
            'template': snippet.template_ng.code_name,
            'template_version': snippet.template_ng.version,
            'targeting': 'true',
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
            'targeting': '',
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
                TargetFactory.create(channels='release'),
                TargetFactory.create(channels='release;beta;nightly'),
                TargetFactory.create(channels=''),
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
                TargetFactory(channels='nightly', jexl_expr='(la==lo)'),
                TargetFactory(channels='beta;nightly'),
                TargetFactory(channels='beta;nightly', jexl_expr='foo==bar'),
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
                TargetFactory(channels='nightly', jexl_expr='(la==lo)'),
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


class TargetTests(TestCase):
    def test_is_custom(self):
        target = TargetFactory(channels='')
        self.assertTrue(target.is_custom)
        not_custom_target = TargetFactory(filtr_is_default_browser='true')
        self.assertFalse(not_custom_target.is_custom)
