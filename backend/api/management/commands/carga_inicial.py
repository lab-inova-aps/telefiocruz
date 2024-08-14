from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    def handle(self, *args, **options):
        User.objects.filter(username='admin').update(username='000.000.000-00')
        call_command('loaddata', 'initial_data.json.gz')
