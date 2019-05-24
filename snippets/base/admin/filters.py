from distutils.util import strtobool
from datetime import datetime, timedelta

from django.apps import apps
from django.contrib import admin
from django.utils.encoding import force_text

from snippets.base.managers import SnippetQuerySet
from snippets.base.models import Template


class ModifiedFilter(admin.SimpleListFilter):
    title = 'Last modified'
    parameter_name = 'last_modified'

    def lookups(self, request, model_admin):
        return (
            ('24', '24 hours'),
            ('168', '7 days'),
            ('336', '14 days'),
            ('720', '30 days'),
            ('1440', '60 days'),
            ('all', 'All'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value or value == 'all':
            return queryset

        when = datetime.utcnow() - timedelta(hours=int(value))
        return queryset.exclude(modified__lt=when)

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == force_text(lookup),
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }


class ChannelFilter(admin.SimpleListFilter):
    title = 'Channel'
    parameter_name = 'channel'

    def lookups(self, request, model_admin):
        return (
            ('on_release', 'Release'),
            ('on_esr', 'ESR'),
            ('on_beta', 'Beta'),
            ('on_aurora', 'Dev (Aurora)'),
            ('on_nightly', 'Nightly'),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        if isinstance(queryset, SnippetQuerySet):
            return queryset.filter(**{self.value(): True})
        return queryset.filter(**{f'targets__{self.value()}': True}).distinct()


class ActivityStreamFilter(admin.SimpleListFilter):
    title = 'Activity Stream'
    parameter_name = 'is_activity_stream'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        elif self.value() == 'yes':
            return queryset.filter(on_startpage_5=True)
        elif self.value() == 'no':
            return queryset.exclude(on_startpage_5=True)


class ScheduledFilter(admin.SimpleListFilter):
    title = 'is scheduled'
    parameter_name = 'is_scheduled'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value is None:
            return queryset
        value = strtobool(value)
        if value:
            return queryset.exclude(publish_start=None, publish_end=None)
        else:
            return queryset.filter(publish_start=None, publish_end=None)


class TemplateFilter(admin.SimpleListFilter):
    title = 'template type'
    parameter_name = 'template'
    LOOKUPS = sorted([
        (model.__name__, model.NAME)
        for model in apps.get_models()
        if issubclass(model, Template) and not model.__name__ == 'Template'
    ], key=lambda x: x[1])

    def lookups(self, request, model_admin):
        return self.LOOKUPS

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        filters = {}
        for k, v in self.LOOKUPS:
            if value != k:
                filters['template_relation__{}'.format(k.lower())] = None

        return queryset.filter(**filters)
