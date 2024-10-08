# Generated by Django 4.2.6 on 2024-08-15 08:30

from django.db import migrations
import slth.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_alter_atendimento_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='unidade',
            name='gestores',
            field=slth.db.models.ManyToManyField(blank=True, related_name='r3', to='api.pessoafisica', verbose_name='Gestores'),
        ),
        migrations.AddField(
            model_name='unidade',
            name='operadores',
            field=slth.db.models.ManyToManyField(blank=True, related_name='r4', to='api.pessoafisica', verbose_name='Operadores'),
        ),
    ]
