from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from config.datatables import datatable_response

from .forms import ProductForm
from .models import Product


def _first_form_error(form):
    for field_errors in form.errors.values():
        return field_errors[0]
    return "Please correct the errors below."


@login_required
def product_list(request):
    return render(request, "products/product_list.html")


@login_required
def product_data(request):

    queryset = Product.objects.all()
    csrf_token = get_token(request)

    def row(product):
        if product.image:
            image_html = (
                f'<img src="{product.image.url}" alt="{product.name}" '
                f'class="product-thumb">'
            )
        else:
            image_html = '<span class="product-thumb-placeholder">No image</span>'

        delete_url = reverse("product_delete", args=[product.id])
        actions = (
            f'<a href="{reverse("product_edit", args=[product.id])}" '
            f'class="btn btn-secondary">Edit</a> '
            f'<form method="POST" action="{delete_url}" style="display:inline;" '
            f'onsubmit="return confirm(\'Delete this product?\');">'
            f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">'
            f'<button type="submit" class="btn btn-danger">Delete</button>'
            f'</form>'
        )

        if product.quantity <= 0:
            qty_html = '<span class="stock-badge stock-out">Out of stock</span>'
        elif product.quantity <= 5:
            qty_html = f'<span class="stock-badge stock-low">{product.quantity} left</span>'
        else:
            qty_html = str(product.quantity)

        return {
            "image": image_html,
            "name": f"<strong>{product.name}</strong>",
            "price": f"Rs {product.price:.2f}",
            "quantity": qty_html,
            "actions": actions,
        }

    return datatable_response(
        request, queryset, row,
        search_fields=["name"],
        order_fields=[None, "name", "price", "quantity", None],
    )


@login_required
def product_create(request):

    if request.method == "POST":

        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Product added successfully."
            )

            return redirect("product_list")

        messages.error(request, _first_form_error(form))

    else:
        form = ProductForm()

    return render(
        request,
        "products/product_form.html",
        {"form": form}
    )


@login_required
def product_edit(request, pk):

    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":

        form = ProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Product updated successfully."
            )

            return redirect("product_list")

        messages.error(request, _first_form_error(form))

    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "products/product_form.html",
        {"form": form, "product": product}
    )


@login_required
def product_delete(request, pk):

    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        product.delete()

        messages.success(
            request,
            "Product deleted successfully."
        )

    return redirect("product_list")
