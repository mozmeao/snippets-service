import copy
import io
import hashlib
import json
import os
import re
import uuid
import subprocess
from collections import namedtuple
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.core import validators as django_validators
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse
from django.db import models
from django.db.models.manager import Manager
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template import engines
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import format_html

import bleach
from PIL import Image
from jinja2 import Markup
from jinja2.utils import LRUCache
from taggit_selectize.managers import TaggableManager

import snippets.base.fields as snippet_fields
from snippets.base import managers, slack, util, validators


JINJA_ENV = engines['backend']

CHANNELS = ('release', 'beta', 'aurora', 'nightly', 'esr')
SNIPPET_WEIGHTS = (
    (2, 'Appear 1/50th as often as an average snippet'),
    (5, 'Appear 1/20th as often as an average snippet'),
    (10, 'Appear 1/10th as often as an average snippet'),
    (33, 'Appear 1/3rd as often as an average snippet'),
    (50, 'Appear half as often as an average snippet'),
    (66, 'Appear 2/3rds as often as an average snippet'),
    (100, 'Appear as often as an average snippet'),
    (150, 'Appear 1.5 times as often as an average snippet'),
    (200, 'Appear twice as often as an average snippet'),
    (300, 'Appear three times as often as an average snippet')
)


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
    code = models.TextField(validators=[validators.validate_xml_template])

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        ordering = ('-priority', 'name')

    def __str__(self):
        return self.name

    def render(self, ctx):
        ctx.setdefault('snippet_id', 0)

        # Check if template is in cache, and cache it if it's not.
        cache_key = hashlib.sha1(self.code.encode('utf-8')).hexdigest()
        template = template_cache.get(cache_key)
        if not template:
            template = JINJA_ENV.from_string(self.code)
            template_cache[cache_key] = template
        return template.render(ctx)

    def get_rich_text_variables(self):
        variables = (self.variable_set
                     .filter(type__in=[SnippetTemplateVariable.RICH_TEXT,
                                       SnippetTemplateVariable.BODY])
                     .values_list('name', flat=True))
        return variables


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
    RICH_TEXT = 5
    TYPE_CHOICES = (
        # Main Text is also Rich Text
        (BODY, 'Main Text'),
        # Text field that allows some HTML tags and attributes.
        (RICH_TEXT, 'Rich Text'),
        (TEXT, 'Text'),
        (SMALLTEXT, 'Small Text'),
        (IMAGE, 'Image'),
        (CHECKBOX, 'Checkbox'),
    )

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

    startpage_version = snippet_fields.RegexField()
    name = snippet_fields.RegexField()
    version = snippet_fields.RegexField()
    appbuildid = snippet_fields.RegexField()
    build_target = snippet_fields.RegexField()
    locale = snippet_fields.RegexField()
    channel = snippet_fields.RegexField()
    os_version = snippet_fields.RegexField()
    distribution = snippet_fields.RegexField()
    distribution_version = snippet_fields.RegexField()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = managers.ClientMatchRuleManager()

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


class SnippetBaseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def duplicate(self, creator):
        snippet_copy = copy.deepcopy(self)
        snippet_copy.id = None
        snippet_copy.created = None
        snippet_copy.modified = None
        snippet_copy.creator = creator
        snippet_copy.published = False
        snippet_copy.ready_for_review = False
        snippet_copy.uuid = uuid.uuid4()
        snippet_copy.name = '{0} - {1}'.format(
            self.name,
            datetime.strftime(timezone.now(), '%Y.%m.%d %H:%M:%S'))
        snippet_copy.save()

        for field in self._meta.get_fields():
            attr = getattr(self, field.name)
            if isinstance(attr, Manager):
                manager = attr
                if manager.__class__.__name__ == 'RelatedManager':
                    for itm in manager.all():
                        itm_copy = copy.deepcopy(itm)
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

    published = models.BooleanField(default=False, db_index=True)

    countries = models.ManyToManyField(
        'TargetedCountry', blank=True, verbose_name='Targeted Countries')
    locales = models.ManyToManyField('TargetedLocale', blank=True, verbose_name='Targeted Locales')

    publish_start = models.DateTimeField(blank=True, null=True)
    publish_end = models.DateTimeField(blank=True, null=True)

    on_release = models.BooleanField(default=False, verbose_name='Release', db_index=True)
    on_beta = models.BooleanField(default=False, verbose_name='Beta', db_index=True)
    on_aurora = models.BooleanField(default=False, verbose_name='Dev Edition (old Aurora)',
                                    db_index=True)
    on_nightly = models.BooleanField(default=False, verbose_name='Nightly', db_index=True)
    on_esr = models.BooleanField(default=False, verbose_name='ESR', db_index=True)

    on_startpage_1 = models.BooleanField(default=False, verbose_name='Version 1')
    on_startpage_2 = models.BooleanField(default=False, verbose_name='Version 2')
    on_startpage_3 = models.BooleanField(default=False, verbose_name='Version 3')
    on_startpage_4 = models.BooleanField(default=False, verbose_name='Version 4', db_index=True)
    on_startpage_5 = models.BooleanField(default=False, verbose_name='Activity Stream',
                                         db_index=True)

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

    ready_for_review = models.BooleanField(default=False)

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    client_option_version_lower_bound = models.CharField(max_length=20, default='any')
    client_option_version_upper_bound = models.CharField(max_length=20, default='any')
    client_option_has_fxaccount = models.CharField(max_length=10, default='any')
    client_option_is_developer = models.CharField(max_length=10, default='any')
    client_option_is_default_browser = models.CharField(max_length=10, default='any')
    client_option_profileage_lower_bound = models.IntegerField(default=-1)
    client_option_profileage_upper_bound = models.IntegerField(default=-1)
    client_option_sessionage_lower_bound = models.IntegerField(default=-1)
    client_option_sessionage_upper_bound = models.IntegerField(default=-1)
    client_option_bookmarks_count_lower_bound = models.IntegerField(default=-1)
    client_option_bookmarks_count_upper_bound = models.IntegerField(default=-1)
    client_option_addon_check_type = models.CharField(max_length=20, default='any')
    client_option_addon_name = models.CharField(max_length=100, default='', blank=True)
    client_option_screen_resolutions = models.CharField(
        max_length=150, default='0-1024;1024-1920;1920-50000')

    objects = managers.SnippetManager()

    class Meta:
        ordering = ('-modified',)
        permissions = (
            ('can_publish_on_release', 'Can publish snippets on Release'),
            ('can_publish_on_beta', 'Can publish snippets on Beta'),
            ('can_publish_on_aurora', 'Can publish snippets on Aurora'),
            ('can_publish_on_nightly', 'Can publish snippets on Nightly'),
            ('can_publish_on_esr', 'Can publish snippets on ESR'),
        )

    def get_client_options(self):
        return {
            'version_lower_bound': self.client_option_version_lower_bound,
            'version_upper_bound': self.client_option_version_upper_bound,
            'has_fxaccount': self.client_option_has_fxaccount,
            'is_developer': self.client_option_is_developer,
            'is_default_browser': self.client_option_is_default_browser,
            'profileage_lower_bound': self.client_option_profileage_lower_bound,
            'profileage_upper_bound': self.client_option_profileage_upper_bound,
            'sessionage_lower_bound': self.client_option_sessionage_lower_bound,
            'sessionage_upper_bound': self.client_option_sessionage_upper_bound,
            'bookmarks_count_lower_bound': self.client_option_bookmarks_count_lower_bound,
            'bookmarks_count_upper_bound': self.client_option_bookmarks_count_upper_bound,
            'addon_check_type': self.client_option_addon_check_type,
            'addon_name': self.client_option_addon_name,
            'screen_resolutions': self.client_option_screen_resolutions,
        }

    def to_dict(self):
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.render(),
            'countries': [],
            'campaign': self.campaign,
            'weight': self.weight,
            'exclude_from_search_engines': [],
            'client_options': self.get_client_options(),
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

    def get_admin_url(self, full=True):
        # Not using reverse() because the `admin:` namespace is not registered
        # in all clusters and app instances.
        url = '/admin/base/snippet/{}/change/'.format(self.id)
        if full:
            url = urljoin(settings.ADMIN_REDIRECT_URL or settings.SITE_URL, url)
        return url

    def get_absolute_url(self):
        return reverse('base.show', kwargs={'snippet_id': self.id})

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        return super(Snippet, self).save(*args, **kwargs)


def _generate_filename(instance, filename, root=None):
    """Generate a new unique filename while preserving the original
    filename extension. If an existing UploadedFile gets updated
    do not generate a new filename.
    """
    if not root:
        root = settings.MEDIA_ICONS_ROOT

    ext = os.path.splitext(filename)[1]
    filename = str(uuid.uuid4()) + ext
    return os.path.join(root, filename)


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
    filtr_is_default_browser = models.CharField(max_length=10, blank=True, default='')
    filtr_profile_age_created = models.CharField(max_length=250, blank=True, default='')
    filtr_firefox_version = models.CharField(max_length=10, blank=True, default='')
    filtr_previous_session_end = models.CharField(max_length=250, blank=True, default='')
    filtr_uses_firefox_sync = models.CharField(max_length=10, blank=True, default='')
    filtr_country = models.CharField(max_length=1250, blank=True, default='')
    filtr_is_developer = models.CharField(max_length=250, blank=True, default='')
    filtr_updates_enabled = models.CharField(max_length=10, blank=True, default='')
    filtr_updates_autodownload_enabled = models.CharField(max_length=10, blank=True, default='')
    filtr_current_search_engine = models.CharField(max_length=250, blank=True, default='')
    filtr_browser_addon = models.CharField(max_length=250, blank=True, default='')
    filtr_total_bookmarks_count = models.CharField(max_length=250, blank=True, default='')
    filtr_desktop_devices_count = models.CharField(max_length=250, blank=True, default='')
    filtr_mobile_devices_count = models.CharField(max_length=250, blank=True, default='')
    filtr_total_devices_count = models.CharField(max_length=250, blank=True, default='')
    filtr_can_install_addons = models.CharField(max_length=250, blank=True, default='')
    filtr_total_addons = models.CharField(max_length=250, blank=True, default='')
    filtr_firefox_service = models.CharField(max_length=250, blank=True, default='')

    jexl_expr = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Campaign(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(
        max_length=255, blank=False, unique=True,
        help_text=('Campaign slug. Will be added in the stats ping. '
                   'Will be used for snippet blocking if set.'))

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=False)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ('name',)

    def __str__(self):
        return '{}: {}'.format(self.name, self.description)


class Icon(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=255)
    height = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    image = models.ImageField(
        upload_to=_generate_filename,
        height_field='height',
        width_field='width',
        help_text=('PNG only. A reasonable file size is about 5 KiB. Note that updating the '
                   'image will update all snippets using this image.'),
    )

    def __str__(self):
        return self.name

    @property
    def url(self):
        full_url = urljoin(settings.SITE_URL, self.image.url).split('?')[0]
        cdn_url = getattr(settings, 'CDN_URL', None)
        if cdn_url:
            full_url = urljoin(cdn_url, urlparse(self.image.url).path)

        return full_url

    @property
    def snippets(self):
        """Returns a Queryset of ASRSnippets using this icon. Needs this fancy code
        b/c icons have multiple relations with multiple Templates.

        """
        all_snippets = []
        for relation_name, relation in self._meta.fields_map.items():
            if issubclass(relation.related_model, Template):
                related_snippets = (getattr(self, relation_name)
                                    .values_list('snippet__id', flat=True))

                if related_snippets:
                    all_snippets.extend(related_snippets)

        return ASRSnippet.objects.filter(pk__in=all_snippets).distinct()

    def clean(self):
        super().clean()

        # If not new file, just return
        if not isinstance(self.image.file, InMemoryUploadedFile):
            return

        im = Image.open(self.image.open())
        if im.format != 'PNG':
            raise ValidationError({'image': 'Upload only PNG images.'})

        if (settings.IMAGE_MAX_DIMENSION and
            (im.width > settings.IMAGE_MAX_DIMENSION or
             im.height > settings.IMAGE_MAX_DIMENSION)):
            raise ValidationError({
                'image': 'Upload an image at most {0}x{0}. This image is {1}x{2}.'.format(
                    settings.IMAGE_MAX_DIMENSION, im.width, im.height)
            })

        # Optimize only when settings is True
        if settings.IMAGE_OPTIMIZE:
            self.image.seek(0)
            cmd = subprocess.run(
                ['pngquant', '-', '--quality=95', '--skip-if-larger', '--speed=1', '--strip'],
                input=self.image.read(),
                stdout=subprocess.PIPE
            )
            if cmd.stdout:
                new_image = io.BytesIO(cmd.stdout)
                self.image.file = InMemoryUploadedFile(
                    new_image, 'ImageField', self.image.name,
                    'image/png', len(new_image.read()), None
                )

        if settings.IMAGE_MAX_SIZE > 0 and self.image.size > settings.IMAGE_MAX_SIZE:
            raise ValidationError({
                'image': 'Upload an image less than {0:.0f} KiB. This image is {1:.0f} KiB.'.format(
                    settings.IMAGE_MAX_SIZE / 1024, self.image.size / 1024)
            })


class Template(models.Model):
    snippet = models.OneToOneField('ASRSnippet', related_name='template_relation',
                                   on_delete=models.CASCADE)

    @property
    def subtemplate(self):
        if type(self) is not Template:
            # We 're already in the subclass
            return self

        for field in self._meta.fields_map.values():
            if issubclass(field.related_model, Template):
                try:
                    return getattr(self, field.name)
                except Template.DoesNotExist:
                    continue

    def _convert_special_buttons(self, data):
        local_data = copy.deepcopy(data)
        to_delete = []
        to_append = {}
        for key, value in local_data.items():
            if key == 'button_url':
                if value == 'special:appMenu':
                    to_append['button_action'] = 'OPEN_APPLICATIONS_MENU'
                    to_append['button_action_args'] = 'appMenu'
                    to_delete.append(key)
                elif value == 'special:accounts':
                    to_append['button_action'] = 'SHOW_FIREFOX_ACCOUNTS'
                    to_delete.append(key)
                elif value.startswith('special:about'):
                    to_append['button_action'] = 'OPEN_ABOUT_PAGE'
                    to_append['button_action_args'] = value.rsplit(':', 1)[1]
                elif value == 'special:monitor':
                    to_append['button_action'] = 'ENABLE_FIREFOX_MONITOR'
                    to_append['button_action_args'] = {
                        'url': ('https://monitor.firefox.com/oauth/init?'
                                'utm_source=desktop-snippet&utm_term=[[job_id]]&'
                                'utm_content=[[channels]]&utm_campaign=[[campaign_slug]]&'
                                'entrypoint=snippets&form_type=button'),
                        'flowRequestParams': {
                            'entrypoint': 'snippets',
                            'utm_term': 'snippet-job-[[job_id]]',
                            'form_type': 'button'
                        }
                    }
                    to_delete.append(key)

        for key in to_delete:
            local_data.pop(key)

        local_data.update(to_append)

        return local_data

    def _process_rendered_data(self, data):
        # Convert links in text fields in fluent format.
        data = util.fluent_link_extractor(data, self.get_rich_text_fields())

        # Convert button special links
        data = self._convert_special_buttons(data)

        # Remove values that are empty strings
        data = {k: v for k, v in data.items() if v != ''}

        return data

    def get_rich_text_fields(self):
        raise Exception('Not Implemented')

    def render(self):
        raise Exception('Not Implemented')

    @property
    def version(self):
        return self.VERSION

    def get_main_body(self, bleached=False):
        body = self.text
        if bleached:
            body = bleach.clean(body, tags=[], strip=True).strip()
        return body

    def get_main_url(self):
        button_url = getattr(self, 'button_url', '')
        if button_url:
            return button_url

        # Try to find the URL in the body
        url = ''
        body = self.get_main_body()
        match = re.search('href="(?P<link>https?://.+?)"', body)
        if match:
            url = match.groupdict()['link']

        return url

    def get_url_fields(self):
        """ Returns a list of URL field names of the model. """
        fields = []
        for field in self._meta.fields:
            if isinstance(field, snippet_fields.URLField):
                fields.append(field.name)
        return fields

    def add_utm_params(self):
        """Appends UTM params to links in both Rich Text Fields and URL Fields.

        UTM params get placeholders -like `[[snippet_id]]`- that will get
        replaced with actual values when the snippet is rendered to go into a
        Bundle.

        This separates of snippet content from targeting attributes and allows
        the same snippet to be scheduled for different channels and during
        campaigns.

        """
        params = {
            'utm_source': 'desktop-snippet',
            'utm_medium': 'snippet',
            'utm_campaign': '[[campaign_slug]]',
            'utm_term': '[[job_id]]',
            'utm_content': '[[channels]]',
        }

        def _replacer(matchobj):
            return util.urlparams(matchobj.group(), replace=False, **params)

        for field in self.get_rich_text_fields():
            value = getattr(self, field)
            if value:
                value = re.sub('(?<=href=")(https://.+?)(?=")', _replacer, value)
                setattr(self, field, value)

        for field in self.get_url_fields():
            value = getattr(self, field)
            # Check that value not starts with special so we don't alter special links
            if value and not value.startswith('special:'):
                value = util.urlparams(value, replace=False, **params)
                setattr(self, field, value)

    def clean(self):
        super().clean()
        validators.validate_as_router_fluent_variables(self, self.get_rich_text_fields())
        self.add_utm_params()


class SimpleTemplate(Template):
    VERSION = '1.0.0'
    NAME = 'Simple'

    title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='simple_title_icons',
        verbose_name='Title Icon',
        help_text=('Small icon that shows up before the title / text. 64x64px.'
                   'PNG. Grayscale.')
    )
    title = models.CharField(
        max_length=255, blank=True,
        help_text='Snippet title displayed before snippet text.',
    )
    text = models.TextField(
        help_text='Main body text of snippet. HTML subset allowed: i, b, u, strong, em, br',
    )
    icon = models.ForeignKey(
        Icon,
        on_delete=models.PROTECT,
        related_name='simple_icons',
        help_text='Snippet icon. 192x192px PNG.'
    )
    button_label = models.CharField(
        max_length=50, blank=True,
        verbose_name='Button Label',
        help_text=('Text for a button next to main snippet text that '
                   'links to button_url. Requires button_url.'),
    )
    button_color = models.CharField(
        verbose_name='Button Color',
        max_length=20, blank=True,
        help_text='The text color of the button. Valid CSS color.',
    )
    button_background_color = models.CharField(
        verbose_name='Button Background Color',
        max_length=20, blank=True,
        help_text='The text color of the button. Valid CSS color.',
    )
    button_url = snippet_fields.URLField(
        verbose_name='Button URL',
        max_length=500,
        blank=True,
        help_text='A url, button_label links to this',
    )
    section_title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        verbose_name='Section Title Icon',
        related_name='simple_section_icons',
        help_text=('Section title icon. 16x16px. PNG. '
                   'section_title_text must also be specified to display.'),
    )
    section_title_text = models.CharField(
        verbose_name='Section Title Text',
        blank=True,
        max_length=255,
        help_text='Section title text. section_title_icon must also be specified to display.',
    )
    section_title_url = snippet_fields.URLField(
        verbose_name='Section Title URL',
        blank=True,
        max_length=500,
        help_text='A url, section_title_text links to this',
    )
    tall = models.BooleanField(
        default=False, blank=True,
        help_text=('To be used by fundraising only, increases height '
                   'to roughly 120px. Defaults to false.'),
    )
    block_button_text = models.CharField(
        verbose_name='Block Button Text',
        max_length=50, default='Remove this',
        help_text='Tooltip text used for dismiss button.'
    )
    do_not_autoblock = models.BooleanField(
        verbose_name='Do Not Autoblock',
        default=False, blank=True,
        help_text=('Used to prevent blocking the snippet after the '
                   'CTA (link or button) has been clicked.'),
    )

    @property
    def code_name(self):
        return 'simple_snippet'

    def render(self):
        data = {
            'title_icon': self.title_icon.url if self.title_icon else '',
            'title': self.title,
            'text': self.text,
            'icon': self.icon.url if self.icon else '',
            'button_label': self.button_label,
            'button_url': self.button_url,
            'button_color': self.button_color,
            'button_background_color': self.button_background_color,
            'section_title_icon': self.section_title_icon.url if self.section_title_icon else '',
            'section_title_text': self.section_title_text,
            'section_title_url': self.section_title_url,
            'tall': self.tall,
            'block_button_text': self.block_button_text,
            'do_not_autoblock': self.do_not_autoblock,
        }
        data = self._process_rendered_data(data)
        return data

    def get_rich_text_fields(self):
        return ['text']


class FundraisingTemplate(Template):
    """Also known as EOY Template"""
    VERSION = '1.0.0'
    NAME = 'Fundraising'

    donation_form_url = snippet_fields.URLField(
        verbose_name='Donation Form URL',
        default='https://donate.mozilla.org/?utm_source=desktop-snippet&utm_medium=snippet',
        max_length=500,
    )
    currency_code = models.CharField(
        verbose_name='Currency Code',
        max_length=10, default='usd'
    )
    locale = models.CharField(max_length=10, default='en-US')
    title = models.CharField(
        max_length=255, blank=True,
        help_text='Snippet title displayed before snippet text.',
    )
    text = models.TextField(
        help_text='Main body text of snippet. HTML subset allowed: i, b, u, strong, em, br'
    )
    text_color = models.CharField(
        verbose_name='Text Color',
        max_length=10, blank=True
    )
    background_color = models.CharField(
        verbose_name='Background Color',
        max_length=10, blank=True
    )
    highlight_color = models.CharField(
        verbose_name='Highlight Color',
        max_length=10,
        help_text='Paragraph em highlight color.',
        blank=True,
        default='#FFE900',
    )
    donation_amount_first = models.PositiveSmallIntegerField(verbose_name='First')
    donation_amount_second = models.PositiveSmallIntegerField(verbose_name='Second')
    donation_amount_third = models.PositiveSmallIntegerField(verbose_name='Third')
    donation_amount_fourth = models.PositiveSmallIntegerField(verbose_name='Fourth')
    selected_button = models.CharField(
        verbose_name='Selected Button',
        max_length=25,
        choices=(
            ('donation_amount_first', 'First'),
            ('donation_amount_second', 'Second'),
            ('donation_amount_third', 'Third'),
            ('donation_amount_fourth', 'Fourth'),
        ),
        default='donation_amount_second',
        help_text='Donation amount button that\'s selected by default.',
    )
    icon = models.ForeignKey(
        Icon,
        on_delete=models.PROTECT,
        related_name='fundraising_icons',
        help_text='Snippet icon. 192x192px PNG.'
    )
    title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        verbose_name='Title Icon',
        on_delete=models.SET_NULL,
        related_name='fundraising_title_icons',
        help_text=('Small icon that shows up before the title / text. 64x64px.'
                   'PNG. Grayscale.')
    )
    button_label = models.CharField(
        verbose_name='Button Label',
        max_length=50,
        help_text=('Text for a button next to main snippet text that links '
                   'to button_url. Requires button_url.'),
    )
    button_color = models.CharField(
        verbose_name='Button Color',
        max_length=20, blank=True,
        help_text='defaults to firefox theme'
    )
    button_background_color = models.CharField(
        verbose_name='Button Background Color',
        max_length=20, blank=True, help_text='defaults to firefox theme')
    monthly_checkbox_label_text = models.CharField(
        verbose_name='Monthly Checkbox Label Text',
        max_length=255,
        default='Make my donation monthly',
    )
    test = models.CharField(max_length=10,
                            choices=(('', 'Default'),
                                     ('bold', 'Bold'),
                                     ('takeover', 'Takeover')),
                            blank=True,
                            help_text=('Different styles for the snippet.'))
    block_button_text = models.CharField(
        verbose_name='Block Button Text',
        max_length=50, default='Remove this',
        help_text='Tooltip text used for dismiss button.'
    )
    do_not_autoblock = models.BooleanField(
        verbose_name='Do Not Autoblock',
        default=False, blank=True,
        help_text=('Used to prevent blocking the snippet after the '
                   'CTA (link or button) has been clicked.'),
    )

    @property
    def code_name(self):
        return 'eoy_snippet'

    def render(self):
        data = {
            'donation_form_url': self.donation_form_url,
            'currency_code': self.currency_code,
            'locale': self.locale,
            'title': self.title,
            'text': self.text,
            'text_color': self.text_color,
            'background_color': self.background_color,
            'highlight_color': self.highlight_color,
            'donation_amount_first': self.donation_amount_first,
            'donation_amount_second': self.donation_amount_second,
            'donation_amount_third': self.donation_amount_third,
            'donation_amount_fourth': self.donation_amount_fourth,
            'selected_button': self.selected_button,
            'icon': self.icon.url if self.icon else '',
            'title_icon': self.title_icon.url if self.title_icon else '',
            'button_label': self.button_label,
            'button_color': self.button_color,
            'button_background_color': self.button_background_color,
            'monthly_checkbox_label_text': self.monthly_checkbox_label_text,
            'test': self.test,
            'block_button_text': self.block_button_text,
            'do_not_autoblock': self.do_not_autoblock,
        }
        data = self._process_rendered_data(data)
        return data

    def get_rich_text_fields(self):
        return ['text']


class FxASignupTemplate(Template):
    VERSION = '1.0.0'
    NAME = 'FxA Sign up'

    scene1_title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='Scene 1 Title Icon',
        related_name='fxasignup_scene1_title_icons',
        help_text=('Small icon that shows up before the title / text. 64x64px.'
                   'PNG. Grayscale.')
    )
    scene1_title = models.CharField(
        verbose_name='Scene 1 Title',
        max_length=255, blank=True,
        help_text='Snippet title displayed before snippet text.',
    )
    scene1_text = models.TextField(
        verbose_name='Scene 1 Text',
        help_text='Main body text of snippet. HTML subset allowed: i, b, u, strong, em, br.',
    )
    scene1_icon = models.ForeignKey(
        Icon,
        on_delete=models.PROTECT,
        verbose_name='Scene 1 Icon',
        related_name='fxasignup_scene1_icons',
        help_text='Snippet icon. 192x192px PNG.')
    scene1_button_label = models.CharField(
        verbose_name='Scene 1 Button Label',
        max_length=50,
        default='Learn more',
        help_text='Label for the button on Scene 1 that leads to Scene 2.'
    )
    scene1_button_color = models.CharField(
        verbose_name='Scene 1 Button Color',
        max_length=20, blank=True,
        help_text=('The text color of the button. Valid CSS color. '
                   'Defaults to Firefox Theme Color.'),
    )
    scene1_button_background_color = models.CharField(
        verbose_name='Scene 1 Button Background Color',
        max_length=20, blank=True,
        help_text=('The background color of the button. Valid CSS color. '
                   'Defaults to Firefox Theme Color.'),
    )
    scene1_section_title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        verbose_name='Section Title Icon',
        related_name='fxa_scene1_section_icons',
        help_text=('Section title icon. 16x16px. PNG. '
                   'scene1_section_title_text must also be specified to display.'),
    )
    scene1_section_title_text = models.CharField(
        verbose_name='Section Title Text',
        blank=True,
        max_length=255,
        help_text=('Section title text. scene1_section_title_icon must also '
                   'be specified to display.'),
    )
    scene1_section_title_url = snippet_fields.URLField(
        verbose_name='Section Title URL',
        blank=True,
        max_length=500,
        help_text='A url, scene1_section_title_text links to this',
    )

    ###
    # Scene 2
    ###
    scene2_title = models.CharField(
        verbose_name='Scene 2 Title',
        max_length=255, blank=True,
        help_text='Title displayed before text in scene 2.',
    )
    scene2_text = models.TextField(
        verbose_name='Scene 2 Text',
        help_text='Scene 2 main text. HTML subset allowed: i, b, u, strong, em, br.',
    )
    scene2_button_label = models.CharField(
        verbose_name='Scene 2 Button Label',
        max_length=50,
        default='Sign me up',
        help_text='Label for form submit button.',
    )
    scene2_email_placeholder_text = models.CharField(
        verbose_name='Scene 2 Email Placeholder Text',
        max_length=255,
        default='Your email here',
        help_text='Value to show while input is empty.',
    )
    scene2_dismiss_button_text = models.CharField(
        verbose_name='Scene 2 Dismiss Button Text',
        max_length=50,
        default='Dismiss',
        help_text='Label for the dismiss button on Scene 2.'
    )

    ###
    # Extras
    ###
    utm_term = models.CharField(
        verbose_name='UTM Term',
        max_length=100, blank=True,
        help_text='Value to pass through to GA as utm_term.',
    )
    utm_campaign = models.CharField(
        verbose_name='UTM Campaign',
        max_length=100, blank=True,
        help_text='Value to pass through to GA as utm_campaign.',
    )
    block_button_text = models.CharField(
        verbose_name='Block Button Text',
        max_length=50, default='Remove this',
        help_text='Tooltip text used for dismiss button.'
    )
    do_not_autoblock = models.BooleanField(
        verbose_name='Do Not Autoblock',
        default=False, blank=True,
        help_text=('Used to prevent blocking the snippet after the '
                   'CTA (link or button) has been clicked.'),
    )

    @property
    def code_name(self):
        return 'fxa_signup_snippet'

    def render(self):
        data = {
            'scene1_title_icon': self.scene1_title_icon.url if self.scene1_title_icon else '',
            'scene1_title': self.scene1_title,
            'scene1_text': self.scene1_text,
            'scene1_icon': self.scene1_icon.url if self.scene1_icon else '',
            'scene1_button_label': self.scene1_button_label,
            'scene1_button_color': self.scene1_button_color,
            'scene1_button_background_color': self.scene1_button_background_color,
            'scene1_section_title_icon':
                self.scene1_section_title_icon.url if self.scene1_section_title_icon else '',
            'scene1_section_title_text': self.scene1_section_title_text,
            'scene1_section_title_url': self.scene1_section_title_url,
            'scene2_title': self.scene2_title,
            'scene2_text': self.scene2_text,
            'scene2_button_label': self.scene2_button_label,
            'scene2_email_placeholder_text': self.scene2_email_placeholder_text,
            'scene2_dismiss_button_text': self.scene2_dismiss_button_text,
            'utm_term': self.utm_term,
            'utm_campaign': self.utm_campaign,
            'block_button_text': self.block_button_text,
            'do_not_autoblock': self.do_not_autoblock,
        }
        data = self._process_rendered_data(data)
        return data

    def get_rich_text_fields(self):
        return ['scene1_text', 'scene2_text']

    def get_main_body(self, bleached=False):
        body = self.scene1_text
        if bleached:
            body = bleach.clean(body, tags=[], strip=True).strip()
        return body


class NewsletterTemplate(Template):
    VERSION = '1.0.0'
    NAME = 'Newsletter'

    scene1_title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='Scene 1 Title Icon',
        related_name='newsletter_scene1_title_icons',
        help_text=('Small icon that shows up before the title / text. 64x64px.'
                   'PNG. Grayscale.')
    )
    scene1_title = models.CharField(
        verbose_name='Scene 1 Title',
        max_length=255, blank=True,
        help_text='Snippet title displayed before snippet text.',
    )
    scene1_text = models.TextField(
        verbose_name='Scene 1 Text',
        help_text='Main body text of snippet. HTML subset allowed: i, b, u, strong, em, br.',
    )
    scene1_icon = models.ForeignKey(
        Icon,
        on_delete=models.PROTECT,
        verbose_name='Scene 1 Icon',
        related_name='newsletter_scene1_icons',
        help_text='Snippet icon. 192x192px PNG.')
    scene1_button_label = models.CharField(
        verbose_name='Scene 1 Button Label',
        max_length=50,
        default='Learn more',
        help_text='Label for the button on Scene 1 that leads to Scene 2.'
    )
    scene1_button_color = models.CharField(
        verbose_name='Scene 1 Button Color',
        max_length=20, blank=True,
        help_text=('The text color of the button. Valid CSS color. '
                   'Defaults to Firefox Theme Color.'),
    )
    scene1_button_background_color = models.CharField(
        verbose_name='Scene 1 Button Background Color',
        max_length=20, blank=True,
        help_text=('The background color of the button. Valid CSS color. '
                   'Defaults to Firefox Theme Color.'),
    )
    scene1_section_title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        verbose_name='Section Title Icon',
        related_name='newsletter_scene1_section_icons',
        help_text=('Section title icon. 16x16px. PNG. '
                   'scene1_section_title_text must also be specified to display.'),
    )
    scene1_section_title_text = models.CharField(
        verbose_name='Section Title Text',
        blank=True,
        max_length=255,
        help_text=('Section title text. scene1_section_title_icon must also '
                   'be specified to display.'),
    )
    scene1_section_title_url = snippet_fields.URLField(
        verbose_name='Section Title URL',
        blank=True,
        max_length=500,
        help_text='A url, scene1_section_title_text links to this',
    )

    ###
    # Scene 2
    ###
    scene2_title = models.CharField(
        verbose_name='Scene 2 Title',
        max_length=255, blank=True,
        help_text='Title displayed before text in scene 2.',
    )
    scene2_text = models.TextField(
        verbose_name='Scene 2 Text',
        help_text='Scene 2 main text. HTML subset allowed: i, b, u, strong, em, br.',
    )
    scene2_button_label = models.CharField(
        verbose_name='Scene 2 Button Label',
        max_length=50,
        default='Sign me up',
        help_text='Label for form submit button.',
    )
    scene2_email_placeholder_text = models.CharField(
        verbose_name='Scene 2 Email Placeholder Text',
        max_length=255,
        default='Your email here',
        help_text='Value to show while input is empty.',
    )
    scene2_dismiss_button_text = models.CharField(
        verbose_name='Scene 2 Dismiss Button Text',
        max_length=50,
        default='Dismiss',
        help_text='Label for the dismiss button on Scene 2.'
    )

    scene2_newsletter = models.CharField(
        verbose_name='Scene 2 Newsletter',
        max_length=50,
        default='mozilla-foundation',
        help_text=('Newsletter/basket id user is subscribing to. Must be a value from the "Slug" '
                   'column here: https://basket.mozilla.org/news/.'),
    )
    scene2_privacy_html = models.TextField(
        verbose_name='Scene 2 Privacy HTML',
        help_text='Text and link next to the privacy checkbox. Must link to a privacy policy.',
    )

    locale = models.CharField(
        max_length=10,
        default='en-US',
        help_text='String for the newsletter locale code.',
    )
    success_text = models.TextField(
        verbose_name='Success Text',
        help_text='Text of success message after form submission.',
    )
    error_text = models.TextField(
        verbose_name='Error Text',
        help_text='Text of error message if form submission fails.',
    )
    retry_button_label = models.CharField(
        verbose_name='Retry Button Label',
        max_length=50,
        default='Try again',
        help_text='Button label after a failed form submission'
    )

    ###
    # Extras
    ###
    block_button_text = models.CharField(
        verbose_name='Block Button Text',
        max_length=50, default='Remove this',
        help_text='Tooltip text used for dismiss button.'
    )
    do_not_autoblock = models.BooleanField(
        verbose_name='Do Not Autoblock',
        default=False, blank=True,
        help_text=('Used to prevent blocking the snippet after the '
                   'CTA (link or button) has been clicked.'),
    )

    @property
    def code_name(self):
        return 'newsletter_snippet'

    def render(self):
        data = {
            'scene1_title_icon': self.scene1_title_icon.url if self.scene1_title_icon else '',
            'scene1_title': self.scene1_title,
            'scene1_text': self.scene1_text,
            'scene1_icon': self.scene1_icon.url if self.scene1_icon else '',
            'scene1_button_label': self.scene1_button_label,
            'scene1_button_color': self.scene1_button_color,
            'scene1_button_background_color': self.scene1_button_background_color,
            'scene1_section_title_icon':
                self.scene1_section_title_icon.url if self.scene1_section_title_icon else '',
            'scene1_section_title_text': self.scene1_section_title_text,
            'scene1_section_title_url': self.scene1_section_title_url,
            'scene2_title': self.scene2_title,
            'scene2_text': self.scene2_text,
            'scene2_button_label': self.scene2_button_label,
            'scene2_email_placeholder_text': self.scene2_email_placeholder_text,
            'scene2_dismiss_button_text': self.scene2_dismiss_button_text,
            'scene2_newsletter': self.scene2_newsletter,
            'scene2_privacy_html': self.scene2_privacy_html,
            'locale': self.locale,
            'success_text': self.success_text,
            'error_text': self.error_text,
            'block_button_text': self.block_button_text,
            'do_not_autoblock': self.do_not_autoblock,
            'retry_button_label': self.retry_button_label,
        }
        data = self._process_rendered_data(data)
        return data

    def get_rich_text_fields(self):
        return [
            'scene1_text',
            'scene2_privacy_html',
        ]

    def get_main_body(self, bleached=False):
        body = self.scene1_text
        if bleached:
            body = bleach.clean(body, tags=[], strip=True).strip()
        return body


class SendToDeviceTemplate(Template):
    VERSION = '1.0.0'
    NAME = 'Send to Device'

    scene1_title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='Scene 1 Title Icon',
        related_name='sendtodevice_scene1_title_icons',
        help_text=('Small icon that shows up before the title / text. 64x64px.'
                   'PNG. Grayscale.')
    )
    scene1_title = models.CharField(
        verbose_name='Scene 1 Title',
        max_length=255, blank=True,
        help_text='Snippet title displayed before snippet text.',
    )
    scene1_text = models.TextField(
        verbose_name='Scene 1 Text',
        help_text='Main body text of snippet. HTML subset allowed: i, b, u, strong, em, br.',
    )
    scene1_icon = models.ForeignKey(
        Icon,
        on_delete=models.PROTECT,
        verbose_name='Scene 1 Icon',
        related_name='sendtodevice_scene1_icons',
        help_text='Snippet icon. 192x192 PNG.')
    scene1_button_label = models.CharField(
        verbose_name='Scene 1 Button Label',
        max_length=50,
        default='Learn more',
        help_text='Label for the button on Scene 1 that leads to Scene 2.'
    )
    scene1_button_color = models.CharField(
        verbose_name='Scene 1 Button Color',
        max_length=20, blank=True,
        help_text=('The text color of the button. Valid CSS color. '
                   'Defaults to Firefox Theme Color.'),
    )
    scene1_button_background_color = models.CharField(
        verbose_name='Scene 1 Button Background Color',
        max_length=20, blank=True,
        help_text=('The background color of the button. Valid CSS color. '
                   'Defaults to Firefox Theme Color.'),
    )
    scene1_section_title_icon = models.ForeignKey(
        Icon,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        verbose_name='Section Title Icon',
        related_name='sendtodevice_scene1_section_icons',
        help_text=('Section title icon. 16x16px. PNG. '
                   'scene1_section_title_text must also be specified to display.'),
    )
    scene1_section_title_text = models.CharField(
        verbose_name='Section Title Text',
        blank=True,
        max_length=255,
        help_text=('Section title text. scene1_section_title_icon must also '
                   'be specified to display.'),
    )
    scene1_section_title_url = snippet_fields.URLField(
        verbose_name='Section Title URL',
        blank=True,
        max_length=500,
        help_text='A url, scene1_section_title_text links to this',
    )

    ###
    # Scene 2
    ###
    scene2_title = models.CharField(
        verbose_name='Scene 2 Title',
        max_length=255, blank=True,
        help_text='Title displayed before text in scene 2.',
    )
    scene2_text = models.TextField(
        verbose_name='Scene 2 Text',
        help_text='Scene 2 main text. HTML subset allowed: i, b, u, strong, em, br.',
    )
    scene2_icon = models.ForeignKey(
        Icon,
        on_delete=models.PROTECT,
        verbose_name='Scene 2 Icon',
        related_name='sendtodevice_scene2_icons',
        help_text='Image to display above the form. 192x192px PNG.'
    )
    scene2_button_label = models.CharField(
        verbose_name='Scene 2 Button Label',
        max_length=50,
        default='Send',
        help_text='Label for form submit button.',
    )
    scene2_input_placeholder = models.CharField(
        verbose_name='Scene 2 Input Placeholder',
        max_length=255,
        default='Your email here',
        help_text='Placeholder text for email / phone number field.',
    )
    scene2_dismiss_button_text = models.CharField(
        verbose_name='Scene 2 Dismiss Button Text',
        max_length=50,
        default='Dismiss',
        help_text='Label for the dismiss button on Scene 2.'
    )
    scene2_disclaimer_html = models.TextField(
        verbose_name='Scene 2 Disclaimer HTML',
        help_text='Text and link underneath the input box.',
    )

    locale = models.CharField(
        max_length=10,
        default='EN',
        help_text='Two to five character string for the locale code. Default "EN".',
    )
    country = models.CharField(
        max_length=10,
        default='us',
        help_text='Two character string for the country code (used for SMS). Default "us".',
    )
    include_sms = models.BooleanField(
        verbose_name='Include SMS',
        blank=True,
        default=False,
        help_text='Defines whether SMS is available.',
    )
    message_id_sms = models.CharField(
        verbose_name='Message ID for SMS',
        max_length=100,
        blank=True,
        help_text='Newsletter/basket id representing the SMS message to be sent.',
    )
    message_id_email = models.CharField(
        verbose_name='Message ID for Email',
        max_length=100,
        help_text=('Newsletter/basket id representing the email message to be sent. Must be '
                   'a value from the "Slug" column here: https://basket.mozilla.org/news/.'),
    )

    success_title = models.TextField(
        verbose_name='Success Title',
        help_text='Title of success message after form submission.',
    )
    success_text = models.TextField(
        verbose_name='Success Text',
        help_text='Text of success message after form submission.',
    )
    error_text = models.TextField(
        verbose_name='Error Text',
        help_text='Text of error message if form submission fails.',
    )
    retry_button_label = models.CharField(
        verbose_name='Retry Button Label',
        max_length=50,
        default='Try again',
        help_text='Button label after a failed form submission'
    )

    ###
    # Extras
    ###
    block_button_text = models.CharField(
        verbose_name='Block Button Text',
        max_length=50, default='Remove this',
        help_text='Tooltip text used for dismiss button.'
    )
    do_not_autoblock = models.BooleanField(
        verbose_name='Do Not Autoblock',
        default=False, blank=True,
        help_text=('Used to prevent blocking the snippet after the '
                   'CTA (link or button) has been clicked.'),
    )

    @property
    def code_name(self):
        return 'send_to_device_snippet'

    def render(self):
        data = {
            'scene1_title_icon': self.scene1_title_icon.url if self.scene1_title_icon else '',
            'scene1_title': self.scene1_title,
            'scene1_text': self.scene1_text,
            'scene1_icon': self.scene1_icon.url if self.scene1_icon else '',
            'scene1_button_label': self.scene1_button_label,
            'scene1_button_color': self.scene1_button_color,
            'scene1_button_background_color': self.scene1_button_background_color,
            'scene1_section_title_icon':
                self.scene1_section_title_icon.url if self.scene1_section_title_icon else '',
            'scene1_section_title_text': self.scene1_section_title_text,
            'scene1_section_title_url': self.scene1_section_title_url,
            'scene2_title': self.scene2_title,
            'scene2_text': self.scene2_text,
            'scene2_icon': self.scene2_icon.url if self.scene2_icon else '',
            'scene2_button_label': self.scene2_button_label,
            'scene2_input_placeholder': self.scene2_input_placeholder,
            'scene2_dismiss_button_text': self.scene2_dismiss_button_text,
            'scene2_disclaimer_html': self.scene2_disclaimer_html,
            'locale': self.locale,
            'country': self.country,
            'include_sms': self.include_sms,
            'message_id_sms': self.message_id_sms,
            'message_id_email': self.message_id_email,
            'success_title': self.success_title,
            'success_text': self.success_text,
            'error_text': self.error_text,
            'block_button_text': self.block_button_text,
            'do_not_autoblock': self.do_not_autoblock,
            'retry_button_label': self.retry_button_label,
        }
        data = self._process_rendered_data(data)
        return data

    def get_rich_text_fields(self):
        return [
            'scene1_text',
            'scene2_text',
            'scene2_disclaimer_html',
        ]

    def get_main_body(self, bleached=False):
        body = self.scene1_text
        if bleached:
            body = bleach.clean(body, tags=[], strip=True).strip()
        return body


class SimpleBelowSearchTemplate(Template):
    VERSION = '1.0.1'
    NAME = 'Simple below Search Bar'

    title = models.CharField(
        max_length=255, blank=True,
        help_text='Snippet title displayed before snippet text.',
    )
    text = models.TextField(
        help_text='Main body text of snippet. HTML subset allowed: i, b, u, strong, em, br',
    )
    icon = models.ForeignKey(
        Icon,
        on_delete=models.PROTECT,
        related_name='simple_below_search_icons',
        help_text='Snippet icon. 192x192px PNG.'
    )
    button_label = models.CharField(
        verbose_name='Button Label',
        max_length=50, blank=True,
        help_text=('Text for a button next to main snippet text that '
                   'links to button_url. Requires button_url.'),
    )
    button_color = models.CharField(
        verbose_name='Button Color',
        max_length=20, blank=True,
        help_text='The text color of the button. Valid CSS color.',
    )
    button_background_color = models.CharField(
        verbose_name='Button Background Color',
        max_length=20, blank=True,
        help_text='The text color of the button. Valid CSS color.',
    )
    button_url = snippet_fields.URLField(
        verbose_name='Button URL',
        max_length=500,
        blank=True,
        help_text='A url, button_label links to this',
    )
    block_button_text = models.CharField(
        verbose_name='Block Button Text',
        max_length=50, default='Remove this',
        help_text='Tooltip text used for dismiss button.'
    )
    do_not_autoblock = models.BooleanField(
        verbose_name='Do Not Autoblock',
        default=False, blank=True,
        help_text=('Used to prevent blocking the snippet after the '
                   'CTA (link or button) has been clicked.'),
    )

    @property
    def code_name(self):
        return 'simple_below_search_snippet'

    def render(self):
        data = {
            'title': self.title,
            'text': self.text,
            'icon': self.icon.url,
            'button_label': self.button_label,
            'button_url': self.button_url,
            'button_color': self.button_color,
            'button_background_color': self.button_background_color,
            'block_button_text': self.block_button_text,
            'do_not_autoblock': self.do_not_autoblock,
        }
        data = self._process_rendered_data(data)
        return data

    def get_rich_text_fields(self):
        return ['text']


class Locale(models.Model):
    name = models.CharField(max_length=100)
    # Code can be a locale without territory information (e.g. `en`), a locale
    # with territory information (e.g. `en-us`) or a combination of multiple
    # locales with or without territory information (e.g. es-mx,es-ar). This is
    # useful to target locales like LatAm Spanish which are different from
    # Spain's Spanish (`es-es`). We add commas at the start and at the end of
    # the code string to create queries matching the exact code in
    # ASRSnippetManager.
    code = models.CharField(
        max_length=255, unique=True,
        validators=[django_validators.RegexValidator(regex=r'^,?([A-Za-z-]+,?)+$')],
        help_text=(
            'Comma separated list of locales with or without territory information. E.g '
            '`en-us` and `es-mx,es-ar`'
        )
    )
    translations = models.TextField(
        blank=True, validators=[validators.validate_json_data], default='{}',
        help_text='JSON dictionary with Template fields as keys and localized strings as values.'
    )

    def save(self, *args, **kwargs):
        # Make sure that code always starts and ends with `,` and it's always
        # lowercase.
        self.code = self.code.lower()
        if self.code[0] != ',':
            self.code = ',' + self.code
        if self.code[-1] != ',':
            self.code = self.code + ','
        super().save(*args, **kwargs)

    class Meta:
        ordering = ('name', 'code')

    def __str__(self):
        return self.name


class Job(models.Model):
    DRAFT = 0
    SCHEDULED = 100
    PUBLISHED = 200
    CANCELED = 300
    COMPLETED = 400

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.IntegerField(choices=((DRAFT, 'Draft'),
                                          (SCHEDULED, 'Scheduled'),
                                          (PUBLISHED, 'Published'),
                                          (CANCELED, 'Canceled'),
                                          (COMPLETED, 'Completed')),
                                 default=DRAFT,
                                 db_index=True,
                                 editable=False)

    snippet = models.ForeignKey('ASRSnippet', null=False, blank=False, on_delete=models.PROTECT,
                                related_name='jobs')

    campaign = models.ForeignKey(Campaign, blank=True, null=True, on_delete=models.PROTECT,
                                 related_name='jobs')
    weight = models.IntegerField(
        choices=SNIPPET_WEIGHTS, default=100,
        help_text='How often should this snippet be shown to users?')
    targets = models.ManyToManyField(Target, default=None, blank=False, related_name='jobs')

    publish_start = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Publish Starts',
        help_text=format_html(
            'See the current time in <a target="_blank" href="https://time.is/UTC">UTC</a>'))
    publish_end = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Publish Ends',
        help_text=format_html(
            'See the current time in <a target="_blank" href="https://time.is/UTC">UTC</a>'))
    distribution = models.ForeignKey(
        'Distribution',
        on_delete=models.PROTECT,
        related_name='jobs',
        help_text=('Set a Distribution for this Job. It should be normally '
                   'left to Default. Useful for running Normandy experiments.'),
    )

    metric_last_update = models.DateTimeField('Last Update', default='1970-01-01', editable=False)
    metric_impressions = models.PositiveIntegerField(default=0, editable=False)
    metric_clicks = models.PositiveIntegerField(default=0, editable=False)
    metric_blocks = models.PositiveIntegerField(default=0, editable=False)

    objects = managers.JobManager()

    class Meta:
        ordering = ['-modified']

    def __str__(self):
        return str(self.uuid)

    def clean(self):
        super().clean()

        self.publish_start = max(
            datetime.utcnow() + timedelta(minutes=settings.SNIPPETS_PUBLICATION_OFFSET),
            self.publish_start or datetime.utcnow())

        if ((all([self.publish_start, self.publish_end]) and
             self.publish_start >= self.publish_end)):
            raise ValidationError('Publish start must come before publish end.')

    def render(self):
        rendered_snippet = self.snippet.render()

        rendered_snippet['id'] = str(self.id)

        # Add weight info
        rendered_snippet['weight'] = self.weight

        # Add campaign info
        campaign_slug = self.campaign.slug if self.campaign else ''
        rendered_snippet = util.deep_search_and_replace(
            rendered_snippet, '[[campaign_slug]]', campaign_slug)
        # Add job id info
        rendered_snippet = util.deep_search_and_replace(
            rendered_snippet, '[[job_id]]', str(self.id))

        # Include campaign key when needed
        if campaign_slug:
            rendered_snippet['campaign'] = campaign_slug

        # Add Channels
        CHANNELS_MAP = {
            'release': 'REL',
            'esr': 'ESR',
            'beta': 'BETA',
            'aurora': 'DEV',
            'nightly': 'NIGHTLY',
        }
        channels = '_'.join([
            # Iterate CHANNELS_MAP instead of self.channels to ensure order
            CHANNELS_MAP[channel] for channel in CHANNELS_MAP if channel in self.channels
        ])
        rendered_snippet = util.deep_search_and_replace(rendered_snippet, '[[channels]]', channels)

        # Add JEXL targeting
        rendered_snippet['targeting'] = ' && '.join(
            [target.jexl_expr for
             target in self.targets.all().order_by('id') if
             target.jexl_expr]
        )

        return rendered_snippet

    @property
    def channels(self):
        channels = []

        for target in self.targets.all():
            for channel in CHANNELS:
                if getattr(target, 'on_{0}'.format(channel), False):
                    channels.append(channel)
        return set(channels)

    def change_status(self, status, user=None, send_slack=True):
        if self.status == status:
            return

        self.status = status
        self.save()

        if user:
            LogEntry.objects.log_action(
                user_id=user.pk,
                content_type_id=get_content_type_for_model(self).pk,
                object_id=self.id,
                object_repr=str(self),
                action_flag=CHANGE,
                change_message='Changed status to {}'.format(self.get_status_display())
            )

        if send_slack:
            template = 'slack/job_{}.jinja.json'.format(self.get_status_display().lower())
            data = render_to_string(template, context={'job': self})
            slack._send_slack(data)

    def get_admin_url(self, full=True):
        # Not using reverse() because the `admin:` namespace is not registered
        # in all clusters and app instances.
        url = '/admin/base/job/{}/change/'.format(self.id)
        if full:
            url = urljoin(settings.ADMIN_REDIRECT_URL or settings.SITE_URL, url)
        return url

    def duplicate(self, creator):
        job_copy = copy.deepcopy(self)
        job_copy.id = None
        job_copy.created = None
        job_copy.modified = None
        job_copy.status = self.DRAFT
        job_copy.creator = creator
        job_copy.uuid = uuid.uuid4()
        job_copy.save()

        for field in self._meta.get_fields():
            attr = getattr(self, field.name, None)
            if isinstance(attr, Manager):
                manager = attr
                if manager.__class__.__name__ == 'RelatedManager':
                    for itm in manager.all():
                        itm_copy = copy.deepcopy(itm)
                        itm_copy.id = None
                        getattr(job_copy, field.name).add(itm_copy)
                elif manager.__class__.__name__ == 'ManyRelatedManager':
                    for snippet in manager.all():
                        getattr(job_copy, field.name).add(snippet)

        return job_copy

    def analytics_export(self):
        body = self.snippet.template_ng.get_main_body(bleached=True)
        url = self.snippet.template_ng.get_main_url()
        export = {
            'id': self.id,
            'name': self.snippet.name,
            'campaign': self.campaign.name if self.campaign else '',
            'category': self.snippet.category.name if self.snippet.category else '',
            'url': url,
            'body': body,
            'tags': ','.join([tag.name for tag in self.snippet.tags.all().order_by('name')]),
            'snippet_id': self.snippet.id,
        }
        return export


class ASRSnippet(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255, unique=True)

    category = models.ForeignKey(Category, blank=True, null=True, on_delete=models.PROTECT,
                                 related_name='snippets')

    tags = TaggableManager(blank=True)

    status = models.IntegerField('Content Status',
                                 choices=[(100, 'Draft'),
                                          (200, 'Ready for review'),
                                          (300, 'Approved')],
                                 db_index=True, default=100)

    locale = models.ForeignKey('Locale', blank=False, null=True, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-modified']
        verbose_name = 'ASR Snippet'
        verbose_name_plural = 'ASR Snippets'
        permissions = (
            ('publish_on_release', 'Publish snippets on Release'),
            ('publish_on_beta', 'Publish snippets on Beta'),
            ('publish_on_aurora', 'Publish snippets on Aurora'),
            ('publish_on_nightly', 'Publish snippets on Nightly'),
            ('publish_on_esr', 'Publish snippets on ESR'),
        )

    def __str__(self):
        return self.name

    @property
    def template_ng(self):
        return self.template_relation.subtemplate

    def render(self, preview=False):
        template_code_name = self.template_ng.code_name
        template_version = self.template_ng.version
        data = self.template_ng.render()

        rendered_snippet = {
            'template': template_code_name,
            'template_version': template_version,
            'content': data,
        }

        if preview:
            for variable in ['campaign_slug', 'channels', 'snippet_id', 'job_id']:
                rendered_snippet = util.deep_search_and_replace(
                    rendered_snippet, f'[[{variable}]]', '')

            rendered_snippet['id'] = 'preview-{}'.format(self.id)
            # Always set do_not_autoblock when previewing.
            rendered_snippet['content']['do_not_autoblock'] = True
        else:
            data = util.deep_search_and_replace(data, '[[snippet_id]]', str(self.id))

        return rendered_snippet

    def get_preview_url(self, dark=False):
        theme = 'light'
        if dark:
            theme = 'dark'
        url = reverse('asr-preview', kwargs={'uuid': self.uuid})
        full_url = urljoin(settings.SITE_URL, url)
        return 'about:newtab?theme={}&endpoint={}'.format(theme, full_url)

    def get_admin_url(self, full=True):
        # Not using reverse() because the `admin:` namespace is not registered
        # in all clusters and app instances.
        url = '/admin/base/asrsnippet/{}/change/'.format(self.id)
        if full:
            url = urljoin(settings.ADMIN_REDIRECT_URL or settings.SITE_URL, url)
        return url

    def duplicate(self, creator):
        snippet_copy = copy.deepcopy(self)
        snippet_copy.id = None
        snippet_copy.created = None
        snippet_copy.modified = None
        snippet_copy.status = STATUS_CHOICES['Draft']
        snippet_copy.creator = creator
        snippet_copy.uuid = uuid.uuid4()
        snippet_copy.name = '{0} - {1}'.format(
            self.name,
            datetime.strftime(timezone.now(), '%Y.%m.%d %H:%M:%S'))
        snippet_copy.save()

        # From https://djangosnippets.org/snippets/1040/ Needed due to the
        # model inheritance where setting instance.pk = None isn't enough.
        def copy_model_instance(obj):
            initial = dict(
                [(f.name, getattr(obj, f.name)) for f in obj._meta.fields
                 if not isinstance(f, models.AutoField) and f not in obj._meta.parents.values()]
            )
            return obj.__class__(**initial)
        new_template = copy_model_instance(self.template_ng)
        new_template.snippet = snippet_copy
        new_template.save()

        for field in self._meta.get_fields():
            attr = getattr(self, field.name, None)
            if isinstance(attr, Manager):
                manager = attr
                if manager.__class__.__name__ == 'RelatedManager':
                    for itm in manager.all():
                        itm_copy = copy.deepcopy(itm)
                        itm_copy.id = None
                        getattr(snippet_copy, field.name).add(itm_copy)
                elif manager.__class__.__name__ == 'ManyRelatedManager':
                    for snippet in manager.all():
                        getattr(snippet_copy, field.name).add(snippet)

        return snippet_copy


# We could connect the signal to specific senders using `sender` argument but
# we would have to connect each template class separately which will create
# another thing to do when we add more templates and that can be potentially
# forgotten. Instead we're collecting all signals and we do instance type
# checking.
@receiver(post_save, dispatch_uid='update_asrsnippet_modified')
def update_asrsnippet_modified_date(sender, instance, **kwargs):
    if kwargs['raw']:
        return

    now = timezone.now()
    snippets = None

    if isinstance(instance, (Template, Job)):
        snippets = [instance.snippet.pk]

    elif isinstance(instance, (Campaign, Target)):
        snippets = {id for id in instance.jobs.values_list('snippet__pk', flat=True)}

    elif isinstance(instance, Icon):
        # Convert the value_list Queryset to a list, required for the upcoming
        # update() query to work.
        snippets = {id for id in instance.snippets.values_list('pk', flat=True)}

    elif isinstance(instance, DistributionBundle):
        snippets = {id for id in instance.distributions.values_list('jobs__snippet_id', flat=True)}

    if snippets:
        ASRSnippet.objects.filter(pk__in=snippets).update(modified=now)


class Addon(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(unique=True)
    guid = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name


class Distribution(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name


class DistributionBundle(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=255, unique=True)
    code_name = models.CharField(max_length=100, unique=True)
    distributions = models.ManyToManyField(
        'Distribution'
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.code_name = self.code_name.lower()

        super().save(*args, **kwargs)
