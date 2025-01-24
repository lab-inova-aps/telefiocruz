import os
import hashlib
import base64
from uuid import uuid1
from PIL import Image as PILImage
import requests
from slth.models import Email, TimeZone
from django.conf import settings
from .signer import VidaasPdfSigner
from datetime import date, datetime, timedelta, time
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.timesince import timesince
from slth import printer
from slth.pdf import PdfWriter
from django.core.cache import cache
from django.core.files.base import ContentFile
from slth.db import models, meta, role
from slth.models import User, RoleFilter, WhatsappNotification
from slth.components import Scheduler, FileLink, Image, Map, Text, Badge, TemplateContent
from slth.printer import qrcode_base64
from django.core import signing
from django.db import transaction
from . import whatsapp


@role('a', username='cpf')
class Administrador(models.Model):
    nome = models.CharField(verbose_name='Nome', max_length=80)
    cpf = models.CharField(verbose_name='CPF', max_length=14, unique=True)

    class Meta:
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'

    def __str__(self):
        return self.nome


@role('s', username='cpf')
class Supervisor(models.Model):
    nome = models.CharField(verbose_name='Nome', max_length=80)
    cpf = models.CharField(verbose_name='CPF', max_length=14, unique=True)

    class Meta:
        verbose_name = 'Supervisor'
        verbose_name_plural = 'Supervisores'

    def __str__(self):
        return self.nome


class CIDQuerySet(models.QuerySet):
    def all(self):
        return self.search('codigo', 'doenca')


class CID(models.Model):
    codigo = models.CharField(verbose_name="Código", max_length=6, unique=True)
    doenca = models.CharField(verbose_name="Doença", max_length=250)

    objects = CIDQuerySet()
    class Meta:
        verbose_name = "CID"
        verbose_name_plural = "CIDs"

    def __str__(self):
        return "%s - %s" % (self.codigo, self.doenca)


class CIAP(models.Model):
    codigo = models.CharField(verbose_name="Código", max_length=6, unique=True)
    doenca = models.CharField(verbose_name="Doença", max_length=100)

    class Meta:
        verbose_name = "CIAP"
        verbose_name_plural = "CIAPs"

    def __str__(self):
        return "%s - %s" % (self.codigo, self.doenca)


class AreaQuerySet(models.QuerySet):
    def all(self):
        return self.fields('nome', 'get_qtd_profissonais_saude').actions('area.profissionaissaude')


class Area(models.Model):
    nome = models.CharField(max_length=60, unique=True)

    objects = AreaQuerySet()

    class Meta:
        ordering = ("nome",)
        verbose_name = "Área"
        verbose_name_plural = "Áreas"

    def get_profissonais_saude(self):
        return ProfissionalSaude.objects.filter(especialidade__area=self).fields('pessoa_fisica', 'get_estabelecimento')
    
    @meta('Qtd. de Profissionais')
    def get_qtd_profissonais_saude(self):
        return self.get_profissonais_saude().count()
    
    def __str__(self):
        return self.nome


class TipoAtendimento(models.Model):
    TELECONSULTA = 1
    TELE_INTERCONSULTA = 2
    nome = models.CharField(verbose_name='Nome', max_length=30)

    class Meta:
        verbose_name = "Tipo de Atendimento"
        verbose_name_plural = "Tipos de Atendimentos"

    def __str__(self):
        return "%s" % self.nome
    
    def is_teleconsulta(self):
        return self.nome == 'Teleconsulta'
    
    def is_teleinterconsulta(self):
        return self.nome == 'Teleinterconsulta'


class EstadoQuerySet(models.QuerySet):
    def all(self):
        return self.search('sigla', 'nome', 'codigo')


class Estado(models.Model):
    codigo = models.CharField(verbose_name='Código IBGE', max_length=2, unique=True)
    sigla = models.CharField(verbose_name='Sigla', max_length=2, unique=True)
    nome = models.CharField(verbose_name='Nome', max_length=60, unique=True)
    fuso_horario = models.ForeignKey(TimeZone, verbose_name='Fuso Horário', on_delete=models.CASCADE, null=True, blank=True)

    objects = EstadoQuerySet()

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"
        ordering = ["nome"]

    @property
    def id(self):
        return self.codigo

    def __str__(self):
        return "%s/%s" % (self.nome, self.sigla)


class ConselhoClasse(models.Model):
    sigla = models.CharField(verbose_name='Sigla', max_length=20, unique=True)
    estado = models.ForeignKey(Estado, verbose_name='Estado', on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Conselho de Classe"
        verbose_name_plural = "Conselhos de Classe"
        ordering = ["sigla"]

    def __str__(self):
        return self.sigla


class Sexo(models.Model):
    nome = models.CharField(verbose_name='Nome')

    def __str__(self):
        return self.nome


class MunicipioQuerySet(models.QuerySet):
    def all(self):
        return self.search('nome', 'codigo').filters('estado')


class Municipio(models.Model):
    estado = models.ForeignKey(Estado, verbose_name='Estado', on_delete=models.CASCADE)
    codigo = models.CharField(max_length=7, verbose_name='Código IBGE', unique=True)
    nome = models.CharField(verbose_name='Nome', max_length=60)

    objects = MunicipioQuerySet()

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"

    def __str__(self):
        return "%s/%s" % (self.nome, self.estado.sigla)


class EspecialidadeQuerySet(models.QuerySet):
    def all(self):
        return (
            self.search('nome')
            .fields('cbo', 'nome', 'area', 'get_qtd_profissonais_saude')
            .filters('categoria', 'area')
            .actions('especialidade.profissionaissaude')
        )
    

class Especialidade(models.Model):

    cbo = models.CharField(verbose_name="Código", max_length=6, null=True, blank=True)
    nome = models.CharField(max_length=150)

    area = models.ForeignKey(Area, verbose_name='Área', on_delete=models.CASCADE, null=True, blank=True)

    objects = EspecialidadeQuerySet()

    class Meta:
        verbose_name = 'Especialidade'
        verbose_name_plural = 'Especialidades'

    def get_profissonais_saude(self):
        return self.profissionalsaude_set.fields('pessoa_fisica', 'nucleo')
    
    @meta('Qtd. de Profissionais')
    def get_qtd_profissonais_saude(self):
        return self.profissionalsaude_set.count()

    def __str__(self):
        return self.nome


class PessoaFisicaQueryset(models.QuerySet):
    def all(self):
        return self.search("nome", "cpf").fields("nome", "cpf").filters('municipio', papel=RoleFilter('cpf'))

class PessoaFisica(models.Model):

    foto = models.ImageField(
        verbose_name="Foto", null=True, blank=True, upload_to="pessoas_fisicas"
    )

    nome = models.CharField(verbose_name='Nome', max_length=80)
    nome_social = models.CharField(verbose_name='Nome Social', max_length=80, null=True, blank=True)
    cpf = models.CharField(verbose_name='CPF', max_length=14, unique=True)

    endereco = models.CharField(verbose_name='Endereço', max_length=255, blank=True, null=True)
    numero = models.CharField(verbose_name='Número', max_length=255, blank=True, null=True)
    cep = models.CharField(verbose_name='CEP', max_length=255, blank=True, null=True)
    bairro = models.CharField(verbose_name='Bairro', max_length=255, blank=True, null=True)
    complemento = models.CharField(verbose_name='Complemento', max_length=150, blank=True, null=True)
    municipio = models.ForeignKey(Municipio, verbose_name='Município', null=True, on_delete=models.PROTECT, blank=False)
    data_nascimento = models.DateField(verbose_name='Data de Nascimento', null=True)
    cns = models.CharField(verbose_name='CNS', max_length=15, null=True, blank=True)

    sexo = models.ForeignKey(Sexo, verbose_name='Sexo', null=True, on_delete=models.PROTECT, pick=True)

    nome_responsavel = models.CharField(verbose_name='Nome do Responsável', max_length=80, null=True, blank=True)
    cpf_responsavel = models.CharField(verbose_name='CPF do Responsável', max_length=14, null=True, blank=True)

    email = models.CharField(verbose_name='E-mail', null=True, blank=True)
    telefone = models.CharField(verbose_name='Telefone', null=True, blank=False)

    objects = PessoaFisicaQueryset()

    class Meta:
        icon = "users"
        verbose_name = "Pessoa Física"
        verbose_name_plural = "Pessoas Físicas"

    def formfactory(self):
        return (
            super()
            .formfactory()
            .fieldset("Dados Gerais", (("cpf", "nome"), ("data_nascimento", "nome_social"), "sexo",))
            .fieldset("Dados de Contato", (("email", "telefone"),))
            .fieldset("Dados do Responsável", (("cpf_responsavel", "nome_responsavel"),),)
            .fieldset("Endereço", (("cep", "bairro"), "endereco", ("numero", "municipio")))
        )

    def serializer(self):
        return (
            super()
            .serializer()
            .fieldset("Dados Gerais", (("nome", "nome_social"), ("cpf", "data_nascimento"), ("sexo", "telefone"),),)
            .fieldset("Dados de Contato", (("email", "telefone"),))
            .fieldset("Endereço", (("cep", "bairro"), "endereco", ("numero", "municipio")))
        )

    def get_nome(self):
        if self.nome_social:
            return "%s / %s" % (self.nome_social, self.nome)
        else:
            return self.nome

    def __str__(self):
        if self.nome_social:
            return "%s / %s - %s" % (self.nome_social, self.nome, self.cpf)
        else:
            return "%s - %s" % (self.nome, self.cpf)

    def get_idade(self):
        today = date.today()
        if self.data_nascimento:
            return (
                today.year
                - self.data_nascimento.year
                - (
                    (today.month, today.day)
                    < (self.data_nascimento.month, self.data_nascimento.day)
                )
            )
        else:
            return "Não informada"
        
    def get_endereco(self):
        if self.endereco:
            endereco = [self.endereco]
            if self.numero: endereco.append(self.numero)
            if self.bairro: endereco.append(self.bairro)
            if self.cep: endereco.append(self.cep)
            if self.municipio: endereco.append(str(self.municipio))
            if self.complemento: endereco.append(self.complemento)
            return ', '.join(endereco)
        return None
    
    def get_atendimentos(self):
        return self.atendimentos_paciente.all().filters('especialidade').actions('atendimento.view')


class UnidadeQuerySet(models.QuerySet):
    def all(self):
        return (
            self.search("cnes", "nome")
            .fields("foto", "get_qtd_profissionais_saude")
            .filters("municipio__estado", "municipio").cards()
        )

@role('gu', username='gestores__cpf', unidade='pk')
@role('ou', username='operadores__cpf', unidade='pk')
class Unidade(models.Model):
    foto = models.ImageField(
        verbose_name="Foto", null=True, blank=True, upload_to="unidades", width=300
    )

    cnes = models.CharField(verbose_name="CNES", max_length=12, null=True, blank=True)
    nome = models.CharField(max_length=100)
    municipio = models.ForeignKey(
        Municipio, on_delete=models.CASCADE
    )

    logradouro = models.CharField(verbose_name='Logradouro', max_length=120, null=True, blank=True)
    numero = models.CharField(verbose_name='Número', max_length=10, null=True, blank=True)
    bairro = models.CharField(verbose_name='Bairro', max_length=40, null=True, blank=True)
    cep = models.CharField(verbose_name='CEP', max_length=10, null=True, blank=True)

    latitude = models.CharField(verbose_name="Latitude", null=True, blank=True)
    longitude = models.CharField(verbose_name="Longitude", null=True, blank=True)

    gestores = models.ManyToManyField(PessoaFisica, verbose_name="Gestores", blank=True, related_name='r3')
    operadores = models.ManyToManyField(PessoaFisica, verbose_name="Operadores", blank=True, related_name='r4')

    objects = UnidadeQuerySet()

    class Meta:
        icon = "building"
        verbose_name = "Unidade de Saúde"
        verbose_name_plural = "Unidades de Saúde"

    def serializer(self):
        return (
            super()
            .serializer().actions('unidade.edit')
            .fieldset("Dados Gerais", ("foto", ("nome", "cnes"), 'gestores', 'operadores'))
            .fieldset("Endereço", (("cep", "bairro"), "logradouro", ("numero", "municipio")))
            .fieldset("Geolocalização", (("latitude", "longitude"), 'get_mapa'))
            .queryset("Profissionais de Saúde", 'get_profissionais_saude')
        )

    def formfactory(self):
        return (
            super()
            .formfactory()
            .fieldset("Dados Gerais", ("foto", ("nome", "cnes"), 'gestores:pessoafisica.add', 'operadores:pessoafisica.add'))
            .fieldset("Endereço", (("cep", "bairro"), "logradouro", ("numero", "municipio")))
            .fieldset("Geolocalização", (("latitude", "longitude"),))
        )

    def __str__(self):
        return self.nome
    
    @meta()
    def get_foto(self):
        return Image(self.foto, placeholder='/static/images/sus.png', width='auto', height='auto')
    
    @meta('Mapa')
    def get_mapa(self):
        return Map(self.latitude, self.longitude) if self.latitude and self.longitude else None
    
    @meta('Profissionais de Saúde')
    def get_profissionais_saude(self):
        return self.profissionalsaude_set.all().actions('unidade.addprofissionalsaude', 'profissionalsaude.edit', 'profissionalsaude.view')
    
    @meta('Quantidade de Profissionais')
    def get_qtd_profissionais_saude(self):
        return self.profissionalsaude_set.count()
    


class NucleoQuerySet(models.QuerySet):
    def all(self):
        return self.fields('nome', 'gestores', 'operadores', 'get_qtd_profissonais_saude').actions('nucleo.agenda').cards()


@role('g', username='gestores__cpf', nucleo='pk')
@role('o', username='operadores__cpf', nucleo='pk')
class Nucleo(models.Model):
    nome = models.CharField(verbose_name='Nome')
    gestores = models.ManyToManyField(PessoaFisica, verbose_name="Gestores", blank=True)
    operadores = models.ManyToManyField(PessoaFisica, verbose_name="Operadores", blank=True, related_name='r2')
    unidades = models.ManyToManyField(Unidade, verbose_name='Unidades Atendidas', blank=True)

    objects = NucleoQuerySet()

    class Meta:
        icon = "building-user"
        verbose_name = "Núcleo de Telessaúde"
        verbose_name_plural = "Núcleos de Telessaúde"

    def formfactory(self):
        return (
            super()
            .formfactory()
            .fieldset("Dados Gerais", ("nome", 'gestores:pessoafisica.add', 'operadores:pessoafisica.add'))
            .fieldset("Atuação", ("unidades",),)
        )

    def serializer(self):
        return (
            super()
            .serializer().actions('nucleo.edit')
            .fieldset("Dados Gerais", ("nome", 'gestores', 'operadores'))
            .group('Detalhamento')
                .queryset('Unidades Atendidas', 'get_unidades')
                .queryset('Profissionais de Saúde', 'get_profissionais_saude')
            .parent()
        )
    
    @meta('Profissionais de Saúde')
    def get_profissionais_saude(self):
        return self.profissionalsaude_set.all().filters('especialidade').actions('nucleo.addprofissionalsaude')
    
    @meta('Qtd. de Profissionais')
    def get_qtd_profissonais_saude(self):
        return self.profissionalsaude_set.count()

    @meta('Gestores')
    def get_gestores(self):
        return self.gestores.fields('cpf', 'nome')
    
    @meta('Operadores')
    def get_operadores(self):
        return self.operadores.fields('cpf', 'nome')

    @meta()
    def get_agenda(self, semana=1, url=None):
        qs = HorarioProfissionalSaude.objects.filter(
            profissional_saude__nucleo=self, data_hora__gte=datetime.now()
        )
        start_day = date.today() + timedelta(days=((semana-1)*7))
        scheduler = Scheduler(start_day=start_day, chucks=3, readonly=True, url=url)
        campos = ("data_hora", "profissional_saude__pessoa_fisica__nome", "profissional_saude__especialidade__area__nome")
        qs1 = qs.filter(atendimentos_especialista__isnull=True)
        qs2 = qs.filter(atendimentos_especialista__isnull=False)
        horarios = {}
        for i, atendimentos in enumerate([qs1, qs2]):
            for data_hora, nome, area in atendimentos.values_list(*campos):
                if data_hora not in horarios:
                    horarios[data_hora] = []
                profissional = f'{nome} ({area.upper()} )' if area else nome
                horarios[data_hora].append(Text(profissional, color="#a4e2a4" if i==0 else "#f47c7c"))
        for data_hora, text in horarios.items():
            scheduler.append(data_hora, text, icon='stethoscope')
        return scheduler
    
    @meta('Unidades de Atuação')
    def get_unidades(self):
        return self.unidades.all().actions('unidade.view', 'unidade.edit')
    
    def __str__(self):
        return self.nome  

class ProfissionalSaudeQueryset(models.QuerySet):
    def all(self):
        return (
            self.search("pessoa_fisica__nome", "pessoa_fisica__cpf")
            .filters("nucleo", "unidade", "especialidade",)
            .fields("get_estabelecimento", "especialidade")
            .actions('profissionalsaude.definirhorario', 'profissionalsaude.alteraragenda')
        ).cards()

@role('ps', username='pessoa_fisica__cpf')
class ProfissionalSaude(models.Model):
    pessoa_fisica = models.ForeignKey(
        PessoaFisica,
        on_delete=models.PROTECT,
        verbose_name="Pessoa Física",
    )
    registro_profissional = models.CharField(
        "Nº do Registro Profissional", max_length=30, blank=False
    )
    conselho_profissional = models.ForeignKey(
       ConselhoClasse, verbose_name="Conselho Profissional", blank=False, null=True
    )
    especialidade = models.ForeignKey(
        Especialidade, null=True, on_delete=models.CASCADE
    )
    registro_especialista = models.CharField(
        "Nº do Registro de Especialista", max_length=30, blank=True, null=True
    )
    conselho_especialista = models.ForeignKey(
       ConselhoClasse, verbose_name="Conselho de Especialista", blank=True, null=True, related_name='r3'
    )
    programa_provab = models.BooleanField(verbose_name='Programa PROVAB', default=False)
    programa_mais_medico = models.BooleanField(verbose_name='Programa Mais Médico', default=False)
    residente = models.BooleanField(verbose_name='Residente', default=False)
    perceptor = models.BooleanField(verbose_name='Perceptor', default=False)
    
    ativo = models.BooleanField(default=False)
    # Atenção primária
    unidade = models.ForeignKey(Unidade, verbose_name='Unidade', null=True, on_delete=models.CASCADE)
    # Teleatendimento
    nucleo = models.ForeignKey(Nucleo, verbose_name='Núcleo', null=True, on_delete=models.CASCADE)

    objects = ProfissionalSaudeQueryset()

    class Meta:
        icon = "stethoscope"
        verbose_name = "Profissional de Saúde"
        verbose_name_plural = "Profissionais de Saúde"
        search_fields = 'pessoa_fisica__cpf', 'pessoa_fisica__nome'

    def enviar_senha_acesso(self, mensagem=None):
        if self.pessoa_fisica.email:
            senha = uuid1().hex[0:6]
            user = User.objects.get(username=self.pessoa_fisica.cpf)
            user.set_password(senha)
            user.save()
            subject = "Telefiocruz - Primeiro Acesso"
            content = "<p>Sua senha de acesso ao sistema é <b>{}</b>.</p>".format(senha)
            url = settings.SITE_URL
            email = Email(to=self.pessoa_fisica.email, subject=subject, content=content, action="Acessar", url=url)
            email.send()

    def assinar_arquivo_pdf(self, caminho_arquivo, token):
        url = 'https://certificado.vidaas.com.br/valid/api/v1/trusted-services/signatures'
        filename = caminho_arquivo.split('/')[-1]
        filecontent = open(caminho_arquivo, 'r+b').read()
        base64_content = base64.b64encode(filecontent).decode()
        sha256 = hashlib.sha256()
        sha256.update(filecontent)
        hash=sha256.hexdigest()
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer {}'.format(token)}
        data = {"hashes": [{"id": filename, "alias": filename, "hash": hash, "hash_algorithm": "2.16.840.1.101.3.4.2.1", "signature_format": "CAdES_AD_RB", "base64_content": base64_content,}]}
        response = requests.post(url, json=data, headers=headers).json()
        file_content=base64.b64decode(response['signatures'][0]['file_base64_signed'].replace('\r\n', ''))
        open(caminho_arquivo, 'w+b').write(file_content)

    def assinar_arquivo_imagem(self, caminho_arquivo):
        caminho_arquivo_pdf = f'{caminho_arquivo}.pdf'
        PILImage.open(caminho_arquivo).save(caminho_arquivo_pdf, "PDF")
        self.assinar_arquivo_pdf(caminho_arquivo_pdf)

    def get_horarios_ocupados(self, semana=1):
        horarios_ocupados = {}
        midnight = datetime.combine(datetime.now().date(), time())
        qs_teleconsultor = HorarioProfissionalSaude.objects.filter(data_hora__gte=midnight, profissional_saude__pessoa_fisica=self.pessoa_fisica, atendimentos_profissional_saude__situacao=SituacaoAtendimento.AGENDADO)
        qs_teleconsultor = qs_teleconsultor.da_semana(semana).values_list('data_hora', 'atendimentos_profissional_saude').order_by('-data_hora')
        for data_hora, pk in qs_teleconsultor:
            horarios_ocupados[data_hora] = pk
        qs_teleinterconsultor = HorarioProfissionalSaude.objects.filter(data_hora__gte=midnight, profissional_saude__pessoa_fisica=self.pessoa_fisica, atendimentos_especialista__situacao=SituacaoAtendimento.AGENDADO)
        qs_teleinterconsultor = qs_teleinterconsultor.da_semana(semana).values_list('data_hora', 'atendimentos_especialista').order_by('-data_hora')
        for data_hora, pk in qs_teleinterconsultor:
            horarios_ocupados[data_hora] = pk
        return horarios_ocupados
    
    def get_horarios_disponiveis(self, semana=1):
        return self.horarioprofissionalsaude_set.da_semana(semana=semana).filter(
            data_hora__gte=datetime.now()
        ).exclude(data_hora__in=self.get_horarios_ocupados(semana=semana).keys()).values_list('data_hora', flat=True)


    def criar_sala_virtual(self, nome):
        pass

    def is_user(self, user):
        return self.pessoa_fisica.cpf == user.username

    def formfactory(self):
        return (
            super()
            .formfactory()
            .fieldset("Dados Gerais", (("pessoa_fisica:pessoafisica.add",),))
            .fieldset("Dados Profissionais", ("especialidade", ("conselho_profissional", "registro_profissional"), ("conselho_especialista", "registro_especialista",),),)
            .fieldset("Informações Adicionais", (("programa_provab", "programa_mais_medico"), ("residente", "perceptor"),),)
        ) if self.pk is None else (
            super()
            .formfactory()
            .fieldset("Dados Profissionais", ("especialidade", ("conselho_profissional", "registro_profissional"), ("conselho_especialista", "registro_especialista"),),)
            .fieldset("Informações Adicionais", (("programa_provab", "programa_mais_medico"), ("residente", "perceptor"),),)
        )


    def serializer(self):
        return (
            super()
            .serializer()
            .actions("profissionalsaude.edit", "profissionalsaude.definirhorario", "profissionalsaude.alteraragenda")
            .fieldset("Dados Gerais", (("pessoa_fisica"),))
            .fieldset("Dados Profissionais", (("especialidade", "get_estabelecimento"), ("conselho_profissional", "registro_profissional"), ("conselho_especialista", "registro_especialista"),),)
            .group()
                .fieldset("Outras Informações", (("programa_provab", "programa_mais_medico"), ("residente", "perceptor"),),)
                .fieldset("Horário de Atendimento", ("get_horarios_atendimento",))
                .fieldset("Agenda", ("get_agenda",))
            .parent()
        )

    def __str__(self):
        return "{} / {} / {} / {}".format(
            self.pessoa_fisica.nome,
            self.get_registro_profissional(),
            self.especialidade,
            self.get_estabelecimento(),
        )

    def get_registro_profissional(self):
        return f'{self.conselho_profissional} {self.registro_profissional}'
    
    def get_registro_especialista(self):
        return f'{self.conselho_especialista} {self.registro_especialista}' if self.conselho_especialista else None
    
    def pode_realizar_atendimento(self, data_hora, duracao):
        disponivel = self.horarioprofissionalsaude_set.filter(data_hora=data_hora).disponiveis().exists()
        if disponivel and duracao >= 40:
            disponivel = self.horarioprofissionalsaude_set.filter(data_hora=data_hora + timedelta(minutes=20)).disponiveis().exists()
            if disponivel and duracao == 60:
                disponivel = self.horarioprofissionalsaude_set.filter(data_hora=data_hora + timedelta(minutes=40)).disponiveis().exists()
        return disponivel

    @meta(None)
    def get_agenda(self, readonly=True, single_selection=False, available=True, semana=1, url=None):
        start_day = date.today() + timedelta(days=((semana-1)*7))
        scheduler = Scheduler(start_day=start_day, readonly=readonly, chucks=3, single_selection=single_selection, url=url)
        for data_hora, pk in self.get_horarios_ocupados(semana=semana).items():
            scheduler.append(data_hora, f'Atendimento {pk}', icon='stethoscope')
        if available:
            for data_hora in self.get_horarios_disponiveis(semana=semana):
                scheduler.append(data_hora)
        return scheduler
    
    def get_horarios_atendimento(self, readonly=True):
        scheduler=Scheduler(weekly=True, chucks=3, readonly=readonly)
        for ha in self.horarioatendimento_set.all():
           scheduler.append_weekday(ha.dia, ha.hora, ha.minuto)
        return scheduler
    
    def atualizar_horarios_atendimento(self, inicio, fim, adicionar_datas, remover_datas):
        for data in adicionar_datas:
            HorarioAtendimento.objects.get_or_create(profissional_saude=self, dia=data.weekday(), hora=data.hour, minuto=data.minute)
        for data in remover_datas:
            HorarioAtendimento.objects.filter(profissional_saude=self, dia=data.weekday(), hora=data.hour, minuto=data.minute).delete()
        dias_semana = {}
        for ha in self.horarioatendimento_set.all():
            if int(ha.dia)not in dias_semana:
                dias_semana[int(ha.dia)] = []
            dias_semana[int(ha.dia)].append(ha)
        
        horarios = HorarioProfissionalSaude.objects.filter(
            profissional_saude=self, data_hora__gte=inicio, data_hora__lte=fim + timedelta(days=1),
            atendimentos_profissional_saude__isnull=True, atendimentos_especialista__isnull=True
        )
        if inicio and fim:
            ids = []
            while inicio <= fim:
                for ha in dias_semana.get(inicio.weekday(), ()):
                    hps = HorarioProfissionalSaude.objects.get_or_create(
                        profissional_saude=self, data_hora=datetime(inicio.year, inicio.month, inicio.day, ha.hora, ha.minuto)
                    )[0]
                    ids.append(hps.id)
                inicio += timedelta(days=1)
            horarios.exclude(id__in=ids).delete()

    @meta('Estabelecimento')
    def get_estabelecimento(self):
        return self.nucleo if self.nucleo_id else self.unidade


class HorarioAtendimento(models.Model):
    DIA_SEMANA_CHOICES = [[i, j] for i, j in enumerate(('SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM'))]
    
    profissional_saude = models.ForeignKey(ProfissionalSaude, verbose_name='Profissional de Saúde', on_delete=models.CASCADE)
    dia = models.CharField(verbose_name='Dia da Semana', choices=DIA_SEMANA_CHOICES)
    hora = models.IntegerField(verbose_name='Hora')
    minuto = models.IntegerField(verbose_name='Minuto')

    class Meta:
        verbose_name = 'Horário de Atendimento'
        verbose_name_plural = 'Horários de Atendimento'

    def __str__(self):
        return f'{self.id} - {self.get_dia_display()} ({self.dia}, {self.hora})'
  

class HorarioProfissionalQuerySet(models.QuerySet):
    def disponiveis(self):
        return self.filter(
            atendimentos_profissional_saude__isnull=True,
            atendimentos_especialista__isnull=True,
            data_hora__gte=datetime.now()
        )
    
    def da_semana(self, semana=1):
        ate = date.today() + timedelta(days=(semana*7)+1)
        return self.filter(data_hora__lt=ate)


class HorarioProfissionalSaude(models.Model):
    profissional_saude = models.ForeignKey(
        ProfissionalSaude,
        verbose_name="Profissional de Saúde",
        on_delete=models.CASCADE,
    )
    data_hora = models.DateTimeField(verbose_name="Data/Hora")

    objects = HorarioProfissionalQuerySet()

    class Meta:
        verbose_name = "Horário de Atendimento"
        verbose_name_plural = "Horários de Atendimento"

    def __str__(self):
        return "{}".format(
            self.data_hora.strftime("%d/%m/%Y %H:%M")
        )


class SituacaoAtendimentoQuerySet(models.QuerySet):
    def all(self):
        return self


class SituacaoAtendimento(models.Model):
    AGENDADO = 1
    REAGENDADO = 2
    CANCELADO = 3
    FINALIZADO = 4
    
    nome = models.CharField(verbose_name='Nome')
    
    class Meta:
        verbose_name = 'Situação de Atendimento'
        verbose_name_plural = 'Situações de Atendimento'

    objects = SituacaoAtendimentoQuerySet()

    def __str__(self):
        return self.nome


class AtendimentoQuerySet(models.QuerySet):
    def all(self):
        return (
            self.filters("especialidade", "profissional__unidade", "paciente", "profissional", "especialista")
            .fields(
                ("especialidade", "agendado_para", "tipo"),
                ("get_estabelecimento", "profissional", "paciente"),
                ("especialista", "get_duracao_prevista"), "get_tags"
            ).limit(5).order_by('-id')
        )
    
    def do_dia(self):
        midnight = datetime.combine(datetime.now().date(), time())
        tomorrow = midnight + timedelta(days=1)
        return self.filter(agendado_para__gte=midnight, agendado_para__lte=tomorrow, finalizado_em__isnull=True)
    
    @meta('Total de Atendimentos')
    def get_total(self):
        return self.total()
    
    @meta('Profissionais Envolvidos')
    def get_total_profissioinais(self):
        return self.total('profissional')
    
    @meta('Pacientes Atendidos')
    def get_total_pacientes(self):
        return self.total('paciente')
    
    @meta('Total por Tipo de Atendimento')
    def get_total_por_tipo(self):
        return self.counter('tipo', chart='bar')
    
    @meta('Total por Especialidade')
    def get_total_por_area(self):
        return self.counter('especialidade__area', chart='donut')
    
    @meta('Total por Situação')
    def get_total_por_situacao(self):
        return self.counter('situacao', chart='pie')
    
    @meta('Total por Mês')
    def get_total_por_mes(self):
        return self.counter('agendado_para__month', chart='line')
    
    @meta('Atendimentos por Unidade e Especialidade')
    def get_total_por_area_e_unidade(self):
        return self.counter('especialidade__area__especialidade', 'unidade')
    
    def agenda(self, profissional=None, especialista=None, is_teleconsulta=False, is_proprio_profissional=False, semana=1):
        selectable = []
        scheduled = {}
        if profissional:
            # exibir os horários ocupados
            for data_hora, pk in profissional.get_horarios_ocupados(semana=semana).items():
                scheduled[data_hora] = pk
            # agenda ocupada do profissional de saúde
            if is_proprio_profissional:
                if especialista:
                    # pode agendar uma teleconsulta em qualquer horário disponível do especialista
                    selectable = especialista.get_horarios_disponiveis(semana=semana)
                # pode agendar uma teleconsulta em qualquer dia/horário independente do seu horário de trabalho
                else:
                    selectable = None
            else:
                selectable = profissional.get_horarios_disponiveis(semana=semana)
                if especialista:
                    # exibir os horários ocupados do especialista
                    for data_hora, pk in especialista.get_horarios_ocupados(semana=semana).items():
                        scheduled[data_hora] = pk
                    # cruzando os horários de atendimento do profissional de saúde com os do especialista
                    selectable = selectable.filter(data_hora__in=especialista.get_horarios_disponiveis(semana=semana))
        start_day = date.today() + timedelta(days=((semana-1)*7))
        scheduler = Scheduler(
            start_day=start_day,
            chucks=3,
            watch=['profissional', 'especialista'],
            url='/api/atendimento/horariosdisponiveis/',
            single_selection=True,
            selectable=selectable,
            readonly=False
        )
        for dt, pk in scheduled.items():
            scheduler.append(dt, 'Atendimento {}'.format(pk), 'stethoscope')
        return scheduler

@role('p', username='paciente__cpf')
class Atendimento(models.Model):
    profissional = models.ForeignKey(
        ProfissionalSaude,
        verbose_name='Profissional Responsável',
        related_name="atendimentos_profissional",
        on_delete=models.CASCADE,
        null=True
    )
    especialista = models.ForeignKey(
        ProfissionalSaude,
        related_name="atendimentos_especialista",
        on_delete=models.CASCADE,
        null=True, blank=True, pick = True
    )

    especialidade = models.ForeignKey(
        Especialidade, verbose_name='Especialidade', on_delete=models.CASCADE, pick=True
    )

    tipo = models.ForeignKey(
        TipoAtendimento, verbose_name='Tipo de Atendimento', on_delete=models.CASCADE, pick=True
    )

    cid = models.ManyToManyField(CID, verbose_name='CID', blank=True)
    ciap = models.ManyToManyField(CIAP, verbose_name='CIAP', blank=True)

    data = models.DateTimeField(blank=True)
    assunto = models.CharField(verbose_name='Motivo',max_length=200)
    duvida = models.TextField(verbose_name='Dúvida/Queixa', max_length=2000)
    paciente = models.ForeignKey(
        "PessoaFisica", verbose_name='Paciente', related_name="atendimentos_paciente", on_delete=models.PROTECT
    )
    duracao = models.IntegerField(verbose_name='Duração Prevista', null=True, choices=[(20, '20min'), (40, '40min'), (60, '1h')], pick=True, default=20)
    horarios_profissional_saude = models.ManyToManyField(HorarioProfissionalSaude, verbose_name='Horários', blank=True, related_name='atendimentos_profissional_saude', pick=True)
    horarios_especialista = models.ManyToManyField(HorarioProfissionalSaude, verbose_name='Horários', blank=True, related_name='atendimentos_especialista', pick=True)
    horario_excepcional = models.BooleanField(
        verbose_name="Horário Excepcional",
        default=False,
        help_text="Marque essa opção caso deseje agendar em um horário fora da agenda do profissional.",
    )
    agendado_para = models.DateTimeField(verbose_name='Data Prevista', null=True, blank=True)
    iniciado_em = models.DateTimeField(verbose_name='Data de Início', null=True, blank=True)
    finalizado_em = models.DateTimeField(verbose_name='Data de Término', null=True, blank=True)

    situacao = models.ForeignKey(SituacaoAtendimento, verbose_name='Situação', on_delete=models.CASCADE, null=True)
    motivo_cancelamento = models.TextField(verbose_name='Motivo do Cancelamento', null=True)
    motivo_reagendamento = models.TextField(verbose_name='Motivo do Reagendamento', null=True)

    token = models.CharField(verbose_name='Token', null=True, blank=True)
    data_hora_confirmacao = models.DateTimeField(verbose_name='Data/Hora da Confirmação', null=True)
    
    emails = models.ManyToManyField(Email, verbose_name='E-mails', blank=True)

    objects = AtendimentoQuerySet()

    class Meta:
        icon = "laptop-file"
        verbose_name = "Atendimento"
        verbose_name_plural = "Atendimentos"

    def is_envolvido(self, user):
        return user.is_superuser or (user.username and user.username in Atendimento.objects.filter(pk=self.pk).values_list(
            'paciente__cpf', 'profissional__pessoa_fisica__cpf', 'especialista__pessoa_fisica__cpf'
        ).first())

    def get_envolvidos(self, paciente=True, profissional=True, especialista=True):
        envolvidos = []
        if paciente:
            envolvidos.append(self.paciente)
        if profissional:
            envolvidos.append(self.profissional.pessoa_fisica)
        if especialista and self.especialista:
            envolvidos.append(self.especialista.pessoa_fisica)
        return envolvidos
    
    @meta('Notificações')
    def get_notificacoes(self):
        return self.notificacao_set.fields('canal', 'data_hora', 'destinatario', 'mensagem', 'get_situacao')
    
    def enviar_notificacao(self, mensagem=None, complemento=None, remetente=None):
        data_hora_envio = datetime.now()
        for pessoa_fisica in self.get_envolvidos():
            if pessoa_fisica == remetente:
                continue
            data_hora = self.agendado_para
            fuso_horario = pessoa_fisica.municipio and pessoa_fisica.municipio.estado and pessoa_fisica.municipio.estado.fuso_horario or None
            if fuso_horario:
                data_hora = fuso_horario.localtime(data_hora)
            url = self.get_url_externa() if pessoa_fisica == self.paciente else self.get_url_interna()
            subject = "Telefiocruz - Notificação de Atendimento"
            content = self.get_conteudo_notificacao_email(mensagem, complemento, data_hora, pessoa_fisica.municipio, url)
            if pessoa_fisica.email:
                Email.objects.create(to=pessoa_fisica.email, subject=subject, content=content, send_at=data_hora_envio, action="Acessar", url=url)
                Notificacao.objects.create(atendimento=self, data_hora=data_hora_envio, canal=Notificacao.CANAL_EMAIL, mensagem=mensagem, destinatario=pessoa_fisica)
            if pessoa_fisica.telefone:
                # notificação do agendamento
                content = self.get_conteudo_notificacao_whatsapp(mensagem, complemento, data_hora, pessoa_fisica.municipio, url)
                WhatsappNotification.objects.create(pessoa_fisica.telefone, subject, content, send_at=data_hora_envio, url=url)
                Notificacao.objects.create(atendimento=self, data_hora=data_hora_envio, canal=Notificacao.CANAL_WHATSAPP, mensagem=mensagem, destinatario=pessoa_fisica)
    
    def agendar_notificacao(self):
        data_hora = self.agendado_para
        fuso_horario = self.paciente.municipio and self.paciente.municipio.estado and self.paciente.municipio.estado.fuso_horario or None
        if fuso_horario:
            data_hora = fuso_horario.localtime(data_hora)
        key = 'agendamento_notificacao_atendimento_{}'.format(self.pk)
        subject = "Telefiocruz - Notificação de Atendimento"
        # notificação para confirmação um dia antes
        dia_anterior = self.agendado_para - timedelta(days=1)
        mensagem = "Confirme sua presença clicando no link abaixo."
        content = self.get_conteudo_notificacao_whatsapp(mensagem, {}, data_hora, self.paciente.municipio, self.get_url_confirmacao())
        WhatsappNotification.objects.create(self.paciente.telefone, subject, content, send_at=dia_anterior, url=None, key=key)
        Notificacao.objects.create(atendimento=self, data_hora=dia_anterior, canal=Notificacao.CANAL_WHATSAPP, mensagem=mensagem, destinatario=self.paciente)
        # notificação para acesso em uma hora
        hora_anterior = self.agendado_para - timedelta(hours=1)
        mensagem = "Não esqueça do seu atendimento. Acesse o link no horário marcado."
        content = self.get_conteudo_notificacao_whatsapp(mensagem, {}, data_hora, self.paciente.municipio, self.get_url_externa())
        WhatsappNotification.objects.create(self.paciente.telefone, subject, content, send_at=hora_anterior, url=None, key=key)
        Notificacao.objects.create(atendimento=self, data_hora=hora_anterior, canal=Notificacao.CANAL_WHATSAPP, mensagem=mensagem, destinatario=self.paciente)

    def get_conteudo_notificacao_email(self, mensagem, complemento, data_hora, municipio, url):
        content =  "<p>Notificação referente ao atendimento <b>Nº {}</b>: {}</p>".format(self.get_numero()['label'], mensagem or "")
        content += "<p><b>Data/Hora</b>: {} ({})</p>".format(data_hora.strftime('%d/%m/%Y %H:%M'), municipio or '')
        content += "<p><b>Especialidade</b>: {}</p>".format(self.especialidade)
        content += "<p><b>Profissional Responsável</b>: {}</p>".format(self.profissional)
        if self.especialista:
            content += "<p><b>Especialista</b>: {}</p>".format(self.especialista)
        for k, v in (complemento or {}).items():
                content += "<p><b>{}</b>: {}</p>".format(k, v)
        return content

    def get_conteudo_notificacao_whatsapp(self, mensagem, complemento, data_hora, municipio, url):
        content = "*SISTEMA TELEFIOCRUZ*\n\n"
        content += "Notificação referente ao atendimento *nº {}*: {}\n\n".format(self.get_numero()['label'], mensagem or "")
        content += "*Data/Hora*: {} ({})\n".format(data_hora.strftime('%d/%m/%Y %H:%M'), municipio or '')
        content += "*Especialidade*: {}\n".format(self.especialidade)
        content += "*Profissional Responsável*: {}\n".format(self.profissional)
        if self.especialista:
            content += "*Especialista*: {}\n\n".format(self.especialista)
        for k, v in (complemento or {}).items():
                content += "*{}*: {}\n".format(k, v)
        content += "*Link*: {}".format(url)
        return content

    def formfactory(self):
        return (
            super()
            .formfactory()
            .fieldset("Dados Gerais", ("tipo", "especialidade",),)
            .fieldset("Detalhamento", ("paciente:pessoafisica.add", "assunto", "duvida", ("cid", "ciap"),),)
            .fieldset("Agendamento", ("profissional", "especialista", "duracao", "agendado_para",),)
        )
    
    def get_estabelecimento(self):
        return self.profissional.get_estabelecimento()
    
    def serializer(self):
        return (
            super()
            .serializer()
            .fields('get_tags')
            .actions('atendimento.enviarnotificacao', 'atendimento.anexararquivo', 'salavirtual', 'atendimento.emitiratestado', 'atendimento.solicitarexames', 'atendimento.prescrevermedicamento', 'atendimento.registrarecanminhamentoscondutas', 'atendimento.reagendaratendimento', 'atendimento.cancelaratendimento', 'atendimento.retornoatendimento', 'atendimento.finalizaratendimento')
            .fieldset(
                "Dados Gerais",
                (
                    ("id", "tipo", "get_estabelecimento", "situacao"),
                    ("agendado_para", "get_duracao_prevista", "iniciado_em", "finalizado_em"),
                    "get_url_externa"
                ) 
            )
            .group()
                .section('Detalhamento')
                    .fieldset(
                        "Dados da Consulta", (
                            ("assunto", "especialidade"),
                            "duvida",
                            ("cid", "ciap"),
                        )
                    )
                    .fieldset(
                        "Dados do Paciente", (
                            ("cpf", "nome"),
                            ("sexo", "nome_social"),
                            ("data_nascimento", "get_idade"),
                            ("telefone", "email")
                        ), attr="paciente", actions=('pessoafisica.atualizarpaciente', 'pessoafisica.historicopaciente') if self.is_agendado() else ()
                    )
                    .fieldset(
                        "Profissional Responsável", (
                            ("pessoa_fisica__nome", "get_registro_profissional", "get_registro_especialista"),
                        ), attr="profissional"
                    )
                    .fieldset(
                        "Dados do Especialista", (
                            ("pessoa_fisica__nome", "get_registro_profissional", "get_registro_especialista"),
                        ), attr="especialista", condition='especialista'
                    )
                    .queryset('Anexos', 'get_anexos')
                    .fieldset('Outras Informações', ("motivo_cancelamento", "motivo_reagendamento"))
                .parent()
                .queryset('Encaminhamentos', 'get_condutas_ecaminhamentos', roles=('ps',))
                .queryset('Notificações', 'get_notificacoes')
            .parent()
        )
    
    @meta('Número')
    def get_numero(self):
        return Badge('#2670e8', str(self.id).rjust(6, '0'))
    
    @meta('Duração Prevista')
    def get_duracao_prevista(self):
        return f'{self.duracao} minutos'
    
    @meta()
    def get_tags(self):
        tags = []
        if self.tipo_id == TipoAtendimento.TELE_INTERCONSULTA:
            color = "#265890"
            icon = 'people-group'
        else:
            color = '#265890'
            icon = 'people-arrows'
        tag = Badge(color, self.tipo, icon=icon)
        tags.append(tag)
        tags.append(self.get_situacao())
        if self.data_hora_confirmacao:
            tags.append(Badge("#5ca05d", 'Confirmado pelo Paciente', icon='person-circle-check'))
        return tags
    
    @meta('Situação')
    def get_situacao(self):
        if self.situacao_id == SituacaoAtendimento.FINALIZADO:
            return Badge("#5ca05d", 'Finalizado', icon='check')
        elif self.situacao_id == SituacaoAtendimento.REAGENDADO:
            return Badge("#c4beb1", 'Reagendado', icon='calendar')
        elif self.situacao_id == SituacaoAtendimento.CANCELADO:
            return Badge("red", 'Cancelado', icon='x')
        elif self.situacao_id == SituacaoAtendimento.AGENDADO:
            return Badge("#d9a91f", 'Agendado', icon='clock')
    
    @meta('Anexos')
    def get_anexos(self):
        return self.anexoatendimento_set.fields('get_nome_arquivo', 'autor', 'assinaturas', 'get_arquivo')
    
    @meta('Anexos')
    def get_anexos_webconf(self):
        return self.get_anexos().reloadable()
    
    @meta('Encaminhamentos e Condutas')
    def get_condutas_ecaminhamentos(self):
        return self.encaminhamentoscondutas_set.fields(
            'data', 'subjetivo', 'objetivo', 'avaliacao', 'plano', 'comentario'
        ).timeline()

    @meta('Duração')
    def duracao_webconf(self):
        if self.finalizado_em and self.agendado_para:
            return timesince(self.agendado_para, self.finalizado_em)
        return "-"
    
    @meta(None)
    def get_termo_consentimento_digital(self):
        return TemplateContent('termoconsentimento.html', dict(atendimento=self))

    def is_termo_consentimento_assinado(self):
        return True
        termo_consentimento = self.get_termo_consentimento()
        if termo_consentimento:
            qtd_assinaturas = termo_consentimento.assinaturas.count()
            return qtd_assinaturas == (2 if self.especialista_id else 1)
        return False

    @meta('Termo de Consentimento')
    def get_termo_consentimento(self):
        return self.anexoatendimento_set.filter(nome='Termo de Consentimento').order_by('id').last()

    def get_agendado_para(self):
        return Badge("#5ca05d", self.agendado_para.strftime('%d/%m/%Y %H:%M'), icon='clock')

    @meta('URL Externa')
    def get_url_externa(self):
        return '{}/app/atendimento/publico/?token={}'.format(settings.SITE_URL, self.token)
    
    @meta('URL Confirmação')
    def get_url_confirmacao(self):
        return '{}/app/atendimento/confirmacao/?token={}'.format(settings.SITE_URL, self.token)
    
    @meta('URL Externa')
    def get_url_interna(self):
        return '{}/app/salavirtual/{}/'.format(settings.SITE_URL, self.pk)
    
    def get_qrcode_link_webconf(self):
        return qrcode_base64(self.get_url_externa())

    def __str__(self):
        return "%s - %s" % (self.id, self.assunto)
    
    def is_agendado(self):
        return self.situacao_id == SituacaoAtendimento.AGENDADO

    def save(self, *args, **kwargs):
        if self.token is None:
            self.token = uuid1().hex
        if self.data is None:
            self.data = timezone.now()
        if self.situacao_id is None:
            self.situacao_id = SituacaoAtendimento.AGENDADO
        super(Atendimento, self).save(*args, **kwargs)

    def post_save(self):
        minutos = [0]
        if self.duracao >= 40: minutos.append(20)
        if self.duracao == 60: minutos.append(40)
        # atendimentos marcados pelo próprio profissional não requer que o horário esteva previamente marcado em sua agenda
        for minuto in minutos:
            data_hora = self.agendado_para + timedelta(minutes=minuto)
            if not self.profissional.horarioprofissionalsaude_set.filter(data_hora=data_hora).exists():
                HorarioProfissionalSaude.objects.create(data_hora=data_hora, profissional_saude=self.profissional)
            if self.especialista_id and not self.especialista.horarioprofissionalsaude_set.filter(data_hora=data_hora).exists():
                HorarioProfissionalSaude.objects.create(data_hora=data_hora, profissional_saude=self.especialista)
        
        for minuto in minutos:
            data_hora = self.agendado_para + timedelta(minutes=minuto)
            self.horarios_profissional_saude.add(self.profissional.horarioprofissionalsaude_set.get(data_hora=data_hora))
            if self.especialista_id:
                self.horarios_especialista.add(self.especialista.horarioprofissionalsaude_set.get(data_hora=data_hora))
  
    def criar_anexo(self, nome, template, cpf, dados):
        AnexoAtendimento.objects.filter(atendimento=self, nome=nome).delete()
        autor = PessoaFisica.objects.get(cpf=cpf)
        anexo = AnexoAtendimento(atendimento=self, autor=autor, nome=nome)
        dados.update(atendimento=self, data_hora=date.today(), logo=f'{settings.SITE_URL}/static/images/icon-black.svg')
        writter = PdfWriter()
        writter.render(template, dados)
        anexo.arquivo.save('{}.pdf'.format(uuid1().hex), ContentFile(writter.pdf.output()))
        anexo.save()

    def cancelar(self):
        self.situacao_id = SituacaoAtendimento.CANCELADO
        self.save()
        complemento = {'Motivo do Cancelamento': self.motivo_cancelamento}
        self.enviar_notificacao('Atendimento cancelado.', complemento)

    @transaction.atomic()
    def reagendar(self, data_hora):
        numero = self.get_numero()['label']
        motivo = self.motivo_reagendamento
        self.situacao_id = SituacaoAtendimento.REAGENDADO
        self.save()
        self.pk = None
        self.situacao_id = None
        self.data = None
        self.agendado_para = data_hora
        self.motivo_reagendamento = None
        self.token = None
        self.save()
        self.post_save()
        complemento = {'Motivo do Reagendamento': motivo}
        self.enviar_notificacao(f'Atendimento anterior de número Nº {numero} reagendado. Observe a nova data/hora e acesse o link no dia/hora marcados.', complemento)
        self.agendar_notificacao()
        return self
    
    @transaction.atomic()
    def retorno(self, data_hora):
        self.pk = None
        self.situacao_id = None
        self.data = None
        self.data_hora_confirmacao = None
        self.agendado_para = data_hora
        self.motivo_reagendamento = None
        self.motivo_cancelamento = None
        self.token = None
        self.save()
        self.post_save()
        self.enviar_notificacao('Agendamento cadastrado. Leia atentamente as informações e acesse o link no dia/hora marcados.')
        self.agendar_notificacao()
        return self

    def finalizar(self, authorization_code=None):
        self.situacao_id = SituacaoAtendimento.FINALIZADO
        self.save()
        cpf = self.profissional.pessoa_fisica.cpf.replace('.', '').replace('-', '')
        # cpf = '04770402414'
        if authorization_code:
            for anexo in self.anexoatendimento_set.all():
                signer = VidaasPdfSigner(anexo.arquivo.path, f'{self.profissional.pessoa_fisica.nome}:{cpf}')
                signer.authorize(authorization_code)
                signer.sign(anexo.arquivo.path)
                anexo.checar_assinaturas()
        self.enviar_notificacao('Atendimento finalizado pelo profissional de saúde.')


class NotificacaoQuerySet(models.QuerySet):
    def all(self):
        return self


class Notificacao(models.Model):
    CANAL_EMAIL = 'E-mail'
    CANAL_WHATSAPP = 'Whatsapp'

    atendimento = models.ForeignKey(Atendimento, verbose_name='Atendimento', on_delete=models.CASCADE)
    canal = models.CharField(verbose_name='Canal')
    data_hora = models.DateTimeField(verbose_name='Data/Hora')
    destinatario = models.ForeignKey(PessoaFisica, verbose_name='Destinatário', on_delete=models.CASCADE)
    mensagem = models.CharField(verbose_name='Mensagem')

    class Meta:
        icon = 'mail-bulk'
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    objects = NotificacaoQuerySet()

    def __str__(self):
        return f'Notificação {self.id}'
    
    @meta('Destinatário')
    def get_destinatario(self):
        return self.destinatario.nome
    
    @meta('Situação')
    def get_situacao(self):
        return "Enviada" if self.data_hora <= datetime.now() else "Agendada"


class AnexoAtendimento(models.Model):
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.CASCADE
    )
    nome = models.CharField(verbose_name='Nome', default='')
    arquivo = models.FileField(max_length=200, upload_to="anexos_teleconsuta")
    autor = models.ForeignKey(PessoaFisica, null=True, on_delete=models.CASCADE)
    assinaturas = models.ManyToManyField(PessoaFisica, verbose_name='Assinaturas', blank=True, related_name='anexos_assinados')

    class Meta:
        verbose_name = "Anexo de Solicitação"
        verbose_name_plural = "Anexos de Solicitação"

    def __str__(self):
        return "%s" % self.atendimento

    @meta('Nome do Arquivo')
    def get_nome_arquivo(self):
        return self.nome
    
    def get_arquivo(self):
        return FileLink(self.arquivo, icon='file', modal=True)

    def possui_assinatura(self, cpf):
        if os.path.exists(self.arquivo.path):
            data = self.arquivo.read()
            def index_of(n=1):
                if n == 1:
                    return data.find(b'/ByteRange')
                else:
                    return data.find(b'/ByteRange', index_of(n - 1) + 1)

            for i in range(1, data.count(b'/ByteRange') + 1):
                n = index_of(i)
                start = data.find(b'[', n)
                stop = data.find(b']', start)
                assert n != -1 and start != -1 and stop != -1
                br = [int(i, 10) for i in data[start + 1: stop].split()]
                contents = data[br[0] + br[1] + 1: br[2] - 1]
                datas = bytes.fromhex(contents.decode('utf8'))
                try:
                    cpf = cpf.replace('.', '').replace('-', '')
                    datas.index(cpf.encode())
                    return True
                except ValueError:
                    return False
        return False
            
    def checar_assinaturas(self):
        if self.possui_assinatura('047.704.024-14'):
            self.assinaturas.add(PessoaFisica.objects.get(cpf='047.704.024-14'))
        if self.possui_assinatura(self.atendimento.profissional.pessoa_fisica.cpf):
            self.assinaturas.add(self.atendimento.profissional.pessoa_fisica)
        if self.atendimento.especialista:
            if self.possui_assinatura(self.atendimento.especialista.pessoa_fisica.cpf):
                self.assinaturas.add(self.atendimento.especialista.pessoa_fisica)
    

class AvaliacaoAtendimento(models.Model):
    SATISFACAO = (
        (1, "Muito Satisfeito"),
        (2, "Satisfeito"),
        (3, "Indiferente"),
        (4, "Insatisfeito"),
        (5, "Muito Insatisfeito"),
    )
    RESPONDEU_DUVIDA = ((1, "Sim"), (2, "Parcialmente"), (3, "Não"))
    EVITOU_ENCAMINHAMENTO = (
        (1, "Sim, evitou"),
        (2, "Não, pois ainda será necessário referenciá-lo (encaminhá-lo)"),
        (3, "Não, pois não era minha intenção referenciá-lo antes da teleconsulta"),
        (4, "Não, por outros motivos"),
    )
    MUDOU_CONDUTA = (
        (1, "Sim"),
        (2, "Não, pois eu já seguia a conduta/abordagem sugerida"),
        (3, "Não, pois não concordo com a reposta"),
        (4, "Não, pois não há como seguir a conduta sugerida em nosso contexto"),
        (5, "Não, por outros motivos"),
    )
    POSSIBILIDADE_TEXTO_CHOICES = (
        (0, "Sim, pode ser plenamente respondida"),
        (1, "Sim, parcialmente"),
        (2, "Não, a dúvida necessita de teleconsulta por vídeo"),
        (3, "Não está clara qual é a dúvida"),
    )
    SIM_NAO_CHOICES = ((True, "Sim"), (False, "Não"))

    atendimento = models.ForeignKey(Atendimento, on_delete=models.PROTECT)

    satisfacao = models.IntegerField(verbose_name='Grau de Satisfação', choices=SATISFACAO)
    respondeu_duvida = models.IntegerField(verbose_name='Respondeu a Dúvida/Problema', choices=RESPONDEU_DUVIDA)
    evitou_encaminhamento = models.IntegerField(verbose_name='Evitou Encaminhamento', choices=EVITOU_ENCAMINHAMENTO)
    mudou_conduta = models.IntegerField(verbose_name='Mudou Conduta', choices=MUDOU_CONDUTA)
    recomendaria = models.BooleanField(verbose_name='Recomendaria', choices=SIM_NAO_CHOICES, default=None)
    data = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Avaliação de Solicitação"
        verbose_name_plural = "Avaliações de Solicitação"


class EncaminhamentosCondutas(models.Model):
    atendimento = models.ForeignKey(Atendimento, on_delete=models.CASCADE)
    responsavel = models.ForeignKey(ProfissionalSaude, on_delete=models.CASCADE)

    # Método SOAP - Subjetivo, Objetivo, Avaliação, Plano
    subjetivo = models.TextField(verbose_name='S - subjetivo', blank=True, null=True, help_text='Conjunto de campos que possibilita o registro da parte subjetiva da anamnese da consulta, ou seja, os dados dos sentimentos e percepções do cidadão em relação à sua saúde.')
    objetivo = models.TextField(verbose_name='O - objetivo', blank=True, null=True, help_text='Conjunto de campos que possibilita o registro do exame físico, como os sinais e sintomas detectados, além do registro de resultados de exames realizados.')
    avaliacao = models.TextField(verbose_name='A - avaliação', blank=True, null=True, help_text='Conjunto de campos que possibilita o registro da conclusão feita pelo profissional de saúde a partir dos dados observados nos itens anteriores, como os motivos para aquele encontro, a anamnese do cidadão e dos exames físico e complementares.')
    plano = models.TextField(verbose_name='P - Plano', blank=True, null=True, help_text='Conjunto de funcionalidades que permite registrar o plano de cuidado ao cidadão em relação ao(s) problema(s) avaliado(s).')

    data = models.DateTimeField(auto_now_add=True)

    comentario = models.TextField(verbose_name='Comentário', blank=True)
    encaminhamento = models.TextField(verbose_name='Encaminhamento', blank=True, null=True)
    conduta = models.TextField(verbose_name='Conduta', blank=True, null=True)

    class Meta:
        verbose_name = 'Encaminhamento e Condutas'
        verbose_name_plural = 'Encaminhamentos e Condutas'

    def __str__(self):
        return '{} - {}'.format(self.data.strftime('%d/%m/%Y %H:%M'), self.responsavel)


class DocumentoQuerySet(models.QuerySet):
    def all(self):
        return self
    
    def gerar(self, nome, conteudo):
        Documento.objects.create()


class Documento(models.Model):
    uuid = models.CharField(verbose_name='UUID')
    nome = models.CharField(verbose_name='Nome')
    data = models.DateTimeField(verbose_name='Data')
    arquivo = models.FileField(verbose_name='Arquivo', upload_to='documentos')

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'

    objects = DocumentoQuerySet()

    def __str__(self):
        return f'Documento {self.id}'
    
    def get_codigo_verificador(self):
        return str(self.id).rjust(6, '0')
    
    def get_codigo_autenticacao(self):
        return self.uuid[0:6]


class TipoExameQuerySet(models.QuerySet):
    def all(self):
        return self


class TipoExame(models.Model):
    codigo = models.CharField(verbose_name='Código', null=True)
    nome = models.CharField(verbose_name='Nome')
    detalhe = models.CharField(verbose_name='Detalhe', blank=True, null=True)
    profissional_saude = models.ForeignKey(ProfissionalSaude, verbose_name='Profissional de Saúde', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = 'Tipo de Exame'
        verbose_name_plural = 'Tipos de Exames'

    objects = TipoExameQuerySet()

    def __str__(self):
        return self.nome
    
    def formfactory(self):
        return (
            super().formfactory().fields('codigo', 'nome', 'detalhe')
        )



class MedicamentoQuerySet(models.QuerySet):
    def all(self):
        return self


class Medicamento(models.Model):
    nome = models.CharField(verbose_name='Nome')
    profissional_saude = models.ForeignKey(ProfissionalSaude, verbose_name='Profissional de Saúde', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = 'Medicamento'
        verbose_name_plural = 'Medicamentos'

    objects = MedicamentoQuerySet()

    def __str__(self):
        return self.nome
    
    def formfactory(self):
        return (
            super().formfactory().fields('nome')
        )

