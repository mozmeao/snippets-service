import json

from django.contrib.auth.models import User, Permission

from unittest.mock import Mock, patch
from pyquery import PyQuery as pq

from snippets.base.forms import (ASRSnippetAdminForm, IconWidget,
                                 SnippetAdminForm, TargetAdminForm,
                                 TemplateDataWidget, TemplateSelect)
from snippets.base.models import STATUS_CHOICES
from snippets.base.tests import (ASRSnippetFactory, SnippetFactory,
                                 SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory, TestCase,
                                 TargetFactory)


class IconWidgetTests(TestCase):
    def test_basic(self):
        with patch('snippets.base.forms.forms.TextInput.render') as render_mock:
            render_mock.return_value = 'original widget code'
            widget = IconWidget()
            rendered_widget = widget.render('iconname', 'iconvalue')
        self.assertTrue('original widget code' in rendered_widget)
        d = pq(rendered_widget)
        self.assertEqual(d.find('img').attr('src'), 'iconvalue')
        self.assertTrue(d.attr('id'), 'iconname')


class TemplateSelectTests(TestCase):
    def test_basic(self):
        variable1 = SnippetTemplateVariableFactory()
        variable2 = SnippetTemplateVariableFactory()
        template1 = SnippetTemplateFactory.create(
            variable_set=[variable1, variable2])

        variable3 = SnippetTemplateVariableFactory()
        template2 = SnippetTemplateFactory.create(variable_set=[variable3])

        choices = (('', 'blank'), (template1.pk, 't1'), (template2.pk, 't2'))
        widget = TemplateSelect(choices=choices)
        d = pq(widget.render('blah', None))

        # Blank option should have no data attributes.
        blank_option = d('option:contains("blank")')
        self.assertEqual(blank_option.attr('data-variables'), None)

        # Option 1 should have two variables in the data attribute.
        option1 = d('option:contains("t1")')
        variables = json.loads(option1.attr('data-variables'))
        self.assertEqual(len(variables), 2)

        self.assertTrue({'name': variable1.name, 'type': variable1.type, 'order': variable1.order,
                         'description': variable1.description} in variables)
        self.assertTrue({'name': variable2.name, 'type': variable2.type, 'order': variable2.order,
                         'description': variable1.description} in variables)

        # Option 2 should have just one variable.
        option2 = d('option:contains("t2")')
        variables = json.loads(option2.attr('data-variables'))
        self.assertEqual(variables, [{'name': variable3.name,
                                      'type': variable3.type,
                                      'order': variable3.order,
                                      'description': variable3.description}])


class SnippetAdminFormTests(TestCase):
    def setUp(self):
        template = SnippetTemplateFactory()
        self.data = {
            'name': 'Test Snippet',
            'template': template.id,
            'client_option_version_lower_bound': 'any',
            'client_option_version_upper_bound': 'any',
            'client_option_is_developer': 'any',
            'client_option_is_default_browser': 'any',
            'client_option_screen_resolutions': ['0-1024', '1024-1920', '1920-50000'],
            'client_option_has_fxaccount': 'any',
            'client_option_sessionage_lower_bound': -1,
            'client_option_sessionage_upper_bound': -1,
            'client_option_profileage_lower_bound': -1,
            'client_option_profileage_upper_bound': -1,
            'client_option_bookmarks_count_lower_bound': -1,
            'client_option_bookmarks_count_upper_bound': -1,
            'client_option_addon_check_type': 'any',
            'data': '{}',
            'weight': 100,
            'on_release': 'on',
        }

    def test_no_xml_validation_for_startpage_5(self):
        data = self.data.copy()
        data.update({
            'on_startpage_5': 'on',
        })
        with patch('snippets.base.validators.validate_xml_variables') as validate_mock:
            form = SnippetAdminForm(data)
            self.assertTrue(form.is_valid())
        self.assertTrue(not validate_mock.called)

    def test_xml_validation_for_startpage_4(self):
        data = self.data.copy()
        data.update({
            'on_startpage_4': 'on',
        })
        with patch('snippets.base.forms.validate_xml_variables') as validate_mock:
            form = SnippetAdminForm(data)
            self.assertTrue(form.is_valid())
        self.assertTrue(validate_mock.called)

    def test_permission_check_called(self):
        data = self.data.copy()
        data.update({
            'on_startpage_5': 'on',
        })
        form = SnippetAdminForm(data)
        check_mock = Mock()
        form._publish_permission_check = check_mock
        form.full_clean()
        self.assertTrue(check_mock.called)


class TemplateDataWidgetTests(TestCase):
    def test_basic(self):
        widget = TemplateDataWidget('somename')
        d = pq(widget.render('anothername', None))
        data_widget = d('.template-data-widget')

        self.assertEqual(data_widget.attr('data-select-name'), 'somename')
        self.assertEqual(data_widget.attr('data-input-name'), 'anothername')


class BaseSnippetAdminFormTests(TestCase):
    def test_publish_permission_check(self):
        variable1 = SnippetTemplateVariableFactory()
        variable2 = SnippetTemplateVariableFactory()
        self.template1 = SnippetTemplateFactory.create(
            variable_set=[variable1, variable2])
        user = User.objects.create_user(username='admin',
                                        email='foo@example.com',
                                        password='admin')

        perm_beta = Permission.objects.get(
            codename='can_publish_on_beta',
            content_type__model='snippet'
        )
        user.user_permissions.add(perm_beta)

        perm_nightly = Permission.objects.get(
            codename='can_publish_on_nightly',
            content_type__model='snippet'
        )
        user.user_permissions.add(perm_nightly)

        data = {
            'name': 'Test',
            'weight': 100,
            'client_option_is_developer': 'any',
            'client_option_addon_check_type': 'any',
            'client_option_sessionage_lower_bound': -1,
            'client_option_sessionage_upper_bound': -1,
            'client_option_profileage_lower_bound': -1,
            'client_option_profileage_upper_bound': -1,
            'client_option_bookmarks_count_lower_bound': -1,
            'client_option_bookmarks_count_upper_bound': -1,
            'client_option_version_lower_bound': 'any',
            'client_option_version_upper_bound': 'any',
            'client_option_is_default_browser': 'any',
            'client_option_has_fxaccount': 'any',
            'client_option_screen_resolutions': ['0-1024'],
            'on_startpage_5': True,
            'template': self.template1.id,
            'data': '{}',
        }

        # User should get an error trying to publish on Release
        new_data = data.copy()
        new_data['published'] = True
        new_data['on_release'] = True
        form = SnippetAdminForm(new_data)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])

        # User should get an error trying to edit or publish  on Release even though Beta
        # is selected too.
        new_data = data.copy()
        new_data['published'] = True
        new_data['on_release'] = True
        new_data['on_beta'] = True
        form = SnippetAdminForm(new_data)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])

        # Form is valid if user tries to edit or publish on Beta.
        new_data = data.copy()
        new_data['published'] = True
        new_data['on_beta'] = True
        form = SnippetAdminForm(new_data)
        form.current_user = user
        self.assertTrue(form.is_valid())

        # Form is valid if user tries to publish or edit on Beta and Nightly.
        new_data = data.copy()
        new_data['published'] = True
        new_data['on_beta'] = True
        new_data['on_nightly'] = True
        form = SnippetAdminForm(new_data)
        form.current_user = user
        self.assertTrue(form.is_valid())

        # Form is invalid if user tries edit published Snippet on Release.
        instance = SnippetFactory.create(published=True, on_release=True)
        new_data = data.copy()
        new_data['on_release'] = True
        new_data['on_beta'] = True
        new_data['on_nightly'] = True
        form = SnippetAdminForm(new_data, instance=instance)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])

        # User cannot unset Release channel and save.
        instance = SnippetFactory.create(published=True, on_release=True)
        new_data = data.copy()
        new_data['on_release'] = False
        new_data['on_beta'] = True
        new_data['on_nightly'] = True
        form = SnippetAdminForm(new_data, instance=instance)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])

        # User can un-publish if they have permission on all channels.
        instance = SnippetFactory.create(published=True, on_release=False, on_beta=True,
                                         on_nightly=True)
        new_data = data.copy()
        new_data['published'] = False
        new_data['on_beta'] = True
        new_data['on_nightly'] = True
        form = SnippetAdminForm(new_data, instance=instance)
        form.current_user = user
        self.assertTrue(form.is_valid())

        # User cannot un-publish if they don't have permission on all channels.
        instance = SnippetFactory.create(published=True, on_release=True, on_nightly=True)
        new_data = data.copy()
        new_data['on_release'] = True
        new_data['on_nightly'] = True
        new_data['published'] = False
        form = SnippetAdminForm(new_data, instance=instance)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])


class ASRSnippetAdminFormTests(TestCase):
    def test_publish_permission_check_asr(self):
        user = User.objects.create_user(username='admin',
                                        email='foo@example.com',
                                        password='admin')

        perm_beta = Permission.objects.get(
            codename='publish_on_beta',
            content_type__model='asrsnippet'
        )
        user.user_permissions.add(perm_beta)

        perm_nightly = Permission.objects.get(
            codename='publish_on_nightly',
            content_type__model='asrsnippet'
        )
        user.user_permissions.add(perm_nightly)

        target_release = TargetFactory(
            on_release=True, on_beta=False, on_esr=False, on_nightly=False, on_aurora=False)

        target_beta = TargetFactory(
            on_release=False, on_beta=True, on_esr=False, on_nightly=False, on_aurora=False)

        target_nightly = TargetFactory(
            on_release=False, on_beta=False, on_esr=False, on_nightly=True, on_aurora=False)

        asrsnippet = ASRSnippetFactory(targets=[])

        data = {
            'name': 'Test',
            'weight': 100,
            'template': asrsnippet.template.id,
            'data': '{}',
        }

        # User should get an error trying to publish on Release
        new_data = data.copy()
        new_data['status'] = STATUS_CHOICES['Published']
        new_data['targets'] = [target_release]
        form = ASRSnippetAdminForm(new_data, instance=asrsnippet)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])

        # User should get an error trying to edit or publish on Release even though Beta
        # is selected too.
        new_data = data.copy()
        new_data['status'] = STATUS_CHOICES['Published']
        new_data['targets'] = [
            target_release,
            target_beta
        ]
        form = ASRSnippetAdminForm(new_data, instance=asrsnippet)
        form.current_user = user

        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])

        # Form is valid if user tries to edit or publish on Beta.
        new_data = data.copy()
        new_data['status'] = STATUS_CHOICES['Published']
        new_data['targets'] = [target_beta]
        form = ASRSnippetAdminForm(new_data, instance=asrsnippet)
        form.current_user = user
        self.assertTrue(form.is_valid())

        # Form is valid if user tries to publish or edit on Beta and Nightly.
        new_data = data.copy()
        new_data['status'] = STATUS_CHOICES['Published']
        new_data['targets'] = [
            target_beta,
            target_nightly
        ]
        form = ASRSnippetAdminForm(new_data, instance=asrsnippet)
        form.current_user = user
        self.assertTrue(form.is_valid())

        # Form is invalid if user tries edit published Snippet on Release.
        instance = ASRSnippetFactory.create(
            status=STATUS_CHOICES['Published'], targets=[TargetFactory(on_release=True)]
        )
        new_data = data.copy()
        new_data['targets'] = [
            target_release,
            target_beta,
            target_nightly
        ]
        form = ASRSnippetAdminForm(new_data, instance=instance)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])

        # User cannot unset Release channel and save.
        instance = ASRSnippetFactory.create(
            status=STATUS_CHOICES['Published'],
            targets=[TargetFactory(on_release=True)])
        new_data = data.copy()
        new_data['targets'] = [
            target_beta,
            target_nightly
        ]
        form = ASRSnippetAdminForm(new_data, instance=instance)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])

        # User can un-publish if they have permission on all channels.
        instance = ASRSnippetFactory.create(
            status=STATUS_CHOICES['Published'],
            targets=[TargetFactory(on_release=False, on_beta=True, on_nightly=True)])
        new_data = data.copy()
        new_data['status'] = STATUS_CHOICES['Approved']
        new_data['targets'] = [
            target_beta,
            target_nightly
        ]
        form = ASRSnippetAdminForm(new_data, instance=instance)
        form.current_user = user
        self.assertTrue(form.is_valid())

        # User cannot un-publish if they don't have permission on all channels.
        instance = ASRSnippetFactory.create(
            status=STATUS_CHOICES['Published'],
            targets=[TargetFactory(on_release=True, on_nightly=True)])
        new_data = data.copy()
        new_data['status'] = STATUS_CHOICES['Approved']
        new_data['targets'] = [
            target_release,
            target_nightly
        ]
        form = ASRSnippetAdminForm(new_data, instance=instance)
        form.current_user = user
        self.assertFalse(form.is_valid())
        self.assertTrue('You are not allowed to edit or publish on Release channel.' in
                        form.errors['__all__'][0])


class TargetAdminFormTests(TestCase):
    def setUp(self):
        self.data = {
            'name': 'foo-target',
            'filtr_is_default_browser': 'true',
        }

    def test_set_initial_jexl(self):
        data = self.data.copy()
        instance = TargetFactory(jexl={'filtr_is_default_browser': 'false'})
        form = TargetAdminForm(data, instance=instance)
        self.assertEqual(form.fields['filtr_is_default_browser'].initial, 'false')

    def test_save(self):
        data = self.data.copy()
        instance = TargetFactory()
        form = TargetAdminForm(data, instance=instance)

        self.assertTrue(form.is_valid())
        form.save()
        instance.refresh_from_db()
        self.assertEqual(instance.jexl_expr, 'isDefaultBrowser == true')
        self.assertEqual(instance.jexl, {
            'filtr_is_default_browser': 'true',
        })
