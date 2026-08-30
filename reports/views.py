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

    # POS checkouts create a SALE Invoice directly, without a matching
    # StockOut record (there's no per-line Stock Out entry for a POS
    # cart) - so sales totals must add those Invoices in on top of
    # StockOut, matched by excluding any invoice_number that IS backed
    # by a StockOut (those are already counted via StockOut.total_amount).
    pos_sale_invoices = Invoice.objects.filter(
        invoice_type=Invoice.SALE
    ).exclude(
        invoice_number__in=StockOut.objects.values("invoice_number")
    )

    # All-time sales, purchases & expenses - the primary profit figure is
    # based on these (not scoped to "this month"), so it never misses
    # entries just because they were logged with an older/different date.

    all_time_sales_total = (
        (StockOut.objects.aggregate(total=Sum("total_amount"))["total"] or 0)
        + (pos_sale_invoices.aggregate(total=Sum("subtotal"))["total"] or 0)
    )

    all_time_purchases_total = StockIn.objects.aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    all_time_expenses_total = Expense.objects.aggregate(
        total=Sum("amount")
    )["total"] or 0

    estimated_profit = (
        all_time_sales_total
        - all_time_purchases_total
        - all_time_expenses_total
    )

    # Sales & purchases (this month) - shown as a secondary breakdown.

    monthly_sales_stockout = StockOut.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("total_amount"),
        count=Count("id")
    )

    monthly_pos_sales = pos_sale_invoices.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("subtotal"),
        count=Count("id")
    )

    monthly_sales = {
        "total": (
            (monthly_sales_stockout["total"] or 0)
            + (monthly_pos_sales["total"] or 0)
        ),
        "count": (
            (monthly_sales_stockout["count"] or 0)
            + (monthly_pos_sales["count"] or 0)
        ),
    }

    monthly_purchases = StockIn.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("total_amount"),
        count=Count("id")
    )

    monthly_expenses_total = Expense.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    monthly_profit = (
        (monthly_sales["total"] or 0)
        - (monthly_purchases["total"] or 0)
        - monthly_expenses_total
    )

    # Invoices

    invoice_totals = Invoice.objects.aggregate(
        revenue=Sum("grand_total"),
        collected=Sum("paid_amount"),
        pending=Sum("remaining_amount"),
        count=Count("id"),
    )

    # Expense breakdown (this month)

    expense_breakdown = Expense.objects.filter(
        date__gte=month_start
    ).category_breakdown()

    max_expense_total = max(
        (row["total"] for row in expense_breakdown),
        default=0
    )

    return {
        "today": today,
        "all_time_sales_total": all_time_sales_total,
        "all_time_purchases_total": all_time_purchases_total,
        "all_time_expenses_total": all_time_expenses_total,
        "estimated_profit": estimated_profit,
        "monthly_sales": monthly_sales,
        "monthly_purchases": monthly_purchases,
        "monthly_expenses_total": monthly_expenses_total,
        "monthly_profit": monthly_profit,
        "invoice_totals": invoice_totals,
        "expense_breakdown": expense_breakdown,
        "max_expense_total": max_expense_total,
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
