from slth import endpoints
from ..models import Unidade, ProfissionalSaude
from ..utils import buscar_endereco


class Unidades(endpoints.ListEndpoint[Unidade]):
    def get(self):
        return super().get().lookup('a').lookup('gu', pk='unidade')
    
    def check_permission(self):
        return self.check_role('a', 'gu')
    
    def contribute(self, entrypoint):
        if entrypoint == 'menu':
            return not self.check_role('gu', 'ou', superuser=False)
        return super().contribute(entrypoint)


class Add(endpoints.AddEndpoint[Unidade]):
    def check_permission(self):
        return self.check_role('a', 'gu')
    
    def on_cep_change(self, cep):
        self.form.controller.set(**buscar_endereco(cep))


class Edit(endpoints.EditEndpoint[Unidade]):
    def check_permission(self):
        return self.check_role('a', 'gu')


class Delete(endpoints.DeleteEndpoint[Unidade]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[Unidade]):
    def check_permission(self):
        return self.check_role('a', 'gu')


class AddProfissionalSaude(endpoints.RelationEndpoint[ProfissionalSaude]):
    class Meta:
        icon = 'plus'
        verbose_name = 'Adicionar Profissional'
    
    def formfactory(self):
        return (
            super()
            .formfactory().fields(unidade=self.source)
            .fieldset("Dados Gerais", ("unidade", "pessoa_fisica:pessoafisica.add",))
            .fieldset("Dados Profissionais", ("especialidade", ("conselho_profissional", "registro_profissional")),)
            .fieldset(
                "Informações Adicionais", (
                    ("programa_provab", "programa_mais_medico"),
                    ("residente", "perceptor"),
                ),
            )
        )
