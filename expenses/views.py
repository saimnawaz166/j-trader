from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from config.datatables import datatable_response

from .forms import ExpenseForm
from .models import Expense


@login_required
def expense_list(request):

    return render(
        request,
        "expenses/expense_list.html",
        _expense_list_context(request)
    )


def _expense_list_context(request):
    """Shared query/summary logic used by both the list page and its
    printable version, so the two always agree on what's shown."""

    expenses = Expense.objects.all()

    query = request.GET.get("q", "")

    if query:
        expenses = expenses.filter(
            Q(title__icontains=query) | Q(category__icontains=query)
        )

    total = expenses.aggregate(
        total=Sum("amount")
    )["total"] or 0

    today = timezone.localdate()
    month_start = today.replace(day=1)

    month_total = Expense.objects.filter(
        date__gte=month_start
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    category_breakdown = Expense.objects.filter(
        date__gte=month_start
    ).category_breakdown()

    max_category_total = category_breakdown[0]["total"] if category_breakdown else 0

    return {
        "expenses": expenses,
        "query": query,
        "total": total,
        "month_total": month_total,
        "today": today,
        "category_breakdown": category_breakdown,
        "max_category_total": max_category_total,
    }


@login_required
def expense_data(request):

    queryset = Expense.objects.all()
    csrf_token = get_token(request)

    def row(expense):
        delete_url = reverse("expense_delete", args=[expense.id])
        actions = (
            f'<div class="exp-actions">'
            f'<a href="{reverse("expense_edit", args=[expense.id])}" '
            f'class="exp-btn-edit">Edit</a>'
            f'<form method="POST" action="{delete_url}" '
            f'onsubmit="return confirm(\'Delete this expense?\');">'
            f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">'
            f'<button type="submit" class="exp-btn-delete">Delete</button>'
            f'</form></div>'
        )

        return {
            "title": f"<strong>{expense.title}</strong>",
            "category": (
                f'<span class="cat-tag cat-{expense.category}">'
                f'{expense.get_category_display()}</span>'
            ),
            "amount": f"Rs {expense.amount:.0f}",
            "date": str(expense.date),
            "notes": expense.notes or "—",
            "actions": actions,
        }

    return datatable_response(
        request, queryset, row,
        search_fields=["title", "category"],
        order_fields=["title", None, "amount", "date", None, None],
    )


@login_required
def expense_print(request):

    return render(
        request,
        "expenses/expense_print.html",
        _expense_list_context(request)
    )


@login_required
def expense_create(request):

    if request.method == "POST":

        form = ExpenseForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Expense recorded successfully."
            )

            return redirect("expense_list")

        messages.error(request, "Please enter all required fields correctly.")

        return redirect("expense_create")

    context = {
        "categories": Expense.CATEGORY_CHOICES,
        "today": timezone.localdate(),
    }

    return render(
        request,
        "expenses/expense_form.html",
        context
    )


@login_required
def expense_edit(request, pk):

    expense = get_object_or_404(Expense, pk=pk)

    if request.method == "POST":

        form = ExpenseForm(request.POST, instance=expense)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Expense updated successfully."
            )

            return redirect("expense_list")

        messages.error(request, "Please enter all required fields correctly.")

        return redirect("expense_edit", pk=pk)

    context = {
        "expense": expense,
        "categories": Expense.CATEGORY_CHOICES,
    }

    return render(
        request,
        "expenses/expense_form.html",
        context
    )


@login_required
def expense_delete(request, pk):

    expense = get_object_or_404(Expense, pk=pk)

    if request.method == "POST":
        expense.delete()

        messages.success(
            request,
            "Expense deleted successfully."
        )

    return redirect("expense_list")
