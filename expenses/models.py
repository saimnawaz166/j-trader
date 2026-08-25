from django.db import models
from django.db.models import Sum


class ExpenseQuerySet(models.QuerySet):

    def category_breakdown(self):
        """Total spend per category, with a human-readable label attached.

        Returns a list of dicts ordered by highest spend first, e.g.
        [{"category": "rent", "label": "Rent", "total": Decimal("500.00")}].
        """

        labels = dict(Expense.CATEGORY_CHOICES)

        breakdown = list(
            self.values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        for row in breakdown:
            row["label"] = labels.get(row["category"], row["category"])

        return breakdown


class Expense(models.Model):

    CATEGORY_CHOICES = [
        ("rent", "Rent"),
        ("utilities", "Utilities"),
        ("salaries", "Salaries"),
        ("transport", "Transport"),
        ("maintenance", "Maintenance"),
        ("supplies", "Office Supplies"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200)

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    date = models.DateField()

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = ExpenseQuerySet.as_manager()

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.amount}"
