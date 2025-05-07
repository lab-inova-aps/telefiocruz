from slth import endpoints
from ..models import *


class Agendadores(endpoints.ListEndpoint[Agendador]):
    class Meta:
        verbose_name = 'Agendadores'

    def get(self):
        return (
            super().get()
            .actions('agendador.cadastrar', 'agendador.visualizar', 'agendador.editar', 'agendador.excluir')
        )


class Cadastrar(endpoints.AddEndpoint[Agendador]):
    class Meta:
        icon = 'plus'
        verbose_name = 'Cadastrar Agendador'

    def get(self):
        return (
            super().get()
        )

        
class Visualizar(endpoints.ViewEndpoint[Agendador]):
    class Meta:
        modal = False
        icon = 'eye'
        verbose_name = 'Visualizar Agendador'

    def get(self):
        return (
            super().get()
        )
    

class Editar(endpoints.EditEndpoint[Agendador]):
    class Meta:
        icon = 'pen'
        verbose_name = 'Editar Agendador'

    def get(self):
        return (
            super().get()
        )


class Excluir(endpoints.DeleteEndpoint[Agendador]):
    class Meta:
        icon = 'trash'
        verbose_name = 'Excluir Agendador'

    def get(self):
        return (
            super().get()
        )

