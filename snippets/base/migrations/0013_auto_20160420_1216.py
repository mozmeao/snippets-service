# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0012_auto_20160420_1201'),
    ]

    operations = [
        migrations.AlterField(
            model_name='targetedcountry',
            name='code',
            field=models.CharField(unique=True, max_length=16, verbose_name=b'Geolocation Country'),
        ),
    ]
