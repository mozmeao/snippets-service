# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_isdefaultbrowser_clientoption(apps, schema_editor):
    # Part the Dynamic Column Removal Effort (Issue #940)
    pass

def noop(apps, schema_editor):
    # nothing needed to go back in time.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0015_auto_20160420_1317'),
    ]

    operations = [
        migrations.RunPython(set_isdefaultbrowser_clientoption, noop),
    ]
