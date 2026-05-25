from django.urls import path
from . import views

app_name = "actividades"

urlpatterns = [
    path("tipos/", views.tipo_actividad_list, name="tipo_list"),
    path("tipos/crear/", views.tipo_actividad_create, name="tipo_create"),
    path("tipos/editar/<int:pk>/", views.tipo_actividad_edit, name="tipo_edit"),
    path("tipos/eliminar/<int:pk>/", views.tipo_actividad_delete, name="tipo_delete"),
    path("actividades/", views.actividad_list, name="actividad_list"),
    path("actividades/crear/", views.actividad_create, name="actividad_create"),
    path("actividades/editar/<int:pk>/", views.actividad_edit, name="actividad_edit"),
    path("actividades/eliminar/<int:pk>/", views.actividad_delete, name="actividad_delete"),
]
