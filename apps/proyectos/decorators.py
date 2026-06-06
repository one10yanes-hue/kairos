"""Decoradores y helpers de autorización para proyectos.
   Controlan el acceso a vistas y acciones basado en membresía y rol."""
from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Proyecto, MiembroProyecto

# Roles que pueden editar/crear contenido en el proyecto
ROLES_EDICION = ["lider", "responsable", "ejecutor"]
# Roles que pueden administrar el proyecto (equipo, cierre, etc.)
ROLES_ADMIN = ["lider", "responsable"]
# Cualquier miembro puede ver el proyecto
ROLES_VISUALIZACION = ["lider", "responsable", "revisor", "aprobador", "ejecutor", "observador"]


def miembro_requerido(roles_permitidos=None):
    """Decorador: requiere que el usuario sea miembro del proyecto con un rol permitido.
       El primer argumento de la vista debe ser 'pk' (ID del proyecto).
       Si no se especifican roles, cualquier miembro puede acceder."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, pk, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("root")
            proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
            # Master y Admin global siempre pueden acceder
            if request.user.rol.nombre in ["Master", "Admin"]:
                request.proyecto = proyecto
                request.membresia = None
                return view_func(request, pk, *args, **kwargs)
            # Verificar membresía
            membresia = MiembroProyecto.objects.filter(
                proyecto=proyecto, user=request.user, activo=True
            ).first()
            if not membresia:
                messages.error(request, "No eres miembro de este proyecto.")
                return redirect("proyectos:proyecto_list")
            if roles_permitidos and membresia.rol not in roles_permitidos:
                messages.error(request, "No tienes permisos para esta accion.")
                return redirect("proyectos:proyecto_detail", pk=proyecto.pk)
            request.proyecto = proyecto
            request.membresia = membresia
            return view_func(request, pk, *args, **kwargs)
        return wrapper
    return decorator


def proyecto_es_miembro(user, proyecto):
    """Verifica si un usuario es miembro activo de un proyecto."""
    if user.rol.nombre in ["Master", "Admin"]:
        return True
    return MiembroProyecto.objects.filter(
        proyecto=proyecto, user=user, activo=True
    ).exists()
