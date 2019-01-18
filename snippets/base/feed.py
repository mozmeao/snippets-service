from datetime import timedelta
from distutils.util import strtobool
from textwrap import dedent
from urllib.parse import urlparse

from django.conf import settings

import django_filters
from django_ical.views import ICalFeed

from snippets.base import models


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class ASRSnippetFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    locale = CharInFilter(field_name='locales__code', lookup_expr='in')
    only_scheduled = django_filters.ChoiceFilter(
        method='filter_scheduled', choices=(('true', 'Yes'),
                                            ('false', 'No'),
                                            ('all', 'All')))

    def filter_scheduled(self, queryset, name, value):
        if value == 'all':
            return queryset

        value = strtobool(value)

        if value:
            return queryset.exclude(publish_start=None, publish_end=None)

        return queryset.filter(publish_start=None, publish_end=None)

    class Meta:
        model = models.ASRSnippet
        fields = []


class SnippetsFeed(ICalFeed):
    timezone = 'UTC'
    title = 'Snippets'

    def __call__(self, request, *args, **kwargs):
        self.request = request
        return super().__call__(request, *args, **kwargs)

    @property
    def product_id(self):
        return '//{}/Snippets?{}'.format(urlparse(settings.SITE_URL).netloc,
                                         self.request.GET.urlencode())

    def items(self):
        queryset = (models.ASRSnippet.objects
                    .filter(for_qa=False, status=models.STATUS_CHOICES['Published'])
                    .order_by('publish_start'))
        filtr = ASRSnippetFilter(self.request.GET, queryset=queryset)
        return filtr.qs

    def item_title(self, item):
        return item.name

    def item_link(self, item):
        return item.get_admin_url()

    def item_description(self, item):
        description = dedent('''\
        Channels: {}
        Locales: {}'
        Preview Link: {}
        '''.format(', '.join(item.channels),
                   ', '.join(item.locales.values_list('name', flat=True)),
                   item.get_preview_url()))
        return description

    def item_start_datetime(self, item):
        return item.publish_start or item.created

    def item_end_datetime(self, item):
        return item.publish_end or (self.item_start_datetime(item) + timedelta(days=365))

    def item_created(self, item):
        return item.created

    def item_updateddate(self, item):
        return item.modified
