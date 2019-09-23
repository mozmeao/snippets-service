import copy
import datetime
import re
from urllib.parse import ParseResult, urlparse, urlencode

from django.http import QueryDict
from django.utils.encoding import smart_bytes

from product_details import product_details
from product_details.version_compare import version_list

EPOCH = datetime.datetime.utcfromtimestamp(0)


def get_object_or_none(model_class, **filters):
    """
    Identical to Model.get, except instead of throwing exceptions, this returns
    None.
    """
    try:
        return model_class.objects.get(**filters)
    except (model_class.DoesNotExist, model_class.MultipleObjectsReturned):
        return None


def first(collection, callback):
    """
    Find the first item in collection that, when passed to callback, returns
    True. Returns None if no such item is found.
    """
    return next((item for item in collection if callback(item)), None)


def create_locales():
    from snippets.base.models import TargetedLocale

    for code, name in product_details.languages.items():
        locale = TargetedLocale.objects.get_or_create(code=code.lower())[0]
        name = name['English']
        if locale.name != name:
            locale.name = name
            locale.save()


def create_countries():
    from snippets.base.models import TargetedCountry

    for code, name in product_details.get_regions('en-US').items():
        country = TargetedCountry.objects.get_or_create(code=code.upper())[0]
        if country.name != name:
            country.name = name
            country.save()


def current_firefox_major_version():
    full_version = version_list(
        product_details.firefox_history_major_releases)[0]

    return full_version.split('.', 1)[0]


def urlparams(url_, fragment=None, query_dict=None, replace=True, **query):
    """
    Add a fragment and/or query parameters to a URL.
    New query params will be appended to exising parameters, except duplicate
    names, which will be replaced when replace=True otherwise preserved.

    Copied from mozilla/kuma, modified:
     - to not always replace vars
     - to not escape `[]` characters
    """
    url_ = urlparse(url_)
    fragment = fragment if fragment is not None else url_.fragment

    q = url_.query
    new_query_dict = (QueryDict(smart_bytes(q), mutable=True) if
                      q else QueryDict('', mutable=True))
    if query_dict:
        for k, l in query_dict.lists():
            if not replace and k in new_query_dict:
                continue
            new_query_dict[k] = None
            for v in l:
                new_query_dict.appendlist(k, v)

    for k, v in query.items():
        if not replace and k in new_query_dict:
            continue

        if isinstance(v, list):
            new_query_dict.setlist(k, v)
        else:
            new_query_dict[k] = v

    query_string = urlencode([(k, v) for k, l in new_query_dict.lists() for
                              v in l if v is not None], safe='[]')
    new = ParseResult(url_.scheme, url_.netloc, url_.path or '/',
                      url_.params, query_string, fragment)
    return new.geturl()


def fluent_link_extractor(data, variables):
    """Replaces all <a> elements with fluent.js link elements sequentially
    numbered.

    Returns a tuple with the new text and a dict of all the links with url and
    custom metric where available.

    """
    class Replacer:
        link_counter = 0
        links = {}

        def __call__(self, matchobj):
            keyname = 'link{0}'.format(self.link_counter)
            replacement = '<{keyname}>{text}</{keyname}>'.format(
                keyname=keyname,
                text=matchobj.group('innerText'))
            # Find the URL
            url_match = re.search('href="(?P<url>.+?)"', matchobj.group('attrs'))
            url = ''

            if url_match:
                url = url_match.group('url')

            if url == 'special:appMenu':
                self.links[keyname] = {
                    'action': 'OPEN_APPLICATIONS_MENU',
                    'args': 'appMenu',
                }
            elif url.startswith('special:about'):
                self.links[keyname] = {
                    'action': 'OPEN_ABOUT_PAGE',
                    'args': url.rsplit(':', 1)[1],
                }
            elif url == 'special:accounts':
                self.links[keyname] = {
                    'action': 'SHOW_FIREFOX_ACCOUNTS',
                }
            elif url == 'special:monitor':
                self.links[keyname] = {
                    'action': 'ENABLE_FIREFOX_MONITOR',
                    'args': {
                        'url': ('https://monitor.firefox.com/oauth/init?'
                                'utm_source=desktop-snippet&utm_term=[[job_id]]&'
                                'utm_content=[[channels]]&utm_campaign=[[campaign_slug]]&'
                                'entrypoint=snippets&form_type=button'),
                        'flowRequestParams': {
                            'entrypoint': 'snippets',
                            'utm_term': 'snippet-job-[[job_id]]',
                            'form_type': 'button'
                        }
                    }
                }
            else:
                self.links[keyname] = {
                    'url': url,
                }

            # Find the optional data-metric attrib
            metric_match = re.search('data-metric="(?P<metric>.+?)"', matchobj.group('attrs'))
            if metric_match:
                self.links[keyname]['metric'] = metric_match.group('metric')

            self.link_counter += 1
            return replacement

    local_data = copy.deepcopy(data)
    replacer = Replacer()
    for variable in variables:
        if variable not in local_data:
            continue
        local_data[variable] = re.sub('(<a(?P<attrs> .*?)>)(?P<innerText>.+?)(</a>)',
                                      replacer, local_data[variable])

    local_data['links'] = replacer.links
    return local_data


def deep_search_and_replace(data, search_string, replace_string):
    for key, value in data.items():
        if isinstance(value, str):
            data[key] = value.replace(search_string, replace_string)

        elif isinstance(value, list):
            data[key] = [v.replace(search_string, replace_string) for v in value]

        elif isinstance(value, dict):
            data[key] = deep_search_and_replace(value, search_string, replace_string)

    return data
