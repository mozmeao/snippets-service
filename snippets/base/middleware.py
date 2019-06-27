from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.core.validators import validate_ipv4_address, ValidationError
from django.http.request import split_domain_port
from django.urls import Resolver404, resolve

from enforce_host import EnforceHostMiddleware

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
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            result = resolve(request.path)
        except Resolver404:
            # If we cannot resolve, continue with the next middleware.
            return self.get_response(request)

        if result.func in (fetch_snippets,):
            return result.func(request, *result.args, **result.kwargs)

        return self.get_response(request)


class HostnameMiddleware(object):
    def __init__(self, get_response):
        if not settings.ENABLE_HOSTNAME_MIDDLEWARE:
            raise MiddlewareNotUsed

        values = [getattr(settings, x) for x in [
                    'CLUSTER_NAME', 'K8S_NAMESPACE', 'K8S_POD_NAME']]
        self.backend_server = '/'.join(x for x in values if x)
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Backend-Server'] = self.backend_server
        return response


# Direct copy from kitsune.sumo.middleware
class EnforceHostIPMiddleware(EnforceHostMiddleware):
    """Modify the `EnforceHostMiddleware` to allow IP addresses"""
    def process_request(self, request):
        host = request.get_host()
        domain, port = split_domain_port(host)
        try:
            validate_ipv4_address(domain)
        except ValidationError:
            # not an IP address. Call the superclass
            return super(EnforceHostIPMiddleware, self).process_request(request)

        # it is an IP address
        return
