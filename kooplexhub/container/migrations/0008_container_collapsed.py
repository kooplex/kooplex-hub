# Generated by Django 3.2.5 on 2021-08-13 07:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('container', '0007_alter_container_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='container',
            name='collapsed',
            field=models.BooleanField(default=True),
        ),
    ]
