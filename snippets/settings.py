"""
Django settings for snippets project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
import os
import platform

import dj_database_url
import django_cache_url
from decouple import Csv, config


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.join(BASE_DIR, '..'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)
DEBUG_TEMPLATE = config('DEBUG_TEMPLATE', default=DEBUG, cast=bool),

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# Application definition

INSTALLED_APPS = [
    # Project specific apps
    'snippets.base',
    'snippets.saml',

    # Third party apps
    'django_jinja',
    'django_filters',
    'django_ace',
    'product_details',
    'clear_cache',
    'django_extensions',
    'django_mysql',
    'reversion',

    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

for app in config('EXTRA_APPS', default='', cast=Csv()):
    INSTALLED_APPS.append(app)


MIDDLEWARE_CLASSES = (
    'sslify.middleware.SSLifyMiddleware',
    'snippets.base.middleware.FetchSnippetsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

HOSTNAME = platform.node()
DEIS_APP = config('DEIS_APP', default=None)
DEIS_DOMAIN = config('DEIS_DOMAIN', default=None)
ENABLE_HOSTNAME_MIDDLEWARE = config('ENABLE_HOSTNAME_MIDDLEWARE',
                                    default=bool(DEIS_APP), cast=bool)
if ENABLE_HOSTNAME_MIDDLEWARE:
    MIDDLEWARE_CLASSES = (
        ('snippets.base.middleware.HostnameMiddleware',) +
        MIDDLEWARE_CLASSES)

ROOT_URLCONF = 'snippets.urls'

WSGI_APPLICATION = 'snippets.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': config(
        'DATABASE_URL',
        cast=dj_database_url.parse
    )
}


if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
    DATABASES['default']['OPTIONS'] = {
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'; SET innodb_strict_mode=1;",
    }

    # Dockerized MariaDB reports MySQL 5.5.5 as version. Need to
    # override this to work with DynamicField.
    if config('OVERRIDE_MARIADB_VERSION', default=False):
        from django.utils.functional import cached_property
        from django.db.backends.mysql.base import DatabaseWrapper

        @cached_property
        def mysql_version(self):
            return config('OVERRIDE_MARIADB_VERSION', cast=tuple)

        DatabaseWrapper.mysql_version = mysql_version

SILENCED_SYSTEM_CHECKS = [
    'django_mysql.W003',
]


# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')

TIME_ZONE = config('TIME_ZONE', default='UTC')

USE_I18N = config('USE_I18N', default=False, cast=bool)

USE_L10N = config('USE_L10N', default=False, cast=bool)

USE_TZ = config('USE_TZ', default=False, cast=bool)

STATIC_ROOT = config('STATIC_ROOT', default=os.path.join(BASE_DIR, 'static'))
STATIC_URL = config('STATIC_URL', '/static/')
if not DEBUG_TEMPLATE:
    STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'

MEDIA_URL = config('MEDIA_URL', '/media/')
MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))
MEDIA_FILES_ROOT = config('MEDIA_FILES_ROOT', default='files/')
MEDIA_BUNDLES_ROOT = config('MEDIA_BUNDLES_ROOT', default='bundles/')

SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)

SSLIFY_DISABLE = config('DISABLE_SSL', default=DEBUG, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

TEMPLATES = [
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG_TEMPLATE,
            'match_extension': '.jinja',
            'newstyle_gettext': True,
            'context_processors': [
                'session_csrf.context_processor',
                'snippets.base.context_processors.settings',
                'snippets.base.context_processors.i18n',
            ],
        }
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'session_csrf.context_processor',
                'snippets.base.context_processors.settings',
            ],
        }
    },
]

SNIPPET_SIZE_LIMIT = 500
SNIPPET_IMAGE_SIZE_LIMIT = 250

ENABLE_ADMIN = config('ENABLE_ADMIN', default=True, cast=bool)

ANON_ALWAYS = True

SNIPPET_BUNDLE_TIMEOUT = 15 * 60  # 15 minutes

METRICS_URL = config('METRICS_URL', default='https://snippets-stats.mozilla.org/foo.html')
METRICS_SAMPLE_RATE = config('METRICS_SAMPLE_RATE', default=0.1, cast=float)

SITE_URL = config('SITE_URL', default='')

CACHES = {
    'default': config('CACHE_URL', default='locmem://', cast=django_cache_url.parse),
}

SERVE_SNIPPET_BUNDLES = config('SERVE_SNIPPET_BUNDLES', default=not DEBUG, cast=bool)

GEO_URL = 'https://location.services.mozilla.com/v1/country?key=fff72d56-b040-4205-9a11-82feda9d83a3'  # noqa

PROD_DETAILS_STORAGE = config('PROD_DETAILS_STORAGE',
                              default='product_details.storage.PDFileStorage')


SAML_ENABLE = config('SAML_ENABLE', default=False, cast=bool)
if SAML_ENABLE:
    from saml.settings import *  # noqa


DEFAULT_FILE_STORAGE = config('FILE_STORAGE', 'storages.backends.overwrite.OverwriteStorage')

CDN_URL = config('CDN_URL', default='')


# Set to 'storages.backends.s3boto.S3BotoStorage' for S3
if DEFAULT_FILE_STORAGE == 'snippets.base.storage.S3Storage':
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    # Full list of S3 endpoints http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region
    AWS_S3_HOST = config('AWS_S3_HOST')
    AWS_CACHE_CONTROL_HEADERS = {
        MEDIA_FILES_ROOT: 'max-age=900',  # 15 Minutes
        MEDIA_BUNDLES_ROOT: 'max-age=2592000',  # 1 Month
    }

DEAD_MANS_SNITCH_URL = config('DEAD_MANS_SNITCH_URL', default=None)

SNIPPET_HTTP_MAX_AGE = config('SNIPPET_HTTP_MAX_AGE', default=90)
SNIPPETS_PER_PAGE = config('SNIPPETS_PER_PAGE', default=50)

ENGAGE_ROBOTS = config('ENGAGE_ROBOTS', default=False)
