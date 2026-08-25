from django.urls import path

from . import views


urlpatterns = [
    path("", views.stock_in_list, name="stock_in_list"),
    path("data/", views.stock_in_data, name="stock_in_data"),
    path("add/", views.stock_in_create, name="stock_in_create"),

    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/data/", views.supplier_data, name="supplier_data"),
    path("suppliers/add/", views.supplier_create, name="supplier_create"),

    path("stock-out/", views.stock_out_list, name="stock_out_list"),
    path("stock-out/data/", views.stock_out_data, name="stock_out_data"),
    path("stock-out/add/", views.stock_out_create, name="stock_out_create"),

    path("customers/", views.customer_list, name="customer_list"),
    path("customers/data/", views.customer_data, name="customer_data"),
    path("customers/add/", views.customer_create, name="customer_create"),

    path("invoices/", views.invoices, name="invoices"),
    path("invoices/data/", views.invoices_data, name="invoices_data"),
    path("invoices/export/", views.invoices_export, name="invoices_export"),
    path("invoices/add/", views.add_invoice, name="add_invoice"),
    path("invoices/<int:pk>/edit/", views.edit_invoice, name="edit_invoice"),
    path("invoices/<int:pk>/print/", views.invoice_print, name="invoice_print"),
]
