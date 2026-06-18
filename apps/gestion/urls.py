from django.urls import path
from . import views
from apps.accounts import views as accounts_views

app_name = "gestion"

urlpatterns = [
    path("tablero/", views.tablero, name="tablero"),
    path("actividad/<int:pk>/iniciar/", views.activar_actividad, name="activar_actividad"),
    path("actividad/<int:pk>/pausar/", views.pausar_actividad, name="pausar_actividad"),
    path("actividad/<int:pk>/finalizar/", views.finalizar_actividad, name="finalizar_actividad"),
    path("actividad/<int:pk>/trasladar/", views.trasladar_actividad, name="trasladar_actividad"),
    path("actividad/<int:pk>/comentar/", views.agregar_comentario, name="agregar_comentario"),
    path("actividad/<int:pk>/detalle/", views.detalle_actividad, name="detalle_actividad"),
    path("actividad/no-programada/crear/", views.crear_no_programada, name="crear_no_programada"),
    path("api/usuarios/buscar/", views.buscar_usuarios_traslado, name="buscar_usuarios"),
    path("api/asignacion/<int:pk>/proyecto/", views.asignacion_proyecto, name="asignacion_proyecto"),
    path("api/actividades/buscar/", views.buscar_actividades_reemplazo, name="buscar_actividades"),
    path("calendario/", views.calendario, name="calendario"),
    path("traslado/<int:pk>/aceptar/", views.aceptar_traslado, name="aceptar_traslado"),
    path("traslado/<int:pk>/cancelar/", views.cancelar_traslado, name="cancelar_traslado"),
    path("api/traslados/pendientes/", views.api_traslados_pendientes, name="api_traslados_pendientes"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/subir-foto/", accounts_views.subir_foto, name="subir_foto"),
    path("revisiones/", views.revisiones_list, name="revisiones"),
    path("revision/<int:pk>/aprobar/", views.revision_aprobar, name="revision_aprobar"),
    path("revision/<int:pk>/rechazar/", views.revision_rechazar, name="revision_rechazar"),
]
