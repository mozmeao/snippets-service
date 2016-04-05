# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from product_details import product_details


def migrate_locales(apps, schema_editor):
    languages = {}
    for code, value in product_details.languages.items():
        languages[code.lower()] = value['English']

    for model in ['SnippetLocale', 'JSONSnippetLocale']:
        SnippetLocale = apps.get_model('base', model)
        TargetedLocale = apps.get_model('base', 'TargetedLocale')

        for obj in SnippetLocale.objects.all():
            name = languages.get(obj.locale)
            locale = TargetedLocale.objects.get_or_create(code=obj.locale, name=name)[0]
            obj.snippet.locales.add(locale)


def noop(apps, schema_editor):
    # nothing needed to go back in time.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_auto_20160331_1344'),
    ]

    operations = [
        migrations.RunPython(migrate_locales, noop),
    ]
