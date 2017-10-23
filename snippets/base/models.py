import copy
import hashlib
import json
import os
import re
import uuid
import xml.sax
from StringIO import StringIO
from collections import namedtuple
from datetime import datetime
from urlparse import urljoin, urlparse
from xml.sax import ContentHandler

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.manager import Manager
from django.template import engines
from django.template.loader import render_to_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property

import django_mysql.models
from jinja2 import Markup
from jinja2.utils import LRUCache

from snippets.base import util
from snippets.base.fields import RegexField
from snippets.base.managers import ClientMatchRuleManager, SnippetManager


ONE_DAY = 60 * 60 * 24

JINJA_ENV = engines['backend']

SNIPPET_FETCH_TEMPLATE_HASH = hashlib.sha1(
    render_to_string(
        'base/fetch_snippets.jinja',
        {
            'snippet_ids': [],
            'snippets_json': '',
            'locale': 'xx',
            'settings': settings,
            'current_firefox_major_version': '00',
            'metrics_url': settings.METRICS_URL,
        }
    )).hexdigest()

SNIPPET_FETCH_TEMPLATE_AS_HASH = hashlib.sha1(
    render_to_string(
        'base/fetch_snippets_as.jinja',
        {
            'snippet_ids': [],
            'snippets_json': '',
            'locale': 'xx',
            'settings': settings,
            'current_firefox_major_version': '00',
            'metrics_url': settings.METRICS_URL,
        }
    )).hexdigest()

CHANNELS = ('release', 'beta', 'aurora', 'nightly')
FIREFOX_STARTPAGE_VERSIONS = ('1', '2', '3', '4', '5')
FENNEC_STARTPAGE_VERSIONS = ('1',)
SNIPPET_WEIGHTS = ((33, 'Appear 1/3rd as often as an average snippet'),
                   (50, 'Appear half as often as an average snippet'),
                   (66, 'Appear 2/3rds as often as an average snippet'),
                   (100, 'Appear as often as an average snippet'),
                   (150, 'Appear 1.5 times as often as an average snippet'),
                   (200, 'Appear twice as often as an average snippet'),
                   (300, 'Appear three times as often as an average snippet'))


def validate_xml_template(data):
    parser = xml.sax.make_parser()
    parser.setContentHandler(ContentHandler())
    parser.setFeature(xml.sax.handler.feature_external_ges, 0)

    data = data.encode('utf-8')
    xml_str = '<div>\n{0}</div>'.format(data)
    try:
        parser.parse(StringIO(xml_str))
    except xml.sax.SAXParseException as e:
        # getLineNumber() - 1 to get the correct line number because
        # we're wrapping contents into a div.
        error_msg = (
            'XML Error: {message} in line {line} column {column}').format(
                message=e.getMessage(), line=e.getLineNumber()-1, column=e.getColumnNumber())
        raise ValidationError(error_msg)
    return data


def validate_xml_variables(data):
    data_dict = json.loads(data)

    # set up a safer XML parser that does not resolve external
    # entities
    parser = xml.sax.make_parser()
    parser.setContentHandler(ContentHandler())
    parser.setFeature(xml.sax.handler.feature_external_ges, 0)

    for name, value in data_dict.items():
        # Skip over values that aren't strings.
        if not isinstance(value, basestring):
            continue

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


# Cache for compiled snippet templates. Using jinja's built in cache
# requires either an extra trip to the database/cache or jumping through
# hoops.
template_cache = LRUCache(100)


class SnippetBundle(object):
    """
    Group of snippets to be sent to a particular client configuration.
    """
    def __init__(self, client):
        self.client = client

    @cached_property
    def key(self):
        """A unique key for this bundle as a sha1 hexdigest."""
        # Key should consist of snippets that are in the bundle plus any
        # properties of the client that may change the snippet code
        # being sent.
        key_properties = [
            '{id}-{date}-{templatedate}'.format(id=snippet.id,
                                                date=snippet.modified.isoformat(),
                                                templatedate=snippet.template.modified.isoformat())
            for snippet in self.snippets]

        key_properties.extend(self.client)
        key_properties.extend([
            SNIPPET_FETCH_TEMPLATE_HASH,
            SNIPPET_FETCH_TEMPLATE_AS_HASH,
            util.current_firefox_major_version(),
        ])

        key_string = u'_'.join(key_properties)
        return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

    @property
    def cache_key(self):
        return u'bundle_' + self.key

    @property
    def cached(self):
        if cache.get(self.cache_key):
            return True

        # Check if available on S3 already.
        if default_storage.exists(self.filename):
            cache.set(self.cache_key, True, ONE_DAY)
            return True

        return False

    @property
    def expired(self):
        """
        If True, the code for this bundle should be re-generated before
        use.
        """
        return not cache.get(self.cache_key)

    @property
    def filename(self):
        return urljoin(settings.MEDIA_BUNDLES_ROOT, 'bundle_{0}.html'.format(self.key))

    @property
    def url(self):
        bundle_url = default_storage.url(self.filename)
        full_url = urljoin(settings.SITE_URL, bundle_url).split('?')[0]
        cdn_url = getattr(settings, 'CDN_URL', None)
        if cdn_url:
            full_url = urljoin(cdn_url, urlparse(bundle_url).path)

        return full_url

    @cached_property
    def snippets(self):
        return (Snippet.objects
                .filter(disabled=False)
                .match_client(self.client)
                .select_related('template')
                .prefetch_related('countries', 'exclude_from_search_providers')
                .filter_by_available())

    def generate(self):
        """Generate and save the code for this snippet bundle."""
        template = 'base/fetch_snippets.jinja'
        if self.client.startpage_version == '5':
            template = 'base/fetch_snippets_as.jinja'
        bundle_content = render_to_string(template, {
            'snippet_ids': [snippet.id for snippet in self.snippets],
            'snippets_json': json.dumps([s.to_dict() for s in self.snippets]),
            'client': self.client,
            'locale': self.client.locale,
            'settings': settings,
            'current_firefox_major_version': util.current_firefox_major_version(),
        })

        if isinstance(bundle_content, unicode):
            bundle_content = bundle_content.encode('utf-8')
        default_storage.save(self.filename, ContentFile(bundle_content))
        cache.set(self.cache_key, True, ONE_DAY)


class SnippetTemplate(models.Model):
    """
    A template for the body of a snippet. Can have multiple variables that the
    snippet will fill in.
    """
    name = models.CharField(max_length=255, unique=True)
    priority = models.BooleanField(
        verbose_name='Priority template', default=False,
        help_text='Set to true to display first in dropdowns for faster selections')
    hidden = models.BooleanField(help_text='Hide from template selection dropdown', default=False)
    code = models.TextField(validators=[validate_xml_template])

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def render(self, ctx):
        ctx.setdefault('snippet_id', 0)

        # Check if template is in cache, and cache it if it's not.
        cache_key = hashlib.sha1(self.code).hexdigest()
        template = template_cache.get(cache_key)
        if not template:
            template = JINJA_ENV.from_string(self.code)
            template_cache[cache_key] = template
        return template.render(ctx)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('-priority', 'name')


class SnippetTemplateVariable(models.Model):
    """
    A variable for a template that an individual snippet can fill in with its
    own content.
    """
    TEXT = 0
    IMAGE = 1
    SMALLTEXT = 2
    CHECKBOX = 3
    BODY = 4
    TYPE_CHOICES = ((BODY, 'Main Text'), (TEXT, 'Text'), (SMALLTEXT, 'Small Text'),
                    (IMAGE, 'Image'), (CHECKBOX, 'Checkbox'))

    template = models.ForeignKey(SnippetTemplate, related_name='variable_set')
    name = models.CharField(max_length=255)
    type = models.IntegerField(choices=TYPE_CHOICES, default=TEXT)
    description = models.TextField(blank=True, default='')

    def __unicode__(self):
        return u'{0}: {1}'.format(self.template.name, self.name)

    class Meta:
        ordering = ('name',)


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

    class Meta:
        ordering = ('description',)

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


class SnippetBaseModel(django_mysql.models.Model):
    def duplicate(self):
        snippet_copy = copy.copy(self)
        snippet_copy.id = None
        snippet_copy.disabled = True
        snippet_copy.name = '{0} - {1}'.format(
            self.name,
            datetime.strftime(datetime.now(), '%Y.%m.%d %H:%M:%S'))
        snippet_copy.save()

        for field in self._meta.get_fields():
            attr = getattr(self, field.name)
            if isinstance(attr, Manager):
                manager = attr
                if manager.__class__.__name__ == 'RelatedManager':
                    for itm in manager.all():
                        itm_copy = copy.copy(itm)
                        itm_copy.id = None
                        getattr(snippet_copy, field.name).add(itm_copy)
                elif manager.__class__.__name__ == 'ManyRelatedManager':
                    for snippet in manager.all():
                        getattr(snippet_copy, field.name).add(snippet)

        return snippet_copy

    class Meta:
        abstract = True


class Snippet(SnippetBaseModel):
    name = models.CharField(max_length=255, unique=True)
    template = models.ForeignKey(SnippetTemplate)
    data = models.TextField(default='{}', validators=[validate_xml_variables])

    disabled = models.BooleanField(default=True)

    countries = models.ManyToManyField(
        'TargetedCountry', blank=True, verbose_name='Targeted Countries')
    locales = models.ManyToManyField('TargetedLocale', blank=True, verbose_name='Targeted Locales')

    publish_start = models.DateTimeField(blank=True, null=True)
    publish_end = models.DateTimeField(blank=True, null=True)

    on_release = models.BooleanField(default=False, verbose_name='Release')
    on_beta = models.BooleanField(default=False, verbose_name='Beta')
    on_aurora = models.BooleanField(default=False, verbose_name='Aurora')
    on_nightly = models.BooleanField(default=False, verbose_name='Nightly')

    on_startpage_1 = models.BooleanField(default=False, verbose_name='Version 1')
    on_startpage_2 = models.BooleanField(default=True, verbose_name='Version 2')
    on_startpage_3 = models.BooleanField(default=True, verbose_name='Version 3')
    on_startpage_4 = models.BooleanField(default=True, verbose_name='Version 4')
    on_startpage_5 = models.BooleanField(default=False, verbose_name='Activity Stream')

    weight = models.IntegerField(
        'Prevalence', choices=SNIPPET_WEIGHTS, default=100,
        help_text='How often should this snippet be shown to users?')

    client_match_rules = models.ManyToManyField(
        ClientMatchRule, blank=True, verbose_name='Client Match Rules')

    exclude_from_search_providers = models.ManyToManyField(
        'SearchProvider', blank=True, verbose_name='Excluded Search Providers')

    campaign = models.CharField(
        max_length=255, blank=True, default='',
        help_text=('Optional campaign name. Will be added in the stats ping. '
                   'Will be used for snippet blocking if set.'))
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    client_options = django_mysql.models.DynamicField(
        default=None,
        spec={
            'version_lower_bound': unicode,
            'version_upper_bound': unicode,
            'has_fxaccount': unicode,
            'has_testpilot': unicode,
            'is_default_browser': unicode,
            'screen_resolutions': unicode,
            'profileage_lower_bound': int,
            'profileage_upper_bound': int,
        }
    )

    objects = SnippetManager()

    class Meta:
        ordering = ('-modified',)

    def to_dict(self):
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.render(),
            'countries': [],
            'campaign': self.campaign,
            'weight': self.weight,
            'exclude_from_search_engines': [],
            'client_options': self.client_options,
        }
        if self.id:
            data['countries'] = [country.code for country in self.countries.all()]
            data['exclude_from_search_engines'] = [
                provider.identifier for provider in self.exclude_from_search_providers.all()]

        return data

    def render(self):
        data = json.loads(self.data)
        snippet_id = self.id or 0
        data.setdefault('snippet_id', snippet_id)

        # Add snippet ID to template variables.
        for key, value in data.items():
            if isinstance(value, basestring):
                data[key] = value.replace(u'[[snippet_id]]', unicode(snippet_id))

        # Use a list for attrs to make the output order predictable.
        attrs = [('data-snippet-id', self.id),
                 ('data-weight', self.weight),
                 ('data-campaign', self.campaign),
                 ('class', 'snippet-metadata')]

        if self.id:
            countries = ','.join([country.code for country in self.countries.all()])
            if countries:
                attrs.append(('data-countries', countries))

            # Avoid using values_list() because django-cache-machine
            # does not support it.
            search_engine_identifiers = [
                provider.identifier for provider in self.exclude_from_search_providers.all()
            ]
            if search_engine_identifiers:
                attrs.append(('data-exclude-from-search-engines',
                              u','.join(search_engine_identifiers)))

        attr_string = u' '.join(u'{0}="{1}"'.format(key, value) for key, value in
                                attrs)

        rendered_snippet = u'<div {attrs}>{content}</div>'.format(
            attrs=attr_string,
            content=self.template.render(data)
        )

        return Markup(rendered_snippet)

    @property
    def channels(self):
        channels = []
        for channel in CHANNELS:
            if getattr(self, 'on_{0}'.format(channel), False):
                channels.append(channel)
        return channels

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('base.show', kwargs={'snippet_id': self.id})

    def save(self, *args, **kwargs):
        if self.client_options is None:
            self.client_options = {}
        return super(Snippet, self).save(*args, **kwargs)


class JSONSnippet(SnippetBaseModel):
    name = models.CharField(max_length=255, unique=True)
    disabled = models.BooleanField(default=True)

    icon = models.TextField(help_text='Icon should be a 96x96px PNG.')
    text = models.CharField(max_length=140,
                            help_text='Maximum length 140 characters.')
    url = models.CharField(max_length=500)

    countries = models.ManyToManyField(
        'TargetedCountry', blank=True, verbose_name='Targeted Countries')
    locales = models.ManyToManyField('TargetedLocale', blank=True, verbose_name='Targeted Locales')

    publish_start = models.DateTimeField(blank=True, null=True)
    publish_end = models.DateTimeField(blank=True, null=True)

    on_release = models.BooleanField(default=True, verbose_name='Release')
    on_beta = models.BooleanField(default=False, verbose_name='Beta')
    on_aurora = models.BooleanField(default=False, verbose_name='Aurora')
    on_nightly = models.BooleanField(default=False, verbose_name='Nightly')

    on_startpage_1 = models.BooleanField(default=True, verbose_name='Version 1')

    weight = models.IntegerField(
        'Prevalence', choices=SNIPPET_WEIGHTS, default=100,
        help_text='How often should this snippet be shown to users?')

    client_match_rules = models.ManyToManyField(
        ClientMatchRule, blank=True, verbose_name='Client Match Rules')

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = SnippetManager()

    class Meta:
        ordering = ('-modified',)
        verbose_name = 'JSON Snippet'

    def __unicode__(self):
        return self.name


def _generate_filename(instance, filename):
    """Generate a new unique filename while preserving the original
    filename extension. If an existing UploadedFile gets updated
    do not generate a new filename.
    """

    # Instance is new UploadedFile, generate a filename
    if not instance.id:
        ext = os.path.splitext(filename)[1]
        filename = str(uuid.uuid4()) + ext
        return os.path.join(settings.MEDIA_FILES_ROOT, filename)

    # Use existing filename.
    obj = UploadedFile.objects.get(id=instance.id)
    return obj.file.name


class UploadedFile(models.Model):
    file = models.FileField(upload_to=_generate_filename)
    name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    @property
    def url(self):
        full_url = urljoin(settings.SITE_URL, self.file.url).split('?')[0]
        cdn_url = getattr(settings, 'CDN_URL', None)
        if cdn_url:
            full_url = urljoin(cdn_url, urlparse(self.file.url).path)

        return full_url

    @property
    def snippets(self):
        return Snippet.objects.filter(
            models.Q(data__contains=self.file.url) |
            models.Q(template__code__contains=self.file.url)
        )


class SearchProvider(models.Model):
    name = models.CharField(max_length=255, unique=True)
    identifier = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('id',)


@python_2_unicode_compatible
class TargetedCountry(models.Model):
    code = models.CharField('Geolocation Country', max_length=16, unique=True)
    name = models.CharField(max_length=100)
    priority = models.BooleanField(default=False)

    def __str__(self):
        return u'{0} ({1})'.format(self.name, self.code)

    class Meta:
        ordering = ('-priority', 'name', 'code',)
        verbose_name_plural = 'targeted countries'


@python_2_unicode_compatible
class TargetedLocale(models.Model):
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    priority = models.BooleanField(default=False)

    class Meta:
        ordering = ('-priority', 'name', 'code')

    def __str__(self):
        return u'{} ({})'.format(self.name, self.code)
