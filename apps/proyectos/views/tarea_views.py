from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, Sprint, HistoriaUsuario, Tarea
from ..signals import crear_asignacion_desde_tarea
from ..decorators import miembro_requerido, ROLES_EDICION
from apps.actividades.models import Actividad, TipoActividad


@miembro_requerido()
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
            actividad_catalogo_id=request.POST.get("actividad_id") or None,
            historia_id=request.POST.get("historia_id") or None,
            sprint_id=request.POST.get("sprint_id") or None,
            creador=request.user,
        )
        tarea.codigo = f"{proyecto.codigo}-T-{tarea.pk:03d}"
        tarea.save()
        # Si se asigna a un usuario, crear AsignacionActividad automaticamente
        if tarea.asignado_a:
            asignacion = crear_asignacion_desde_tarea(tarea)
            if asignacion:
                messages.success(request, f"Tarea {tarea.codigo} creada y asignada a {tarea.asignado_a.get_full_name()}.")
            else:
                messages.success(request, f"Tarea {tarea.codigo} creada.")
        else:
            messages.success(request, f"Tarea {tarea.codigo} creada.")
        return redirect("proyectos:tarea_list", pk=proyecto.pk)
    historias = proyecto.historias.filter(activo=True)
    sprints = proyecto.sprints.filter(activo=True)
    miembros = proyecto.membresias.filter(activo=True).select_related("user")
    actividades = Actividad.objects.filter(subarea__in=proyecto.subareas.all(), activo=True).select_related("tipo_actividad")
    return render(request, "proyectos/tarea_form.html", {
        "proyecto": proyecto, "historias": historias, "sprints": sprints,
        "miembros": miembros, "actividades": actividades
    })


@login_required
def tarea_detail(request, pk, tid):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=proyecto)
    return render(request, "proyectos/tarea_detail.html", {"proyecto": proyecto, "tarea": tarea})


@login_required
def tarea_activar(request, pk, tid):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=proyecto)
    if request.method == "POST":
        asignacion = crear_asignacion_desde_tarea(tarea)
        if asignacion:
            messages.success(request, f"Tarea '{tarea.titulo}' activada. Aparece en el Tablero de {tarea.asignado_a.get_full_name()}.")
        else:
            messages.warning(request, "La tarea ya tiene asignacion o no tiene usuario asignado.")
    return redirect("proyectos:tarea_list", pk=proyecto.pk)
