from datetime import datetime
from django.db import transaction
from api.utils import normalizar_nome
from ...models import ConselhoClasse, Area, Especialidade, PessoaFisica, Unidade, Municipio, Estado, ProfissionalSaude, Sexo
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        with transaction.atomic():
            estado = Estado.objects.get_or_create(codigo=50, defaults=dict(sigla='MS', nome='Mato Grosso do Sul'))[0]
            municipio = Municipio.objects.get_or_create(codigo=5003702, nome='Dourados', estado=estado)[0]
            with open('profissionais2.csv') as file:
                line = file.readline()
                line = file.readline()
                while line:
                    print(line.strip().split(';'))
                    nome, cpf, sexo, data_nascimento, email, telefone, numero_registro, sigla_conselho, especialidade, unidade = line.strip().split(';')
                    sexo = Sexo.objects.get(nome=sexo)
                    data_nascimento = datetime.strptime(data_nascimento, "%d/%m/%Y")
                    conselho = ConselhoClasse.objects.get(sigla=sigla_conselho)
                    especialidade = Especialidade.objects.get(id=especialidade)
                    pessoa_fisica = PessoaFisica.objects.get_or_create(cpf=cpf, defaults=dict(nome=normalizar_nome(nome), email=email, telefone=telefone, sexo=sexo, data_nascimento=data_nascimento))[0]
                    unidade = Unidade.objects.get_or_create(nome=unidade, defaults=dict(municipio=municipio))[0]
                    ProfissionalSaude.objects.get_or_create(
                        pessoa_fisica=pessoa_fisica, unidade=unidade, especialidade=especialidade,
                        defaults=dict(registro_profissional=numero_registro, conselho_profissional=conselho)
                    )
                    line = file.readline()
