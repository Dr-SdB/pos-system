from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from pos import views as v

tenant_urlpatterns = [
    # Pages
    path("", v.page_dashboard, name="dashboard"),
    path("catalogue/", v.page_catalogue, name="catalogue"),
    path("sale/", v.page_sale, name="sale"),
    path("availability/", v.page_availability, name="availability"),
    path("history/", v.page_history, name="history"),
    path("search/", v.page_search, name="search"),
    path("restock/", v.page_restock, name="restock"),
    path("adjustments/", v.page_adjustments, name="adjustments"),
    path("employees/", v.page_employees, name="employees"),

    # APIs
    path("api/dashboard", v.dashboard),
    path("api/products", v.product_search),
    path("api/catalogue", v.catalogue),
    path("api/catalogue/add", v.add_variant),
    path("api/catalogue/<int:variant_id>", v.update_variant),
    path("api/availability", v.stock_availability),
    path("api/sale", v.create_sale),
    path("api/sales", v.sales_history),
    path("api/sales/<int:sale_id>/void", v.void_sale),
    path("api/sales/export", v.export_csv),
    path("api/adjustments", v.save_adjustments),
    path("api/adjustments/history", v.adjustment_history),
    path("api/restock", v.api_restock),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", RedirectView.as_view(url="/admin/", permanent=False)),
    path("", v.root_redirect, name="root"),
    path("<slug:tenant_slug>/", include(tenant_urlpatterns)),
]
