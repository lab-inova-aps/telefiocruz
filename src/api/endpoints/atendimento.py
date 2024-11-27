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
        return super().get().hidden('unidade', 'especialista')
    
    def getform(self, form):
        form = super().getform(form)
        form.fields['agendado_para'] = forms.SchedulerField(scheduler=Atendimento.objects.agenda())
        if self.check_role('ps'):
            form.fields['unidade'].pick = True
        form.fields['profissional'].pick = True
        return form
        
    def on_tipo_change(self, controller, values):
        tipo = values.get('tipo')
        unidades = self.get_unidade_queryset(Unidade.objects, values)
        controller.reload('especialidade', 'profissional', 'especialista', 'agendado_para')
        if tipo and tipo.nome == 'Teleconsulta':
            controller.hide('especialista')
            if self.check_role('o'):
                controller.hide('unidade')
            else:
                if unidades.exists(): controller.show('unidade')
        else:
            controller.show('especialista')
            if unidades.exists(): controller.show('unidade')
        
    def get_unidade_queryset(self, queryset, values):
        if self.check_role('o'):
            qs = queryset.none()
            for nucleo in Nucleo.objects.filter(operadores__cpf=self.request.user.username):
                qs = qs | nucleo.unidades.all()
        elif self.check_role('ps'):
            return queryset.filter(profissionalsaude__pessoa_fisica__cpf=self.request.user.username)
        else:
            qs = queryset.none()
        return qs
    
    def get_especialidade_queryset(self, queryset, values):
        tipo = values.get('tipo')
        if tipo:
            if self.check_role('o'):
                return queryset
            elif self.check_role('ps'):
                if tipo.nome == 'Teleconsulta':
                    return queryset.filter(profissionalsaude__pessoa_fisica__cpf=self.request.user.username)
                else:
                    return queryset
        return queryset.none()
    
    def on_especialidade_change(self, controller, values):
        controller.reload('profissional', 'especialista', 'agendado_para')
        controller.set(profissional=None)

    def get_profissional_queryset(self, queryset, values):
        tipo = values.get('tipo')
        unidade = values.get('unidade')
        especialidade = values.get('especialidade')
        if self.check_role('ps'):
            queryset = queryset.filter(pessoa_fisica__cpf=self.request.user.username)
        else:
            queryset = queryset.filter(unidade=unidade) if unidade else queryset.none()
        if especialidade and tipo:
            if tipo.id == TipoAtendimento.TELECONSULTA:
                queryset = queryset.filter(especialidade=especialidade)
            return queryset
        return queryset
    
    def get_especialista_queryset(self, queryset, values):
        tipo = values.get('tipo')
        especialidade = values.get('especialidade')
        if tipo and especialidade:
            if tipo.id == TipoAtendimento.TELE_INTERCONSULTA:
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
        cadastrador = ProfissionalSaude.objects.filter(pessoa_fisica__cpf=self.request.user.username).first()
        if profissional != cadastrador:
            if not profissional.pode_realizar_atendimento(agendado_para, duracao):
                raise endpoints.ValidationError('O horário selecionado é incompatível com a duração informada.')
            if especialista and not especialista.pode_realizar_atendimento(agendado_para, duracao):
                raise endpoints.ValidationError('O horário selecionado é incompatível com a duração informada.')
        return agendado_para

    def check_permission(self):
        return self.check_role('o', 'ps')
    
    def post(self):
        return self.redirect('/api/atendimento/view/{}/'.format(self.instance.pk))


class Delete(endpoints.DeleteEndpoint[Atendimento]):
    def check_permission(self):
        return self.check_role('a')


class View(endpoints.ViewEndpoint[Atendimento]):
    def check_permission(self):
        return self.check_role('g', 'ps', 'o') or self.instance.paciente.cpf == self.request.user.username


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
            .calendar("agendado_para")
        )

    def check_permission(self):
        return self.request.user.is_authenticated


class HorariosDisponiveis(endpoints.PublicEndpoint):
    class Meta:
        verbose_name = 'Horários Disponíveis'

    def get(self):
        cadastrador = ProfissionalSaude.objects.filter(pessoa_fisica__cpf=self.request.user.username).first()
        profissional = ProfissionalSaude.objects.filter(pk=self.request.GET.get('profissional')).first()
        especialista = ProfissionalSaude.objects.filter(pk=self.request.GET.get('especialista')).first()
        is_teleconsulta = self.request.GET.get('tipo') == '1'
        is_proprio_profissional = cadastrador == profissional
        return Atendimento.objects.agenda(profissional, especialista, is_teleconsulta, is_proprio_profissional)


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
        return self.instance.finalizado_em is None and self.check_role('ps')


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
        return self.instance.finalizado_em is None and self.check_role('ps')


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
        return self.instance.finalizado_em is None and self.check_role('ps')


class RegistrarEcanminhamentosCondutas(endpoints.ChildEndpoint):
    cid = forms.ModelMultipleChoiceField(CID.objects.all(), label='CID')
    ciap = forms.ModelMultipleChoiceField(CIAP.objects.all(), label='CIAP')

    class Meta:
        icon = 'file-signature'
        verbose_name = 'Registrar Encaminhamento'

    def getform(self, form):
        if 'cid' in form.fields:
            form.fields['cid'].initial = self.source.cid.all()
            form.fields['ciap'].initial = self.source.ciap.all()
        return form

    def get(self):
        responsavel = ProfissionalSaude.objects.get(
            pessoa_fisica__cpf=self.request.user.username
        )
        instance = EncaminhamentosCondutas.objects.filter(
            atendimento=self.source, responsavel=responsavel
        ).first()
        if instance is None:
            instance = EncaminhamentosCondutas(
                atendimento=self.source, responsavel=responsavel
            )
        return (
            self.formfactory(instance)
            .initial(cid=self.source.cid.all(), ciap=self.source.ciap.all())
            .fieldset('Dados Gerais', (('cid', 'ciap'),))
            .fieldset('Método SOAP', ('subjetivo', 'objetivo', 'avaliacao', 'plano'))
            .fieldset('Outras Informações', ('comentario',))# 'encaminhamento', 'conduta'
        )
    
    def post(self):
        if self.source.iniciado_em is None:
            self.source.iniciado_em = datetime.now()
        # self.source.finalizado_em = datetime.now()
        self.source.save()
        self.source.cid.set(self.cleaned_data['cid'])
        self.source.ciap.set(self.cleaned_data['ciap'])
        self.source.criar_anexo('Atendimento', 'documentos/atendimento.html', self.source.profissional.pessoa_fisica.cpf, {})
        self.redirect(f'/api/atendimento/view/{self.source.id}/')

    def check_permission(self):
        return self.source.finalizado_em is None and self.check_role('ps')


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
            self.source.finalizado_em is None
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
        return self.source.situacao_id == SituacaoAtendimento.AGENDADO and self.request.user.username == self.source.profissional.pessoa_fisica.cpf


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
        return self.source.finalizado_em is None and self.request.user.username == self.source.profissional.pessoa_fisica.cpf and self.source.encaminhamentoscondutas_set.filter(responsavel__pessoa_fisica__cpf=self.request.user.username).exists()


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
    mensagem = forms.CharField(label='Mensagem', widget=Textarea())

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
        return self.request.user.is_superuser
