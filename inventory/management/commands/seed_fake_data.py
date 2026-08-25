import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventory.models import (
    Customer, Invoice, InvoiceItem, StockIn, StockOut, Supplier,
)

# Everything this command creates is tagged so it can be found and removed
# cleanly later with `manage.py clear_fake_data` - real data is never
# touched, since real records never use this prefix.
TEST_TAG = "FAKE TEST DATA - safe to delete via `manage.py clear_fake_data`"
TEST_PUR_PREFIX = "TESTPUR"
TEST_INV_PREFIX = "TESTINV"
TEST_PARTY_PREFIX = "TEST "

ITEM_NAMES = [
    "Steel Pipe 2 inch", "PVC Pipe 4 inch", "Cement Bag 50kg",
    "Paint Bucket 20L", "Wire Roll 100m", "Nails Box 5kg",
    "Tile Box", "Wood Plank 8ft", "Glass Sheet 6mm", "Sand Bag",
]


class Command(BaseCommand):
    help = (
        "Seed the database with fake Stock In / Stock Out / Invoice "
        "records for testing (e.g. DataTables pagination with a large "
        "dataset). Everything created is clearly tagged and can be "
        "removed later with `manage.py clear_fake_data`."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=5000,
            help="Total number of Stock In + Stock Out records to create "
                 "(split evenly). Default: 5000.",
        )

    def handle(self, *args, **options):
        total = options["count"]
        half = total // 2

        today = timezone.localdate()

        with transaction.atomic():

            suppliers = [
                Supplier.objects.create(
                    name=f"{TEST_PARTY_PREFIX}Supplier {i}",
                    phone="0300-0000000",
                    address=TEST_TAG,
                )
                for i in range(1, 31)
            ]

            customers = [
                Customer.objects.create(
                    name=f"{TEST_PARTY_PREFIX}Customer {i}",
                    phone="0300-0000000",
                    address=TEST_TAG,
                )
                for i in range(1, 31)
            ]

            stock_ins = []
            purchase_invoices = []
            purchase_items = []

            for i in range(1, half + 1):
                number = f"{TEST_PUR_PREFIX}{i:07d}"
                supplier = random.choice(suppliers)
                item_name = random.choice(ITEM_NAMES)
                quantity = random.randint(1, 50)
                unit_cost = Decimal(random.randint(100, 200000)) / 100
                total_amount = quantity * unit_cost
                date = today - timedelta(days=random.randint(0, 730))

                stock_ins.append(StockIn(
                    invoice_number=number, supplier=supplier,
                    item_name=item_name, quantity=quantity,
                    unit_cost=unit_cost, total_amount=total_amount,
                    date=date, notes=TEST_TAG,
                ))
                purchase_invoices.append(Invoice(
                    invoice_number=number, invoice_type=Invoice.PURCHASE,
                    supplier=supplier, date=date, subtotal=total_amount,
                    grand_total=total_amount, remaining_amount=total_amount,
                    notes=TEST_TAG,
                ))
                purchase_items.append((number, item_name, quantity, unit_cost, total_amount))

            StockIn.objects.bulk_create(stock_ins, batch_size=1000)
            created_invoices = Invoice.objects.bulk_create(purchase_invoices, batch_size=1000)

            invoice_by_number = {inv.invoice_number: inv for inv in created_invoices}
            InvoiceItem.objects.bulk_create([
                InvoiceItem(
                    invoice=invoice_by_number[number], item_name=item_name,
                    quantity=quantity, unit_price=unit_cost, total=total_amount,
                )
                for number, item_name, quantity, unit_cost, total_amount in purchase_items
            ], batch_size=1000)

            stock_outs = []
            sale_invoices = []
            sale_items = []

            for i in range(1, (total - half) + 1):
                number = f"{TEST_INV_PREFIX}{i:07d}"
                customer = random.choice(customers)
                item_name = random.choice(ITEM_NAMES)
                quantity = random.randint(1, 50)
                unit_price = Decimal(random.randint(100, 300000)) / 100
                total_amount = quantity * unit_price
                date = today - timedelta(days=random.randint(0, 730))
                paid = random.choice([Decimal("0"), total_amount, total_amount / 2])

                stock_outs.append(StockOut(
                    invoice_number=number, customer=customer,
                    item_name=item_name, quantity=quantity,
                    unit_price=unit_price, total_amount=total_amount,
                    date=date, notes=TEST_TAG,
                ))
                sale_invoices.append(Invoice(
                    invoice_number=number, invoice_type=Invoice.SALE,
                    customer=customer, date=date, subtotal=total_amount,
                    grand_total=total_amount, paid_amount=paid,
                    remaining_amount=total_amount - paid, notes=TEST_TAG,
                ))
                sale_items.append((number, item_name, quantity, unit_price, total_amount))

            StockOut.objects.bulk_create(stock_outs, batch_size=1000)
            created_sale_invoices = Invoice.objects.bulk_create(sale_invoices, batch_size=1000)

            sale_invoice_by_number = {inv.invoice_number: inv for inv in created_sale_invoices}
            InvoiceItem.objects.bulk_create([
                InvoiceItem(
                    invoice=sale_invoice_by_number[number], item_name=item_name,
                    quantity=quantity, unit_price=unit_price, total=total_amount,
                )
                for number, item_name, quantity, unit_price, total_amount in sale_items
            ], batch_size=1000)

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(stock_ins)} fake Stock In and {len(stock_outs)} "
            f"fake Stock Out records (with matching invoices).\n"
            f"Run `manage.py clear_fake_data` to remove all of it later."
        ))
