import csv
from datetime import datetime

from django.db import transaction
from django.http import HttpResponse


@transaction.atomic
def duplicate_snippets_action(modeladmin, request, queryset):
    for snippet in queryset:
        snippet.duplicate(request.user)
duplicate_snippets_action.short_description = 'Duplicate selected snippets'  # noqa


def export_as_csv(modeladmin, request, queryset):
    """Adapted from https://books.agiliq.com/projects/django-admin-cookbook/en/latest/export.html"""
    meta = modeladmin.model._meta
    field_names = [field.name for field in meta.fields]
    filename = f'{meta}-{datetime.today().strftime("%Y-%m-%d-%H-%M")}'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}.csv'.format(filename)
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])

    return response
export_as_csv.short_description = 'Export Selected to CSV'  # noqa
