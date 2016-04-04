# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_mysql.models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0008_auto_20160331_1405'),
    ]

    operations = [
        migrations.AddField(
            model_name='snippet',
            name='client_options',
            field=django_mysql.models.DynamicField(default=None),
        ),
    ]
