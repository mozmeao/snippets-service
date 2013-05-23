import json

from nose.tools import eq_, ok_
from pyquery import PyQuery as pq

from snippets.base.forms import TemplateDataWidget, TemplateSelect
from snippets.base.tests import (SnippetTemplateFactory,
                                 SnippetTemplateVariableFactory, TestCase)


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
        ok_({'name': variable1.name, 'type': variable1.type} in variables)
        ok_({'name': variable2.name, 'type': variable2.type} in variables)

        # Option 2 should have just one variable.
        option2 = d('option:contains("t2")')
        variables = json.loads(option2.attr('data-variables'))
        eq_(variables, [{'name': variable3.name, 'type': variable3.type}])


class TemplateDataWidgetTests(TestCase):
    def test_basic(self):
        widget = TemplateDataWidget('somename')
        d = pq(widget.render('anothername', None))
        data_widget = d('.template-data-widget')

        eq_(data_widget.attr('data-select-name'), 'somename')
        eq_(data_widget.attr('data-input-name'), 'anothername')
