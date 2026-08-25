from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.expense_list,
        name="expense_list"
    ),

    path(
        "data/",
        views.expense_data,
        name="expense_data"
    ),

    path(
        "print/",
        views.expense_print,
        name="expense_print"
    ),

    path(
        "add/",
        views.expense_create,
        name="expense_create"
    ),

    path(
        "edit/<int:pk>/",
        views.expense_edit,
        name="expense_edit"
    ),

    path(
        "delete/<int:pk>/",
        views.expense_delete,
        name="expense_delete"
    ),

]
