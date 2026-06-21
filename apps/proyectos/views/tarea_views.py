from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ..models import Proyecto, Sprint, HistoriaUsuario, Tarea
from ..signals import crear_asignacion_desde_tarea
from ..decorators import miembro_requerido, ROLES_EDICION, ROLES_MOVER, ROLES_REVISION
from apps.actividades.models import Actividad, TipoActividad


def _tipo_to_tarea(tipo_nombre):
    """Mapea nombre de TipoActividad a Tarea.TIPOS valido."""
    n = tipo_nombre.lower()
    if "bug" in n: return "bug"
    if "mejora" in n: return "mejora"
    if "document" in n: return "documentacion"
    if "prueba" in n or "test" in n: return "prueba"
    if "diseno" in n or "diseño" in n: return "diseno"
    return "tarea"


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

        # Validar tipo de actividad desde catalogo
        tipo_actividad_id = request.POST.get("tipo_actividad_id") or None
        tipo_nombre = "tarea"
        if tipo_actividad_id:
            try:
                tipo_act = TipoActividad.objects.get(pk=tipo_actividad_id, subarea__in=proyecto.subareas.all(), activo=True)
                tipo_nombre = _tipo_to_tarea(tipo_act.nombre)
                if tipo_act.requiere_fecha_limite and not fl:
                    messages.error(request, f"El tipo '{tipo_act.nombre}' requiere fecha limite.")
                    return redirect("proyectos:tarea_list", pk=proyecto.pk)
            except TipoActividad.DoesNotExist:
                pass

        tarea = Tarea.objects.create(
            proyecto=proyecto,
            titulo=titulo,
            descripcion=request.POST.get("descripcion", ""),
            tipo=tipo_nombre,
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
        from ..models import RegistroAvance
        RegistroAvance.objects.create(proyecto=proyecto, tipo="tarea_creada",
            descripcion=f"Tarea {tarea.codigo} creada: {tarea.titulo[:60]}", user=request.user, referencia_id=tarea.pk)
        if tarea.asignado_a:
            asignacion = crear_asignacion_desde_tarea(tarea)
            if asignacion:
                from apps.gestion.views import _notificar_usuario
                _notificar_usuario(tarea.asignado_a.pk, "nueva_asignacion", {"actividad": tarea.titulo})
                messages.success(request, f"Tarea {tarea.codigo} creada y asignada a {tarea.asignado_a.get_full_name()}. Aparecera en su tablero Kanban.")
            else:
                messages.success(request, f"Tarea {tarea.codigo} creada.")
        else:
            messages.success(request, f"Tarea {tarea.codigo} creada (sin asignar). Asignala para que aparezca en el tablero Kanban.")
        return redirect("proyectos:tarea_list", pk=proyecto.pk)

    historias = proyecto.historias.filter(activo=True)
    sprints = proyecto.sprints.filter(activo=True)
    miembros = _miembros_asignables(proyecto, request)
    tipos_actividad = TipoActividad.objects.filter(subarea__in=proyecto.subareas.all(), activo=True, solo_proyecto=True).distinct().order_by("nombre")
    actividades = Actividad.objects.filter(subarea__in=proyecto.subareas.all(), activo=True).select_related("tipo_actividad")

    # Contexto de la historia pre-seleccionada
    sel_historia_id = request.GET.get("historia", "")
    sel_historia = None
    sel_sprint = None
    if sel_historia_id:
        sel_historia = get_object_or_404(HistoriaUsuario, pk=sel_historia_id, proyecto=proyecto, activo=True)
        sel_sprint = sel_historia.sprint
        tareas_historia = sel_historia.tareas.filter(activo=True)

    return render(request, "proyectos/tarea_form.html", {
        "proyecto": proyecto, "historias": historias, "sprints": sprints, "miembros": miembros,
        "tipos_actividad": tipos_actividad, "actividades": actividades,
        "selected_historia_id": sel_historia_id,
        "sel_historia": sel_historia,
        "sel_sprint": sel_sprint,
        "tareas_historia": sel_historia.tareas.filter(activo=True) if sel_historia else None,
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
            # Actualizar historia padre
            if tarea.historia:
                tarea.historia.actualizar_estado()
            from ..models import RegistroAvance
            RegistroAvance.objects.create(
                proyecto=request.proyecto, tipo="tarea_rechazada",
                descripcion=f"Tarea {tarea.codigo} rechazada por {request.user.get_full_name()}: {motivo[:80]}",
                user=request.user, referencia_id=tarea.pk
            )
            if tarea.asignacion:
                tarea.asignacion.estado = "Pendiente"
                tarea.asignacion.estado_revision = "rechazado"
                tarea.asignacion.revision_comentario = motivo
                tarea.asignacion.save()
            # Cerrar todas las AsignacionActividad de revision para esta tarea
            from apps.gestion.models import AsignacionActividad
            AsignacionActividad.objects.filter(
                nombre_actividad__startswith=f"[Revisar] {tarea.codigo}:",
                activo=True
            ).update(activo=False, estado="Cancelada")
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
                tarea.full_clean()
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
                    # Cuando tarea entra en revision, crear AsignacionActividad para cada Revisor/Aprobador
                    if nuevo == "revision":
                        from ..models import MiembroProyecto
                        from ..decorators import ROLES_REVISION
                        from apps.actividades.models import Actividad, TipoActividad
                        from apps.gestion.models import AsignacionActividad
                        from apps.gestion.views import _notificar_usuario
                        subarea = proyecto.subareas.first()
                        if subarea:
                            tipo_rev, _ = TipoActividad.objects.get_or_create(
                                subarea=subarea, nombre="Revision de Proyecto",
                                defaults={"requiere_fecha_limite": False, "requiere_entregable": False, "es_flash": False}
                            )
                            act_rev, _ = Actividad.objects.get_or_create(
                                subarea=subarea, tipo_actividad=tipo_rev,
                                defaults={"nombre": f"Revision de Proyecto - {proyecto.codigo}"}
                            )
                            revisores = MiembroProyecto.objects.filter(
                                proyecto=proyecto, activo=True, rol__in=ROLES_REVISION
                            )
                            for m in revisores:
                                AsignacionActividad.objects.get_or_create(
                                    user=m.user,
                                    nombre_actividad=f"[Revisar] {tarea.codigo}: {tarea.titulo[:80]}",
                                    origen="Revision",
                                    activo=True,
                                    defaults={
                                        "actividad": act_rev,
                                        "estado": "Pendiente",
                                        "origen_user": tarea.asignado_a or tarea.creador,
                                        "nombre_tipo": "Revision de Tarea",
                                    }
                                )
                                _notificar_usuario(m.user_id, "nueva_revision", {
                                    "tarea": tarea.titulo, "codigo": tarea.codigo,
                                    "proyecto": proyecto.codigo,
                                })
                return JsonResponse({"ok": True})
        except Exception as e:
            import logging
            logging.getLogger("proyectos").error(f"tarea_mover error: {e}")
    return JsonResponse({"ok": False}, status=400)


@miembro_requerido(ROLES_EDICION)
def tarea_edit(request, pk, tid):
    proyecto = request.proyecto
    tarea = get_object_or_404(Tarea, pk=tid, proyecto=proyecto, activo=True)
    if tarea.estado in ["finalizada", "cancelada", "pausada", "revision"]:
        messages.error(request, "No se puede editar una tarea finalizada, cancelada, pausada o en revision.")
        return redirect("proyectos:tarea_detail", pk=proyecto.pk, tid=tarea.pk)
    if request.method == "POST":
        old_asignado = tarea.asignado_a_id
        old_historia = tarea.historia_id
        old_sprint = tarea.sprint_id
        tarea.titulo = request.POST.get("titulo", tarea.titulo)
        tarea.descripcion = request.POST.get("descripcion", tarea.descripcion)
        tarea.prioridad = request.POST.get("prioridad", tarea.prioridad)
        tarea.asignado_a_id = request.POST.get("user_id") or None
        tarea.historia_id = request.POST.get("historia_id") or None
        tarea.sprint_id = request.POST.get("sprint_id") or None
        tarea.actividad_catalogo_id = request.POST.get("actividad_id") or None
        tarea.fecha_limite = request.POST.get("fecha_limite") or None
        tid = request.POST.get("tipo_actividad_id") or None
        if tid:
            try:
                tp = TipoActividad.objects.get(pk=tid)
                tarea.tipo = _tipo_to_tarea(tp.nombre)
                if tp.requiere_fecha_limite and not tarea.fecha_limite:
                    messages.error(request, f"El tipo '{tp.nombre}' requiere fecha limite.")
                    return redirect("proyectos:tarea_edit", pk=proyecto.pk, tid=tarea.pk)
            except TipoActividad.DoesNotExist:
                pass
        nuevo_estado = request.POST.get("estado")
        if nuevo_estado and nuevo_estado != tarea.estado and tarea.estado not in ["finalizada", "cancelada"]:
            tarea.estado = nuevo_estado
        tarea.save()

        # Bitacora de cambios
        cambios = []
        if old_asignado != tarea.asignado_a_id: cambios.append("asignado")
        if old_historia != tarea.historia_id: cambios.append("historia")
        if old_sprint != tarea.sprint_id: cambios.append("sprint")
        if cambios:
            from ..models import RegistroAvance
            RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                descripcion=f"Tarea {tarea.codigo} editada: {', '.join(cambios)} por {request.user.get_full_name()}",
                user=request.user, referencia_id=tarea.pk)

        # Si se asigno un nuevo ejecutor, crear/actualizar AsignacionActividad
        if tarea.asignado_a_id and tarea.asignado_a_id != old_asignado:
            # Desactivar asignacion anterior
            if tarea.asignacion:
                tarea.asignacion.activo = False
                tarea.asignacion.save()
                tarea.asignacion = None
                tarea.save(update_fields=["asignacion"])
            from ..signals import crear_asignacion_desde_tarea
            crear_asignacion_desde_tarea(tarea)

        messages.success(request, "Tarea actualizada.")
        return redirect("proyectos:tarea_list", pk=proyecto.pk)
    historias = proyecto.historias.filter(activo=True)
    sprints = proyecto.sprints.filter(activo=True)
    miembros = _miembros_asignables(proyecto, request)
    tipos_actividad = TipoActividad.objects.filter(subarea__in=proyecto.subareas.all(), activo=True, solo_proyecto=True).distinct().order_by("nombre")
    actividades = Actividad.objects.filter(subarea__in=proyecto.subareas.all(), activo=True).select_related("tipo_actividad")
    return render(request, "proyectos/tarea_form.html", {
        "proyecto": proyecto, "tarea": tarea, "editando": True,
        "historias": historias, "sprints": sprints, "miembros": miembros,
        "tipos_actividad": tipos_actividad, "actividades": actividades,
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
        # Eventos de bitacora (RegistroAvance) de esta tarea
        from ..models import RegistroAvance
        for ra in RegistroAvance.objects.filter(referencia_id=tarea.pk, proyecto=proyecto).order_by("-fecha"):
            timeline.append({
                "fecha": ra.fecha, "tipo": "bitacora", "icono": "pencil",
                "descripcion": ra.descripcion
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
