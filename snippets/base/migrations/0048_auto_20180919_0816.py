# Generated by Django 2.1 on 2018-09-19 08:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0047_auto_20180919_0815'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asrsnippet',
            name='campaign',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='base.Campaign'),
        ),
    ]
