# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0011_auto_20160407_1435'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jsonsnippetlocale',
            name='snippet',
        ),
        migrations.RemoveField(
            model_name='snippetlocale',
            name='snippet',
        ),
        migrations.DeleteModel(
            name='JSONSnippetLocale',
        ),
        migrations.DeleteModel(
            name='SnippetLocale',
        ),
    ]
