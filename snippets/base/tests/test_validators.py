import io
import json
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile

from PIL import Image

from snippets.base.validators import (validate_as_router_fluent_variables,
                                      validate_xml_template, validate_xml_variables,
                                      validate_regex, validate_image_format,
                                      validate_json_data)
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
        data = json.dumps({'text': 'Link to <a href="https://example.com">example.com</a>.',
                           'foo': 'This is <strong>important</strong>',
                           'special': 'This is <a href="special:accounts">special link</a>.',
                           'bar': 'This is not rich text.'})
        self.assertEqual(validate_as_router_fluent_variables(data, ['text', 'foo']), data)

    @patch('snippets.base.validators.ALLOWED_TAGS', 'a')
    def test_invalid_tag(self):
        data = json.dumps({'text': '<strong>Strong</strong> text.'})
        self.assertRaises(ValidationError, validate_as_router_fluent_variables, data, ['text'])

    def test_invalid_protocol(self):
        data = json.dumps({'text': '<a href="http://example.com">Strong</strong> text.'})
        self.assertRaises(ValidationError, validate_as_router_fluent_variables, data, ['text'])


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


class ImageFormatValidatorTests(TestCase):
    def test_valid_image_png(self):
        img = Image.new('RGB', (30, 30), color='red')
        fle = io.BytesIO()
        img.save(fle, 'PNG')
        image = InMemoryUploadedFile(fle, 'ImageField', 'foo.png', 'image/png', None, None)

        self.assertEqual(validate_image_format(image), image)

    def test_invalid_image(self):
        img = Image.new('RGB', (30, 30), color='red')
        fle = io.BytesIO()
        img.save(fle, 'JPEG')
        image = InMemoryUploadedFile(fle, 'ImageField', 'foo.jpg', 'image/jpeg', None, None)

        self.assertRaises(ValidationError, validate_image_format, image)


class ValidateJSONDataTests(TestCase):
    def test_base(self):
        data = '{"foo": 3}'
        self.assertEqual(validate_json_data(data), data)

    def test_invalid_data(self):
        data = '{"foo": 3'
        self.assertRaises(ValidationError, validate_json_data, data)
