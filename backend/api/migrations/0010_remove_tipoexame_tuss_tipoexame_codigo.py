# Generated by Django 4.2.6 on 2024-08-26 16:25

from django.db import migrations
import slth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_unidade_gestores_unidade_operadores'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tipoexame',
            name='tuss',
        ),
        migrations.AddField(
            model_name='tipoexame',
            name='codigo',
            field=slth.db.models.CharField(max_length=255, null=True, verbose_name='Código'),
        ),
    ]
