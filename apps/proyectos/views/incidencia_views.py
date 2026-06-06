from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, Incidencia, Tarea


@login_required
def incidencia_list(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    incidencias = proyecto.incidencias.filter(activo=True).select_related("reportado_por", "asignado_a")
    return render(request, "proyectos/incidencia_list.html", {"proyecto": proyecto, "incidencias": incidencias})


@login_required
def incidencia_create(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        if not titulo:
            messages.error(request, "El titulo es obligatorio.")
            return redirect("proyectos:incidencia_list", pk=proyecto.pk)
        inc = Incidencia.objects.create(
            proyecto=proyecto,
            titulo=titulo,
            descripcion=request.POST.get("descripcion", ""),
            tipo=request.POST.get("tipo", "bug"),
            severidad=request.POST.get("severidad", "media"),
            reportado_por=request.user,
            asignado_a_id=request.POST.get("user_id") or None,
        )
        inc.codigo = f"{proyecto.codigo}-INC-{inc.pk:03d}"
        inc.save()
        messages.success(request, f"Incidencia {inc.codigo} reportada.")
        return redirect("proyectos:incidencia_list", pk=proyecto.pk)
    miembros = proyecto.membresias.filter(activo=True).select_related("user")
    return render(request, "proyectos/incidencia_form.html", {"proyecto": proyecto, "miembros": miembros})


@login_required
def incidencia_detail(request, pk, iid):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    incidencia = get_object_or_404(Incidencia, pk=iid, proyecto=proyecto)
    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")
        if nuevo_estado in dict(Incidencia.ESTADOS):
            incidencia.estado = nuevo_estado
            if nuevo_estado == "cerrada":
                from django.utils import timezone
                incidencia.fecha_resolucion = timezone.now()
            incidencia.save()
            messages.success(request, f"Incidencia {incidencia.codigo} actualizada.")
        return redirect("proyectos:incidencia_detail", pk=proyecto.pk, iid=incidencia.pk)
    miembros = proyecto.membresias.filter(activo=True).select_related("user")
    return render(request, "proyectos/incidencia_detail.html", {
        "proyecto": proyecto, "incidencia": incidencia, "miembros": miembros
    })
