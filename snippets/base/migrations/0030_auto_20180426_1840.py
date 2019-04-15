
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def set_default_bounds_for_sessionage(apps, schema_editor):
    # Part the Dynamic Column Removal Effort (Issue #940)
    pass


def noop(apps, schema_editor):
    # nothing needed to go back in time.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0029_auto_20180426_0605'),
    ]

    operations = [
        migrations.RunPython(set_default_bounds_for_sessionage, noop)
    ]
