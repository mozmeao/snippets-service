from django.http import HttpResponse

from snippets.base.decorators import access_control
from snippets.base.tests import TestCase


class AccessControlTests(TestCase):
    def test_basic(self):
        @access_control(origin='DENY', max_age=64, methods=('DELETE', 'PUT'))
        def test_view():
            return HttpResponse()

        response = test_view()
        self.assertEqual(response['Access-Control-Allow-Origin'], 'DENY')
        self.assertEqual(response['Access-Control-Max-Age'], '64')
        self.assertEqual(response['Access-Control-Allow-Methods'], 'DELETE, PUT')
