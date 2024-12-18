from datetime import datetime
from slth import endpoints
from slth import tests
from django.forms.widgets import Textarea
from ..models import Atendimento, Nucleo, TipoAtendimento, ProfissionalSaude, TipoExame, Medicamento, PessoaFisica, \
    AnexoAtendimento, EncaminhamentosCondutas, Unidade, SituacaoAtendimento, CID, CIAP
from slth import forms
from ..mail import send_mail


class Atendimentos(endpoints.ListEndpoint[Atendimento]):
    def check_permission(self):
        return self.check_role('a', 'g')
    
    def contribute(self, entrypoint):
        if entrypoint == 'menu':
            return not self.check_role('g', superuser=False)
        return super().contribute(entrypoint)


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
        
    def on_tipo_change(self, controller, values):
        tipo = values.get('tipo')
        controller.reload('especialidade', 'profissional', 'especialista', 'agendado_para')
        if tipo and tipo.is_teleconsulta():
            controller.hide('especialista')
        else:
            controller.show('especialista')

    def get_especialidade_queryset(self, queryset, values):
        tipo = values.get('tipo')
        if tipo:
            if self.check_role('o'):
                return queryset
            elif self.check_role('ps'):
                if tipo.is_teleconsulta():
                    vinculos = ProfissionalSaude.objects.filter(pessoa_fisica__cpf=self.request.user.username)
                    return queryset.filter(pk__in=vinculos.values_list('especialidade', flat=True).distinct())
                else:
                    pks = ProfissionalSaude.objects.filter(nucleo__isnull=False).values_list('especialidade', flat=True).distinct()
                    return queryset.filter(pk__in=pks)
        return queryset.none()
    
    def on_especialidade_change(self, controller, values):
        controller.reload('profissional', 'especialista', 'agendado_para')
        controller.set(profissional=None)

    def get_profissional_queryset(self, queryset, values):
        tipo = values.get('tipo')
        especialidade = values.get('especialidade')
        if self.check_role('ps'):
            queryset = queryset.filter(pessoa_fisica__cpf=self.request.user.username)
        if especialidade and tipo and tipo.is_teleconsulta():
            queryset = queryset.filter(especialidade=especialidade)
        return queryset
    
    def get_especialista_queryset(self, queryset, values):
        tipo = values.get('tipo')
        especialidade = values.get('especialidade')
        if tipo and especialidade:
            if tipo.is_teleinterconsulta():
                queryset = queryset.filter(nucleo__isnull=False, especialidade=especialidade)
            return queryset
        return queryset.none()
    
    def on_profissional_change(self, controller, values):
        controller.reload('agendado_para')
    
    def on_especialista_change(self, controller, values):
        controller.reload('agendado_para')

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
        return self.redirect('/api/atendimento/view/{}/'.format(self.instance.pk))


class Delete(endpoints.DeleteEndpoint[Atendimento]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[Atendimento]):

    def check_permission(self):
        return self.check_role('g', 'ps', 'o', 's') or self.instance.paciente.cpf == self.request.user.username


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
        return self.request.user.is_authenticated


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
        icon = 'file'
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
        )
        self.instance.criar_anexo('Atestado Médico', 'documentos/atestado.html', self.request.user.username, dados)
        return super().post()
    
    def check_permission(self):
        return self.instance.is_agendado() and self.check_role('ps')


class SolicitarExames(endpoints.InstanceEndpoint[Atendimento]):
    tipos = forms.ModelMultipleChoiceField(TipoExame.objects)
    
    class Meta:
        icon = 'file'
        modal = True
        verbose_name = 'Solicitar Exames'

    def get(self):
        return self.formfactory().fields('tipos:tipoexame.add')
    
    def post(self):
        dados = dict(tipos=self.cleaned_data['tipos'])
        self.instance.criar_anexo('Solicitação de Exame', 'documentos/exames.html', self.request.user.username, dados)
        return super().post()
    
    def check_permission(self):
        return self.instance.is_agendado() and self.check_role('ps')


class PrescreverMedicamento(endpoints.InstanceEndpoint[Atendimento]):
    
    class Meta:
        icon = 'file'
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
        self.instance.criar_anexo('Prescrição Médica', 'documentos/prescricao.html', self.request.user.username, dados)
        return super().post()
    
    def check_permission(self):
        return self.instance.is_agendado() and self.check_role('ps')


class RegistrarEcanminhamentosCondutas(endpoints.InstanceEndpoint[Atendimento]):
    cid = forms.ModelMultipleChoiceField(CID.objects.all(), label='CID', required=False)
    ciap = forms.ModelMultipleChoiceField(CIAP.objects.all(), label='CIAP', required=False)

    class Meta:
        icon = 'file-signature'
        verbose_name = 'Registrar Encaminhamento'

    def getform(self, form):
        if 'cid' in form.fields:
            form.fields['cid'].initial = self.instance.cid.all()
            form.fields['ciap'].initial = self.instance.ciap.all()
        return form

    def get(self):
        responsavel = self.instance.profissional if self.instance.profissional.is_user(self.request.user) else self.instance.especialista
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
        return self.instance.is_agendado() and self.check_role('ps')


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
                or self.request.user.username == self.source.paciente.cpf
                or self.request.user.username == self.source.profissional.pessoa_fisica.cpf
                or self.source.especialista and self.request.user.username == self.source.especialista.pessoa_fisica.cpf
            )
        )


class CancelarAtendimento(endpoints.ChildEndpoint):
    class Meta:
        icon = 'x'
        verbose_name = 'Cancelar Atendimento'

    def get(self):
        return self.formfactory(self.source).fields('motivo_cancelamento')
    
    def post(self):
        self.source.cancelar()
        return super().post()
    
    def check_permission(self):
        return self.source.is_agendado() and not self.source.get_condutas_ecaminhamentos().exists() and self.request.user.username == self.source.profissional.pessoa_fisica.cpf


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
        return self.formfactory(self.source).fieldset(None, fields=('motivo_reagendamento', 'data_hora'))
    
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
        return self.formfactory(self.source).fields('data_hora')
    
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
        return self.formfactory(self.source).image('/static/images/signature.png').fields('tipo_assinatura', finalizado_em=datetime.now())
    
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
    concordo = forms.BooleanField(label='Concordo e aceito os termo acima apresentados')
    
    class Meta:
        modal = False
        verbose_name = None

    def get(self):
        atendimento = Atendimento.objects.get(token=self.request.GET.get('token'))
        return self.formfactory(atendimento).fields('concordo').display(None, ('get_termo_consentimento_digital',))
   
    def post(self):
        atendimento = Atendimento.objects.get(token=self.request.GET.get('token'))
        if atendimento.finalizado_em:
            raise endpoints.ValidationError('Atendimento finalizado.')
        if not atendimento.get_anexos().filter(nome='Termo de Consentimento').exists():
            atendimento.criar_anexo('Termo de Consentimento', 'documentos/termo.html', atendimento.paciente.cpf, {})
        self.redirect('/api/salaespera/?token={}'.format(self.request.GET.get('token')))


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
        return self.source.is_agendado() and self.check_role('ps')
