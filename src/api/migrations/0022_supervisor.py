# Generated by Django 5.1.3 on 2024-12-18 06:39

import slth
import slth.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0021_notificacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='Supervisor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', slth.db.models.CharField(max_length=80, verbose_name='Nome')),
                ('cpf', slth.db.models.CharField(max_length=14, unique=True, verbose_name='CPF')),
            ],
            options={
                'verbose_name': 'Supervisor',
                'verbose_name_plural': 'Supervisores',
            },
            bases=(models.Model, slth.ModelMixin),
        ),
    ]