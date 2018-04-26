# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from django_mysql.models.functions import AsType, ColumnAdd


def set_default_bounds_for_sessionage(apps, schema_editor):
    Snippet = apps.get_model('base', 'Snippet')
    Snippet.objects.update(
        client_options=ColumnAdd('client_options',
                                 {'sessionage_lower_bound': AsType(-1, 'INTEGER')})
    )
    Snippet.objects.update(
        client_options=ColumnAdd('client_options',
                                 {'sessionage_upper_bound': AsType(-1, 'INTEGER')})
    )


def noop(apps, schema_editor):
    # nothing needed to go back in time.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0028_auto_20180426_1021'),
    ]

    operations = [
        migrations.RunPython(set_default_bounds_for_sessionage, noop)
    ]
