# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from product_details import product_details


def populate_country_names(apps, schema_editor):
    TargetedCountry = apps.get_model('base', 'TargetedCountry')
    countries = product_details.get_regions('en-US')
    for obj in TargetedCountry.objects.all():
        obj.name = countries.get(obj.code)
        obj.save()


def noop(apps, schema_editor):
    # Nothing needed to do to migrate backwards
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_auto_20160331_1311'),
    ]

    operations = [
        migrations.RunPython(populate_country_names, noop),
    ]
