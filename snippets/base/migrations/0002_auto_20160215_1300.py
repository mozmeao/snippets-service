# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import snippets.base.fields
import snippets.base.models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadedfile',
            name='file',
            field=models.FileField(upload_to=snippets.base.models._generate_filename),
        ),
    ]
