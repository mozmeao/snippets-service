import json
import re
import xml.sax

from collections import namedtuple
from xml.sax import ContentHandler

from django.core.exceptions import ValidationError
from django.db import models

from jingo import env
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


def validate_regex(regex_str):
    if regex_str.startswith('/'):
        try:
            re.compile(regex_str[1:-1])
        except re.error, exp:
            raise ValidationError(str(exp))
    return regex_str


def validate_xml(data):
    data_dict = json.loads(data)
    for name, value in data_dict.items():
        xml_str = '<div>{0}</div>'.format(value)
        try:
            xml.sax.parseString(xml_str, ContentHandler())
        except xml.sax.SAXParseException as e:
            error_msg = (
                'XML Error in value "{name}": {message} in column {column}'
                ).format(name=name, message=e.getMessage(),
                         column=e.getColumnNumber())
            raise ValidationError(error_msg)
    return data


class RegexField(models.CharField):
    def __init__(self, *args, **kwargs):
        myargs = {'max_length': 64,
                  'blank': True,
                  'validators': [validate_regex]}
        myargs.update(kwargs)
        return super(RegexField, self).__init__(*args, **myargs)


class SnippetTemplate(models.Model):
    """
    A template for the body of a snippet. Can have multiple variables that the
    snippet will fill in.
    """
    name = models.CharField(max_length=255, unique=True)
    code = models.TextField()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def render(self, ctx):
        return env.from_string(self.code).render(ctx)

    def __unicode__(self):
        return self.name


class SnippetTemplateVariable(models.Model):
    """
    A variable for a template that an individual snippet can fill in with its
    own content.
    """
    TEXT = 0
    IMAGE = 1
    TYPE_CHOICES = ((TEXT, 'Text'), (IMAGE, 'Image'))

    template = models.ForeignKey(SnippetTemplate, related_name='variable_set')
    name = models.CharField(max_length=255)
    type = models.IntegerField(choices=TYPE_CHOICES, default=TEXT)

    def __unicode__(self):
        return u'{0}: {1}'.format(self.template.name, self.name)


class ClientMatchRule(models.Model):
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


class Snippet(models.Model):
    name = models.CharField(max_length=255, unique=True)
    template = models.ForeignKey(SnippetTemplate)
    data = models.TextField(default='{}', validators=[validate_xml])

    priority = models.IntegerField(default=0, blank=True)
    disabled = models.BooleanField(default=True)

    publish_start = models.DateTimeField(blank=True, null=True)
    publish_end = models.DateTimeField(blank=True, null=True)

    client_match_rules = models.ManyToManyField(
        ClientMatchRule, blank=True, verbose_name='Client Match Rules')

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def render(self):
        data = json.loads(self.data)
        rendered_snippet = """
            <div data-snippet-id="{id}">{content}</div>
        """.format(
            id=self.id,
            content=self.template.render(data)
        )

        return Markup(rendered_snippet)

    def __unicode__(self):
        return self.name
