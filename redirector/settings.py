#!/usr/bin/env python3

from decouple import config

DEBUG = config('DEBUG', default=False, cast=bool)

SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT = config(
    'SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT', default=60 * 60 * 24, cast=int)  # One day

GIT_SHA = config('GIT_SHA', default='HEAD')
