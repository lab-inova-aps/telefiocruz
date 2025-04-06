from slth import endpoints
from ..models import *


class MateriaisApoio(endpoints.ListEndpoint[MaterialApoio]):
    class Meta:
        verbose_name = 'Materiais de Apoio'

    def get(self):
        return (
            super().get().fields('nome', 'objetivo', 'get_arquivo')
            .actions('materialapoio.cadastrar', 'materialapoio.excluir')
            .filter(pessoa_fisica__cpf=self.request.user.username)
        )
    
    def check_permission(self):
        return self.check_role('ps')


class Cadastrar(endpoints.AddEndpoint[MaterialApoio]):
    class Meta:
        icon = 'plus'
        verbose_name = 'Cadastrar Materia de Apoio'

    def get_pessoa_fisica(self):
        return PessoaFisica.objects.get(cpf=self.request.user.username)

    def get(self):
        return (
            super().get().fields('nome', 'tipo', 'arquivo', 'url', 'objetivo', pessoa_fisica=self.get_pessoa_fisica()).hidden('arquivo', 'url')
        )
    
    def on_tipo_change(self, tipo):
        self.form.controller.visible(tipo == 'arquivo', 'arquivo')
        self.form.controller.visible(tipo == 'url', 'url')
    
    def check_permission(self):
        return self.check_role('ps')


class Excluir(endpoints.DeleteEndpoint[MaterialApoio]):
    class Meta:
        icon = 'trash'
        verbose_name = 'Excluir Materia de Apoio'

    def get(self):
        return (
            super().get()
        )
    
    def check_permission(self):
        return self.check_role('ps') and self.instance.pessoa_fisica.cpf == self.request.user.username

