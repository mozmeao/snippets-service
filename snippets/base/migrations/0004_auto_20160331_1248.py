# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_auto_20160324_1340'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='snippettemplate',
            options={'ordering': ('-priority', 'name')},
        ),
        migrations.AddField(
            model_name='snippettemplate',
            name='priority',
            field=models.BooleanField(default=False, help_text=b'Set to true to display first in dropdowns for faster selections', verbose_name=b'Priority template'),
        ),
    ]
