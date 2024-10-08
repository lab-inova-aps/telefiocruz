# Generated by Django 4.2.6 on 2024-08-12 08:48

from django.db import migrations, models
import slth
import slth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_medicamento'),
    ]

    operations = [
        migrations.CreateModel(
            name='Administrador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', slth.db.models.CharField(max_length=80, verbose_name='Nome')),
                ('cpf', slth.db.models.CharField(max_length=14, unique=True, verbose_name='CPF')),
            ],
            options={
                'verbose_name': 'Administrador',
                'verbose_name_plural': 'Administradores',
            },
            bases=(models.Model, slth.ModelMixin),
        ),
    ]
