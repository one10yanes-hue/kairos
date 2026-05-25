from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("master/usuarios/", views.master_usuarios, name="master_usuarios"),
    path("master/usuarios/crear/", views.master_usuario_create, name="master_usuario_create"),
    path("master/usuarios/editar/<int:pk>/", views.master_usuario_edit, name="master_usuario_edit"),
    path("master/usuarios/eliminar/<int:pk>/", views.master_usuario_delete, name="master_usuario_delete"),
    path("master/usuarios/<int:pk>/empresas/", views.master_usuario_empresas, name="master_usuario_empresas"),
    path("master/usuarios/<int:pk>/empresas/<int:empresa_pk>/remover/", views.master_usuario_empresa_remove, name="master_usuario_empresa_remove"),
]
