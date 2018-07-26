import datetime
import re

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
        country = TargetedCountry.objects.get_or_create(code=code)[0]
        if country.name != name:
            country.name = name
            country.save()


def current_firefox_major_version():
    full_version = version_list(
        product_details.firefox_history_major_releases)[0]

    return full_version.split('.', 1)[0]


def fluent_link_extractor(text):
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
            self.links[keyname] = {
                'url': url,
            }

            # Find the optional data-metric attrib
            metric_match = re.search('data-metric="(?P<metric>.+?)"', matchobj.group('attrs'))
            if metric_match:
                self.links[keyname]['metric'] = metric_match.group('metric')

            self.link_counter += 1
            return replacement

    replacer = Replacer()
    final_text = re.sub('(<a(?P<attrs> .*?)>)(?P<innerText>.+?)(</a>)', replacer, text)
    return final_text, replacer.links


def to_unix_time_seconds(dt):
    return int((dt - EPOCH).total_seconds())
