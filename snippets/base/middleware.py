from django.core.urlresolvers import resolve


class SkipMiddleware(object):
    """
    If the incoming request is for a view that has the skip_middleware
    kwarg, execute the view and return the response before other
    middleware can run.

    Allows views like the FetchSnippets view to bypass unnecessary
    middleware.
    """
    def process_request(self, request):
        result = resolve(request.path)
        if result.kwargs.pop('skip_middleware', False):
            return result.func(request, *result.args, **result.kwargs)
