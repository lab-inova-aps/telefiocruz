from slth import endpoints
from ..models import Supervisor


class Supervisores(endpoints.ListEndpoint[Supervisor]):
    pass

class Add(endpoints.AddEndpoint[Supervisor]):
    pass


class Edit(endpoints.EditEndpoint[Supervisor]):
    pass


class Delete(endpoints.DeleteEndpoint[Supervisor]):
    pass


class View(endpoints.ViewEndpoint[Supervisor]):
    pass