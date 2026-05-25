from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def root_redirect(request):
    if request.user.is_authenticated:
        from apps.accounts.models import Rol
        try:
            if request.user.rol.nombre == "Master":
                return redirect("estructura:empresa_list")
            elif request.user.rol.nombre == "Admin":
                return redirect("dashboard:dashboard_admin")
            else:
                return redirect("gestion:tablero")
        except Exception:
            return redirect("gestion:tablero")
    return redirect("accounts:login")

urlpatterns = [
    path("", root_redirect, name="root"),
    path("", include("apps.accounts.urls")),
    path("master/", include("apps.estructura.urls")),
    path("admin/", include("apps.dashboard.urls")),
    path("admin/", include("apps.actividades.urls")),
    path("admin/", include("apps.planificacion.urls")),
    path("admin/", include("apps.reportes.urls")),

    path("usuario/", include("apps.gestion.urls")),
]

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
