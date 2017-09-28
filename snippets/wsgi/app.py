"""
WSGI config for snippets project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'snippets.settings')  # NOQA

from django.core.handlers.wsgi import WSGIRequest
from django.core.wsgi import get_wsgi_application

import newrelic.agent
from decouple import config
from raven.contrib.django.raven_compat.middleware.wsgi import Sentry


IS_HTTPS = os.environ.get('HTTPS', '').strip() == 'on'


class WSGIHTTPSRequest(WSGIRequest):
    def _get_scheme(self):
        if IS_HTTPS:
            return 'https'

        return super(WSGIHTTPSRequest, self)._get_scheme()


application = get_wsgi_application()
application.request_class = WSGIHTTPSRequest
application = Sentry(application)

# Add NewRelic
newrelic_ini = config('NEW_RELIC_CONFIG_FILE', default='newrelic.ini')
newrelic_license_key = config('NEW_RELIC_LICENSE_KEY', default=None)
if newrelic_ini and newrelic_license_key:
    newrelic.agent.initialize(newrelic_ini)
    application = newrelic.agent.wsgi_application()(application)
