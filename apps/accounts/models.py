import os
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


def foto_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1] or ".jpg"
    return f"profile/{instance.cedula}{ext}"


class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rol"
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.nombre


class UserManager(BaseUserManager):
    def create_user(self, cedula, fecha_expedicion, password=None, **extra_fields):
        if not cedula:
            raise ValueError("La cedula es obligatoria")
        if not fecha_expedicion:
            raise ValueError("La fecha de expedicion es obligatoria")
        email = extra_fields.get("email", "")
        if email:
            email = self.normalize_email(email)
        user = self.model(cedula=cedula, fecha_expedicion=fecha_expedicion, email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, cedula, fecha_expedicion, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(cedula, fecha_expedicion, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    cedula = models.CharField(max_length=20, unique=True)
    fecha_expedicion = models.DateField()
    nombre = models.CharField(max_length=100, db_index=True)
    apellido = models.CharField(max_length=100, db_index=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    cargo = models.CharField(max_length=200, blank=True, null=True)
    foto = models.ImageField(upload_to=foto_upload_path, blank=True, null=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name="usuarios")
    roles_adicionales = models.ManyToManyField(Rol, blank=True, related_name="usuarios_extra")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "cedula"
    REQUIRED_FIELDS = ["fecha_expedicion", "nombre", "apellido"]

    objects = UserManager()

    class Meta:
        db_table = "usuario"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.cedula})"

    def get_full_name(self):
        return f"{self.nombre} {self.apellido}"

    def get_short_name(self):
        return self.nombre

    def tiene_rol(self, rol_id):
        if self.rol_id == rol_id or self.roles_adicionales.filter(pk=rol_id).exists():
            return True
        # Revisar rol primario original en BD (el middleware cambia self.rol_id)
        return type(self).objects.filter(pk=self.pk, rol_id=rol_id).exists()

    def roles_disponibles(self):
        # Obtener rol original desde BD (el middleware cambia self.rol en memoria)
        db = User.objects.values_list("rol_id", flat=True).get(pk=self.pk)
        return Rol.objects.filter(
            models.Q(pk=db) | models.Q(usuarios_extra=self)
        ).distinct()

    def save(self, *args, **kwargs):
        self.is_active = self.activo
        super().save(*args, **kwargs)


class Empresa(models.Model):
    codigo = models.CharField(max_length=6, unique=True, blank=True)
    nombre = models.CharField(max_length=200, db_index=True)
    nit = models.CharField(max_length=50, unique=True)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "empresa"
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def save(self, *args, **kwargs):
        if not self.codigo:
            from apps.core.utils import generar_codigo
            self.codigo = generar_codigo()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class UserEmpresa(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="empresas")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="usuarios")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_empresa"
        verbose_name = "Usuario-Empresa"
        verbose_name_plural = "Usuarios-Empresas"
        unique_together = ["user", "empresa"]

    def __str__(self):
        return f"{self.user} - {self.empresa}"
