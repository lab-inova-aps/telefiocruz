from slth import endpoints
from ..models import Estado


class Estados(endpoints.ListEndpoint[Estado]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[Estado]):
    def check_permission(self):
        return self.check_role('a')


class Edit(endpoints.EditEndpoint[Estado]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[Estado]):
    def check_permission(self):
        return self.check_role('a')
