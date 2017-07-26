# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0018_auto_20170614_0925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='snippet',
            name='campaign',
            field=models.CharField(default=b'', help_text=b'Optional campaign name. Will be added in the stats ping. Will be used for snippet blocking if set.', max_length=255, blank=True),
        ),
    ]
