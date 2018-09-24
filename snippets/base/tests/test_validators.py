import json
from mock import patch

from django.core.exceptions import ValidationError

from snippets.base.validators import (validate_as_router_fluent_variables,
                                      validate_xml_template, validate_xml_variables,
                                      validate_regex)
from snippets.base.tests import TestCase


class XMLVariablesValidatorTests(TestCase):
    def test_valid_xml(self):
        valid_xml = '{"foo": "<b>foobar</b>"}'
        self.assertEqual(validate_xml_variables(valid_xml), valid_xml)

    def test_invalid_xml(self):
        invalid_xml = '{"foo": "<b><i>foobar<i></b>"}'
        self.assertRaises(ValidationError, validate_xml_variables, invalid_xml)

    def test_unicode(self):
        unicode_xml = '{"foo": "<b>\u03c6\u03bf\u03bf</b>"}'
        self.assertEqual(validate_xml_variables(unicode_xml), unicode_xml)

    def test_non_string_values(self):
        """
        If a value isn't a string, skip over it and continue validating.
        """
        valid_xml = '{"foo": "<b>Bar</b>", "baz": true}'
        self.assertEqual(validate_xml_variables(valid_xml), valid_xml)


class XMLTemplateValidatorTests(TestCase):
    def test_valid_xml(self):
        valid_xml = '<div>yo</div>'
        self.assertEqual(validate_xml_template(valid_xml), valid_xml)

    def test_unicode(self):
        valid_xml = '<div><b>\u03c6\u03bf\u03bf</b></div>'
        self.assertEqual(validate_xml_template(valid_xml), valid_xml)

    def test_invalid_xml(self):
        invalid_xml = '<div><input type="text" name="foo"></div>'
        self.assertRaises(ValidationError, validate_xml_template, invalid_xml)


class ASRouterFluentVariablesValidatorTests(TestCase):
    @patch('snippets.base.validators.ALLOWED_TAGS', ['a', 'strong'])
    def test_valid(self):
        data = json.dumps({'text': 'Link to <a href="http://example.com">example.com</a>.',
                           'foo': 'This is <strong>important</strong>',
                           'bar': 'This is not rich text.'})
        self.assertEqual(validate_as_router_fluent_variables(data, ['text', 'foo']), data)

    @patch('snippets.base.validators.ALLOWED_TAGS', 'a')
    def test_invalid(self):
        data = json.dumps({'text': '<strong>Strong</strong> text.'})
        self.assertRaises(ValidationError, validate_as_router_fluent_variables, data, ['text'])


class RegexValidatorTests(TestCase):
    def test_valid_string(self):
        valid_string = 'foobar'
        self.assertEqual(validate_regex(valid_string), valid_string)

    def test_valid_regex(self):
        valid_regex = '/\d+/'
        self.assertEqual(validate_regex(valid_regex), valid_regex)

    def test_invalid_regex(self):
        bogus_regex = '/(?P\d+)/'
        self.assertRaises(ValidationError, validate_regex, bogus_regex)
