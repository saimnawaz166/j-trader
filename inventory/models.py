from django.db import models
from django.core.validators import MinValueValidator


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockIn(models.Model):
    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="stock_ins"
    )

    item_name = models.CharField(
        max_length=200
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    date = models.DateField()

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return self.invoice_number


class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockOut(models.Model):
    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="stock_outs"
    )

    item_name = models.CharField(
        max_length=200
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    date = models.DateField()

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return self.invoice_number


class Invoice(models.Model):

    SALE = "sale"
    PURCHASE = "purchase"

    TYPE_CHOICES = [
        (SALE, "Sale"),
        (PURCHASE, "Purchase"),
    ]

    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    invoice_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=SALE,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="invoices",
        null=True,
        blank=True
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="invoices",
        null=True,
        blank=True
    )

    date = models.DateField()

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    remaining_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return self.invoice_number

    @property
    def party(self):
        """The customer (sale) or supplier (purchase) this invoice is with."""
        return self.customer if self.invoice_type == self.SALE else self.supplier


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item_name = models.CharField(
        max_length=200
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.item_name}"
