from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Customer, Invoice, StockIn, StockOut, Supplier

TEST_PUR_PREFIX = "TESTPUR"
TEST_INV_PREFIX = "TESTINV"
TEST_PARTY_PREFIX = "TEST "


class Command(BaseCommand):
    help = (
        "Remove all fake data created by `manage.py seed_fake_data`. "
        "Only removes records tagged with the TESTPUR/TESTINV invoice "
        "prefixes and 'TEST '-prefixed supplier/customer names - real "
        "data is never touched."
    )

    def handle(self, *args, **options):

        with transaction.atomic():

            stock_in_qs = StockIn.objects.filter(invoice_number__startswith=TEST_PUR_PREFIX)
            stock_out_qs = StockOut.objects.filter(invoice_number__startswith=TEST_INV_PREFIX)
            invoice_qs = Invoice.objects.filter(
                invoice_number__startswith=TEST_PUR_PREFIX
            ) | Invoice.objects.filter(invoice_number__startswith=TEST_INV_PREFIX)
            supplier_qs = Supplier.objects.filter(name__startswith=TEST_PARTY_PREFIX)
            customer_qs = Customer.objects.filter(name__startswith=TEST_PARTY_PREFIX)

            # Counted before delete() - its return value also counts
            # cascade-deleted InvoiceItem rows, which would be misleading here.
            stock_in_count = stock_in_qs.count()
            stock_out_count = stock_out_qs.count()
            invoice_count = invoice_qs.count()
            supplier_count = supplier_qs.count()
            customer_count = customer_qs.count()

            stock_in_qs.delete()
            stock_out_qs.delete()
            invoice_qs.delete()
            supplier_qs.delete()
            customer_qs.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Removed {stock_in_count} Stock In, {stock_out_count} Stock Out, "
            f"{invoice_count} Invoice, {supplier_count} Supplier and "
            f"{customer_count} Customer fake test records."
        ))
