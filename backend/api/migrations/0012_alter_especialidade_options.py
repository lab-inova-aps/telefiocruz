# Generated by Django 5.1.1 on 2024-09-24 08:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_alter_atendimento_agendado_para_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='especialidade',
            options={'verbose_name': 'Especialidade', 'verbose_name_plural': 'Especialidades'},
        ),
    ]
