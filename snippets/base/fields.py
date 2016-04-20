import re

from django.core.exceptions import ValidationError
from django.db import models


class RegexField(models.CharField):
    def __init__(self, *args, **kwargs):
        myargs = {'max_length': 255,
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
