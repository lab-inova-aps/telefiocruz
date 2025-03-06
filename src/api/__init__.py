from slth.application import Application


class ApiApplication(Application):
    def __init__(self):
        super().__init__()
        self.title = "Telefiocruz"
        self.subtitle = "Telefiocruz - Telessaúde da Fiocruz"
        self.icon = "/static/images/icon.png"
        self.logo = "/static/images/logo.png"
        self.groups.add(
            a="Administrador",
            g="Gestor de Núcleo",
            o="Operador de Núcleo",
            ps="Profissinal de Saúde",
            p="Paciente",
            gu="Gestor de Unidade",
            ou="Operador de Unidade",
            s="Supervisor",
        )
        self.dashboard.usermenu.add(
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
            "pessoafisica.pessoasfisicas",
            "nucleo.nucleos",
            "unidade.unidades",
            "profissionalsaude.profissionaissaude",
            "profissionalsaude.definirhorarios",
            "atendimento.atendimentos",
            "atendimento.agenda",
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

        self.theme.primary.update(color="#265890")
        self.theme.secondary.update(color="#071e41")
        self.theme.auxiliary.update(color="#2670e8")
        self.theme.info.update(color="#265890", background="#d4e5ff")
        self.theme.success.update(color="#5ca05d")
        self.theme.warning.update(color="#fff5c2")
        self.theme.danger.update(color="#e52207")
