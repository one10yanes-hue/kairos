from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("cedula", "get_full_name", "rol", "maneja_proyectos", "is_active")
    list_filter = ("rol", "maneja_proyectos", "is_active")
    search_fields = ("cedula", "nombre", "apellido")
