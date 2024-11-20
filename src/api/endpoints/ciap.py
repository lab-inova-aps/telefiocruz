from slth import endpoints
from ..models import CIAP


class CIAPs(endpoints.ListEndpoint[CIAP]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[CIAP]):
    def check_permission(self):
        return self.check_role('a')


class Edit(endpoints.EditEndpoint[CIAP]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[CIAP]):
    def check_permission(self):
        return self.check_role('a')