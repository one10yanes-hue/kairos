from django.db import models
from apps.accounts.models import User


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="auditoria")
    accion = models.CharField(max_length=50)
    modelo_afectado = models.CharField(max_length=100)
    id_registro = models.IntegerField(null=True, blank=True)
    detalle = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.accion} - {self.modelo_afectado} (#{self.id_registro}) por {self.user}"
