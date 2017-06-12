# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from django_mysql.models.functions import AsType, ColumnAdd


def migrate_aboutaccounts_snippets(apps, schema_editor):
    """Migrate existing snippets that used about:accounts link filtering."""
    Snippet = apps.get_model('base', 'Snippet')
    Snippet.objects.filter(data__icontains='href=\\"about:accounts').update(
        client_options=ColumnAdd('client_options', {'has_fxaccount': AsType('yes', 'CHAR')})
    )
    Snippet.objects.exclude(data__icontains='href=\\"about:accounts').update(
        client_options=ColumnAdd('client_options', {'has_fxaccount': AsType('any', 'CHAR')})
    )


def set_has_testpilot(apps, schema_editor):
    Snippet = apps.get_model('base', 'Snippet')
    Snippet.objects.update(
        client_options=ColumnAdd('client_options', {'has_testpilot': AsType('any', 'CHAR')})
    )


def noop(apps, schema_editor):
    # nothing needed to go back in time.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0013_auto_20160420_1216'),
    ]

    operations = [
        migrations.RunPython(migrate_aboutaccounts_snippets, noop),
        migrations.RunPython(set_has_testpilot, noop),
    ]
