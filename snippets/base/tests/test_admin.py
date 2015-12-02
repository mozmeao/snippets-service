from django.forms import ModelForm
from django.test.client import RequestFactory

from mock import Mock, patch

from snippets.base.admin import SnippetAdmin, SnippetTemplateAdmin
from snippets.base.forms import SnippetAdminForm
from snippets.base.models import (Snippet, SnippetLocale, SnippetTemplate,
                                  SnippetTemplateVariable)
from snippets.base.tests import (SnippetFactory, SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory, TestCase)


class SnippetAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = SnippetAdmin(Snippet, None)
        self.model_admin.admin_site = Mock()

    def _save_model(self, snippet, form):
        """Call SnippetAdmin.save_model for the given snippet instance."""
        request = self.factory.post('/url', {})
        form.is_valid()  # Generate cleaned_data.
        self.model_admin.save_model(request, snippet, form, True)

    def test_save_model_locales(self):
        """
        save_model should delete any locales that were removed from the snippet
        and save any locales that were added.
        """
        en_us = SnippetLocale(locale='en-us')
        fr = SnippetLocale(locale='fr')
        snippet = SnippetFactory.create(locale_set=[en_us, fr])
        data = {
            'name': 'test',
            'data': '{}',
            'template': snippet.template.id,
            'locales': ['en-us', 'de'],
            'priority': 0,
            'weight': 100,
        }

        form = SnippetAdminForm(data, instance=snippet)
        self._save_model(snippet, form)

        snippet = Snippet.objects.get(pk=snippet.pk)
        locales = (l.locale for l in snippet.locale_set.all())
        self.assertEqual(set(locales), set(('en-us', 'de')))

    def test_no_locales(self):
        """
        If the form being saved has no locale field, do not alter the snippet's
        locale.
        """
        en_us = SnippetLocale(locale='en-us')
        fr = SnippetLocale(locale='fr')
        snippet = SnippetFactory.create(locale_set=[en_us, fr])
        data = {
            'name': 'test',
            'data': '{}',
            'template': snippet.template.id,
            'priority': 0,
            'weight': 100,
        }

        # FormClass has no locale field.
        class FormClass(ModelForm):
            class Meta:
                model = Snippet
        form = FormClass(data, instance=snippet)
        self._save_model(snippet, form)

        snippet = Snippet.objects.get(pk=snippet.pk)
        locales = (l.locale for l in snippet.locale_set.all())
        self.assertEqual(set(locales), set(('en-us', 'fr')))

    def test_save_as_disabled(self):
        request = self.factory.post('/', data={
            'name': 'test',
            'template': 'foo',
            'disabled': u'off',
            '_saveasnew': True
        })

        with patch('snippets.base.admin.BaseModelAdmin.change_view') as change_view_mock:
            self.model_admin.change_view(request, 999)
            change_view_mock.assert_called_with(request, 999)
            request = change_view_mock.call_args[0][0]
            self.assertEqual(request.POST['disabled'], u'on')

    def test_normal_save_disabled(self):
        """Test that normal save doesn't alter 'disabled' attribute."""
        request = self.factory.post('/', data={
            'name': 'test',
            'template': 'foo',
            'disabled': u'foo'
        })

        with patch('snippets.base.admin.BaseModelAdmin.change_view') as change_view_mock:
            self.model_admin.change_view(request, 999)
            change_view_mock.assert_called_with(request, 999)
            request = change_view_mock.call_args[0][0]
            self.assertEqual(request.POST['disabled'], u'foo')


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
        self.assertTrue(SnippetTemplateVariable.objects
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
