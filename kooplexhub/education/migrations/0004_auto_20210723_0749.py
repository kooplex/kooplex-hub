# Generated by Django 3.2.5 on 2021-07-23 05:49

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('education', '0003_auto_20210722_2355'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userassignmentbinding',
            options={'ordering': ['assignment__name']},
        ),
        migrations.AlterUniqueTogether(
            name='userassignmentbinding',
            unique_together={('user', 'assignment')},
        ),
    ]
