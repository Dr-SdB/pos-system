from django.contrib import admin
from .models import Tenant, UserProfile, Product, ProductVariant, Sale, SaleItem

# Only Tenant and UserProfile are exposed in Django admin.
# Product, Sale, and stock data belong to clients and are managed
# exclusively through their own tenant interface (/slug/).


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "subdomain", "is_active", "is_demo", "primary_color", "created_at")
    list_filter = ("is_active", "is_demo")
    search_fields = ("name", "subdomain")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant")
    list_filter = ("tenant",)
    search_fields = ("user__username", "user__email")
