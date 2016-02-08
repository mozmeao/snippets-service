from django.core.exceptions import ValidationError

from snippets.base.fields import validate_regex
from snippets.base.tests import TestCase


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
