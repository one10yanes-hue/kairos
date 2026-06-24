from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from . import views as config_views
from apps.planificacion import views as planificacion_views

from django.conf import settings
from django.conf.urls.static import static

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
    path("admin/", config_views.admin_root, name="admin_root"),
    path("admin/", include("apps.dashboard.urls")),
    path("admin/", include("apps.actividades.urls")),
    path("admin/", include("apps.planificacion.urls")),
    path("admin/", include("apps.reportes.urls")),

    path("proyectos/", include("apps.proyectos.urls")),

    path("usuario/", include("apps.gestion.urls")),
    path("usuario/planificaciones/", planificacion_views.planificacion_self_list, name="planificacion_self_list"),
    path("usuario/planificaciones/crear/", planificacion_views.planificacion_self_create, name="planificacion_self_create"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    path("<path:path>", config_views.catch_all_404),
]

handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
