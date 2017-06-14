# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from django_mysql.models.functions import AsType, ColumnAdd


def set_default_bounds_for_profileage(apps, schema_editor):
    Snippet = apps.get_model('base', 'Snippet')
    Snippet.objects.update(
        client_options=ColumnAdd('client_options',
                                 {'profileage_lower_bound': AsType(-1, 'INTEGER')})
    )
    Snippet.objects.update(
        client_options=ColumnAdd('client_options',
                                 {'profileage_upper_bound': AsType(-1, 'INTEGER')})
    )


def noop(apps, schema_editor):
    # nothing needed to go back in time.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0017_auto_20170609_1246'),
    ]

    operations = [
        migrations.RunPython(set_default_bounds_for_profileage, noop)
    ]
