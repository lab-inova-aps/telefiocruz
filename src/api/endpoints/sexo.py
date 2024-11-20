from slth import endpoints
from ..models import Sexo


class Sexos(endpoints.ListEndpoint[Sexo]):
    def check_permission(self):
        return self.check_role()


class Add(endpoints.AddEndpoint[Sexo]):
    def check_permission(self):
        return self.check_role()


class Edit(endpoints.EditEndpoint[Sexo]):
    def check_permission(self):
        return self.check_role()


class Delete(endpoints.DeleteEndpoint[Sexo]):
    def check_permission(self):
        return self.check_role()
