# Generated by Django 2.2.1 on 2019-06-19 10:39

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import snippets.base.validators


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0093_auto_20190618_1325'),
    ]

    operations = [
        migrations.CreateModel(
            name='Locale',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=255, unique=True, validators=[django.core.validators.RegexValidator(regex='^,?([A-Za-z-]+,?)+$')])),
                ('translations', models.TextField(blank=True, default='{}', help_text='JSON dictionary with Template fields as keys and localized strings as values.', validators=[snippets.base.validators.validate_json_data])),
            ],
            options={
                'ordering': ('name', 'code'),
            },
        ),
        migrations.AddField(
            model_name='asrsnippet',
            name='locale',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='base.Locale'),
        ),
    ]