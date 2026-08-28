from django import forms
from django.core.exceptions import ValidationError

from .models import Product


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = ["name", "image", "price"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise ValidationError("Product name is required.")

        return name

    def clean_price(self):
        price = self.cleaned_data["price"]

        if price < 0:
            raise ValidationError("Price can't be negative.")

        return price
