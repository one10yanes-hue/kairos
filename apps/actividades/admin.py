from django.contrib import admin
from .models import TipoActividad, Actividad


@admin.register(TipoActividad)
class TipoActividadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "subarea", "activo"]


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "subarea", "tipo_actividad", "activo"]
