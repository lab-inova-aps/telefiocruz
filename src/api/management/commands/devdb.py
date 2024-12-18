from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from api.models import PessoaFisica


class Command(BaseCommand):
    def handle(self, *args, **options):
        user = User.objects.first()
        user.set_password('123')
        total = User.objects.update(password=user.password)
        print(f'{total} senhas atualizadas!')
        total = PessoaFisica.objects.update(email='', telefone='')
        print(f'{total} emails/telefones atualizados!')
