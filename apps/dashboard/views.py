from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q, Avg, F, OuterRef, Subquery, Max
from django.core.cache import cache
from collections import OrderedDict
from django.utils import timezone
from datetime import date, timedelta
from apps.gestion.models import AsignacionActividad, RegistroTiempo
from apps.estructura.models import UserSubArea, SubArea
from apps.accounts.models import User, Empresa


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.rol.nombre not in ["Admin", "Master"]:
            from django.shortcuts import redirect
            return redirect("root")
        return view_func(request, *args, **kwargs)
    return wrapper


def get_admin_subareas(user):
    if user.rol.nombre == "Master":
        return SubArea.objects.filter(activo=True)
    return SubArea.objects.filter(usuarios__user=user, activo=True)


@login_required
@admin_required
def dashboard_admin(request):
    subareas = get_admin_subareas(request.user)

    empresa_id = request.GET.get("empresa_id")
    if empresa_id:
        try:
            empresa_id = int(empresa_id)
        except (ValueError, TypeError):
            empresa_id = None

    subarea_id = request.GET.get("subarea_id")
    if subarea_id:
        subareas = subareas.filter(id=subarea_id)

    user_id = request.GET.get("user_id")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    usuarios = User.objects.filter(
        subareas__subarea__in=subareas, subareas__activo=True, activo=True
    ).filter(
        Q(rol__nombre="Usuario") | Q(roles_adicionales__nombre="Usuario")
    ).distinct()

    if user_id:
        usuarios = usuarios.filter(id=user_id)

    asignaciones = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas, activo=True
    ).filter(user__activo=True)

    # Todas las asignaciones (inclusive inactivas) para calcular tiempo real
    asignaciones_tiempo = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas
    )

    if user_id:
        asignaciones = asignaciones.filter(user_id=user_id)
        asignaciones_tiempo = asignaciones_tiempo.filter(user_id=user_id)

    if fecha_desde:
        asignaciones = asignaciones.filter(fecha_asignacion__date__gte=fecha_desde)
        asignaciones_tiempo = asignaciones_tiempo.filter(fecha_asignacion__date__gte=fecha_desde)
    if fecha_hasta:
        asignaciones = asignaciones.filter(fecha_asignacion__date__lte=fecha_hasta)
        asignaciones_tiempo = asignaciones_tiempo.filter(fecha_asignacion__date__lte=fecha_hasta)

    registros_base = RegistroTiempo.objects.filter(
        asignacion__actividad__subarea__in=subareas, activo=True
    ).filter(asignacion__user__activo=True)
    if user_id:
        registros_base = registros_base.filter(asignacion__user_id=user_id)
    if fecha_desde:
        registros_base = registros_base.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        registros_base = registros_base.filter(fecha_hora__date__lte=fecha_hasta)

    # Cache key para KPIs agregados
    cache_key = f"dash_kpi_{request.user.pk}_{subarea_id}_{fecha_desde}_{fecha_hasta}_{empresa_id}"
    kpi_cached = cache.get(cache_key)
    if kpi_cached:
        return render(request, "dashboard/dashboard_admin.html", kpi_cached)

    total_actividades = asignaciones.count()
    actividades_curso = asignaciones.filter(estado="EnCurso").count()
    actividades_finalizadas = asignaciones.filter(estado__in=["Finalizada", "Trasladada"]).count()
    actividades_pausadas = asignaciones.filter(estado="Pausada").count()
    actividades_pendientes = asignaciones.filter(estado="Pendiente").count()
    prorrogas_total = asignaciones.aggregate(total=Sum("prorroga_count"))["total"] or 0
    vencidas_total = asignaciones.filter(
        planificacion_detalle__fecha_vencimiento__lt=timezone.now(),
        actividad__tipo_actividad__requiere_fecha_limite=True,
        estado__in=["Pendiente", "Pausada"]
    ).count()

    vencidas_detalle = asignaciones.filter(
        planificacion_detalle__fecha_vencimiento__lt=timezone.now(),
        actividad__tipo_actividad__requiere_fecha_limite=True,
        estado__in=["Pendiente", "Pausada"]
    ).select_related("user", "actividad", "planificacion_detalle").order_by(
        "planificacion_detalle__fecha_vencimiento"
    )[:10]

    # Tiempo total trabajado: usa cache en BD (Sum) en vez de iterar tiempo_efectivo()
    tiempo_total_seg = asignaciones_tiempo.aggregate(total=Sum("tiempo_total_segundos"))["total"] or 0
    # Sumar tiempo extra para actividades EnCurso (ultimo segmento sin cerrar)
    en_curso_ids = list(asignaciones_tiempo.filter(estado="EnCurso").values_list("pk", flat=True))
    if en_curso_ids:
        ultimos = RegistroTiempo.objects.filter(
            asignacion_id__in=en_curso_ids, activo=True,
            evento__in=["Inicio", "Reanudacion"]
        ).values("asignacion_id").annotate(ultima=Max("fecha_hora"))
        ahora = timezone.now()
        for u in ultimos:
            tiempo_total_seg += int((ahora - u["ultima"]).total_seconds())

    horas_total = int(tiempo_total_seg // 3600)
    mins_total = int((tiempo_total_seg % 3600) // 60)

    # Tiempo promedio por actividad: nro de items finalizados
    nro_values = registros_base.filter(
        evento="Finalizacion", nro_actividad__isnull=False
    ).values_list("nro_actividad", flat=True)
    nro_total = sum(int(v) for v in nro_values if v.strip().isdigit())
    if nro_total and tiempo_total_seg > 0:
        prom_seg_x_item = tiempo_total_seg / nro_total
        prom_min = int(prom_seg_x_item // 60)
        prom_seg = int(prom_seg_x_item % 60)
        promedio_item = f"{prom_min}:{prom_seg:02d}"
    else:
        promedio_item = "--"

    # Productividad media
    total_asig = total_actividades
    productividad_media = round(
        (actividades_finalizadas / total_asig * 100) if total_asig > 0 else 0, 1
    )

    hoy = timezone.now().date()
    finalizadas_hoy = registros_base.filter(
        evento="Finalizacion", fecha_hora__date=hoy
    ).count()

    def _dead_time_sum(usuario_ids):
        """Calcula dead time para MULTIPLES usuarios en 1 query."""
        from collections import defaultdict
        regs = list(RegistroTiempo.objects.filter(
            asignacion__actividad__subarea__in=subareas,
            asignacion__user_id__in=usuario_ids, activo=True,
            evento__in=["Inicio", "Reanudacion", "Finalizacion", "Traslado"],
        ).values("asignacion__user_id", "evento", "fecha_hora").order_by("asignacion__user_id", "fecha_hora"))
        if fecha_desde:
            fd = date.fromisoformat(fecha_desde)
            regs = [r for r in regs if r["fecha_hora"].date() >= fd]
        if fecha_hasta:
            fh = date.fromisoformat(fecha_hasta)
            regs = [r for r in regs if r["fecha_hora"].date() <= fh]
        muertos = defaultdict(int)
        uid_actual = None
        anterior = None
        for r in regs:
            if r["asignacion__user_id"] != uid_actual:
                uid_actual = r["asignacion__user_id"]
                anterior = None
            if anterior and r["fecha_hora"].date() == anterior["fecha_hora"].date():
                if anterior["evento"] in ("Finalizacion", "Traslado") and r["evento"] in ("Inicio", "Reanudacion"):
                    gap = (r["fecha_hora"] - anterior["fecha_hora"]).total_seconds()
                    if gap > 0:
                        muertos[uid_actual] += gap
            anterior = r
        return muertos

    user_pks = [u.pk for u in usuarios]
    mostrar_todos = request.GET.get("todos") == "1"

    # Batch: tiempo agregado por usuario en 1 query
    tiempo_por_user = defaultdict(lambda: {"activo": 0, "pausado": 0})
    agg_tiempo = asignaciones_tiempo.filter(user_id__in=user_pks).values("user_id").annotate(
        total_activo=Sum("tiempo_total_segundos"),
        total_pausado=Sum("tiempo_pausado_segundos"),
    )
    ahora = timezone.now()
    for row in agg_tiempo:
        uid = row["user_id"]
        tiempo_por_user[uid]["activo"] = row["total_activo"] or 0
        tiempo_por_user[uid]["pausado"] = row["total_pausado"] or 0

    # Sumar tiempo extra para EnCurso (batch, 1 query)
    en_curso_ids = list(asignaciones_tiempo.filter(
        user_id__in=user_pks, estado="EnCurso"
    ).values_list("pk", "user_id"))
    if en_curso_ids:
        ids_asig = [e[0] for e in en_curso_ids]
        ultimos = RegistroTiempo.objects.filter(
            asignacion_id__in=ids_asig, activo=True,
            evento__in=["Inicio", "Reanudacion"]
        ).values("asignacion_id").annotate(ultima=Max("fecha_hora"))
        asig_uid = {e[0]: e[1] for e in en_curso_ids}
        for u in ultimos:
            uid = asig_uid.get(u["asignacion_id"])
            if uid:
                tiempo_por_user[uid]["activo"] += int((ahora - u["ultima"]).total_seconds())

    # Batch _dead_time (1 query)
    muertos = _dead_time_sum(user_pks)

    # nro_actividad batch por usuario
    nro_batch = defaultdict(int)
    nro_rows = registros_base.filter(
        asignacion__user_id__in=user_pks,
        evento="Finalizacion", nro_actividad__isnull=False
    ).values_list("asignacion__user_id", "nro_actividad")
    for uid, val in nro_rows:
        if isinstance(val, str) and val.strip().isdigit():
            nro_batch[uid] += int(val)

    # Contar estados por usuario en 1 query
    estados_agg = asignaciones.filter(user_id__in=user_pks).values("user_id", "estado").annotate(cnt=Count("pk"))
    estados_por_user = defaultdict(dict)
    for row in estados_agg:
        estados_por_user[row["user_id"]][row["estado"]] = row["cnt"]

    count_por_user = dict(asignaciones.filter(user_id__in=user_pks).values("user_id").annotate(total=Count("pk")).values_list("user_id", "total"))

    prorroga_por_user = dict(asignaciones.filter(user_id__in=user_pks, prorroga_count__gt=0).values("user_id").annotate(total=Sum("prorroga_count")).values_list("user_id", "total"))

    vencidas_por_user = dict(asignaciones.filter(
        user_id__in=user_pks,
        planificacion_detalle__fecha_vencimiento__lt=timezone.now(),
        actividad__tipo_actividad__requiere_fecha_limite=True,
        estado__in=["Pendiente", "Pausada"]
    ).values("user_id").annotate(total=Count("pk")).values_list("user_id", "total"))

    usuarios_stats = []
    for usuario in usuarios:
        uid = usuario.pk
        estados = estados_por_user.get(uid, {})
        u_total = count_por_user.get(uid, 0)
        u_fin = estados.get("Finalizada", 0) + estados.get("Trasladada", 0)
        u_curso = estados.get("EnCurso", 0)
        u_pausa = estados.get("Pausada", 0)
        u_pen = estados.get("Pendiente", 0)
        u_ven = vencidas_por_user.get(uid, 0)
        u_prr = prorroga_por_user.get(uid, 0)
        t_activo = tiempo_por_user[uid]["activo"]
        t_pausado = tiempo_por_user[uid]["pausado"]
        t_muerto = muertos.get(uid, 0)
        nro_items = nro_batch.get(uid, 0)
        prom = f"{int(t_activo//60//60)}:{int((t_activo//60)%60):02d}" if nro_items and t_activo > 0 else "--"
        if nro_items and t_activo > 0:
            prom_seg = t_activo / nro_items
            prom = f"{int(prom_seg//60)}:{int(prom_seg%60):02d}"
        usuarios_stats.append({
            "usuario": usuario,
            "total": u_total,
            "finalizadas": u_fin,
            "en_curso": u_curso,
            "pausadas": u_pausa,
            "pendientes": u_pen,
            "vencidas": u_ven,
            "prorrogas": u_prr,
            "tiempo": f"{t_activo//3600:02d}:{(t_activo%3600)//60:02d}",
            "tiempo_pausado": f"{t_pausado//3600:02d}:{(t_pausado%3600)//60:02d}",
            "tiempo_inactividad": f"{t_muerto//3600:02d}:{(t_muerto%3600)//60:02d}",
            "nro_items": nro_items,
            "promedio": prom,
            "productividad": round((u_fin / u_total * 100) if u_total > 0 else 0, 1),
        })

    if not mostrar_todos:
        usuarios_stats = [u for u in usuarios_stats if u["total"] > 0]

    tm_total = sum(muertos.values())

    context = {
        "subareas": subareas,
        "empresas": Empresa.objects.filter(
            areas_funcionales__area__subareas__in=get_admin_subareas(request.user)
        ).distinct().order_by("nombre"),
        "empresa_id": empresa_id,
        "usuarios_select": User.objects.filter(
            subareas__subarea__in=subareas, subareas__activo=True, activo=True
        ).filter(
        Q(rol__nombre="Usuario") | Q(roles_adicionales__nombre="Usuario")
    ).distinct(),
        "total_actividades": total_actividades,
        "actividades_curso": actividades_curso,
        "actividades_finalizadas": actividades_finalizadas,
        "actividades_pausadas": actividades_pausadas,
        "actividades_pendientes": actividades_pendientes,
        "actividades_vencidas": vencidas_total,
        "vencidas_detalle": vencidas_detalle,
        "prorrogas_total": prorrogas_total,
        "tiempo_total": f"{horas_total:02d}:{mins_total:02d}",
        "tiempo_inactividad_total": f"{tm_total // 3600:02d}:{(tm_total % 3600) // 60:02d}",
        "productividad_media": productividad_media,
        "nro_total_items": nro_total,
        "promedio_item": promedio_item,
        "finalizadas_hoy": finalizadas_hoy,
        "usuarios_stats": usuarios_stats,
        "mostrar_todos": mostrar_todos,
        "subarea_id": int(subarea_id) if subarea_id else None,
        "user_id": int(user_id) if user_id else None,
        "fecha_desde": fecha_desde or "",
        "fecha_hasta": fecha_hasta or "",
    }
    cache.set(cache_key, context, 30)
    return render(request, "dashboard/dashboard_admin.html", context)


@login_required
@admin_required
def progreso(request):
    subareas = get_admin_subareas(request.user)

    empresa_id = request.GET.get("empresa_id")
    if empresa_id:
        try:
            empresa_id = int(empresa_id)
        except (ValueError, TypeError):
            empresa_id = None

    subarea_id = request.GET.get("subarea_id")
    if subarea_id:
        subareas = subareas.filter(id=subarea_id)

    user_id = request.GET.get("user_id")
    estado_filter = request.GET.get("estado", "")
    q = request.GET.get("q", "")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    from django.db.models import OuterRef, Subquery, Min
    from apps.gestion.models import RegistroTiempo

    asignaciones = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas, activo=True
    ).filter(user__activo=True).select_related(
        "user", "actividad", "actividad__tipo_actividad",
        "actividad__subarea__area",
        "planificacion_detalle__planificacion",
    ).annotate(
        primer_inicio=Subquery(
            RegistroTiempo.objects.filter(
                asignacion_id=OuterRef("pk"), evento="Inicio", activo=True
            ).order_by("fecha_hora").values("fecha_hora")[:1]
        ),
        ultimo_fin=Subquery(
            RegistroTiempo.objects.filter(
                asignacion_id=OuterRef("pk"), evento__in=["Finalizacion", "Traslado"], activo=True
            ).order_by("-fecha_hora").values("fecha_hora")[:1]
        )
    ).order_by("-fecha_asignacion")

    if user_id:
        asignaciones = asignaciones.filter(user_id=user_id)
    if estado_filter == "Vencidas":
        asignaciones = asignaciones.filter(
            planificacion_detalle__fecha_vencimiento__lt=timezone.now(),
            actividad__tipo_actividad__requiere_fecha_limite=True,
            estado__in=["Pendiente", "Pausada"]
        )
    elif estado_filter:
        asignaciones = asignaciones.filter(estado=estado_filter)
    if q:
        asignaciones = asignaciones.filter(
            Q(actividad__nombre__icontains=q) |
            Q(user__nombre__icontains=q) |
            Q(user__apellido__icontains=q)
        )
    if fecha_desde:
        asignaciones = asignaciones.filter(fecha_asignacion__date__gte=fecha_desde)
    if fecha_hasta:
        asignaciones = asignaciones.filter(fecha_asignacion__date__lte=fecha_hasta)

    paginator = Paginator(asignaciones, 20)
    page = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(page)
    except Exception:
        page_obj = paginator.page(1)

    usuarios_filtro = User.objects.filter(
        subareas__subarea__in=subareas, subareas__activo=True, activo=True
    ).filter(
        Q(rol__nombre="Usuario") | Q(roles_adicionales__nombre="Usuario")
    ).distinct()

    # Resumen
    total_qs = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas, activo=True
    ).filter(user__activo=True)
    if subarea_id:
        total_qs = total_qs.filter(actividad__subarea__in=subareas)
    resumen_total = total_qs.count()
    resumen_curso = total_qs.filter(estado="EnCurso").count()
    resumen_pausa = total_qs.filter(estado="Pausada").count()
    resumen_fin = total_qs.filter(estado="Finalizada").count()

    context = {
        "page_obj": page_obj,
        "asignaciones": page_obj.object_list,
        "subareas": subareas,
        "empresas": Empresa.objects.filter(
            areas_funcionales__area__subareas__in=get_admin_subareas(request.user)
        ).distinct().order_by("nombre"),
        "empresa_id": empresa_id,
        "usuarios_filtro": usuarios_filtro,
        "resumen_total": resumen_total,
        "resumen_curso": resumen_curso,
        "resumen_pausa": resumen_pausa,
        "resumen_fin": resumen_fin,
        "estado_filter": estado_filter,
        "subarea_id": int(subarea_id) if subarea_id else None,
        "user_id": int(user_id) if user_id else None,
        "q": q,
        "fecha_desde": fecha_desde or "",
        "fecha_hasta": fecha_hasta or "",
    }
    return render(request, "dashboard/progreso.html", context)


@login_required
@admin_required
def linea_tiempo(request):
    subareas = get_admin_subareas(request.user)
    hoy = timezone.localtime(timezone.now()).date()
    fecha = request.GET.get("fecha", hoy.isoformat())
    try:
        dia = date.fromisoformat(fecha)
    except (ValueError, TypeError):
        dia = hoy
    manana = dia + timedelta(days=1)

    user_filter = request.GET.get("user_id")
    if user_filter:
        try:
            user_filter = int(user_filter)
        except (ValueError, TypeError):
            user_filter = None

    subarea_filter = request.GET.get("subarea_id")
    if subarea_filter:
        try:
            subarea_filter = int(subarea_filter)
        except (ValueError, TypeError):
            subarea_filter = None

    usuarios_disponibles = User.objects.filter(
        id__in=UserSubArea.objects.filter(subarea__in=subareas, activo=True).values_list("user_id", flat=True),
        activo=True, is_active=True
    ).filter(
        Q(rol__nombre="Usuario") | Q(roles_adicionales__nombre="Usuario")
    )
    if subarea_filter:
        usuarios_disponibles = usuarios_disponibles.filter(subareas__subarea_id=subarea_filter, subareas__activo=True)
    usuarios_disponibles = usuarios_disponibles.order_by("nombre")

    subareas_disponibles = subareas.select_related("area")

    asignaciones = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas, activo=True
    ).filter(user__activo=True)
    if user_filter:
        asignaciones = asignaciones.filter(user_id=user_filter)
    if subarea_filter:
        asignaciones = asignaciones.filter(actividad__subarea_id=subarea_filter)

    asignaciones = asignaciones.select_related(
        "user", "actividad", "actividad__tipo_actividad",
        "actividad__subarea__area",
    )

    # Actividades con actividad en el dia o relevantes para la fecha
    items = []
    tz_local = timezone.get_current_timezone()

    for a in asignaciones:
        registros = list(a.registros.filter(
            activo=True, fecha_hora__date=dia
        ).order_by("fecha_hora"))

        tiene_registros_hoy = bool(registros)
        es_relevante = (
            tiene_registros_hoy or
            a.estado in ("EnCurso", "Pausada")
        )
        if not es_relevante:
            continue

        if not tiene_registros_hoy:
            if a.estado in ("EnCurso", "Pausada"):
                ultimo_reg = a.registros.filter(activo=True).order_by("-fecha_hora").first()
                if ultimo_reg:
                    inicio_local = ultimo_reg.fecha_hora.astimezone(tz_local)
                else:
                    inicio_naive = timezone.datetime(dia.year, dia.month, dia.day, 0, 0)
                    inicio_local = timezone.make_aware(inicio_naive)
                fin_local = timezone.localtime(timezone.now())
                segmentos = [{"tipo": "activo" if a.estado == "EnCurso" else "pausado", "inicio": inicio_local, "fin": fin_local}]
            else:
                continue
        else:
            # Construir segmentos desde los eventos
            segmentos = []
            inicio_dia_dt = timezone.make_aware(timezone.datetime(dia.year, dia.month, dia.day, 0, 0), tz_local)
            ultimo_antes = a.registros.filter(activo=True, fecha_hora__lt=inicio_dia_dt).order_by("-fecha_hora").first()
            if ultimo_antes and ultimo_antes.evento in ("Inicio", "Reanudacion"):
                inicio_seg = inicio_dia_dt
                tipo_actual = "activo"
            elif ultimo_antes and ultimo_antes.evento == "Pausa":
                inicio_seg = inicio_dia_dt
                tipo_actual = "pausado"
            else:
                inicio_seg = None
                tipo_actual = None
            ultima_fecha = None

            for r in registros:
                r_dt = r.fecha_hora.astimezone(tz_local)
                if r.evento in ("Inicio", "Reanudacion"):
                    if inicio_seg is not None and tipo_actual and (r_dt - inicio_seg).total_seconds() >= 60:
                        seg_tipo = "finz" if tipo_actual == "pausado" and a.estado == "Finalizada" else tipo_actual
                        segmentos.append({"tipo": seg_tipo, "inicio": inicio_seg, "fin": r_dt})
                    inicio_seg = r_dt
                    tipo_actual = "activo"
                elif r.evento == "Pausa":
                    if inicio_seg is not None and tipo_actual and (r_dt - inicio_seg).total_seconds() >= 60:
                        segmentos.append({"tipo": tipo_actual, "inicio": inicio_seg, "fin": r_dt})
                    inicio_seg = r_dt
                    tipo_actual = "pausado"
                elif r.evento in ("Finalizacion", "Traslado"):
                    if inicio_seg is not None and tipo_actual and (r_dt - inicio_seg).total_seconds() >= 60:
                        seg_tipo = "finz" if r.evento == "Finalizacion" and tipo_actual == "pausado" else tipo_actual
                        segmentos.append({"tipo": seg_tipo, "inicio": inicio_seg, "fin": r_dt})
                    inicio_seg = None
                    tipo_actual = None
                ultima_fecha = r_dt

            # Si quedo abierto (EnCurso o Pausada al final del dia)
            if inicio_seg is not None and tipo_actual:
                if a.estado in ("EnCurso", "Pausada"):
                    seg_fin = timezone.localtime(timezone.now())
                else:
                    siguiente_cierre = a.registros.filter(
                        activo=True, fecha_hora__gt=inicio_seg,
                        evento__in=["Reanudacion", "Finalizacion", "Traslado"]
                    ).order_by("fecha_hora").first()
                    if siguiente_cierre and siguiente_cierre.fecha_hora.date() == dia:
                        seg_fin = siguiente_cierre.fecha_hora.astimezone(tz_local)
                    else:
                        seg_fin = inicio_dia_dt + timedelta(days=1)
                if (seg_fin - inicio_seg).total_seconds() >= 60:
                    seg_tipo = "finz" if a.estado in ("Finalizada", "Cancelada") and tipo_actual == "pausado" else tipo_actual
                    segmentos.append({"tipo": seg_tipo, "inicio": inicio_seg, "fin": seg_fin})

            if not segmentos and tiene_registros_hoy:
                # Hay registros pero no se formaron segmentos (ej: solo evento Traslado)
                first_r = registros[0].fecha_hora.astimezone(tz_local)
                last_r = registros[-1].fecha_hora.astimezone(tz_local)
                if last_r <= first_r:
                    last_r = first_r + timedelta(hours=1)
                segmentos.append({"tipo": "activo", "inicio": first_r, "fin": last_r})
            elif not segmentos:
                continue

        def to_min(t):
            return t.hour * 60 + t.minute

        # Calcular posiciones para cada segmento
        seg_data = []
        for seg in segmentos:
            min_ini = max(to_min(seg["inicio"]), 0)
            min_fin = min(to_min(seg["fin"]), 24 * 60)
            dur = max(min_fin - min_ini, 3)
            seg_data.append({
                "tipo": seg["tipo"],
                "left": (min_ini / (24 * 60)) * 100,
                "width": (dur / (24 * 60)) * 100,
                "inicio": seg["inicio"],
                "fin": seg["fin"],
            })

        inicio_actividad = segmentos[0]["inicio"]
        fin_actividad = segmentos[-1]["fin"]

        items.append({
            "asignacion": a,
            "inicio": inicio_actividad,
            "fin": fin_actividad,
            "segmentos": seg_data,
            "estado": a.estado,
        })

    # Ordenar por usuario, luego por inicio
    items.sort(key=lambda x: (x["asignacion"].user.get_full_name(), x["inicio"]))

    # Agrupar por usuario para ver si se solapan
    from collections import defaultdict
    items_por_usuario = defaultdict(list)
    for item in items:
        items_por_usuario[item["asignacion"].user.pk].append(item)

    timeline_groups = []
    timeline_items = []
    tooltip_map = {}
    item_id = 1
    class_map = {
        "activo": "actv",
        "pausado": "paus",
        "pendiente": "pend",
        "finz": "finz",
    }
    for user_pk, user_items in items_por_usuario.items():
        user = user_items[0]["asignacion"].user

        # Determinar si las actividades del usuario se solapan en el tiempo
        solapan = False
        for i in range(len(user_items)):
            for j in range(i + 1, len(user_items)):
                ai, bi = user_items[i], user_items[j]
                if not (ai["fin"] <= bi["inicio"] or bi["fin"] <= ai["inicio"]):
                    solapan = True
                    break
            if solapan:
                break

        if solapan:
            # Apilado: una fila por actividad
            for item in user_items:
                asignacion = item["asignacion"]
                actividad_nombre = asignacion.actividad.nombre
                timeline_groups.append({
                    "id": asignacion.pk,
                    "content": f"{user.get_full_name()} — {actividad_nombre}",
                })
                for seg in item["segmentos"]:
                    if seg["fin"] <= seg["inicio"]:
                        seg["fin"] = seg["inicio"] + timedelta(minutes=1)
                    class_name = class_map.get(seg["tipo"], "")
                    tooltip_text = f"{actividad_nombre}|{seg['inicio'].strftime('%H:%M')}-{seg['fin'].strftime('%H:%M')}"
                    tooltip_map[item_id] = tooltip_text
                    timeline_items.append({
                        "id": item_id,
                        "group": asignacion.pk,
                        "content": "",
                        "start": seg["inicio"].strftime("%Y-%m-%dT%H:%M:%S"),
                        "end": seg["fin"].strftime("%Y-%m-%dT%H:%M:%S"),
                        "className": class_name,
                    })
                    item_id += 1
        else:
            # Secuencial: una sola fila por usuario
            timeline_groups.append({
                "id": user_pk,
                "content": f"{user.get_full_name()} ({len(user_items)})",
            })
            for item in user_items:
                actividad_nombre = item["asignacion"].actividad.nombre
                for seg in item["segmentos"]:
                    if seg["fin"] <= seg["inicio"]:
                        seg["fin"] = seg["inicio"] + timedelta(minutes=1)
                    class_name = class_map.get(seg["tipo"], "")
                    tooltip_text = f"{actividad_nombre}|{seg['inicio'].strftime('%H:%M')}-{seg['fin'].strftime('%H:%M')}"
                    tooltip_map[item_id] = tooltip_text
                    timeline_items.append({
                        "id": item_id,
                        "group": user_pk,
                        "content": "",
                        "start": seg["inicio"].strftime("%Y-%m-%dT%H:%M:%S"),
                        "end": seg["fin"].strftime("%Y-%m-%dT%H:%M:%S"),
                        "className": class_name,
                    })
                    item_id += 1

    dia_inicio = timezone.make_aware(timezone.datetime(dia.year, dia.month, dia.day, 0, 0), tz_local)
    dia_fin = dia_inicio + timedelta(days=1)
    window_start = dia_inicio + timedelta(hours=6)
    window_end = dia_inicio + timedelta(hours=20)

    ayer = dia - timedelta(days=1)
    maniana = dia + timedelta(days=1)

    # ============= PROYECTOS — GANTT =============
    try:
        from apps.proyectos.models import Proyecto
        _has_proyectos = True
    except ImportError:
        _has_proyectos = False

    proyecto_filter = None
    proyectos_disponibles = []
    proyecto_groups = []
    proyecto_items = []
    gantt_tips = {}
    gantt_window = {"min": (hoy - timedelta(days=7)).isoformat(), "max": (hoy + timedelta(days=30)).isoformat()}

    if _has_proyectos:
        proyecto_filter = request.GET.get("proyecto_id")
        if proyecto_filter:
            try:
                proyecto_filter = int(proyecto_filter)
            except (ValueError, TypeError):
                proyecto_filter = None

        if request.user.rol.nombre == "Master":
            proyectos_qs = Proyecto.objects.filter(activo=True)
            if subarea_filter:
                proyectos_qs = proyectos_qs.filter(subareas__id=subarea_filter)
        elif request.user.rol.nombre == "Admin" and request.user.maneja_proyectos:
            proyectos_qs = Proyecto.objects.filter(activo=True)
            if subarea_filter:
                proyectos_qs = proyectos_qs.filter(subareas__id=subarea_filter)
        elif request.user.maneja_proyectos:
            proyectos_qs = Proyecto.objects.filter(
                activo=True,
                membresias__user=request.user,
                membresias__activo=True,
            )
        else:
            proyectos_qs = Proyecto.objects.none()

        if proyecto_filter:
            proyectos_qs = proyectos_qs.filter(pk=proyecto_filter)

        proyectos_disponibles = proyectos_qs.distinct()

        color_class = {
            "planificado": "gantt-plan",
            "activo": "gantt-activo",
            "finalizado": "gantt-fin",
        }

        gantt_dates = []
        for p in proyectos_disponibles:
            sprints_qs = p.sprints.filter(activo=True).order_by("numero")
            if not sprints_qs.exists():
                continue
            total_tareas = p.tareas.filter(activo=True).count()
            done_tareas = p.tareas.filter(activo=True, estado="finalizada").count()
            proyecto_groups.append({
                "id": f"prj-{p.pk}",
                "content": f"{p.codigo} {p.nombre[:30]}  ({total_tareas - done_tareas}/{total_tareas} pend)",
            })
            for sp in sprints_qs:
                if not sp.fecha_inicio or not sp.fecha_fin:
                    continue
                gantt_dates.extend([sp.fecha_inicio, sp.fecha_fin])
                t_total = sp.tareas.filter(activo=True).count()
                t_done = sp.tareas.filter(activo=True, estado="finalizada").count()
                pct = int(t_done / t_total * 100) if t_total else 0
                cls = color_class.get(sp.estado, "gantt-plan")
                label = f"S{sp.numero}: {sp.nombre[:25]}{' ✓' if pct == 100 else ''}"
                item_id = f"sp-{sp.pk}"
                proyecto_items.append({
                    "id": item_id,
                    "group": f"prj-{p.pk}",
                    "content": label,
                    "start": sp.fecha_inicio.isoformat(),
                    "end": sp.fecha_fin.isoformat(),
                    "className": cls,
                    "title": f"{sp.nombre}|Estado: {sp.get_estado_display()}|Tareas: {t_done}/{t_total} ({pct}%)|{sp.fecha_inicio.strftime('%d/%m/%Y')} → {sp.fecha_fin.strftime('%d/%m/%Y')}",
                })
                gantt_tips[item_id] = f"{sp.nombre}|{sp.get_estado_display()}|{t_done}/{t_total} tareas ({pct}%)"

        if gantt_dates:
            gantt_min = min(gantt_dates) - timedelta(days=3)
            gantt_max = max(max(gantt_dates), hoy) + timedelta(days=3)
            gantt_window = {
                "min": gantt_min.isoformat(),
                "max": gantt_max.isoformat(),
            }

    return render(request, "dashboard/linea_tiempo.html", {
        "timeline_groups": timeline_groups,
        "timeline_items": timeline_items,
        "tooltip_map": tooltip_map,
        "timeline_window": {
            "start": window_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "end": window_end.strftime("%Y-%m-%dT%H:%M:%S"),
            "min": dia_inicio.strftime("%Y-%m-%dT%H:%M:%S"),
            "max": dia_fin.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "dia": dia,
        "ayer": ayer,
        "maniana": maniana,
        "fecha_str": dia.isoformat(),
        "usuarios_disponibles": usuarios_disponibles,
        "user_filter": user_filter,
        "subareas_disponibles": subareas_disponibles,
        "subarea_filter": subarea_filter,
        # -- Proyectos Gantt --
        "proyectos_disponibles": proyectos_disponibles,
        "proyecto_filter": proyecto_filter,
        "proyecto_groups": proyecto_groups,
        "proyecto_items": proyecto_items,
        "gantt_tips": gantt_tips,
        "gantt_window": gantt_window,
        "hay_proyectos": bool(proyecto_items),
    })


@login_required
@admin_required
def tiempo_inactividad(request):
    from apps.gestion.models import TiempoInactividad
    from django.core.paginator import Paginator
    user_id = request.GET.get("user_id")
    subarea_id = request.GET.get("subarea_id")

    subareas = get_admin_subareas(request.user)
    usuarios_subarea = User.objects.filter(
        subareas__subarea__in=subareas, subareas__activo=True, activo=True
    ).distinct()

    if subarea_id:
        usuarios_subarea = usuarios_subarea.filter(subareas__subarea_id=subarea_id)

    from apps.gestion.models import AsignacionActividad, TiempoInactividad
    # Cerrar TMs abiertos para usuarios que ahora tienen EnCurso (todos los usuarios)
    for tm in TiempoInactividad.objects.filter(activo=True, fin__isnull=True).select_related('user'):
        if AsignacionActividad.objects.filter(user=tm.user, activo=True, estado="EnCurso").exists():
            ahora = timezone.now()
            if tm.inicio:
                tm.duracion_segundos += int((ahora - tm.inicio).total_seconds())
            tm.fin = ahora
            tm.activo = False
            tm.save()
    # Crear TMs solo para usuarios en subareas que no tengan EnCurso ni TM abierto
    for u in usuarios_subarea if not user_id else usuarios_subarea.filter(pk=user_id):
        tiene_curso = AsignacionActividad.objects.filter(user=u, activo=True, estado="EnCurso").exists()
        if not tiene_curso and not TiempoInactividad.objects.filter(user=u, activo=True, fin__isnull=True).exists():
            ultimo = RegistroTiempo.objects.filter(
                asignacion__user=u, activo=True,
                evento__in=["Finalizacion", "Pausa", "Inicio", "Reanudacion"]
            ).order_by("-fecha_hora").first()
            inicio = ultimo.fecha_hora if ultimo else timezone.now()
            TiempoInactividad.objects.create(user=u, fecha=inicio.date(), inicio=inicio)

    tiempos = TiempoInactividad.objects.filter(
        user__in=usuarios_subarea
    ).select_related("user").order_by("-fecha", "-inicio")
    if user_id:
        tiempos = tiempos.filter(user_id=user_id)

    total_seg = sum(
        t.duracion_segundos + (int((timezone.now() - t.inicio).total_seconds()) if t.activo and not t.fin and t.inicio else 0)
        for t in tiempos
    )
    horas_t = int(total_seg // 3600)
    mins_t = int((total_seg % 3600) // 60)
    seg_t = int(total_seg % 60)

    paginator = Paginator(tiempos, 15)
    page = request.GET.get("page", 1)
    tiempos_page = paginator.get_page(page)

    tiempos_list = []
    for t in tiempos_page:
        secs = t.duracion_segundos
        if not t.fin and t.inicio:
            secs += int((timezone.now() - t.inicio).total_seconds())
        dias = secs // 86400
        horas = (secs % 86400) // 3600
        mins = (secs % 3600) // 60
        if dias > 0:
            duracion = f"{dias}d {horas}h {mins}m"
        elif horas > 0:
            duracion = f"{horas}h {mins}m"
        else:
            duracion = f"{mins}m" if mins > 0 else "< 1m"
        estado = "abierto"
        if t.fin:
            dias_diff = (t.fin.date() - t.inicio.date()).days if t.inicio else 0
            estado = f"cerrado ({dias_diff}d)" if dias_diff > 0 else "cerrado"
        elif t.inicio and (timezone.now().date() - t.inicio.date()).days > 0:
            estado = "abierto (multi-dia)"
        tiempos_list.append({"objeto": t, "duracion": duracion, "estado": estado})

    usuarios = usuarios_subarea.order_by("nombre")

    return render(request, "dashboard/tiempo_inactividad.html", {
        "tiempos_list": tiempos_list,
        "page_obj": tiempos_page,
        "usuarios": usuarios,
        "subareas": subareas,
        "total_tiempo": f"{horas_t:02d}:{mins_t:02d}:{seg_t:02d}",
        "user_id": int(user_id) if user_id else None,
        "subarea_id": int(subarea_id) if subarea_id else None,
    })
