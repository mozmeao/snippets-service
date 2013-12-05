from django.core.urlresolvers import resolve

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
        result = resolve(request.path)
        if result.func in (fetch_snippets, fetch_json_snippets):
            return result.func(request, *result.args, **result.kwargs)
