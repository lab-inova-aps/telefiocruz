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


class AlterarAgenda(endpoints.InstanceEndpoint[ProfissionalSaude]):

    class Meta:
        icon = "calendar-plus"
        verbose_name = "Alterar Agenda"

    def get(self):
        return (
            self.formfactory()
            .display(
                "Dados do Profissional",
                (("pessoa_fisica", "especialidade"),),
            )
            .fields()
        )

    def getform(self, form):
        form.fields["horarios"] = forms.SchedulerField(
            scheduler=self.instance.get_agenda(readonly=False)
        )
        return form

    def post(self):
        for data_hora in self.cleaned_data["horarios"]["select"]:
            HorarioProfissionalSaude.objects.create(data_hora=data_hora, profissional_saude=self.instance)
        for data_hora in self.cleaned_data["horarios"]["deselect"]:
            HorarioProfissionalSaude.objects.filter(data_hora=data_hora, profissional_saude=self.instance).delete()
        return super().post()
    
    def check_permission(self):
        return self.check_role('g', 'o', 'ou')#  or self.instance.pessoa_fisica.cpf == self.request.user.username


class DefinirHorario(endpoints.InstanceEndpoint[ProfissionalSaude]):
    horarios = forms.SchedulerField(scheduler=components.Scheduler(weekly=True, chucks=3))

    class Meta:
        icon = "user-clock"
        verbose_name = "Definir Horários"

    def getform(self, form):
        form.fields['horarios'] = forms.SchedulerField(scheduler=self.instance.get_horarios_atendimento(False))
        return super().getform(form)

    def get(self):
        return (self.formfactory().fields('horarios'))
    
    def post(self):
        self.instance.atualizar_horarios_atendimento(self.cleaned_data['horarios']['select'], self.cleaned_data['horarios']['deselect'])
        return super().post()
    
    def check_permission(self):
        return self.check_role('g', 'o', 'ou')


class DefinirHorarios(endpoints.Endpoint):
    profissionais = forms.ModelMultipleChoiceField(ProfissionalSaude.objects, label='Profissionais de Saúde')
    horarios = forms.SchedulerField(scheduler=components.Scheduler(weekly=True, chucks=3))

    class Meta:
        icon = "user-clock"
        verbose_name = "Definir Horários de Atendimento"

    def get(self):
        return (self.formfactory().fields('profissionais', 'horarios'))
    
    def post(self):
        for profissional_saude in self.cleaned_data['profissionais']:
            profissional_saude.atualizar_horarios_atendimento(self.cleaned_data['horarios']['select'], self.cleaned_data['horarios']['deselect'])
        return super().post()


class ProximosAtendimentos(endpoints.QuerySetEndpoint[Atendimento]):
    class Meta:
        verbose_name= 'Próximos Atendimentos'

    def get(self):
        return super().get().proximos().fields('get_numero', 'tipo', 'paciente', 'assunto', 'get_agendado_para').actions('atendimento.view').lookup('ps', profissional__pessoa_fisica__cpf='username', especialista__pessoa_fisica__cpf='username')
    
    def check_permission(self):
        return self.check_role('ps', superuser=False)
    

class Vinculos(endpoints.ListEndpoint[ProfissionalSaude]):
    
    class Meta:
        verbose_name= 'Meus Vínculos'
    
    def get(self):
        return super().get().filter(pessoa_fisica__cpf=self.request.user).fields('get_estabelecimento', 'especialidade').actions("profissionalsaude.alteraragenda")

    def check_permission(self):
        return self.check_role('ps', superuser=False)


class MinhaAgenda(endpoints.Endpoint):
    class Meta:
        icon = 'calendar-days'
        verbose_name = 'Minha Agenda'

    def get(self):
        return ProfissionalSaude.objects.filter(pessoa_fisica__cpf=self.request.user.username).first().get_agenda()
    
    def check_permission(self):
        return self.check_role('ps', superuser=False)