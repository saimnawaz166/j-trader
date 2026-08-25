from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Customer, Invoice, StockIn, StockOut, Supplier


ZERO = Decimal("0")


def clamp_non_negative(value):
    return value if value > ZERO else ZERO


class SupplierForm(forms.ModelForm):

    class Meta:
        model = Supplier
        fields = ["name", "phone", "email", "address"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise ValidationError("Supplier name is required.")

        return name


class CustomerForm(forms.ModelForm):

    class Meta:
        model = Customer
        fields = ["name", "phone", "email", "address"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise ValidationError("Customer name is required.")

        return name


class StockInForm(forms.ModelForm):
    """`invoice_number` is deliberately excluded - it's auto-generated
    (see `inventory.numbering.next_invoice_number`) and assigned by the
    view right before saving, not entered by the user."""

    class Meta:
        model = StockIn
        fields = [
            "supplier",
            "item_name",
            "quantity",
            "unit_cost",
            "date",
            "notes",
        ]

    def clean_item_name(self):
        item_name = self.cleaned_data["item_name"].strip()

        if not item_name:
            raise ValidationError("Item name is required.")

        return item_name

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        return quantity

    def clean_unit_cost(self):
        unit_cost = self.cleaned_data["unit_cost"]

        if unit_cost < 0:
            raise ValidationError("Unit cost can't be negative.")

        return unit_cost

    def save(self, commit=True):
        stock_in = super().save(commit=False)
        stock_in.total_amount = stock_in.quantity * stock_in.unit_cost

        if commit:
            stock_in.save()

        return stock_in


class StockOutForm(forms.ModelForm):
    """`invoice_number` is deliberately excluded - it's auto-generated
    (see `inventory.numbering.next_invoice_number`) and assigned by the
    view right before saving, not entered by the user."""

    class Meta:
        model = StockOut
        fields = [
            "customer",
            "item_name",
            "quantity",
            "unit_price",
            "date",
            "notes",
        ]

    def clean_item_name(self):
        item_name = self.cleaned_data["item_name"].strip()

        if not item_name:
            raise ValidationError("Item name is required.")

        return item_name

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data["unit_price"]

        if unit_price < 0:
            raise ValidationError("Sale price can't be negative.")

        return unit_price

    def save(self, commit=True):
        stock_out = super().save(commit=False)
        stock_out.total_amount = stock_out.quantity * stock_out.unit_price

        if commit:
            stock_out.save()

        return stock_out


class InvoiceCreateForm(forms.Form):
    """Header fields for a new, manually-built sales invoice.

    Line items (item name/quantity/price) arrive as parallel POST lists and
    are validated separately in the view, since they're a dynamic set of
    rows rather than a fixed set of form fields.
    """

    invoice_number = forms.CharField(max_length=100)
    customer = forms.ModelChoiceField(queryset=Customer.objects.all())
    discount = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=ZERO
    )
    paid_amount = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=ZERO
    )
    notes = forms.CharField(required=False, widget=forms.Textarea)

    def clean_invoice_number(self):
        invoice_number = self.cleaned_data["invoice_number"].strip()

        if Invoice.objects.filter(invoice_number=invoice_number).exists():
            raise ValidationError("Invoice number already exists.")

        return invoice_number

    def clean_discount(self):
        return self.cleaned_data.get("discount") or ZERO

    def clean_paid_amount(self):
        return self.cleaned_data.get("paid_amount") or ZERO


class InvoiceEditForm(forms.Form):
    """Header fields for an existing invoice.

    Line items can't be edited here (this matches what happened at
    creation), so only invoice-level fields are exposed. The "party" field
    is the customer for a Sale invoice or the supplier for a Purchase
    invoice - which one is decided by the `invoice` passed in.
    """

    invoice_number = forms.CharField(max_length=100)
    party = forms.ModelChoiceField(queryset=Customer.objects.none())
    date = forms.DateField()
    discount = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=ZERO
    )
    paid_amount = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=ZERO
    )
    notes = forms.CharField(required=False, widget=forms.Textarea)

    def __init__(self, *args, invoice=None, **kwargs):
        self.invoice = invoice
        super().__init__(*args, **kwargs)

        if invoice is not None and invoice.invoice_type == Invoice.PURCHASE:
            self.fields["party"].queryset = Supplier.objects.all()
            self.fields["party"].label = "Supplier"
        else:
            self.fields["party"].queryset = Customer.objects.all()
            self.fields["party"].label = "Customer"

    def clean_invoice_number(self):
        invoice_number = self.cleaned_data["invoice_number"].strip()

        conflict = Invoice.objects.filter(invoice_number=invoice_number)

        if self.invoice is not None:
            conflict = conflict.exclude(pk=self.invoice.pk)

        if conflict.exists():
            raise ValidationError("That invoice number is already in use.")

        return invoice_number

    def clean_discount(self):
        return self.cleaned_data.get("discount") or ZERO

    def clean_paid_amount(self):
        return self.cleaned_data.get("paid_amount") or ZERO

    def apply_to(self, invoice):
        """Update `invoice` in-place from cleaned data and recompute totals
        from its existing subtotal (line items aren't editable here)."""

        invoice.invoice_number = self.cleaned_data["invoice_number"]
        invoice.date = self.cleaned_data["date"]
        invoice.discount = self.cleaned_data["discount"]
        invoice.notes = self.cleaned_data["notes"]

        if invoice.invoice_type == Invoice.PURCHASE:
            invoice.supplier = self.cleaned_data["party"]
        else:
            invoice.customer = self.cleaned_data["party"]

        invoice.grand_total = clamp_non_negative(
            invoice.subtotal - invoice.discount
        )
        invoice.paid_amount = self.cleaned_data["paid_amount"]
        invoice.remaining_amount = clamp_non_negative(
            invoice.grand_total - invoice.paid_amount
        )

        return invoice
