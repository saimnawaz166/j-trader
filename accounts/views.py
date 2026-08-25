from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from config.datatables import datatable_response

from .forms import LoginForm, UserAccountForm


def admin_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_superuser:

            messages.error(
                request,
                "You don't have permission to access that page."
            )

            return redirect("dashboard")

        return view_func(request, *args, **kwargs)

    return wrapper


def login_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    next_url = request.GET.get("next", "")

    if request.method == "POST":

        next_url = request.POST.get("next", "") or next_url
        form = LoginForm(request.POST)

        if not form.is_valid():

            messages.error(
                request,
                "Please enter both username and password."
            )

            return render(
                request,
                "accounts/login.html",
                {"next": next_url}
            )

        username = form.cleaned_data["username"].strip()
        password = form.cleaned_data["password"]

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:

            messages.error(
                request,
                "Invalid username or password."
            )

            return render(
                request,
                "accounts/login.html",
                {"next": next_url}
            )

        if not user.is_active:

            messages.error(
                request,
                "This account has been disabled."
            )

            return render(
                request,
                "accounts/login.html",
                {"next": next_url}
            )

        login(request, user)

        if next_url:
            return redirect(next_url)

        return redirect("dashboard")

    return render(
        request,
        "accounts/login.html",
        {"next": next_url}
    )


@login_required
def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out."
    )

    return redirect("login")


@login_required
@admin_required
def user_list(request):
    return render(request, "accounts/user_list.html")


@login_required
@admin_required
def user_data(request):

    queryset = User.objects.all()
    csrf_token = get_token(request)

    def row(account):
        name = (
            f"{account.first_name} {account.last_name}".strip()
            or "&mdash;"
        )

        role = (
            '<span class="role-tag role-admin">Admin</span>'
            if account.is_superuser
            else '<span class="role-tag role-staff">Staff</span>'
        )

        status = (
            '<span class="status-tag status-active">Active</span>'
            if account.is_active
            else '<span class="status-tag status-inactive">Inactive</span>'
        )

        last_login = (
            account.last_login.strftime("%d %b %Y, %H:%M")
            if account.last_login else "Never"
        )

        you_tag = (
            '<span class="usr-you-tag">(You)</span>'
            if account == request.user else ""
        )

        if account == request.user:
            delete_html = '<span class="usr-btn-disabled">Delete</span>'
        else:
            delete_url = reverse("user_delete", args=[account.id])
            delete_html = (
                f'<form method="POST" action="{delete_url}" '
                f'onsubmit="return confirm(\'Delete user {account.username}? '
                f'This cannot be undone.\');">'
                f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">'
                f'<button type="submit" class="usr-btn-delete">Delete</button>'
                f'</form>'
            )

        actions = (
            f'<div class="usr-actions">'
            f'<a href="{reverse("user_edit", args=[account.id])}" '
            f'class="usr-btn-edit">Edit</a>{delete_html}</div>'
        )

        return {
            "username": f"<strong>{account.username}</strong>{you_tag}",
            "name": name,
            "role": role,
            "status": status,
            "last_login": f'<span class="usr-last-login">{last_login}</span>',
            "actions": actions,
        }

    return datatable_response(
        request, queryset, row,
        search_fields=["username", "first_name", "last_name"],
        order_fields=["username", None, None, None, "last_login", None],
    )


def _first_form_error(form):
    for field_errors in form.errors.values():
        return field_errors[0]
    return "Please correct the errors below."


@login_required
@admin_required
def user_create(request):

    if request.method == "POST":

        form = UserAccountForm(request.POST)

        if form.is_valid():

            new_user = form.save()

            messages.success(
                request,
                f"User '{new_user.username}' created successfully."
            )

            return redirect("user_list")

        messages.error(request, _first_form_error(form))

        return redirect("user_create")

    return render(
        request,
        "accounts/user_form.html",
        {}
    )


@login_required
@admin_required
def user_edit(request, pk):

    account = get_object_or_404(User, pk=pk)

    if request.method == "POST":

        form = UserAccountForm(request.POST, instance=account)
        is_active_flag = request.POST.get("is_active") == "on"
        is_admin_flag = request.POST.get("is_admin") == "on"

        if account == request.user and not is_active_flag:

            messages.error(
                request,
                "You can't deactivate your own account."
            )

            return redirect("user_edit", pk=pk)

        if account == request.user and not is_admin_flag:

            messages.error(
                request,
                "You can't remove your own admin access."
            )

            return redirect("user_edit", pk=pk)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                f"User '{account.username}' updated successfully."
            )

            return redirect("user_list")

        messages.error(request, _first_form_error(form))

        return redirect("user_edit", pk=pk)

    context = {
        "account": account,
    }

    return render(
        request,
        "accounts/user_form.html",
        context
    )


@login_required
@admin_required
def user_delete(request, pk):

    account = get_object_or_404(User, pk=pk)

    if request.method == "POST":

        if account == request.user:

            messages.error(
                request,
                "You can't delete your own account."
            )

            return redirect("user_list")

        username = account.username
        account.delete()

        messages.success(
            request,
            f"User '{username}' deleted."
        )

    return redirect("user_list")


@login_required
@admin_required
@require_POST
def reset_data(request):
    """Wipe every business record (Stock In/Out, Invoices, Suppliers,
    Customers, Expenses) - login accounts (Users) are never touched.

    Superuser-only, POST-only (via the confirm button on Settings), so it
    can't be triggered by simply visiting a URL.
    """

    from expenses.models import Expense
    from inventory.models import Customer, Invoice, StockIn, StockOut, Supplier

    with transaction.atomic():
        StockIn.objects.all().delete()
        StockOut.objects.all().delete()
        Invoice.objects.all().delete()
        Supplier.objects.all().delete()
        Customer.objects.all().delete()
        Expense.objects.all().delete()

    messages.success(
        request,
        "All business data has been deleted. Login accounts were kept."
    )

    return redirect("user_list")
