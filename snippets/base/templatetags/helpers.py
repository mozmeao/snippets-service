import datetime
import urllib.parse as urlparse

from django.template.defaultfilters import escapejs_filter

from django_jinja import library
from django.utils.http import urlencode
from jinja2 import Markup


@library.global_function
def thisyear():
    """The current year."""
    return datetime.date.today().year


@library.filter
def urlparams(url_, hash=None, **query):
    """Add a fragment and/or query paramaters to a URL.

    New query params will be appended to exising parameters, except duplicate
    names, which will be replaced.
    """
    url = urlparse.urlparse(url_)
    fragment = hash if hash is not None else url.fragment

    # Use dict(parse_qsl) so we don't get lists of values.
    query_dict = dict(urlparse.parse_qsl(url.query))
    query_dict.update(query)

    query_string = urlencode(
        [(k, v) for k, v in list(query_dict.items()) if v is not None])
    new = urlparse.ParseResult(url.scheme, url.netloc, url.path, url.params,
                               query_string, fragment)
    return new.geturl()


@library.filter
def humanize(date):
    """Return a human readable date string."""
    if isinstance(date, datetime.datetime):
        return date.strftime('%a %d %b %Y, %H:%M UTC')
    return None


@library.global_function
def utcnow():
    return Markup(datetime.datetime.utcnow())


@library.filter
def escapejs(data):
    return escapejs_filter(data)
