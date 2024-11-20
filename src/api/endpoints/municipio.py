from slth import endpoints
from ..models import Municipio


class Municipios(endpoints.ListEndpoint[Municipio]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[Municipio]):
    def check_permission(self):
        return self.check_role('a')


class Edit(endpoints.EditEndpoint[Municipio]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[Municipio]):
    def check_permission(self):
        return self.check_role('a')
