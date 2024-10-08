import os
import binascii
from uuid import uuid1
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



class SalaEspera(endpoints.PublicEndpoint):
    class Meta:
        verbose_name = 'Sala de Espera'

    def get(self):
        atendimento = Atendimento.objects.get(token=self.request.GET.get('token'))
        if atendimento.numero_webconf:
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
        # se a sala virtual ainda não foi criada
        if not RUNNING_TESTING:
            # criar sala virtual caso esteja sendo acessado pelo profissional responsável
            if self.instance.profissional.pessoa_fisica.cpf == self.request.user.username:
                self.instance.check_webconf()
            # redirecionar para a sala de espera
            else:
                self.redirect('/api/salaespera/?token={}'.format(self.instance.token))
        return (
            self.serializer().actions('atendimento.anexararquivo', 'atendimento.emitiratestado', 'atendimento.solicitarexames', 'atendimento.prescrevermedicamento')
            .endpoint('VideoChamada', 'videochamada', wrap=False)
            .queryset('Anexos', 'get_anexos_webconf')
            .endpoint('Condutas e Encaminhamentos', 'atendimento.registrarecanminhamentoscondutas', wrap=False)
        )
    
    def check_permission(self):
        return (
            1 or self.instance.finalizado_em is None
            and (
                self.check_role('ps')
                or self.instance.paciente.cpf == self.request.user.username
                or self.request.GET.get('token') == self.instance.token
            )
        )


class VideoChamada(endpoints.InstanceEndpoint[Atendimento]):
    def get(self):
        cpf = self.request.user.username if self.request.user.is_authenticated else self.instance.paciente.cpf
        return ZoomMeet(self.instance.numero_webconf, cpf)
    
    def check_permission(self):
        return (
            self.instance.finalizado_em is None
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
            if cache.get(token):
                return ZoomMeet(token, self.request.user.username if self.request.user.is_authenticated else 'Convidado')
            self.redirect('/app/dashboard/')
        else:
            profissional_saude = ProfissionalSaude.objects.get(pessoa_fisica__cpf=self.request.user.username)
            number = profissional_saude.criar_sala_virtual(profissional_saude.pessoa_fisica.nome)
            self.redirect(f'/api/abrirsala/?token={number}')

    def check_permission(self):
        profissional_saude = ProfissionalSaude.objects.filter(pessoa_fisica__cpf=self.request.user.username).first()
        return self.request.GET.get('token') or (profissional_saude and profissional_saude.zoom_token)




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
                'especialidade__area', 'especialidade', 'unidade__municipio', 'unidade', 'profissional', 'especialista'
            )
            .bi(
                ('get_total', 'get_total_profissioinais', 'get_total_pacientes'),
                ('get_total_por_tipo', 'get_total_por_area'),
                'get_total_por_mes',
                'get_total_por_area_e_unidade'
            )
        )
    
    def check_permission(self):
        return self.check_role('g', 'gm', 'gu')


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


class EventoZoom(endpoints.PublicEndpoint):
    def post(self):
        return {}


class ConfigurarZoom(endpoints.Endpoint):
    class Meta:
        icon = 'video'
        verbose_name = 'Configurar Zoom'

    def get(self):
        redirect_url = '{}/app/configurarzoom/'.format(settings.SITE_URL)
        profissional_saude = ProfissionalSaude.objects.get(pessoa_fisica__cpf=self.request.user.username)
        
        if profissional_saude.zoom_token:
            info = 'A autorização concedida a Telefiocruz para criar video-chamadas por você será revogada.'
        else:
            info = 'Você será redirecionado para o site da Zoom (https://zoom.us) para autorizar a Telefiocruz criar video-chamadas por você.'
       
        authorization_code = self.request.GET.get('code')
        if authorization_code:
            profissional_saude.configurar_zoom(authorization_code, redirect_url)
            return Response('Configuração realizada com sucesso.', redirect='/api/dashboard/')
        return self.formfactory().info(info)

    def post(self):
        profissional_saude = ProfissionalSaude.objects.get(pessoa_fisica__cpf=self.request.user.username)
        if profissional_saude.zoom_token:
            profissional_saude.zoom_token = None
            profissional_saude.save()
            return Response('Autorização revogada com sucesso.', redirect='/api/dashboard/')
        else:
            redirect_url = '{}/app/configurarzoom/'.format(settings.SITE_URL)
            url = 'https://zoom.us/oauth/authorize?response_type=code&client_id={}&redirect_uri={}'.format(
                os.environ.get('ZOOM_API_KEY'), redirect_url
            )
            self.redirect(url)

    def check_permission(self):
        return self.check_role('ps') or ProfissionalSaude.objects.filter(pessoa_fisica__cpf=self.request.user.username, zoom_token__isnull=True).exists()



class AssinarViaQrCode(endpoints.InstanceEndpoint[Atendimento]):
    class Meta:
        modal = False
        icon = 'qrcode'
        verbose_name = 'Assinar'

    def get(self):
        if RUNNING_TESTING:
            self.redirect(f'/api/atendimento/view/{self.instance.pk}/')
        cpf = '04770402414' or self.request.user.username.replace('.', '').replace('-', '')
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

