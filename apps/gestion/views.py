from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from datetime import timedelta, date as dt_date
import datetime
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
    fecha_sel_dt = timezone.make_aware(datetime.datetime.combine(fecha_sel, datetime.datetime.min.time()))
    fecha_sel_fin = fecha_sel_dt + timedelta(days=1)

    asignaciones = AsignacionActividad.objects.filter(
        user=request.user, activo=True,
    ).filter(
        Q(estado__in=["EnCurso", "Pausada", "Finalizada", "Cancelada", "Trasladada", "Revision"]) |
        Q(planificacion_detalle__isnull=True) |
        Q(planificacion_detalle__fecha_programada__isnull=True) |
        Q(planificacion_detalle__fecha_programada__lte=ahora) |
        Q(actividad__tipo_actividad__requiere_entregable=True)
    ).select_related("actividad__tipo_actividad", "actividad__subarea__area", "planificacion_detalle__planificacion"
    ).prefetch_related("comentarios")

    if subarea_id:
        asignaciones = asignaciones.filter(
            Q(actividad__subarea_id=subarea_id) |
            Q(planificacion_detalle__planificacion__subarea_id=subarea_id)
        )

    # Planificadas para la fecha seleccionada
    planificadas = AsignacionActividad.objects.filter(
        user=request.user, activo=True, estado="Pendiente",
        planificacion_detalle__isnull=False,
        planificacion_detalle__fecha_programada__gte=fecha_sel_dt,
        planificacion_detalle__fecha_programada__lt=fecha_sel_fin,
    ).select_related("actividad__tipo_actividad", "actividad__subarea__area", "planificacion_detalle__planificacion").prefetch_related("comentarios")
    if subarea_id:
        planificadas = planificadas.filter(
            Q(actividad__subarea_id=subarea_id) |
            Q(planificacion_detalle__planificacion__subarea_id=subarea_id)
        )

    # Todas las planificadas pendientes (sin filtro de fecha) para "Iniciar siguiente"
    planificadas_todas = AsignacionActividad.objects.filter(
        user=request.user, activo=True, estado="Pendiente",
        planificacion_detalle__isnull=False,
    ).select_related("actividad__tipo_actividad", "actividad__subarea__area").order_by("planificacion_detalle__fecha_programada", "actividad__nombre")

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

    reemplazo = request.POST.get("reemplazo_actividad")
    entregable_file = request.FILES.get("entregable")

    form = RegistroTiempoForm(request.POST, request.FILES)
    if form.is_valid():
        requiere_ent = asignacion.actividad.tipo_actividad.requiere_entregable
        if not requiere_ent and not form.cleaned_data.get("nro_actividad", "").strip():
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
        if requiere_ent and entregable_file:
            asignacion.entregable = entregable_file
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

        comentario_texto = form.cleaned_data.get("comentario", "").strip()
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
            messages.success(request, f"Actividad '{asignacion.actividad.nombre}' finalizada. Ahora estas trabajando en '{reemplazo_asig.actividad.nombre}'.")
        else:
            messages.success(request, f"Actividad '{asignacion.actividad.nombre}' finalizada.")
    else:
        messages.error(request, "El numero de actividad (cantidad realizada) es obligatorio para finalizar.")
    _gestionar_tiempo_inactividad(request.user)
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
        usuarios = User.objects.filter(
            activo=True, is_active=True
        ).exclude(id=request.user.id)

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
        if query:
            usuarios = usuarios.filter(
                Q(nombre__icontains=query) | Q(apellido__icontains=query) | Q(cedula__icontains=query)
            )
        if subarea_id:
            usuarios = usuarios.filter(subareas__subarea_id=subarea_id, subareas__activo=True)
        data = [{"id": u.id, "nombre": u.get_full_name(), "cedula": u.cedula} for u in usuarios.distinct()[:10]]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


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
    registros = RegistroTiempo.objects.filter(asignacion=asignacion, activo=True).order_by("-fecha_hora")
    comentarios = Comentario.objects.filter(asignacion=asignacion, activo=True).order_by("-fecha_creacion")
    traslados = TrasladoActividad.objects.filter(asignacion_origen=asignacion, activo=True)
    colaboraciones = Colaboracion.objects.filter(asignacion=asignacion, activo=True)
    historial = RevisionHistorial.objects.filter(asignacion=asignacion).select_related("user").order_by("-fecha")
    context = {
        "asignacion": asignacion,
        "registros": registros,
        "comentarios": comentarios,
        "traslados": traslados,
        "colaboraciones": colaboraciones,
        "historial": historial,
        "tiempo_efectivo": asignacion.tiempo_formateado(),
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
        "Pendiente": {"bg": "#93c5fd", "txt": "#1e40af"},
        "EnCurso": {"bg": "#86efac", "txt": "#166534"},
        "Pausada": {"bg": "#cbd5e1", "txt": "#475569"},
        "Finalizada": {"bg": "#bbf7d0", "txt": "#166534"},
        "Vence": {"bg": "#fecaca", "txt": "#991b1b"},
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

    hoy_registros = registros.filter(fecha_hora__date=hoy).order_by("-fecha_hora")[:15]
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
