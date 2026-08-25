from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from expenses.models import Expense
from inventory.models import Customer, Invoice, StockIn, StockOut, Supplier


@login_required
def dashboard_view(request):

    today = timezone.localdate()
    month_start = today.replace(day=1)

    total_customers = Customer.objects.count()
    total_suppliers = Supplier.objects.count()

    recent_invoices = Invoice.objects.select_related(
        "customer"
    ).order_by(
        "-date",
        "-created_at"
    )[:5]

    invoice_totals = Invoice.objects.aggregate(
        revenue=Sum("grand_total"),
        pending=Sum("remaining_amount"),
    )

    total_revenue = invoice_totals["revenue"] or 0
    pending_payments = invoice_totals["pending"] or 0

    monthly_sales = StockOut.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    monthly_purchases = StockIn.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    monthly_expenses = Expense.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    context = {
        "total_customers": total_customers,
        "total_suppliers": total_suppliers,
        "recent_invoices": recent_invoices,
        "total_revenue": total_revenue,
        "pending_payments": pending_payments,
        "monthly_sales": monthly_sales,
        "monthly_purchases": monthly_purchases,
        "monthly_expenses": monthly_expenses,
        "today": today,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )
