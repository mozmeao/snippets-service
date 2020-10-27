import json

import bleach
import django.core.validators as django_validators
from django.core.exceptions import ValidationError

ALLOWED_TAGS = ['a', 'i', 'b', 'u', 'strong', 'em', 'br']
ALLOWED_ATTRIBUTES = {'a': ['href', 'data-metric']}
ALLOWED_PROTOCOLS = ['https', 'special']


def validate_as_router_fluent_variables(obj, variables):
    for variable in variables:
        text = getattr(obj, variable)
        bleached_text = bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            # Allow only secure protocols and custom special links.
            protocols=ALLOWED_PROTOCOLS,
        )
        # Bleach escapes '&' to '&amp;'. We need to revert back to compare with
        # text
        bleached_text = bleached_text.replace('&amp;', '&')

        if text != bleached_text:
            error_msg = (
                'Field contains unsupported tags or insecure links. '
                'Only {} tags and https links are supported.'
            ).format(', '.join(ALLOWED_TAGS))
            raise ValidationError({variable: error_msg})
    return obj


def validate_json_data(data):
    try:
        json.loads(data)
    except ValueError:
        raise ValidationError('Enter valid JSON string.')
    return data


# URLValidator that also allows `special:*` links
class URLValidator(django_validators.URLValidator):
    def __init__(self, schemes=None, **kwargs):
        self.schemes = ['https', 'special']
        self.regex = django_validators._lazy_re_compile(
            r'^(special:\w+)|(' + self.regex.pattern + ')')


def validate_jexl(data):
    try:
        pyjexl.JEXL().parse(data)
    except pyjexl.JEXLException:
        raise ValidationError('Enter valid JEXL expression.')
    return data
