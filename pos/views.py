import json
import csv
import calendar
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from collections import defaultdict
from functools import wraps

from django.db import transaction
from django.utils.timezone import localtime, now as tz_now
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django_ratelimit.decorators import ratelimit

from django.contrib.auth.models import User
from .models import Product, ProductVariant, Sale, SaleItem, Tenant


# ── Root redirect ─────────────────────────────────────────────────────────────

def root_redirect(request):
    from django.conf import settings
    if getattr(settings, 'DEMO_MODE', False):
        return redirect(f'/{settings.DEMO_TENANT_SLUG}/')
    try:
        tenant = request.user.userprofile.tenant
        if tenant:
            return redirect(f'/{tenant.subdomain}/')
    except AttributeError:
        pass
    return redirect('/admin/')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _json(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def _api_login_required(view_func):
    """Like @login_required but returns JSON 401 instead of a redirect."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def _staff_required(view_func):
    """API decorator: requires is_staff=True. Returns JSON 401/403."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        if not request.user.is_staff:
            return JsonResponse({"error": "Permission denied"}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def _ratelimit_api(rate):
    """Decorator: IP-based rate limit for API write endpoints. Returns JSON 429."""
    def decorator(view_func):
        @wraps(view_func)
        @ratelimit(key='ip', rate=rate, method='POST', block=False)
        def wrapper(request, *args, **kwargs):
            if getattr(request, 'limited', False):
                return JsonResponse({'error': 'Demasiadas tentativas. Aguarde um momento.'}, status=429)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _demo_readonly(view_func):
    """Kept for compatibility — demo tenants now have full access."""
    return view_func


def boss_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin/')
        if not request.user.is_staff:
            slug = request.tenant.subdomain if request.tenant else ''
            return redirect(f'/{slug}/sale/')
        return view_func(request, *args, **kwargs)
    return wrapper


def _safe_decimal(value, field_name="value"):
    """Convert a value to Decimal or raise ValueError with a clear message."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Invalid numeric value for '{field_name}'")


def _parse_date(value, field_name):
    """Validate and return a YYYY-MM-DD string, or None if empty."""
    if not value:
        return None
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return value
    except ValueError:
        raise ValueError(f"Invalid date for '{field_name}'. Expected YYYY-MM-DD.")


def _require_tenant(request):
    """Returns a 404 response if no tenant is set, else None."""
    if not request.tenant:
        from django.http import Http404
        raise Http404("Tenant not found")
    return None


# ── API: Dashboard  GET /<tenant>/api/dashboard ───────────────────────────────
@_staff_required
def dashboard(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    if not (1 <= month <= 12):
        return JsonResponse({"error": "Invalid month"}, status=400)
    if not (2000 <= year <= 2100):
        return JsonResponse({"error": "Invalid year"}, status=400)

    qs = Sale.objects.filter(tenant=request.tenant, created_at__year=year, created_at__month=month)

    total_revenue = float(qs.aggregate(t=Sum("total_net"))["t"] or 0)
    total_sales = qs.count()
    total_units = SaleItem.objects.filter(sale__in=qs).aggregate(t=Sum("quantity"))["t"] or 0

    payment_breakdown = {}
    for s in qs.values("payment_method").annotate(total=Sum("total_net"), count=Count("id")):
        key = s["payment_method"] or "Outro"
        payment_breakdown[key] = {
            "total": float(s["total"]),
            "count": s["count"],
        }

    sales_by_day = defaultdict(float)
    for s in qs.values("created_at__day").annotate(total=Sum("total_net")):
        sales_by_day[s["created_at__day"]] = float(s["total"])

    days_in_month = calendar.monthrange(year, month)[1]
    chart_data = [{"day": d, "revenue": sales_by_day.get(d, 0)} for d in range(1, days_in_month + 1)]

    low_stock = list(
        ProductVariant.objects.filter(is_active=True, current_stock__lte=5, product__tenant=request.tenant)
        .select_related("product")
        .values("variant_sku", "current_stock", "product__name", "size", "color")[:10]
    )

    top_products = []
    for item in (
        SaleItem.objects.filter(sale__in=qs)
        .values("product_variant__product__name")
        .annotate(units=Sum("quantity"), revenue=Sum("line_net_total"))
        .order_by("-revenue")[:5]
    ):
        top_products.append({
            "name": item["product_variant__product__name"],
            "units": item["units"],
            "revenue": float(item["revenue"]),
        })

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_qs = Sale.objects.filter(tenant=request.tenant, created_at__year=prev_year, created_at__month=prev_month)
    prev_revenue = float(prev_qs.aggregate(t=Sum("total_net"))["t"] or 0)
    revenue_change = round(((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0, 1)

    total_inventory = ProductVariant.objects.filter(
        is_active=True, product__tenant=request.tenant
    ).aggregate(t=Sum("current_stock"))["t"] or 0

    top_attendant = None
    top_attendant_row = (
        qs.filter(attendant__gt='')
        .values('attendant')
        .annotate(revenue=Sum('total_net'), count=Count('id'))
        .order_by('-revenue')
        .first()
    )
    if top_attendant_row:
        top_attendant = {
            'name': top_attendant_row['attendant'],
            'revenue': float(top_attendant_row['revenue']),
            'count': top_attendant_row['count'],
        }

    # week_day: 1=Sunday, 2=Monday … 7=Saturday
    weekday_order = [2, 3, 4, 5, 6, 7, 1]
    weekday_labels = {2: 'Mon', 3: 'Tue', 4: 'Wed', 5: 'Thu', 6: 'Fri', 7: 'Sat', 1: 'Sun'}
    weekday_totals = defaultdict(float)
    for s in qs.values('created_at__week_day').annotate(total=Sum('total_net')):
        weekday_totals[s['created_at__week_day']] = float(s['total'])
    sales_by_weekday = [
        {'day': weekday_labels[d], 'revenue': weekday_totals.get(d, 0)}
        for d in weekday_order
    ]

    return JsonResponse({
        "month": month,
        "year": year,
        "total_revenue": round(total_revenue, 2),
        "total_sales": total_sales,
        "total_units_sold": total_units,
        "total_inventory": total_inventory,
        "revenue_change_pct": revenue_change,
        "payment_breakdown": payment_breakdown,
        "chart_data": chart_data,
        "low_stock": low_stock,
        "top_products": top_products,
        "top_attendant": top_attendant,
        "sales_by_weekday": sales_by_weekday,
    })


# ── API: Product search  GET /<tenant>/api/products ──────────────────────────
@_api_login_required
def product_search(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    query = request.GET.get("search", "").strip()[:100]
    size = request.GET.get("size", "").strip()[:50]
    color = request.GET.get("color", "").strip()[:50]
    category = request.GET.get("category", "").strip()[:50]

    qs = ProductVariant.objects.select_related("product").filter(
        is_active=True, product__tenant=request.tenant
    )

    if query:
        qs = qs.filter(Q(product__name__icontains=query) | Q(variant_sku__icontains=query))
    if size and size != "all":
        qs = qs.filter(size__iexact=size)
    if color and color != "all":
        qs = qs.filter(color__iexact=color)
    if category and category != "all":
        qs = qs.filter(product__category__iexact=category)

    data = [
        {
            "id": v.id,
            "product_id": v.product_id,
            "product_name": v.product.name,
            "sku": v.variant_sku,
            "base_sku": v.product.sku,
            "size": v.size,
            "color": v.color,
            "unit": v.unit,
            "price": float(v.base_price),
            "stock": v.current_stock,
            "category": v.product.category,
        }
        for v in qs[:100]
    ]
    return JsonResponse({"results": data})


# ── API: Catalogue  GET /<tenant>/api/catalogue ───────────────────────────────
@_staff_required
def catalogue(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    try:
        limit = min(max(int(request.GET.get('limit', 200)), 1), 500)
        offset = max(int(request.GET.get('offset', 0)), 0)
    except (ValueError, TypeError):
        limit, offset = 200, 0

    qs = ProductVariant.objects.select_related("product").filter(
        is_active=True, product__tenant=request.tenant
    ).order_by("product__name", "size", "color")
    total = qs.count()
    data = [
        {
            "id": v.id,
            "product_id": v.product_id,
            "product_name": v.product.name,
            "sku": v.variant_sku,
            "base_sku": v.product.sku,
            "size": v.size,
            "color": v.color,
            "unit": v.unit,
            "price": float(v.base_price),
            "stock": v.current_stock,
            "category": v.product.category,
        }
        for v in qs[offset:offset + limit]
    ]
    return JsonResponse({"results": data, "total": total, "limit": limit, "offset": offset})


# ── API: Update variant  PATCH /<tenant>/api/catalogue/<id> ──────────────────
@_staff_required
@_ratelimit_api('60/m')
def update_variant(request, variant_id, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    try:
        variant = ProductVariant.objects.select_related("product").get(
            id=variant_id, product__tenant=request.tenant
        )
    except ProductVariant.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "DELETE":
        variant.is_active = False
        variant.save()
        return JsonResponse({"ok": True})

    if request.method not in ("PATCH", "PUT", "POST"):
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = _json(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if "price" in data:
        try:
            variant.base_price = _safe_decimal(data["price"], "price")
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
    if "stock" in data:
        try:
            variant.current_stock = max(0, int(data["stock"]))
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid stock value"}, status=400)
    if "size" in data:
        variant.size = str(data["size"])[:50]
    if "color" in data:
        variant.color = str(data["color"])[:50]
    if "unit" in data:
        variant.unit = str(data["unit"])[:20]
    variant.save()

    if "product_name" in data:
        variant.product.name = str(data["product_name"]).strip()[:255]
        variant.product.save()
    if "category" in data:
        variant.product.category = str(data["category"]).strip()[:50]
        variant.product.save()

    return JsonResponse({"ok": True})


# ── API: Add variant  POST /<tenant>/api/catalogue/add ───────────────────────
@_staff_required
@_ratelimit_api('30/m')
def add_variant(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = _json(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    for f in ("product_name", "price"):
        if not data.get(f):
            return JsonResponse({"error": f"Missing field: {f}"}, status=400)

    try:
        price = _safe_decimal(data["price"], "price")
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    product_name = str(data["product_name"]).strip()

    # Auto-generate SKU if not provided: first 3 letters of name + next sequence number
    if data.get("base_sku"):
        base_sku = str(data["base_sku"]).strip().upper()[:50]
    else:
        import re
        prefix = re.sub(r'[^A-Za-z]', '', product_name).upper()[:3].ljust(3, 'X')
        existing = Product.objects.filter(
            tenant=request.tenant, sku__startswith=prefix
        ).count()
        base_sku = f"{prefix}-{str(existing + 1).zfill(3)}"

    product, _ = Product.objects.get_or_create(
        sku=base_sku,
        tenant=request.tenant,
        defaults={
            "name": product_name[:255],
            "category": str(data.get("category", "")).strip()[:50],
        },
    )

    color = str(data.get("color", "")).strip()[:50]
    size = str(data.get("size", "")).strip()[:50]
    unit = str(data.get("unit", "un")).strip()[:20]
    parts = [product.sku]
    if color:
        parts.append(color[:10].replace(" ", "").upper())
    if size:
        parts.append(str(size).replace(" ", "").upper())
    variant_sku = "-".join(parts)[:80]

    if ProductVariant.objects.filter(variant_sku=variant_sku, product__tenant=request.tenant).exists():
        return JsonResponse({"error": f"Variant {variant_sku} already exists"}, status=400)

    try:
        stock = max(0, int(data.get("stock", 0)))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid stock value"}, status=400)

    variant = ProductVariant.objects.create(
        product=product,
        size=size,
        color=color,
        unit=unit,
        base_price=price,
        current_stock=stock,
        variant_sku=variant_sku,
    )
    return JsonResponse({"ok": True, "id": variant.id, "sku": variant_sku})


# ── API: Stock availability  GET /<tenant>/api/availability ──────────────────
@_api_login_required
def stock_availability(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    query = request.GET.get("search", "").strip()[:100]
    qs = ProductVariant.objects.select_related("product").filter(
        is_active=True, product__tenant=request.tenant
    )

    if query:
        qs = qs.filter(Q(product__name__icontains=query) | Q(variant_sku__icontains=query))

    data = [
        {
            "id": v.id,
            "product_name": v.product.name,
            "sku": v.variant_sku,
            "size": v.size,
            "color": v.color,
            "unit": v.unit,
            "stock": v.current_stock,
            "category": v.product.category,
        }
        for v in qs.order_by("product__name", "size", "color")[:200]
    ]
    return JsonResponse({"results": data})


# ── API: Create sale  POST /<tenant>/api/sale ─────────────────────────────────
@_api_login_required
@_ratelimit_api('120/m')
@transaction.atomic
def create_sale(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = _json(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    items = data.get("items", [])
    if not items:
        return JsonResponse({"error": "No items provided"}, status=400)

    payment_method = data.get("payment_method", "Cash")
    valid_methods = {"Cash", "M-Pesa", "E-Mola", "Card", "POS", "Transfer"}
    if payment_method not in valid_methods:
        return JsonResponse({"error": "Invalid payment method"}, status=400)

    try:
        amount_paid = _safe_decimal(data.get("amount_paid", 0), "amount_paid")
        flat_discount = _safe_decimal(data.get("flat_discount", 0), "flat_discount")
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    if flat_discount < 0:
        return JsonResponse({"error": "Flat discount cannot be negative"}, status=400)

    location = str(data.get("location", "Store")).strip()
    if location not in {"Store", "Online"}:
        location = "Store"

    # ── Pass 1: validate items and compute totals before any DB writes ─────────
    subtotal_gross = Decimal("0")
    total_discount = Decimal("0")
    validated_items = []

    for item in items:
        try:
            variant_id = int(item["variant_id"])
            quantity = int(item["quantity"])
            discount_percent = _safe_decimal(item.get("discount_percent", 0), "discount_percent")
        except (KeyError, ValueError, TypeError):
            return JsonResponse({"error": "Invalid item data"}, status=400)

        if quantity <= 0:
            return JsonResponse({"error": "Quantity must be positive"}, status=400)
        if not (0 <= discount_percent <= 100):
            return JsonResponse({"error": "Discount must be 0–100"}, status=400)

        try:
            variant = ProductVariant.objects.select_for_update().get(
                id=variant_id, product__tenant=request.tenant
            )
        except ProductVariant.DoesNotExist:
            return JsonResponse({"error": f"Variant {variant_id} not found"}, status=404)

        if variant.current_stock < quantity:
            return JsonResponse(
                {"error": f"Insufficient stock for {variant.variant_sku} (available: {variant.current_stock})"},
                status=400,
            )

        unit_price = variant.base_price
        line_gross = unit_price * quantity
        line_discount = line_gross * (discount_percent / Decimal("100"))
        line_net = line_gross - line_discount

        subtotal_gross += line_gross
        total_discount += line_discount
        validated_items.append((variant, quantity, unit_price, line_gross, line_discount, line_net))

    flat_discount = min(flat_discount, subtotal_gross - total_discount)
    total_net = subtotal_gross - total_discount - flat_discount

    if amount_paid < total_net:
        return JsonResponse({"error": "Amount received is less than the total"}, status=400)

    # ── Pass 2: write to DB ────────────────────────────────────────────────────
    change_given = amount_paid - total_net

    sale = Sale.objects.create(
        tenant=request.tenant,
        payment_method=payment_method,
        customer_name=str(data.get("customer_name", "")).strip()[:255],
        attendant=request.user.username,
        location=location,
        notes=str(data.get("notes", "")).strip()[:1000],
        subtotal_gross=subtotal_gross,
        total_discount=total_discount,
        flat_discount=flat_discount,
        total_net=total_net,
        amount_paid=amount_paid,
        change_given=change_given,
    )

    for variant, quantity, unit_price, line_gross, line_discount, line_net in validated_items:
        SaleItem.objects.create(
            sale=sale,
            product_variant=variant,
            quantity=quantity,
            base_unit_price=unit_price,
            line_gross_total=line_gross,
            line_discount_total=line_discount,
            line_net_total=line_net,
        )
        variant.current_stock -= quantity
        variant.save()

    return JsonResponse({
        "sale_id": sale.id,
        "subtotal": float(subtotal_gross),
        "discount_total": float(total_discount),
        "flat_discount": float(flat_discount),
        "total": float(total_net),
        "amount_paid": float(amount_paid),
        "change": float(change_given),
        "payment_method": payment_method,
    })


# ── API: Sales history  GET /<tenant>/api/sales ───────────────────────────────
@_staff_required
def sales_history(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    qs = Sale.objects.filter(tenant=request.tenant).prefetch_related(
        "items__product_variant__product"
    ).order_by("-created_at")

    try:
        date_from = _parse_date(request.GET.get("from"), "from")
        date_to = _parse_date(request.GET.get("to"), "to")
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    product_filter = request.GET.get("product", "").strip()
    if product_filter:
        qs = qs.filter(
            Q(items__product_variant__product__name__icontains=product_filter) |
            Q(items__product_variant__variant_sku__icontains=product_filter)
        ).distinct()

    # Compute accurate totals from the full queryset before slicing
    totals = qs.aggregate(total_revenue=Sum("total_net"), total_count=Count("id"))
    full_count = totals["total_count"] or 0
    full_revenue = float(totals["total_revenue"] or 0)

    sales = []
    for sale in qs[:500]:
        items = [
            {
                "product_name": si.product_variant.product.name,
                "sku": si.product_variant.variant_sku,
                "size": si.product_variant.size,
                "color": si.product_variant.color,
                "quantity": si.quantity,
                "unit_price": float(si.base_unit_price),
                "discount": float(si.line_discount_total),
                "line_total": float(si.line_net_total),
            }
            for si in sale.items.all()
        ]
        sales.append({
            "id": sale.id,
            "created_at": localtime(sale.created_at).strftime("%Y-%m-%d %H:%M"),
            "payment_method": sale.payment_method,
            "customer_name": sale.customer_name,
            "attendant": sale.attendant,
            "location": sale.location,
            "subtotal": float(sale.subtotal_gross),
            "discount": float(sale.total_discount),
            "flat_discount": float(sale.flat_discount),
            "total": float(sale.total_net),
            "amount_paid": float(sale.amount_paid),
            "change": float(sale.change_given),
            "items": items,
            "can_void": True,
        })

    return JsonResponse({
        "sales": sales,
        "summary": {
            "total_sales": full_count,
            "total_revenue": round(full_revenue, 2),
            "showing": len(sales),
        },
    })


# ── API: Void sale  DELETE /<tenant>/api/sales/<id> ──────────────────────────
@_staff_required
@transaction.atomic
def void_sale(request, sale_id, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    if request.method != "DELETE":
        return JsonResponse({"error": "DELETE required"}, status=405)

    sale = get_object_or_404(Sale, id=sale_id, tenant=request.tenant)

    from .models import StockAdjustment
    # Restore stock and log each item as an adjustment
    for item in sale.items.select_related("product_variant"):
        variant = ProductVariant.objects.select_for_update().get(pk=item.product_variant_id)
        variant.current_stock += item.quantity
        variant.save()
        StockAdjustment.objects.create(
            product_variant=variant,
            quantity=item.quantity,
            reason="Voided",
            notes=f"Sale #{sale.id} voided",
        )

    sale.delete()
    return JsonResponse({"ok": True})


# ── API: Export CSV  GET /<tenant>/api/sales/export ───────────────────────────
@_staff_required
def export_csv(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    try:
        date_from = _parse_date(request.GET.get("from"), "from")
        date_to = _parse_date(request.GET.get("to"), "to")
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    qs = Sale.objects.filter(tenant=request.tenant).prefetch_related(
        "items__product_variant__product"
    ).order_by("-created_at")
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    from django.db.models import Sum, Count as DCount
    summary = qs.aggregate(total_rev=Sum("total_net"), count=DCount("id"))
    total_revenue = float(summary["total_rev"] or 0)
    sale_count = summary["count"] or 0

    now_local = localtime(tz_now())
    tenant_slug = request.tenant.subdomain

    if date_from and date_to:
        period_label = f"{date_from.strftime('%d-%m-%Y')} a {date_to.strftime('%d-%m-%Y')}"
        period_slug = f"{date_from.strftime('%d-%m-%Y')}_a_{date_to.strftime('%d-%m-%Y')}"
    elif date_from:
        period_label = f"desde {date_from.strftime('%d-%m-%Y')}"
        period_slug = f"desde_{date_from.strftime('%d-%m-%Y')}"
    elif date_to:
        period_label = f"ate {date_to.strftime('%d-%m-%Y')}"
        period_slug = f"ate_{date_to.strftime('%d-%m-%Y')}"
    else:
        period_label = "Todos os registos"
        period_slug = now_local.strftime('%d-%m-%Y')

    filename = f"relatorio_vendas_{tenant_slug}_{period_slug}.csv"

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # BOM for Excel UTF-8

    writer = csv.writer(response)

    # Metadata header block
    writer.writerow(["Relatório de Vendas"])
    writer.writerow(["Loja:", request.tenant.name, "", "Período:", period_label])
    writer.writerow(["Gerado em:", now_local.strftime("%d-%m-%Y %H:%M")])
    writer.writerow([])

    # Column headers - date in DD-MM-YYYY so Excel does not auto-convert it
    writer.writerow([
        "Venda #", "Data", "Produto", "Tamanho", "Cor", "SKU",
        "Qtd", "Preço Unit. (MZN)", "Total Item (MZN)", "Total Venda (MZN)",
        "Pagamento", "Local", "Atendente", "Cliente",
    ])

    for sale in qs:
        for si in sale.items.all():
            writer.writerow([
                sale.id,
                localtime(sale.created_at).strftime("%d-%m-%Y %H:%M"),
                si.product_variant.product.name,
                si.product_variant.size or "",
                si.product_variant.color or "",
                si.product_variant.variant_sku,
                si.quantity,
                f"{float(si.base_unit_price):.2f}",
                f"{float(si.line_net_total):.2f}",
                f"{float(sale.total_net):.2f}",
                sale.payment_method,
                sale.location or "Loja",
                sale.attendant,
                sale.customer_name,
            ])

    # Summary footer
    writer.writerow([])
    writer.writerow(["Total de vendas:", sale_count])
    writer.writerow(["Receita total (MZN):", f"{total_revenue:.2f}"])

    return response


# ── Pages ─────────────────────────────────────────────────────────────────────
@boss_required
def page_dashboard(request, **kwargs):
    _require_tenant(request)
    return render(request, "pos/dashboard.html")

@boss_required
def page_catalogue(request, **kwargs):
    _require_tenant(request)
    return render(request, "pos/catalogue.html")

@boss_required
def page_history(request, **kwargs):
    _require_tenant(request)
    return render(request, "pos/history.html")

@boss_required
def page_restock(request, **kwargs):
    _require_tenant(request)
    return render(request, "pos/restock.html")

@boss_required
def page_adjustments(request, **kwargs):
    _require_tenant(request)
    return render(request, "pos/adjustments.html")

@boss_required
def page_employees(request, **kwargs):
    import secrets
    import re
    from .models import UserProfile
    _require_tenant(request)

    error = None
    success = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            username = request.POST.get("username", "").strip().lower()
            full_name = request.POST.get("full_name", "").strip()
            password = request.POST.get("password", "").strip()
            if not username:
                error = "Nome de utilizador é obrigatório."
            elif not re.match(r'^[a-z0-9_]+$', username):
                error = "Utilizador só pode conter letras minúsculas, números e _."
            elif not password or len(password) < 4:
                error = "Senha deve ter pelo menos 4 caracteres."
            elif User.objects.filter(username=username).exists():
                error = f"Utilizador '{username}' já existe."
            else:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=full_name,
                    is_staff=False,
                )
                user.userprofile.tenant = request.tenant
                user.userprofile.temp_password = password
                user.userprofile.save()
                success = {"username": username, "password": password}

        elif action == "reset":
            username = request.POST.get("username", "").strip()
            new_password = request.POST.get("new_password", "").strip()
            if not new_password or len(new_password) < 4:
                error = "Senha deve ter pelo menos 4 caracteres."
            else:
                try:
                    user = User.objects.get(username=username, userprofile__tenant=request.tenant)
                    user.set_password(new_password)
                    user.save()
                    user.userprofile.must_change_password = False
                    user.userprofile.temp_password = new_password
                    user.userprofile.save()
                    success = {"username": username, "password": new_password, "reset": True}
                except User.DoesNotExist:
                    error = "Funcionário não encontrado."

        elif action == "delete":
            username = request.POST.get("username", "").strip()
            try:
                user = User.objects.get(username=username, userprofile__tenant=request.tenant, is_staff=False)
                user.delete()
            except User.DoesNotExist:
                error = "Funcionário não encontrado."

    # List all non-staff users for this tenant
    employees = User.objects.filter(
        userprofile__tenant=request.tenant, is_staff=False
    ).select_related("userprofile").order_by("username")

    return render(request, "pos/employees.html", {
        "employees": employees,
        "error": error,
        "success": success,
    })

def page_sale(request, **kwargs):
    _require_tenant(request)
    return render(request, "pos/sale.html")

def page_availability(request, **kwargs):
    _require_tenant(request)
    return render(request, "pos/availability.html")

def page_search(request, **kwargs):
    _require_tenant(request)
    return render(request, "pos/search.html")


# ── API: Save stock adjustment  POST /<tenant>/api/adjustments ───────────────
@_staff_required
@_ratelimit_api('60/m')
@transaction.atomic
def save_adjustments(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = _json(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    items = data.get("items", [])
    if not items:
        return JsonResponse({"error": "No items"}, status=400)

    from .models import StockAdjustment
    valid_reasons = {"Damage", "Loss", "Theft", "Other", "Restock"}
    saved = 0

    for item in items:
        try:
            variant = ProductVariant.objects.select_for_update().get(
                id=int(item["variant_id"]), product__tenant=request.tenant
            )
        except (ProductVariant.DoesNotExist, KeyError, ValueError, TypeError):
            continue

        try:
            qty_removed = int(item["quantity"])
        except (ValueError, TypeError):
            continue

        reason = str(item.get("reason", "Outro"))
        if reason not in valid_reasons:
            reason = "Outro"
        notes = str(item.get("notes", "")).strip()[:1000]

        new_stock = max(0, variant.current_stock - qty_removed)
        variant.current_stock = new_stock
        variant.save()

        StockAdjustment.objects.create(
            product_variant=variant,
            quantity=-qty_removed,
            reason=reason,
            notes=notes,
        )
        saved += 1

    return JsonResponse({"ok": True, "saved": saved})


# ── API: Restock  POST /<tenant>/api/restock ──────────────────────────────────
@_staff_required
@_ratelimit_api('60/m')
@transaction.atomic
def api_restock(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = _json(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    items = data.get("items", [])
    if not items:
        return JsonResponse({"error": "No items"}, status=400)

    from .models import StockAdjustment
    saved = 0

    for item in items:
        try:
            variant = ProductVariant.objects.select_for_update().get(
                id=int(item["variant_id"]), product__tenant=request.tenant, is_active=True
            )
        except (ProductVariant.DoesNotExist, KeyError, ValueError, TypeError):
            continue

        try:
            qty = max(1, int(item["quantity"]))
        except (ValueError, TypeError, KeyError):
            continue

        variant.current_stock += qty
        variant.save()

        StockAdjustment.objects.create(
            product_variant=variant,
            quantity=qty,
            reason="Restocked",
            notes="",
        )
        saved += 1

    return JsonResponse({"ok": True, "saved": saved})


# ── API: Stock adjustment history  GET /<tenant>/api/adjustments/history ──────
@_staff_required
def adjustment_history(request, **kwargs):
    err = _require_tenant(request)
    if err:
        return err

    from .models import StockAdjustment
    qs = StockAdjustment.objects.select_related(
        "product_variant__product"
    ).filter(
        product_variant__product__tenant=request.tenant
    ).order_by("-created_at")

    try:
        date_from = _parse_date(request.GET.get("from"), "from")
        date_to = _parse_date(request.GET.get("to"), "to")
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    reason = request.GET.get("reason")

    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if reason:
        qs = qs.filter(reason=reason)

    from django.db.models import Sum, Count, Q as DQ
    stats = qs.aggregate(
        total_count=Count("id"),
        total_removed=Sum("quantity", filter=DQ(quantity__lt=0)),
        total_added=Sum("quantity", filter=DQ(quantity__gt=0)),
    )

    data = [
        {
            "id": a.id,
            "date": localtime(a.created_at).strftime("%Y-%m-%d %H:%M"),
            "product_name": a.product_variant.product.name,
            "sku": a.product_variant.variant_sku,
            "size": a.product_variant.size,
            "color": a.product_variant.color,
            "quantity": a.quantity,
            "reason": a.reason,
            "notes": a.notes,
        }
        for a in qs[:500]
    ]

    return JsonResponse({
        "results": data,
        "total": stats["total_count"] or 0,
        "showing": len(data),
        "total_removed": abs(stats["total_removed"] or 0),
        "total_added": stats["total_added"] or 0,
    })
