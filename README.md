# SGI — Smart Management Interface

A full-stack Point of Sale system built with Django, designed for retail stores. Features a multi-tenant architecture, real-time inventory tracking, and a sales analytics dashboard.

**[Live Demo →](https://pos-sdb.up.railway.app/demo/)**
No login required — opens directly as a demo store.

---

## Features

- **Dashboard** — Monthly revenue, units sold, top employee, low stock alerts, sales by weekday, payment method breakdown, and top products — all with Chart.js visualisations
- **New Sale** — Product search, cart management, per-item discounts, multiple payment methods, and a receipt modal on completion
- **Sales History** — Full transaction log with date/product filters, expandable sale details, void with stock rollback, and CSV export
- **Inventory** — Live stock view with in-stock / low / out-of-stock filters and search
- **Catalogue** — Add and edit product variants (name, size, color, price, stock) via modal forms
- **Restock** — Bulk stock replenishment with a pending-changes summary before committing
- **Stock Adjustments** — Log stock removals by reason (Damage, Loss, Theft) with a full audit history
- **Employees** — Create staff accounts with generated passwords, reset credentials, and manage the team

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Django |
| Database | PostgreSQL (Railway) |
| Frontend | Vanilla JS, Tailwind CSS, Chart.js |
| Auth | Django Auth — multi-tenant session isolation |
| Deployment | Railway, Gunicorn, WhiteNoise |

## Architecture

The system uses a **slug-based multi-tenancy** model — each store lives under its own URL prefix (`/<store>/`). A middleware layer resolves the tenant from the path and enforces that users can only access their own store's data. A second middleware handles demo auto-login so recruiters see the full system without any setup.

All frontend interactions are API-driven (fetch + JSON) with no page reloads, keeping the UX fast and clean.

## Screenshots

| Dashboard | New Sale | Sales History |
|---|---|---|
| ![Dashboard](https://pos-sdb.up.railway.app/static/screenshots/dashboard.png) | ![Sale](https://pos-sdb.up.railway.app/static/screenshots/sale.png) | ![History](https://pos-sdb.up.railway.app/static/screenshots/history.png) |

---

Built by [Shelton de Brito](https://github.com/Dr-SdB)
