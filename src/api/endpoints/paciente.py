from slth import endpoints
from slth.components import FileViewer
from datetime import datetime
from ..models import PessoaFisica, Atendimento
from ..utils import buscar_endereco, buscar_pessoafisica
from django.core import signing


class Pacientes(endpoints.QuerySetEndpoint[PessoaFisica]):
    class Meta:
        verbose_name = 'Pacientes'

    def get(self):
        return super().get().pacientes()

    def check_permission(self):
        return self.check_role('a', 'r')


