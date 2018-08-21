from django.conf import settings


class HostnameMiddleware(object):
    def __init__(self, get_response):
        values = [getattr(settings, x) for x in ['HOSTNAME', 'DEIS_APP', 'DEIS_DOMAIN']]
        self.backend_server = '.'.join(x for x in values if x)
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Backend-Server'] = self.backend_server
        return response
