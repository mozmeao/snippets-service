# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_default_bounds_for_profileage(apps, schema_editor):
    # Part the Dynamic Column Removal Effort (Issue #940)
    pass

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
