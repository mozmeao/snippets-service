# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0004_auto_20160331_1248'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='targetedcountry',
            options={'ordering': ('-priority', 'name', 'code'), 'verbose_name_plural': 'targeted countries'},
        ),
        migrations.AddField(
            model_name='targetedcountry',
            name='name',
            field=models.CharField(default='TBU', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='targetedcountry',
            name='priority',
            field=models.BooleanField(default=False),
        ),
    ]
