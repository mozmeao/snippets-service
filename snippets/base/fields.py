import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from south.modelsinspector import add_introspection_rules

from snippets.base import ENGLISH_COUNTRY_CHOICES, ENGLISH_LANGUAGE_CHOICES


class LocaleField(models.CharField):
    description = ('CharField with locale settings specific to Snippets '
                   'defaults.')

    def __init__(self, *args, **kwargs):
        options = {
            'max_length': 32,
            'default': settings.LANGUAGE_CODE,
            'choices': ENGLISH_LANGUAGE_CHOICES
        }
        options.update(kwargs)
        return super(LocaleField, self).__init__(*args, **options)


class CountryField(models.CharField):
    description = ('CharField with country settings specific to Snippets '
                   'defaults.')

    def __init__(self, *args, **kwargs):
        options = {
            'max_length': 16,
            'default': u'us',
            'choices': ENGLISH_COUNTRY_CHOICES
        }
        options.update(kwargs)
        return super(CountryField, self).__init__(*args, **options)


class RegexField(models.CharField):
    def __init__(self, *args, **kwargs):
        myargs = {'max_length': 64,
                  'blank': True,
                  'validators': [validate_regex]}
        myargs.update(kwargs)
        return super(RegexField, self).__init__(*args, **myargs)


def validate_regex(regex_str):
    if regex_str.startswith('/'):
        try:
            re.compile(regex_str[1:-1])
        except re.error, exp:
            raise ValidationError(str(exp))
    return regex_str


add_introspection_rules([], ['^snippets\.base\.fields\.LocaleField'])
add_introspection_rules([], ['^snippets\.base\.fields\.CountryField'])
add_introspection_rules([], ["^snippets\.base\.fields\.RegexField"])
