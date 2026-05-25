from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["accion", "modelo_afectado", "user", "fecha_creacion"]
    list_filter = ["accion", "modelo_afectado"]
    search_fields = ["modelo_afectado", "detalle"]
    readonly_fields = ["user", "accion", "modelo_afectado", "id_registro", "detalle", "ip_address", "fecha_creacion"]
