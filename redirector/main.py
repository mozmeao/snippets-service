#!/usr/bin/env python3
#
from bottle import redirect, response, route, run
from decouple import config

from redirect import calculate_redirect

DEBUG = config('DEBUG', default=False, cast=bool)

SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT = config(
    'SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT', default=60 * 60 * 24, cast=int)  # One day

GIT_SHA = config('GIT_SHA', default='HEAD')


@route('/')
def index():
    return redirect('https://snippets.cdn.mozilla.net/')


@route('/static/revision.txt')
def revision():
    return GIT_SHA


@route('/healthz')
@route('/healthz/')
def healthz():
    return 'OK'


@route('/<startpage_version>/<name>/<version>/<appbuildid>/'
       '<build_target>/<locale>/<channel>/<os_version>/'
       '<distribution>/<distribution_version>/')
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
    else:
        run(host='0.0.0.0',
            port=8000,
            server='gunicorn',
            workers=config('WSGI_NUM_WORKERS', default=2, cast=int))
