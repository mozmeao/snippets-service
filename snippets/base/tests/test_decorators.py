from django.http import HttpResponse

from nose.tools import eq_

from snippets.base.decorators import access_control
from snippets.base.tests import TestCase


class AccessControlTests(TestCase):
    def test_basic(self):
        @access_control(origin='DENY', max_age=64, methods=('DELETE', 'PUT'))
        def test_view():
            return HttpResponse()

        response = test_view()
        eq_(response['Access-Control-Allow-Origin'], 'DENY')
        eq_(response['Access-Control-Max-Age'], '64')
        eq_(response['Access-Control-Allow-Methods'], 'DELETE, PUT')
