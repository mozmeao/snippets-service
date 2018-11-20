from unittest.mock import DEFAULT, patch

from django.core.exceptions import ValidationError

from snippets.base.admin.fields import (JEXLAddonField, JEXLChoiceField, JEXLFirefoxRangeField,
                                        JEXLRangeField)
from snippets.base.tests import AddonFactory, TestCase


class JEXLChoiceFieldTests(TestCase):
    def test_to_jexl(self):
        field = JEXLChoiceField('foo')
        self.assertEqual(field.to_jexl(500), 'foo == 500')
        self.assertEqual(field.to_jexl(''), None)

    def test_custom_jexl(self):
        field = JEXLChoiceField('foo', jexl='{value} != {attr_name}')
        self.assertEqual(field.to_jexl(500), '500 != foo')
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

    def test_custom_jexl(self):
        field = JEXLChoiceField('foo', jexl='{value} != {attr_name}')
        self.assertEqual(field.to_jexl(500), '500 != foo')
        self.assertEqual(field.to_jexl(''), None)

    def test_to_jexl(self):
        expected_output = '1 <= foo && foo < 3'
        generated_output = self.field.to_jexl('1,3')
        self.assertEqual(expected_output, generated_output)


class JEXLAddonFieldTests(TestCase):
    def setUp(self):
        self.field = JEXLAddonField()
        self.addon = AddonFactory()

    def test_compress(self):
        self.assertEqual(self.field.compress(data_list=[]), '')
        self.assertEqual(self.field.compress(data_list=['installed', self.addon]),
                         'installed,{}'.format(self.addon.id))

    def test_to_jexl(self):
        guid = self.addon.guid

        value = 'installed,{}'.format(self.addon.id)
        self.assertEqual(self.field.to_jexl(value),
                         '("{}" in addonsInfo.addons|keys) == true'.format(guid))

        value = 'not_installed,{}'.format(self.addon.id)
        self.assertEqual(self.field.to_jexl(value),
                         '("{}" in addonsInfo.addons|keys) == false'.format(guid))

        value = ','
        self.assertEqual(self.field.to_jexl(value), '')

        value = 'installed,'
        self.assertEqual(self.field.to_jexl(value), '')

        value = ',3'
        self.assertEqual(self.field.to_jexl(value), '')

    def test_validate(self):
        with patch.multiple('snippets.base.admin.fields',
                            ChoiceField=DEFAULT, ModelChoiceField=DEFAULT):
            field = JEXLAddonField()
            field.validate('installed,{}'.format(self.addon.id))

        field.fields[0].validate.assert_called_with('installed')
        field.fields[1].validate.assert_called_with(str(self.addon.id))

    def test_validate_no_selection(self):
        self.assertEqual(self.field.validate(','), ',')

    def test_validate_no_addon(self):
        with self.assertRaises(ValidationError):
            self.field.validate('installed,')

    def test_validate_no_action(self):
        with self.assertRaises(ValidationError):
            self.field.validate(',3')


class JEXLFirefoxRangeFieldTests(TestCase):
    def setUp(self):
        with patch('snippets.base.admin.fields.product_details') as product_details:
            product_details.firefox_versions = {
                'FIREFOX_NIGHTLY': '67.0'
            }
            self.field = JEXLFirefoxRangeField()

    def test_validate(self):
        self.assertEqual(self.field.validate('64,65'), '64,65')
        self.assertEqual(self.field.validate('64,64'), '64,64')

    def test_validate_invalid_values(self):
        # Check first subfield
        with self.assertRaises(ValidationError):
            self.field.validate('20.0,60.0')

        # Check second subfield
        with self.assertRaises(ValidationError):
            self.field.validate('57.0,20.0')

    def test_validate_min_max(self):
        with self.assertRaises(ValidationError):
            self.field.validate('60.0,57.0')
