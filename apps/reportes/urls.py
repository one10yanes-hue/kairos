from django.urls import path
from . import views

app_name = "reportes"

urlpatterns = [
    path("reportes/", views.reporte_list, name="reporte_list"),
    path("reportes/exportar/", views.exportar_completo, name="exportar_completo"),
]
