from slth import endpoints
from ..models import CID


class CIDs(endpoints.ListEndpoint[CID]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[CID]):
    def check_permission(self):
        return self.check_role('a')


class Edit(endpoints.EditEndpoint[CID]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[CID]):
    def check_permission(self):
        return self.check_role('a')
