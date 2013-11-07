from django.core.urlresolvers import resolve

from snippets.base.views import fetch_snippets


class FetchSnippetsMiddleware(object):
    """
    If the incoming request is for the fetch_snippets view, execute the view
    and return it before other middleware can run.

    fetch_snippets is a very very basic view that doesn't need any of the
    middleware that the rest of the site needs, such as the session or csrf
    middlewares. To avoid unintended issues (such as headers we don't want
    being added to the response) this middleware detects requests to that view
    and executes the view early, bypassing the rest of the middleware.

    Also disables New Relic's apdex for views that aren't the
    fetch_snippets, as we only really care about the apdex for
    fetch_snippets.
    """
    def process_request(self, request):
        result = resolve(request.path)
        if result.func == fetch_snippets:
            return fetch_snippets(request, *result.args, **result.kwargs)
        else:
            # Not fetch_snippets? Then no New Relic for you!
            try:
                import newrelic.agent
            except ImportError:
                pass
            else:
                newrelic.agent.suppress_apdex_metric()
