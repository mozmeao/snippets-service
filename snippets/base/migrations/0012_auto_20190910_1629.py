# Generated by Django 2.2.4 on 2019-09-10 16:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0011_auto_20190909_1027'),
    ]

    operations = [
        migrations.AddField(
            model_name='fxasignuptemplate',
            name='retry_button_label',
            field=models.CharField(default='Try again', help_text='Button label after a failed form submission', max_length=50, verbose_name='Retry Button Label'),
        ),
        migrations.AddField(
            model_name='newslettertemplate',
            name='retry_button_label',
            field=models.CharField(default='Try again', help_text='Button label after a failed form submission', max_length=50, verbose_name='Retry Button Label'),
        ),
        migrations.AddField(
            model_name='sendtodevicetemplate',
            name='retry_button_label',
            field=models.CharField(default='Try again', help_text='Button label after a failed form submission', max_length=50, verbose_name='Retry Button Label'),
        ),
    ]
