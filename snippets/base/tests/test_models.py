from django.core.exceptions import ValidationError

from mock import Mock
from nose.tools import assert_raises, eq_, ok_
from pyquery import PyQuery as pq

from snippets.base.models import Client, validate_xml
from snippets.base.tests import (ClientMatchRuleFactory, SnippetFactory,
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


class SnippetTemplateTests(TestCase):
    def test_render(self):
        template = SnippetTemplateFactory(code='<p>{{myvar}}</p>')
        eq_(template.render({'myvar': 'foo'}), '<p>foo</p>')


class SnippetTests(TestCase):
    def test_render(self):
        template = SnippetTemplateFactory.create()
        template.render = Mock()
        template.render.return_value = '<a href="asdf">qwer</a>'

        data = '{"url": "asdf", "text": "qwer"}'
        snippet = SnippetFactory.create(template=template, data=data,
                                        country='us')

        expected = ('<div data-snippet-id="{0}" data-country="us">'
                    '<a href="asdf">qwer</a></div>'.format(snippet.id))
        eq_(snippet.render().strip(), expected)
        template.render.assert_called_with({'url': 'asdf', 'text': 'qwer'})

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

        expected = ('<div data-snippet-id="{0}"><a href="asdf">qwer</a></div>'
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
