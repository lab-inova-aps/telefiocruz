# Generated by Django 5.1.3 on 2024-11-26 18:23

import django.db.models.deletion
import slth.db.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0017_situacaoatendimento_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pessoafisica',
            name='sexo',
            field=slth.db.models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='api.sexo', verbose_name='Sexo'),
        ),
    ]
