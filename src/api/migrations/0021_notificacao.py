# Generated by Django 5.1.3 on 2024-12-14 16:54

import django.db.models.deletion
import slth
import slth.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_remove_atendimento_unidade'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notificacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canal', slth.db.models.CharField(max_length=255, verbose_name='Canal')),
                ('data_hora', slth.db.models.DateTimeField(verbose_name='Data/Hora')),
                ('mensagem', slth.db.models.CharField(max_length=255, verbose_name='Mensagem')),
                ('atendimento', slth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.atendimento', verbose_name='Atendimento')),
                ('destinatario', slth.db.models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.pessoafisica', verbose_name='Destinatário')),
            ],
            options={
                'verbose_name': 'Notificação',
                'verbose_name_plural': 'Notificações',
                'icon': 'mail-bulk',
            },
            bases=(models.Model, slth.ModelMixin),
        ),
    ]