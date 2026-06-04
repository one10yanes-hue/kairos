from django.db import models
from apps.accounts.models import Empresa, User


class EmpresaArea(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="areas_funcionales")
    area = models.ForeignKey("Area", on_delete=models.PROTECT, related_name="relaciones_empresas")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "empresa_area"
        verbose_name = "Empresa-Area"
        verbose_name_plural = "Empresas-Areas"
        unique_together = ["empresa", "area"]

    def __str__(self):
        return f"{self.empresa.nombre} → {self.area.nombre}"


class EmpresaSubArea(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="subareas_funcionales")
    subarea = models.ForeignKey("SubArea", on_delete=models.PROTECT, related_name="empresas_permitidas")
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "empresa_subarea"
        verbose_name = "Empresa-SubArea"
        verbose_name_plural = "Empresas-SubAreas"
        unique_together = ["empresa", "subarea"]

    def __str__(self):
        return f"{self.empresa.nombre} → {self.subarea.nombre}"


class Area(models.Model):
    codigo = models.CharField(max_length=6, unique=True, blank=True)
    nombre = models.CharField(max_length=200, db_index=True, unique=True)
    empresas = models.ManyToManyField(Empresa, through=EmpresaArea, related_name="areas_m2m")
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "area"
        verbose_name = "Area"
        verbose_name_plural = "Areas"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            from apps.core.utils import generar_codigo
            self.codigo = generar_codigo()
        super().save(*args, **kwargs)


class SubArea(models.Model):
    codigo = models.CharField(max_length=6, unique=True, blank=True)
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
        unique_together = ["area", "nombre"]

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
