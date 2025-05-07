from datetime import datetime
from slth import endpoints
from slth import tests
from slth.components import FileViewer
from django.forms.widgets import Textarea
from ..models import Atendimento, Nucleo, TipoAtendimento, ProfissionalSaude, TipoExame, Medicamento, PessoaFisica, \
    AnexoAtendimento, EncaminhamentosCondutas, Unidade, SituacaoAtendimento, CID, CIAP, MaterialApoio
from slth import forms
from ..mail import send_mail
from django.core import signing


class Atendimentos(endpoints.ListEndpoint[Atendimento]):
    def check_permission(self):
        return self.check_role('a', 'g')
    
    def get(self):
        return super().get().xlsx('tipo', 'paciente__cpf', 'paciente__nome', 'profissional', 'especialista', 'especialidade', 'agendado_para', 'assunto')
    
    def contribute(self, entrypoint):
        if entrypoint == 'menu':
            return not self.check_role('g', superuser=False)
        return super().contribute(entrypoint)


class Proximos(endpoints.QuerySetEndpoint[Atendimento]):

    class Meta:
        icon = "laptop-file"
        verbose_name = 'Próximos Atendimentos'
    
    def get(self):
        return super().get().all().proximos().actions('atendimento.convidartestedispositivo', 'atendimento.confirmartestedispositivo', 'atendimento.solicitarconfirmacaopresenca', 'atendimento.confirmarpresenca', 'atendimento.cancelaratendimento').calendar("agendado_para")

    def check_permission(self):
        return self.check_role('ag')


class AguardandoTesteDispositivo(Proximos):

    class Meta:
        icon = 'mobile-screen'
        verbose_name = 'Aguardando Teste de Dispositivo'
    
    def get(self):
        return super().get().filter(paciente__data_hora_teste_dispositivo__isnull=True)
    

class AguardandoConfirmacao(Proximos):

    class Meta:
        icon = 'person-circle-check'
        verbose_name = 'Aguardando Confirmação'
    
    def get(self):
        return super().get().filter(data_hora_confirmacao__isnull=True)


class ConvidarTesteDispositivo(endpoints.InstanceEndpoint[Atendimento]):
    mensagem = forms.CharField(label='Mensagem', widget=forms.Textarea())
    class Meta:
        icon = 'mobile-screen'
        verbose_name = 'Convidar para Teste de Dispositivo'
        modal = True

    def getform(self, form):
        if form and 'mensagem' in form.fields:
            form.fields['mensagem'].help_text = self.instance.paciente.get_url_sala_teste_dispositivo()
        return form

    def get(self):
        return (
            self.formfactory(self.instance.paciente).fields('mensagem').initial(mensagem=self.instance.get_mensagem_whatsapp_teste_dispositvo())
        )
    
    def post(self):
        self.instance.notificar_paciente(self.cleaned_data['mensagem'])
        return super().post()
    
    def check_permission(self):
        return self.check_role('ag') and self.instance.is_agendado()


class ConfirmarTesteDispositivo(endpoints.InstanceEndpoint[Atendimento]):
    class Meta:
        icon = 'check'
        verbose_name = 'Confirmar Teste de Dispositivo'
        modal = True

    def get(self):
        return (self.formfactory(self.instance.paciente).fields('data_hora_teste_dispositivo', 'evidencia_teste_dispositivo').initial(data_hora_teste_dispositivo=datetime.now()))

    def check_permission(self):
        return self.check_role('ag') and self.instance.is_agendado()

class SolicitarConfirmacaoPresenca(endpoints.InstanceEndpoint[Atendimento]):
    mensagem = forms.CharField(label='Mensagem', widget=forms.Textarea())
    
    class Meta:
        icon = 'person-circle-check'
        verbose_name = 'Solicitar Confirmação de Presença'
        modal = True

    def get(self):
        return (self.formfactory(self.instance.paciente).fields('mensagem').initial(mensagem=self.instance.get_mensagem_whatsapp_confirmacao_atendimento()))
    
    def post(self):
        self.instance.notificar_paciente(self.cleaned_data['mensagem'])
        return super().post()
    
    def check_permission(self):
        return self.check_role('ag') and self.instance.is_agendado()


class ConfirmarPresenca(endpoints.InstanceEndpoint[Atendimento]):
    class Meta:
        icon = 'check-double'
        verbose_name = 'Confirmar Presença'
        modal = True

    def get(self):
        return (self.formfactory().fields('data_hora_confirmacao').initial(data_hora_confirmacao=datetime.now()))
    
    def check_permission(self):
        return self.check_role('ag') and self.instance.is_agendado()
    

class Add(endpoints.AddEndpoint[Atendimento]):

    class Meta:
        icon = 'plus'
        modal = False
        verbose_name = 'Cadastrar Atendimento'

    def get(self):
        return super().get().hidden('especialista')
    
    def getform(self, form):
        form = super().getform(form)
        form.fields['agendado_para'] = forms.SchedulerField(label="Data/Hora", scheduler=Atendimento.objects.agenda())
        form.fields['profissional'].pick = True
        return form
        
    def on_tipo_change(self, tipo):
        self.form.controller.reload('especialidade', 'profissional', 'especialista', 'agendado_para')
        if tipo and tipo.is_teleconsulta():
            self.form.controller.hide('especialista')
        else:
            self.form.controller.show('especialista')

    def get_especialidade_queryset(self, queryset):
        tipo = self.form.controller.get('tipo')
        if tipo:
            if self.check_role('o'):
                return queryset
            elif self.check_role('ps'):
                if tipo.is_teleconsulta():
                    vinculos = ProfissionalSaude.objects.filter(pessoa_fisica__cpf=self.request.user.username).filter(ativo=True)
                    return queryset.filter(pk__in=vinculos.values_list('especialidade', flat=True).distinct())
                else:
                    pks = ProfissionalSaude.objects.filter(nucleo__isnull=False).values_list('especialidade', flat=True).filter(ativo=True).distinct()
                    return queryset.filter(pk__in=pks)
        return queryset.none()
    
    def on_especialidade_change(self, especialidade):
        self.form.controller.reload('profissional', 'especialista', 'agendado_para')
        self.form.controller.set(profissional=None)

    def get_profissional_queryset(self, queryset):
        tipo = self.form.controller.get('tipo')
        especialidade = self.form.controller.get('especialidade')
        if self.check_role('ps'):
            queryset = queryset.filter(pessoa_fisica__cpf=self.request.user.username)
        if especialidade and tipo and tipo.is_teleconsulta():
            queryset = queryset.filter(especialidade=especialidade)
        return queryset.filter(ativo=True)
    
    def get_especialista_queryset(self, queryset):
        tipo = self.form.controller.get('tipo')
        especialidade = self.form.controller.get('especialidade')
        if tipo and especialidade:
            if tipo.is_teleinterconsulta():
                queryset = queryset.filter(nucleo__isnull=False, especialidade=especialidade)
            return queryset
        return queryset.none()
    
    def on_profissional_change(self, profissional):
        self.form.controller.reload('agendado_para')
    
    def on_especialista_change(self, especialista):
        self.form.controller.reload('agendado_para')

    def clean_agendado_para(self, cleaned_data):
        duracao = cleaned_data.get('duracao')
        agendado_para = cleaned_data.get('agendado_para')
        profissional = cleaned_data.get('profissional')
        especialista = cleaned_data.get('especialista')
        if profissional and not profissional.is_user(self.request.user):
            if not profissional.pode_realizar_atendimento(agendado_para, duracao):
                raise endpoints.ValidationError('O horário selecionado é incompatível com a duração informada.')
            if especialista and not especialista.pode_realizar_atendimento(agendado_para, duracao):
                raise endpoints.ValidationError('O horário selecionado é incompatível com a duração informada.')
        return agendado_para

    def check_permission(self):
        return self.check_role('o', 'ps')
    
    def post(self):
        self.instance.enviar_notificacao(mensagem="Atendimento agendado. Leia atentamente as informações abaixo e acesse o link no dia/hora marcados.")
        self.instance.agendar_notificacao()
        return self.redirect('/api/atendimento/view/{}/'.format(self.instance.pk))


class Delete(endpoints.DeleteEndpoint[Atendimento]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[Atendimento]):

    def check_permission(self):
        return self.check_role('g', 'o', 's') or self.instance.is_envolvido(self.request.user)


class Agenda(endpoints.QuerySetEndpoint[Atendimento]):
    
    class Meta:
        modal = False
        icon = 'calendar-days'
        verbose_name= 'Agenda de Atendimentos'
    
    def get(self):
        return (
            super().get().all().actions('atendimento.add', 'atendimento.view')
            .lookup('g', profissional__nucleo__gestores__cpf='username')
            .lookup('o', unidade__nucleo__operadores__cpf='username')
            .lookup('ou', unidade__operadores__cpf='username')
            .lookup('ps', profissional__pessoa_fisica__cpf='username', especialista__pessoa_fisica__cpf='username')
            .lookup('p', paciente__cpf='username')
            .lookup('s')
            .calendar("agendado_para")
        )

    def check_permission(self):
        return super().check_role('g', 'o', 'ou', 'ps', 'p', 's')


class HorariosDisponiveis(endpoints.PublicEndpoint):
    class Meta:
        verbose_name = 'Horários Disponíveis'

    def get(self):
        profissional = ProfissionalSaude.objects.filter(pk=self.request.GET.get('profissional')).first()
        especialista = ProfissionalSaude.objects.filter(pk=self.request.GET.get('especialista')).first()
        is_teleconsulta = self.request.GET.get('tipo') == '1'
        is_proprio_profissional = profissional and profissional.is_user(self.request.user)
        return Atendimento.objects.agenda(profissional, especialista, is_teleconsulta, is_proprio_profissional, int(self.request.GET.get('week', 1)))


class EmitirAtestado(endpoints.InstanceEndpoint[Atendimento]):
    quantidade_dias = forms.IntegerField(label='Quantidade de Dias')
    informar_endereco = forms.BooleanField(label='Informar Endereço', required=False)
    informar_cid = forms.BooleanField(label='Informar CID', required=False)

    
    class Meta:
        icon = 'file-medical'
        modal = True
        verbose_name = 'Emitir Atestado'

    def get(self):
        return self.formfactory().fields(
            'quantidade_dias', ('informar_endereco', 'informar_cid')
        ).initial(informar_endereco=False, informar_cid=False)
    
    def post(self):
        dados = dict(
            quantidade_dias=self.cleaned_data['quantidade_dias'],
            informar_endereco=self.cleaned_data['informar_endereco'],
            informar_cid=self.cleaned_data['informar_cid'],
            profissional=ProfissionalSaude.objects.get(pessoa_fisica__cpf=self.request.user.username)
        )
        self.instance.criar_anexo('Atestado Médico', 'documentos/atestado.html', self.request.user.username, dados)
        return super().post()
    
    def check_permission(self):
        return self.instance.is_agendado() and self.check_role('ps') and self.instance.is_envolvido(self.request.user)


class SolicitarExames(endpoints.InstanceEndpoint[Atendimento]):
    tipos = forms.ModelMultipleChoiceField(TipoExame.objects)
    
    class Meta:
        icon = 'file-waveform'
        modal = True
        verbose_name = 'Solicitar Exames'

    def get(self):
        return self.formfactory().fields('tipos:tipoexame.add')
    
    def post(self):
        dados = dict(
            tipos=self.cleaned_data['tipos'],
            profissional=ProfissionalSaude.objects.get(pessoa_fisica__cpf=self.request.user.username)
        )
        self.instance.criar_anexo('Solicitação de Exame', 'documentos/exames.html', self.request.user.username, dados)
        return super().post()
    
    def check_permission(self):
        return self.instance.is_agendado() and self.check_role('ps') and self.instance.is_envolvido(self.request.user)


class VisualizarProntuarioPaciente(endpoints.InstanceEndpoint[Atendimento]):
    class Meta:
        modal = True
        icon = 'history'
        verbose_name = 'Prontuário do Paciente'

    def get(self):
        if self.request.GET.get('view'):
            return self.render(dict(obj=self.instance.paciente), "prontuario.html", pdf=True)
        else:
            return FileViewer(f'/api/pessoafisica/prontuariopaciente/{self.instance.paciente.pk}/?view={signing.dumps(self.instance.pk)}')

    def check_permission(self):
        return self.check_role('ps') or (self.request.GET.get('view') and signing.loads(self.request.GET.get('view')) == self.instance.pk)


class PrescreverMedicamento(endpoints.InstanceEndpoint[Atendimento]):
    
    class Meta:
        icon = 'file-signature'
        modal = True
        verbose_name = 'Prescrever'

    def getform(self, form):
        form = super().getform(form)
        for i in range(0, 10):
            form.fields[f'medicamento_{i}'] = forms.ModelChoiceField(Medicamento.objects, label=None if i else 'Medicamento', required=False)
            form.fields[f'orientacao_{i}'] = forms.CharField(label=None if i else 'Orientação', required=False)
        return form

    def get(self):
        return self.formfactory().fields(
            *[(f'medicamento_{i}' if i else f'medicamento_{i}:medicamento.add', f'orientacao_{i}') for i in range(0, 5)]
        )
    
    def post(self):
        dados = dict(medicamentos=[(self.cleaned_data[f'medicamento_{i}'], self.cleaned_data[f'orientacao_{i}']) for i in range(0, 10)])
        dados.update(profissional=ProfissionalSaude.objects.get(pessoa_fisica__cpf=self.request.user.username))
        self.instance.criar_anexo('Prescrição Médica', 'documentos/prescricao.html', self.request.user.username, dados)
        return super().post()
    
    def check_permission(self):
        return self.instance.is_agendado() and self.check_role('ps') and self.instance.is_envolvido(self.request.user)


class RegistrarEcanminhamentosCondutas(endpoints.InstanceEndpoint[Atendimento]):
    cid = forms.ModelMultipleChoiceField(CID.objects.all(), label='CID', required=False)
    ciap = forms.ModelMultipleChoiceField(CIAP.objects.all(), label='CIAP', required=False)

    class Meta:
        icon = 'file-export'
        verbose_name = 'Registrar Encaminhamento'

    def getform(self, form):
        if 'cid' in form.fields:
            form.fields['cid'].initial = self.instance.cid.all()
            form.fields['ciap'].initial = self.instance.ciap.all()
            ultimo_encaminhamento = EncaminhamentosCondutas.objects.filter(
            atendimento__paciente=self.instance.paciente, responsavel=self.get_responsavel()
            ).exclude(atendimento=self.instance).order_by('-data').first()
            if ultimo_encaminhamento:
                data_hora = ultimo_encaminhamento.data.strftime("%d/%m/%Y %H:%M")
                form.fields['subjetivo'].help_text = f"{data_hora}: {ultimo_encaminhamento.subjetivo}"
                form.fields['objetivo'].help_text = f"{data_hora}: {ultimo_encaminhamento.objetivo}"
                form.fields['avaliacao'].help_text = f"{data_hora}: {ultimo_encaminhamento.avaliacao}"
                form.fields['plano'].help_text = f"{data_hora}: {ultimo_encaminhamento.plano}"
        return form
    
    def get_responsavel(self):
        return self.instance.profissional if self.instance.profissional.is_user(self.request.user) else self.instance.especialista

    def get(self):
        responsavel = self.get_responsavel()
        instance = EncaminhamentosCondutas.objects.filter(
            atendimento=self.instance, responsavel=responsavel
        ).first()
        if instance is None:
            instance = EncaminhamentosCondutas(
                atendimento=self.instance, responsavel=responsavel
            )
        return (
            self.formfactory(instance).autosubmit(30)
            .initial(cid=self.instance.cid.all(), ciap=self.instance.ciap.all())
            .fieldset('Dados Gerais', (('cid', 'ciap'),))
            .fieldset('Método SOAP', ('subjetivo', 'objetivo', 'avaliacao', 'plano'))
            .fieldset('Outras Informações', ('comentario',))# 'encaminhamento', 'conduta'
            .info('Os dados registrados abaixo serão salvos automaticamente a cada minuto. Clique no botão "Enviar" apenas quando concluir a video-chamada e quiser retornar para a página de visualização do atendimento.' if "/registrarecanminhamentoscondutas/" not in self.request.path else None)
        )
    
    def post(self):
        if self.instance.iniciado_em is None:
            self.instance.iniciado_em = datetime.now()
        # self.source.finalizado_em = datetime.now()
        self.instance.save()
        self.instance.cid.set(self.cleaned_data['cid'])
        self.instance.ciap.set(self.cleaned_data['ciap'])
        if self.request.GET.get('autosubmit') is None:
            self.instance.criar_anexo('Atendimento', 'documentos/atendimento.html', self.instance.profissional.pessoa_fisica.cpf, {})
        self.redirect(f'/api/atendimento/view/{self.instance.id}/')

    def check_permission(self):
        return self.instance.is_agendado() and self.check_role('ps') and self.instance.is_envolvido(self.request.user)


class AnexarArquivo(endpoints.ChildEndpoint):
    class Meta:
        icon = 'upload'
        verbose_name = 'Anexar Arquivo'

    def get(self):
        autor = PessoaFisica.objects.filter(cpf=self.request.user.username).first() or self.source.paciente
        instance = AnexoAtendimento(atendimento=self.source, autor=autor)
        return self.formfactory(instance).fields('nome', 'arquivo')
    
    def check_permission(self):
        return (
            self.source.is_agendado()
            and (
                self.request.GET.get('token') == self.source.token
                or self.source.is_envolvido(self.request.user)
            )
        )


class CancelarAtendimento(endpoints.InstanceEndpoint[Atendimento]):
    class Meta:
        icon = 'x'
        verbose_name = 'Cancelar Atendimento'

    def get(self):
        return self.formfactory(self.instance).fields('motivo_cancelamento')
    
    def post(self):
        self.instance.cancelar()
        return super().post()
    
    def check_permission(self):
        return (self.instance.is_agendado() and not self.instance.get_condutas_ecaminhamentos().exists()) and (self.request.user.username == self.instance.profissional.pessoa_fisica.cpf or self.check_role('ag'))


class ReagendarAtendimento(endpoints.ChildEndpoint):
    data_hora = forms.DateTimeField(label='Data/Hora')
    class Meta:
        icon = 'calendar'
        verbose_name = 'Reagendar Atendimento'

    def getform(self, form):
        form = super().getform(form)
        is_proprio_profissional = self.source.profissional.is_user(self.request.user)
        scheduler = Atendimento.objects.agenda(self.source.profissional, self.source.especialista, self.source.tipo.is_teleconsulta(), is_proprio_profissional)
        form.fields['data_hora'] = forms.SchedulerField(scheduler=scheduler)
        return form

    def get(self):
        return self.formfactory(self.source).info("Ao submeter o formulário, o sistema redirecionará para o novo atendimento agendado.").fieldset(None, fields=('tipo', 'profissional', 'especialista', 'motivo_reagendamento', 'data_hora')).hidden('tipo', 'profissional', 'especialista')
    
    def post(self):
        instance = self.source.reagendar(self.cleaned_data['data_hora'])
        return self.redirect('/api/atendimento/view/{}/'.format(instance.pk))
    
    def check_permission(self):
        return self.source.is_agendado() and not self.source.get_condutas_ecaminhamentos().exists() and self.request.user.username == self.source.profissional.pessoa_fisica.cpf


class RetornoAtendimento(endpoints.ChildEndpoint):
    data_hora = forms.DateTimeField(label='Data/Hora')
    
    class Meta:
        icon = 'calendar-plus'
        verbose_name = 'Agendar Retorno'

    def getform(self, form):
        form = super().getform(form)
        is_proprio_profissional = self.source.profissional.is_user(self.request.user)
        scheduler = Atendimento.objects.agenda(self.source.profissional, self.source.especialista, self.source.tipo.is_teleconsulta(), is_proprio_profissional)
        form.fields['data_hora'] = forms.SchedulerField(scheduler=scheduler)
        return form

    def get(self):
        return self.formfactory(self.source).info("Ao submeter o formulário, o sistema redirecionará para o novo atendimento agendado.").fieldset(None, fields=('tipo', 'profissional', 'especialista', 'data_hora')).hidden('tipo', 'profissional', 'especialista')
    
    def post(self):
        instance = self.source.retorno(self.cleaned_data['data_hora'])
        return self.redirect('/api/atendimento/view/{}/'.format(instance.pk))
    
    def check_permission(self):
        return self.request.user.username == self.source.profissional.pessoa_fisica.cpf


class FinalizarAtendimento(endpoints.ChildEndpoint):
    tipo_assinatura = forms.ChoiceField(label='Forma de autorização da assinatura digital', choices=[['QrCode', 'QrCode'], ['Notificação', 'Notificação']], pick=True, required=False)

    class Meta:
        icon = 'check'
        verbose_name = 'Finalizar Atendimento'

    def get(self):
        return (
            self.formfactory(self.source)
            .info('Caso não deseje assinar digitalmente os documentos com o aplicativo VIDAAS, apenas clique no botão "Enviar".')
            .image('/static/images/signature.png')
            .fields('tipo_assinatura', finalizado_em=datetime.now())
        )
    
    def post(self):
        super().post()
        tipo_assinatura = self.cleaned_data['tipo_assinatura']
        if tipo_assinatura == 'QrCode':
            self.redirect(f'/api/assinarviaqrcode/{self.source.id}/')
        elif tipo_assinatura == 'Notificação':
            if tests.RUNNING_TESTING:
                self.redirect(f'/api/atendimento/view/{self.source.id}/')
            else:
                self.source.finalizar()
                self.redirect(f'/api/atendimento/view/{self.source.id}/')
        else:
            self.source.finalizar()
            self.redirect(f'/api/atendimento/view/{self.source.id}/')

    def check_permission(self):
        return self.source.is_agendado() and self.request.user.username == self.source.profissional.pessoa_fisica.cpf and self.source.encaminhamentoscondutas_set.filter(responsavel__pessoa_fisica__cpf=self.request.user.username).exists()


class Publico(endpoints.PublicEndpoint):
    
    class Meta:
        modal = False
        verbose_name = "Público"
        submit_label = 'Aceitar termo e iniciar'
        submit_icon = 'thumbs-up'

    def get(self):
        atendimento = Atendimento.objects.filter(token=self.request.GET.get('token')).order_by('id').last()
        return self.formfactory(atendimento).fields().display(None, ('get_termo_consentimento_digital',))
   
    def post(self):
        atendimento = Atendimento.objects.get(token=self.request.GET.get('token'))
        if atendimento.finalizado_em:
            raise endpoints.ValidationError('Atendimento finalizado.')
        if not atendimento.get_anexos().filter(nome='Termo de Consentimento').exists():
            atendimento.criar_anexo('Termo de Consentimento', 'documentos/termo.html', atendimento.paciente.cpf, {})
        if atendimento.profissional.url_webconf:
            self.redirect(atendimento.profissional.url_webconf)
        else:
            self.redirect('/api/salaespera/?token={}'.format(self.request.GET.get('token')))


class Confirmacao(endpoints.PublicEndpoint):
    class Meta:
        verbose_name = 'Confirmação de Atendimento'

    def get(self):
        atendimento = Atendimento.objects.filter(token=self.request.GET.get('token')).order_by('id').last()
        atendimento.data_hora_confirmacao = datetime.now()
        atendimento.save()
        return self.render(dict(atendimento=atendimento))


class EnviarNotificacao(endpoints.ChildEndpoint):
    mensagem = forms.CharField(label='Mensagem', widget=Textarea(), initial='Atendimento confirmado. Não esqueça de acessar a plataforma no horário marcado.')

    class Meta:
        modal = True
        icon = 'mail-bulk'
        verbose_name = 'Enviar Notificação'

    def get(self):
        return self.formfactory().fields("mensagem")
    
    def post(self):
        self.source.enviar_notificacao(self.cleaned_data['mensagem'])
        return super().post()
    
    def check_permission(self):
        return self.source.is_agendado() and self.check_role('ps') and self.source.is_envolvido(self.request.user)


class InformarMateriaisApoio(endpoints.InstanceEndpoint[Atendimento]):

    class Meta:
        icon = 'file'
        verbose_name = 'Informar Materiais de Apoio'

    def get(self):
        return self.formfactory().fields('materiais_apoio')
    
    def get_materiais_apoio_queryset(self, queryset):
        return queryset.filter(pessoa_fisica__cpf=self.request.user.username)
    
    def check_permission(self):
        return self.instance.is_agendado() and self.check_role('ps') and self.instance.especialista and self.instance.especialista.pessoa_fisica.cpf == self.request.user.username

