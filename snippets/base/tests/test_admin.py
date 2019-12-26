from datetime import date
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test.client import RequestFactory

from unittest.mock import DEFAULT as DEFAULT_MOCK, Mock, patch

from snippets.base import etl
from snippets.base.admin.adminmodels import (
    ASRSnippetAdmin, DailyChannelMetricsAdmin, DailyCountryMetricsAdmin,
    DailyJobMetricsAdmin, DailySnippetMetricsAdmin, JobAdmin,
    SnippetTemplateAdmin)
from snippets.base.admin.legacy import SnippetAdmin
from snippets.base.models import (
    STATUS_CHOICES, ASRSnippet, DailyChannelMetrics, DailyCountryMetrics,
    DailyJobMetrics, DailySnippetMetrics, Job, Snippet, SnippetTemplate,
    SnippetTemplateVariable)
from snippets.base.tests import (ASRSnippetFactory, JobFactory, SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory, TestCase, UserFactory)


class SnippetAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = SnippetAdmin(Snippet, None)
        self.model_admin.admin_site = Mock()
        self.user = User.objects.get_or_create(username='foo', email='foo@example.com')[0]

    def test_save_as_published(self):
        request = self.factory.post('/', data={
            'name': 'test',
            'template': 'foo',
            'published': 'on',
            'ready_for_review': 'on',
            '_saveasnew': True
        })
        request.user = self.user

        with patch('snippets.base.admin.admin.ModelAdmin.change_view') as change_view_mock:
            self.model_admin.change_view(request, 999)
            change_view_mock.assert_called_with(request, 999, '', None)
            request = change_view_mock.call_args[0][0]
            self.assertTrue('published' not in request.POST)
            self.assertTrue('ready_for_review' not in request.POST)

    def test_normal_save_published(self):
        """Test that normal save doesn't alter 'published' attribute."""
        request = self.factory.post('/', data={
            'name': 'test',
            'template': 'foo',
            'ready_for_review': 'foo',
            'published': 'foo'
        })
        request.user = self.user

        with patch('snippets.base.admin.admin.ModelAdmin.change_view') as change_view_mock:
            self.model_admin.change_view(request, 999)
            change_view_mock.assert_called_with(request, 999, '', None)
            request = change_view_mock.call_args[0][0]
            self.assertEqual(request.POST['published'], 'foo')
            self.assertEqual(request.POST['ready_for_review'], 'foo')


class SnippetTemplateAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = SnippetTemplateAdmin(SnippetTemplate, None)

    def _save_related(self, template):
        """
        Call SnippetTemplateAdmin.save_related for the given template instance.

        :returns:
            A list of the new template variables after save_related was called.
        """
        request = self.factory.post('/url', {})
        ModelForm = self.model_admin.get_form(request)

        form = ModelForm(instance=template)
        form.save_m2m = Mock()  # Called by save_related but unnecessary here.
        self.model_admin.save_related(request, form, [], True)

        return [variable.name for variable in
                SnippetTemplateVariable.objects.filter(template=template)]

    def test_save_related_add_new(self):
        """
        save_related should add new TemplateVariables for any new variables in
        the template code.
        """
        template = SnippetTemplateFactory.create(code="""
            <p>Testing {{ sample_var }}</p>
            {% if not another_test_var %}
              <p>Blah</p>
            {% endif %}
        """)
        variables = self._save_related(template)
        self.assertEqual(len(variables), 2)
        self.assertTrue('sample_var' in variables)
        self.assertTrue('another_test_var' in variables)

    def test_save_related_remove_old(self):
        """
        save_related should delete TemplateVariables that don't exist in the
        saved template anymore.
        """
        template = SnippetTemplateFactory.create(code="""
            <p>Testing {{ sample_var }}</p>
            {% if not another_test_var %}
              <p>Blah</p>
            {% endif %}
        """)
        SnippetTemplateVariableFactory.create(
            name='does_not_exist', template=template)
        SnippetTemplateVariableFactory.create(
            name='does_not_exist_2', template=template)

        self.assertTrue(SnippetTemplateVariable.objects
                        .filter(template=template, name='does_not_exist').exists())
        self.assertTrue(SnippetTemplateVariable.objects
                        .filter(template=template, name='does_not_exist_2').exists())

        variables = self._save_related(template)
        self.assertEqual(len(variables), 2)
        self.assertTrue('sample_var' in variables)
        self.assertTrue('another_test_var' in variables)

        self.assertFalse(SnippetTemplateVariable.objects
                         .filter(template=template, name='does_not_exist').exists())

        self.assertFalse(SnippetTemplateVariable.objects
                         .filter(template=template, name='does_not_exist_2').exists())

    @patch('snippets.base.admin.adminmodels.RESERVED_VARIABLES', ('reserved_name',))
    def test_save_related_reserved_name(self):
        """
        save_related should not add new TemplateVariables for variables that
        are in the RESERVED_VARIABLES list.
        """
        template = SnippetTemplateFactory.create(code="""
            <p>Testing {{ reserved_name }}</p>
            {% if not another_test_var %}
              <p>Blah</p>
            {% endif %}
        """)
        variables = self._save_related(template)
        self.assertEqual(len(variables), 1)
        self.assertTrue('another_test_var' in variables)

        self.assertFalse(SnippetTemplateVariable.objects
                         .filter(template=template, name='reserved_name').exists())


class ASRSnippetAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = ASRSnippetAdmin(ASRSnippet, None)
        self.model_admin.admin_site = Mock()
        self.user = UserFactory()

    def test_save_as_published(self):
        request = self.factory.post('/', data={
            'name': 'test',
            'template': 'foo',
            'status': STATUS_CHOICES['Published'],
            '_saveasnew': True
        })
        request.user = self.user

        with patch('snippets.base.admin.admin.ModelAdmin.change_view') as change_view_mock:
            self.model_admin.change_view(request, 999)
            change_view_mock.assert_called_with(request, 999)
            request = change_view_mock.call_args[0][0]
            self.assertEqual(request.POST['status'], STATUS_CHOICES['Draft'])

    def test_normal_save_published(self):
        """Test that normal save doesn't alter `status` attribute."""
        request = self.factory.post('/', data={
            'name': 'test',
            'template': 'foo',
            'status': STATUS_CHOICES['Published'],
        })
        request.user = self.user

        with patch('snippets.base.admin.admin.ModelAdmin.change_view') as change_view_mock:
            self.model_admin.change_view(request, 999)
            change_view_mock.assert_called_with(request, 999)
            request = change_view_mock.call_args[0][0]
            self.assertEqual(request.POST['status'], str(STATUS_CHOICES['Published']))

    def test_get_readonly_fields(self):
        asrsnippet = ASRSnippetFactory()
        request = self.factory.get('/')
        admin = ASRSnippetAdmin(ASRSnippet, AdminSite())
        request.user = UserFactory

        # No obj
        readonly_fields = admin.get_readonly_fields(request, None)
        self.assertTrue('status' in readonly_fields)

        # With obj
        readonly_fields = admin.get_readonly_fields(request, asrsnippet)
        self.assertTrue('status' not in readonly_fields)


class JobAdminTests(TestCase):
    def test_action_schedule_job(self):
        to_get_scheduled = JobFactory.create_batch(2, status=Job.DRAFT)
        already_scheduled = JobFactory(status=Job.SCHEDULED)
        already_published = JobFactory(status=Job.PUBLISHED)
        cancelled = JobFactory(status=Job.CANCELED)
        completed = JobFactory(status=Job.COMPLETED)
        JobFactory.create_batch(2, status=Job.DRAFT)

        queryset = Job.objects.filter(id__in=[
            to_get_scheduled[0].id,
            to_get_scheduled[1].id,
            already_scheduled.id,
            already_published.id,
            cancelled.id,
            completed.id,
        ])

        request = Mock()
        request.user = UserFactory.create()
        with patch.multiple('snippets.base.admin.adminmodels.messages',
                            warning=DEFAULT_MOCK,
                            success=DEFAULT_MOCK) as message_mocks:
            JobAdmin(Job, None).action_schedule_job(request, queryset)

        self.assertEqual(
            set(Job.objects.filter(status=Job.SCHEDULED)),
            set(to_get_scheduled + [already_scheduled])
        )
        self.assertTrue(message_mocks['warning'].called)
        self.assertTrue(message_mocks['success'].called)

    def test_action_cancel_job(self):
        to_get_canceled = [
            JobFactory.create(status=Job.PUBLISHED),
            JobFactory.create(status=Job.SCHEDULED),
        ]
        already_cancelled = JobFactory(status=Job.CANCELED)
        completed = JobFactory(status=Job.COMPLETED)
        JobFactory.create_batch(2, status=Job.DRAFT)

        queryset = Job.objects.filter(id__in=[
            to_get_canceled[0].id,
            to_get_canceled[1].id,
            already_cancelled.id,
            completed.id,
        ])

        request = Mock()
        request.user = UserFactory.create()
        with patch.multiple('snippets.base.admin.adminmodels.messages',
                            warning=DEFAULT_MOCK,
                            success=DEFAULT_MOCK) as message_mocks:
            JobAdmin(Job, None).action_cancel_job(request, queryset)

        self.assertEqual(
            set(Job.objects.filter(status=Job.CANCELED)),
            set(to_get_canceled + [already_cancelled])
        )
        self.assertTrue(message_mocks['warning'].called)
        self.assertTrue(message_mocks['success'].called)


class DailyMetricsAdminTests(TestCase):
    def test_channel_redash_link(self):
        metrics_admin = DailyChannelMetricsAdmin(
            DailyChannelMetrics, AdminSite())
        metrics = DailyChannelMetrics(date=date(2019, 12, 26))
        html = metrics_admin.redash_link(metrics)
        bq_url = etl.redash_source_url(
            'bq-channel', begin_date=metrics.date, end_date='2019-12-27')
        assert f'href="{bq_url}"' in html
        redshift_url = etl.redash_source_url(
            'redshift-channel', begin_date=metrics.date, end_date=metrics.date)
        assert f'href="{redshift_url}"' in html

    def test_country_redash_link(self):
        metrics_admin = DailyCountryMetricsAdmin(
            DailyCountryMetrics, AdminSite())
        metrics = DailyCountryMetrics(date=date(2019, 12, 26))
        html = metrics_admin.redash_link(metrics)
        bq_url = etl.redash_source_url(
            'bq-country', begin_date=metrics.date, end_date='2019-12-27')
        assert f'href="{bq_url}"' in html
        redshift_url = etl.redash_source_url(
            'redshift-country', begin_date=metrics.date, end_date=metrics.date)
        assert f'href="{redshift_url}"' in html

    def test_Job_redash_link(self):
        metrics_admin = DailyJobMetricsAdmin(
            DailyJobMetrics, AdminSite())
        metrics = DailyJobMetrics(date=date(2019, 12, 26))
        html = metrics_admin.redash_link(metrics)
        bq_url = etl.redash_source_url(
            'bq-message-id', begin_date=metrics.date, end_date='2019-12-27')
        assert f'href="{bq_url}"' in html
        redshift_url = etl.redash_source_url(
            'redshift-message-id', begin_date=metrics.date, end_date=metrics.date)
        assert f'href="{redshift_url}"' in html

    def test_snippet_redash_link(self):
        metrics_admin = DailySnippetMetricsAdmin(
            DailySnippetMetrics, AdminSite())
        metrics = DailySnippetMetrics(date=date(2019, 12, 26))
        html = metrics_admin.redash_link(metrics)
        bq_url = etl.redash_source_url(
            'bq-message-id', begin_date=metrics.date, end_date='2019-12-27')
        assert f'href="{bq_url}"' in html
        redshift_url = etl.redash_source_url(
            'redshift-message-id', begin_date=metrics.date, end_date=metrics.date)
        assert f'href="{redshift_url}"' in html
