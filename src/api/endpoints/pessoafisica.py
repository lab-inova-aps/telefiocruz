from slth import endpoints
from slth.components import FileViewer
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
        if self.check_role('a', 'o', 'gu', 'ou', 'ps'):
            return False
        return self.check_role('p', superuser=False)


class AtualizarPaciente(endpoints.EditEndpoint[PessoaFisica]):
    class Meta:
        icon = 'pencil'
        verbose_name = 'Atualizar Dados do Paciente'
    
    def check_permission(self):
        return self.check_role('o', 'ps')
    

class ProntuarioPaciente(endpoints.InstanceEndpoint[PessoaFisica]):
    class Meta:
        icon = 'history'
        verbose_name = 'Prontuário do Paciente'

    def get(self):
        if self.request.GET.get('view'):
            return self.render(dict(obj=self.instance), "prontuario.html", pdf=True)
        else:
            return FileViewer(f'/api/pessoafisica/prontuariopaciente/{self.instance.pk}/?view={self.request.user.id}')

    def check_permission(self):
        token = self.request.GET.get('view')
        return self.check_role('ps') or (token is None or token == str(self.request.user.id))



