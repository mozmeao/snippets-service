from django.conf import settings
from django.core.urlresolvers import Resolver404, resolve

from snippets.base.views import fetch_json_snippets, fetch_snippets


class FetchSnippetsMiddleware(object):
    """
    If the incoming request is for the fetch_snippets view, execute the view
    and return it before other middleware can run.

    fetch_snippets is a very very basic view that doesn't need any of the
    middleware that the rest of the site needs, such as the session or csrf
    middlewares. To avoid unintended issues (such as headers we don't want
    being added to the response) this middleware detects requests to that view
    and executes the view early, bypassing the rest of the middleware.
    """
    def process_request(self, request):
        try:
            result = resolve(request.path)
        except Resolver404:
            return

        if result.func in (fetch_snippets, fetch_json_snippets):
            return result.func(request, *result.args, **result.kwargs)


class HostnameMiddleware(object):
    def __init__(self):
        values = [getattr(settings, x) for x in ['HOSTNAME', 'DEIS_APP', 'DEIS_DOMAIN']]
        self.backend_server = '.'.join(x for x in values if x)

    def process_response(self, request, response):
        response['X-Backend-Server'] = self.backend_server
        return response
