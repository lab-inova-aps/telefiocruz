from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    def handle(self, *args, **options):
        username = '000.000.000-00'
        User.objects.filter(username='admin').update(username=username)
        admin = User.objects.filter(username=username).first()
        if admin is None:
            User.objects.create_superuser(username, password='123')
        call_command('loaddata', 'initial_data.json.gz')
