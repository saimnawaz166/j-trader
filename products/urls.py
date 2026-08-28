from django.urls import path

from . import views

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("data/", views.product_data, name="product_data"),
    path("add/", views.product_create, name="product_create"),
    path("edit/<int:pk>/", views.product_edit, name="product_edit"),
    path("delete/<int:pk>/", views.product_delete, name="product_delete"),
]
