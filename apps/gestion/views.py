from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from apps.actividades.models import Actividad, TipoActividad
from apps.estructura.models import SubArea, UserSubArea
from apps.planificacion.models import PlanificacionDetalle
from apps.accounts.models import User
from .models import AsignacionActividad, RegistroTiempo, TrasladoActividad, Colaboracion, Comentario
from .forms import RegistroTiempoForm, ComentarioForm


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

    user_subareas = UserSubArea.objects.filter(user=request.user, activo=True).select_related("subarea__area__empresa")

    if not subarea_id and user_subareas.exists():
        subarea_id = user_subareas.first().subarea_id
    if not empresa_id and user_subareas.exists():
        empresa_id = user_subareas.first().subarea.area.empresa_id

    asignaciones = AsignacionActividad.objects.filter(
        user=request.user, activo=True
    ).select_related("actividad__tipo_actividad", "actividad__subarea__area__empresa", "planificacion_detalle__planificacion")

    if subarea_id:
        asignaciones = asignaciones.filter(
            Q(actividad__subarea_id=subarea_id) |
            Q(planificacion_detalle__planificacion__subarea_id=subarea_id)
        )

    planificadas = asignaciones.filter(estado="Pendiente")
    en_curso = asignaciones.filter(estado="EnCurso")
    pausadas = asignaciones.filter(estado="Pausada")

    hoy = timezone.now().date()
    # Solo finalizadas del dia actual, ordenadas por ultimo evento
    finalizadas = asignaciones.filter(
        estado="Finalizada",
        registros__evento="Finalizacion",
        registros__fecha_hora__date=hoy
    ).order_by("-registros__fecha_hora").distinct()

    actividades_hoy = asignaciones.filter(estado__in=["Pendiente", "EnCurso", "Pausada"])

    actividad_no_programada_tipo = TipoActividad.objects.filter(
        subarea__in=user_subareas.values("subarea"),
        nombre__icontains="No Programada",
        activo=True
    ).first()

    context = {
        "user_subareas": user_subareas,
        "subarea_id": int(subarea_id) if subarea_id else None,
        "empresa_id": int(empresa_id) if empresa_id else None,
        "planificadas": planificadas,
        "en_curso": en_curso,
        "pausadas": pausadas,
        "finalizadas": finalizadas,
        "actividades_hoy": actividades_hoy,
        "hoy": hoy,
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

    return redirect("gestion:tablero")


@login_required
def finalizar_actividad(request, pk):
    if request.method != "POST":
        return redirect("gestion:tablero")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, user=request.user, activo=True)

    if asignacion.estado not in ["EnCurso", "Pausada"]:
        messages.error(request, f"Solo puedes finalizar actividades En Curso o Pausadas. Estado actual: '{asignacion.get_estado_display()}'.")
        return redirect("gestion:tablero")

    form = RegistroTiempoForm(request.POST)
    if form.is_valid():
        if not form.cleaned_data.get("nro_actividad", "").strip():
            messages.error(request, "El numero de actividad (cantidad realizada) es obligatorio para finalizar.")
            return redirect("gestion:tablero")
        asignacion.estado = "Finalizada"
        asignacion.save()
        registro = form.save(commit=False)
        registro.asignacion = asignacion
        registro.evento = "Finalizacion"
        registro.fecha_hora = timezone.now()
        registro.save()
        # Iniciar actividad de reemplazo si se selecciono
        reemplazo_pk = request.POST.get("reemplazo_actividad")
        if reemplazo_pk:
            reemplazo = AsignacionActividad.objects.filter(
                pk=reemplazo_pk, user=request.user, activo=True, estado="Pendiente"
            ).first()
            if reemplazo:
                _pausar_activas(request.user)
                reemplazo.estado = "EnCurso"
                reemplazo.save()
                RegistroTiempo.objects.create(
                    asignacion=reemplazo, evento="Inicio", fecha_hora=timezone.now(),
                    comentario=f"Iniciada tras finalizar '{asignacion.actividad.nombre}'"
                )
                messages.success(request, f"Actividad '{asignacion.actividad.nombre}' finalizada. Ahora estas trabajando en '{reemplazo.actividad.nombre}'.")
            else:
                messages.success(request, f"Actividad '{asignacion.actividad.nombre}' finalizada.")
        else:
            messages.success(request, f"Actividad '{asignacion.actividad.nombre}' finalizada con {registro.nro_actividad or '0'} unidades registradas.")
    else:
        messages.error(request, "El numero de actividad (cantidad realizada) es obligatorio para finalizar.")
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

        _pausar_activas(request.user)

        asignacion = AsignacionActividad.objects.create(
            user=request.user,
            actividad=actividad,
            estado="EnCurso",
            origen="Manual",
            origen_user=request.user,
        )
        RegistroTiempo.objects.create(
            asignacion=asignacion,
            evento="Inicio",
            fecha_hora=timezone.now(),
            comentario=comentario or None,
        )
        messages.success(request, f"Actividad '{actividad.nombre}' iniciada.")
        return redirect("gestion:tablero")

    context = {
        "user_subareas": user_subareas,
    }
    return render(request, "gestion/crear_no_programada.html", context)


@login_required
def trasladar_actividad(request, pk):
    if request.method != "POST":
        return redirect("gestion:tablero")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, user=request.user, activo=True)

    if asignacion.estado not in ["Pendiente", "EnCurso", "Pausada"]:
        messages.error(request, f"Solo puedes trasladar actividades Pendientes, En Curso o Pausadas. Esta actividad esta '{asignacion.get_estado_display()}'.")
        return redirect("gestion:tablero")

    user_destino_id = request.POST.get("user_destino")
    actividad_reemplazo_id = request.POST.get("actividad_reemplazo")
    motivo = request.POST.get("motivo", "")

    if not user_destino_id or not actividad_reemplazo_id:
        messages.error(request, "Debes seleccionar un usuario destino y tu actividad de reemplazo.")
        return redirect("gestion:tablero")

    user_destino = get_object_or_404(User, pk=user_destino_id, activo=True)
    actividad_reemplazo = get_object_or_404(Actividad, pk=actividad_reemplazo_id, activo=True)

    # Evitar solicitudes duplicadas pendientes
    if TrasladoActividad.objects.filter(
        asignacion_origen=asignacion, user_destino=user_destino, estado="Pendiente", activo=True
    ).exists():
        messages.error(request, "Ya existe una solicitud de traslado pendiente para esta actividad.")
        return redirect("gestion:tablero")

    TrasladoActividad.objects.create(
        asignacion_origen=asignacion,
        user_origen=request.user,
        user_destino=user_destino,
        actividad_reemplazo=actividad_reemplazo,
        estado="Pendiente",
        motivo=motivo,
    )

    messages.success(request, f"Solicitud de traslado enviada a {user_destino.get_full_name()}. Pendiente de aceptacion.")
    return redirect("gestion:tablero")


@login_required
def aceptar_traslado(request, pk):
    traslado = get_object_or_404(TrasladoActividad, pk=pk, user_destino=request.user, estado="Pendiente", activo=True)

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
    return redirect("gestion:tablero")


@login_required
def cancelar_traslado(request, pk):
    traslado = get_object_or_404(
        TrasladoActividad, pk=pk, estado="Pendiente", activo=True
    )
    # Solo el origen o el destino pueden cancelar
    if request.user not in [traslado.user_origen, traslado.user_destino]:
        return redirect("gestion:tablero")

    traslado.estado = "Cancelado" if request.user == traslado.user_origen else "Rechazado"
    traslado.save()
    messages.success(request, "Solicitud de traslado cancelada.")
    return redirect("gestion:tablero")
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
            usuarios = usuarios.filter(rol__nombre="Usuario")
        elif request.user.rol.nombre == "Admin":
            usuarios = usuarios.filter(rol__nombre__in=["Usuario", "Admin"]).exclude(rol__nombre="Master")

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
        comentario.save()
        messages.success(request, "Comentario agregado.")
    return redirect("gestion:tablero")


@login_required
def detalle_actividad(request, pk):
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True)
    if asignacion.user != request.user and request.user.rol.nombre not in ["Admin", "Master"]:
        return redirect("gestion:tablero")
    registros = RegistroTiempo.objects.filter(asignacion=asignacion, activo=True).order_by("-fecha_hora")
    comentarios = Comentario.objects.filter(asignacion=asignacion, activo=True).order_by("-fecha_creacion")
    traslados = TrasladoActividad.objects.filter(asignacion_origen=asignacion, activo=True)
    colaboraciones = Colaboracion.objects.filter(asignacion=asignacion, activo=True)
    context = {
        "asignacion": asignacion,
        "registros": registros,
        "comentarios": comentarios,
        "traslados": traslados,
        "colaboraciones": colaboraciones,
        "tiempo_efectivo": asignacion.tiempo_formateado(),
    }
    return render(request, "gestion/detalle_actividad.html", context)


@login_required
def calendario(request):
    from datetime import timedelta, date as dt_date
    import calendar as cal_mod
    hoy = timezone.now().date()
    year = int(request.GET.get("year", hoy.year))
    month = int(request.GET.get("month", hoy.month))
    vista = request.GET.get("vista", "mes")  # mes, semana, dia

    # Rango segun vista
    week_days = []
    if vista == "dia":
        dia_sel = dt_date(year, month, int(request.GET.get("dia", hoy.day)))
        first_day = last_day = dia_sel
    elif vista == "semana":
        # Encontrar el lunes de la semana
        dia_sel = dt_date(year, month, int(request.GET.get("dia", hoy.day)))
        inicio_semana = dia_sel - timedelta(days=dia_sel.weekday())
        first_day = inicio_semana
        last_day = inicio_semana + timedelta(days=6)
    else:
        first_day = dt_date(year, month, 1)
        if month == 12:
            last_day = dt_date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = dt_date(year, month + 1, 1) - timedelta(days=1)

    # Poblar week_days solo para vista semana
    if vista == "semana":
        d = first_day
        while d <= last_day:
            week_days.append(d)
            d += timedelta(days=1)

    # Asignaciones del usuario
    asignaciones = AsignacionActividad.objects.filter(user=request.user, activo=True).select_related(
        "actividad", "actividad__tipo_actividad", "planificacion_detalle"
    )

    # Registros de tiempo del usuario
    registros = RegistroTiempo.objects.filter(
        asignacion__user=request.user, activo=True
    ).select_related("asignacion__actividad").order_by("fecha_hora")

    # Construir datos por dia
    dias_con_actividades = {}
    for a in asignaciones:
        dia = a.fecha_asignacion.date() if hasattr(a.fecha_asignacion, 'date') else a.fecha_asignacion
        iso = dia.isoformat()
        dias_con_actividades.setdefault(iso, {"count": 0, "items": []})
        dias_con_actividades[iso]["count"] += 1
        dias_con_actividades[iso]["items"].append({
            "nombre": a.actividad.nombre,
            "tipo": a.actividad.tipo_actividad.nombre,
            "estado": a.estado,
            "tiempo": a.tiempo_formateado(),
            "hora": 8,  # hora por defecto si no hay registros
        })
        pd = a.planificacion_detalle
        if pd and pd.fecha_limite:
            ld = pd.fecha_limite.date() if hasattr(pd.fecha_limite, 'date') else pd.fecha_limite
            liso = ld.isoformat()
            dias_con_actividades.setdefault(liso, {"count": 0, "items": []})
            dias_con_actividades[liso]["count"] += 1
            dias_con_actividades[liso]["items"].append({
                "nombre": a.actividad.nombre,
                "tipo": a.actividad.tipo_actividad.nombre,
                "estado": "Vence",
                "tiempo": "",
                "hora": 8,
            })

    # Asignar hora real desde RegistroTiempo (primer evento del dia)
    for r in registros:
        rd = r.fecha_hora.date()
        iso = rd.isoformat()
        if iso in dias_con_actividades:
            h = r.fecha_hora.hour
            for item in dias_con_actividades[iso]["items"]:
                if item["nombre"] == r.asignacion.actividad.nombre and item["hora"] == 8:
                    item["hora"] = h
                    break

    # Construir timeline por hora para vistas dia/semana
    horas = list(range(24))
    timeline_flat = []  # [(iso, hora, item_dict)]
    if vista in ("dia", "semana"):
        rango = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
        for d in rango:
            iso = d.isoformat()
            if iso in dias_con_actividades:
                for item in dias_con_actividades[iso]["items"]:
                    timeline_flat.append((iso, item["hora"], item))

    # Grid del mes (necesario para navegacion en todas las vistas)
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
    dias_semana = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]

    # Determinar fecha actual para navegacion
    nav_date = dt_date(year, month, first_day.day if vista != "dia" else dia_sel.day)

    return render(request, "gestion/calendario.html", {
        "vista": vista,
        "month_cal": month_cal,
        "week_days": week_days if vista == "semana" else [],
        "dia_sel": dia_sel if vista in ("semana", "dia") else first_day,
        "dias_con_actividades": dias_con_actividades,
        "timeline_flat": timeline_flat if vista in ("dia", "semana") else [],
        "horas": horas,
        "year": year, "month": month, "mes": meses[month - 1],
        "hoy": hoy,
        "registros": registros,
        "prev_month": month - 1 if month > 1 else 12,
        "prev_year": year if month > 1 else year - 1,
        "next_month": month + 1 if month < 12 else 1,
        "next_year": year if month < 12 else year + 1,
    })


@login_required
def perfil(request):
    user = request.user
    ahora = timezone.now()
    hoy = ahora.date()
    from django.db.models import Sum, Count

    asignaciones = AsignacionActividad.objects.filter(user=user, activo=True)
    registros = RegistroTiempo.objects.filter(asignacion__user=user, activo=True)

    total_asignaciones = asignaciones.count()
    completadas = asignaciones.filter(estado="Finalizada").count()
    en_curso = asignaciones.filter(estado="EnCurso").count()
    pausadas = asignaciones.filter(estado="Pausada").count()
    pendientes = asignaciones.filter(estado="Pendiente").count()
    prorrogas = asignaciones.filter(prorroga_count__gt=0).count()

    tiempo_total = sum(a.tiempo_efectivo() for a in asignaciones)
    horas = int(tiempo_total // 3600)
    minutos = int((tiempo_total % 3600) // 60)

    tiempo_pausado = sum(a.tiempo_pausado() for a in asignaciones)
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
