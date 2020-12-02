#!/usr/bin/env python3
#
from bottle import redirect, response, route, run, default_app
from decouple import config

from redirect import calculate_redirect

DEBUG = config('DEBUG', default=False, cast=bool)

SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT = config(
    'SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT', default=60 * 60 * 24, cast=int)  # One day

GIT_SHA = config('GIT_SHA', default='HEAD')

CLUSTER_NAME = config('CLUSTER_NAME', default='cluster')
K8S_NAMESPACE = config('K8S_NAMESPACE', default='namespace')
K8S_POD_NAME = config('K8S_POD_NAME', default='pod')

app = default_app()


def set_xbackend_header(fn):
    def _inner(*args, **kwargs):
        response.add_header('X-Backend-Server', f'{CLUSTER_NAME}/{K8S_NAMESPACE}/{K8S_POD_NAME}')
        return fn(*args, **kwargs)

    return _inner


@route('/')
@set_xbackend_header
def index():
    return ''


@route('/static/revision.txt')
@set_xbackend_header
def revision():
    return GIT_SHA


@route('/healthz')
@route('/healthz/')
@set_xbackend_header
def healthz():
    return 'OK'


@route('/<startpage_version>/<name>/<version>/<appbuildid>/'
       '<build_target>/<locale>/<channel>/<os_version>/'
       '<distribution>/<distribution_version>/')
@set_xbackend_header
def redirect_to_bundle(*args, **kwargs):
    locale, distribution, full_url = calculate_redirect(*args, **kwargs)

    response.set_header(
        'Cache-Control',
        f'public, max-age={SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT}'
    )
    return redirect(full_url)


if __name__ == '__main__':
    if DEBUG:
        run(host='localhost', port=8000)
