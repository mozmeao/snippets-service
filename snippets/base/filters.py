from distutils.util import strtobool

from django.db.models import Q

import django_filters

from snippets.base import models


class JobFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        label='Snippet Name',
        method='filter_name',
    )
    locale = django_filters.ModelChoiceFilter(
        label='Locale',
        empty_label='All Locales',
        queryset=models.Locale.objects.all(),
        field_name='snippet__locale',
    )
    only_scheduled = django_filters.ChoiceFilter(
        label='Include',
        method='filter_scheduled',
        empty_label=None,
        null_label='All Snipppets',
        null_value='all',
        choices=(('true', 'Jobs with Start and End Date'),
                 ('false', 'Jobs without Start and End Date'))
    )

    def __init__(self, data=None, *args, **kwargs):
        # Set only_scheduled=true as default since this is the most common scenario
        if data is not None:
            data = data.copy()
            data['only_scheduled'] = data.get('only_scheduled', '') or 'true'
        else:
            data = {
                'only_scheduled': 'true'
            }
        super().__init__(data, *args, **kwargs)

    def filter_name(self, queryset, name, value):
        # Filter based on Name, Snippet ID or Job ID
        if not value:
            return queryset

        try:
            value = int(value)
        except ValueError:
            # Not an ID
            return queryset.filter(snippet__name__icontains=f'{value}')
        else:
            return queryset.filter(
                Q(snippet__id=value) |
                Q(id=value)
            )

    def filter_scheduled(self, queryset, name, value):
        if value == 'all':
            return queryset

        try:
            value = strtobool(value)
        except ValueError:
            value = True

        if value:
            return queryset.exclude(publish_end=None)
        return queryset.filter(publish_end=None)

    @property
    def qs(self):
        # Return only Published and Scheduled Snippets
        qs = super().qs
        return qs.filter(
            Q(status=models.Job.PUBLISHED) |
            Q(status=models.Job.SCHEDULED)
        )

    class Meta:
        model = models.Job
        fields = []
