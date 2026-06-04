from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse


class RoleSwitchMiddleware:
    """Permite cambiar el rol activo del usuario via sesion."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            rol_id = request.session.get("rol_activo")
            if rol_id and hasattr(request.user, "tiene_rol"):
                if request.user.tiene_rol(rol_id):
                    from apps.accounts.models import Rol
                    try:
                        request.user.rol = Rol.objects.get(pk=rol_id)
                    except Rol.DoesNotExist:
                        del request.session["rol_activo"]
        return self.get_response(request)
