# Generated by Django 2.2.6 on 2019-12-16 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0026_auto_20191211_0815'),
    ]

    operations = [
        migrations.AddField(
            model_name='target',
            name='filtr_needs_update',
            field=models.CharField(blank=True, default='', max_length=250),
        ),
    ]
