from slth import endpoints
from ..models import TipoAtendimento


class TiposAtendimento(endpoints.ListEndpoint[TipoAtendimento]):
    def check_permission(self):
        return self.check_role()


class Add(endpoints.AddEndpoint[TipoAtendimento]):
    def check_permission(self):
        return self.check_role()


class Edit(endpoints.EditEndpoint[TipoAtendimento]):
    def check_permission(self):
        return self.check_role()


class Delete(endpoints.DeleteEndpoint[TipoAtendimento]):
    def check_permission(self):
        return self.check_role()
