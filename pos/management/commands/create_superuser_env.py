import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create superuser from environment variables (DJANGO_SU_NAME, DJANGO_SU_PASSWORD)'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SU_NAME')
        password = os.environ.get('DJANGO_SU_PASSWORD')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                'Skipping superuser creation: DJANGO_SU_NAME or DJANGO_SU_PASSWORD not set.'
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'Superuser "{username}" already exists. Skipping.'
            ))
            return

        User.objects.create_superuser(username=username, password=password, email='')
        self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully.'))
