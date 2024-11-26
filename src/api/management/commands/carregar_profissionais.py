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
            with open('profissionais.csv') as file:
                line = file.readline()
                while line:
                    tokens = line.strip().split(';')
                    nome, cpf, sexo, data_nascimento, email, registro, unidade, especialidade, extra = tokens
                    sexo = Sexo.objects.get(nome=sexo)
                    data_nascimento = datetime.strptime(data_nascimento, "%d/%m/%Y")
                    numero_registro, sigla_conselho = registro.split()
                    print(cpf, nome)
                    conselho = ConselhoClasse.objects.get_or_create(sigla=sigla_conselho, estado=estado)[0]
                    area = especialidade.split()[0]
                    area = Area.objects.get_or_create(nome=area)[0]
                    if especialidade == 'Medicina':
                        especialidade = 'Clínica Geral'
                    especialidade = Especialidade.objects.get_or_create(nome=especialidade, area=area, defaults=dict(cbo='00'))[0]
                    pessoa_fisica = PessoaFisica.objects.get_or_create(cpf=cpf, defaults=dict(nome=normalizar_nome(nome), email=email, sexo=sexo, data_nascimento=data_nascimento))[0]
                    unidade = Unidade.objects.get_or_create(nome=unidade, defaults=dict(municipio=municipio))[0]
                    ProfissionalSaude.objects.get_or_create(
                        pessoa_fisica=pessoa_fisica, unidade=unidade, especialidade=especialidade,
                        defaults=dict(registro_profissional=numero_registro, conselho_profissional=conselho)
                    )
                    line = file.readline()
