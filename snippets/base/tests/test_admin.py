from django.contrib.auth.models import User
from django.test.client import RequestFactory

from mock import Mock, patch

from snippets.base.admin import SnippetTemplateAdmin
from snippets.base.models import SnippetTemplate, SnippetTemplateVariable
from snippets.base.tests import (SnippetFactory, SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory, TestCase)


class SnippetAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User.objects.create_superuser(username='admin',
                                      email='foo@example.com',
                                      password='admin')
        self.client.login(username='admin', password='admin')

    def test_action_publish_snippet(self):
        snippet = SnippetFactory(published=False)
        self.assertFalse(snippet.published)
        snippet_action_url = '/admin/base/snippet/{}/actions/publish_object/'.format(snippet.pk,)
        self.client.get(snippet_action_url)
        snippet.refresh_from_db()
        self.assertTrue(snippet.published)

    def test_action_unpublish_snippet(self):
        snippet = SnippetFactory(published=True)
        self.assertTrue(snippet.published)
        snippet_action_url = '/admin/base/snippet/{}/actions/unpublish_object/'.format(snippet.pk,)
        self.client.get(snippet_action_url)
        snippet.refresh_from_db()
        self.assertFalse(snippet.published)


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

    @patch('snippets.base.admin.RESERVED_VARIABLES', ('reserved_name',))
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
