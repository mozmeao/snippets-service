from django.db import models

from snippets.base.validators import URLValidator


class URLField(models.CharField):
    validators = [URLValidator]
