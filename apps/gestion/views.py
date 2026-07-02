from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.db.models.functions import TruncDate
from datetime import timedelta, date as dt_date
from apps.actividades.views import get_admin_subareas
from apps.actividades.models import Actividad, TipoActividad
from apps.estructura.models import SubArea, UserSubArea
from apps.planificacion.models import PlanificacionDetalle
from apps.accounts.models import User
from .models import AsignacionActividad, RegistroTiempo, TrasladoActividad, Colaboracion, Comentario, TiempoInactividad, RevisionHistorial
from .forms import RegistroTiempoForm, ComentarioForm
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def _notificar_usuario(user_id, tipo, data):
    """Envia notificacion WebSocket a un usuario especifico."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {"type": tipo, **data}
        )
    except Exception:
        pass  # Si channels no esta disponible, no pasa nada


def _log_proyecto(asignacion, descripcion):
    """Registra en la bitacora del proyecto si la actividad es de un proyecto."""
    try:
        tarea = getattr(asignacion, 'tarea_proyecto', None)
        if tarea:
            from apps.proyectos.models import RegistroAvance
            RegistroAvance.objects.create(
                proyecto=tarea.proyecto, tipo="comentario",
                descripcion=descripcion,
                user=asignacion.user, referencia_id=tarea.pk
            )
    except Exception:
        pass


def _gestionar_tiempo_inactividad(user):
    """Si el usuario no tiene actividad EnCurso, abre periodo de inactividad.
       Si tiene EnCurso, cierra cualquier periodo abierto."""
    ahora = timezone.now()
    tiene_curso = AsignacionActividad.objects.filter(user=user, activo=True, estado="EnCurso").exists()
    if tiene_curso:
        for tm in TiempoInactividad.objects.filter(user=user, activo=True, fin__isnull=True):
            if tm.inicio:
                tm.duracion_segundos += int((ahora - tm.inicio).total_seconds())
            tm.fin = ahora
            tm.activo = False
            tm.save()
        # Si tenia EnCurso pero no habia TM abierto, hubo inactividad no registrada.
        # Crear TM retroactivo desde el ultimo evento hasta ahora y cerrarlo.
        if not TiempoInactividad.objects.filter(user=user, activo=True, fin__isnull=True).exists():
            ultimo = RegistroTiempo.objects.filter(
                asignacion__user=user, activo=True,
                evento__in=["Finalizacion", "Pausa", "Inicio", "Reanudacion"]
            ).order_by("-fecha_hora").first()
            if ultimo and not AsignacionActividad.objects.filter(
                user=user, activo=True, estado="EnCurso"
            ).exclude(fecha_update__gte=ultimo.fecha_hora).exists():
                # El ultimo evento fue hace tiempo, el usuario estuvo inactivo
                tm = TiempoInactividad.objects.create(
                    user=user, fecha=ultimo.fecha_hora.date(),
                    inicio=ultimo.fecha_hora
                )
                tm.duracion_segundos = int((ahora - tm.inicio).total_seconds())
                tm.fin = ahora
                tm.activo = False
                tm.save()
    else:
        if not TiempoInactividad.objects.filter(user=user, activo=True, fin__isnull=True).exists():
            # Usar ultimo evento como inicio si existe
            ultimo = RegistroTiempo.objects.filter(
                asignacion__user=user, activo=True,
                evento__in=["Finalizacion", "Pausa", "Inicio", "Reanudacion"]
            ).order_by("-fecha_hora").first()
            inicio = ultimo.fecha_hora if ultimo else ahora
            TiempoInactividad.objects.create(
                user=user, fecha=inicio.date(), inicio=inicio
            )


def _pausar_activas(user, motivo=None):
    en_curso = AsignacionActividad.objects.filter(user=user, estado="EnCurso", activo=True)
    for a in en_curso:
        a.estado = "Pausada"
        a.save()
        RegistroTiempo.objects.create(
            asignacion=a,
            evento="Pausa",
            motivo_pausa=motivo,
            fecha_hora=timezone.now(),
            comentario="Pausada automaticamente al iniciar otra actividad"
        )


@login_required
def tablero(request):
    empresa_id = request.GET.get("empresa_id")
    subarea_id = request.GET.get("subarea_id")

    user_subareas = UserSubArea.objects.filter(user=request.user, activo=True).select_related("subarea__area")

    if not subarea_id and user_subareas.exists():
        subarea_id = user_subareas.first().subarea_id

    ahora = timezone.now()
    hoy = ahora.date()

    # Fecha seleccionada por el usuario (default: hoy)
    fecha_str = request.GET.get("fecha", hoy.isoformat())
    try:
        fecha_sel = dt_date.fromisoformat(fecha_str)
    except (ValueError, TypeError):
        fecha_sel = hoy

    asignaciones = AsignacionActividad.objects.filter(
        user=request.user, activo=True,
    ).filter(
        Q(estado__in=["EnCurso", "Pausada", "Finalizada", "Cancelada", "Trasladada", "Revision"]) |
        Q(planificacion_detalle__isnull=True) |
        Q(planificacion_detalle__fecha_programada__isnull=True) |
        Q(planificacion_detalle__fecha_programada__lte=ahora) |
        Q(actividad__tipo_actividad__requiere_entregable=True)
    ).select_related("actividad__tipo_actividad", "actividad__subarea__area", "planificacion_detalle__planificacion", "tarea_proyecto__proyecto"
    ).prefetch_related("comentarios")

    if subarea_id:
        asignaciones = asignaciones.filter(
            Q(actividad__subarea_id=subarea_id) |
            Q(planificacion_detalle__planificacion__subarea_id=subarea_id)
        )

    # Planificadas: filtradas por fecha seleccionada + las sin fecha (siempre visibles)
    planificadas_qs = AsignacionActividad.objects.filter(
        user=request.user, activo=True, estado="Pendiente",
    ).select_related("actividad__tipo_actividad", "actividad__subarea__area", "planificacion_detalle__planificacion").prefetch_related("comentarios")
    if subarea_id:
        planificadas_qs = planificadas_qs.filter(
            Q(actividad__subarea_id=subarea_id) |
            Q(planificacion_detalle__planificacion__subarea_id=subarea_id)
        )
    # Filtrar por fecha en Python (evita problemas de timezone en MySQL)
    planificadas = [a for a in planificadas_qs if (
        not a.planificacion_detalle or
        not a.planificacion_detalle.fecha_programada or
        a.planificacion_detalle.fecha_programada.date() == fecha_sel
    )]

    # Actividades del dia para la lista horizontal (EnCurso/Pausadas siempre + Pendientes/Finalizadas del dia)
    actividades_dia = AsignacionActividad.objects.filter(
        user=request.user, activo=True
    ).annotate(
        prog_date=TruncDate('planificacion_detalle__fecha_programada'),
        fin_date=TruncDate('registros__fecha_hora')
    ).filter(
        Q(estado__in=["EnCurso", "Pausada"]) |
        Q(estado="Pendiente", prog_date=fecha_sel) |
        Q(estado="Pendiente", planificacion_detalle__fecha_programada__isnull=True) |
        Q(estado__in=["Finalizada", "Trasladada"], registros__evento="Finalizacion", fin_date=fecha_sel)
    ).select_related("actividad__tipo_actividad", "actividad__subarea__area", "planificacion_detalle__planificacion").distinct()

    # Todas las planificadas pendientes (sin filtro de fecha) para "Iniciar siguiente"
    planificadas_todas = AsignacionActividad.objects.filter(
        user=request.user, activo=True, estado="Pendiente",
    ).select_related("actividad__tipo_actividad", "actividad__subarea__area", "planificacion_detalle").order_by("planificacion_detalle__fecha_programada", "actividad__nombre")

    en_curso = asignaciones.filter(estado="EnCurso")
    pausadas = asignaciones.filter(estado="Pausada")
    revision = asignaciones.filter(estado="Revision")

    # Finalizadas de las ultimas 24 horas
    un_dia_atras = ahora - timedelta(hours=24)
    finalizadas = asignaciones.filter(
        estado__in=["Finalizada", "Revision"],
        registros__evento="Finalizacion",
        registros__fecha_hora__gte=un_dia_atras
    ).order_by("-registros__fecha_hora").distinct()

    context = {
        "user_subareas": user_subareas,
        "subarea_id": int(subarea_id) if subarea_id else None,
        "empresa_id": int(empresa_id) if empresa_id else None,
        "planificadas": planificadas,
        "planificadas_todas": planificadas_todas,
        "actividades_dia": actividades_dia,
        "en_curso": en_curso,
        "pausadas": pausadas,
        "revision": revision,
        "finalizadas": finalizadas,
        "fecha_sel": fecha_sel,
        "now": timezone.now(),
        "form_finalizar": RegistroTiempoForm(),
        "form_comentario": ComentarioForm(),
        "traslados_recibidos": TrasladoActividad.objects.filter(
            user_destino=request.user, estado="Pendiente", activo=True
        ).select_related("asignacion_origen__actividad", "user_origen"),
        "traslados_enviados": TrasladoActividad.objects.filter(
            user_origen=request.user, estado="Pendiente", activo=True
        ).select_related("asignacion_origen__actividad", "user_destino"),
    }

    # --- Tareas pendientes de Revision de Proyectos ---
    from apps.proyectos.models import Tarea, HistoriaUsuario, MiembroProyecto
    from apps.proyectos.decorators import ROLES_REVISION
    proyectos_revisor = MiembroProyecto.objects.filter(
        user=request.user, activo=True, rol__in=ROLES_REVISION
    ).values_list("proyecto_id", flat=True)
    if proyectos_revisor:
        tareas_revision = Tarea.objects.filter(
            proyecto_id__in=proyectos_revisor, activo=True, estado="revision"
        ).select_related("proyecto", "historia", "asignado_a", "creador").order_by("-fecha_creacion")
        historias_revision = HistoriaUsuario.objects.filter(
            proyecto_id__in=proyectos_revisor, activo=True, estado="revision"
        ).select_related("proyecto", "sprint", "creador").prefetch_related("tareas__asignado_a").order_by("-fecha_creacion")
    else:
        tareas_revision = Tarea.objects.none()
        historias_revision = HistoriaUsuario.objects.none()
    context["tareas_revision"] = tareas_revision
    context["historias_revision"] = historias_revision

    return render(request, "gestion/tablero.html", context)


@login_required
def activar_actividad(request, pk):
    if request.method != "POST":
        return redirect("gestion:tablero")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, user=request.user, activo=True)

    if asignacion.estado not in ["Pendiente", "Pausada"]:
        messages.error(request, f"Solo puedes iniciar actividades Pendiente o Pausada. Esta actividad esta '{asignacion.get_estado_display()}'.")
        return redirect("gestion:tablero")

    _pausar_activas(request.user)

    estado_anterior = asignacion.estado
    asignacion.estado = "EnCurso"
    asignacion.save()

    evento = "Inicio" if estado_anterior == "Pendiente" else "Reanudacion"
    RegistroTiempo.objects.create(
        asignacion=asignacion,
        evento=evento,
        fecha_hora=timezone.now()
    )

    messages.success(request, f"Actividad {'iniciada' if evento == 'Inicio' else 'reanudada'}.")
    _gestionar_tiempo_inactividad(request.user)
    # Registrar en bitacora del proyecto si es tarea de proyecto
    _log_proyecto(asignacion, f"Tarea iniciada por {request.user.get_full_name()}")
    return redirect("gestion:tablero")


@login_required
def pausar_actividad(request, pk):
    if request.method != "POST":
        return redirect("gestion:tablero")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, user=request.user, activo=True)

    if asignacion.estado != "EnCurso":
        messages.error(request, f"Solo puedes pausar actividades En Curso. Esta actividad esta '{asignacion.get_estado_display()}'.")
        return redirect("gestion:tablero")

    motivo_pausa = request.POST.get("motivo_pausa", "")
    comentario = request.POST.get("comentario", "")
    actividad_id = request.POST.get("actividad_id")
    subarea_id = request.POST.get("subarea_id")

    # Si es cambio de prioridad, requiere una actividad de reemplazo
    if motivo_pausa == "Cambio de prioridad":
        if not actividad_id or not subarea_id:
            messages.error(request, "Para cambio de prioridad debes seleccionar la nueva actividad.")
            return redirect("gestion:tablero")

    # Pausar la actual
    asignacion.estado = "Pausada"
    asignacion.save()
    RegistroTiempo.objects.create(
        asignacion=asignacion,
        evento="Pausa",
        motivo_pausa=motivo_pausa or None,
        comentario=comentario or None,
        fecha_hora=timezone.now(),
    )

    # Iniciar la nueva actividad si se selecciono una
    if actividad_id and subarea_id:
        nueva = get_object_or_404(Actividad, pk=actividad_id, subarea_id=subarea_id, activo=True)
        _pausar_activas(request.user, motivo=motivo_pausa)
        nueva_asignacion = AsignacionActividad.objects.create(
            user=request.user, actividad=nueva, estado="EnCurso",
            origen="Manual", origen_user=request.user,
            nombre_actividad=nueva.nombre,
            nombre_tipo=nueva.tipo_actividad.nombre,
        )
        RegistroTiempo.objects.create(
            asignacion=nueva_asignacion, evento="Inicio", fecha_hora=timezone.now()
        )
        if motivo_pausa == "Cambio de prioridad":
            messages.success(request, f"Actividad cambiada a '{nueva.nombre}'.")
        else:
            messages.success(request, f"Actividad pausada. '{nueva.nombre}' iniciada.")
    else:
        messages.success(request, "Actividad pausada.")

    _gestionar_tiempo_inactividad(request.user)
    return redirect("gestion:tablero")


@login_required
def finalizar_actividad(request, pk):
    if request.method != "POST":
        return redirect("gestion:tablero")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, user=request.user, activo=True)

    if asignacion.estado not in ["EnCurso", "Pausada"]:
        messages.error(request, f"Solo puedes finalizar actividades En Curso o Pausadas. Estado actual: '{asignacion.get_estado_display()}'.")
        return redirect("gestion:tablero")

    # Validar entregable si el tipo de actividad del proyecto lo requiere
    if hasattr(asignacion, 'tarea_proyecto') and asignacion.tarea_proyecto:
        tarea = asignacion.tarea_proyecto
        if tarea.actividad_catalogo and tarea.actividad_catalogo.tipo_actividad.requiere_entregable:
            if not asignacion.entregable:
                messages.error(request, "Este tipo de actividad requiere un archivo entregable. Adjunta el entregable antes de finalizar.")
                return redirect("gestion:detalle_actividad", pk=asignacion.pk)

    # --- Revision de proyecto: aprobar o rechazar via el modal Finalizar ---
    accion_rev = request.POST.get("accion_revision")
    if accion_rev and asignacion.origen == "Revision":
        # Determinar si es revision de historia o de tarea
        nombre = asignacion.nombre_actividad

        # Formato tarea: "[Revisar] PRJ-0007-T-013: Crear formulario..."
        if nombre.startswith("[Revisar] "):
            from apps.proyectos.models import Tarea
            tarea_codigo = nombre.split("] ")[1].split(":")[0].strip()
            tarea = Tarea.objects.filter(codigo=tarea_codigo, activo=True).first()
            if tarea:
                if accion_rev == "aprobar":
                    tarea.estado = "finalizada"
                    tarea.save()
                    if tarea.historia:
                        old_h = tarea.historia.estado
                        tarea.historia.actualizar_estado()
                        # Si la historia entra en revision, crear [Aprobar] cards
                        if tarea.historia.estado == "revision" and old_h != "revision":
                            from apps.proyectos.signals import _crear_cards_aprobar_historia
                            _crear_cards_aprobar_historia(tarea.historia, tarea.asignado_a or tarea.creador)
                    AsignacionActividad.objects.filter(
                        nombre_actividad__startswith=f"[Revisar] {tarea.codigo}:",
                        activo=True
                    ).update(activo=False, estado="Finalizada")
                    from apps.proyectos.models import RegistroAvance
                    RegistroAvance.objects.create(
                        proyecto=tarea.proyecto, tipo="tarea_finalizada",
                        descripcion=f"Tarea {tarea.codigo} aprobada por {request.user.get_full_name()}",
                        user=request.user, referencia_id=tarea.pk
                    )
                    messages.success(request, f"Tarea {tarea.codigo} aprobada.")
                elif accion_rev == "rechazar":
                    motivo = request.POST.get("motivo_rechazo", "").strip()
                    if not motivo:
                        messages.error(request, "Debes indicar el motivo del rechazo.")
                        return redirect("gestion:tablero")
                    if request.POST.get("crear_bug"):
                        # Crear incidencia + tarea hija (NO devuelve la original)
                        from apps.proyectos.models import Incidencia, RegistroAvance as RA
                        inc = Incidencia.objects.create(
                            proyecto=tarea.proyecto, tarea=tarea, historia=tarea.historia,
                            titulo=f"Bug: {tarea.titulo}", descripcion=motivo,
                            tipo="bug", severidad="media", estado="abierta",
                            reportado_por=request.user,
                            asignado_a=tarea.asignado_a,
                        )
                        inc.codigo = f"{tarea.proyecto.codigo}-INC-{inc.pk:03d}"
                        inc.save()
                        # Crear tarea hija desde la incidencia
                        from apps.proyectos.models import Tarea as TareaModel
                        tarea_hija = TareaModel.objects.create(
                            proyecto=tarea.proyecto,
                            historia=tarea.historia,
                            sprint=tarea.sprint,
                            titulo=f"[Bug] {tarea.titulo}",
                            descripcion=motivo,
                            tipo="bug",
                            asignado_a=tarea.asignado_a,
                            creador=request.user,
                            actividad_catalogo=tarea.actividad_catalogo,
                        )
                        tarea_hija.codigo = f"{tarea.proyecto.codigo}-T-{tarea_hija.pk:03d}"
                        tarea_hija.save()
                        inc.tarea = tarea_hija
                        inc.save()
                        from apps.proyectos.signals import crear_asignacion_desde_tarea
                        crear_asignacion_desde_tarea(tarea_hija)
                        RA.objects.create(
                            proyecto=tarea.proyecto, tipo="tarea_creada",
                            descripcion=f"Bug {inc.codigo} genero tarea {tarea_hija.codigo}: {tarea_hija.titulo[:60]}",
                            user=request.user, referencia_id=tarea_hija.pk
                        )
                        messages.warning(request, f"Tarea {tarea.codigo} rechazada. Bug {inc.codigo} creado y asignado a {tarea.asignado_a.get_full_name()}.")
                    else:
                        # Rechazo normal: devolver al ejecutor
                        tarea.estado = "pendiente"
                        tarea.save()
                        if tarea.asignacion:
                            tarea.asignacion.estado = "Pendiente"
                            tarea.asignacion.estado_revision = "rechazado"
                            tarea.asignacion.revision_comentario = motivo
                            tarea.asignacion.save()
                        if tarea.historia:
                            tarea.historia.actualizar_estado()
                        messages.warning(request, f"Tarea {tarea.codigo} rechazada: {motivo}")
                    # Cancelar todas las [Revisar] para esta tarea en ambos casos
                    AsignacionActividad.objects.filter(
                        nombre_actividad__startswith=f"[Revisar] {tarea.codigo}:",
                        activo=True
                    ).update(activo=False, estado="Cancelada")
                    from apps.proyectos.models import RegistroAvance
                    RegistroAvance.objects.create(
                        proyecto=tarea.proyecto, tipo="comentario",
                        descripcion=f"Tarea {tarea.codigo} rechazada por {request.user.get_full_name()}: {motivo[:80]}",
                        user=request.user, referencia_id=tarea.pk
                    )
                    messages.warning(request, f"Tarea {tarea.codigo} rechazada.")
            return redirect("gestion:tablero")
        elif nombre.startswith("[Rev-"):
            import re
            match = re.match(r'\[Rev-(\d+)\]\s+([^:]+):', nombre)
            if match:
                paso_num = int(match.group(1))
                tarea_codigo = match.group(2).strip()
                from apps.proyectos.models import Tarea
                tarea = Tarea.objects.filter(codigo=tarea_codigo, activo=True).first()
                if tarea:
                    if accion_rev == "aprobar":
                        from apps.proyectos.signals import _avanzar_paso_revision
                        # Cerrar todas las cards [Rev-N] para esta tarea
                        for p in range(1, 10):
                            AsignacionActividad.objects.filter(
                                nombre_actividad__startswith=f"[Rev-{p}] {tarea.codigo}:",
                                activo=True
                            ).update(activo=False, estado="Finalizada")
                        from apps.proyectos.models import RegistroAvance
                        RegistroAvance.objects.create(
                            proyecto=tarea.proyecto, tipo="comentario",
                            descripcion=f"Tarea {tarea.codigo} paso {paso_num} aprobado por {request.user.get_full_name()}",
                            user=request.user, referencia_id=tarea.pk
                        )
                        _avanzar_paso_revision(tarea, paso_num)
                        messages.success(request, f"Paso {paso_num} de revision de {tarea.codigo} aprobado.")
                    elif accion_rev == "rechazar":
                        motivo = request.POST.get("motivo_rechazo", "").strip()
                        if not motivo:
                            messages.error(request, "Debes indicar el motivo del rechazo.")
                            return redirect("gestion:tablero")
                        # Rechazo: devolver al ejecutor (reinicia desde paso 1)
                        tarea.estado = "pendiente"
                        tarea.save()
                        if tarea.asignacion:
                            tarea.asignacion.estado = "Pendiente"
                            tarea.asignacion.estado_revision = "rechazado"
                            tarea.asignacion.revision_comentario = motivo
                            tarea.asignacion.save()
                        # Cancelar TODAS las cards [Rev-N] activas
                        for p in range(1, 10):
                            AsignacionActividad.objects.filter(
                                nombre_actividad__startswith=f"[Rev-{p}] {tarea.codigo}:",
                                activo=True
                            ).update(activo=False, estado="Cancelada")
                        from apps.proyectos.models import RegistroAvance
                        RegistroAvance.objects.create(
                            proyecto=tarea.proyecto, tipo="comentario",
                            descripcion=f"Tarea {tarea.codigo} rechazada en paso {paso_num}: {motivo[:80]}",
                            user=request.user, referencia_id=tarea.pk
                        )
                        messages.warning(request, f"Tarea {tarea.codigo} rechazada en paso {paso_num}.")
            return redirect("gestion:tablero")

        # Formato historia: "[Aprobar] US-019: Recuperar contraseña"
        historia_codigo = nombre.split("] ")[1].split(":")[0].strip() if "] " in nombre else ""
        from apps.proyectos.models import HistoriaUsuario
        historia = HistoriaUsuario.objects.filter(codigo=historia_codigo, activo=True).first()
        if historia:
            if accion_rev == "aprobar":
                historia.estado = "done"
                historia.save()
                from apps.proyectos.models import RegistroAvance
                RegistroAvance.objects.create(
                    proyecto=historia.proyecto, tipo="historia_completada",
                    descripcion=f"Historia {historia.codigo} aprobada por {request.user.get_full_name()}",
                    user=request.user, referencia_id=historia.pk
                )
                messages.success(request, f"Historia {historia.codigo} aprobada.")
            elif accion_rev == "rechazar":
                motivo = request.POST.get("motivo_rechazo", "").strip()
                if not motivo:
                    messages.error(request, "Debes indicar el motivo del rechazo.")
                    return redirect("gestion:tablero")
                # Devolver todas las tareas de la historia a pendiente
                for t in historia.tareas.filter(activo=True, estado__in=["finalizada", "revision"]):
                    t.estado = "pendiente"
                    t.save()
                    if t.asignacion:
                        t.asignacion.estado = "Pendiente"
                        t.asignacion.estado_revision = "rechazado"
                        t.asignacion.revision_comentario = motivo
                        t.asignacion.save()
                    # Cancelar [Revisar] cards de esta tarea
                    AsignacionActividad.objects.filter(
                        nombre_actividad__startswith=f"[Revisar] {t.codigo}:",
                        activo=True
                    ).update(activo=False, estado="Cancelada")
                from apps.proyectos.models import Incidencia, RegistroAvance as RA
                if request.POST.get("crear_bug"):
                    inc = Incidencia.objects.create(
                        proyecto=historia.proyecto, historia=historia,
                        titulo=f"Bug en historia: {historia.titulo}", descripcion=motivo,
                        tipo="bug", severidad="media", estado="abierta",
                        reportado_por=request.user,
                        asignado_a=historia.creador,
                    )
                    inc.codigo = f"{historia.proyecto.codigo}-INC-{inc.pk:03d}"
                    inc.save()
                    RA.objects.create(
                        proyecto=historia.proyecto, tipo="incidencia_creada",
                        descripcion=f"Bug {inc.codigo} creado al rechazar historia {historia.codigo}: {motivo[:60]}",
                        user=request.user, referencia_id=inc.pk
                    )
                    messages.warning(request, f"Historia {historia.codigo} rechazada. Bug {inc.codigo} creado.")
                else:
                    messages.warning(request, f"Historia {historia.codigo} rechazada. Tareas devueltas al Ejecutor.")
                historia.actualizar_estado()
            # Cerrar todas las AsignacionActividad de revision para esta historia
            AsignacionActividad.objects.filter(
                nombre_actividad__startswith=f"[Aprobar] {historia.codigo}:",
                activo=True
            ).update(activo=False, estado="Finalizada")
        return redirect("gestion:tablero")

    reemplazo = request.POST.get("reemplazo_actividad")
    entregable_file = request.FILES.get("entregable")

    form = RegistroTiempoForm(request.POST, request.FILES)
    if form.is_valid():
        requiere_ent = asignacion.actividad.tipo_actividad.requiere_entregable
        nro = form.cleaned_data.get("nro_actividad")
        if not requiere_ent and not nro:
            messages.error(request, "El numero de actividad (cantidad realizada) es obligatorio para finalizar.")
            return redirect("gestion:tablero")
        if requiere_ent and not entregable_file:
            messages.error(request, "Esta actividad requiere un archivo entregable.")
            return redirect("gestion:tablero")
        if (asignacion.planificacion_detalle and asignacion.planificacion_detalle.fecha_vencimiento
                and asignacion.actividad.tipo_actividad.requiere_fecha_limite):
            venc = asignacion.planificacion_detalle.fecha_vencimiento
            if venc < timezone.now():
                asignacion.dias_vencida = ((timezone.now() - venc).days)
        if entregable_file:
            asignacion.entregable = entregable_file
        if requiere_ent and entregable_file:
            asignacion.estado = "Revision"
            asignacion.estado_revision = "pendiente"
        else:
            asignacion.estado = "Finalizada"
        asignacion.save()
        # Cancelar cualquier traslado pendiente de esta actividad
        traslados_pendientes = TrasladoActividad.objects.filter(
            asignacion_origen=asignacion, estado="Pendiente", activo=True
        )
        for t in traslados_pendientes:
            t.estado = "Cancelado"
            t.save()
        registro = form.save(commit=False)
        registro.asignacion = asignacion
        registro.evento = "Finalizacion"
        registro.fecha_hora = timezone.now()
        registro.save()

        comentario_texto = (form.cleaned_data.get("comentario", "") or "").strip()
        if comentario_texto:
            Comentario.objects.create(
                asignacion=asignacion, user=request.user,
                texto=comentario_texto,
                detalle=asignacion.planificacion_detalle
            )

        if reemplazo == "flash":
            flash_actividad_id = request.POST.get("flash_actividad_id")
            flash_subarea_id = request.POST.get("flash_subarea")
            if flash_actividad_id and flash_subarea_id:
                flash_actividad = get_object_or_404(Actividad, pk=flash_actividad_id, subarea_id=flash_subarea_id, activo=True)
                _pausar_activas(request.user)
                flash_asignacion = AsignacionActividad.objects.create(
                    user=request.user,
                    actividad=flash_actividad,
                    estado="EnCurso",
                    origen="Manual",
                    origen_user=request.user,
                    nombre_actividad=flash_actividad.nombre,
                    nombre_tipo=flash_actividad.tipo_actividad.nombre,
                )
                RegistroTiempo.objects.create(
                    asignacion=flash_asignacion,
                    evento="Inicio",
                    fecha_hora=timezone.now(),
                    comentario=f"Flash iniciada tras finalizar '{asignacion.actividad.nombre}'",
                )
                messages.success(request, f"Actividad '{asignacion.actividad.nombre}' finalizada. Flash '{flash_actividad.nombre}' iniciada.")
            else:
                messages.error(request, "Error al iniciar la actividad flash.")
            return redirect("gestion:tablero")

        reemplazo_asig = AsignacionActividad.objects.filter(
            pk=reemplazo, user=request.user, activo=True, estado="Pendiente"
        ).first()
        if reemplazo_asig:
            _pausar_activas(request.user)
            reemplazo_asig.estado = "EnCurso"
            reemplazo_asig.save()
            RegistroTiempo.objects.create(
                asignacion=reemplazo_asig, evento="Inicio", fecha_hora=timezone.now(),
                comentario=f"Iniciada tras finalizar '{asignacion.actividad.nombre}'"
            )
            messages.success(request, f"'{asignacion.actividad.nombre}' finalizada. Ahora estas en '{reemplazo_asig.actividad.nombre}'.")
        elif reemplazo == "nada" or not reemplazo:
            messages.success(request, f"'{asignacion.actividad.nombre}' finalizada.")
        else:
            messages.success(request, f"'{asignacion.actividad.nombre}' finalizada.")
    else:
        messages.error(request, "El numero de actividad (cantidad realizada) es obligatorio para finalizar.")
    _gestionar_tiempo_inactividad(request.user)
    _log_proyecto(asignacion, f"Tarea finalizada por {request.user.get_full_name()}")
    return redirect("gestion:tablero")


@login_required
def crear_no_programada(request):
    user_subareas = UserSubArea.objects.filter(user=request.user, activo=True).select_related("subarea")

    if request.method == "POST":
        actividad_id = request.POST.get("actividad_id")
        subarea_id = request.POST.get("subarea_id")
        comentario = request.POST.get("comentario", "").strip()

        if not actividad_id or not subarea_id:
            messages.error(request, "Selecciona una actividad y una subarea para iniciar una actividad no programada.")
            return redirect("gestion:crear_no_programada")

        actividad = get_object_or_404(Actividad, pk=actividad_id, subarea_id=subarea_id, activo=True)

        if not actividad.tipo_actividad.es_flash:
            messages.error(request, f"'{actividad.nombre}' no es un evento flash. Selecciona una actividad flash.")
            return redirect("gestion:crear_no_programada")

        duplicada = AsignacionActividad.objects.filter(
            user=request.user, actividad=actividad, activo=True
        ).exclude(estado__in=["Finalizada", "Cancelada", "Trasladada"]).exists()
        if duplicada:
            messages.warning(request, f"Ya tienes la actividad '{actividad.nombre}' pendiente o en curso.")
            return redirect("gestion:crear_no_programada")

        _pausar_activas(request.user)

        asignacion = AsignacionActividad.objects.create(
            user=request.user,
            actividad=actividad,
            estado="EnCurso",
            origen="Manual",
            origen_user=request.user,
            nombre_actividad=actividad.nombre,
            nombre_tipo=actividad.tipo_actividad.nombre,
        )
        RegistroTiempo.objects.create(
            asignacion=asignacion,
            evento="Inicio",
            fecha_hora=timezone.now(),
            comentario=comentario or None,
        )
        messages.success(request, f"Actividad '{actividad.nombre}' iniciada.")
        request.audit_record_id = asignacion.pk
        request.audit_modelo = "AsignacionActividad"
    _gestionar_tiempo_inactividad(request.user)
    _log_proyecto(asignacion, f"Tarea pausada por {request.user.get_full_name()}{' (' + motivo_pausa + ')' if motivo_pausa else ''}")
    return redirect("gestion:tablero")

    context = {
        "user_subareas": user_subareas,
    }
    return render(request, "gestion/crear_no_programada.html", context)


@login_required
def trasladar_actividad(request, pk):
    if request.method != "POST":
        return redirect("gestion:tablero")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True)
    if asignacion.user != request.user and request.user.rol.nombre not in ["Master", "Admin"]:
        return redirect("gestion:tablero")

    if asignacion.estado not in ["Pendiente", "EnCurso", "Pausada"]:
        messages.error(request, f"Solo puedes trasladar actividades Pendientes, En Curso o Pausadas. Esta actividad esta '{asignacion.get_estado_display()}'.")
        return redirect("gestion:tablero")

    if asignacion.actividad.tipo_actividad.requiere_entregable:
        messages.error(request, "No puedes trasladar actividades que requieren entregable.")
        return redirect("gestion:tablero")

    user_destino_id = request.POST.get("user_destino")
    actividad_reemplazo_id = request.POST.get("actividad_reemplazo")
    motivo = request.POST.get("motivo", "")

    if not user_destino_id:
        messages.error(request, "Debes seleccionar un usuario destino.")
        return redirect("gestion:tablero")

    user_destino = get_object_or_404(User, pk=user_destino_id, activo=True)
    # Si la actividad pertenece a un proyecto, validar el rol segun tipo de card
    nombre = asignacion.nombre_actividad or ""
    if nombre.startswith("[Revisar] "):
        rol_requerido = "revisor"
    elif nombre.startswith("[Aprobar] "):
        rol_requerido = "aprobador"
    else:
        rol_requerido = "ejecutor"
    if hasattr(asignacion, 'tarea_proyecto') and asignacion.tarea_proyecto:
        from apps.proyectos.models import MiembroProyecto
        if not MiembroProyecto.objects.filter(
            proyecto=asignacion.tarea_proyecto.proyecto, user=user_destino, activo=True, rol=rol_requerido
        ).exists():
            messages.error(request, f"El usuario destino debe ser miembro '{rol_requerido}' del proyecto.")
            return redirect("gestion:tablero")
    actividad_reemplazo = None
    if actividad_reemplazo_id:
        actividad_reemplazo = get_object_or_404(Actividad, pk=actividad_reemplazo_id, activo=True)
        if actividad_reemplazo.pk == asignacion.actividad.pk:
            messages.error(request, "No puedes seleccionar la misma actividad como reemplazo.")
            return redirect("gestion:tablero")

    if TrasladoActividad.objects.filter(
        asignacion_origen=asignacion, user_destino=user_destino, estado="Pendiente", activo=True
    ).exists():
        messages.error(request, "Ya existe una solicitud de traslado pendiente para esta actividad.")
        return redirect("gestion:tablero")

    traslado = TrasladoActividad.objects.create(
        asignacion_origen=asignacion,
        user_origen=request.user,
        user_destino=user_destino,
        actividad_reemplazo=actividad_reemplazo,
        estado="Pendiente",
        motivo=motivo,
    )

    request.audit_record_id = traslado.pk
    request.audit_modelo = "TrasladoActividad"
    _log_proyecto(asignacion, f"Traslado de {request.user.get_full_name()} a {user_destino.get_full_name()}{' (' + motivo + ')' if motivo else ''}")
    _notificar_usuario(user_destino.pk, "nuevo_traslado", {
        "origen": request.user.get_full_name(),
        "actividad": asignacion.actividad.nombre,
        "traslado_id": traslado.pk,
    })
    messages.success(request, f"Solicitud de traslado enviada a {user_destino.get_full_name()}. Pendiente de aceptacion.")
    return redirect("gestion:tablero")


@login_required
def aceptar_traslado(request, pk):
    traslado = get_object_or_404(TrasladoActividad, pk=pk, user_destino=request.user, activo=True)
    if traslado.estado != "Pendiente":
        messages.warning(request, f"Este traslado ya fue {traslado.get_estado_display().lower()}.")
        return redirect("gestion:tablero")

    # Validar que la asignacion origen aun sea transferible
    asignacion = traslado.asignacion_origen
    if asignacion.estado not in ["Pendiente", "EnCurso", "Pausada"]:
        traslado.estado = "Cancelado"
        traslado.save()
        messages.warning(request, "El traslado fue cancelado porque la actividad origen ya no esta disponible.")
        return redirect("gestion:tablero")
    if asignacion.estado == "EnCurso":
        asignacion.estado = "Pausada"
        asignacion.save()
        RegistroTiempo.objects.create(
            asignacion=asignacion, evento="Pausa", fecha_hora=timezone.now(),
            comentario="Pausada por traslado aceptado"
        )

    # Marcar origen como trasladada
    if (asignacion.planificacion_detalle and asignacion.planificacion_detalle.fecha_vencimiento
            and asignacion.actividad.tipo_actividad.requiere_fecha_limite):
        venc = asignacion.planificacion_detalle.fecha_vencimiento
        if venc < timezone.now():
            asignacion.dias_vencida = ((timezone.now() - venc).days)
    asignacion.estado = "Trasladada"
    asignacion.save()
    RegistroTiempo.objects.create(
        asignacion=asignacion, evento="Traslado", fecha_hora=timezone.now(),
        comentario=f"Trasladada a {request.user.get_full_name()}"
    )

    # Crear asignacion para el destino (quien acepta)
    # Si no tiene actividades en curso, inicia inmediatamente
    tiene_en_curso = AsignacionActividad.objects.filter(user=request.user, estado="EnCurso", activo=True).exists()
    estado_destino = "EnCurso" if not tiene_en_curso else "Pendiente"
    nueva = AsignacionActividad.objects.create(
        user=request.user,
        actividad=asignacion.actividad,
        estado=estado_destino,
        planificacion_detalle=asignacion.planificacion_detalle,
        origen="Traslado",
        origen_user=traslado.user_origen,
        nombre_actividad=asignacion.actividad.nombre,
        nombre_tipo=asignacion.actividad.tipo_actividad.nombre,
    )
    if estado_destino == "EnCurso":
        RegistroTiempo.objects.create(
            asignacion=nueva, evento="Inicio", fecha_hora=timezone.now()
        )

    traslado.asignacion_destino = nueva
    traslado.estado = "Aceptado"
    traslado.save()

    # Activar actividad de reemplazo para el ORIGEN
    if traslado.actividad_reemplazo:
        origen_user = traslado.user_origen
        tiene_curso_origen = AsignacionActividad.objects.filter(
            user=origen_user, estado="EnCurso", activo=True
        ).exists()
        reemplazo = AsignacionActividad.objects.create(
            user=origen_user,
            actividad=traslado.actividad_reemplazo,
            estado="EnCurso" if not tiene_curso_origen else "Pendiente",
            origen="Traslado",
            origen_user=request.user,
            nombre_actividad=traslado.actividad_reemplazo.nombre,
            nombre_tipo=traslado.actividad_reemplazo.tipo_actividad.nombre,
        )
        if not tiene_curso_origen:
            RegistroTiempo.objects.create(
                asignacion=reemplazo, evento="Inicio", fecha_hora=timezone.now(),
                comentario=f"Iniciada automaticamente tras trasladar '{asignacion.actividad.nombre}'"
            )
    elif not AsignacionActividad.objects.filter(
        user=traslado.user_origen, estado="EnCurso", activo=True
    ).exists():
        # Sin reemplazo definido pero sin nada en curso: activar la primera pendiente
        pendiente_origen = AsignacionActividad.objects.filter(
            user=traslado.user_origen, estado="Pendiente", activo=True
        ).first()
        if pendiente_origen:
            pendiente_origen.estado = "EnCurso"
            pendiente_origen.save()
            RegistroTiempo.objects.create(
                asignacion=pendiente_origen, evento="Inicio", fecha_hora=timezone.now(),
                comentario=f"Iniciada automaticamente tras trasladar '{asignacion.actividad.nombre}'"
            )

    _log_proyecto(asignacion, f"Traslado aceptado: de {traslado.user_origen.get_full_name()} a {request.user.get_full_name()}")
    messages.success(request, f"Traslado aceptado. Actividad '{asignacion.actividad.nombre}' agregada a tu tablero.")
    _notificar_usuario(traslado.user_origen.pk, "traslado_respuesta", {
        "accion": "aceptado",
        "actividad": asignacion.actividad.nombre,
        "destino": request.user.get_full_name(),
    })
    _gestionar_tiempo_inactividad(traslado.user_origen)
    return redirect("gestion:tablero")


@login_required
def cancelar_traslado(request, pk):
    traslado = get_object_or_404(
        TrasladoActividad, pk=pk, estado="Pendiente", activo=True
    )
    if request.user not in [traslado.user_origen, traslado.user_destino]:
        return redirect("gestion:tablero")

    traslado.estado = "Cancelado" if request.user == traslado.user_origen else "Rechazado"
    traslado.save()
    # Notificar a la otra parte
    if request.user == traslado.user_origen:
        _notificar_usuario(traslado.user_destino.pk, "traslado_respuesta", {
            "accion": "cancelado",
            "actividad": traslado.asignacion_origen.actividad.nombre,
            "origen": request.user.get_full_name(),
        })
    else:
        _notificar_usuario(traslado.user_origen.pk, "traslado_respuesta", {
            "accion": "rechazado",
            "actividad": traslado.asignacion_origen.actividad.nombre,
            "destino": request.user.get_full_name(),
        })
    messages.success(request, "Solicitud de traslado cancelada.")
    return redirect("gestion:tablero")


@login_required
def buscar_usuarios_traslado(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        query = request.GET.get("q", "")
        subarea_id = request.GET.get("subarea_id")
        proyecto_id = request.GET.get("proyecto_id")
        tipo_traslado = request.GET.get("tipo_traslado", "ejecutar")
        usuarios = User.objects.filter(
            activo=True, is_active=True
        ).exclude(id=request.user.id)

        # Si es tarea de proyecto, filtrar por rol segun tipo de card
        if proyecto_id:
            from apps.proyectos.models import MiembroProyecto
            # Verificar que el Admin tiene acceso a las subareas del proyecto
            if request.user.rol.nombre == "Admin":
                from apps.estructura.utils import get_admin_subareas
                admin_subareas = get_admin_subareas(request.user)
                from apps.proyectos.models import Proyecto
                proyecto = Proyecto.objects.filter(pk=proyecto_id, subareas__in=admin_subareas).first()
                if not proyecto:
                    return JsonResponse([], safe=False)
            rol_traslado = {"revision": "revisor", "aprobar": "aprobador", "ejecutar": "ejecutor"}.get(tipo_traslado, "ejecutor")
            miembros_ids = MiembroProyecto.objects.filter(
                proyecto_id=proyecto_id, activo=True, rol=rol_traslado
            ).values_list("user_id", flat=True)
            usuarios = usuarios.filter(id__in=miembros_ids)
        else:
            # Mismo nivel: Usuario solo ve Usuario, Admin ve Usuarios
            if request.user.rol.nombre == "Usuario":
                usuarios = usuarios.filter(
                    Q(rol__nombre="Usuario") | Q(roles_adicionales__nombre="Usuario")
                )
            elif request.user.rol.nombre == "Admin":
                usuarios = usuarios.filter(
                    Q(rol__nombre__in=["Usuario", "Admin"]) | Q(roles_adicionales__nombre__in=["Usuario", "Admin"])
                ).exclude(rol__nombre="Master")

            usuarios = usuarios.filter(
                subareas__subarea__in=SubArea.objects.filter(usuarios__user=request.user, activo=True),
                subareas__activo=True
            )
            if subarea_id:
                usuarios = usuarios.filter(subareas__subarea_id=subarea_id, subareas__activo=True)
        data = [{"id": u.id, "nombre": u.get_full_name(), "cedula": u.cedula} for u in usuarios.distinct()[:10]]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


@login_required
def asignacion_proyecto(request, pk):
    from apps.gestion.models import AsignacionActividad
    try:
        a = AsignacionActividad.objects.get(pk=pk, activo=True)
        try:
            tarea = a.tarea_proyecto
        except:
            tarea = None
        if tarea:
            return JsonResponse({"proyecto_id": tarea.proyecto_id, "proyecto_codigo": tarea.proyecto.codigo})
    except:
        pass
    return JsonResponse({"proyecto_id": None})


@login_required
def buscar_actividades_reemplazo(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        query = request.GET.get("q", "")
        subarea_id = request.GET.get("subarea_id")
        user_subareas = UserSubArea.objects.filter(user=request.user, activo=True)
        if subarea_id:
            user_subareas = user_subareas.filter(subarea_id=subarea_id)
        actividades = Actividad.objects.filter(
            subarea__in=user_subareas.values("subarea"), activo=True
        )
        if query:
            actividades = actividades.filter(nombre__icontains=query)
        data = [{"id": a.id, "nombre": a.nombre, "tipo": a.tipo_actividad.nombre} for a in actividades[:20]]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


@login_required
def api_traslados_pendientes(request):
    count = TrasladoActividad.objects.filter(user_destino=request.user, estado="Pendiente", activo=True).count()
    return JsonResponse({"count": count})


@login_required
def agregar_comentario(request, pk):
    if request.method != "POST":
        return redirect("gestion:tablero")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True)
    form = ComentarioForm(request.POST)
    if form.is_valid():
        comentario = form.save(commit=False)
        comentario.asignacion = asignacion
        comentario.user = request.user
        comentario.detalle = asignacion.planificacion_detalle
        comentario.save()
        _log_proyecto(asignacion, f"Comentario de {request.user.get_full_name()}: {comentario.texto[:60]}")
        messages.success(request, "Comentario agregado.")
    return redirect("gestion:detalle_actividad", pk=pk)


@login_required
def detalle_actividad(request, pk):
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True)
    es_traslado_destino = TrasladoActividad.objects.filter(
        asignacion_origen=asignacion, user_destino=request.user, estado="Pendiente", activo=True
    ).exists()
    if asignacion.user != request.user and request.user.rol.nombre not in ["Admin", "Master"] and not es_traslado_destino:
        return redirect("gestion:tablero")
    # Admin: verificar que tiene acceso a la subarea de la actividad
    if asignacion.user != request.user and request.user.rol.nombre == "Admin":
        from apps.estructura.utils import get_admin_subareas
        admin_subareas = get_admin_subareas(request.user)
        if asignacion.actividad.subarea_id not in [s.pk for s in admin_subareas]:
            messages.error(request, "No tienes acceso a la subarea de esta actividad.")
            return redirect("gestion:tablero")
    registros = RegistroTiempo.objects.filter(asignacion=asignacion, activo=True).order_by("-fecha_hora")
    comentarios = Comentario.objects.filter(asignacion=asignacion, activo=True).order_by("-fecha_creacion")
    traslados = TrasladoActividad.objects.filter(asignacion_origen=asignacion, activo=True)
    colaboraciones = Colaboracion.objects.filter(asignacion=asignacion, activo=True)
    historial = RevisionHistorial.objects.filter(asignacion=asignacion).select_related("user").order_by("-fecha")
    # Si es tarea de revision [Revisar], buscar la asignacion original del ejecutor
    orig_entregable = None
    orig_asignacion = None
    historia_aprobacion = None
    tareas_historia = []
    try:
        if asignacion.nombre_actividad and "[Revisar]" in asignacion.nombre_actividad:
            import re as _re
            match = _re.match(r'\[Revisar\]\s+(\S+):', asignacion.nombre_actividad)
            if match:
                from apps.proyectos.models import Tarea
                codigo_tarea = match.group(1)
                tarea_orig = Tarea.objects.filter(codigo=codigo_tarea, activo=True).first()
                if tarea_orig and tarea_orig.asignacion_id:
                    orig_asignacion = tarea_orig.asignacion
                    orig_entregable = orig_asignacion.entregable
        elif asignacion.nombre_actividad and "[Aprobar]" in asignacion.nombre_actividad:
            import re as _re
            match = _re.match(r'\[Aprobar\]\s+(\S+):', asignacion.nombre_actividad)
            if match:
                from apps.proyectos.models import HistoriaUsuario, Tarea, Incidencia
                codigo_hist = match.group(1)
                historia_aprobacion = HistoriaUsuario.objects.filter(codigo=codigo_hist, activo=True).first()
                if historia_aprobacion:
                    for t in historia_aprobacion.tareas.filter(activo=True).select_related("asignacion", "asignado_a", "sprint"):
                        info = {
                            "tarea": t,
                            "asignacion": t.asignacion,
                            "user": t.asignado_a,
                            "estado": t.get_estado_display(),
                            "incidencias": list(t.incidencias.filter(activo=True)),
                            "tiempo": t.asignacion.tiempo_formateado() if t.asignacion else "—",
                        }
                        tareas_historia.append(info)
    except Exception:
        pass
    # Timeline unificado (como tarea_detail)
    timeline = []
    timeline.append({
        "fecha": asignacion.fecha_asignacion, "tipo": "creacion", "icono": "plus-circle",
        "descripcion": f"Asignacion creada por {asignacion.origen_user.get_full_name() if asignacion.origen_user else 'Sistema'}"
    })
    # Agregar entrada de planificacion si existe
    planificacion = None
    if asignacion.planificacion_detalle and asignacion.planificacion_detalle.planificacion:
        planificacion = asignacion.planificacion_detalle.planificacion
        desc_planif = planificacion.descripcion or "Sin instrucciones"
        timeline.append({
            "fecha": planificacion.fecha_creacion, "tipo": "planificacion", "icono": "calendar-check",
            "descripcion": f"Planificacion: {desc_planif[:80]}"
        })
    for r in registros:
        icono = {"Inicio":"play-fill","Pausa":"pause-fill","Reanudacion":"arrow-clockwise","Finalizacion":"check-circle-fill","Traslado":"arrow-right-circle"}.get(r.evento,"circle")
        timeline.append({"fecha":r.fecha_hora,"tipo":"registro","icono":icono,"descripcion":f"{r.evento} por {asignacion.user.get_full_name()}{' ('+r.motivo_pausa+')' if r.motivo_pausa else ''}"})
    if asignacion.entregable:
        timeline.append({"fecha":asignacion.fecha_update,"tipo":"entregable","icono":"file-earmark-arrow-up","descripcion":f"Entregable adjuntado por {asignacion.user.get_full_name()}"})
    if orig_entregable and orig_asignacion:
        timeline.append({"fecha":orig_asignacion.fecha_update,"tipo":"entregable","icono":"file-earmark-arrow-up","descripcion":f"Entregable adjuntado por {orig_asignacion.user.get_full_name()} (ejecutor)"})
    for c in comentarios:
        timeline.append({"fecha":c.fecha_creacion,"tipo":"comentario","icono":"chat-text","descripcion":f"Comentario de {c.user.get_full_name()}: {c.texto[:60]}"})
    for t in traslados:
        timeline.append({
            "fecha": t.fecha_creacion, "tipo": "traslado", "icono": "arrow-right-circle",
            "descripcion": f"Solicitud de traslado de {t.user_origen.get_full_name()} a {t.user_destino.get_full_name()}"
        })
        if t.estado == "Aceptado" and t.fecha_update and t.fecha_update != t.fecha_creacion:
            timeline.append({
                "fecha": t.fecha_update, "tipo": "traslado", "icono": "check-circle",
                "descripcion": f"Traslado aceptado por {t.user_destino.get_full_name()}"
            })
        elif t.estado == "Rechazado":
            motivo = t.motivo or ""
            timeline.append({
                "fecha": t.fecha_update or t.fecha_creacion, "tipo": "traslado", "icono": "x-circle",
                "descripcion": f"Traslado rechazado por {t.user_destino.get_full_name()}{' (' + motivo[:40] + ')' if motivo else ''}"
            })
    for h in historial:
        timeline.append({"fecha":h.fecha,"tipo":"revision","icono":"check-circle" if h.accion=="aprobar" else "x-circle","descripcion":f"{'Aprobacion' if h.accion=='aprobar' else 'Rechazo'} por {h.user.get_full_name()}"})
    if asignacion.estado_revision == "aprobado":
        timeline.append({"fecha":asignacion.fecha_revision or asignacion.fecha_update,"tipo":"revision","icono":"check-circle","descripcion":"Tarea aprobada"})
    elif asignacion.estado_revision == "rechazado" and asignacion.revision_comentario:
        timeline.append({"fecha":asignacion.fecha_revision or asignacion.fecha_update,"tipo":"revision","icono":"x-circle","descripcion":f"Tarea rechazada: {asignacion.revision_comentario[:80]}"})
    if hasattr(asignacion, 'tarea_proyecto') and asignacion.tarea_proyecto:
        from apps.proyectos.models import Incidencia
        for inc in Incidencia.objects.filter(tarea=asignacion.tarea_proyecto, activo=True):
            timeline.append({"fecha":inc.fecha_creacion,"tipo":"incidencia","icono":"bug","descripcion":f"Bug {inc.codigo}: {inc.titulo[:60]} ({inc.get_estado_display()})"})
    timeline.sort(key=lambda x: x["fecha"], reverse=True)

    context = {
        "asignacion": asignacion,
        "registros": registros,
        "comentarios": comentarios,
        "traslados": traslados,
        "colaboraciones": colaboraciones,
        "historial": historial,
        "tiempo_efectivo": asignacion.tiempo_formateado(),
        "timeline": timeline,
        "planificacion": planificacion,
        "orig_entregable": orig_entregable,
        "orig_asignacion": orig_asignacion,
        "historia_aprobacion": historia_aprobacion,
        "tareas_historia": tareas_historia,
    }
    return render(request, "gestion/detalle_actividad.html", context)


@login_required
def calendario(request):
    from datetime import timedelta, date as dt_date
    hoy = timezone.now().date()
    year = int(request.GET.get("year", hoy.year))
    month = int(request.GET.get("month", hoy.month))
    vista = request.GET.get("vista", "dayGridMonth")

    asignaciones = AsignacionActividad.objects.filter(user=request.user, activo=True).select_related(
        "actividad", "actividad__tipo_actividad", "planificacion_detalle"
    )

    registros = RegistroTiempo.objects.filter(
        asignacion__user=request.user, activo=True
    ).select_related("asignacion__actividad").order_by("fecha_hora")

    # Construir eventos FullCalendar
    color_map = {
        "Pendiente": {"bg": "#c4d0e8", "txt": "#334155"},
        "EnCurso": {"bg": "#a7f0ba", "txt": "#1a7a3a"},
        "Pausada": {"bg": "#fde68a", "txt": "#92400e"},
        "Finalizada": {"bg": "#99f6e4", "txt": "#0f766e"},
    }
    events = []
    for a in asignaciones:
        color = color_map.get(a.estado, {"bg": "#e2e8f0", "txt": "#334155"})
        pd = a.planificacion_detalle
        start_date = pd.fecha_programada.strftime("%Y-%m-%d") if pd and pd.fecha_programada else a.fecha_asignacion.strftime("%Y-%m-%d")
        events.append({
            "id": str(a.pk),
            "title": a.actividad.nombre,
            "start": start_date,
            "allDay": True,
            "backgroundColor": color["bg"],
            "textColor": color["txt"],
            "borderColor": color["bg"],
            "extendedProps": {
                "tipo": a.actividad.tipo_actividad.nombre,
                "estado": a.estado,
                "tiempo": a.tiempo_formateado(),
                "origen": a.origen or "Manual",
            },
        })

    # Grid del mes para navegacion
    month_cal = []
    week = [None] * dt_date(year, month, 1).weekday()
    if month == 12:
        ultimo = dt_date(year + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo = dt_date(year, month + 1, 1) - timedelta(days=1)
    for d in range(1, ultimo.day + 1):
        week.append(dt_date(year, month, d))
        if len(week) == 7:
            month_cal.append(week)
            week = []
    if week:
        week += [None] * (7 - len(week))
        month_cal.append(week)

    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render(request, "gestion/calendario.html", {
        "vista": vista,
        "events_json": events,
        "year": year, "month": month, "mes": meses[month - 1],
        "prev_month": prev_month, "prev_year": prev_year,
        "next_month": next_month, "next_year": next_year,
        "hoy": hoy,
        "registros": registros,
    })


@login_required
def perfil(request):
    user = request.user
    ahora = timezone.now()
    hoy = ahora.date()
    from django.db.models import Sum, Count

    asignaciones = AsignacionActividad.objects.filter(user=user, activo=True)
    # Incluye inactivas para el tiempo real acumulado
    asignaciones_tiempo = AsignacionActividad.objects.filter(user=user)
    registros = RegistroTiempo.objects.filter(asignacion__user=user, activo=True)

    total_asignaciones = asignaciones.count()
    completadas = asignaciones.filter(estado="Finalizada").count()
    en_curso = asignaciones.filter(estado="EnCurso").count()
    pausadas = asignaciones.filter(estado="Pausada").count()
    pendientes = asignaciones.filter(estado="Pendiente").count()
    prorrogas = asignaciones.filter(prorroga_count__gt=0).count()

    tiempo_total = sum(a.tiempo_efectivo() for a in asignaciones_tiempo)
    horas = int(tiempo_total // 3600)
    minutos = int((tiempo_total % 3600) // 60)

    tiempo_pausado = sum(a.tiempo_pausado() for a in asignaciones_tiempo)
    horas_p = int(tiempo_pausado // 3600)
    mins_p = int((tiempo_pausado % 3600) // 60)

    nro_values = registros.filter(evento="Finalizacion", nro_actividad__isnull=False).values_list("nro_actividad", flat=True)
    total_items = sum(int(v) for v in nro_values if v.strip().isdigit())

    hoy_registros_raw = registros.order_by("-fecha_hora")[:50]
    hoy_registros = [r for r in hoy_registros_raw if r.fecha_hora.date() == hoy][:15]
    ultimas = asignaciones.select_related("actividad", "actividad__tipo_actividad").order_by("-fecha_asignacion")[:5]

    return render(request, "gestion/perfil.html", {
        "total_asignaciones": total_asignaciones,
        "completadas": completadas,
        "en_curso": en_curso,
        "pausadas": pausadas,
        "pendientes": pendientes,
        "prorrogas": prorrogas,
        "horas": horas,
        "minutos": minutos,
        "horas_p": horas_p,
        "mins_p": mins_p,
        "total_items": total_items,
        "hoy_registros": hoy_registros,
        "ultimas": ultimas,
    })


@login_required
def revisiones_list(request):
    from apps.estructura.models import SubArea, UserSubArea
    from django.core.paginator import Paginator

    subareas = get_admin_subareas(request.user) if request.user.rol.nombre in ["Master", "Admin"] else SubArea.objects.filter(
        usuarios__user=request.user, activo=True
    )

    user_id = request.GET.get("user_id")
    estado_filtro = request.GET.get("estado", "")

    revisiones = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas,
        actividad__tipo_actividad__requiere_entregable=True,
        activo=True,
    ).select_related(
        "user", "actividad__tipo_actividad", "actividad__subarea__area"
    ).prefetch_related("comentarios").order_by("-fecha_asignacion")

    # Si no hay filtro o es pendiente: solo actividades en estado Revision (pendientes de revision)
    # Si filtro aprobado/rechazado: todas las que tengan ese estado_revision
    if estado_filtro == "pendiente":
        revisiones = revisiones.filter(estado="Revision", estado_revision="pendiente")
    elif estado_filtro:
        revisiones = revisiones.filter(estado_revision=estado_filtro)
    else:
        revisiones = revisiones.filter(estado="Revision")

    if user_id:
        revisiones = revisiones.filter(user_id=user_id)

    paginator = Paginator(revisiones, 20)
    page = request.GET.get("page", 1)
    revisiones_page = paginator.get_page(page)

    usuarios = User.objects.filter(
        Q(asignaciones__actividad__subarea__in=subareas, asignaciones__estado="Revision", asignaciones__estado_revision="pendiente") |
        Q(asignaciones__actividad__subarea__in=subareas, asignaciones__estado_revision__in=["aprobado", "rechazado"]),
        activo=True
    ).distinct().order_by("nombre")

    return render(request, "gestion/revisiones.html", {
        "revisiones": revisiones_page,
        "page_obj": revisiones_page,
        "usuarios": usuarios,
        "user_id": int(user_id) if user_id else None,
        "estado_filtro": estado_filtro,
    })


@login_required
def revision_aprobar(request, pk):
    if request.method != "POST":
        return redirect("gestion:revisiones")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True, estado="Revision")
    if request.user.rol.nombre not in ["Master", "Admin"]:
        return redirect("gestion:revisiones")
    comentario = request.POST.get("comentario", "")
    entregable_file = request.FILES.get("revision_entregable")
    if entregable_file:
        asignacion.revision_entregable = entregable_file
    asignacion.estado = "Finalizada"
    asignacion.estado_revision = "aprobado"
    asignacion.revision_comentario = comentario or None
    asignacion.fecha_revision = timezone.now()
    asignacion.save()
    RevisionHistorial.objects.create(
        asignacion=asignacion, user=request.user,
        accion="aprobado", comentario=comentario or ""
    )
    messages.success(request, f"Actividad '{asignacion.actividad.nombre}' aprobada.")
    return redirect("gestion:revisiones")


@login_required
def revision_rechazar(request, pk):
    if request.method != "POST":
        return redirect("gestion:revisiones")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True, estado="Revision")
    if request.user.rol.nombre not in ["Master", "Admin"]:
        return redirect("gestion:revisiones")
    comentario = request.POST.get("comentario", "")
    if not comentario:
        messages.error(request, "Debes indicar el motivo del rechazo.")
        return redirect("gestion:revisiones")
    asignacion.estado = "Pendiente"
    asignacion.estado_revision = "rechazado"
    asignacion.revision_comentario = comentario
    asignacion.fecha_revision = timezone.now()
    asignacion.prorroga_count += 1
    asignacion.save()
    RevisionHistorial.objects.create(
        asignacion=asignacion, user=request.user,
        accion="rechazado", comentario=comentario
    )
    messages.warning(request, f"Actividad '{asignacion.actividad.nombre}' rechazada. Se ha regresado a pendiente.")
    return redirect("gestion:revisiones")
