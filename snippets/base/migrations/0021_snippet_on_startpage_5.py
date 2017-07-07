# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0020_auto_20170726_0636'),
    ]

    operations = [
        migrations.AddField(
            model_name='snippet',
            name='on_startpage_5',
            field=models.BooleanField(default=False, verbose_name=b'Activity Stream'),
        ),
    ]
