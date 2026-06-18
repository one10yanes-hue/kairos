from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ..models import Proyecto, Sprint, HistoriaUsuario, Tarea
from ..signals import crear_asignacion_desde_tarea
from ..decorators import miembro_requerido, ROLES_EDICION, ROLES_MOVER, ROLES_REVISION
from apps.actividades.models import Actividad, TipoActividad


def _miembros_asignables(proyecto, request):
    """Solo Ejecutores pueden ser asignados a tareas."""
    qs = proyecto.membresias.filter(activo=True, rol="ejecutor").select_related("user")
    if request.membresia and request.membresia.rol == "ejecutor":
        qs = qs.filter(user=request.user)
    return qs


@miembro_requerido()
def tarea_list(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    tareas = proyecto.tareas.filter(activo=True).select_related("asignado_a", "historia", "sprint")
    # Filtrar por rol del miembro
    membresia = request.membresia
    if membresia and membresia.rol == "ejecutor":
        tareas = tareas.filter(asignado_a=request.user)
    elif membresia and membresia.rol in ["revisor", "aprobador"]:
        from django.db.models import Q
        tareas = tareas.filter(Q(estado="revision") | Q(asignado_a=request.user))
    # Lider/Responsable/Observador ven todas
    return render(request, "proyectos/tarea_list.html", {"proyecto": proyecto, "tareas": tareas, "today": timezone.now().date()})


@miembro_requerido(ROLES_EDICION)
def tarea_create(request, pk):
    proyecto = request.proyecto
    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        if not titulo:
            messages.error(request, "El titulo es obligatorio.")
            return redirect("proyectos:tarea_list", pk=proyecto.pk)
        fl = request.POST.get("fecha_limite") or None
        if fl:
            from django.utils import timezone
            if fl < str(timezone.now().date()):
                messages.error(request, "La fecha limite no puede ser anterior a hoy.")
                return redirect("proyectos:tarea_list", pk=proyecto.pk)
        tarea = Tarea.objects.create(
            proyecto=proyecto,
            titulo=titulo,
            descripcion=request.POST.get("descripcion", ""),
            tipo=request.POST.get("tipo", "tarea"),
            prioridad=request.POST.get("prioridad", "should"),
            asignado_a_id=request.POST.get("user_id") or None,
            actividad_catalogo_id=request.POST.get("actividad_id") or None,
            historia_id=request.POST.get("historia_id") or None,
            sprint_id=request.POST.get("sprint_id") or None,
            fecha_limite=request.POST.get("fecha_limite") or None,
            creador=request.user,
        )
        tarea.codigo = f"{proyecto.codigo}-T-{tarea.pk:03d}"
        tarea.save()
        if tarea.asignado_a:
            asignacion = crear_asignacion_desde_tarea(tarea)
            if asignacion:
                from apps.gestion.views import _notificar_usuario
                _notificar_usuario(tarea.asignado_a.pk, "nueva_asignacion", {"actividad": tarea.titulo})
                messages.success(request, f"Tarea {tarea.codigo} creada y asignada a {tarea.asignado_a.get_full_name()}.")
            else:
                messages.success(request, f"Tarea {tarea.codigo} creada.")
        else:
            messages.success(request, f"Tarea {tarea.codigo} creada.")
        return redirect("proyectos:tarea_list", pk=proyecto.pk)
    historias = proyecto.historias.filter(activo=True)
    sprints = proyecto.sprints.filter(activo=True)
    miembros = _miembros_asignables(proyecto, request)
    actividades = Actividad.objects.filter(subarea__in=proyecto.subareas.all(), activo=True).select_related("tipo_actividad")
    return render(request, "proyectos/tarea_form.html", {
        "proyecto": proyecto, "historias": historias, "sprints": sprints, "miembros": miembros, "actividades": actividades,
        "selected_historia": request.GET.get("historia", ""),
        "selected_sprint": request.GET.get("sprint", ""),
    })


@miembro_requerido(ROLES_REVISION)
def tarea_aprobar(request, pk, tid):
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=request.proyecto, activo=True)
    if tarea.estado == "revision":
        tarea.estado = "finalizada"
        tarea.save()
        if tarea.historia:
            tarea.historia.actualizar_estado()
        # Cerrar todas las AsignacionActividad de revision
        from apps.gestion.models import AsignacionActividad
        AsignacionActividad.objects.filter(
            nombre_actividad__startswith=f"[Revisar] {tarea.codigo}:",
            activo=True
        ).update(activo=False, estado="Finalizada")
        from ..models import RegistroAvance
        RegistroAvance.objects.create(
            proyecto=request.proyecto, tipo="tarea_finalizada",
            descripcion=f"Tarea {tarea.codigo} aprobada por {request.user.get_full_name()}",
            user=request.user, referencia_id=tarea.pk
        )
        messages.success(request, f"Tarea {tarea.codigo} aprobada.")
    referer = request.META.get("HTTP_REFERER", "")
    if referer and "/usuario/tablero" in referer:
        return redirect("gestion:tablero")
    return redirect("proyectos:tarea_list", pk=request.proyecto.pk)


@miembro_requerido(ROLES_REVISION)
def tarea_rechazar(request, pk, tid):
    if request.method == "POST":
        tarea = get_object_or_404(Tarea, pk=tid, proyecto=request.proyecto, activo=True)
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo del rechazo.")
            return redirect("proyectos:tarea_list", pk=request.proyecto.pk)
        if tarea.estado == "revision" or tarea.estado == "finalizada":
            tarea.estado = "pendiente"
            tarea.save()
            # Si la tarea estaba finalizada y es rechazada, revertir AsignacionActividad
            if tarea.asignacion and tarea.asignacion.estado == "Finalizada":
                tarea.asignacion.estado = "Pendiente"
                tarea.asignacion.estado_revision = "rechazado"
                tarea.asignacion.revision_comentario = motivo
                tarea.asignacion.save()
            # Actualizar historia padre: si no todas estan finalizadas → en_progreso
            if tarea.historia:
                tarea.historia.actualizar_estado()
            from ..models import RegistroAvance
            RegistroAvance.objects.create(
                proyecto=request.proyecto, tipo="comentario",
                descripcion=f"Tarea {tarea.codigo} rechazada por {request.user.get_full_name()}: {motivo[:80]}",
                user=request.user, referencia_id=tarea.pk
            )
            if tarea.asignacion:
                tarea.asignacion.estado = "Pendiente"
                tarea.asignacion.estado_revision = "rechazado"
                tarea.asignacion.revision_comentario = motivo
                tarea.asignacion.save()
            # Crear incidencia si se solicito
            if request.POST.get("crear_bug"):
                from ..models import Incidencia
                inc = Incidencia.objects.create(
                    proyecto=request.proyecto, tarea=tarea, historia=tarea.historia,
                    titulo=f"Bug: {tarea.titulo}", descripcion=motivo,
                    tipo="bug", severidad="media", estado="abierta",
                    reportado_por=request.user,
                    asignado_a=tarea.asignado_a,
                )
                inc.codigo = f"{request.proyecto.codigo}-INC-{inc.pk:03d}"
                inc.save()
                messages.info(request, f"Incidencia {inc.codigo} creada.")
            # Notificar al Ejecutor
            if tarea.asignado_a:
                from apps.gestion.views import _notificar_usuario
                _notificar_usuario(tarea.asignado_a.pk, "tarea_rechazada", {
                    "actividad": tarea.titulo, "codigo": tarea.codigo, "motivo": motivo
                })
            messages.warning(request, f"Tarea {tarea.codigo} rechazada: {motivo}")
        referer = request.META.get("HTTP_REFERER", "")
        if referer and "/usuario/tablero" in referer:
            return redirect("gestion:tablero")
        return redirect("proyectos:tarea_list", pk=request.proyecto.pk)
    return redirect("proyectos:tarea_list", pk=request.proyecto.pk)


@miembro_requerido(ROLES_MOVER)
def tarea_mover(request, pk, tid):
    from django.http import JsonResponse
    from django.utils import timezone
    import json
    proyecto = request.proyecto
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=proyecto)
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            nuevo = data.get("estado")
            if nuevo in dict(Tarea.ESTADOS):
                tarea.estado = nuevo
                tarea.save()
                # Sincronizar AsignacionActividad del Ejecutor
                mapping_reverse = {
                    "pendiente": "Pendiente", "en_curso": "EnCurso", "pausada": "Pausada",
                    "bloqueada": "Pausada", "finalizada": "Finalizada", "revision": "Revision", "cancelada": "Cancelada",
                }
                ga_estado = mapping_reverse.get(nuevo)
                if ga_estado and tarea.asignacion:
                    old_ga = tarea.asignacion.estado
                    tarea.asignacion.estado = ga_estado
                    tarea.asignacion.save()
                    # Crear evento de tiempo para transiciones clave
                    from apps.gestion.models import RegistroTiempo
                    evento_map = {"en_curso": "Inicio", "pausada": "Pausa", "finalizada": "Finalizacion"}
                    if nuevo in evento_map and old_ga != ga_estado:
                        RegistroTiempo.objects.create(asignacion=tarea.asignacion, evento=evento_map[nuevo], fecha_hora=timezone.now())
                return JsonResponse({"ok": True})
        except Exception:
            pass
    return JsonResponse({"ok": False}, status=400)


@miembro_requerido(ROLES_EDICION)
def tarea_edit(request, pk, tid):
    proyecto = request.proyecto
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=proyecto, activo=True)
    if request.method == "POST":
        tarea.titulo = request.POST.get("titulo", tarea.titulo)
        tarea.descripcion = request.POST.get("descripcion", tarea.descripcion)
        tarea.tipo = request.POST.get("tipo", tarea.tipo)
        tarea.prioridad = request.POST.get("prioridad", tarea.prioridad)
        tarea.estado = request.POST.get("estado", tarea.estado)
        tarea.asignado_a_id = request.POST.get("user_id") or None
        tarea.historia_id = request.POST.get("historia_id") or None
        tarea.sprint_id = request.POST.get("sprint_id") or None
        tarea.actividad_catalogo_id = request.POST.get("actividad_id") or None
        tarea.fecha_limite = request.POST.get("fecha_limite") or None
        tarea.save()
        messages.success(request, "Tarea actualizada.")
        return redirect("proyectos:tarea_list", pk=proyecto.pk)
    historias = proyecto.historias.filter(activo=True)
    sprints = proyecto.sprints.filter(activo=True)
    miembros = _miembros_asignables(proyecto, request)
    actividades = Actividad.objects.filter(subarea__in=proyecto.subareas.all(), activo=True).select_related("tipo_actividad")
    return render(request, "proyectos/tarea_form.html", {
        "proyecto": proyecto, "tarea": tarea, "editando": True,
        "historias": historias, "sprints": sprints, "miembros": miembros, "actividades": actividades,
        "selected_historia": str(tarea.historia_id or ""),
        "selected_sprint": str(tarea.sprint_id or ""),
    })


@miembro_requerido()
def tarea_detail(request, pk, tid):
    proyecto = request.proyecto
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=proyecto)

    asignacion = tarea.asignacion
    registros = []
    comentarios = []
    traslados = []
    colaboraciones = []
    historial = []
    tiempo_efectivo = ""
    if asignacion:
        from apps.gestion.models import RegistroTiempo, Comentario, TrasladoActividad, Colaboracion, RevisionHistorial
        registros = RegistroTiempo.objects.filter(asignacion=asignacion, activo=True).order_by("-fecha_hora")
        comentarios = Comentario.objects.filter(asignacion=asignacion, activo=True).order_by("-fecha_creacion")
        traslados = TrasladoActividad.objects.filter(asignacion_origen=asignacion, activo=True)
        colaboraciones = Colaboracion.objects.filter(asignacion=asignacion, activo=True)
        historial = RevisionHistorial.objects.filter(asignacion=asignacion).select_related("user").order_by("-fecha")
        tiempo_efectivo = asignacion.tiempo_formateado()
        # Timeline
        timeline = []
        timeline.append({
            "fecha": tarea.fecha_creacion, "tipo": "creacion", "icono": "plus-circle",
            "descripcion": f"Tarea creada por {tarea.creador.get_full_name()}"
        })
        for r in registros:
            icono = {"Inicio": "play-fill", "Pausa": "pause-fill", "Reanudacion": "arrow-clockwise", "Finalizacion": "check-circle-fill", "Traslado": "arrow-right-circle"}.get(r.evento, "circle")
            timeline.append({
                "fecha": r.fecha_hora, "tipo": "registro", "icono": icono,
                "descripcion": f"{r.evento} por {asignacion.user.get_full_name()}"
            })
        for c in comentarios:
            timeline.append({
                "fecha": c.fecha_creacion, "tipo": "comentario", "icono": "chat-text",
                "descripcion": f"Comentario de {c.user.get_full_name()}: {c.texto[:60]}"
            })
        for t in traslados:
            timeline.append({
                "fecha": t.fecha_creacion, "tipo": "traslado", "icono": "arrow-right-circle",
                "descripcion": f"Traslado de {t.user_origen.get_full_name()} → {t.user_destino.get_full_name()} ({t.estado})"
            })
        for h in historial:
            timeline.append({
                "fecha": h.fecha, "tipo": "revision", "icono": "check-circle" if h.accion == "aprobar" else "x-circle",
                "descripcion": f"{'Aprobacion' if h.accion == 'aprobar' else 'Rechazo'} por {h.user.get_full_name()}"
            })
        # Rechazo / aprobacion de tarea (flujo nuevo de proyecto)
        if asignacion.estado_revision == "aprobado":
            timeline.append({
                "fecha": asignacion.fecha_revision or asignacion.fecha_update,
                "tipo": "revision", "icono": "check-circle",
                "descripcion": f"Tarea aprobada"
            })
        elif asignacion.estado_revision == "rechazado" and asignacion.revision_comentario:
            timeline.append({
                "fecha": asignacion.fecha_revision or asignacion.fecha_update,
                "tipo": "revision", "icono": "x-circle",
                "descripcion": f"Tarea rechazada: {asignacion.revision_comentario[:80]}"
            })
        # Incidencias vinculadas
        from ..models import Incidencia
        for inc in Incidencia.objects.filter(tarea=tarea, activo=True):
            timeline.append({
                "fecha": inc.fecha_creacion, "tipo": "incidencia", "icono": "bug",
                "descripcion": f"Bug {inc.codigo}: {inc.titulo[:60]} ({inc.get_estado_display()})"
            })
        timeline.sort(key=lambda x: x["fecha"], reverse=True)
    else:
        timeline = []

    return render(request, "proyectos/tarea_detail.html", {
        "proyecto": proyecto,
        "tarea": tarea,
        "asignacion": asignacion,
        "registros": registros,
        "comentarios": comentarios,
        "traslados": traslados,
        "colaboraciones": colaboraciones,
        "historial": historial,
        "tiempo_efectivo": tiempo_efectivo,
        "timeline": timeline,
        "today": timezone.now().date(),
    })


@miembro_requerido(ROLES_EDICION)
def tarea_activar(request, pk, tid):
    proyecto = request.proyecto
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=proyecto)
    if request.method == "POST":
        asignacion = crear_asignacion_desde_tarea(tarea)
        if asignacion:
            messages.success(request, f"Tarea '{tarea.titulo}' activada. Aparece en el Tablero de {tarea.asignado_a.get_full_name()}.")
        else:
            messages.warning(request, "La tarea ya tiene asignacion o no tiene usuario asignado.")
    return redirect("proyectos:tarea_list", pk=proyecto.pk)
