# Generated by Django 2.2.2 on 2019-07-16 11:23

from django.db import migrations
import taggit_selectize.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0003_taggeditem_add_unique_index'),
        ('base', '0096_remove_asrsnippet_locales'),
    ]

    operations = [
        migrations.AddField(
            model_name='asrsnippet',
            name='tags',
            field=taggit_selectize.managers.TaggableManager(blank=True, help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags'),
        ),
    ]
