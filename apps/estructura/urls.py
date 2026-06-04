from django.urls import path
from . import views
from . import integracion_views

app_name = "estructura"

urlpatterns = [
    path("integracion/habilitaciones/", integracion_views.integracion_cargo, name="integracion_cargo"),
    path("integracion/api/cargos/", integracion_views.api_integracion_cargos, name="api_integracion_cargos"),
    path("integracion/api/empleados/", integracion_views.api_integracion_empleados, name="api_integracion_empleados"),
    path("integracion/api/subareas/", integracion_views.api_integracion_subareas, name="api_integracion_subareas"),
    path("integracion/sync/", integracion_views.sync_cargo, name="sync_cargo"),
    path("integracion/api/sync/comparar/", integracion_views.api_sync_comparar, name="api_sync_comparar"),
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
    path("importaciones/", views.importar_exportar, name="importar_exportar"),
    path("importaciones/template/", views.descargar_template, name="descargar_template"),
    path("importaciones/subir/", views.importar_datos, name="importar_datos"),
    path("importaciones/usuarios/", views.importar_usuarios, name="importar_usuarios"),
    path("importaciones/usuarios/template/", views.descargar_template_usuarios, name="descargar_template_usuarios"),
    path("importaciones/usuarios/subir/", views.importar_usuarios_datos, name="importar_usuarios_datos"),
]
