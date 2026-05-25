from django.db import models
from apps.accounts.models import Empresa, User


class Area(models.Model):
    codigo = models.CharField(max_length=6, unique=True, blank=True, null=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="areas")
    nombre = models.CharField(max_length=200, db_index=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "area"
        verbose_name = "Area"
        verbose_name_plural = "Areas"

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

    def save(self, *args, **kwargs):
        if not self.codigo:
            from apps.core.utils import generar_codigo
            self.codigo = generar_codigo()
        super().save(*args, **kwargs)


class SubArea(models.Model):
    codigo = models.CharField(max_length=6, unique=True, blank=True, null=True)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="subareas")
    nombre = models.CharField(max_length=200, db_index=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subarea"
        verbose_name = "SubArea"
        verbose_name_plural = "SubAreas"

    def __str__(self):
        return f"{self.nombre} ({self.area.nombre})"

    def save(self, *args, **kwargs):
        if not self.codigo:
            from apps.core.utils import generar_codigo
            self.codigo = generar_codigo()
        super().save(*args, **kwargs)


class UserSubArea(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="subareas")
    subarea = models.ForeignKey(SubArea, on_delete=models.PROTECT, related_name="usuarios")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_subarea"
        verbose_name = "Usuario-SubArea"
        verbose_name_plural = "Usuarios-SubAreas"
        unique_together = ["user", "subarea"]

    def __str__(self):
        return f"{self.user} - {self.subarea}"
