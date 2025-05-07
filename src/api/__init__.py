from slth.application import Application


class ApiApplication(Application):
    def __init__(self):
        super().__init__()
        self.title = "Telefiocruz"
        self.subtitle = "Telefiocruz - Telessaúde da Fiocruz"
        self.icon = "/static/images/icon.svg"
        self.logo = "/static/images/logo.svg"
        self.version = '1.0.7'
        self.groups.add(
            a="Administrador",
            g="Gestor de Núcleo",
            o="Operador de Núcleo",
            ps="Profissinal de Saúde",
            p="Paciente",
            gu="Gestor de Unidade",
            ou="Operador de Unidade",
            s="Supervisor",
            ag="Agendador",
        )
        self.dashboard.usermenu.add(
            "profile.userprofile",
            "dev.icons",
            "user.users",
            "log.logs",
            "email.emails",
            "pushsubscription.pushsubscriptions",
            "job.jobs",
            "deletion.deletions",
            "auth.logout",
        )
        self.dashboard.boxes.add(
            "abrirsala",
            "profissionalsaude.configurarurlwebconf",
            "pessoafisica.pessoasfisicas",
            "nucleo.nucleos",
            "unidade.unidades",
            "profissionalsaude.profissionaissaude",
            "profissionalsaude.definirhorarios",
            "paciente.pacientes",
            "atendimento.atendimentos",
            "atendimento.proximos",
            "atendimento.aguardandotestedispositivo",
            "atendimento.aguardandoconfirmacao",
            "atendimento.agenda",
            "materialapoio.materiaisapoio",
            "estatistica",
            "profissionalsaude.especialistas",
        )
        self.dashboard.center.add(
            'profissionalsaude.vinculos', 
            'profissionalsaude.atendimentosdodia', 
            'pessoafisica.atendimentosdodia', 
            'profissionalsaude.minhaagenda'
        )
        self.dashboard.toolbar.add("profissionalsaude.primeiroacesso")

        self.menu.add(
            {
                "user-gear:Usuários": {
                    "Administradores": "administrador.administradores",
                    "Supervisores": "supervisor.supervisores",
                    "Agendadores": "agendador.agendadores",
                },
                "list:Cadastros Gerais": {
                    "CIDs": "cid.cids",
                    "CIAPs": "ciap.ciaps",
                    "Conselhos de Classe": "conselhoclasse.conselhosclasse",
                    "Sexos": "sexo.sexos",
                    "Tipos de Atendimento": "tipoatendimento.tiposatendimento",
                    "Estados": "estado.estados",
                    "Municípios": "municipio.municipios",
                    "Áreas": "area.areas",
                    "Especialidades": "especialidade.especialidades",
                    "Tipos de Exame": "tipoexame.tiposexame",
                    "Medicamentos": "medicamento.medicamentos",
                },
                "building-user:Núcleos de Telessaúde": "nucleo.nucleos",
                "building:Unidades de Saúde": "unidade.unidades",
                "stethoscope:Profissionais de Saúde": "profissionalsaude.profissionaissaude",
                "users:Pessoas Físicas": "pessoafisica.pessoasfisicas",
                "laptop-file:Atendimentos": "atendimento.atendimentos",
            }
        )
        self.theme.light.primary.update(color="#265890", background="#265890")
        self.theme.light.secondary.update(color="#071e41")
        self.theme.light.auxiliary.update(color="#2670e8")
        self.theme.light.info.update(color="#265890", background="#d4e5ff")
        self.theme.light.success.update(color="#ffffff", background="#5ca05d")
        self.theme.light.warning.update(color="#fff5c2")
        self.theme.light.danger.update(color="#e52207")
        self.theme.light.header.update(color="#ffffff", background="#265890")

        self.theme.dark.header.update(color="#0D1117", background="#90C4F9")
