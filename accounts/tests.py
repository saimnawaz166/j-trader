from django.contrib.auth.models import User
from django.test import TestCase

from expenses.models import Expense
from inventory.models import Customer, Invoice, StockIn, StockOut, Supplier


class ResetDataTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser("admin", password="pass12345")
        self.staff = User.objects.create_user("staff", password="pass12345")

        supplier = Supplier.objects.create(name="Test Supplier")
        customer = Customer.objects.create(name="Test Customer")

        StockIn.objects.create(
            invoice_number="PUR0000001", supplier=supplier,
            item_name="Item", quantity=1, unit_cost="10.00",
            total_amount="10.00", date="2026-08-23",
        )
        StockOut.objects.create(
            invoice_number="INV0000001", customer=customer,
            item_name="Item", quantity=1, unit_price="20.00",
            total_amount="20.00", date="2026-08-23",
        )
        Invoice.objects.create(
            invoice_number="INV0000001", invoice_type=Invoice.SALE,
            customer=customer, date="2026-08-23",
        )
        Expense.objects.create(
            title="Rent", category="rent", amount="500.00", date="2026-08-23",
        )

    def test_reset_data_wipes_business_data_but_keeps_users(self):
        self.client.login(username="admin", password="pass12345")

        resp = self.client.post("/accounts/reset-data/")

        self.assertRedirects(resp, "/accounts/users/")
        self.assertEqual(StockIn.objects.count(), 0)
        self.assertEqual(StockOut.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(Supplier.objects.count(), 0)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Expense.objects.count(), 0)

        # Users must survive.
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(User.objects.filter(username="admin").exists())
        self.assertTrue(User.objects.filter(username="staff").exists())

    def test_reset_data_requires_post(self):
        self.client.login(username="admin", password="pass12345")

        resp = self.client.get("/accounts/reset-data/")

        self.assertEqual(resp.status_code, 405)
        self.assertEqual(StockIn.objects.count(), 1)

    def test_reset_data_requires_superuser(self):
        self.client.login(username="staff", password="pass12345")

        resp = self.client.post("/accounts/reset-data/")

        self.assertRedirects(resp, "/")
        self.assertEqual(StockIn.objects.count(), 1)

    def test_reset_data_requires_login(self):
        resp = self.client.post("/accounts/reset-data/")

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)
        self.assertEqual(StockIn.objects.count(), 1)
