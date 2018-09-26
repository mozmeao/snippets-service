import copy
import hashlib
import json
import os
import re
import uuid
from collections import namedtuple
from datetime import datetime
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.urls import reverse
from django.db import models
from django.db.models.manager import Manager
from django.template import engines
from django.utils.html import format_html

import django_mysql.models
from jinja2 import Markup
from jinja2.utils import LRUCache

from snippets.base import util
from snippets.base.fields import RegexField
from snippets.base.managers import ASRSnippetManager, ClientMatchRuleManager, SnippetManager
from snippets.base.validators import validate_xml_template


JINJA_ENV = engines['backend']

CHANNELS = ('release', 'beta', 'aurora', 'nightly', 'esr')
SNIPPET_WEIGHTS = ((33, 'Appear 1/3rd as often as an average snippet'),
                   (50, 'Appear half as often as an average snippet'),
                   (66, 'Appear 2/3rds as often as an average snippet'),
                   (100, 'Appear as often as an average snippet'),
                   (150, 'Appear 1.5 times as often as an average snippet'),
                   (200, 'Appear twice as often as an average snippet'),
                   (300, 'Appear three times as often as an average snippet'))


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

STATUS_CHOICES = {
    'Draft': 100,
    'Ready for review': 200,
    'Approved': 300,
    'Published': 400,
}


# Cache for compiled snippet templates. Using jinja's built in cache
# requires either an extra trip to the database/cache or jumping through
# hoops.
template_cache = LRUCache(100)


class SnippetTemplate(models.Model):
    """
    A template for the body of a snippet. Can have multiple variables that the
    snippet will fill in.
    """
    name = models.CharField(max_length=255, unique=True)
    code_name = models.CharField(max_length=255, unique=True)
    startpage = models.SmallIntegerField(default=4)
    version = models.CharField(max_length=10)
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
        cache_key = hashlib.sha1(self.code.encode('utf-8')).hexdigest()
        template = template_cache.get(cache_key)
        if not template:
            template = JINJA_ENV.from_string(self.code)
            template_cache[cache_key] = template
        return template.render(ctx)

    def __str__(self):
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

    template = models.ForeignKey(SnippetTemplate, on_delete=models.CASCADE,
                                 related_name='variable_set')
    name = models.CharField(max_length=255)
    type = models.IntegerField(choices=TYPE_CHOICES, default=TEXT)
    description = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return '{0}: {1}'.format(self.template.name, self.name)

    class Meta:
        ordering = ('order', 'name',)


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

    def __str__(self):
        return self.description


class SnippetBaseModel(django_mysql.models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def duplicate(self):
        snippet_copy = copy.copy(self)
        snippet_copy.id = None
        snippet_copy.published = False
        snippet_copy.uuid = uuid.uuid4()
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
    template = models.ForeignKey(SnippetTemplate, on_delete=models.PROTECT)
    data = models.TextField(default='{}')

    published = models.BooleanField(default=False)

    countries = models.ManyToManyField(
        'TargetedCountry', blank=True, verbose_name='Targeted Countries')
    locales = models.ManyToManyField('TargetedLocale', blank=True, verbose_name='Targeted Locales')

    publish_start = models.DateTimeField(blank=True, null=True)
    publish_end = models.DateTimeField(blank=True, null=True)

    on_release = models.BooleanField(default=False, verbose_name='Release')
    on_beta = models.BooleanField(default=False, verbose_name='Beta')
    on_aurora = models.BooleanField(default=False, verbose_name='Dev Edition (old Aurora)')
    on_nightly = models.BooleanField(default=False, verbose_name='Nightly')
    on_esr = models.BooleanField(default=False, verbose_name='ESR')

    on_startpage_1 = models.BooleanField(default=False, verbose_name='Version 1')
    on_startpage_2 = models.BooleanField(default=False, verbose_name='Version 2')
    on_startpage_3 = models.BooleanField(default=False, verbose_name='Version 3')
    on_startpage_4 = models.BooleanField(default=False, verbose_name='Version 4')
    on_startpage_5 = models.BooleanField(default=False, verbose_name='Activity Stream')
    on_startpage_6 = models.BooleanField(default=False, verbose_name='Activity Stream NG')

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
            'version_lower_bound': str,
            'version_upper_bound': str,
            'has_fxaccount': str,
            'has_testpilot': str,
            'is_developer': str,
            'is_default_browser': str,
            'screen_resolutions': str,
            'profileage_lower_bound': int,
            'profileage_upper_bound': int,
            'sessionage_lower_bound': int,
            'sessionage_upper_bound': int,
            'addon_check_type': str,
            'addon_name': str,
            'bookmarks_count_lower_bound': int,
            'bookmarks_count_upper_bound': int,
        }
    )

    objects = SnippetManager()

    class Meta:
        ordering = ('-modified',)
        permissions = (
            ('can_publish_on_release', 'Can publish snippets on Release'),
            ('can_publish_on_beta', 'Can publish snippets on Beta'),
            ('can_publish_on_aurora', 'Can publish snippets on Aurora'),
            ('can_publish_on_nightly', 'Can publish snippets on Nightly'),
            ('can_publish_on_esr', 'Can publish snippets on ESR'),
        )

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
            if isinstance(value, str):
                data[key] = value.replace(u'[[snippet_id]]', str(snippet_id))

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

        attr_string = ' '.join('{0}="{1}"'.format(key, value) for key, value in
                               attrs)

        rendered_snippet = '<div {attrs}>{content}</div>'.format(
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

    @property
    def dict_data(self):
        return json.loads(self.data)

    def set_data_property(self, name, value):
        data = json.loads(self.data)
        data[name] = value
        self.data = json.dumps(data)

    def get_preview_url(self):
        url = reverse('base.show_uuid', kwargs={'snippet_id': self.uuid})
        full_url = urljoin(settings.SITE_URL, url)
        return full_url

    def get_absolute_url(self):
        return reverse('base.show', kwargs={'snippet_id': self.id})

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.client_options is None:
            self.client_options = {}
        return super(Snippet, self).save(*args, **kwargs)


class SnippetNG(Snippet):
    class Meta:
        proxy = True
        verbose_name = 'Snippet NG'
        verbose_name_plural = 'Snippets NG'


class JSONSnippet(SnippetBaseModel):
    name = models.CharField(max_length=255, unique=True)
    published = models.BooleanField(default=False)

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
    on_esr = models.BooleanField(default=False, verbose_name='ESR')

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

    def __str__(self):
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

    def __str__(self):
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

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('id',)


class TargetedCountry(models.Model):
    code = models.CharField('Geolocation Country', max_length=16, unique=True)
    name = models.CharField(max_length=100)
    priority = models.BooleanField(default=False)

    def __str__(self):
        return '{} ({})'.format(self.name, self.code)

    class Meta:
        ordering = ('-priority', 'name', 'code',)
        verbose_name_plural = 'targeted countries'


class TargetedLocale(models.Model):
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    priority = models.BooleanField(default=False)

    class Meta:
        ordering = ('-priority', 'name', 'code')

    def __str__(self):
        return '{} ({})'.format(self.name, self.code)


class Target(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=255, unique=True)

    on_release = models.BooleanField(default=False, verbose_name='Release', db_index=True)
    on_beta = models.BooleanField(default=False, verbose_name='Beta', db_index=True)
    on_aurora = models.BooleanField(default=False, verbose_name='Dev Edition (old Aurora)',
                                    db_index=True)
    on_nightly = models.BooleanField(default=False, verbose_name='Nightly', db_index=True)
    on_esr = models.BooleanField(default=False, verbose_name='ESR', db_index=True)

    on_startpage_6 = models.BooleanField(default=True, verbose_name='Activity Stream Router',
                                         db_index=True)

    client_match_rules = models.ManyToManyField(
        ClientMatchRule, blank=True, verbose_name='Client Match Rules')
    jexl = django_mysql.models.DynamicField(
        default={},
        spec={
            'filtr_is_default_browser': str,
            'filtr_profile_age_created': int,
            'filtr_uses_firefox_sync': str,
            'filtr_is_developer': str,
        }
    )
    jexl_expr = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Campaign(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(
        max_length=255, blank=True, default='', unique=True,
        help_text=('Optional campaign slug. Will be added in the stats ping. '
                   'Will be used for snippet blocking if set.'))

    def __str__(self):
        return self.name


class ASRSnippet(django_mysql.models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255, unique=True)

    campaign = models.ForeignKey(Campaign, blank=True, null=True, on_delete=models.PROTECT)

    template = models.ForeignKey(SnippetTemplate, on_delete=models.PROTECT)
    data = models.TextField(default='{}')

    status = models.IntegerField(choices=[(y, x) for x, y in STATUS_CHOICES.items()],
                                 db_index=True, default=100)

    publish_start = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Publish Starts',
        help_text=format_html('See the current time in <a href="http://time.is/UTC">UTC</a>'))
    publish_end = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Publish Ends',
        help_text=format_html('See the current time in <a href="http://time.is/UTC">UTC</a>'))

    target = models.ForeignKey(Target, on_delete=models.PROTECT,
                               default=None, blank=True, null=True)

    weight = models.IntegerField(
        choices=SNIPPET_WEIGHTS, default=100,
        help_text='How often should this snippet be shown to users?')

    objects = ASRSnippetManager()

    class Meta:
        ordering = ['-modified']
        verbose_name = 'ASR Snippet'
        verbose_name_plural = 'ASR Snippets'

    def __str__(self):
        return self.name

    def render(self):
        data = json.loads(self.data)

        # Add snippet ID to template variables.
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value.replace('[[snippet_id]]', str(self.id))

        # Will be replaced with a more generic solution when we develop more AS
        # Router templates. See #565
        text, links = util.fluent_link_extractor(data.get('text', ''))
        data['text'] = text
        data['links'] = links

        rendered_snippet = {
            'id': str(self.id),
            'template': self.template.code_name,
            'template_version': self.template.version,
            'campaign': self.campaign.slug,
            'weight': self.weight,
            'content': data,
        }

        return rendered_snippet

    def get_preview_url(self):
        url = reverse('asr-preview', kwargs={'uuid': self.uuid})
        full_url = urljoin(settings.SITE_URL, url)
        return 'about:newtab?endpoint=' + full_url
