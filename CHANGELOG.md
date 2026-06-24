# Changelog

All notable changes to **SGI — Smart Management Interface** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and the
project aims to follow [Semantic Versioning](https://semver.org/).

🔗 **[Live demo](https://pos-sdb.up.railway.app/demo/)** — no login required, opens directly as a demo store.

---

## [1.2.0] — 2026-06-24

A performance and visibility pass: streaming CSV export, leaner ORM queries, a full
UI/UX redesign across all templates, and a new catalogue-audit trail that records every
price change, stock reset, rename, and deletion.

### Highlights

- 📋 **Catalogue change log** — every edit to a product variant (price, stock, name, category, deletion) is now recorded and browsable in a new tab on the Adjustments page.
- 🔑 **Forced password change** — new employees are redirected to a secure change-password page on first login.
- ⚡ **Memory-safe CSV export** — large export jobs no longer buffer all rows in RAM.
- 🎨 **Full UI/UX redesign** — all 9 templates rebuilt with CSS variable theming, Lucide icons, and consistent skeleton loaders.

### Added

- **`CatalogueChangeLog` model (migration `0018`).** Stores an immutable record for each
  field change on a `ProductVariant`: action type (`Preço alterado`, `Stock definido`,
  `Nome alterado`, `Categoria alterada`, `Artigo eliminado`), old and new values, the
  acting user, and a timestamp. Scoped per tenant.
- **Catalogue history API (`/api/catalogue/history`).** Filterable by date range and
  action type. Drives the new "Alterações de Catálogo" tab on the Adjustments page.
- **Automatic audit logging in `update_variant`.** Every PATCH and DELETE call now
  creates the appropriate `CatalogueChangeLog` entries — no manual step required from
  the operator.
- **`change_password` view and template.** A standalone dark-themed page that validates
  the new password against Django's built-in `validate_password`, clears the
  `must_change_password` flag on the user's profile, and keeps the session alive via
  `update_session_auth_hash`.
- **"Alterações de Catálogo" tab** on the Adjustments page. Shows catalogue edits in a
  filterable table with KPI cards (total changes, price edits, deletions, active editors).
- **Truncation notice on Sales History.** When there are more than 50 results, a banner
  indicates how many are shown and prompts the user to narrow the date range.

### Changed

- **Full template redesign (all 9 pages).** Every template was rebuilt to use
  `var(--primary)` CSS variables for theming, the `.skel` skeleton-loader class
  (consistent animation, `color: transparent` to hide text during load), Lucide icons
  via `data-lucide` attributes, and Portuguese copy aligned with the production system.
  Pages affected: `dashboard`, `sale`, `catalogue`, `availability`, `history`, `restock`,
  `adjustments`, `employees`, `change_password`.
- **Dashboard layout.** Switched from a single wide revenue card to four individual KPI
  cards (revenue, orders, avg. ticket, best payment method) in a bento grid alongside
  the charts and low-stock alert panel.
- **Adjustments page.** Previously showed only the stock-adjustment log. Now has two tabs —
  stock adjustments and the new catalogue change log — each with their own KPI row and
  filterable table.
- **Sales history ORM limit.** Reduced from 500 to 50 rows per request. The summary now
  carries `total_sales` and `showing` so the UI can display the truncation notice.
- **Username validation regex.** Broadened from `[a-z0-9_]+` to `[a-z0-9_.@+-]+` so
  usernames like `maria.silva` are accepted without error.

### Performance

- **Streaming CSV export.** Replaced the eager `HttpResponse` (which loaded all
  `SaleItem` rows into memory) with a `StreamingHttpResponse` generator using an `Echo`
  pseudo-buffer. Rows are written and flushed one at a time, keeping memory flat
  regardless of export size.
- **Sales history — leaner ORM.** Added `.only(...)` to the `Sale` queryset to fetch
  only the 12 columns needed by the history page, and replaced `prefetch_related(
  "items__product_variant__product")` with an explicit `Prefetch` object using
  `select_related` — cutting the number of columns fetched and avoiding repeated
  per-variant lookups.
- **`create_sale` — `bulk_update`.** Stock deduction on checkout now accumulates
  variant objects into a list and calls a single `ProductVariant.objects.bulk_update(
  variants_to_update, ["current_stock"])` instead of one `save()` per line item.
- **Adjustment history — offset pagination.** The `/api/adjustments` endpoint now
  accepts an `offset` query parameter so clients can page through large logs without
  re-fetching earlier rows.

---

## [1.1.0] — 2026-06-08

A production-readiness pass: a full UI overhaul, complete mobile support, a safety
net against cross-store data leaks, and performance and cost work on the database
layer.

### Highlights

- 🛡️ **Tenant-isolation guard** that catches cross-store data leaks before they ship.
- 📱 **Full mobile support** via a responsive, slide-in sidebar.
- ✨ **UI overhaul** — a neutral, professional palette, Lucide icons, skeleton loaders, toasts, and a frosted-glass top bar.
- ⚡ **Faster and cheaper** — targeted database indexes plus PostgreSQL connection reuse.

### Security

- **Tenant-isolation guard.** An automated check flags any Django queryset against a
  store-scoped model that isn't filtered to the current store, catching accidental
  cross-tenant data leaks before they reach production. It's implemented as a
  Claude Code `PostToolUse` hook that runs on every file edit, so the check happens
  at authoring time rather than in review; an inline `# noqa: tenant-scope` comment
  opts out lookups that are known to be safe.

### Added

- **Skeleton loading states.** Dashboard KPI values, catalogue table rows, and
  sales-history stat and sale cards now show an animated shimmer while data is being
  fetched, replacing the abrupt jump from blank to content.
- **Global toast notifications.** A reusable `showToast()` helper and toast element
  live in the base template and are available on every page.
- **Responsive mobile navigation.** Below 768px the sidebar slides off-canvas; a
  hamburger button in the top bar brings it back, a semi-transparent overlay closes
  it on tap, and navigating auto-closes the drawer. Main content runs full-width on
  mobile.

### Changed

- **Icons → Lucide.** Replaced ad-hoc emoji icons across all 15 templates with a
  consistent Lucide vector set. Emoji that still read best as a glyph — the store
  marker and payment-method icons — were kept.
- **Ranking indicators → Lucide.** The dashboard's top-products widget swapped its
  medal emoji (🥇🥈🥉…) for Lucide `hash` icons paired with a muted rank number,
  bringing it in line with the rest of the icon system.
- **Neutral colour palette for data.** Removed decorative colour-coding from data
  values across the dashboard, catalogue, inventory, restock, and history. Financial
  figures, stock counts, and employee revenue now render in neutral grays, with
  status carried by small coloured dot indicators rather than coloured text — cleaner
  and more readable without losing the signal.
- **Stock status dots.** Stock tables (catalogue, inventory, restock) now show a
  small 8px coloured dot beside the value instead of tinted rows or coloured text:
  red for out of stock, amber for low stock (≤5 units), and none for healthy stock.
  The row tinting (`bg-red-50`, `bg-yellow-50`) was removed from all tables.
- **Notifications → toasts.** Replaced blocking `alert()` dialogs in the sale,
  catalogue, and history pages with non-blocking toasts (green for success, amber
  for validation, red for errors), and removed a duplicate implementation in restock.
- **Sidebar active state.** Now a left-border accent instead of a full background
  fill — subtler and more in line with modern dashboards.
- **Top bar.** A frosted-glass effect (`backdrop-filter: blur`) so page content
  blurs beneath it on scroll instead of hiding behind a solid bar.
- **Typography.** The Inter web font now actually loads across all pages (it was
  referenced in the stylesheet but never fetched).
- **Dashboard cards.** A subtle 2px hover lift with a deeper shadow for clearer
  interactive feedback.

### Performance

- **Database indexes (migration `0018`).** Three indexes targeting the heaviest
  query paths:
  - `Sale(tenant, created_at)` — dashboard monthly aggregations and every
    date-range filter on the history page.
  - `CatalogueChangeLog(tenant, created_at)` — the stock-adjustments history list.
  - `ProductVariant(is_active)` — filtered on every catalogue and inventory load.
- **PostgreSQL connection reuse (`CONN_MAX_AGE=60`).** Gunicorn workers now keep a
  database connection open for up to 60 seconds instead of opening a new one on
  every request, reducing connection overhead, per-request latency, and hosting cost.

---

## [1.0.0] — Initial public release

Core point-of-sale for multi-tenant retail:

- **Sales** with product search, cart management, per-item discounts, multiple
  payment methods, and a receipt on completion.
- **Sales history** with date and product filters, expandable details, void with
  stock rollback, and CSV export.
- **Inventory** with live in-stock / low / out-of-stock views.
- **Catalogue** for adding and editing product variants.
- **Restock** with a pending-changes summary before committing.
- **Stock adjustments** logged by reason with a full audit history.
- **Employees** with generated passwords and credential resets.
- **Analytics dashboard** built on Chart.js.

Slug-based multi-tenancy with path-prefixed stores and middleware tenant
resolution. Deployed on Railway with Gunicorn and WhiteNoise.

---

Built by [Shelton de Brito](https://github.com/Dr-SdB) · [Live demo](https://pos-sdb.up.railway.app/demo/) · MIT License
