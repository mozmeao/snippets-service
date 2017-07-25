# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0019_auto_20170726_0635'),
    ]

    operations = [
        migrations.AlterField(
            model_name='snippet',
            name='on_release',
            field=models.BooleanField(default=False, verbose_name=b'Release'),
        ),
    ]
