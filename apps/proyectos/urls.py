from django.urls import path
from .views import proyecto_views, backlog_views, sprint_views, tarea_views, incidencia_views

app_name = "proyectos"

urlpatterns = [
    path("", proyecto_views.proyecto_list, name="proyecto_list"),
    path("crear/", proyecto_views.proyecto_create, name="proyecto_create"),
    path("<int:pk>/", proyecto_views.proyecto_detail, name="proyecto_detail"),
    path("<int:pk>/editar/", proyecto_views.proyecto_edit, name="proyecto_edit"),
    path("<int:pk>/equipo/", proyecto_views.proyecto_equipo, name="proyecto_equipo"),
    # Backlog
    path("<int:pk>/backlog/", backlog_views.backlog_view, name="backlog"),
    path("<int:pk>/backlog/reordenar/", backlog_views.backlog_reordenar, name="backlog_reordenar"),
    path("<int:pk>/historias/crear/", backlog_views.historia_create, name="historia_create"),
    path("<int:pk>/historias/<int:hid>/editar/", backlog_views.historia_edit, name="historia_edit"),
    path("<int:pk>/historias/<int:hid>/aprobar/", backlog_views.historia_aprobar, name="historia_aprobar"),
    path("<int:pk>/historias/<int:hid>/rechazar/", backlog_views.historia_rechazar, name="historia_rechazar"),
    path("<int:pk>/historias/<int:hid>/comentarios/", backlog_views.historia_comentarios, name="historia_comentarios"),
    # Sprints
    path("<int:pk>/sprints/", sprint_views.sprint_list, name="sprint_list"),
    path("<int:pk>/sprints/crear/", sprint_views.sprint_create, name="sprint_create"),
    path("<int:pk>/sprints/<int:spk>/editar/", sprint_views.sprint_edit, name="sprint_edit"),
    path("<int:pk>/sprints/<int:spk>/", sprint_views.sprint_board, name="sprint_board"),
    path("<int:pk>/sprints/<int:spk>/burndown/", sprint_views.sprint_burndown, name="sprint_burndown"),
    path("<int:pk>/sprints/<int:spk>/finalizar/", sprint_views.sprint_finalizar, name="sprint_finalizar"),
    path("<int:pk>/sprints/<int:spk>/iniciar/", sprint_views.sprint_iniciar, name="sprint_iniciar"),
    path("<int:pk>/sprints/<int:spk>/cancelar/", sprint_views.sprint_cancelar, name="sprint_cancelar"),
    # Tareas
    path("<int:pk>/tareas/", tarea_views.tarea_list, name="tarea_list"),
    path("<int:pk>/tareas/crear/", tarea_views.tarea_create, name="tarea_create"),
    path("<int:pk>/tareas/<int:tid>/", tarea_views.tarea_detail, name="tarea_detail"),
    path("<int:pk>/tareas/<int:tid>/editar/", tarea_views.tarea_edit, name="tarea_edit"),
    path("<int:pk>/tareas/<int:tid>/activar/", tarea_views.tarea_activar, name="tarea_activar"),
    path("<int:pk>/tareas/<int:tid>/mover/", tarea_views.tarea_mover, name="tarea_mover"),
    path("<int:pk>/tareas/<int:tid>/aprobar/", tarea_views.tarea_aprobar, name="tarea_aprobar"),
    path("<int:pk>/tareas/<int:tid>/rechazar/", tarea_views.tarea_rechazar, name="tarea_rechazar"),
    # Incidencias
    path("<int:pk>/incidencias/", incidencia_views.incidencia_list, name="incidencia_list"),
    path("<int:pk>/incidencias/crear/", incidencia_views.incidencia_create, name="incidencia_create"),
    path("<int:pk>/incidencias/<int:iid>/", incidencia_views.incidencia_detail, name="incidencia_detail"),
    path("<int:pk>/incidencias/<int:iid>/convertir/", incidencia_views.incidencia_convertir, name="incidencia_convertir"),
    # Reportes
    path("<int:pk>/gantt/", proyecto_views.proyecto_gantt, name="proyecto_gantt"),
    path("<int:pk>/estructura/", proyecto_views.proyecto_estructura, name="proyecto_estructura"),
    path("<int:pk>/workflow/", proyecto_views.proyecto_workflow, name="proyecto_workflow"),
    path("<int:pk>/toggle/", proyecto_views.proyecto_toggle_activo, name="proyecto_toggle_activo"),
]
