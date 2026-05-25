from django.db import models
from django.core.exceptions import ValidationError
from apps.estructura.models import SubArea


class TipoActividad(models.Model):
    codigo = models.CharField(max_length=6, unique=True, blank=True, null=True)
    subarea = models.ForeignKey(SubArea, on_delete=models.PROTECT, related_name="tipos_actividad")
    nombre = models.CharField(max_length=200, db_index=True)
    descripcion = models.TextField(blank=True, null=True)
    requiere_fecha_limite = models.BooleanField(default=True, help_text="Si esta activo, al planificar esta actividad la fecha limite sera obligatoria")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tipo_actividad"
        verbose_name = "Tipo de Actividad"
        verbose_name_plural = "Tipos de Actividad"

    def __str__(self):
        return f"{self.nombre} ({self.subarea.nombre})"

    def save(self, *args, **kwargs):
        if not self.codigo:
            from apps.core.utils import generar_codigo
            self.codigo = generar_codigo()
        super().save(*args, **kwargs)


class Actividad(models.Model):
    codigo = models.CharField(max_length=6, unique=True, blank=True, null=True)
    subarea = models.ForeignKey(SubArea, on_delete=models.PROTECT, related_name="actividades")
    tipo_actividad = models.ForeignKey(TipoActividad, on_delete=models.PROTECT, related_name="actividades")
    nombre = models.CharField(max_length=300, db_index=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "actividad"
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"

    def __str__(self):
        return self.nombre

    def clean(self):
        if self.tipo_actividad and self.tipo_actividad.subarea_id != self.subarea_id:
            raise ValidationError("La actividad debe pertenecer a la misma subarea que su tipo de actividad.")

    def save(self, *args, **kwargs):
        self.clean()
        if not self.codigo:
            from apps.core.utils import generar_codigo
            self.codigo = generar_codigo()
        super().save(*args, **kwargs)
