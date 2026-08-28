from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=200)

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField(
        default=0,
        help_text="Stock currently on hand. Decreases automatically as sales are made in the POS.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
