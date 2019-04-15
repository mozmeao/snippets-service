# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def migrate_aboutaccounts_snippets(apps, schema_editor):
    # Part the Dynamic Column Removal Effort (Issue #940)
    pass

def set_has_testpilot(apps, schema_editor):
    # Part the Dynamic Column Removal Effort (Issue #940)
    pass

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
