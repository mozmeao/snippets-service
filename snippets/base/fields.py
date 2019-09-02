from django.db import models

from snippets.base.validators import URLValidator, validate_regex


class RegexField(models.CharField):
    def __init__(self, *args, **kwargs):
        myargs = {'max_length': 255,
                  'blank': True,
                  'validators': [validate_regex]}
        myargs.update(kwargs)
        return super(RegexField, self).__init__(*args, **myargs)


class URLField(models.CharField):
    validators = [URLValidator]
