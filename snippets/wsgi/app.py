"""
WSGI config for snippets project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""
import newrelic.agent
newrelic.agent.initialize('newrelic.ini')

import os  # NOQA
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'snippets.settings')  # NOQA

from django.core.wsgi import get_wsgi_application  # NOQA
application = get_wsgi_application()
