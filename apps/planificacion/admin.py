from django.contrib import admin
from .models import Planificacion, PlanificacionDetalle


@admin.register(Planificacion)
class PlanificacionAdmin(admin.ModelAdmin):
    list_display = ["nombre", "subarea", "admin", "activo"]


@admin.register(PlanificacionDetalle)
class PlanificacionDetalleAdmin(admin.ModelAdmin):
    list_display = ["planificacion", "actividad", "user", "fecha_limite"]
