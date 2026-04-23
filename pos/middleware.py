from django.conf import settings
from django.http import Http404

from .models import Tenant


class DemoAutoLoginMiddleware:
    """
    When DEMO_MODE=1, automatically logs every visitor in as the demo guest user.
    Must be placed after AuthenticationMiddleware in settings.MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'DEMO_MODE', False) and not request.user.is_authenticated:
            if not request.path_info.startswith('/admin/'):
                from django.contrib.auth import login
                from django.contrib.auth.models import User
                try:
                    guest = User.objects.get(username=settings.DEMO_GUEST_USER)
                    login(request, guest, backend='django.contrib.auth.backends.ModelBackend')
                except User.DoesNotExist:
                    pass
        return self.get_response(request)


class TenantMiddleware:
    """
    Resolves the tenant from the URL path prefix.
    URLs are structured as /<tenant_slug>/...

    In DEBUG mode with no matching tenant slug, falls through so that
    /admin/ and other non-tenant paths work normally.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Strip leading slash and grab first path segment
        parts = request.path_info.lstrip('/').split('/')
        slug = parts[0] if parts else ''

        request.tenant = None

        if slug and slug not in ('admin', 'login', 'logout', 'static'):
            try:
                request.tenant = Tenant.objects.get(subdomain=slug, is_active=True)
            except Tenant.DoesNotExist:
                raise Http404('Tenant not found')
            except Exception:
                # DB not ready yet (e.g. migrations haven't run) — fail silently
                pass

        # If a tenant was resolved, verify the logged-in user belongs to it.
        # Superusers are blocked from tenant pages — they use /panel/ instead.
        if request.tenant and request.user.is_authenticated:
            if request.user.is_superuser:
                raise Http404('Superusers do not have tenant access')
            try:
                user_tenant = request.user.userprofile.tenant
                if user_tenant and user_tenant != request.tenant:
                    raise Http404('Access denied')
            except AttributeError:
                pass  # userprofile not yet created — let auth handle it

        return self.get_response(request)
