"""
Idempotent demo setup: creates the demo tenant and guest user if they don't
exist, and ensures the guest is assigned to the tenant with staff access.

Run automatically on startup via Dockerfile CMD.
"""
import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from pos.models import Tenant


class Command(BaseCommand):
    help = 'Set up demo tenant and guest user'

    def handle(self, *args, **options):
        slug = os.environ.get('DEMO_TENANT_SLUG', 'demo')
        guest_username = os.environ.get('DEMO_GUEST_USER', 'guest')

        tenant, created = Tenant.objects.get_or_create(
            subdomain=slug,
            defaults={'name': 'Demo', 'is_active': True, 'is_demo': True},
        )
        if not tenant.is_active:
            tenant.is_active = True
            tenant.save()
        self.stdout.write(f'Tenant "{slug}": {"created" if created else "exists"}')

        guest, created = User.objects.get_or_create(
            username=guest_username,
            defaults={'is_staff': True},
        )
        if not guest.is_staff:
            guest.is_staff = True
            guest.save()

        profile = guest.userprofile
        if profile.tenant != tenant:
            profile.tenant = tenant
            profile.save()

        self.stdout.write(self.style.SUCCESS(f'Guest user "{guest_username}" ready.'))
