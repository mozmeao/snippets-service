from datetime import datetime, timedelta

from django.apps import apps
from django.contrib import admin
from django.utils.encoding import force_text

from snippets.base import models


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

        if hasattr(queryset.model, 'jobs'):
            return queryset.filter(**{f'jobs__targets__{self.value()}': True}).distinct()
        return queryset.filter(**{f'targets__{self.value()}': True}).distinct()


class TemplateFilter(admin.SimpleListFilter):
    title = 'template type'
    parameter_name = 'template'
    LOOKUPS = sorted([
        (model.__name__, model.NAME)
        for model in apps.get_models()
        if issubclass(model, models.Template) and not model.__name__ == 'Template'
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


class RelatedPublishedASRSnippetFilter(admin.SimpleListFilter):
    title = 'Currently Published'
    parameter_name = 'is_currently_published'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        if hasattr(queryset.model, 'snippets'):
            if self.value() == 'yes':
                return queryset.filter(snippets__jobs__status=models.Job.PUBLISHED).distinct()
            elif self.value() == 'no':
                return queryset.exclude(snippets__jobs__status=models.Job.PUBLISHED).distinct()
        else:
            if self.value() == 'yes':
                return queryset.filter(jobs__status=models.Job.PUBLISHED).distinct()
            elif self.value() == 'no':
                return queryset.exclude(jobs__status=models.Job.PUBLISHED).distinct()


class IconRelatedPublishedASRSnippetFilter(RelatedPublishedASRSnippetFilter):
    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        icon_ids = []
        for icon in queryset.all():
            if icon.snippets.filter(jobs__status=models.Job.PUBLISHED).count():
                icon_ids.append(icon.id)

        if self.value() == 'yes':
            return queryset.filter(id__in=icon_ids)
        elif self.value() == 'no':
            return queryset.exclude(id__in=icon_ids)
