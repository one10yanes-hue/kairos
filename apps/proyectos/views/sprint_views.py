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


@login_required
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


@login_required
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
