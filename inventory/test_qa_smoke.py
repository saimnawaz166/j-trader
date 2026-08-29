"""Cross-app QA pass: smoke-tests every page, plus targeted coverage for
flows that had no dedicated tests yet (Expenses CRUD, Supplier/Customer
CRUD, login edge cases, full add/edit invoice round-trips, Stock In/Out
validation, migration consistency). All against the isolated test
database - the real db.sqlite3/Neon data is never touched.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from expenses.models import Expense
from products.models import Product

from .models import Customer, Invoice, InvoiceItem, StockIn, StockOut, Supplier


class SmokeTestAllPagesAsAdmin(TestCase):
    """Every page in the app must render (200) for an admin, with a
    reasonable amount of real data in the database so templates that
    branch on "is there data" get exercised both ways."""

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")

        self.supplier = Supplier.objects.create(name="QA Supplier", phone="0300-0000000")
        self.customer = Customer.objects.create(name="QA Customer", phone="0300-1111111")
        self.product = Product.objects.create(name="QA Widget", price="50.00", quantity=25)

        self.stock_in = StockIn.objects.create(
            invoice_number="PUR0000001", supplier=self.supplier,
            item_name="Raw Material", quantity=10, unit_cost="20.00",
            total_amount="200.00", date=timezone.localdate(),
        )
        self.stock_out = StockOut.objects.create(
            invoice_number="INV0000001", customer=self.customer,
            item_name="Finished Good", quantity=2, unit_price="80.00",
            total_amount="160.00", date=timezone.localdate(),
        )
        self.invoice = Invoice.objects.create(
            invoice_number="INV0000002", invoice_type=Invoice.SALE,
            customer=self.customer, date=timezone.localdate(),
            subtotal="160.00", grand_total="160.00", paid_amount="60.00",
            remaining_amount="100.00",
        )
        InvoiceItem.objects.create(
            invoice=self.invoice, item_name="Finished Good",
            quantity=2, unit_price="80.00", total="160.00",
        )
        self.expense = Expense.objects.create(
            title="Office Rent", category="rent", amount="500.00",
            date=timezone.localdate(),
        )

    def test_every_get_page_renders(self):
        pages = [
            "/",
            "/products/", "/products/add/",
            f"/products/edit/{self.product.pk}/",
            "/inventory/", "/inventory/add/",
            "/inventory/suppliers/", "/inventory/suppliers/add/",
            "/inventory/stock-out/", "/inventory/stock-out/add/",
            "/inventory/customers/", "/inventory/customers/add/",
            "/inventory/invoices/", "/inventory/invoices/add/",
            f"/inventory/invoices/{self.invoice.pk}/edit/",
            f"/inventory/invoices/{self.invoice.pk}/print/",
            "/inventory/pos/",
            "/expenses/", "/expenses/add/",
            f"/expenses/edit/{self.expense.pk}/",
            "/expenses/print/",
            "/reports/", "/reports/print/",
            "/accounts/users/", "/accounts/users/add/",
        ]

        for url in pages:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(
                    resp.status_code, 200,
                    f"{url} returned {resp.status_code} instead of 200"
                )

    def test_every_data_endpoint_returns_valid_json(self):
        endpoints = [
            "/products/data/", "/inventory/data/", "/inventory/suppliers/data/",
            "/inventory/stock-out/data/", "/inventory/customers/data/",
            "/inventory/invoices/data/", "/expenses/data/", "/accounts/users/data/",
        ]

        for url in endpoints:
            with self.subTest(url=url):
                resp = self.client.get(
                    url + "?draw=1&start=0&length=10&search[value]="
                )
                self.assertEqual(resp.status_code, 200)
                payload = resp.json()
                self.assertIn("recordsTotal", payload)
                self.assertIn("data", payload)

    def test_money_values_show_no_decimal_places(self):
        # Amounts are shown as whole rupees everywhere (no "100.00") -
        # spot-check the money-heavy list pages.
        checks = {
            "/products/data/": "price",
            "/inventory/data/": "unit_cost",
            "/inventory/stock-out/data/": "unit_price",
            "/inventory/invoices/data/": "subtotal",
        }

        for url, field in checks.items():
            with self.subTest(url=url):
                resp = self.client.get(
                    url + "?draw=1&start=0&length=10&search[value]="
                )
                payload = resp.json()
                for row in payload["data"]:
                    self.assertNotIn(
                        ".", row[field],
                        f"{url} field '{field}' still shows a decimal: {row[field]!r}"
                    )

    def test_invoice_print_shows_no_decimal_places(self):
        resp = self.client.get(f"/inventory/invoices/{self.invoice.pk}/print/")
        self.assertNotContains(resp, "160.00")
        self.assertContains(resp, "Rs 160")

    def test_price_fields_have_no_spinner_class_and_wheel_guard(self):
        # Price/Discount/Amount inputs must carry the no-spinner class,
        # and the shared base template must wire up the wheel-blur guard.
        resp = self.client.get("/inventory/pos/")
        self.assertIn('class="no-spinner"', resp.content.decode())
        self.assertIn("input.no-spinner", resp.content.decode())

    def test_quantity_fields_have_wheel_guard(self):
        # Quantity inputs (Stock In/Out) keep their spinner arrows but
        # must still be covered by the wheel-blur guard.
        resp = self.client.get("/inventory/add/")
        self.assertIn('class="quantity-field"', resp.content.decode())

        base_body = self.client.get("/").content.decode()
        self.assertIn("input.quantity-field", base_body)


class SmokeTestPagesAsStaff(TestCase):
    """A non-admin (staff) user should be able to use the app day-to-day,
    but must be turned away from admin-only pages."""

    def setUp(self):
        User.objects.create_user("staff", password="pass12345")
        self.client.login(username="staff", password="pass12345")

        customer = Customer.objects.create(name="Staff Test Customer")
        self.invoice = Invoice.objects.create(
            invoice_number="INV0000099", invoice_type=Invoice.SALE,
            customer=customer, date=timezone.localdate(),
        )

    def test_staff_can_use_normal_pages(self):
        pages = [
            "/", "/products/", "/inventory/", "/inventory/add/",
            "/inventory/stock-out/", "/inventory/stock-out/add/",
            "/inventory/invoices/", "/inventory/invoices/add/",
            "/inventory/pos/", "/expenses/", "/reports/",
        ]

        for url in pages:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)

    def test_staff_blocked_from_admin_only_pages(self):
        admin_only = [
            "/accounts/users/",
            "/accounts/users/add/",
            f"/inventory/invoices/{self.invoice.pk}/edit/",
        ]

        for url in admin_only:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 302)


class LoginEdgeCaseTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            "loginuser", password="CorrectPass123!", is_active=True
        )

    def test_wrong_password_shows_generic_error(self):
        resp = self.client.post("/accounts/login/", {
            "username": "loginuser", "password": "WrongPassword",
        })

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid username or password")

    def test_nonexistent_user_shows_generic_error(self):
        resp = self.client.post("/accounts/login/", {
            "username": "ghost", "password": "whatever",
        })

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid username or password")

    def test_disabled_account_shows_specific_message(self):
        self.user.is_active = False
        self.user.save()

        resp = self.client.post("/accounts/login/", {
            "username": "loginuser", "password": "CorrectPass123!",
        })

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "This account has been disabled")

    def test_correct_credentials_log_in(self):
        resp = self.client.post("/accounts/login/", {
            "username": "loginuser", "password": "CorrectPass123!",
        })

        self.assertRedirects(resp, "/")

    def test_missing_fields_show_error(self):
        resp = self.client.post("/accounts/login/", {"username": "loginuser"})

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please enter both username and password")


class ExpenseCrudTests(TestCase):
    """Expenses had zero dedicated test coverage before this QA pass."""

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")

    def test_create_expense(self):
        resp = self.client.post("/expenses/add/", {
            "title": "Electricity Bill", "category": "utilities",
            "amount": "1200.50", "date": timezone.localdate(), "notes": "August",
        })

        self.assertRedirects(resp, "/expenses/")
        expense = Expense.objects.get(title="Electricity Bill")
        self.assertEqual(expense.amount, Decimal("1200.50"))
        self.assertEqual(expense.category, "utilities")

    def test_edit_expense(self):
        expense = Expense.objects.create(
            title="Old Title", category="other", amount="10.00",
            date=timezone.localdate(),
        )

        resp = self.client.post(f"/expenses/edit/{expense.pk}/", {
            "title": "New Title", "category": "transport",
            "amount": "25.00", "date": timezone.localdate(),
        })

        self.assertRedirects(resp, "/expenses/")
        expense.refresh_from_db()
        self.assertEqual(expense.title, "New Title")
        self.assertEqual(expense.category, "transport")
        self.assertEqual(expense.amount, Decimal("25.00"))

    def test_delete_expense(self):
        expense = Expense.objects.create(
            title="Gone", category="other", amount="5.00", date=timezone.localdate(),
        )

        resp = self.client.post(f"/expenses/delete/{expense.pk}/")

        self.assertRedirects(resp, "/expenses/")
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_missing_required_fields_rejected(self):
        resp = self.client.post("/expenses/add/", {
            "title": "", "category": "other", "amount": "10.00",
            "date": timezone.localdate(),
        }, follow=True)

        self.assertEqual(Expense.objects.count(), 0)


class SupplierCustomerCrudTests(TestCase):

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")

    def test_create_supplier(self):
        resp = self.client.post("/inventory/suppliers/add/", {
            "name": "New Supplier", "phone": "0300-9999999",
        })

        self.assertRedirects(resp, "/inventory/suppliers/")
        self.assertTrue(Supplier.objects.filter(name="New Supplier").exists())

    def test_create_supplier_requires_name(self):
        resp = self.client.post("/inventory/suppliers/add/", {"name": ""})

        self.assertEqual(Supplier.objects.count(), 0)

    def test_create_customer(self):
        resp = self.client.post("/inventory/customers/add/", {
            "name": "New Customer", "email": "customer@example.com",
        })

        self.assertRedirects(resp, "/inventory/customers/")
        self.assertTrue(Customer.objects.filter(name="New Customer").exists())


class AddInvoiceFullFlowTests(TestCase):
    """The manual multi-item invoice form (separate from the POS)."""

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")
        self.customer = Customer.objects.create(name="Manual Invoice Customer")

    def test_create_invoice_with_multiple_items(self):
        resp = self.client.post("/inventory/invoices/add/", {
            "invoice_number": "MANUAL0001",
            "customer": self.customer.id,
            "discount": "50",
            "paid_amount": "100",
            "notes": "Test invoice",
            "item_name": ["Item A", "Item B"],
            "quantity": ["2", "1"],
            "price": ["100.00", "50.00"],
        })

        self.assertRedirects(resp, "/inventory/invoices/")

        invoice = Invoice.objects.get(invoice_number="MANUAL0001")
        # Subtotal = 2*100 + 1*50 = 250; discount 50 -> grand total 200;
        # paid 100 -> remaining 100.
        self.assertEqual(invoice.subtotal, 250)
        self.assertEqual(invoice.grand_total, 200)
        self.assertEqual(invoice.remaining_amount, 100)
        self.assertEqual(invoice.items.count(), 2)

    def test_duplicate_invoice_number_rejected(self):
        Invoice.objects.create(
            invoice_number="DUPLICATE1", invoice_type=Invoice.SALE,
            customer=self.customer, date=timezone.localdate(),
        )

        resp = self.client.post("/inventory/invoices/add/", {
            "invoice_number": "DUPLICATE1",
            "customer": self.customer.id,
            "discount": "0", "paid_amount": "0",
            "item_name": ["Item A"], "quantity": ["1"], "price": ["10.00"],
        }, follow=True)

        self.assertEqual(
            Invoice.objects.filter(invoice_number="DUPLICATE1").count(), 1
        )


class EditInvoiceFullFlowTests(TestCase):

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")
        self.customer = Customer.objects.create(name="Edit Test Customer")
        self.invoice = Invoice.objects.create(
            invoice_number="EDIT0001", invoice_type=Invoice.SALE,
            customer=self.customer, date=timezone.localdate(),
            subtotal="500.00", grand_total="500.00",
            paid_amount="0", remaining_amount="500.00",
        )

    def test_edit_recomputes_totals_from_existing_subtotal(self):
        resp = self.client.post(f"/inventory/invoices/{self.invoice.pk}/edit/", {
            "invoice_number": "EDIT0001", "party": self.customer.id,
            "date": timezone.localdate(), "discount": "100", "paid_amount": "200",
            "notes": "updated",
        })

        self.assertRedirects(resp, "/inventory/invoices/")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.grand_total, 400)  # 500 - 100
        self.assertEqual(self.invoice.remaining_amount, 200)  # 400 - 200

    def test_cannot_reuse_another_invoices_number(self):
        Invoice.objects.create(
            invoice_number="TAKEN0001", invoice_type=Invoice.SALE,
            customer=self.customer, date=timezone.localdate(),
        )

        resp = self.client.post(f"/inventory/invoices/{self.invoice.pk}/edit/", {
            "invoice_number": "TAKEN0001", "party": self.customer.id,
            "date": timezone.localdate(), "discount": "0", "paid_amount": "0",
        }, follow=True)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.invoice_number, "EDIT0001")


class StockInOutValidationTests(TestCase):

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")
        self.supplier = Supplier.objects.create(name="Val Supplier")
        self.customer = Customer.objects.create(name="Val Customer")

    def test_stock_in_rejects_zero_quantity(self):
        resp = self.client.post("/inventory/add/", {
            "supplier": self.supplier.id, "item_name": "Item",
            "quantity": "0", "unit_cost": "10.00",
            "date": timezone.localdate(), "notes": "",
        }, follow=True)

        self.assertEqual(StockIn.objects.count(), 0)

    def test_stock_in_rejects_negative_unit_cost(self):
        resp = self.client.post("/inventory/add/", {
            "supplier": self.supplier.id, "item_name": "Item",
            "quantity": "1", "unit_cost": "-10.00",
            "date": timezone.localdate(), "notes": "",
        }, follow=True)

        self.assertEqual(StockIn.objects.count(), 0)

    def test_stock_out_rejects_zero_quantity(self):
        resp = self.client.post("/inventory/stock-out/add/", {
            "customer": self.customer.id, "item_name": "Item",
            "quantity": "0", "unit_price": "10.00",
            "date": timezone.localdate(), "notes": "",
        }, follow=True)

        self.assertEqual(StockOut.objects.count(), 0)

    def test_stock_in_missing_item_name_rejected(self):
        resp = self.client.post("/inventory/add/", {
            "supplier": self.supplier.id, "item_name": "",
            "quantity": "1", "unit_cost": "10.00",
            "date": timezone.localdate(), "notes": "",
        }, follow=True)

        self.assertEqual(StockIn.objects.count(), 0)


class MigrationConsistencyTests(TestCase):

    def test_no_missing_migrations(self):
        """If a model field was changed without generating a migration,
        this fails loudly instead of silently drifting between dev
        machines / environments."""
        from io import StringIO

        out = StringIO()
        try:
            call_command(
                "makemigrations", "--check", "--dry-run", stdout=out, stderr=out
            )
        except SystemExit as exc:
            self.fail(
                f"There are model changes without a migration:\n{out.getvalue()}"
            )
