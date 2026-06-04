from django.urls import path
from . import views
from apps.gestion import views as gestion_views

app_name = "dashboard"

urlpatterns = [
    path("dashboard/", views.dashboard_admin, name="dashboard_admin"),
    path("progreso/", views.progreso, name="progreso"),
    path("linea-tiempo/", views.linea_tiempo, name="linea_tiempo"),
    path("tiempo-inactividad/", views.tiempo_inactividad, name="tiempo_inactividad"),
    path("revisiones/", gestion_views.revisiones_list, name="revisiones"),
    path("revision/<int:pk>/aprobar/", gestion_views.revision_aprobar, name="revision_aprobar"),
    path("revision/<int:pk>/rechazar/", gestion_views.revision_rechazar, name="revision_rechazar"),
]
