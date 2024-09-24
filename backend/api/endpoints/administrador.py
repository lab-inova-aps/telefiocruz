from slth import endpoints
from ..models import Administrador


class Administradores(endpoints.ListEndpoint[Administrador]):
    pass

class Add(endpoints.AddEndpoint[Administrador]):
    pass


class Edit(endpoints.EditEndpoint[Administrador]):
    pass


class Delete(endpoints.DeleteEndpoint[Administrador]):
    pass


class View(endpoints.ViewEndpoint[Administrador]):
    pass