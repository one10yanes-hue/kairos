from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..models import Proyecto, HistoriaUsuario
from ..decorators import miembro_requerido, ROLES_EDICION, ROLES_ADMIN
import json


@miembro_requerido(ROLES_ADMIN)
def historia_aprobar(request, pk, hid):
    proyecto = request.proyecto
    historia = get_object_or_404(HistoriaUsuario, pk=hid, proyecto=proyecto, activo=True)
    if historia.estado == "revision":
        historia.estado = "done"
        historia.save()
        messages.success(request, f"Historia {historia.codigo} aprobada como Done.")
    return redirect("proyectos:backlog", pk=proyecto.pk)


@miembro_requerido()
def backlog_view(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    historias = proyecto.historias.filter(activo=True)
    return render(request, "proyectos/backlog.html", {"proyecto": proyecto, "historias": historias})


@miembro_requerido(ROLES_EDICION)
def backlog_reordenar(request, pk):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            for item in data.get("ordenes", []):
                HistoriaUsuario.objects.filter(pk=item["id"], proyecto_id=pk).update(orden=item["orden"])
        except Exception:
            pass
    return JsonResponse({"ok": True})


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
