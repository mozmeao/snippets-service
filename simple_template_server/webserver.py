import glob
import os
import json
import datetime

import jinja2
import yaml
from bottle import route, run, hook, response

try:
    STARTPAGE_VERSION = int(os.getenv('SNIPPETS_STARTPAGE_VERSION', 5))
except ValueError:
    raise Exception('Invalid startpage version: {}'.format(os.getenv('SNIPPETS_STARTPAGE_VERSION')))


jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'),
    autoescape=True,
)


def escapejs(value):
    _js_escapes = {
        ord(u'\\'): u'\\u005C',
        ord(u'\''): u'\\u0027',
        ord(u'"'): u'\\u0022',
        ord(u'>'): u'\\u003E',
        ord(u'<'): u'\\u003C',
        ord(u'&'): u'\\u0026',
        ord(u'='): u'\\u003D',
        ord(u'-'): u'\\u002D',
        ord(u';'): u'\\u003B',
        ord(u'\u2028'): u'\\u2028',
        ord(u'\u2029'): u'\\u2029'
    }

    return value.replace(u'\n', u'').translate(_js_escapes)
jinja_env.filters['escapejs'] = escapejs


class Settings():
    METRICS_URL = 'http://example.com'
    METRICS_SAMPLE_RATE = '1.0'
    GEO_URL = 'https://location.services.mozilla.com/v1/country?key=fff72d56-b040-4205-9a11-82feda9d83a3'


class Client():
    startpage_version = STARTPAGE_VERSION
    locale = 'en-US'


def render_snippet(snippet_code, data):
    attrs = [('data-snippet-id', data['snippet_id']),
             ('data-weight', 100),
             ('data-campaign', 'campaign'),
             ('class', 'snippet-metadata')]
    attr_string = ' '.join('{0}="{1}"'.format(key, value) for key, value in attrs)
    snippet_template = jinja_env.from_string(snippet_code)
    rendered_snippet = '<div {attrs}>{content}</div>'.format(
            attrs=attr_string,
            content=snippet_template.render(data),
        )
    return rendered_snippet


@route('<:re:.*>')
def home():
    data = []

    if STARTPAGE_VERSION == 5:
        directory = 'snippets_as'
    else:
        directory = 'snippets'

    for snippet_id, snippet_filename in enumerate(glob.glob('{}/*.html'.format(directory))):
        with open('{}'.format(snippet_filename)) as f:
            snippet_code = f.read()

        snippet_name = os.path.splitext(snippet_filename)[0]
        try:
            with open('{}.yml'.format(snippet_name)) as snippet_data_file:
                snippet_data = yaml.load(snippet_data_file)
        except IOError:
            snippet_data = {}

        snippet_data['snippet_id'] = snippet_id

        data.append({
            'id': snippet_id,
            'code': render_snippet(snippet_code, snippet_data),
            'countries': [],
            'campaign': '',
            'weight': 100,
            'exclude_from_search_engines': [],
            'client_options': {
                'has_fxaccount': 'any',
                'version_lower_bound': 'any',
                'version_upper_bound': 'any',
                'is_default_browser': 'any',
                'screen_resolutions': "0-1024;1024-1920;1920-50000",
                'profileage_lower_bound': -1,
                'profileage_upper_bound': -1,
                'addon_check_type': 'any',
                'addon_name': '',
                'bookmarks_count_lower_bound': -1,
                'bookmarks_count_upper_bound': -1,
            }
        })

    if STARTPAGE_VERSION == 5:
        template = jinja_env.get_or_select_template('fetch_snippets_as.jinja')
    else:
        template = jinja_env.get_or_select_template('fetch_snippets.jinja')

    return template.render(**{
        'utcnow': datetime.datetime.utcnow,
        'snippet_ids': list(range(len(data))),
        'snippets_json': unicode(json.dumps(data)),
        'client': Client(),
        'locale': Client().locale,
        'settings': Settings(),
        'current_firefox_major_version': 57,
    })


@hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'


run(host='0.0.0.0', port=8000, reloader=True)
