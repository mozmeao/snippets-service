from snippets.base.forms import TargetAdminForm
from snippets.base.tests import TestCase, TargetFactory


class TargetAdminFormTests(TestCase):
    def setUp(self):
        self.data = {
            'name': 'foo-target',
            'filtr_is_default_browser': 'true',
        }

    def test_save(self):
        data = self.data.copy()
        instance = TargetFactory()
        form = TargetAdminForm(data, instance=instance)

        self.assertTrue(form.is_valid())
        form.save()
        instance.refresh_from_db()
        self.assertEqual(instance.jexl_expr, 'isDefaultBrowser == true')
        self.assertTrue(instance.filtr_is_default_browser)
