from slth import endpoints
from datetime import datetime
from ..models import PessoaFisica, Atendimento
from ..utils import buscar_endereco, buscar_pessoafisica


class PessoasFisicas(endpoints.ListEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('a')


class Add(endpoints.AddEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('g', 'o', 'a', 'ps', 'gu')
    
    def on_cep_change(self, cep):
        dados = buscar_endereco(cep)
        if dados:
            dados['endereco'] = dados.pop('logradouro')
        self.form.controller.set(**dados)

    def on_cpf_change(self, cpf):
        self.form.controller.set(**buscar_pessoafisica(cpf))


class Edit(endpoints.EditEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('g', 'o', 'a', 'ps', 'gu')
    
    def on_cep_change(self, cep):
        dados = buscar_endereco(cep)
        if dados:
            dados['endereco'] = dados.pop('logradouro')
        self.form.controller.set(**dados)


class Delete(endpoints.DeleteEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[PessoaFisica]):
    def check_permission(self):
        return self.check_role('a')


class AtendimentosDoDia(endpoints.QuerySetEndpoint[Atendimento]):
    class Meta:
        verbose_name= 'Atendimentos do Dia'

    def get(self):
        return super().get().do_dia().fields('profissional', 'assunto', 'get_agendado_para').actions('atendimento.view').lookup('p', paciente__cpf='username')
    
    def check_permission(self):
        if self.check_role('a', 'o', 'gu', 'ou'):
            return False
        return self.check_role('p', superuser=False)


class AtualizarPaciente(endpoints.EditEndpoint[PessoaFisica]):
    class Meta:
        icon = 'pencil'
        verbose_name = 'Atualizar Dados do Paciente'
    
    def check_permission(self):
        return self.check_role('o', 'ps')
    

class HistoricoPaciente(endpoints.ViewEndpoint[PessoaFisica]):
    class Meta:
        icon = 'history'
        verbose_name = 'Detalhe e Histórico do Paciente'

    def get(self):
        return super().get().queryset('Histórico de Atendimentos', 'get_atendimentos')

    def check_permission(self):
        return self.check_role('ps')



