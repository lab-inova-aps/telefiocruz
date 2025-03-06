from slth import endpoints
from ..models import Nucleo, ProfissionalSaude


class Nucleos(endpoints.ListEndpoint[Nucleo]):
    def check_permission(self):
        return self.check_role('a', 'g')
    
    def contribute(self, entrypoint):
        if entrypoint == 'menu':
            return not self.check_role('g', superuser=False)
        return super().contribute(entrypoint)


class Add(endpoints.AddEndpoint[Nucleo]):
    def check_permission(self):
        return self.check_role('a')


class Edit(endpoints.EditEndpoint[Nucleo]):
    def check_permission(self):
        return self.check_role('a', 'g')


class Delete(endpoints.DeleteEndpoint[Nucleo]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[Nucleo]):
    def check_permission(self):
        return self.check_role('a', 'g')


class AddProfissionalSaude(endpoints.RelationEndpoint[ProfissionalSaude]):
    class Meta:
        icon = 'plus'
        verbose_name = 'Adicionar Profissional'
    
    def formfactory(self):
        return (
            super()
            .formfactory().fields(nucleo=self.source)
            .fieldset("Dados Gerais", ("nucleo", "pessoa_fisica:pessoafisica.add",))
            .fieldset("Dados Profissionais", ("especialidade", ("conselho_profissional", "registro_profissional"), ("conselho_especialista", "registro_especialista"),),)
            .fieldset("Informações Adicionais", (("programa_provab", "programa_mais_medico"),("residente", "perceptor"),),)
        )
    
    def get_nucleo_queryset(self, queryset):
        return queryset.lookup('g', gestores__cpf='username')
    
    def check_permission(self):
        return self.check_role('a', 'g')
    

class Agenda(endpoints.InstanceEndpoint[Nucleo]):
    class Meta:
        icon = 'clock'
        verbose_name = 'Agenda de Atendimento'

    def get(self):
        return self.instance.get_agenda(
            semana=int(self.request.GET.get('week', 1)), url=self.request.path
        )
    
    def check_permission(self):
        return True
