from slth import endpoints
from ..models import Medicamento


class Medicamentos(endpoints.ListEndpoint[Medicamento]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[Medicamento]):
    def check_permission(self):
        return self.check_role('a', 'ps')


class Edit(endpoints.EditEndpoint[Medicamento]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[Medicamento]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[Medicamento]):
    def check_permission(self):
        return self.check_role('a')
