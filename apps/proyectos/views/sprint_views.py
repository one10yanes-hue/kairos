from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, Sprint


@login_required
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
