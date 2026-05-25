from django.contrib import admin
from .models import Rol, User, Empresa, UserEmpresa


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activo", "fecha_creacion"]
    search_fields = ["nombre"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["cedula", "nombre", "apellido", "rol", "is_active", "activo"]
    search_fields = ["cedula", "nombre", "apellido"]
    list_filter = ["rol", "is_active"]


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "nit", "activo"]
    search_fields = ["nombre", "nit"]


@admin.register(UserEmpresa)
class UserEmpresaAdmin(admin.ModelAdmin):
    list_display = ["user", "empresa", "activo"]
