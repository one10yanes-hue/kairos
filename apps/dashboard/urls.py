from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("dashboard/", views.dashboard_admin, name="dashboard_admin"),
    path("progreso/", views.progreso, name="progreso"),
    path("linea-tiempo/", views.linea_tiempo, name="linea_tiempo"),
]
