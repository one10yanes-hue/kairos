from django.urls import path
from . import views

app_name = "estructura"

urlpatterns = [
    path("empresas/", views.empresa_list, name="empresa_list"),
    path("empresas/crear/", views.empresa_create, name="empresa_create"),
    path("empresas/editar/<int:pk>/", views.empresa_edit, name="empresa_edit"),
    path("empresas/eliminar/<int:pk>/", views.empresa_delete, name="empresa_delete"),
    path("areas/", views.area_list, name="area_list"),
    path("areas/crear/", views.area_create, name="area_create"),
    path("areas/editar/<int:pk>/", views.area_edit, name="area_edit"),
    path("areas/eliminar/<int:pk>/", views.area_delete, name="area_delete"),
    path("subareas/", views.subarea_list, name="subarea_list"),
    path("subareas/crear/", views.subarea_create, name="subarea_create"),
    path("subareas/editar/<int:pk>/", views.subarea_edit, name="subarea_edit"),
    path("subareas/eliminar/<int:pk>/", views.subarea_delete, name="subarea_delete"),
    path("subareas/<int:pk>/usuarios/", views.subarea_usuarios, name="subarea_usuarios"),
    path("subareas/<int:pk>/usuarios/<int:user_pk>/remover/", views.subarea_usuario_remove, name="subarea_usuario_remove"),
    path("api/buscar/<str:modelo>/", views.api_buscar, name="api_buscar"),
    path("importar/", views.importar_exportar, name="importar_exportar"),
    path("importar/template/<int:empresa_id>/", views.descargar_template, name="descargar_template"),
    path("importar/subir/", views.importar_datos, name="importar_datos"),
]
