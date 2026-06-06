from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, Sprint, HistoriaUsuario, Tarea


@login_required
def tarea_list(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    tareas = proyecto.tareas.filter(activo=True).select_related("asignado_a", "historia", "sprint")
    return render(request, "proyectos/tarea_list.html", {"proyecto": proyecto, "tareas": tareas})


@login_required
def tarea_create(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        if not titulo:
            messages.error(request, "El titulo es obligatorio.")
            return redirect("proyectos:tarea_list", pk=proyecto.pk)
        tarea = Tarea.objects.create(
            proyecto=proyecto,
            titulo=titulo,
            descripcion=request.POST.get("descripcion", ""),
            tipo=request.POST.get("tipo", "tarea"),
            asignado_a_id=request.POST.get("user_id") or None,
            historia_id=request.POST.get("historia_id") or None,
            sprint_id=request.POST.get("sprint_id") or None,
            creador=request.user,
        )
        tarea.codigo = f"{proyecto.codigo}-T-{tarea.pk:03d}"
        tarea.save()
        messages.success(request, f"Tarea {tarea.codigo} creada.")
        return redirect("proyectos:tarea_list", pk=proyecto.pk)
    historias = proyecto.historias.filter(activo=True)
    sprints = proyecto.sprints.filter(activo=True)
    miembros = proyecto.membresias.filter(activo=True).select_related("user")
    return render(request, "proyectos/tarea_form.html", {
        "proyecto": proyecto, "historias": historias, "sprints": sprints, "miembros": miembros
    })


@login_required
def tarea_detail(request, pk, tid):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=proyecto)
    return render(request, "proyectos/tarea_detail.html", {"proyecto": proyecto, "tarea": tarea})
