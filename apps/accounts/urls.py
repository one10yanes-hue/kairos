from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("master/usuarios/", views.master_usuarios, name="master_usuarios"),
    path("master/usuarios/crear/", views.master_usuario_create, name="master_usuario_create"),
    path("master/usuarios/<int:pk>/editar/", views.master_usuario_edit, name="master_usuario_edit"),
    path("master/usuarios/<int:pk>/inactivar/", views.master_usuario_delete, name="master_usuario_delete"),
    path("switch-role/", views.switch_role, name="switch_role"),
]
