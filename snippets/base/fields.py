import re

from django.core.exceptions import ValidationError
from django.db import models
from django.forms import MultipleChoiceField


class RegexField(models.CharField):
    def __init__(self, *args, **kwargs):
        myargs = {'max_length': 255,
                  'blank': True,
                  'validators': [validate_regex]}
        myargs.update(kwargs)
        return super(RegexField, self).__init__(*args, **myargs)


class MultipleChoiceFieldCSV(MultipleChoiceField):
    # To be used with in snippets.base.forms.SnippetAdminForm and in
    # combination with DynamicField. We don't directly save() this field in the
    # database so get_prep_value has not been implemented.

    def prepare_value(self, value):
        value = super(MultipleChoiceFieldCSV, self).prepare_value(value)
        if not isinstance(value, list):
            value = value.split(';')
        return value

    def clean(self, value):
        value = super(MultipleChoiceFieldCSV, self).clean(value)
        return ';'.join(value)


def validate_regex(regex_str):
    if regex_str.startswith('/'):
        try:
            re.compile(regex_str[1:-1])
        except re.error, exp:
            raise ValidationError(str(exp))
    return regex_str
