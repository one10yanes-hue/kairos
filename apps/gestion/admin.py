from django.contrib import admin
from .models import AsignacionActividad, RegistroTiempo, TrasladoActividad, Colaboracion, Comentario


@admin.register(AsignacionActividad)
class AsignacionActividadAdmin(admin.ModelAdmin):
    list_display = ["actividad", "user", "estado", "fecha_asignacion"]


@admin.register(RegistroTiempo)
class RegistroTiempoAdmin(admin.ModelAdmin):
    list_display = ["asignacion", "evento", "fecha_hora"]


@admin.register(TrasladoActividad)
class TrasladoActividadAdmin(admin.ModelAdmin):
    list_display = ["user_origen", "user_destino", "asignacion_origen"]


@admin.register(Colaboracion)
class ColaboracionAdmin(admin.ModelAdmin):
    list_display = ["user_colaborador", "asignacion"]


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ["user", "asignacion", "fecha_creacion"]
