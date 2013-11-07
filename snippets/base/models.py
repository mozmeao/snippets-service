import json
import re
import xml.sax
from StringIO import StringIO
from collections import namedtuple
from xml.sax import ContentHandler

from django.core.exceptions import ValidationError
from django.db import models

from caching.base import CachingManager, CachingMixin
from jingo import env
from jinja2 import Markup

from snippets.base.fields import CountryField, LocaleField, RegexField
from snippets.base.managers import ClientMatchRuleManager, SnippetManager


CHANNELS = ('release', 'beta', 'aurora', 'nightly')
STARTPAGE_VERSIONS = ('1', '2', '3', '4')
CLIENT_NAMES = {'Firefox': 'firefox', 'fennec': 'fennec'}
SNIPPET_WEIGHTS = ((33, 'Appear 1/3rd as often as an average snippet'),
                   (50, 'Appear half as often as an average snippet'),
                   (66, 'Appear 2/3rds as often as an average snippet'),
                   (100, 'Appear as often as an average snippet'),
                   (150, 'Appear 1.5 times as often as an average snippet'),
                   (200, 'Appear twice as often as an average snippet'),
                   (300, 'Appear three times as often as an average snippet'))


def validate_xml(data):
    data_dict = json.loads(data)

    # set up a safer XML parser that does not resolve external
    # entities
    parser = xml.sax.make_parser()
    parser.setContentHandler(ContentHandler())
    parser.setFeature(xml.sax.handler.feature_external_ges, 0)

    for name, value in data_dict.items():
        value = value.encode('utf-8')
        xml_str = '<div>{0}</div>'.format(value)
        try:
            parser.parse(StringIO(xml_str))
        except xml.sax.SAXParseException as e:
            error_msg = (
                'XML Error in value "{name}": {message} in column {column}'
                .format(name=name, message=e.getMessage(),
                        column=e.getColumnNumber()))
            raise ValidationError(error_msg)
    return data


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


class SnippetTemplate(CachingMixin, models.Model):
    """
    A template for the body of a snippet. Can have multiple variables that the
    snippet will fill in.
    """
    name = models.CharField(max_length=255, unique=True)
    code = models.TextField()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    cached_objects = CachingManager()

    def render(self, ctx):
        ctx.setdefault('snippet_id', 0)
        return env.from_string(self.code).render(ctx)

    def __unicode__(self):
        return self.name


class SnippetTemplateVariable(CachingMixin, models.Model):
    """
    A variable for a template that an individual snippet can fill in with its
    own content.
    """
    TEXT = 0
    IMAGE = 1
    SMALLTEXT = 2
    TYPE_CHOICES = ((TEXT, 'Text'), (IMAGE, 'Image'), (SMALLTEXT, 'Small Text'))

    template = models.ForeignKey(SnippetTemplate, related_name='variable_set')
    name = models.CharField(max_length=255)
    type = models.IntegerField(choices=TYPE_CHOICES, default=TEXT)
    description = models.TextField(blank=True, default='')

    objects = models.Manager()
    cached_objects = CachingManager()

    def __unicode__(self):
        return u'{0}: {1}'.format(self.template.name, self.name)


class ClientMatchRule(CachingMixin, models.Model):
    """Defines a rule that matches a snippet to certain clients."""
    description = models.CharField(max_length=255, unique=True)
    is_exclusion = models.BooleanField(default=False)

    startpage_version = RegexField()
    name = RegexField()
    version = RegexField()
    appbuildid = RegexField()
    build_target = RegexField()
    locale = RegexField()
    channel = RegexField()
    os_version = RegexField()
    distribution = RegexField()
    distribution_version = RegexField()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    cached_objects = ClientMatchRuleManager()

    class Meta:
        ordering = ('-modified',)

    def matches(self, client):
        """Evaluate whether this rule matches the given client."""
        match = True
        for field in client._fields:
            field_value = getattr(self, field, None)
            if not field_value:
                continue

            client_field_value = getattr(client, field)
            if field_value.startswith('/'):  # Match field as a regex.
                if re.match(field_value[1:-1], client_field_value) is None:
                    match = False
                    break
            elif field_value != client_field_value:  # Match field as a string.
                match = False
                break

        # Exclusion rules match clients that do not match their rule.
        return not match if self.is_exclusion else match

    def __unicode__(self):
        return self.description


class Snippet(CachingMixin, models.Model):
    name = models.CharField(max_length=255, unique=True)
    template = models.ForeignKey(SnippetTemplate)
    data = models.TextField(default='{}', validators=[validate_xml])

    priority = models.IntegerField(default=0, blank=True)
    disabled = models.BooleanField(default=True)

    country = CountryField('Geolocation Country', blank=True, default='')

    publish_start = models.DateTimeField(blank=True, null=True)
    publish_end = models.DateTimeField(blank=True, null=True)

    on_firefox = models.BooleanField(default=True, verbose_name='Firefox')
    on_fennec = models.BooleanField(default=False, verbose_name='Fennec')

    on_release = models.BooleanField(default=True, verbose_name='Release')
    on_beta = models.BooleanField(default=False, verbose_name='Beta')
    on_aurora = models.BooleanField(default=False, verbose_name='Aurora')
    on_nightly = models.BooleanField(default=False, verbose_name='Nightly')

    on_startpage_1 = models.BooleanField(default=False, verbose_name='Version 1')
    on_startpage_2 = models.BooleanField(default=True, verbose_name='Version 2')
    on_startpage_3 = models.BooleanField(default=True, verbose_name='Version 3')
    on_startpage_4 = models.BooleanField(default=True, verbose_name='Version 4')

    weight = models.IntegerField(
        'Prevalence', choices=SNIPPET_WEIGHTS, default=100,
        help_text='How often should this snippet be shown to users?')

    client_match_rules = models.ManyToManyField(
        ClientMatchRule, blank=True, verbose_name='Client Match Rules')

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    cached_objects = SnippetManager()

    class Meta:
        ordering = ('-modified',)

    def render(self):
        data = json.loads(self.data)
        if self.id:
            data.setdefault('snippet_id', self.id)

        # Use a list for attrs to make the output order predictable.
        attrs = [('data-snippet-id', self.id),
                 ('data-weight', self.weight)]
        if self.country:
            attrs.append(('data-country', self.country))
        attr_string = ' '.join('{0}="{1}"'.format(key, value) for key, value in
                               attrs)

        rendered_snippet = u'<div {attrs}>{content}</div>'.format(
            attrs=attr_string,
            content=self.template.render(data)
        )

        return Markup(rendered_snippet)

    @property
    def products(self):
        products = []
        for key, value in CLIENT_NAMES.items():
            if getattr(self, 'on_{0}'.format(value), False):
                products.append(key)
        return products

    @property
    def channels(self):
        channels = []
        for channel in CHANNELS:
            if getattr(self, 'on_{0}'.format(channel), False):
                channels.append(channel)
        return channels

    def __unicode__(self):
        return self.name


class SnippetLocale(CachingMixin, models.Model):
    snippet = models.ForeignKey(Snippet, related_name='locale_set')
    locale = LocaleField()

    objects = models.Manager()
    cached_objects = CachingManager()
