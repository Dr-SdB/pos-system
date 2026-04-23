from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Tenant(models.Model):
    name = models.CharField(max_length=255)
    subdomain = models.SlugField(unique=True)  # used as URL prefix: /sgi/, /maputo/
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    primary_color = models.CharField(max_length=7, default='#7c3aed')  # hex color e.g. #7c3aed
    icon = models.CharField(max_length=10, default='🏪')  # emoji or short text
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    temp_password = models.CharField(max_length=100, blank=True, default='')  # cleared when user sets own password

    def __str__(self):
        return f"{self.user.username} ({self.tenant})"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class Product(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50)
    category = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [('sku', 'tenant')]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20, default='un')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_stock = models.IntegerField(default=0)
    variant_sku = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (("product", "size", "color"),)

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color} ({self.variant_sku})"


class Sale(models.Model):
    PAYMENT_CHOICES = [
        ("Dinheiro", "Dinheiro"),
        ("M-Pesa", "M-Pesa"),
        ("E-Mola", "E-Mola"),
        ("eMola", "eMola"),
        ("Cartao", "Cartão"),
        ("Transferencia", "Transferência"),
        ("POS", "POS"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    subtotal_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    flat_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="Dinheiro")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_given = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    LOCATION_CHOICES = [("Loja", "Loja"), ("Online", "Online")]
    customer_name = models.CharField(max_length=255, blank=True)
    attendant = models.CharField(max_length=100, blank=True)  # auto-set to logged-in username
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default="Loja")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Venda #{self.pk} - {self.created_at:%Y-%m-%d %H:%M}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    base_unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_gross_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_net_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.product_variant} x {self.quantity} (Venda #{self.sale_id})"


class StockAdjustment(models.Model):
    REASON_CHOICES = [
        ("Dano", "Dano"),
        ("Perda", "Perda"),
        ("Roubo", "Roubo"),
        ("Outro", "Outro"),
        ("Reposição", "Reposição"),
        ("Reposto", "Reposto"),
        ("Anulado", "Anulado"),
    ]

    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name="adjustments")
    quantity = models.IntegerField(help_text="Positive = added, Negative = removed")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'+' if self.quantity > 0 else ''}{self.quantity} x {self.product_variant} ({self.reason})"
