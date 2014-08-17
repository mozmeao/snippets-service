from django.test.client import RequestFactory

from nose.tools import eq_

from snippets.base.middleware import SkipMiddleware
from snippets.base.tests import TestCase


class SkipMiddlewareTests(TestCase):
    urls = 'snippets.base.tests.urls'

    def setUp(self):
        self.middleware = SkipMiddleware()
        self.factory = RequestFactory()

    def test_process_request_no_kwargs(self):
        """If the skip_middleware kwarg is missing, return None."""
        request = self.factory.get('test')
        eq_(self.middleware.process_request(request), None)

    def test_process_request_kwargs(self):
        """
        If the skip_middleware kwarg is present, execute the view and
        return the response.
        """
        request = self.factory.get('test_skip')
        eq_(self.middleware.process_request(request), 'skipped')
