from ...models import Estado
from slth.models import TimeZone
from django.core.management.base import BaseCommand

lines = '''11;Rondônia;RO;America/Campo_Grande
12;Acre;AC;America/Rio_Branco
13;Amazonas;AM;America/Campo_Grande
14;Roraima;RR;America/Campo_Grande
15;Pará;PA;America/Fortaleza
16;Amapá;AP;America/Fortaleza
17;Tocantins;TO;America/Fortaleza
21;Maranhão;MA;America/Fortaleza
22;Piauí;PI;America/Fortaleza
23;Ceará;CE;America/Fortaleza
24;Rio Grande do Norte;RN;America/Fortaleza
25;Paraíba;PB;America/Fortaleza
26;Pernambuco;PE;America/Fortaleza
27;Alagoas;AL;America/Fortaleza
28;Sergipe;SE;America/Fortaleza
29;Bahia;BA;America/Fortaleza
31;Minas Gerais;MG;America/Fortaleza
32;Espírito Santo;ES;America/Fortaleza
33;Rio de Janeiro;RJ;America/Fortaleza
35;São Paulo;SP;America/Fortaleza
41;Paraná;PR;America/Fortaleza
42;Santa Catarina;SC;America/Fortaleza
43;Rio Grande do Sul;RS;America/Campo_Grande
50;Mato Grosso do Sul;MS;America/Campo_Grande
51;Mato Grosso;MT;America/Fortaleza
52;Goiás;GO;America/Fortaleza
53;Distrito Federal;DF;America/Fortaleza'''


class Command(BaseCommand):
    def handle(self, *args, **options):
        for line in lines.split('\n'):
            codigo, nome, sigla, nome_fuso_horario = line.split(';')
            if not Estado.objects.filter(sigla=sigla).exists():
                fuso_horario = TimeZone.objects.get_or_create(name=nome_fuso_horario)[0]
                Estado.objects.create(sigla=sigla, nome=nome, codigo=codigo, fuso_horario=fuso_horario)