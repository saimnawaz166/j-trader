from decimal import Decimal, InvalidOperation

import openpyxl
from openpyxl.styles import Font

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.views import admin_required
from config.datatables import datatable_response

from .forms import (
    CustomerForm,
    InvoiceCreateForm,
    InvoiceEditForm,
    StockInForm,
    StockOutForm,
    SupplierForm,
)
from .models import Customer, Invoice, InvoiceItem, StockIn, StockOut, Supplier
from .numbering import next_invoice_number

PURCHASE_PREFIX = "PUR"
SALE_PREFIX = "INV"


def _first_form_error(form):
    for field_errors in form.errors.values():
        return field_errors[0]
    return "Please correct the errors below."


@login_required
def stock_in_list(request):
    return render(request, "inventory/stock_in_list.html")


def _print_invoice_button(invoice_number):
    """Small "Print Invoice" link for a Stock In/Out list row, resolved
    via the matching auto-generated Invoice's invoice_number."""

    invoice_id = Invoice.objects.filter(
        invoice_number=invoice_number
    ).values_list("id", flat=True).first()

    if not invoice_id:
        return ""

    url = reverse("invoice_print", args=[invoice_id])
    return (
        f'<a href="{url}" target="_blank" class="btn btn-secondary" '
        f'style="padding: 8px 14px; font-size: 14px;">Print Invoice</a>'
    )


@login_required
def stock_in_data(request):

    queryset = StockIn.objects.select_related("supplier").all()

    def row(stock_in):
        return {
            "invoice_number": f"<strong>{stock_in.invoice_number}</strong>",
            "date": str(stock_in.date),
            "supplier": stock_in.supplier.name,
            "item_name": stock_in.item_name,
            "quantity": stock_in.quantity,
            "unit_cost": str(stock_in.unit_cost),
            "total_amount": f"<strong>{stock_in.total_amount}</strong>",
            "actions": _print_invoice_button(stock_in.invoice_number),
        }

    return datatable_response(
        request, queryset, row,
        search_fields=["invoice_number", "item_name", "supplier__name"],
        order_fields=[
            "invoice_number", "date", "supplier__name", "item_name",
            "quantity", "unit_cost", "total_amount", None,
        ],
    )


@login_required
def stock_in_create(request):

    suppliers = Supplier.objects.all()

    if request.method == "POST":

        form = StockInForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                stock_in = form.save(commit=False)
                stock_in.invoice_number = next_invoice_number(PURCHASE_PREFIX)
                stock_in.save()

                # Automatically generate a matching purchase invoice.
                invoice = Invoice.objects.create(
                    invoice_number=stock_in.invoice_number,
                    invoice_type=Invoice.PURCHASE,
                    supplier=stock_in.supplier,
                    date=stock_in.date,
                    subtotal=stock_in.total_amount,
                    discount=Decimal("0"),
                    grand_total=stock_in.total_amount,
                    paid_amount=Decimal("0"),
                    remaining_amount=stock_in.total_amount,
                    notes=stock_in.notes,
                )

                InvoiceItem.objects.create(
                    invoice=invoice,
                    item_name=stock_in.item_name,
                    quantity=stock_in.quantity,
                    unit_price=stock_in.unit_cost,
                    total=stock_in.total_amount,
                )

            messages.success(
                request,
                f"Stock added successfully. "
                f"Invoice {stock_in.invoice_number} created."
            )

            return redirect("stock_in_list")

        messages.error(request, _first_form_error(form))

        return redirect("stock_in_create")

    context = {
        "suppliers": suppliers,
        "today": timezone.localdate(),
        "next_invoice_number": next_invoice_number(PURCHASE_PREFIX),
    }

    return render(
        request,
        "inventory/stock_in_form.html",
        context
    )


@login_required
def supplier_list(request):
    return render(request, "inventory/supplier_list.html")


@login_required
def supplier_data(request):

    queryset = Supplier.objects.all()

    def row(supplier):
        return {
            "name": f"<strong>{supplier.name}</strong>",
            "phone": supplier.phone or "-",
            "email": supplier.email or "-",
            "address": supplier.address or "-",
        }

    return datatable_response(
        request, queryset, row,
        search_fields=["name", "phone", "email", "address"],
        order_fields=["name", "phone", "email", "address"],
    )


@login_required
def supplier_create(request):

    if request.method == "POST":

        form = SupplierForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Supplier added successfully."
            )

            return redirect("supplier_list")

        messages.error(request, _first_form_error(form))

        return redirect("supplier_create")

    return render(
        request,
        "inventory/supplier_form.html"
    )


@login_required
def stock_out_list(request):
    return render(request, "inventory/stock_out_list.html")


@login_required
def stock_out_data(request):

    queryset = StockOut.objects.select_related("customer").all()

    def row(stock_out):
        return {
            "invoice_number": f"<strong>{stock_out.invoice_number}</strong>",
            "date": str(stock_out.date),
            "customer": stock_out.customer.name,
            "item_name": stock_out.item_name,
            "quantity": stock_out.quantity,
            "unit_price": str(stock_out.unit_price),
            "total_amount": f"<strong>{stock_out.total_amount}</strong>",
            "actions": _print_invoice_button(stock_out.invoice_number),
        }

    return datatable_response(
        request, queryset, row,
        search_fields=["invoice_number", "item_name", "customer__name"],
        order_fields=[
            "invoice_number", "date", "customer__name", "item_name",
            "quantity", "unit_price", "total_amount", None,
        ],
    )


@login_required
def stock_out_create(request):

    customers = Customer.objects.all()

    if request.method == "POST":

        form = StockOutForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                stock_out = form.save(commit=False)
                stock_out.invoice_number = next_invoice_number(SALE_PREFIX)
                stock_out.save()

                # Automatically generate a matching sales invoice.
                invoice = Invoice.objects.create(
                    invoice_number=stock_out.invoice_number,
                    invoice_type=Invoice.SALE,
                    customer=stock_out.customer,
                    date=stock_out.date,
                    subtotal=stock_out.total_amount,
                    discount=Decimal("0"),
                    grand_total=stock_out.total_amount,
                    paid_amount=Decimal("0"),
                    remaining_amount=stock_out.total_amount,
                    notes=stock_out.notes,
                )

                InvoiceItem.objects.create(
                    invoice=invoice,
                    item_name=stock_out.item_name,
                    quantity=stock_out.quantity,
                    unit_price=stock_out.unit_price,
                    total=stock_out.total_amount,
                )

            messages.success(
                request,
                f"Stock removed successfully. "
                f"Invoice {stock_out.invoice_number} created."
            )

            return redirect("stock_out_list")

        messages.error(request, _first_form_error(form))

        return redirect("stock_out_create")

    context = {
        "customers": customers,
        "today": timezone.localdate(),
        "next_invoice_number": next_invoice_number(SALE_PREFIX),
    }

    return render(
        request,
        "inventory/stock_out_form.html",
        context
    )


@login_required
def customer_list(request):
    return render(request, "inventory/customer_list.html")


@login_required
def customer_data(request):

    queryset = Customer.objects.all()

    def row(customer):
        return {
            "name": f"<strong>{customer.name}</strong>",
            "phone": customer.phone or "-",
            "email": customer.email or "-",
            "address": customer.address or "-",
        }

    return datatable_response(
        request, queryset, row,
        search_fields=["name", "phone", "email", "address"],
        order_fields=["name", "phone", "email", "address"],
    )


@login_required
def customer_create(request):

    if request.method == "POST":

        form = CustomerForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Customer added successfully."
            )

            return redirect("customer_list")

        messages.error(request, _first_form_error(form))

        return redirect("customer_create")

    return render(
        request,
        "inventory/customer_form.html"
    )


def _invoices_queryset(request):
    """Shared query logic used by the Excel export - matches the same
    `search` GET param the Invoices page's DataTable forwards to it."""

    invoices_qs = Invoice.objects.select_related("customer", "supplier").all()

    search = request.GET.get("search", "").strip()

    if search:
        invoices_qs = invoices_qs.filter(
            Q(invoice_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(supplier__name__icontains=search)
        )

    return invoices_qs, search


@login_required
def invoices(request):
    return render(request, "inventory/invoices.html")


@login_required
def invoices_data(request):

    queryset = Invoice.objects.select_related("customer", "supplier").all()

    can_edit = request.user.is_superuser

    def row(invoice):
        if invoice.invoice_type == Invoice.PURCHASE:
            type_html = '<span class="badge badge-purchase">Purchase</span>'
        else:
            type_html = '<span class="badge badge-sale">Sale</span>'

        edit_link = (
            f'<a href="{reverse("edit_invoice", args=[invoice.id])}" '
            f'class="btn btn-secondary">Edit</a> '
        ) if can_edit else ""

        actions = (
            f'{edit_link}'
            f'<a href="{reverse("invoice_print", args=[invoice.id])}" '
            f'target="_blank" class="btn btn-secondary">Print</a>'
        )

        return {
            "invoice_number": f"<strong>{invoice.invoice_number}</strong>",
            "invoice_type": type_html,
            "date": invoice.date.strftime("%b %d, %Y"),
            "party": invoice.party.name if invoice.party else "",
            "subtotal": f"{invoice.subtotal:.2f}",
            "discount": f"{invoice.discount:.2f}",
            "grand_total": f"<strong>{invoice.grand_total:.2f}</strong>",
            "paid_amount": f"{invoice.paid_amount:.2f}",
            "remaining_amount": f"{invoice.remaining_amount:.2f}",
            "actions": actions,
        }

    return datatable_response(
        request, queryset, row,
        search_fields=["invoice_number", "customer__name", "supplier__name"],
        order_fields=[
            "invoice_number", None, "date", None, "subtotal",
            "discount", "grand_total", "paid_amount", "remaining_amount", None,
        ],
    )


@login_required
def invoices_export(request):

    invoices_qs, _search = _invoices_queryset(request)

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Invoices"

    headers = [
        "Invoice #", "Type", "Date", "Party", "Subtotal",
        "Discount", "Grand Total", "Paid", "Remaining",
    ]
    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for invoice in invoices_qs:
        sheet.append([
            invoice.invoice_number,
            invoice.get_invoice_type_display(),
            invoice.date.strftime("%Y-%m-%d"),
            invoice.party.name if invoice.party else "",
            float(invoice.subtotal),
            float(invoice.discount),
            float(invoice.grand_total),
            float(invoice.paid_amount),
            float(invoice.remaining_amount),
        ])

    for column_cells in sheet.columns:
        length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = length + 4

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        )
    )
    filename = f"invoices_{timezone.localdate():%Y%m%d}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    workbook.save(response)

    return response


@login_required
def invoice_print(request, pk):

    invoice = get_object_or_404(
        Invoice.objects.select_related("customer", "supplier"),
        pk=pk
    )

    items = invoice.items.all()

    context = {
        "invoice": invoice,
        "items": items,
        "business_name": "J. Gold Traders",
        "business_address": "Your Business Address, City",
        "business_phone": "",
        "business_email": "",
    }

    return render(request, "inventory/invoice_print.html", context)


@login_required
@admin_required
def edit_invoice(request, pk):

    invoice = get_object_or_404(
        Invoice.objects.select_related("customer", "supplier"),
        pk=pk
    )

    items = invoice.items.all()
    is_purchase = invoice.invoice_type == Invoice.PURCHASE
    parties = Supplier.objects.all() if is_purchase else Customer.objects.all()

    if request.method == "POST":

        form = InvoiceEditForm(request.POST, invoice=invoice)

        if form.is_valid():

            form.apply_to(invoice)
            invoice.save()

            messages.success(
                request,
                f"Invoice {invoice.invoice_number} updated successfully."
            )

            return redirect("invoices")

        messages.error(request, _first_form_error(form))

        return redirect("edit_invoice", pk=pk)

    context = {
        "invoice": invoice,
        "is_purchase": is_purchase,
        "parties": parties,
        "items": items,
    }

    return render(
        request,
        "inventory/edit_invoice.html",
        context
    )


def _build_invoice_line_items(item_names, quantities, prices):
    """Validate a new invoice's line items.

    Returns (items, subtotal) where items is a list of dicts ready to
    become InvoiceItem rows. Raises ValueError with a user-facing message
    on any problem (missing name, bad quantity/price, etc).
    """

    subtotal = Decimal("0")
    items = []

    for item_name, quantity, price in zip(item_names, quantities, prices):

        item_name = (item_name or "").strip()

        if not item_name or not quantity:
            continue

        try:
            quantity = int(quantity)
            price = Decimal(price)
        except (ValueError, InvalidOperation):
            raise ValueError("Invalid quantity or price.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        if price < 0:
            raise ValueError("Price can't be negative.")

        line_total = quantity * price
        subtotal += line_total

        items.append({
            "item_name": item_name,
            "quantity": quantity,
            "price": price,
            "total": line_total,
        })

    if not items:
        raise ValueError("Add at least one item to the invoice.")

    return items, subtotal


@login_required
def add_invoice(request):

    customers = Customer.objects.all()

    if request.method == "POST":

        form = InvoiceCreateForm(request.POST)

        item_names = request.POST.getlist("item_name")
        quantities = request.POST.getlist("quantity")
        prices = request.POST.getlist("price")

        if form.is_valid():

            try:
                with transaction.atomic():

                    items, subtotal = _build_invoice_line_items(
                        item_names, quantities, prices
                    )

                    discount = form.cleaned_data["discount"]
                    paid_amount = form.cleaned_data["paid_amount"]

                    grand_total = max(subtotal - discount, Decimal("0"))
                    remaining_amount = max(
                        grand_total - paid_amount, Decimal("0")
                    )

                    invoice = Invoice.objects.create(
                        invoice_number=form.cleaned_data["invoice_number"],
                        invoice_type=Invoice.SALE,
                        customer=form.cleaned_data["customer"],
                        date=timezone.localdate(),
                        subtotal=subtotal,
                        discount=discount,
                        grand_total=grand_total,
                        paid_amount=paid_amount,
                        remaining_amount=remaining_amount,
                        notes=form.cleaned_data["notes"],
                    )

                    for item in items:

                        InvoiceItem.objects.create(
                            invoice=invoice,
                            item_name=item["item_name"],
                            quantity=item["quantity"],
                            unit_price=item["price"],
                            total=item["total"],
                        )

                messages.success(
                    request,
                    f"Invoice {invoice.invoice_number} created successfully."
                )

                return redirect("invoices")

            except ValueError as exc:
                messages.error(request, str(exc))

        else:
            messages.error(request, _first_form_error(form))

    context = {
        "customers": customers,
    }

    return render(
        request,
        "inventory/add_invoice.html",
        context
    )
