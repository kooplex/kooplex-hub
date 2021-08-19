# Generated by Django 3.2.5 on 2021-08-10 15:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0009_coursecontainerbinding'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('description', models.TextField(blank=True, max_length=512)),
                ('course', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='education.course')),
            ],
            options={
                'unique_together': {('name', 'course')},
            },
        ),
        migrations.CreateModel(
            name='UserCourseGroupBinding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='education.group')),
                ('usercoursebinding', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='education.usercoursebinding')),
            ],
            options={
                'unique_together': {('usercoursebinding', 'group')},
            },
        ),
        migrations.CreateModel(
            name='AssignmentGroupBinding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='education.assignment')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='education.group')),
            ],
            options={
                'unique_together': {('assignment', 'group')},
            },
        ),
    ]
