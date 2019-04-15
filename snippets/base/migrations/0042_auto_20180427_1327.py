# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def set_default_bounds_for_bookmarks_count(apps, schema_editor):
    # Part the Dynamic Column Removal Effort (Issue #940)
    pass

def noop(apps, schema_editor):
    # nothing needed to go back in time.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0041_snippettemplate_startpage'),
    ]

    operations = [
        migrations.RunPython(set_default_bounds_for_bookmarks_count, noop)
    ]
