from django.contrib.admin.sites import AdminSite
from django.test.client import RequestFactory

from unittest.mock import DEFAULT as DEFAULT_MOCK, Mock, patch

from snippets.base.admin.adminmodels import ASRSnippetAdmin, JobAdmin
from snippets.base.models import STATUS_CHOICES, ASRSnippet, Job
from snippets.base.tests import (ASRSnippetFactory, JobFactory,
                                 TestCase, UserFactory)


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

    def test_action_delete_job(self):
        to_get_deleted = [
            JobFactory.create(status=Job.DRAFT),
            JobFactory.create(status=Job.DRAFT),
        ]
        to_remain = [
            JobFactory(status=Job.CANCELED),
            JobFactory(status=Job.COMPLETED),
            JobFactory(status=Job.PUBLISHED),
        ]
        queryset = Job.objects.filter(id__in=[x.id for x in to_get_deleted + to_remain])

        request = Mock()
        request.user = UserFactory.create()
        with patch.multiple('snippets.base.admin.adminmodels.messages',
                            warning=DEFAULT_MOCK,
                            success=DEFAULT_MOCK) as message_mocks:
            JobAdmin(Job, None).action_delete_job(request, queryset)

        self.assertEqual(
            set(Job.objects.all()),
            set(to_remain)
        )
        self.assertTrue(message_mocks['warning'].called)
        self.assertTrue(message_mocks['success'].called)
