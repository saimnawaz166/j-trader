from django.contrib.auth.models import User
from django.test import TestCase

from .models import Product


class ProductCatalogTests(TestCase):

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")

    def test_create_product(self):
        resp = self.client.post("/products/add/", {
            "name": "Steel Pipe 2 inch", "price": "150.00", "quantity": "20",
        })

        self.assertRedirects(resp, "/products/")
        product = Product.objects.get(name="Steel Pipe 2 inch")
        self.assertEqual(product.price, 150)
        self.assertEqual(product.quantity, 20)

    def test_edit_product(self):
        product = Product.objects.create(name="Old Name", price="10.00", quantity=3)

        resp = self.client.post(f"/products/edit/{product.pk}/", {
            "name": "New Name", "price": "20.00", "quantity": "5",
        })

        self.assertRedirects(resp, "/products/")
        product.refresh_from_db()
        self.assertEqual(product.name, "New Name")
        self.assertEqual(product.price, 20)
        self.assertEqual(product.quantity, 5)

    def test_delete_product(self):
        product = Product.objects.create(name="Gone Soon", price="5.00", quantity=1)

        resp = self.client.post(f"/products/delete/{product.pk}/")

        self.assertRedirects(resp, "/products/")
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_negative_price_rejected(self):
        resp = self.client.post("/products/add/", {
            "name": "Bad Product", "price": "-5.00", "quantity": "1",
        })

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Product.objects.filter(name="Bad Product").exists())

    def test_product_list_and_data_endpoint(self):
        Product.objects.create(name="Widget", price="99.00", quantity=10)

        resp = self.client.get("/products/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('data-ajax="/products/data/"', resp.content.decode())

        resp = self.client.get(
            "/products/data/?draw=1&start=0&length=10&search[value]="
        )
        payload = resp.json()
        self.assertEqual(payload["recordsTotal"], 1)
        self.assertIn("Widget", payload["data"][0]["name"])
        # Prices display without decimal places project-wide.
        self.assertIn("Rs 99", payload["data"][0]["price"])
        self.assertNotIn(".", payload["data"][0]["price"])
