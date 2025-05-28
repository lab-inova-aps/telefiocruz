from slth import endpoints
from ..models import AnexoAtendimento
from django.http import FileResponse


class Documentos(endpoints.ListEndpoint[AnexoAtendimento]):

    class Meta:
        icon = 'file'
        verbose_name = 'Documentos'

    def get(self):
        return super().get().search('atendimento__paciente__nome').filters('atendimento__profissional', 'atendimento__especialista' ).fields(
            'nome_arquivo', 'paciente', 'atendimento', 'get_data', 'get_profissional', 'get_especialista', 
        ).actions('anexoatendimento.enviar', 'anexoatendimento.baixar').filter(
            nome__in=['Atestado Médico', 'Prescrição Médica', 'Solicitação de Exame']
        )
    
    def check_permission(self):
        return self.check_role('ps')


class Enviar(endpoints.InstanceEndpoint[AnexoAtendimento]):

    class Meta:
        icon = 'mail-bulk'
        verbose_name = 'Enviar'

    def get(self):
        return super().formfactory().fields().info(""
        "O link para este documento ({}) será enviado para o e-mail ({}) e/ou Whatsapp ({}) do paciente.".format(
            self.instance.get_url_temporaria(),
            self.instance.atendimento.paciente.email or "não informado",
            self.instance.atendimento.paciente.telefone or "não informado",
        )
        )
    
    def post(self):
        self.instance.enviar()
        return super().post()

    def check_permission(self):
        return self.check_role('ps')


class Baixar(endpoints.InstanceEndpoint[AnexoAtendimento]):
    
    class Meta:
        icon = 'cloud-download'
        verbose_name = 'Baixar'

    def get(self):
        print(self.instance.arquivo.name, self.instance.arquivo.path)
        return FileResponse(open(self.instance.arquivo.path, 'rb'), as_attachment=False)

    def check_permission(self):
        return self.check_role('ps') or self.instance.is_valid(self.request.GET.get('token'))
