from django import forms
from django.core.exceptions import ValidationError

from .models import Expense


class ExpenseForm(forms.ModelForm):

    class Meta:
        model = Expense
        fields = ["title", "category", "amount", "date", "notes"]

    def clean_amount(self):
        amount = self.cleaned_data["amount"]

        if amount <= 0:
            raise ValidationError("Please enter a valid amount.")

        return amount
