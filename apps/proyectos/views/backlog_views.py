from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, HistoriaUsuario


@login_required
def backlog_view(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    historias = proyecto.historias.filter(activo=True)
    return render(request, "proyectos/backlog.html", {"proyecto": proyecto, "historias": historias})


@login_required
def historia_create(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        if not titulo:
            messages.error(request, "El titulo es obligatorio.")
            return redirect("proyectos:backlog", pk=proyecto.pk)
        historia = HistoriaUsuario.objects.create(
            proyecto=proyecto,
            titulo=titulo,
            descripcion=request.POST.get("descripcion", ""),
            criterios_aceptacion=request.POST.get("criterios", ""),
            prioridad=request.POST.get("prioridad", "should"),
            puntos_historia=int(request.POST.get("puntos", 0) or 0),
            creador=request.user,
        )
        historia.codigo = f"{proyecto.codigo}-US-{historia.pk:03d}"
        historia.save()
        messages.success(request, f"Historia {historia.codigo} creada.")
        return redirect("proyectos:backlog", pk=proyecto.pk)
    return render(request, "proyectos/historia_form.html", {"proyecto": proyecto})


@login_required
def historia_edit(request, pk, hid):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    historia = get_object_or_404(HistoriaUsuario, pk=hid, proyecto=proyecto, activo=True)
    if request.method == "POST":
        historia.titulo = request.POST.get("titulo", historia.titulo)
        historia.descripcion = request.POST.get("descripcion", historia.descripcion)
        historia.criterios_aceptacion = request.POST.get("criterios", historia.criterios_aceptacion)
        historia.prioridad = request.POST.get("prioridad", historia.prioridad)
        historia.puntos_historia = int(request.POST.get("puntos", 0) or 0)
        historia.estado = request.POST.get("estado", historia.estado)
        if request.POST.get("sprint_id"):
            from ..models import Sprint
            historia.sprint = get_object_or_404(Sprint, pk=request.POST.get("sprint_id"), proyecto=proyecto)
        historia.save()
        messages.success(request, "Historia actualizada.")
        return redirect("proyectos:backlog", pk=proyecto.pk)
    return render(request, "proyectos/historia_form.html", {"proyecto": proyecto, "historia": historia, "editando": True})
