from django.contrib import admin
from .models import Area, SubArea, UserSubArea


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "empresa", "activo"]
    search_fields = ["nombre"]


@admin.register(SubArea)
class SubAreaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "area", "activo"]
    search_fields = ["nombre"]


@admin.register(UserSubArea)
class UserSubAreaAdmin(admin.ModelAdmin):
    list_display = ["user", "subarea", "activo"]
