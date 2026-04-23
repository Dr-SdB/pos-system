"""
Adds sample products and sales to a tenant for demo/testing purposes.

Usage:
    python manage.py seed_sample_data --subdomain sgi
"""
from datetime import timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from pos.models import Tenant, Product, ProductVariant, Sale, SaleItem, StockAdjustment


SAMPLE_PRODUCTS = [
    {"name": "Camiseta Básica", "sku": "CAM-001", "category": "Vestuário", "variants": [
        {"size": "S", "color": "Branco", "price": 350, "stock": 20},
        {"size": "M", "color": "Branco", "price": 350, "stock": 25},
        {"size": "L", "color": "Preto",  "price": 350, "stock": 18},
        {"size": "XL", "color": "Preto", "price": 350, "stock": 10},
    ]},
    {"name": "Calças Jeans", "sku": "CAL-001", "category": "Vestuário", "variants": [
        {"size": "32", "color": "Azul",  "price": 850, "stock": 8},
        {"size": "34", "color": "Azul",  "price": 850, "stock": 6},
        {"size": "36", "color": "Preto", "price": 900, "stock": 5},
        {"size": "38", "color": "Azul",  "price": 900, "stock": 4},
    ]},
    {"name": "Polo Masculino", "sku": "POL-001", "category": "Vestuário", "variants": [
        {"size": "M", "color": "Azul Marinho", "price": 550, "stock": 12},
        {"size": "L", "color": "Azul Marinho", "price": 550, "stock": 10},
        {"size": "M", "color": "Branco",       "price": 550, "stock": 8},
    ]},
    {"name": "Shorts Desportivos", "sku": "SHO-001", "category": "Vestuário", "variants": [
        {"size": "M", "color": "Preto", "price": 400, "stock": 15},
        {"size": "L", "color": "Preto", "price": 400, "stock": 12},
        {"size": "M", "color": "Cinza", "price": 400, "stock": 9},
    ]},
    {"name": "Sapatilhas Desportivas", "sku": "SAP-001", "category": "Calçado", "variants": [
        {"size": "39", "color": "Branco", "price": 1200, "stock": 6},
        {"size": "40", "color": "Branco", "price": 1200, "stock": 8},
        {"size": "42", "color": "Preto",  "price": 1200, "stock": 7},
        {"size": "44", "color": "Preto",  "price": 1200, "stock": 4},
    ]},
    {"name": "Sandálias", "sku": "SAN-001", "category": "Calçado", "variants": [
        {"size": "37", "color": "Castanho", "price": 650, "stock": 10},
        {"size": "38", "color": "Castanho", "price": 650, "stock": 8},
        {"size": "40", "color": "Preto",    "price": 650, "stock": 6},
    ]},
    {"name": "Mochila Desportiva", "sku": "MOC-001", "category": "Acessórios", "variants": [
        {"size": "", "color": "Preto", "price": 950,  "stock": 10},
        {"size": "", "color": "Cinza", "price": 950,  "stock": 7},
        {"size": "", "color": "Azul",  "price": 950,  "stock": 5},
    ]},
    {"name": "Boné", "sku": "BON-001", "category": "Acessórios", "variants": [
        {"size": "", "color": "Preto",      "price": 250, "stock": 20},
        {"size": "", "color": "Branco",     "price": 250, "stock": 15},
        {"size": "", "color": "Azul Marinho","price": 250, "stock": 12},
    ]},
    {"name": "Cinto de Couro", "sku": "CIN-001", "category": "Acessórios", "variants": [
        {"size": "M", "color": "Preto",    "price": 380, "stock": 10},
        {"size": "L", "color": "Preto",    "price": 380, "stock": 8},
        {"size": "M", "color": "Castanho", "price": 380, "stock": 6},
    ]},
    {"name": "Garrafa de Água 1L", "sku": "GAR-001", "category": "Acessórios", "variants": [
        {"size": "", "color": "Azul",     "price": 120, "stock": 30},
        {"size": "", "color": "Vermelho", "price": 120, "stock": 25},
        {"size": "", "color": "Preto",    "price": 120, "stock": 20},
    ]},
    {"name": "Auriculares Bluetooth", "sku": "AUR-001", "category": "Electrónica", "variants": [
        {"size": "", "color": "Preto",  "price": 1800, "stock": 8},
        {"size": "", "color": "Branco", "price": 1800, "stock": 6},
    ]},
    {"name": "Carregador Portátil", "sku": "CAR-001", "category": "Electrónica", "variants": [
        {"size": "", "color": "Preto",  "price": 1100, "stock": 10},
        {"size": "", "color": "Branco", "price": 1100, "stock": 7},
    ]},
]

# Weekday weights: Mon–Sun (0=Mon). Fri/Sat busiest, Sun slowest.
WEEKDAY_WEIGHT = [1.0, 1.0, 1.1, 1.2, 1.8, 2.0, 0.5]

# Attendants with individual sales weights — Ana is the clear standout
ATTENDANTS = [
    ("Ana",     0.40),
    ("Carlos",  0.25),
    ("Fátima",  0.20),
    ("João",    0.15),
]

PAYMENT_METHODS = ['Dinheiro', 'M-Pesa', 'E-Mola', 'Cartao', 'POS', 'Transferencia']
PAYMENT_WEIGHTS  = [0.28,       0.25,     0.22,     0.12,     0.08,  0.05]

LOCATIONS = [('Loja', 0.85), ('Online', 0.15)]

HISTORY_DAYS = 180  # 6 months


def _weighted_choice(choices):
    """Pick from [(value, weight), ...] list."""
    values, weights = zip(*choices)
    return random.choices(values, weights=weights, k=1)[0]


def _build_variants(tenant, products_data):
    """Create Product + ProductVariant records, return all variant objects."""
    variants = []
    for p_data in products_data:
        product = Product.objects.create(
            tenant=tenant,
            sku=p_data['sku'],
            name=p_data['name'],
            category=p_data['category'],
        )
        for v in p_data['variants']:
            parts = [tenant.subdomain, p_data['sku']]
            if v['color']:
                parts.append(v['color'][:10].replace(' ', '').upper())
            if v['size']:
                parts.append(v['size'].replace(' ', '').upper())
            variant_sku = '-'.join(parts)[:80]
            variant = ProductVariant.objects.create(
                product=product,
                variant_sku=variant_sku,
                size=v['size'],
                color=v['color'],
                unit='un',
                base_price=Decimal(str(v['price'])),
                current_stock=v['stock'],
            )
            variants.append(variant)
    return variants


def _make_sales(tenant, all_variants, days=HISTORY_DAYS):
    """Generate realistic sales history and return count."""
    sales_created = 0
    now = timezone.now()

    # Temporarily allow setting created_at directly (bypasses auto_now_add)
    _field = Sale._meta.get_field('created_at')
    _field.auto_now_add = False

    # Product popularity weights — electronics and shoes sell at premium, basics sell often
    variant_weights = []
    for v in all_variants:
        price = float(v.base_price)
        if price >= 1500:
            w = 0.5   # expensive items sell less often
        elif price >= 800:
            w = 1.0
        elif price >= 400:
            w = 1.8
        else:
            w = 2.5   # cheap items (garrafas, bonés) sell most often
        variant_weights.append(w)

    for days_ago in range(days, 0, -1):
        sale_date = now - timedelta(days=days_ago)
        weekday = sale_date.weekday()  # 0=Mon
        weight = WEEKDAY_WEIGHT[weekday]

        # Base 4–12 sales/day, scaled by weekday weight
        base = random.randint(4, 12)
        num_sales = max(1, int(base * weight))

        for _ in range(num_sales):
            hour = random.randint(8, 20)
            minute = random.randint(0, 59)
            sale_dt = sale_date.replace(hour=hour, minute=minute, second=random.randint(0, 59), microsecond=0)

            attendant = _weighted_choice(ATTENDANTS)
            payment = _weighted_choice(list(zip(PAYMENT_METHODS, PAYMENT_WEIGHTS)))
            location = _weighted_choice(LOCATIONS)

            num_items = random.choices([1, 2, 3, 4], weights=[0.5, 0.3, 0.15, 0.05])[0]
            chosen = random.choices(all_variants, weights=variant_weights, k=num_items)
            # Remove duplicates while preserving order
            seen, unique_chosen = set(), []
            for v in chosen:
                if v.id not in seen:
                    seen.add(v.id)
                    unique_chosen.append(v)

            subtotal = Decimal('0')
            items = []
            for variant in unique_chosen:
                qty = random.choices([1, 2, 3], weights=[0.65, 0.25, 0.10])[0]
                line = variant.base_price * qty
                subtotal += line
                items.append((variant, qty, variant.base_price, line))

            # ~18% of sales get a small flat discount
            flat_discount = Decimal('0')
            if random.random() < 0.18:
                pct = random.choice([5, 10, 15])
                flat_discount = (subtotal * pct / 100).quantize(Decimal('0.01'))

            total_net = subtotal - flat_discount
            amount_paid = total_net
            change = Decimal('0')
            if payment == 'Dinheiro':
                # Round up to nearest 50
                rounded = (int(total_net / 50) + 1) * 50
                amount_paid = Decimal(str(rounded))
                change = amount_paid - total_net

            sale = Sale.objects.create(
                tenant=tenant,
                created_at=sale_dt,
                subtotal_gross=subtotal,
                total_discount=Decimal('0'),
                flat_discount=flat_discount,
                total_net=total_net,
                payment_method=payment,
                amount_paid=amount_paid,
                change_given=change,
                attendant=attendant,
                location=location,
            )
            for variant, qty, unit_price, line_total in items:
                SaleItem.objects.create(
                    sale=sale,
                    product_variant=variant,
                    quantity=qty,
                    base_unit_price=unit_price,
                    line_gross_total=line_total,
                    line_discount_total=Decimal('0'),
                    line_net_total=line_total,
                )
            sales_created += 1

    _field.auto_now_add = True
    return sales_created


def reset_demo_data(tenant):
    """
    Wipe all products/sales/adjustments for a tenant and re-seed with sample data.
    Returns the number of sales created.
    Called from both the management command and panel_demo_reset view.
    """
    StockAdjustment.objects.filter(product_variant__product__tenant=tenant).delete()
    SaleItem.objects.filter(sale__tenant=tenant).delete()
    Sale.objects.filter(tenant=tenant).delete()
    ProductVariant.objects.filter(product__tenant=tenant).delete()
    Product.objects.filter(tenant=tenant).delete()

    # Reset all three sequences so IDs start from 1 after the wipe.
    with connection.cursor() as cursor:
        for table in ('pos_product', 'pos_productvariant', 'pos_sale'):
            cursor.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 0) + 1,
                    false
                )
            """)

    all_variants = _build_variants(tenant, SAMPLE_PRODUCTS)
    return _make_sales(tenant, all_variants)


class Command(BaseCommand):
    help = 'Seed sample products and sales for a tenant'

    def add_arguments(self, parser):
        parser.add_argument('--subdomain', required=True)

    def handle(self, *args, **options):
        subdomain = options['subdomain'].lower().strip()
        try:
            tenant = Tenant.objects.get(subdomain=subdomain)
        except Tenant.DoesNotExist:
            raise CommandError(f"Tenant '{subdomain}' not found.")

        self.stdout.write(f'Seeding data for "{subdomain}"...')

        variants_created = _build_variants(tenant, SAMPLE_PRODUCTS)
        self.stdout.write(f'  Products/variants created: {len(variants_created)}')

        all_variants = list(ProductVariant.objects.filter(product__tenant=tenant, is_active=True))
        sales_created = _make_sales(tenant, all_variants)

        self.stdout.write(self.style.SUCCESS(f'Done! {sales_created} sales created for "{subdomain}".'))
