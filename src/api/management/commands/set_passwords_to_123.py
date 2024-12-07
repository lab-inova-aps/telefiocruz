from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        user = User.objects.first()
        user.set_password('123')
        User.objects.update(password=user.password)
