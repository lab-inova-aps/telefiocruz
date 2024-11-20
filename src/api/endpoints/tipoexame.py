from slth import endpoints
from ..models import TipoExame


class TiposExame(endpoints.ListEndpoint[TipoExame]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[TipoExame]):
    def check_permission(self):
        return self.check_role('a', 'ps')


class Edit(endpoints.EditEndpoint[TipoExame]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[TipoExame]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[TipoExame]):
    def check_permission(self):
        return self.check_role('a')
