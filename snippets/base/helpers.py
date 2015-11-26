from datetime import datetime

from django.template.defaultfilters import escapejs_filter

import jinja2
from jingo import register


@register.function
def utcnow():
    return jinja2.Markup(datetime.utcnow())


@register.function
def field_with_attrs(bfield, **kwargs):
    """Allows templates to dynamically add html attributes to bound
    fields from django forms.

    Copied from bedrock.
    """
    if kwargs.get('label', None):
        bfield.label = kwargs['label']
    bfield.field.widget.attrs.update(kwargs)
    return bfield


@register.filter
def humanize(date):
    """Return a human readable date string."""
    if isinstance(date, datetime):
        return date.strftime('%a %d %b %Y, %H:%M UTC')
    return None


@register.filter
def escapejs(data):
    return escapejs_filter(data)
