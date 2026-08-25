from django.contrib import admin
from .models import (
    Supplier,
    StockIn,
    Customer,
    StockOut,
    Invoice,
    InvoiceItem,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "phone",
        "email",
        "created_at",
    )

    search_fields = (
        "name",
        "phone",
        "email",
    )


@admin.register(StockIn)
class StockInAdmin(admin.ModelAdmin):

    list_display = (
        "invoice_number",
        "supplier",
        "item_name",
        "quantity",
        "unit_cost",
        "total_amount",
        "date",
    )

    list_filter = (
        "date",
        "supplier",
    )

    search_fields = (
        "invoice_number",
        "item_name",
        "supplier__name",
    )

    readonly_fields = (
        "total_amount",
        "created_at",
    )


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ("total",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    list_display = (
        "invoice_number",
        "customer",
        "date",
        "grand_total",
        "paid_amount",
        "remaining_amount",
    )

    list_filter = (
        "date",
        "customer",
    )

    search_fields = (
        "invoice_number",
        "customer__name",
    )

    readonly_fields = (
        "created_at",
    )

    inlines = [InvoiceItemInline]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "phone",
        "email",
        "created_at",
    )

    search_fields = (
        "name",
        "phone",
        "email",
    )


@admin.register(StockOut)
class StockOutAdmin(admin.ModelAdmin):

    list_display = (
        "invoice_number",
        "customer",
        "item_name",
        "quantity",
        "unit_price",
        "total_amount",
        "date",
    )

    list_filter = (
        "date",
        "customer",
    )

    search_fields = (
        "invoice_number",
        "item_name",
        "customer__name",
    )

    readonly_fields = (
        "total_amount",
        "created_at",
    )