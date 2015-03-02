from . import base

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'snippets',
        'USER': 'snippets',
        'PASSWORD': 'asdf',
        'HOST': 'db',
        'PORT': '',
        'OPTIONS': {
            'init_command': 'SET default_storage_engine=InnoDB',
            'charset': 'utf8',
            'use_unicode': True,
        },
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    },
}

DEBUG = TEMPLATE_DEBUG = True

HMAC_KEYS = {
    '2012-06-06': 'some secret',
}

from django_sha2 import get_password_hashers  # NOQA
PASSWORD_HASHERS = get_password_hashers(base.BASE_PASSWORD_HASHERS, HMAC_KEYS)

# Make this unique, and don't share it with anybody.  It cannot be blank.
SECRET_KEY = 'dev'

# Should robots.txt allow web crawlers?  Set this to True for production
ENGAGE_ROBOTS = True

SESSION_COOKIE_SECURE = False

# Snippets-specific caching
SNIPPET_HTTP_MAX_AGE = 90  # Time to cache HTTP responses for snippets.

# Replace with site protocol, domain, and (optionally) port.
SITE_URL = 'http://docker:8000'
