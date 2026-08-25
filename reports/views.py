from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from expenses.models import Expense
from inventory.models import Invoice, StockIn, StockOut


def _reports_context():
    """Shared query/summary logic used by both the reports page and its
    printable version, so the two always agree on what's shown."""

    today = timezone.localdate()
    month_start = today.replace(day=1)

    # Sales & purchases (this month)

    monthly_sales = StockOut.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("total_amount"),
        count=Count("id")
    )

    monthly_purchases = StockIn.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("total_amount"),
        count=Count("id")
    )

    # Invoices

    invoice_totals = Invoice.objects.aggregate(
        revenue=Sum("grand_total"),
        collected=Sum("paid_amount"),
        pending=Sum("remaining_amount"),
        count=Count("id"),
    )

    # Expenses (this month)

    monthly_expenses_total = Expense.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    expense_breakdown = Expense.objects.filter(
        date__gte=month_start
    ).category_breakdown()

    max_expense_total = max(
        (row["total"] for row in expense_breakdown),
        default=0
    )

    # Rough profit estimate for the month:
    # sales revenue - cost of goods sold (approximated via purchase price)
    # - expenses recorded this month

    monthly_sales_total = monthly_sales["total"] or 0

    estimated_profit = (
        monthly_sales_total
        - (monthly_purchases["total"] or 0)
        - monthly_expenses_total
    )

    return {
        "today": today,
        "monthly_sales": monthly_sales,
        "monthly_purchases": monthly_purchases,
        "invoice_totals": invoice_totals,
        "monthly_expenses_total": monthly_expenses_total,
        "expense_breakdown": expense_breakdown,
        "max_expense_total": max_expense_total,
        "estimated_profit": estimated_profit,
    }


@login_required
def reports_home(request):

    return render(
        request,
        "reports/reports.html",
        _reports_context()
    )


@login_required
def reports_print(request):

    return render(
        request,
        "reports/reports_print.html",
        _reports_context()
    )
