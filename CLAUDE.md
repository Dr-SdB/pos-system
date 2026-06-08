# SGI — Development Guide

## Multi-tenancy

Slug/path-based multi-tenancy. Every URL is prefixed with the tenant slug:
`/<subdomain>/sale/`, `/<subdomain>/api/dashboard`, etc.

**Resolution:** `TenantMiddleware` in `pos/middleware.py` strips the first path
segment, looks up `Tenant.objects.get(subdomain=slug, is_active=True)`, and
attaches the result to `request.tenant`.

### Tenant model

`pos.models.Tenant` — slug field is `subdomain`.

### Store FK field name

All store-scoped models use the field name **`tenant`** (ForeignKey → `Tenant`).

### Scoping patterns

Every queryset that reads store data must be filtered to `request.tenant`.
The exact pattern depends on how far the FK chain is from `Tenant`:

| Model | Required filter argument |
|---|---|
| `Sale` | `tenant=request.tenant` |
| `Product` | `tenant=request.tenant` |
| `UserProfile` | `tenant=request.tenant` |
| `ProductVariant` | `product__tenant=request.tenant` *(no direct FK — hops through Product)* |
| `StockAdjustment` | `product_variant__product__tenant=request.tenant` *(two hops)* |

### Tenant-isolation guard

A `PostToolUse` Claude Code hook at `.claude/hooks/check_tenant_scope.py` warns
when a Python file edit introduces a queryset on a store-scoped model without the
correct tenant filter. The hook fires on every `Edit` or `Write` of a `.py` file,
skips migrations and management commands, and exits 1 (visible warning) if an
issue is found.

Opt out on a specific line when the scope is already guaranteed by context:

```python
variant = ProductVariant.objects.select_for_update().get(pk=pk)  # noqa: tenant-scope
```
