import os
import binascii
from uuid import uuid1
from datetime import datetime
from django.core.files.base import ContentFile
from slth import endpoints
from django.conf import settings
from slth.components import Scheduler, ZoomMeet, Warning, Response
from ..models import *
from slth import forms
from ..utils import buscar_endereco
from slth import printer
from slth.tests import RUNNING_TESTING
from slth.endpoints import Serializer
import requests


MENSAGEM_ASSINATURA_DIGITAL = '''
    Para realizar a assinatura digital, você deverá estar com o aplicativo Vadaas instalado em seu celular.
    Você receberá uma notificação para autorizar a assinatura após clicar no botão "Enviar".
    Conceda a autorização e aguarde até o que o documento seja assinado.

'''


class RecuperarSenha(endpoints.PublicEndpoint):
    cpf = forms.CharField(label='CPF')

    class Meta:
        verbose_name = 'Recuperar Senha'

    def get(self):
        return self.formfactory().fields('cpf').info('Uma senha randômica será enviada para o e-mail vinculado ao CPF informado. Ela poderá ser alterada pelo usuário após o acesso ao sistema.')


class SalaEspera(endpoints.PublicEndpoint):
    class Meta:
        verbose_name = 'Sala de Espera'

    def get(self):
        atendimento = Atendimento.objects.get(token=self.request.GET.get('token'))
        if atendimento.iniciado_em:
            if self.request.user.is_authenticated:
                self.redirect('/api/salavirtual/{}/'.format(atendimento.pk))
            self.redirect('/api/salavirtual/{}/?token={}'.format(atendimento.pk, atendimento.token))
        return self.render(dict(atendimento=atendimento), autoreload=10)


class PoliticaPrivacidade(endpoints.PublicEndpoint):
    def get(self):
        return self.render({})


class GuiaUsuario(endpoints.PublicEndpoint):
    def get(self):
        return self.render(dict(l1=[1, 2, 3, 4, 5, 6], l2=[6, 8, 7, 9], l3=[6, 10, 1]))


class Suporte(endpoints.PublicEndpoint):
    def get(self):
        return self.render({})


class TermosUso(endpoints.PublicEndpoint):
    def get(self):
        return self.render({})


class SalaVirtual(endpoints.InstanceEndpoint[Atendimento]):

    class Meta:
        icon = 'display'
        modal = False
        verbose_name = 'Sala Virtual'

    def get(self):
        if self.instance.iniciado_em is None:
            self.instance.iniciado_em = datetime.now()
            self.instance.save()

        pessoa_fisica = PessoaFisica.objects.filter(cpf=self.request.user.username).first()
        if pessoa_fisica is None:
            pessoa_fisica = self.instance.paciente
        mensagem = '{} acessou a sala virtual.'.format(pessoa_fisica.nome)
        if not self.instance.notificacao_set.filter(mensagem=mensagem).exists():
            self.instance.enviar_notificacao(mensagem, remetente=pessoa_fisica)

        return (
            self.serializer().actions('atendimento.anexararquivo', 'atendimento.emitiratestado', 'atendimento.solicitarexames', 'atendimento.prescrevermedicamento')
            .endpoint('videochamada', wrap=False)
            .queryset('get_anexos_webconf')
            .endpoint('atendimento.registrarecanminhamentoscondutas', wrap=False)
        )
    
    def check_permission(self):
        return (
            self.instance.is_agendado()
            and (
                self.instance.is_envolvido(self.request.user)
                or self.request.GET.get('token') == self.instance.token
            )
        )


class VideoChamada(endpoints.InstanceEndpoint[Atendimento]):
    def get(self):
        cpf = self.request.user.username if self.request.user.is_authenticated else self.instance.paciente.cpf
        return ZoomMeet(self.instance.token, cpf)
    
    def check_permission(self):
        return (
            self.instance.is_agendado()
            and not RUNNING_TESTING
            and (
                self.request.GET.get('token') == self.instance.token
                or self.request.user.username == self.instance.paciente.cpf
                or self.request.user.username == self.instance.profissional.pessoa_fisica.cpf
                or self.instance.especialista and self.request.user.username == self.instance.especialista.pessoa_fisica.cpf
            )
        )


class AbrirSala(endpoints.Endpoint):
    class Meta:
        icon = 'chalkboard-user'
        verbose_name = 'Abrir Sala'
    
    def get(self):
        token = self.request.GET.get('token')
        if token:
            return ZoomMeet(token, self.request.user.username if self.request.user.is_authenticated else 'Convidado')
        else:
            self.redirect(f'/api/abrirsala/?token={uuid1().hex}')

    def check_permission(self):
        return self.request.user.is_superuser or self.request.GET.get('token')


class FazerAlgo(endpoints.Endpoint):
    class Meta:
        modal = False

    x = forms.CharField(label='X')

    def get(self):
        return self.formfactory().fields('x').onsuccess(message='Fantástico :D', dispose=True)


class Estatistica(endpoints.PublicEndpoint):
    class Meta:
        icon = 'line-chart'
        verbose_name = 'Painel de Monitoramento'
    
    def get(self):
        return (
            Atendimento.objects
            .filters(
                'agendado_para__year', 'tipo', 'especialidade__area', 'especialidade', 'profissional__unidade', 'profissional', 'especialista', 'situacao'
            )
            .bi(
                ('get_total', 'get_total_profissioinais', 'get_total_pacientes'),
                ('get_total_por_tipo', 'get_total_por_situacao', 'get_total_por_area'),
                'get_total_por_mes', 'get_total_por_unidade',
                'get_total_por_area_e_unidade', get_total_por_mes='agendado_para__year'
            )
        )
    
    def check_permission(self):
        return self.check_role('g', 'gm', 'gu', 'ps') or not self.request.user.is_authenticated


from .. import tasks
class FazerAlgumaCoisa(endpoints.Endpoint):
    n = forms.IntegerField(label='Total')

    class Meta:
        modal = False
    
    def post(self):
        return tasks.FazerAlgumaCoisa(self.cleaned_data['n'])

class Vidaas(endpoints.Endpoint):
    class Meta:
        verbose_name = 'Configurar Vidaas'

    def get(self):
        self.redirect('{}?code={}'.format(self.cache.get('vidaas_forward'), self.request.GET.get('code')))

    def _get(self):
        profissional_saude = ProfissionalSaude.objects.get(pessoa_fisica__cpf=self.request.user.username)
        code_verifier = 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstwcM'
        authorization_code = self.request.GET.get('code')
        redirect_url = self.absolute_url('/app/vidaas/')
        redirect_url = 'push://http://viddas.com.br'
        if authorization_code:
            profissional_saude.configurar_vidaas(authorization_code, redirect_url, code_verifier)
            # profissional_saude.assinar_arquivo_imagem('/Users/breno/Downloads/file.jpeg')
            return Response('Configuração realizada com sucesso.', redirect='/api/dashboard/')
        else:
            login_hint = self.request.user.username
            if redirect_url.startswith('push://'):
                url = 'https://certificado.vidaas.com.br/valid/api/v1/trusted-services/authorizations?client_id={}&code_challenge={}&code_challenge_method=S256&response_type=code&scope=signature_session&login_hint={}&lifetime=900&redirect_uri={}'.format(
                    os.environ.get('VIDAAS_API_KEY'), code_verifier, login_hint, redirect_url
                )
                authorization_code = requests.get(url).text
                ok = profissional_saude.configurar_vidaas(authorization_code, redirect_url, code_verifier)
                if ok:
                    print('[OK]')
                    profissional_saude.assinar_arquivo_imagem('/Users/breno/Downloads/file.jpeg')
                self.redirect('/app/dashboard/')
            else:
                url = 'https://certificado.vidaas.com.br/v0/oauth/authorize?client_id={}&code_challenge={}&code_challenge_method=S256&response_type=code&scope=signature_session&login_hint={}&lifetime=900&redirect_uri={}'.format(
                    os.environ.get('VIDAAS_API_KEY'), code_verifier, login_hint, redirect_url
                )
                self.redirect(url)

    def check_permission(self):
        return self.check_role('ps')


class AssinarViaQrCode(endpoints.InstanceEndpoint[Atendimento]):
    class Meta:
        modal = False
        icon = 'qrcode'
        verbose_name = 'Assinar'

    def get(self):
        if RUNNING_TESTING:
            self.redirect(f'/api/atendimento/view/{self.instance.pk}/')
        cpf = self.request.user.username.replace('.', '').replace('-', '')
        # cpf = '04770402414'
        authorization_code = self.request.GET.get('code')
        if authorization_code is None:
            code_verifier = 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstwcM'
            redirect_url = '{}/app/vidaas/'.format(settings.SITE_URL)
            self.cache.set('vidaas_forward', self.request.path)
            url = 'https://certificado.vidaas.com.br/v0/oauth/authorize?client_id={}&code_challenge={}&code_challenge_method=S256&response_type=code&scope=signature_session&login_hint={}&lifetime=900&redirect_uri={}'.format(os.environ.get('VIDAAS_API_KEY'), code_verifier, cpf, redirect_url)
            self.redirect(url)
        else:
            self.instance.finalizar(authorization_code)
            self.redirect(f'/api/atendimento/view/{self.instance.id}/')

    def check_permission(self):
        return self.check_role('ps')

