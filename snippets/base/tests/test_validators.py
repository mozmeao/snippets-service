from unittest.mock import patch

from django.core.exceptions import ValidationError

from snippets.base import models
from snippets.base.validators import (validate_as_router_fluent_variables,
                                      validate_json_data, validate_regex)
from snippets.base.tests import TestCase


class ASRouterFluentVariablesValidatorTests(TestCase):
    @patch('snippets.base.validators.ALLOWED_TAGS', ['a', 'strong'])
    def test_valid(self):
        obj = models.SimpleTemplate(
            text='Link to <a href="https://example.com">example.com</a>.',
            title='This is important',
        )
        self.assertEqual(validate_as_router_fluent_variables(obj, ['text', 'title']), obj)

    @patch('snippets.base.validators.ALLOWED_TAGS', 'a')
    def test_invalid_tag(self):
        obj = models.SimpleTemplate(
            text='<strong>Strong</strong> text.',
        )
        self.assertRaises(ValidationError, validate_as_router_fluent_variables, obj, ['text'])

    def test_invalid_protocol(self):
        obj = models.SimpleTemplate(
            text='<a href="http://example.com">Strong</strong> text.',
        )
        self.assertRaises(ValidationError, validate_as_router_fluent_variables, obj, ['text'])


class RegexValidatorTests(TestCase):
    def test_valid_string(self):
        valid_string = 'foobar'
        self.assertEqual(validate_regex(valid_string), valid_string)

    def test_valid_regex(self):
        valid_regex = r'/\d+/'
        self.assertEqual(validate_regex(valid_regex), valid_regex)

    def test_invalid_regex(self):
        bogus_regex = r'/(?P\d+)/'
        self.assertRaises(ValidationError, validate_regex, bogus_regex)


class ValidateJSONDataTests(TestCase):
    def test_base(self):
        data = '{"foo": 3}'
        self.assertEqual(validate_json_data(data), data)

    def test_invalid_data(self):
        data = '{"foo": 3'
        self.assertRaises(ValidationError, validate_json_data, data)
