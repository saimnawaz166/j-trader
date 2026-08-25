from django.urls import path

from . import views


urlpatterns = [

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

    path(
        "users/",
        views.user_list,
        name="user_list"
    ),

    path(
        "users/data/",
        views.user_data,
        name="user_data"
    ),

    path(
        "users/add/",
        views.user_create,
        name="user_create"
    ),

    path(
        "users/edit/<int:pk>/",
        views.user_edit,
        name="user_edit"
    ),

    path(
        "users/delete/<int:pk>/",
        views.user_delete,
        name="user_delete"
    ),

]