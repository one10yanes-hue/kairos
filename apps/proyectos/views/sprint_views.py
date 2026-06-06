from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, Sprint
from ..decorators import miembro_requerido, ROLES_EDICION


@miembro_requerido()
def sprint_list(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprints = proyecto.sprints.filter(activo=True)
    return render(request, "proyectos/sprint_list.html", {"proyecto": proyecto, "sprints": sprints})


@miembro_requerido(ROLES_EDICION)
def sprint_create(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if not nombre:
            messages.error(request, "El nombre es obligatorio.")
            return redirect("proyectos:sprint_list", pk=proyecto.pk)
        ultimo = Sprint.objects.filter(proyecto=proyecto).count()
        sprint = Sprint.objects.create(
            proyecto=proyecto,
            nombre=nombre,
            objetivo=request.POST.get("objetivo", ""),
            numero=ultimo + 1,
            fecha_inicio=request.POST.get("fecha_inicio") or None,
            fecha_fin=request.POST.get("fecha_fin") or None,
        )
        historias_ids = request.POST.getlist("historias")
        if historias_ids:
            proyecto.historias.filter(pk__in=historias_ids).update(sprint=sprint, estado="sprint_backlog")
        messages.success(request, f"Sprint {sprint.numero} creado.")
        return redirect("proyectos:sprint_list", pk=proyecto.pk)
    historias = proyecto.historias.filter(activo=True, estado="backlog")
    return render(request, "proyectos/sprint_form.html", {"proyecto": proyecto, "historias": historias})


@miembro_requerido()
def sprint_board(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    tareas = sprint.tareas.filter(activo=True).select_related("asignado_a", "historia")
    return render(request, "proyectos/sprint_board.html", {
        "proyecto": proyecto, "sprint": sprint, "tareas": tareas,
        "pendientes": tareas.filter(estado="pendiente"),
        "en_curso": tareas.filter(estado__in=["en_curso", "pausada"]),
        "finalizadas": tareas.filter(estado="finalizada"),
    })


@login_required
def sprint_burndown(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    from django.utils import timezone
    from datetime import timedelta
    hoy = timezone.now().date()
    dias_labels = []
    ideal = []
    pts = sprint.puntos_comprometidos
    if sprint.fecha_inicio and sprint.fecha_fin:
        total_dias = max((sprint.fecha_fin - sprint.fecha_inicio).days + 1, 1)
        dias_labels = [(sprint.fecha_inicio + timedelta(days=i)).strftime("%d/%m") for i in range(total_dias)]
        paso = pts / max(total_dias - 1, 1) if total_dias > 1 else 0
        ideal = [max(0, round(pts - paso * i, 1)) for i in range(total_dias)]
    return render(request, "proyectos/sprint_burndown.html", {
        "proyecto": proyecto, "sprint": sprint,
        "dias": dias_labels, "ideal": ideal, "pts_inicio": pts,
    })


@miembro_requerido(ROLES_EDICION)
def sprint_finalizar(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    if request.method == "POST":
        from ..models import RegistroAvance
        sprint.estado = "finalizado"
        sprint.save()
        for h in sprint.historias.filter(activo=True):
            if h.estado in ["revision", "done"]:
                h.estado = "done"
                h.save()
                RegistroAvance.objects.create(proyecto=proyecto, tipo="historia_completada",
                    descripcion=f"Historia {h.codigo} completada en Sprint {sprint.numero}", user=request.user, referencia_id=h.pk)
            else:
                h.estado = "backlog"
                h.sprint = None
                h.save()
        RegistroAvance.objects.create(proyecto=proyecto, tipo="sprint_finalizado",
            descripcion=f"Sprint {sprint.numero} finalizado. Velocidad: {sprint.velocidad} pts.", user=request.user, referencia_id=sprint.pk)
        messages.success(request, f"Sprint {sprint.numero} finalizado. Velocidad: {sprint.velocidad} pts.")
        return redirect("proyectos:sprint_list", pk=proyecto.pk)
    return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)


@miembro_requerido(ROLES_EDICION)
def sprint_iniciar(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    if sprint.estado != "planificado":
        messages.error(request, "Solo se pueden iniciar sprints planificados.")
        return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
    if request.method == "POST":
        sprint.estado = "activo"
        sprint.save()
        # Activar todas las tareas del sprint: crear AsignacionActividad
        activadas = 0
        from ..signals import crear_asignacion_desde_tarea
        from apps.gestion.views import _notificar_usuario
        for t in sprint.tareas.filter(activo=True, asignacion__isnull=True, asignado_a__isnull=False):
            asig = crear_asignacion_desde_tarea(t)
            if asig:
                _notificar_usuario(t.asignado_a.pk, "nueva_asignacion", {"actividad": t.titulo, "fecha_programada": ""})
                activadas += 1
        messages.success(request, f"Sprint {sprint.numero} iniciado. {activadas} tareas activadas en tableros.")
        return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
    return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    if request.method == "POST":
        from ..models import RegistroAvance
        sprint.estado = "finalizado"
        sprint.save()
        for h in sprint.historias.filter(activo=True):
            if h.estado in ["revision", "done"]:
                h.estado = "done"
                h.save()
                RegistroAvance.objects.create(proyecto=proyecto, tipo="historia_completada",
                    descripcion=f"Historia {h.codigo} completada en Sprint {sprint.numero}", user=request.user, referencia_id=h.pk)
            else:
                h.estado = "backlog"
                h.sprint = None
                h.save()
        RegistroAvance.objects.create(proyecto=proyecto, tipo="sprint_finalizado",
            descripcion=f"Sprint {sprint.numero} finalizado. Velocidad: {sprint.velocidad} pts.", user=request.user, referencia_id=sprint.pk)
        messages.success(request, f"Sprint {sprint.numero} finalizado. Velocidad: {sprint.velocidad} pts.")
        return redirect("proyectos:sprint_list", pk=proyecto.pk)
    return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
