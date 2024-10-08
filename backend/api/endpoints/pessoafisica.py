from slth import endpoints
from ..models import PessoaFisica, Atendimento
from ..utils import buscar_endereco


class PessoasFisicas(endpoints.ListEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('g', 'o', 'a', 'ps', 'gu')
    
    def on_cep_change(self, controller, values):
        dados = buscar_endereco(values.get('cep'))
        if dados:
            dados['endereco'] = dados.pop('logradouro')
        controller.set(**dados)


class Edit(endpoints.EditEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('a')


class Delete(endpoints.DeleteEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('a')


class ProximosAtendimentos(endpoints.QuerySetEndpoint[Atendimento]):
    class Meta:
        verbose_name= 'Próximos Atendimentos'

    def get(self):
        return super().get().proximos().fields('profissional', 'assunto', 'get_agendado_para').actions('atendimento.view').lookup('p', paciente__cpf='username')
    
    def check_permission(self):
        return self.check_role('p', superuser=False)


class AtualizarPaciente(endpoints.EditEndpoint[PessoaFisica]):
    class Meta:
        icon = 'pencil'
        verbose_name = 'Atualizar Dados do Paciente'
    
    def check_permission(self):
        return self.check_role('o', 'ps')
    

class HistoricoPaciente(endpoints.InstanceEndpoint[PessoaFisica]):
    class Meta:
        icon = 'history'
        verbose_name = 'Histórico do Paciente'

    def get(self):
        return super().get().queryset('Histórico de Atendimentos', 'get_atendimentos')

    def check_permission(self):
        return self.check_role('ps')



