# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from django_mysql.models.functions import AsType, ColumnAdd


def set_default_resolutions(apps, schema_editor):
    Snippet = apps.get_model('base', 'Snippet')
    resolutions = '0-1024;1024-1920;1920-50000'
    Snippet.objects.update(
        client_options=ColumnAdd('client_options',
                                 {'screen_resolutions': AsType(resolutions, 'CHAR')})
    )


def noop(apps, schema_editor):
    # nothing needed to go back in time.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0016_auto_20160419_1316'),
    ]

    operations = [
        migrations.RunPython(set_default_resolutions, noop),
    ]
