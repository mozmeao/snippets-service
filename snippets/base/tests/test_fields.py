from snippets.base.admin.fields import JEXLChoiceField
from snippets.base.tests import TestCase


class JEXLChoiceFieldTests(TestCase):
    def test_to_jexl(self):
        field = JEXLChoiceField('foo')
        self.assertEqual(field.to_jexl(500), 'foo == 500')
        self.assertEqual(field.to_jexl(''), None)
