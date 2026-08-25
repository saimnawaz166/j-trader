from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from inventory.models import Customer, Invoice


class DashboardViewTests(TestCase):
    def test_dashboard_home_renders(self):
        User.objects.create_superuser('admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Traders')
        self.assertTemplateUsed(response, 'base.html')

    def test_recent_invoices_limited_to_five(self):
        User.objects.create_superuser('admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')
        customer = Customer.objects.create(name='Test Customer')

        for i in range(8):
            Invoice.objects.create(
                invoice_number=f'INV000000{i}',
                invoice_type=Invoice.SALE,
                customer=customer,
                date=f'2026-08-{10 + i:02d}',
            )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(len(response.context['recent_invoices']), 5)
        # Most recent (highest date) invoices should be the ones shown.
        shown_numbers = {inv.invoice_number for inv in response.context['recent_invoices']}
        self.assertEqual(shown_numbers, {'INV0000007', 'INV0000006', 'INV0000005', 'INV0000004', 'INV0000003'})

    def test_recent_invoices_table_has_no_colspan_placeholder_row(self):
        # A static "No invoices yet" row rendered via colspan confuses
        # DataTables' client-side row/column detection (it counts actual
        # <td> elements, not the colspan) and throws a console warning -
        # https://datatables.net/tn/4. With zero invoices, the table body
        # must be completely empty and let DataTables' own emptyTable
        # message handle it instead.
        User.objects.create_superuser('admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')

        response = self.client.get(reverse('dashboard'))

        self.assertNotContains(response, 'colspan')
