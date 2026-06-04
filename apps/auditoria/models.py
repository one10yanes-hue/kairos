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


class AuditLogChange(models.Model):
    log = models.ForeignKey(AuditLog, on_delete=models.CASCADE, related_name="changes")
    campo = models.CharField(max_length=100)
    valor_anterior = models.TextField(blank=True, null=True)
    valor_nuevo = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "audit_log_change"
        verbose_name = "Cambio en Auditoria"
        verbose_name_plural = "Cambios en Auditoria"

    def __str__(self):
        return f"{self.campo}: '{self.valor_anterior}' -> '{self.valor_nuevo}'"


class AuditSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sesiones")
    session_key = models.CharField(max_length=40, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    inicio = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "audit_session"
        verbose_name = "Sesion de Usuario"
        verbose_name_plural = "Sesiones de Usuario"
        ordering = ["-inicio"]

    def __str__(self):
        return f"{self.user} - {self.inicio}"


class SyncLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="syncs")
    accion = models.CharField(max_length=30)
    valor_anterior = models.JSONField(default=dict, blank=True)
    valor_nuevo = models.JSONField(default=dict, blank=True)
    ejecutado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="syncs_ejecutados")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sync_log"
        verbose_name = "Log de Sincronizacion"
        verbose_name_plural = "Logs de Sincronizacion"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Sync: {self.accion} - {self.user}"
