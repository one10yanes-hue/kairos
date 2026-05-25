from django.urls import path
from . import views

app_name = "planificacion"

urlpatterns = [
    path("planificaciones/", views.planificacion_list, name="planificacion_list"),
    path("planificaciones/crear/", views.planificacion_create, name="planificacion_create"),
    path("planificaciones/<int:pk>/", views.planificacion_detail, name="planificacion_detail"),
    path("planificaciones/<int:pk>/eliminar/", views.planificacion_delete, name="planificacion_delete"),
    path("planificaciones/<int:plan_pk>/detalle/<int:detalle_pk>/eliminar/", views.planificacion_detalle_remove, name="planificacion_detalle_remove"),
    path("pendiente/<int:pk>/reprogramar/", views.reprogramar_pendiente, name="reprogramar_pendiente"),
    path("pendiente/<int:pk>/reasignar/", views.reasignar_pendiente, name="reasignar_pendiente"),
    path("pendiente/<int:pk>/cancelar/", views.cancelar_pendiente, name="cancelar_pendiente"),
]
