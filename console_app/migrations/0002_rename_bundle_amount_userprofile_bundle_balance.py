# Generated by Django 5.0 on 2024-02-17 06:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console_app', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userprofile',
            old_name='bundle_amount',
            new_name='bundle_balance',
        ),
    ]
