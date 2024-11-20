from slth import endpoints
from ..models import Especialidade, ProfissionalSaude


class Especialidades(endpoints.ListEndpoint[Especialidade]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[Especialidade]):
    def check_permission(self):
        return self.check_role('a')


class Edit(endpoints.EditEndpoint[Especialidade]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[Especialidade]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[Especialidade]):
    def check_permission(self):
        return self.check_role('a')


class ProfissionaisSaude(endpoints.InstanceEndpoint[Especialidade]):
    class Meta:
        icon = "stethoscope"
        verbose_name = 'Profissionais de Saúde'
    
    def get(self):
        return self.instance.get_profissonais_saude()
