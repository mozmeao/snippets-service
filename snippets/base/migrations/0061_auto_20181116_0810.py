# Generated by Django 2.1.3 on 2018-11-16 08:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0060_auto_20181120_1137'),
    ]

    operations = [
        migrations.AddField(
            model_name='snippet',
            name='migrated_to',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='migrated_from', to='base.ASRSnippet'),
        ),
    ]
