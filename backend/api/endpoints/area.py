from slth import endpoints
from ..models import Area, ProfissionalSaude


class Areas(endpoints.ListEndpoint[Area]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[Area]):
    def check_permission(self):
        return self.check_role('a')


class Edit(endpoints.EditEndpoint[Area]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[Area]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[Area]):
    def check_permission(self):
        return self.check_role('a')


class ProfissionaisSaude(endpoints.InstanceEndpoint[Area]):
    class Meta:
        icon = "stethoscope"
        verbose_name = 'Profissionais de Saúde'
    
    def get(self):
        return self.instance.get_profissonais_saude()
