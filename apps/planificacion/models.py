from django.db import models
from apps.accounts.models import User
from apps.estructura.models import SubArea
from apps.actividades.models import Actividad


class Planificacion(models.Model):
    admin = models.ForeignKey(User, on_delete=models.PROTECT, related_name="planificaciones")
    subarea = models.ForeignKey(SubArea, on_delete=models.PROTECT, related_name="planificaciones")
    nombre = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True, null=True)
    cerrada = models.BooleanField(default=False, help_text="Al cerrar una planificacion no se pueden agregar mas actividades")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "planificacion"
        verbose_name = "Planificacion"
        verbose_name_plural = "Planificaciones"

    def __str__(self):
        return self.nombre


class PlanificacionDetalle(models.Model):
    planificacion = models.ForeignKey(Planificacion, on_delete=models.PROTECT, related_name="detalles")
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="planificaciones_detalle")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="planificaciones_asignadas")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "planificacion_detalle"
        verbose_name = "Detalle de Planificacion"
        verbose_name_plural = "Detalles de Planificacion"
        unique_together = ["planificacion", "actividad", "user"]

    def __str__(self):
        return f"{self.planificacion.nombre} - {self.actividad.nombre} -> {self.user}"
