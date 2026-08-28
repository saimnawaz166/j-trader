import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .models import Product


def _tiny_image_file(name="test.png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


# Image uploads write real files to disk (unlike the DB, which the test
# runner isolates automatically) - point MEDIA_ROOT at a throwaway temp
# directory for the duration of these tests so nothing lands in the
# project's real media/ folder.
_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="inventory_system_test_media_")


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class ProductCatalogTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        User.objects.create_superuser("admin", password="pass12345")
        self.client.login(username="admin", password="pass12345")

    def test_create_product_without_image(self):
        resp = self.client.post("/products/add/", {
            "name": "Steel Pipe 2 inch", "price": "150.00", "quantity": "20",
        })

        self.assertRedirects(resp, "/products/")
        product = Product.objects.get(name="Steel Pipe 2 inch")
        self.assertEqual(product.price, 150)
        self.assertEqual(product.quantity, 20)
        self.assertFalse(product.image)

    def test_create_product_with_image(self):
        resp = self.client.post("/products/add/", {
            "name": "PVC Pipe 4 inch", "price": "220.00", "quantity": "5",
            "image": _tiny_image_file(),
        })

        self.assertRedirects(resp, "/products/")
        product = Product.objects.get(name="PVC Pipe 4 inch")
        self.assertTrue(product.image)
        self.assertIn("products/", product.image.name)

    def test_edit_product_keeps_image_if_not_replaced(self):
        product = Product.objects.create(
            name="Old Name", price="10.00", quantity=3, image=_tiny_image_file()
        )
        original_image_name = product.image.name

        resp = self.client.post(f"/products/edit/{product.pk}/", {
            "name": "New Name", "price": "20.00", "quantity": "3",
        })

        self.assertRedirects(resp, "/products/")
        product.refresh_from_db()
        self.assertEqual(product.name, "New Name")
        self.assertEqual(product.image.name, original_image_name)

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
        Product.objects.create(name="Widget", price="99.99", quantity=10)

        resp = self.client.get("/products/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('data-ajax="/products/data/"', resp.content.decode())

        resp = self.client.get(
            "/products/data/?draw=1&start=0&length=10&search[value]="
        )
        payload = resp.json()
        self.assertEqual(payload["recordsTotal"], 1)
        self.assertIn("Widget", payload["data"][0]["name"])
        self.assertIn("99.99", payload["data"][0]["price"])
