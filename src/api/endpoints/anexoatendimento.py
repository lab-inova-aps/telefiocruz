from slth import endpoints
from ..models import AnexoAtendimento
from django.http import FileResponse


class Enviar(endpoints.InstanceEndpoint[AnexoAtendimento]):

    class Meta:
        icon = 'mail-bulk'
        verbose_name = 'Enviar'

    def get(self):
        print(self.instance.atendimento.paciente.email, 9999)
        return super().formfactory().fields().info(""
        "O link para este documento será enviado para o e-mail ({}) e/ou Whatsapp ({}) do paciente.".format(
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
