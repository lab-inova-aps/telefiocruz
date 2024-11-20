from ...models import Atendimento, TipoExame
from datetime import datetime
from slth.pdf import PdfWriter
from django.core.management.base import BaseCommand

LOGO = '/Users/breno/Documents/Workspace/telefiocruz/src/api/static/images/icon-black.svg'
URL = 'http://telefiocruz.aplicativo.click/arquivo/1518eb3c61a311ef9ca22a8c307b6d2c/'


class Command(BaseCommand):
    def handle(self, *args, **options):
        atendimento = Atendimento.objects.get(pk=43)

        writter = PdfWriter()
        writter.render('documentos/atendimento.html', dict(atendimento=atendimento, data_hora=datetime.now(), logo=LOGO))
        writter.save('/tmp/atendimento.pdf')
        return 
        
        writter = PdfWriter()
        writter.render('documentos/atestado.html', dict(atendimento=atendimento, data_hora=datetime.now(), quantidade_dias=5, logo=LOGO))
        writter.save('/tmp/atestado.pdf')
        
        writter = PdfWriter()
        writter.render('documentos/termo.html', dict(atendimento=atendimento, data_hora=datetime.now(), logo=LOGO))
        writter.save('/tmp/termo.pdf')

        writter = PdfWriter()
        medicamentos = [
            ('Tylenol 100mg', 'Tomar duas vezes ao dia depois do café-da-manhã.'),
            ('Decadron 5mg', 'Tomar antes de dormir.')
        ]
        writter.render('documentos/prescricao.html', dict(atendimento=atendimento, data_hora=datetime.now(), medicamentos=medicamentos, logo=LOGO))
        writter.pdf.image('/tmp/qrcode.png', x=180, y=260, h=30)
        writter.pdf.set_font_size(8)
        writter.pdf.text(77, 293, URL)
        writter.save('/tmp/prescricao.pdf')
        
        writter = PdfWriter()
        tipos = TipoExame.objects.all()
        writter.render('documentos/exames.html', dict(atendimento=atendimento, data_hora=datetime.now(), tipos=tipos, logo=LOGO))
        writter.save('/tmp/exames.pdf')
