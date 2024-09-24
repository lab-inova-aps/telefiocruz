from slth import endpoints
from ..models import ConselhoClasse


class ConselhosClasse(endpoints.ListEndpoint[ConselhoClasse]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[ConselhoClasse]):
    def check_permission(self):
        return self.check_role('a')


class Edit(endpoints.EditEndpoint[ConselhoClasse]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[ConselhoClasse]):
    def check_permission(self):
        return self.check_role('a')
