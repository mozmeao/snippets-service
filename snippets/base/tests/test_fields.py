from django.core.exceptions import ValidationError

from snippets.base.admin.fields import JEXLChoiceField, JEXLRangeField
from snippets.base.tests import TestCase


class JEXLChoiceFieldTests(TestCase):
    def test_to_jexl(self):
        field = JEXLChoiceField('foo')
        self.assertEqual(field.to_jexl(500), 'foo == 500')
        self.assertEqual(field.to_jexl(''), None)


class JEXLRangeFieldTests(TestCase):
    def setUp(self):
        self.field = JEXLRangeField('foo', choices=[('1', '2'), ('3', '4')])

    def test_compress(self):
        self.assertEqual(self.field.compress(data_list=('1', '3')), '1,3')

    def test_validate(self):
        self.assertEqual(self.field.validate('1,3'), '1,3')
        self.assertEqual(self.field.validate('1,1'), '1,1')

    def test_validate_invalid_values(self):
        # Check first subfield
        with self.assertRaises(ValidationError):
            self.field.validate('20,3')

        # Check second subfield
        with self.assertRaises(ValidationError):
            self.field.validate('1,20')

    def test_validate_min_max(self):
        with self.assertRaises(ValidationError):
            self.field.validate('3,1')
