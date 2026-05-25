from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q, Avg, F
from collections import OrderedDict
from django.utils import timezone
from datetime import date, timedelta
from apps.gestion.models import AsignacionActividad, RegistroTiempo
from apps.estructura.models import UserSubArea, SubArea
from apps.accounts.models import User


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
    subarea_id = request.GET.get("subarea_id")
    if subarea_id:
        subareas = subareas.filter(id=subarea_id)

    user_id = request.GET.get("user_id")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    usuarios = User.objects.filter(
        subareas__subarea__in=subareas, subareas__activo=True, activo=True
    ).exclude(rol__nombre__in=["Master", "Admin"]).distinct()

    if user_id:
        usuarios = usuarios.filter(id=user_id)

    asignaciones = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas, activo=True
    )

    if user_id:
        asignaciones = asignaciones.filter(user_id=user_id)

    if fecha_desde:
        asignaciones = asignaciones.filter(fecha_asignacion__date__gte=fecha_desde)
    if fecha_hasta:
        asignaciones = asignaciones.filter(fecha_asignacion__date__lte=fecha_hasta)

    registros_base = RegistroTiempo.objects.filter(
        asignacion__actividad__subarea__in=subareas, activo=True
    )
    if user_id:
        registros_base = registros_base.filter(asignacion__user_id=user_id)
    if fecha_desde:
        registros_base = registros_base.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        registros_base = registros_base.filter(fecha_hora__date__lte=fecha_hasta)

    total_actividades = asignaciones.count()
    actividades_curso = asignaciones.filter(estado="EnCurso").count()
    actividades_finalizadas = asignaciones.filter(estado="Finalizada").count()
    actividades_pausadas = asignaciones.filter(estado="Pausada").count()
    actividades_pendientes = asignaciones.filter(estado="Pendiente").count()
    prorrogas_total = asignaciones.filter(prorroga_count__gt=0).count()

    # Tiempo total trabajado desde RegistroTiempo
    tiempo_total_seg = sum(a.tiempo_efectivo() for a in asignaciones)
    horas_total = int(tiempo_total_seg // 3600)
    mins_total = int((tiempo_total_seg % 3600) // 60)

    # Tiempo promedio por actividad: nro de items finalizados (calculo en Python, es CharField)
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

    usuarios_stats = []
    for usuario in usuarios:
        user_asignaciones = asignaciones.filter(user=usuario)
        user_finalizadas = user_asignaciones.filter(estado="Finalizada").count()
        user_curso = user_asignaciones.filter(estado="EnCurso").count()
        user_pausadas = user_asignaciones.filter(estado="Pausada").count()
        user_pendientes = user_asignaciones.filter(estado="Pendiente").count()
        user_prorrogas = user_asignaciones.filter(prorroga_count__gt=0).count()
        total_tiempo = sum(a.tiempo_efectivo() for a in user_asignaciones)
        total_pausado = sum(a.tiempo_pausado() for a in user_asignaciones)
        horas = int(total_tiempo // 3600)
        minutos = int((total_tiempo % 3600) // 60)
        horas_p = int(total_pausado // 3600)
        mins_p = int((total_pausado % 3600) // 60)
        # Nro de items finalizados por este usuario
        nro_vals = registros_base.filter(
            asignacion__user=usuario, evento="Finalizacion", nro_actividad__isnull=False
        ).values_list("nro_actividad", flat=True)
        nro_user = sum(int(v) for v in nro_vals if v.strip().isdigit())
        if nro_user and total_tiempo > 0:
            prom_user_seg = total_tiempo / nro_user
            prom = f"{int(prom_user_seg//60)}:{int(prom_user_seg%60):02d}"
        else:
            prom = "--"
        total_user = user_asignaciones.count()
        usuarios_stats.append({
            "usuario": usuario,
            "total": total_user,
            "finalizadas": user_finalizadas,
            "en_curso": user_curso,
            "pausadas": user_pausadas,
            "pendientes": user_pendientes,
            "prorrogas": user_prorrogas,
            "tiempo": f"{horas:02d}:{minutos:02d}",
            "tiempo_pausado": f"{horas_p:02d}:{mins_p:02d}",
            "nro_items": nro_user,
            "promedio": prom,
            "productividad": round((user_finalizadas / total_user * 100) if total_user > 0 else 0, 1),
        })

    context = {
        "subareas": subareas,
        "usuarios_select": User.objects.filter(
            subareas__subarea__in=subareas, subareas__activo=True, activo=True
        ).exclude(rol__nombre__in=["Master", "Admin"]).distinct(),
        "total_actividades": total_actividades,
        "actividades_curso": actividades_curso,
        "actividades_finalizadas": actividades_finalizadas,
        "actividades_pausadas": actividades_pausadas,
        "actividades_pendientes": actividades_pendientes,
        "prorrogas_total": prorrogas_total,
        "tiempo_total": f"{horas_total:02d}:{mins_total:02d}",
        "productividad_media": productividad_media,
        "nro_total_items": nro_total,
        "promedio_item": promedio_item,
        "finalizadas_hoy": finalizadas_hoy,
        "usuarios_stats": usuarios_stats,
        "subarea_id": int(subarea_id) if subarea_id else None,
        "user_id": int(user_id) if user_id else None,
        "fecha_desde": fecha_desde or "",
        "fecha_hasta": fecha_hasta or "",
    }
    return render(request, "dashboard/dashboard_admin.html", context)


@login_required
@admin_required
def progreso(request):
    subareas = get_admin_subareas(request.user)
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
    ).select_related(
        "user", "actividad", "actividad__tipo_actividad",
        "actividad__subarea__area__empresa",
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
    if estado_filter:
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
    ).exclude(rol__nombre__in=["Master", "Admin"]).distinct()

    # Resumen
    total_qs = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas, activo=True
    )
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

    asignaciones = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas, activo=True
    ).select_related(
        "user", "actividad", "actividad__tipo_actividad",
        "actividad__subarea__area__empresa",
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
            inicio_seg = None
            tipo_actual = None
            ultima_fecha = None

            for r in registros:
                r_dt = r.fecha_hora.astimezone(tz_local)
                if r.evento in ("Inicio", "Reanudacion"):
                    if inicio_seg is not None and tipo_actual:
                        segmentos.append({"tipo": tipo_actual, "inicio": inicio_seg, "fin": r_dt})
                    inicio_seg = r_dt
                    tipo_actual = "activo"
                elif r.evento == "Pausa":
                    if inicio_seg is not None and tipo_actual:
                        segmentos.append({"tipo": tipo_actual, "inicio": inicio_seg, "fin": r_dt})
                    inicio_seg = r_dt
                    tipo_actual = "pausado"
                elif r.evento in ("Finalizacion", "Traslado"):
                    if inicio_seg is not None and tipo_actual:
                        segmentos.append({"tipo": tipo_actual, "inicio": inicio_seg, "fin": r_dt})
                    inicio_seg = None
                    tipo_actual = None
                ultima_fecha = r_dt

            # Si quedo abierto (EnCurso o Pausada al final del dia)
            if inicio_seg is not None and tipo_actual:
                now_local = timezone.localtime(timezone.now())
                seg_fin = now_local if a.estado in ("EnCurso", "Pausada") else inicio_seg + timedelta(hours=1)
                segmentos.append({"tipo": tipo_actual, "inicio": inicio_seg, "fin": seg_fin})

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

    # Agrupar por usuario
    from collections import OrderedDict
    grupos = OrderedDict()
    for item in items:
        u = item["asignacion"].user
        key = u.pk
        if key not in grupos:
            grupos[key] = {"user": u, "items": []}
        grupos[key]["items"].append(item)

    timeline_groups = []
    timeline_items = []
    tooltip_map = {}
    item_id = 1
    class_map = {
        "activo": "actv",
        "pausado": "paus",
        "pendiente": "pend",
    }
    for g in grupos.values():
        user = g["user"]
        timeline_groups.append({
            "id": user.pk,
            "content": f"{user.get_full_name()} ({len(g['items'])})",
        })
        for item in g["items"]:
            actividad_nombre = item["asignacion"].actividad.nombre
            for seg in item["segmentos"]:
                if seg["fin"] <= seg["inicio"]:
                    seg["fin"] = seg["inicio"] + timedelta(minutes=1)
                class_name = class_map.get(seg["tipo"], "")
                tooltip_text = f"{actividad_nombre}|{seg['inicio'].strftime('%H:%M')}-{seg['fin'].strftime('%H:%M')}"
                tooltip_map[item_id] = tooltip_text
                timeline_items.append({
                    "id": item_id,
                    "group": user.pk,
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
    })
