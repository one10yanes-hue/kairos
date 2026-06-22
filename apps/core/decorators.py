from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """Decorador para vistas que requieren rol Master o Admin (incluye roles_adicionales)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("root")
        # Verificar rol actual y roles adicionales
        if request.user.rol.nombre in ["Master", "Admin"]:
            return view_func(request, *args, **kwargs)
        if request.user.tiene_rol_admin():
            return view_func(request, *args, **kwargs)
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("root")
    return wrapper


def master_required(view_func):
    """Decorador para vistas que requieren rol Master."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("root")
        if request.user.rol.nombre == "Master":
            return view_func(request, *args, **kwargs)
        if hasattr(request.user, 'roles_adicionales') and request.user.roles_adicionales.filter(nombre="Master").exists():
            return view_func(request, *args, **kwargs)
        messages.error(request, "Solo el Master puede acceder a esta seccion.")
        return redirect("accounts:master_usuarios") if request.user.rol.nombre == "Admin" else redirect("gestion:tablero")
    return wrapper
