from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, Incidencia, Tarea, RegistroAvance
from ..decorators import miembro_requerido, ROLES_EDICION


@miembro_requerido()
def incidencia_list(request, pk):
    proyecto = request.proyecto
    incidencias = proyecto.incidencias.filter(activo=True).select_related("reportado_por", "asignado_a")
    return render(request, "proyectos/incidencia_list.html", {"proyecto": proyecto, "incidencias": incidencias})


@miembro_requerido()
def incidencia_create(request, pk):
    proyecto = request.proyecto
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
        adjunto_file = request.FILES.get("adjunto")
        if adjunto_file:
            inc.adjunto = adjunto_file
        inc.codigo = f"{proyecto.codigo}-INC-{inc.pk:03d}"
        inc.save()
        RegistroAvance.objects.create(proyecto=proyecto, tipo="incidencia_creada",
            descripcion=f"Incidencia {inc.codigo} reportada: {inc.titulo[:60]}", user=request.user)
        # Notificar a lider y responsable del proyecto
        from apps.gestion.views import _notificar_usuario
        for m in proyecto.membresias.filter(activo=True, rol__in=["lider","responsable"]):
            _notificar_usuario(m.user_id, "incidencia_reportada", {
                "codigo": inc.codigo, "titulo": inc.titulo
            })
        messages.success(request, f"Incidencia {inc.codigo} reportada.")
        return redirect("proyectos:incidencia_list", pk=proyecto.pk)
    miembros = proyecto.membresias.filter(activo=True).select_related("user")
    return render(request, "proyectos/incidencia_form.html", {"proyecto": proyecto, "miembros": miembros})


@miembro_requerido(ROLES_EDICION)
def incidencia_convertir(request, pk, iid):
    proyecto = request.proyecto
    incidencia = get_object_or_404(Incidencia, pk=iid, proyecto=proyecto)
    if request.method == "POST":
        from ..models import Tarea
        from ..signals import crear_asignacion_desde_tarea
        tarea = Tarea.objects.create(
            proyecto=proyecto,
            titulo=incidencia.titulo,
            descripcion=incidencia.descripcion,
            tipo="bug" if incidencia.tipo == "bug" else "mejora",
            asignado_a=incidencia.asignado_a,
            creador=request.user,
        )
        tarea.codigo = f"{proyecto.codigo}-T-{tarea.pk:03d}"
        tarea.full_clean()
        tarea.save()
        incidencia.tarea = tarea
        incidencia.estado = "en_progreso"
        incidencia.full_clean()
        incidencia.save()
        RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
            descripcion=f"Incidencia {incidencia.codigo} convertida a Tarea {tarea.codigo} por {request.user.get_full_name()}",
            user=request.user, referencia_id=tarea.pk)
        if tarea.asignado_a:
            crear_asignacion_desde_tarea(tarea)
        messages.success(request, f"Incidencia {incidencia.codigo} convertida a Tarea {tarea.codigo}.")
        return redirect("proyectos:incidencia_detail", pk=proyecto.pk, iid=incidencia.pk)


@miembro_requerido()
def incidencia_detail(request, pk, iid):
    proyecto = request.proyecto
    incidencia = get_object_or_404(Incidencia, pk=iid, proyecto=proyecto)
    membresia = request.membresia
    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")
        if nuevo_estado in dict(Incidencia.ESTADOS):
            # Restricciones de rol
            if membresia and membresia.rol == "observador":
                messages.error(request, "Los observadores no pueden cambiar estados.")
            else:
                incidencia.estado = nuevo_estado
                if nuevo_estado in ["cerrada", "resuelta"]:
                    from django.utils import timezone
                    incidencia.fecha_resolucion = timezone.now()
                incidencia.full_clean()
                incidencia.save()
                RegistroAvance.objects.create(proyecto=proyecto, tipo="incidencia_resuelta",
                    descripcion=f"Incidencia {incidencia.codigo} cambiada a '{incidencia.get_estado_display()}' por {request.user.get_full_name()}",
                    user=request.user, referencia_id=incidencia.pk)
                messages.success(request, f"Incidencia {incidencia.codigo} actualizada.")
        return redirect("proyectos:incidencia_detail", pk=proyecto.pk, iid=incidencia.pk)
    miembros = proyecto.membresias.filter(activo=True).select_related("user")
    return render(request, "proyectos/incidencia_detail.html", {
        "proyecto": proyecto, "incidencia": incidencia, "miembros": miembros
    })
