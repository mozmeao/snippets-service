# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0006_auto_20160331_1320'),
    ]

    operations = [
        migrations.CreateModel(
            name='TargetedLocale',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=100)),
                ('priority', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('-priority', 'name', 'code'),
            },
        ),
        migrations.AddField(
            model_name='jsonsnippet',
            name='locales',
            field=models.ManyToManyField(to='base.TargetedLocale', verbose_name=b'Targeted Locales', blank=True),
        ),
        migrations.AddField(
            model_name='snippet',
            name='locales',
            field=models.ManyToManyField(to='base.TargetedLocale', verbose_name=b'Targeted Locales', blank=True),
        ),
    ]
