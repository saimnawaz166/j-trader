from django.contrib.auth.models import User
from django.test import TestCase

from expenses.models import Expense
from inventory.models import Customer, Invoice, StockIn, StockOut, Supplier


class UserAccountFormTests(TestCase):
    """The Add/Edit User form no longer has a 'Confirm Password' field -
    a single password field must be enough to create/update an account."""

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")

    def test_create_user_without_confirm_password_field(self):
        resp = self.client.post("/accounts/users/add/", {
            "username": "newstaff", "first_name": "", "last_name": "",
            "password": "SomePass123!",
        })

        self.assertRedirects(resp, "/accounts/users/")
        user = User.objects.get(username="newstaff")
        self.assertTrue(user.check_password("SomePass123!"))

    def test_edit_user_password_without_confirm_password_field(self):
        target = User.objects.create_user("editme", password="OldPass123!")

        resp = self.client.post(f"/accounts/users/edit/{target.id}/", {
            "username": "editme", "first_name": "", "last_name": "",
            "password": "NewPass456!", "is_active": "on",
        })

        self.assertRedirects(resp, "/accounts/users/")
        target.refresh_from_db()
        self.assertTrue(target.check_password("NewPass456!"))


class UserListHidesAdminTests(TestCase):
    """The 'admin' account must not show up in Settings > Users, even
    though it still exists and can log in normally."""

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")
        User.objects.create_user("visiblestaff", password="pass12345")

    def test_admin_username_excluded_from_user_data(self):
        resp = self.client.get(
            "/accounts/users/data/?draw=1&start=0&length=10&search[value]="
        )
        payload = resp.json()
        usernames = "".join(row["username"] for row in payload["data"])
        self.assertNotIn(">admin<", usernames)
        self.assertIn("visiblestaff", usernames)


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


class RepeatedLoginLogoutTests(TestCase):
    """Reproduce the reported bug: a staff account logs in fine several
    times, then a later login attempt fails with 'Invalid username or
    password' even though the credentials are unchanged."""

    def setUp(self):
        self.staff = User.objects.create_user(
            "faizan", password="Staff@12345",
            is_staff=False, is_superuser=False, is_active=True,
        )

    def test_login_logout_cycle_15_times_from_a_single_client(self):
        for i in range(15):
            resp = self.client.post("/accounts/login/", {
                "username": "faizan", "password": "Staff@12345",
            })
            self.assertRedirects(
                resp, "/", msg_prefix=f"login #{i + 1} failed unexpectedly"
            )

            resp = self.client.get("/accounts/logout/")
            self.assertRedirects(resp, "/accounts/login/")

    def test_login_logout_cycle_15_times_from_fresh_clients(self):
        # A fresh Client() each time simulates closing/reopening the
        # browser (no shared cookies) between attempts.
        from django.test import Client

        for i in range(15):
            client = Client()
            resp = client.post("/accounts/login/", {
                "username": "faizan", "password": "Staff@12345",
            })
            self.assertRedirects(
                resp, "/", msg_prefix=f"login #{i + 1} failed unexpectedly"
            )

        # The account itself must be untouched after 15 successful logins.
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)
        self.assertTrue(self.staff.check_password("Staff@12345"))

    def test_password_hash_and_is_active_stable_across_many_logins(self):
        original_password_hash = self.staff.password

        for _ in range(20):
            self.client.login(username="faizan", password="Staff@12345")
            self.client.logout()

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.password, original_password_hash)
        self.assertTrue(self.staff.is_active)
