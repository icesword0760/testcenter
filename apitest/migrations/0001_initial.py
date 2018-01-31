# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-12-21 09:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TestCase',
            fields=[
                ('case_id', models.IntegerField(primary_key=True, serialize=False)),
                ('case_name', models.CharField(max_length=20)),
                ('variables', models.CharField(max_length=500)),
                ('request', models.CharField(max_length=500)),
                ('extract', models.CharField(max_length=500)),
                ('validate', models.CharField(max_length=500)),
            ],
        ),
        migrations.CreateModel(
            name='TestSuite',
            fields=[
                ('suite_id', models.IntegerField(primary_key=True, serialize=False)),
                ('suite_name', models.CharField(max_length=500)),
                ('suite_variables', models.CharField(max_length=500)),
                ('suite_request', models.CharField(max_length=500)),
            ],
        ),
        migrations.AddField(
            model_name='testcase',
            name='suite_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apitest.TestSuite'),
        ),
    ]