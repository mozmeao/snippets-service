import json

from django.forms import ValidationError

from mock import MagicMock, patch
from nose.tools import assert_raises, eq_, ok_
from pyquery import PyQuery as pq

from snippets.base.forms import IconWidget, TemplateDataWidget, TemplateSelect, UploadedFileAdminForm
from snippets.base.tests import (SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory, TestCase)


class IconWidgetTests(TestCase):
    def test_basic(self):
        with patch('snippets.base.forms.forms.TextInput.render') as render_mock:
            render_mock.return_value = 'original widget code'
            widget = IconWidget()
            rendered_widget = widget.render('iconname', 'iconvalue')
        ok_('original widget code' in rendered_widget)
        d = pq(rendered_widget)
        eq_(d.find('img').attr('src'), 'iconvalue')
        ok_(d.attr('id'), 'iconname')


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
        eq_(blank_option.attr('data-variables'), None)

        # Option 1 should have two variables in the data attribute.
        option1 = d('option:contains("t1")')
        variables = json.loads(option1.attr('data-variables'))
        eq_(len(variables), 2)
        ok_({'name': variable1.name, 'type': variable1.type,
             'description': variable1.description} in variables)
        ok_({'name': variable2.name, 'type': variable2.type,
             'description': variable1.description} in variables)

        # Option 2 should have just one variable.
        option2 = d('option:contains("t2")')
        variables = json.loads(option2.attr('data-variables'))
        eq_(variables, [{'name': variable3.name, 'type': variable3.type,
                         'description': variable3.description}])


class TemplateDataWidgetTests(TestCase):
    def test_basic(self):
        widget = TemplateDataWidget('somename')
        d = pq(widget.render('anothername', None))
        data_widget = d('.template-data-widget')

        eq_(data_widget.attr('data-select-name'), 'somename')
        eq_(data_widget.attr('data-input-name'), 'anothername')


class UploadedFileAdminFormTests(TestCase):
    def test_clean_file(self):
        instance = MagicMock()
        instance.file.name = 'foo.png'
        form = UploadedFileAdminForm(instance=instance)
        file_mock = MagicMock()
        file_mock.name = 'bar.png'
        form.cleaned_data = {'file': file_mock}
        eq_(form.clean_file(), file_mock)

    def test_clean_file_different_extension(self):
        instance = MagicMock()
        instance.file.name = 'foo.png'
        form = UploadedFileAdminForm(instance=instance)
        file_mock = MagicMock()
        file_mock.name = 'bar.pdf'
        form.cleaned_data = {'file': file_mock}
        assert_raises(ValidationError, form.clean_file)
