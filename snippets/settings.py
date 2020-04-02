import os
import platform

import dj_database_url
import django_cache_url
import product_details
import sentry_sdk
from decouple import Csv, config
from sentry_sdk.integrations.django import DjangoIntegration


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
ALLOWED_CIDR_NETS = config('ALLOWED_CIDR_NETS', default='', cast=Csv())

# Needs to be None if not set so that the middleware will be turned off. Can't
# set default to None because of the Csv() cast.
ENFORCE_HOST = config('ENFORCE_HOST', default='', cast=Csv()) or None

# Application definition

INSTALLED_APPS = [
    # Project specific apps
    'snippets.base',

    # Third party apps
    'django_jinja',
    'django_ace',
    'product_details',
    'django_extensions',
    'reversion',
    'cachalot',
    'mozilla_django_oidc',
    'watchman',
    'quickedit',
    'django_admin_listfilter_dropdown',
    'admin_reorder',
    'django_filters',
    'taggit',
    'taggit_helpers',
    'taggit_selectize',

    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.postgres',
    'django.contrib.sessions',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
]

for app in config('EXTRA_APPS', default='', cast=Csv()):
    INSTALLED_APPS.append(app)

MIDDLEWARE = (
    'snippets.base.middleware.HostnameMiddleware',
    'allow_cidr.middleware.AllowCIDRMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django_statsd.middleware.GraphiteRequestTimingMiddleware',
    'django_statsd.middleware.GraphiteMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'snippets.base.middleware.FetchSnippetsMiddleware',
    'snippets.base.middleware.EnforceHostIPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',
    'admin_reorder.middleware.ModelAdminReorder',
)

HOSTNAME = platform.node()
CLUSTER_NAME = config('CLUSTER_NAME', default=None)
K8S_NAMESPACE = config('K8S_NAMESPACE', default=None)
K8S_POD_NAME = config('K8S_POD_NAME', default=None)
ENABLE_HOSTNAME_MIDDLEWARE = config('ENABLE_HOSTNAME_MIDDLEWARE',
                                    default=bool(K8S_NAMESPACE), cast=bool)

ROOT_URLCONF = 'snippets.urls'

WSGI_APPLICATION = 'snippets.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': config('DATABASE_URL', cast=dj_database_url.parse)
}

SILENCED_SYSTEM_CHECKS = [
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
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = config('MEDIA_URL', '/media/')
MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))
MEDIA_BUNDLES_ROOT = config('MEDIA_BUNDLES_ROOT', default='bundles/')
MEDIA_BUNDLES_PREGEN_ROOT = config('MEDIA_BUNDLES_PREGEN_ROOT', default='bundles-pregen/')
MEDIA_ICONS_ROOT = config('MEDIA_ICONS_ROOT', default='icons/')

SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)
SESSION_COOKIE_SAMESITE = config('SESSION_COOKIE_SAMESITE', default='Lax')

USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default='0', cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_BROWSER_XSS_FILTER = config('SECURE_BROWSER_XSS_FILTER', default=False, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = config('SECURE_CONTENT_TYPE_NOSNIFF', default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REDIRECT_EXEMPT = [
    r'^healthz/$',
    r'^readiness/$',
]

# watchman
WATCHMAN_DISABLE_APM = True
WATCHMAN_CHECKS = (
    'watchman.checks.caches',
    'watchman.checks.databases',
)

TEMPLATES = [
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG_TEMPLATE,
            "match_extension": None,
            'match_regex': r'.+\.jinja(\.json)?',
            'newstyle_gettext': True,
            'context_processors': [
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
                'snippets.base.context_processors.settings',
            ],
        }
    },
]

CSP_DEFAULT_SRC = (
    "'self'",
)
CSP_IMG_SRC = (
    "'self'",
    "data:",
)
CSP_REPORT_ONLY = config('CSP_REPORT_ONLY', default=False, cast=bool)
CSP_REPORT_ENABLE = config('CSP_REPORT_ENABLE', default=True, cast=bool)
if CSP_REPORT_ENABLE:
    CSP_REPORT_URI = config('CSP_REPORT_URI', default='/csp-violation-capture')

SNIPPET_SIZE_LIMIT = 500
SNIPPET_IMAGE_SIZE_LIMIT = 250

ENABLE_ADMIN = config('ENABLE_ADMIN', default=False, cast=bool)
CSRF_USE_SESSIONS = config('CSRF_USE_SESSIONS', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=not DEBUG, cast=bool)
CSRF_COOKIE_SAMESITE = config('CSRF_COOKIE_SAMESITE', default='Lax')

SNIPPET_BUNDLE_TIMEOUT = config('SNIPPET_BUNDLE_TIMEOUT', default=15 * 60, cast=int)  # 15 minutes
SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT = config(
    'SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT', default=60 * 60 * 24, cast=int)  # One day

BUNDLE_BROTLI_COMPRESS = config('BUNDLE_BROTLI_COMPRESS', default=False, cast=bool)

METRICS_URL = config('METRICS_URL', default='https://snippets-stats.mozilla.org/foo.html')
METRICS_SAMPLE_RATE = config('METRICS_SAMPLE_RATE', default=0.1, cast=float)

SITE_URL = config('SITE_URL', default='')
SITE_HEADER = config('SITE_HEADER', default='Snippets Administration')
SITE_TITLE = config('SITE_TITLE', default='Mozilla Snippets')

CACHES = {
    'default': config('CACHE_URL', default='locmem://', cast=django_cache_url.parse),
    'product-details': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'product-details',
        'OPTIONS': {
            'MAX_ENTRIES': 200,  # currently 104 json files
            'CULL_FREQUENCY': 4,  # 1/4 entries deleted if max reached
        }

    },
    'cachalot': config(
        'CACHALOT_CACHE_URL',
        default='locmem://?location=cachalog&max_entries=500&cull_frequency=4',
        cast=django_cache_url.parse),
}

GEO_URL = 'https://location.services.mozilla.com/v1/country?key=fff72d56-b040-4205-9a11-82feda9d83a3'  # noqa

PROD_DETAILS_CACHE_NAME = 'product-details'
PROD_DETAILS_STORAGE = config('PROD_DETAILS_STORAGE',
                              default='product_details.storage.PDFileStorage')
PROD_DETAILS_DIR = config('PROD_DETAILS_DIR',
                          default=product_details.settings_defaults.PROD_DETAILS_DIR)

DEFAULT_FILE_STORAGE = config('FILE_STORAGE', 'snippets.base.storage.OverwriteStorage')

CDN_URL = config('CDN_URL', default='')

# Set to 'snippets.base.storage.S3Storage' for S3
if DEFAULT_FILE_STORAGE == 'snippets.base.storage.S3Storage':
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    # Full list of S3 endpoints http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region
    AWS_S3_HOST = config('AWS_S3_HOST')
    AWS_CACHE_CONTROL_HEADERS = {
        MEDIA_BUNDLES_ROOT: 'max-age=2592000',  # 1 Month
        MEDIA_ICONS_ROOT: 'max-age=15552000',  # 6 Months
        MEDIA_BUNDLES_PREGEN_ROOT: 'max-age=600',  # 10 minutes
    }
    AWS_DEFAULT_ACL = 'public-read'
    AWS_BUCKET_ACL = 'public-read'

DEAD_MANS_SNITCH_PRODUCT_DETAILS = config('DEAD_MANS_SNITCH_PRODUCT_DETAILS', default=None)
DEAD_MANS_SNITCH_DISABLE_SNIPPETS = config('DEAD_MANS_SNITCH_DISABLE_SNIPPETS', default=None)
DEAD_MANS_SNITCH_UPDATE_JOBS = config('DEAD_MANS_SNITCH_UPDATE_JOBS', default=None)
DEAD_MANS_SNITCH_FETCH_METRICS = config('DEAD_MANS_SNITCH_FETCH_METRICS', default=None)
DEAD_MANS_SNITCH_FETCH_DAILY_METRICS = config('DEAD_MANS_SNITCH_FETCH_DAILY_METRICS', default=None)

SNIPPETS_PER_PAGE = config('SNIPPETS_PER_PAGE', default=50)

ENGAGE_ROBOTS = config('ENGAGE_ROBOTS', default=False)

CACHE_EMPTY_QUERYSETS = True

ADMIN_REDIRECT_URL = config('ADMIN_REDIRECT_URL', default=None)

STATSD_HOST = config('STATSD_HOST', default='localhost')
STATSD_PORT = config('STATSD_PORT', 8125, cast=int)
STATSD_PREFIX = config('STATSD_PREFIX', K8S_NAMESPACE)
STATSD_CLIENT = config('STATSD_CLIENT', 'django_statsd.clients.null')

sentry_sdk.init(
    dsn=config('SENTRY_DSN', None),
    integrations=[DjangoIntegration()],
    release=config('GIT_SHA', None),
    environment=config('SENTRY_ENVIRONMENT', 'dev'),
    server_name='.'.join(x for x in [HOSTNAME, K8S_NAMESPACE, CLUSTER_NAME] if x),
)


CACHALOT_ENABLED = config('CACHALOT_ENABLED', default=not DEBUG, cast=bool)
CACHALOT_TIMEOUT = config('CACHALOT_TIMEOUT', default=300, cast=int)  # 300 = 5 minutes
CACHALOT_CACHE = config('CACHELOT_CACHE', default='cachalot')

OIDC_ENABLE = config('OIDC_ENABLE', default=False, cast=bool)
if OIDC_ENABLE:
    AUTHENTICATION_BACKENDS = (
        'snippets.base.authentication.AuthBackend',
    )
    OIDC_OP_AUTHORIZATION_ENDPOINT = config('OIDC_OP_AUTHORIZATION_ENDPOINT')
    OIDC_OP_TOKEN_ENDPOINT = config('OIDC_OP_TOKEN_ENDPOINT')
    OIDC_OP_USER_ENDPOINT = config('OIDC_OP_USER_ENDPOINT')

    OIDC_RP_CLIENT_ID = config('OIDC_RP_CLIENT_ID')
    OIDC_RP_CLIENT_SECRET = config('OIDC_RP_CLIENT_SECRET')
    OIDC_CREATE_USER = config('OIDC_CREATE_USER', default=False, cast=bool)
    MIDDLEWARE = MIDDLEWARE + ('mozilla_django_oidc.middleware.SessionRefresh',)
    LOGIN_REDIRECT_URL = '/admin/'


ADMIN_REORDER = [
    {
        'app': 'base',
        'label': 'Snippets',
        'models': [
            'base.Snippet', 'base.SearchProvider', 'base.ClientMatchRule',
            'base.SnippetTemplate', 'base.TargetedCountry', 'base.TargetedLocale',
        ]
    },
    {
        'app': 'base',
        'label': 'ASR Snippets',
        'models': [
            'base.ASRSnippet',
            'base.Job',
            'base.Campaign',
            'base.Category',
            'base.Product',
            'base.Target',
            'base.Icon',
            'base.Addon',
            'base.Locale',
            'base.Distribution',
            'base.DistributionBundle',
        ]

    },
    {
        'app': 'base',
        'label': 'Metrics',
        'models': [
            'base.JobDailyPerformance',
            'base.DailyImpressions',
        ]
    },
    {
        'app': 'auth',
        'label': 'Admin',
        'models': [
            'auth.User',
            'auth.Group',
            'admin.LogEntry'
        ]
    },
]


SLACK_ENABLE = config('SLACK_ENABLE', default=False, cast=bool)
SLACK_WEBHOOK = config('SLACK_WEBHOOK', default='')


# Required for the migration to ASRSnippets or SuspiciousOperation
# (TooManyFields) will be raised due to the number of Snippets selected in the
# admin tool.
DATA_UPLOAD_MAX_NUMBER_FIELDS = config('DATA_UPLOAD_MAX_NUMBER_FIELDS', default=1000, cast=int)

IMAGE_OPTIMIZE = config('IMAGE_OPTIMIZE', default=True, cast=bool)
# Set to zero to disable
IMAGE_MAX_DIMENSION = config('IMAGE_MAX_DIMENSION', default=192, cast=int)
# Set to zero to disable
IMAGE_MAX_SIZE = config('IMAGE_MAX_SIZE', default=40960, cast=int)

TAGGIT_CASE_INSENSITIVE = True

# In minutes
SNIPPETS_PUBLICATION_OFFSET = config('SNIPPETS_PUBLICATION_OFFSET', default=5, cast=int)

REDASH_ENDPOINT = config('REDASH_ENDPOINT', default='https://sql.telemetry.mozilla.org')
REDASH_API_KEY = config('REDASH_API_KEY', default=None)
REDASH_MAX_WAIT = config('REDASH_MAX_WAIT', default=300)
REDASH_JOB_QUERY_ID = config('REDASH_JOB_QUERY_ID', default=63146)
REDASH_JOB_QUERY_BIGQUERY_ID = config('REDASH_JOB_QUERY_BIGQUERY_ID', default=66681)

REDASH_UPDATE_INTERVAL = config('REDASH_UPDATE_INTERVAL', default=600)

USE_PREGEN_BUNDLES = config('USE_PREGEN_BUNDLES', default=False, cast=bool)

NIGHTLY_INCLUDES_RELEASE = config('NIGHTLY_INCLUDES_RELEASE', default=False, cast=bool)

RATELIMIT_ENABLE = config('RATELIMIT_ENABLE', default=False, cast=bool)
RATELIMIT_RATE = config('RATELIMIT_RATE', default='10/m')
