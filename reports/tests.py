from django.contrib.auth.models import User
from django.test import TestCase

from expenses.models import Expense
from inventory.models import Customer, StockOut, Supplier, StockIn


class ProfitReportTests(TestCase):
    """The profit figure must be based on ALL data, not just entries dated
    within the current month - a Stock Out/In/Expense logged with an
    older date must still count towards the shown profit."""

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")

        supplier = Supplier.objects.create(name="Old Supplier")
        customer = Customer.objects.create(name="Old Customer")

        # Deliberately dated well outside the current month.
        StockIn.objects.create(
            invoice_number="PUR0000001", supplier=supplier,
            item_name="Item", quantity=10, unit_cost="10.00",
            total_amount="100.00", date="2020-01-15",
        )
        StockOut.objects.create(
            invoice_number="INV0000001", customer=customer,
            item_name="Item", quantity=10, unit_price="30.00",
            total_amount="300.00", date="2020-01-20",
        )
        Expense.objects.create(
            title="Old Rent", category="rent", amount="50.00", date="2020-01-25",
        )

    def test_all_time_profit_includes_old_dated_entries(self):
        resp = self.client.get("/reports/")

        # 300 (sales) - 100 (purchases) - 50 (expenses) = 150
        self.assertEqual(resp.context["estimated_profit"], 150)
        self.assertEqual(resp.context["all_time_sales_total"], 300)
        self.assertEqual(resp.context["all_time_purchases_total"], 100)
        self.assertEqual(resp.context["all_time_expenses_total"], 50)
        self.assertContains(resp, "All-Time Result")
        self.assertContains(resp, "150")

    def test_this_month_profit_is_zero_when_only_old_data_exists(self):
        resp = self.client.get("/reports/")

        self.assertEqual(resp.context["monthly_profit"], 0)
