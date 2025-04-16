from slth import endpoints
from slth import forms
from slth import components
from ..models import ProfissionalSaude, HorarioProfissionalSaude, Atendimento


class ProfissionaisSaude(endpoints.ListEndpoint[ProfissionalSaude]):
    def check_permission(self):
        return self.check_role('o', 'a', 'ou')
    
    def contribute(self, entrypoint):
        if entrypoint == 'menu':
            return not self.check_role('o', 'ou', superuser=False)
        return super().contribute(entrypoint)


class View(endpoints.ViewEndpoint[ProfissionalSaude]):
    def check_permission(self):
        return self.check_role()


class Edit(endpoints.EditEndpoint[ProfissionalSaude]):
    def check_permission(self):
        return self.check_role()


class Agenda(endpoints.InstanceEndpoint[ProfissionalSaude]):
    class Meta:
        icon = 'calendar-days'
        verbose_name = 'Visualizar Agenda'
    
    def get(self):
        return self.serializer().fieldset(
            "Dados do Profissional",
            ("pessoa_fisica", ("nucleo", "especialidade")),
        ).fieldset('Agenda', ('get_agenda',))
    
    def check_permission(self):
        return True


class Especialistas(endpoints.Endpoint):

    class Meta:
        icon = 'stethoscope'
        verbose_name = 'Especialistas'

    def get(self):
        return ProfissionalSaude.objects.filter(nucleo__isnull=False).fields('pessoa_fisica__nome', 'registro_profissional', 'especialidade', 'nucleo').actions('profissionalsaude.agenda')

    def check_permission(self):
        return self.check_role('ps', 's')


class AlterarAgenda(endpoints.InstanceEndpoint[ProfissionalSaude]):

    class Meta:
        icon = "calendar-plus"
        verbose_name = "Alterar Agenda"

    def get(self):
        if 'week' in self.request.GET:
            return self.get_agenda()
        else:
            return self.formfactory().display("Dados do Profissional", (("pessoa_fisica", "especialidade"),),).fields()

    def getform(self, form):
        form.fields["horarios"] = forms.SchedulerField(scheduler=self.get_agenda())
        return form
    
    def get_agenda(self):
        return self.instance.get_agenda(
            readonly=False, semana=int(self.request.GET.get('week', 1)), url=self.request.path
        )

    def post(self):
        for data_hora in self.cleaned_data["horarios"]["select"]:
            HorarioProfissionalSaude.objects.create(data_hora=data_hora, profissional_saude=self.instance)
        for data_hora in self.cleaned_data["horarios"]["deselect"]:
            HorarioProfissionalSaude.objects.filter(data_hora=data_hora, profissional_saude=self.instance).delete()
        return super().post()
    
    def check_permission(self):
        return self.check_role('g', 'o', 'ou')#  or self.instance.pessoa_fisica.cpf == self.request.user.username


class DefinirHorario(endpoints.InstanceEndpoint[ProfissionalSaude]):
    inicio = forms.DateField(label='Início', required=True)
    fim = forms.DateField(label='Fim', required=True)
    horarios = forms.SchedulerField(label='Dia/Horário', scheduler=components.Scheduler(weekly=True, chucks=3))

    class Meta:
        icon = "user-clock"
        verbose_name = "Definir Horários"

    def getform(self, form):
        form.fields['horarios'] = forms.SchedulerField(label='Dia/Horário', scheduler=self.instance.get_horarios_atendimento(False))
        return super().getform(form)

    def get(self):
        return self.formfactory().fields(('inicio', 'fim'), 'horarios')
    
    def post(self):
        inicio = self.cleaned_data['inicio']
        fim = self.cleaned_data['fim']
        self.instance.atualizar_horarios_atendimento(inicio, fim, self.cleaned_data['horarios']['select'], self.cleaned_data['horarios']['deselect'])
        return super().post()
    
    def check_permission(self):
        return self.check_role('g', 'o', 'ou')


class DefinirHorarios(endpoints.Endpoint):
    inicio = forms.DateField(label='Início', required=False)
    fim = forms.DateField(label='Fim', required=False)
    profissionais = forms.ModelMultipleChoiceField(ProfissionalSaude.objects, label='Profissionais de Saúde')
    horarios = forms.SchedulerField(label='Dia/Horário', scheduler=components.Scheduler(weekly=True, chucks=3))

    class Meta:
        icon = "user-clock"
        verbose_name = "Definir Horários de Atendimento"

    def get(self):
        return self.formfactory().fields(('inicio', 'fim'), 'profissionais', 'horarios')
    
    def post(self):
        inicio = self.cleaned_data['inicio']
        fim = self.cleaned_data['fim']
        for profissional_saude in self.cleaned_data['profissionais']:
            profissional_saude.atualizar_horarios_atendimento(inicio, fim, self.cleaned_data['horarios']['select'], self.cleaned_data['horarios']['deselect'])
        return super().post()


class AtendimentosDoDia(endpoints.QuerySetEndpoint[Atendimento]):
    class Meta:
        verbose_name= 'Atendimentos do Dia'

    def get(self):
        return super().get().do_dia().fields('get_numero', 'tipo', 'paciente', 'get_situacao', 'get_agendado_para').actions('atendimento.view').lookup('ps', profissional__pessoa_fisica__cpf='username', especialista__pessoa_fisica__cpf='username')
    
    def check_permission(self):
        return self.check_role('ps', superuser=False)
    

class Vinculos(endpoints.ListEndpoint[ProfissionalSaude]):
    
    class Meta:
        verbose_name= 'Meus Vínculos'
    
    def get(self):
        vinculos = super().get().search().filters().filter(pessoa_fisica__cpf=self.request.user).fields('get_estabelecimento', 'especialidade', 'ativo').actions("profissionalsaude.alteraragenda", "profissionalsaude.horariosatendimento")
        vinculos.metadata['search'].clear()
        return vinculos

    def check_permission(self):
        return self.check_role('ps', superuser=False)


class HorariosAtendimento(endpoints.ViewEndpoint[ProfissionalSaude]):
    class Meta:
        modal = True
        icon = "user-clock"
        verbose_name = 'Horários de Atendimento'

    def get(self):
        return self.instance.get_horarios_atendimento()

    def check_permission(self):
        return True


class MinhaAgenda(endpoints.Endpoint):
    class Meta:
        icon = 'calendar-days'
        verbose_name = 'Minha Agenda'

    def get(self):
        return ProfissionalSaude.objects.filter(pessoa_fisica__cpf=self.request.user.username).first().get_agenda(
            semana=int(self.request.GET.get('week', 1)), url=self.base_url
        )
    
    def check_permission(self):
        return self.check_role('ps', superuser=False)


class PrimeiroAcesso(endpoints.PublicEndpoint):
    cpf = forms.CharField(label='CPF')
    data_nascimento = forms.DateField(label='Data de Nascimento')
    email = forms.CharField(label='Email')

    class Meta:
        icon = 'user-md'
        verbose_name = 'Primeiro Acesso'

    def get(self):
        texto = 'Será enviada para o e-mail cadastrado uma nova senha, a qual poderá ser trocada após login no sistema.'
        return self.formfactory().info(texto).fields(('cpf', 'data_nascimento'), 'email')
    
    def post(self):
        profissional_saude = ProfissionalSaude.objects.filter(
            pessoa_fisica__cpf=self.cleaned_data['cpf'],
            pessoa_fisica__data_nascimento=self.cleaned_data['data_nascimento'],
            pessoa_fisica__email=self.cleaned_data['email']
        ).first()
        if profissional_saude is None:
            raise endpoints.ValidationError("Profissional não cadastrado.")
        profissional_saude.enviar_senha_acesso()
        return super().post()
    
    def check_permission(self):
        return not self.request.user.is_authenticated
