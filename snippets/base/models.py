import re
from collections import namedtuple

from django.db import models

from jinja2 import Markup

from snippets.base.managers import ClientMatchRuleManager


# NamedTuple that represents a user's client program.
Client = namedtuple('Client', (
    'startpage_version',
    'name',
    'version',
    'appbuildid',
    'build_target',
    'locale',
    'channel',
    'os_version',
    'distribution',
    'distribution_version'
))


class ClientMatchRule(models.Model):
    """Defines a rule that matches a snippet to certain clients."""
    description = models.CharField(max_length=255)
    is_exclusion = models.BooleanField(default=False)

    startpage_version = models.CharField(max_length=64, blank=True)
    name = models.CharField(max_length=64, blank=True)
    version = models.CharField(max_length=64, blank=True)
    appbuildid = models.CharField(max_length=64, blank=True)
    build_target = models.CharField(max_length=64, blank=True)
    locale = models.CharField(max_length=64, blank=True)
    channel = models.CharField(max_length=64, blank=True)
    os_version = models.CharField(max_length=64, blank=True)
    distribution = models.CharField(max_length=64, blank=True)
    distribution_version = models.CharField(max_length=64, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = ClientMatchRuleManager()

    def matches(self, client):
        """Evaluate whether this rule matches the given client."""
        match = True
        for field in client._fields:
            field_value = getattr(self, field, None)
            if not field_value:
                continue

            client_field_value = getattr(client, field)
            if field_value.startswith('/'):  # Match field as a regex.
                try:
                    if re.match(field_value[1:-1], client_field_value) is None:
                        match = False
                        break
                except re.error:
                    # TODO: Figure out better behavior here.
                    match = False
                    break
            elif field_value != client_field_value:  # Match field as a string.
                match = False
                break

        # Exclusion rules match clients that do not match their rule.
        return not match if self.is_exclusion else match

    def __unicode__(self):
        return self.description


class Snippet(models.Model):
    name = models.CharField(max_length=255, unique=True)
    body = models.TextField()

    priority = models.IntegerField(default=0, blank=True)
    disabled = models.BooleanField(default=True)

    publish_start = models.DateTimeField(blank=True, null=True)
    publish_end = models.DateTimeField(blank=True, null=True)

    client_match_rules = models.ManyToManyField(
        ClientMatchRule, blank=True, verbose_name='Client Match Rules')

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def render(self):
        return Markup(self.body)

    def __unicode__(self):
        return self.name
