from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from ..models import Proyecto, MiembroProyecto, WorkflowConfig, RegistroAvance
from ..decorators import miembro_requerido, ROLES_ADMIN, ROLES_EDICION
from apps.accounts.models import User
from apps.estructura.models import SubArea, Area, Empresa


def _get_subareas(user):
    if user.rol.nombre == "Master":
        return SubArea.objects.filter(activo=True)
    return SubArea.objects.filter(usuarios__user=user, activo=True)


@login_required
def proyecto_list(request):
    from apps.accounts.models import Empresa
    # Master ve TODOS los proyectos activos. Admin filtra por subareas.
    if request.user.rol.nombre == "Master":
        proyectos = Proyecto.objects.filter(activo=True)
    elif request.user.rol.nombre == "Admin":
        subareas = _get_subareas(request.user)
        proyectos = Proyecto.objects.filter(subareas__in=subareas, activo=True).distinct()
    else:
        proyectos = Proyecto.objects.filter(
            membresias__user=request.user, membresias__activo=True, activo=True
        ).distinct()

    # Filtros
    q = request.GET.get("q", "").strip()
    estado_filtro = request.GET.get("estado", "")
    empresa_filtro = request.GET.get("empresa_id")
    area_filtro = request.GET.get("area_id")
    subarea_filtro = request.GET.get("subarea_id")
    if area_filtro:
        try:
            area_filtro = int(area_filtro)
            proyectos = proyectos.filter(subareas__area_id=area_filtro).distinct()
        except (ValueError, TypeError):
            area_filtro = None
    if subarea_filtro:
        try:
            subarea_filtro = int(subarea_filtro)
            proyectos = proyectos.filter(subareas__id=subarea_filtro).distinct()
        except (ValueError, TypeError):
            subarea_filtro = None
    if empresa_filtro:
        try:
            empresa_filtro = int(empresa_filtro)
            proyectos = proyectos.filter(subareas__empresas_permitidas__empresa_id=empresa_filtro).distinct()
        except (ValueError, TypeError):
            empresa_filtro = None
    if q:
        from django.db.models import Q
        proyectos = proyectos.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
    if estado_filtro and estado_filtro in ["activo","pausado","finalizado","cancelado"]:
        proyectos = proyectos.filter(estado=estado_filtro)

    # KPIs dinamicos (despues de filtros)
    from apps.proyectos.models import Tarea, Incidencia, Sprint, MiembroProyecto
    proyecto_ids = list(proyectos.values_list("pk", flat=True)[:200])
    total = len(proyecto_ids) if proyecto_ids else 0
    activos = proyectos.filter(estado="activo").count()
    pausados = proyectos.filter(estado="pausado").count()
    finalizados = proyectos.filter(estado="finalizado").count()
    cancelados = proyectos.filter(estado="cancelado").count()

    total_tareas = Tarea.objects.filter(proyecto_id__in=proyecto_ids, activo=True).count() if proyecto_ids else 0
    tareas_pendientes = Tarea.objects.filter(proyecto_id__in=proyecto_ids, activo=True, estado="pendiente").count() if proyecto_ids else 0
    tareas_curso = Tarea.objects.filter(proyecto_id__in=proyecto_ids, activo=True, estado__in=["en_curso","pausada","bloqueada"]).count() if proyecto_ids else 0
    tareas_fin = Tarea.objects.filter(proyecto_id__in=proyecto_ids, activo=True, estado="finalizada").count() if proyecto_ids else 0
    tareas_rev = Tarea.objects.filter(proyecto_id__in=proyecto_ids, activo=True, estado="revision").count() if proyecto_ids else 0
    total_sprints = Sprint.objects.filter(proyecto_id__in=proyecto_ids, activo=True).count() if proyecto_ids else 0
    sprints_activos_count = Sprint.objects.filter(proyecto_id__in=proyecto_ids, activo=True, estado="activo").count() if proyecto_ids else 0
    inc_abiertas = Incidencia.objects.filter(proyecto_id__in=proyecto_ids, activo=True, estado__in=["abierta","triaged","en_progreso"]).count() if proyecto_ids else 0
    miembros_total = MiembroProyecto.objects.filter(proyecto_id__in=proyecto_ids, activo=True).count() if proyecto_ids else 0
    avance_prom = round(sum(p.avance for p in proyectos[:200]) / max(total, 1))
    velocidades = []
    for sp in Sprint.objects.filter(proyecto_id__in=proyecto_ids, activo=True, estado="finalizado").select_related("proyecto"):
        velocidades.append(sp.velocidad)
    velocidad_prom = round(sum(velocidades) / len(velocidades), 1) if velocidades else 0

    proyectos = proyectos.prefetch_related(
        "subareas__area", "subareas__empresas_permitidas__empresa",
        "sprints__historias__tareas__asignado_a",
        "sprints__tareas__asignado_a",
        "tareas", "membresias",
    ).select_related("manager", "empresa").order_by("-fecha_creacion")

    paginator = Paginator(proyectos, 15)
    page = request.GET.get("page", 1)
    proyectos_page = paginator.get_page(page)
    empresas_filtro = Empresa.objects.filter(activo=True).order_by("nombre")
    subareas_disponibles = _get_subareas(request.user).select_related("area").order_by("area__nombre", "nombre")
    if area_filtro:
        subareas_disponibles = subareas_disponibles.filter(area_id=area_filtro)
    areas_disponibles = Area.objects.filter(subareas__in=_get_subareas(request.user)).distinct().order_by("nombre")

    # Miembros por proyecto para tabla de equipo (agrupado por usuario)
    from collections import defaultdict
    miembros_raw = MiembroProyecto.objects.filter(
        proyecto_id__in=proyecto_ids, activo=True
    ).select_related("user", "proyecto").order_by("user__nombre")
    # Agrupar por usuario
    equipo_stats = defaultdict(lambda: {"proyectos": [], "roles": set(), "tareas_total": 0, "tareas_fin": 0, "tareas_pend": 0, "tareas_rev": 0, "tareas_curso": 0})
    for m in miembros_raw:
        u = m.user
        equipo_stats[u.pk]["nombre"] = u.get_full_name()
        equipo_stats[u.pk]["proyectos"].append(m.proyecto.codigo)
        equipo_stats[u.pk]["roles"].add(m.get_rol_display())
    # Contar tareas por usuario
    if proyecto_ids:
        from django.db.models import Count, Q
        tareas_por_user = Tarea.objects.filter(
            proyecto_id__in=proyecto_ids, activo=True, asignado_a__isnull=False
        ).values("asignado_a_id").annotate(
            total=Count("id"),
            fin=Count("id", filter=Q(estado="finalizada")),
            pend=Count("id", filter=Q(estado="pendiente")),
            rev=Count("id", filter=Q(estado="revision")),
            curso=Count("id", filter=Q(estado__in=["en_curso","pausada","bloqueada"])),
        )
        for t in tareas_por_user:
            uid = t["asignado_a_id"]
            if uid in equipo_stats:
                equipo_stats[uid]["tareas_total"] = t["total"]
                equipo_stats[uid]["tareas_fin"] = t["fin"]
                equipo_stats[uid]["tareas_pend"] = t["pend"]
                equipo_stats[uid]["tareas_rev"] = t["rev"]
                equipo_stats[uid]["tareas_curso"] = t["curso"]

    equipo_data = []
    for uid, data in sorted(equipo_stats.items(), key=lambda x: x[1]["nombre"]):
        equipo_data.append({
            "nombre": data["nombre"],
            "proyectos": len(data["proyectos"]),
            "roles": ", ".join(sorted(data["roles"])),
            "tareas_total": data["tareas_total"],
            "tareas_fin": data["tareas_fin"],
            "tareas_pend": data["tareas_pend"],
            "tareas_rev": data["tareas_rev"],
            "tareas_curso": data["tareas_curso"],
        })

    return render(request, "proyectos/proyecto_list.html", {
        "proyectos": proyectos_page,
        "page_obj": proyectos_page,
        "total_proyectos": total, "activos": activos, "pausados": pausados, "finalizados": finalizados, "cancelados": cancelados,
        "empresas_filtro": empresas_filtro,
        "estado_filtro": estado_filtro, "empresa_filtro": empresa_filtro, "area_filtro": area_filtro, "subarea_filtro": subarea_filtro, "q": q,
        "total_tareas": total_tareas, "tareas_pendientes": tareas_pendientes, "tareas_curso": tareas_curso,
        "tareas_fin": tareas_fin, "tareas_rev": tareas_rev,
        "total_sprints": total_sprints, "sprints_activos_count": sprints_activos_count,
        "inc_abiertas": inc_abiertas, "miembros_total": miembros_total,
        "avance_prom": avance_prom, "velocidad_prom": velocidad_prom,
        "equipo_data": equipo_data,
        "subareas_disponibles": subareas_disponibles,
        "areas_disponibles": areas_disponibles,
    })


@login_required
def proyecto_create(request):
    # Solo Master y Admin pueden crear proyectos
    if request.user.rol.nombre not in ["Master", "Admin"]:
        messages.error(request, "No tienes permisos para crear proyectos.")
        return redirect("proyectos:proyecto_list")
    subareas = _get_subareas(request.user)
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        objetivo = request.POST.get("objetivo", "").strip()
        subarea_ids = request.POST.getlist("subareas")
        manager_id = request.POST.get("manager")
        empresa_id = request.POST.get("empresa") or None
        fecha_inicio = request.POST.get("fecha_inicio") or None
        fecha_fin = request.POST.get("fecha_fin_estimada") or None

        if not nombre or not manager_id:
            messages.error(request, "Nombre y manager son obligatorios.")
            return redirect("proyectos:proyecto_create")

        if len(nombre) < 3:
            messages.error(request, "El nombre debe tener al menos 3 caracteres.")
            return redirect("proyectos:proyecto_create")

        if not subarea_ids or len(subarea_ids) == 0:
            messages.error(request, "Debes seleccionar al menos una subarea.")
            return redirect("proyectos:proyecto_create")

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            messages.error(request, "Fecha de inicio no puede ser posterior a la fecha fin.")
            return redirect("proyectos:proyecto_create")

        from django.utils import timezone
        if fecha_inicio and fecha_inicio < str(timezone.now().date()):
            messages.error(request, "La fecha de inicio no puede ser anterior a hoy.")
            return redirect("proyectos:proyecto_create")

        manager = get_object_or_404(User, pk=manager_id, activo=True)

        import time
        tmp = hex(int(time.time() * 1e6))[2:10]  # 8 chars hex unico
        proyecto = Proyecto(
            nombre=nombre,
            descripcion=descripcion,
            objetivo=objetivo,
            manager=manager,
            empresa_id=empresa_id,
            codigo=tmp,  # temporal unico, reemplazado abajo
            fecha_inicio=fecha_inicio,
            fecha_fin_estimada=fecha_fin,
        )
        proyecto.full_clean()
        proyecto.save()
        proyecto.codigo = f"PRJ-{proyecto.pk:04d}"
        proyecto.save(update_fields=["codigo"])
        if subarea_ids:
            proyecto.subareas.set(subarea_ids)

        MiembroProyecto.objects.update_or_create(proyecto=proyecto, user=manager, defaults={"rol": "lider", "activo": True})
        from ..models import RegistroAvance
        RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
            descripcion=f"Proyecto creado por {request.user.get_full_name()}", user=request.user)
        messages.success(request, f"Proyecto '{proyecto.codigo}' creado.")
        return redirect("proyectos:proyecto_detail", pk=proyecto.pk)

    usuarios = User.objects.filter(activo=True, is_active=True).exclude(rol__nombre="Master")
    from apps.accounts.models import Empresa
    from apps.estructura.models import Area
    from collections import defaultdict
    empresas = Empresa.objects.filter(activo=True).order_by("nombre")
    areas = Area.objects.filter(activo=True).order_by("nombre")
    # Agrupar subareas por area para el template
    subareas_por_area = defaultdict(list)
    for s in subareas:
        subareas_por_area[s.area_id].append(s)
    from django.utils import timezone
    return render(request, "proyectos/proyecto_form.html", {
        "subareas": subareas, "usuarios": usuarios, "empresas": empresas,
        "areas": areas, "subareas_por_area": dict(subareas_por_area),
        "today": timezone.now().date()
    })


@login_required
@miembro_requerido()
def proyecto_detail(request, pk):
    proyecto = request.proyecto
    tareas = proyecto.tareas.filter(activo=True)
    incidencias = proyecto.incidencias.filter(activo=True)
    from ..models import Tarea
    from django.utils import timezone
    ahora = timezone.now()

    # Métricas avanzadas
    sprints_hist = proyecto.sprints.filter(activo=True, estado="finalizado").order_by("numero")
    velocidades = [s.velocidad for s in sprints_hist]
    # Aging: tareas pendientes sin movimiento en 3+ días
    limite_aging = ahora - timezone.timedelta(days=3)
    tareas_aging = tareas.filter(estado__in=["pendiente","en_curso","pausada"], fecha_creacion__lt=limite_aging).count()

    # Lead time / Cycle time
    from datetime import timedelta
    tareas_fin_qs = proyecto.tareas.filter(activo=True, estado="finalizada")
    lead_times = []
    for t in tareas_fin_qs[:50]:
        dias = (t.fecha_update.date() - t.fecha_creacion.date()).days
        if dias >= 0:
            lead_times.append(dias)
    lead_time_prom = round(sum(lead_times) / len(lead_times), 1) if lead_times else 0

    # Sprint velocity table
    sprints_all = proyecto.sprints.filter(activo=True).order_by("numero")
    sprint_table = []
    for s in sprints_all:
        t_total = s.tareas.filter(activo=True).count()
        t_done = s.tareas.filter(activo=True, estado="finalizada").count()
        sprint_table.append({
            "numero": s.numero,
            "nombre": s.nombre,
            "estado": s.estado,
            "comprometido": s.puntos_comprometidos,
            "completado": s.velocidad,
            "tareas": f"{t_done}/{t_total}",
            "inicio": s.fecha_inicio,
            "fin": s.fecha_fin,
        })

    context = {
        "proyecto": proyecto,
        "tareas_pend": tareas.filter(estado="pendiente").count(),
        "tareas_curso": tareas.filter(estado__in=["en_curso", "pausada", "bloqueada"]).count(),
        "tareas_rev": tareas.filter(estado="revision").count(),
        "tareas_fin": tareas.filter(estado="finalizada").count(),
        "inc_abiertas": incidencias.filter(estado__in=["abierta", "triaged", "en_progreso"]).count(),
        "sprints_activos": proyecto.sprints.filter(activo=True, estado="activo").count(),
        "sprints_finalizados": sprints_hist.count(),
        "velocidad_prom": round(sum(velocidades) / len(velocidades), 1) if velocidades else 0,
        "tareas_aging": tareas_aging,
        "avances": proyecto.avances.order_by("-fecha")[:200],
        # CFD / distribucion
        "cfd_labels": ["Pendientes", "En Curso", "Revision", "Finalizadas"],
        "cfd_data": [
            tareas.filter(estado="pendiente").count(),
            tareas.filter(estado__in=["en_curso","pausada","bloqueada"]).count(),
            tareas.filter(estado="revision").count(),
            tareas.filter(estado="finalizada").count(),
        ],
        # Velocidad historica
        "vel_labels": [f"S{s.numero}" for s in sprints_hist],
        "vel_data": velocidades,
        "vel_comp": [s.puntos_comprometidos for s in sprints_hist],
        # Reportes
        "lead_time_prom": lead_time_prom,
        "sprint_table": sprint_table,
    }
    return render(request, "proyectos/proyecto_detail.html", context)


@login_required
@miembro_requerido(ROLES_ADMIN)
def proyecto_edit(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    subareas = _get_subareas(request.user)
    original_subarea_ids = set(proyecto.subareas.values_list("pk", flat=True))
    original_estado = proyecto.estado
    original_fin_estimada = proyecto.fecha_fin_estimada
    if request.method == "POST":
        proyecto.nombre = request.POST.get("nombre", proyecto.nombre)
        proyecto.descripcion = request.POST.get("descripcion", proyecto.descripcion)
        proyecto.objetivo = request.POST.get("objetivo", proyecto.objetivo)
        nuevo_estado = request.POST.get("estado", proyecto.estado)
        proyecto.estado = nuevo_estado
        manager_id = request.POST.get("manager")
        if manager_id:
            proyecto.manager = get_object_or_404(User, pk=manager_id, activo=True)
        empresa_id = request.POST.get("empresa")
        proyecto.empresa_id = empresa_id or None
        proyecto.fecha_inicio = request.POST.get("fecha_inicio") or None
        nueva_fin = request.POST.get("fecha_fin_estimada") or None
        proyecto.fecha_fin_estimada = nueva_fin
        fi = proyecto.fecha_inicio
        ff = proyecto.fecha_fin_estimada
        if fi and ff and fi > ff:
            messages.error(request, "Fecha de inicio no puede ser posterior a la fecha fin.")
            return redirect("proyectos:proyecto_edit", pk=proyecto.pk)

        # Validar: no quitar subareas asignadas originalmente
        posted_subarea_ids = set()
        try:
            posted_subarea_ids = set(int(x) for x in request.POST.getlist("subareas"))
        except (ValueError, TypeError):
            messages.error(request, "Datos invalidos en la seleccion de subareas.")
            return redirect("proyectos:proyecto_edit", pk=proyecto.pk)
        missing = original_subarea_ids - posted_subarea_ids
        if missing:
            nombres = SubArea.objects.filter(pk__in=missing).values_list("nombre", flat=True)
            messages.error(request, f"No puedes quitar las subareas asignadas inicialmente: {', '.join(nombres)}. Solo puedes a\u00f1adir nuevas.")
            return redirect("proyectos:proyecto_edit", pk=proyecto.pk)

        proyecto.full_clean()
        proyecto.save()
        proyecto.subareas.set(posted_subarea_ids)

        # Audit trail: cambio de fecha fin estimada
        if original_fin_estimada != proyecto.fecha_fin_estimada:
            RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                descripcion=f"Fecha fin estimada cambiada de {original_fin_estimada or 'sin definir'} a {proyecto.fecha_fin_estimada or 'sin definir'} por {request.user.get_full_name()}",
                user=request.user)

        # Cascade: cambio de estado
        if nuevo_estado != original_estado:
            from ..models import Tarea, Incidencia, Sprint, HistoriaUsuario
            RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                descripcion=f"Estado cambiado de '{dict(Proyecto.ESTADOS).get(original_estado, original_estado)}' a '{dict(Proyecto.ESTADOS).get(nuevo_estado, nuevo_estado)}' por {request.user.get_full_name()}",
                user=request.user)

            if nuevo_estado == "cancelado":
                sprint_ids = list(proyecto.sprints.filter(activo=True).exclude(estado="finalizado").values_list("pk", flat=True))
                Sprint.objects.filter(pk__in=sprint_ids).update(estado="cancelado")
                RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                    descripcion=f"{len(sprint_ids)} sprint(s) pasados a cancelado por cancelacion del proyecto",
                    user=request.user)

                tarea_ids = list(proyecto.tareas.filter(activo=True).exclude(estado__in=["finalizada","cancelada"]).values_list("pk", flat=True))
                Tarea.objects.filter(pk__in=tarea_ids).update(estado="cancelada", activo=False)
                RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                    descripcion=f"{len(tarea_ids)} tarea(s) pasadas a cancelada por cancelacion del proyecto",
                    user=request.user)

                inc_ids = list(proyecto.incidencias.filter(activo=True).exclude(estado__in=["resuelta","cerrada","duplicada"]).values_list("pk", flat=True))
                Incidencia.objects.filter(pk__in=inc_ids).update(estado="cerrada", activo=False)
                RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                    descripcion=f"{len(inc_ids)} incidencia(s) cerradas por cancelacion del proyecto",
                    user=request.user)

                historia_ids = list(proyecto.historias.filter(activo=True).exclude(estado="done").values_list("pk", flat=True))
                HistoriaUsuario.objects.filter(pk__in=historia_ids).update(activo=False)
                RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                    descripcion=f"{len(historia_ids)} historia(s) archivadas por cancelacion del proyecto",
                    user=request.user)

            elif nuevo_estado == "pausado":
                sprint_ids = list(proyecto.sprints.filter(activo=True, estado="activo").values_list("pk", flat=True))
                Sprint.objects.filter(pk__in=sprint_ids).update(estado="planificado")
                RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                    descripcion=f"{len(sprint_ids)} sprint(s) activo(s) puestos en planificacion por pausa del proyecto. El progreso y tiempo trabajado se conservan para cuando se reanude.",
                    user=request.user)

            elif nuevo_estado == "activo" and original_estado == "pausado":
                RegistroAvance.objects.create(proyecto=proyecto, tipo="proyecto_reanudado",
                    descripcion=f"Proyecto reanudado por {request.user.get_full_name()}. Los sprints, tareas e incidencias anteriores mantienen su estado.",
                    user=request.user)

            elif nuevo_estado == "finalizado" and original_estado != "finalizado":
                from django.utils import timezone
                # Finalizar sprints activos/planificados
                sids = list(proyecto.sprints.filter(activo=True).exclude(estado="finalizado").values_list("pk", flat=True))
                Sprint.objects.filter(pk__in=sids).update(estado="finalizado")
                # Finalizar tareas pendientes
                tids = list(proyecto.tareas.filter(activo=True).exclude(estado__in=["finalizada","cancelada"]).values_list("pk", flat=True))
                Tarea.objects.filter(pk__in=tids).update(estado="finalizada")
                # Cerrar incidencias abiertas
                iids = list(proyecto.incidencias.filter(activo=True).exclude(estado__in=["resuelta","cerrada","duplicada"]).values_list("pk", flat=True))
                Incidencia.objects.filter(pk__in=iids).update(estado="cerrada")
                proyecto.fecha_fin_real = timezone.now().date()
                proyecto.save(update_fields=["fecha_fin_real"])
                RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                    descripcion=f"Proyecto finalizado por {request.user.get_full_name()}. {len(sids)} sprint(s), {len(tids)} tarea(s) y {len(iids)} incidencia(s) cerradas.",
                    user=request.user)

        messages.success(request, "Proyecto actualizado.")
        return redirect("proyectos:proyecto_detail", pk=proyecto.pk)
    usuarios = User.objects.filter(activo=True, is_active=True).exclude(rol__nombre="Master")
    from apps.accounts.models import Empresa
    from apps.estructura.models import Area
    from collections import defaultdict
    empresas = Empresa.objects.filter(activo=True).order_by("nombre")
    areas = Area.objects.filter(activo=True).order_by("nombre")
    subareas_por_area = defaultdict(list)
    for s in subareas:
        subareas_por_area[s.area_id].append(s)
    return render(request, "proyectos/proyecto_form.html", {
        "proyecto": proyecto, "subareas": subareas, "usuarios": usuarios,
        "empresas": empresas, "areas": areas, "subareas_por_area": dict(subareas_por_area), "editando": True
    })


@login_required
@miembro_requerido(ROLES_ADMIN)
def proyecto_equipo(request, pk):
    return redirect("proyectos:proyecto_workflow", pk=pk)


@miembro_requerido()
def proyecto_gantt(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    proyecto = request.proyecto
    sprints = proyecto.sprints.filter(activo=True).order_by("numero")
    grupos = []
    items = []
    hoy = timezone.now().date()

    for sp in sprints:
        gid = f"sprint-{sp.pk}"
        tareas_sp = sp.tareas.filter(activo=True).count()
        done_sp = sp.tareas.filter(activo=True, estado="finalizada").count()
        pct_sp = int(done_sp / tareas_sp * 100) if tareas_sp else 0
        clase_sp = "gantt-activo" if sp.estado == "activo" else ("gantt-fin" if sp.estado == "finalizado" else "gantt-plan")
        sp_start = (sp.fecha_inicio.isoformat() if sp.fecha_inicio else None)
        sp_end = (sp.fecha_fin.isoformat() if sp.fecha_fin else None)

        grupos.append({
            "id": gid,
            "content": f"Sprint {sp.numero}: {sp.nombre}",
        })

        # Barra del sprint
        if sp_start and sp_end:
            items.append({
                "id": f"sprint-{sp.pk}-bar",
                "group": gid,
                "content": f"S{sp.numero} {sp.nombre[:20]}",
                "start": sp_start,
                "end": sp_end,
                "className": clase_sp,
                "title": "",
                "pct": pct_sp,
                "tooltip": f"Sprint {sp.numero}: {sp.nombre}|{sp_start} → {sp_end}|{done_sp}/{tareas_sp} tareas ({pct_sp}%)|Estado: {sp.get_estado_display()}",
            })

        # Historias del sprint como sub-grupos
        for h in sp.historias.filter(activo=True).prefetch_related("tareas__asignado_a"):
            hgid = f"historia-{h.pk}"
            tareas_h = [t for t in h.tareas.all() if t.activo]
            done_h = sum(1 for t in tareas_h if t.estado == "finalizada")
            total_h = len(tareas_h)
            pct_h = int(done_h / total_h * 100) if total_h else 0
            clase_h = "gantt-fin" if h.estado == "done" else ("gantt-activo" if h.estado == "en_progreso" else "gantt-plan")
            h_start = sp_start or h.fecha_creacion.date().isoformat()
            # Responsable = primer asignado de cualquier tarea
            responsables = sorted(set(
                t.asignado_a.get_full_name() for t in tareas_h if t.asignado_a
            ))
            responsable = ", ".join(responsables) if responsables else "Sin asignar"

            grupos.append({
                "id": hgid,
                "content": f"  {h.codigo} {h.titulo[:25]}",
            })
            items.append({
                "id": f"historia-{h.pk}-bar",
                "group": hgid,
                "content": f"{h.codigo} {h.titulo[:22]}",
                "start": h_start,
                "end": sp_end,
                "className": clase_h,
                "title": "",
                "pct": pct_h,
                "tooltip": f"{h.codigo}: {h.titulo}|{h_start} → {sp_end or '?'}|{done_h}/{total_h} tareas ({pct_h}%)|Prioridad: {h.get_prioridad_display()}|Responsable: {responsable}",
            })

    # Fechas para navegacion rapida
    if sp_start:
        gantt_min = min(
            sp.fecha_inicio for sp in sprints if sp.fecha_inicio
        ) - timedelta(days=1)
        gantt_max = max(
            sp.fecha_fin for sp in sprints if sp.fecha_fin
        ) + timedelta(days=1)
    else:
        gantt_min = hoy - timedelta(days=7)
        gantt_max = hoy + timedelta(days=30)

    return render(request, "proyectos/proyecto_gantt.html", {
        "proyecto": proyecto,
        "grupos": grupos,
        "items": items,
        "tareas_total": proyecto.tareas.filter(activo=True).count(),
        "gantt_min": gantt_min.isoformat(),
        "gantt_max": gantt_max.isoformat(),
        "hoy": hoy.isoformat(),
        "semana_inicio": (hoy - timedelta(days=hoy.weekday())).isoformat(),
        "semana_fin": (hoy + timedelta(days=6 - hoy.weekday())).isoformat(),
        "mes_inicio": hoy.replace(day=1).isoformat(),
        "mes_fin": (hoy.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
    })


@miembro_requerido()
def proyecto_estructura(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprints = proyecto.sprints.filter(activo=True).order_by("numero")
    tareas_sin = proyecto.tareas.filter(activo=True, historia__isnull=True, sprint__isnull=True).select_related("asignado_a")
    return render(request, "proyectos/proyecto_estructura.html", {
        "proyecto": proyecto,
        "sprints": sprints,
        "tareas_sin": tareas_sin,
    })


@login_required
@miembro_requerido(ROLES_ADMIN)
def proyecto_toggle_activo(request, pk):
    proyecto = request.proyecto
    if request.method == "POST":
        proyecto.activo = not proyecto.activo
        proyecto.save()
        estado = "activado" if proyecto.activo else "desactivado"
        messages.success(request, f"Proyecto {proyecto.codigo} {estado}.")
    return redirect("proyectos:proyecto_list")


@miembro_requerido(ROLES_ADMIN)
def proyecto_workflow(request, pk):
    from django.db.models import Q
    proyecto = request.proyecto

    ROLES_POR_PRESET = {
        "simple": ["lider", "ejecutor"],
        "revision": ["lider", "responsable", "ejecutor", "revisor", "aprobador"],
        "completo": ["lider", "responsable", "ejecutor", "revisor", "aprobador", "observador"],
    }
    presets = {
        "simple": {
            "tarea": [("pendiente","en_curso"),("en_curso","finalizada"),("en_curso","cancelada")],
            "historia": [("backlog","sprint_backlog"),("sprint_backlog","en_progreso"),("en_progreso","done")],
            "incidencia": [("abierta","en_progreso"),("en_progreso","resuelta"),("resuelta","cerrada")],
        },
        "revision": {
            "tarea": [("pendiente","en_curso"),("en_curso","finalizada"),("finalizada","revision"),("en_curso","cancelada"),("revision","finalizada"),("revision","pendiente")],
            "historia": [("backlog","sprint_backlog"),("sprint_backlog","en_progreso"),("en_progreso","revision"),("revision","done"),("revision","en_progreso")],
            "incidencia": [("abierta","en_progreso"),("abierta","cerrada"),("en_progreso","resuelta"),("resuelta","cerrada"),("cerrada","abierta")],
        },
    }

    if request.method == "POST":
        accion = request.POST.get("accion")
        if accion == "actualizar":
            preset = request.POST.get("preset")
            if preset not in presets and preset != "completo":
                messages.error(request, "Plantilla invalida.")
                return redirect("proyectos:proyecto_workflow", pk=proyecto.pk)

            roles_necesarios = ROLES_POR_PRESET.get(preset, ROLES_POR_PRESET["completo"])
            miembros_activos = MiembroProyecto.objects.filter(proyecto=proyecto, activo=True)
            roles_actuales_set = set(miembros_activos.values_list("rol", flat=True))
            roles_sobran = [r for r in roles_actuales_set if r not in roles_necesarios]

            if roles_sobran:
                sobrantes = miembros_activos.filter(rol__in=roles_sobran)
                nombres = ", ".join(m.user.get_full_name() for m in sobrantes)
                messages.error(request, f"Hay miembros con roles que no aplican a '{preset}': {nombres}. Quitalos antes de aplicar la plantilla.")
                return redirect(f"{reverse('proyectos:proyecto_workflow', args=[proyecto.pk])}?preset={preset}")

            # Aplicar preset a todas las entidades
            if preset in presets:
                for ent in ["tarea", "historia", "incidencia"]:
                    if ent in presets[preset]:
                        WorkflowConfig.objects.filter(proyecto=proyecto, entidad=ent).delete()
                        for origen, destino in presets[preset][ent]:
                            WorkflowConfig.objects.get_or_create(proyecto=proyecto, entidad=ent, estado_origen=origen, estado_destino=destino, defaults={"activo": True})
            else:
                WorkflowConfig.objects.filter(proyecto=proyecto).delete()

            # Auto-agregar roles faltantes si el manager los cubre
            for rol in roles_necesarios:
                if rol not in roles_actuales_set and proyecto.manager:
                    MiembroProyecto.objects.get_or_create(proyecto=proyecto, user=proyecto.manager, defaults={"rol": rol, "activo": True})

            messages.success(request, f"Flujo '{preset}' aplicado.")
            return redirect("proyectos:proyecto_workflow", pk=proyecto.pk)

        elif accion == "agregar_equipo":
            user_id = request.POST.get("user_id")
            rol = request.POST.get("rol", "ejecutor")
            if user_id:
                MiembroProyecto.objects.update_or_create(
                    proyecto=proyecto, user_id=user_id,
                    defaults={"rol": rol, "activo": True}
                )
                messages.success(request, "Miembro agregado al equipo.")
        elif accion == "remover_equipo":
            user_id = request.POST.get("user_id")
            if user_id:
                MiembroProyecto.objects.filter(proyecto=proyecto, user_id=user_id).update(activo=False)
                messages.success(request, "Miembro removido del equipo.")

    from ..models import HARDCODED_TAREA, HARDCODED_HISTORIA, HARDCODED_INCIDENCIA, _get_transiciones as gtrans

    workflows_all = WorkflowConfig.objects.filter(proyecto=proyecto, activo=True)
    flujos = {}
    for ent in ["tarea", "historia", "incidencia"]:
        flujos[ent] = gtrans(proyecto, ent)

    miembros = MiembroProyecto.objects.filter(proyecto=proyecto, activo=True).select_related("user")
    if not miembros.exists() and proyecto.manager:
        MiembroProyecto.objects.get_or_create(proyecto=proyecto, user=proyecto.manager, defaults={"rol": "lider"})
        miembros = MiembroProyecto.objects.filter(proyecto=proyecto, activo=True).select_related("user")

    # Detectar preset activo real
    def detectar_preset(trans, ent):
        """Detecta preset activo por heuristica. Funciona correctamente para los 3 presets existentes (simple, revision, completo)."""
        if not workflows_all.filter(entidad=ent).exists():
            return "completo"
        has_rev = any("revision" in [k, *v] for k, vv in trans.items() for v in vv)
        has_bloq = any("bloqueada" in [k, *v] for k, vv in trans.items() for v in vv)
        if has_bloq: return "completo"
        if has_rev: return "revision"
        has_fin = any("finalizada" == v for vv in trans.values() for v in vv)
        return "simple" if has_fin else "completo"

    preset_activo = detectar_preset(flujos["tarea"], "tarea")

    # Preset en preview (GET param)
    preset_preview = request.GET.get("preset")
    if preset_preview and preset_preview in presets:
        flujos_preview = {}
        for ent, transitions in presets[preset_preview].items():
            d = {}
            for o, d2 in transitions:
                d.setdefault(o, []).append(d2)
            flujos_preview[ent] = d
        flujos = flujos_preview
        preset_activo = preset_preview
    elif preset_preview == "completo":
        for ent in ["tarea", "historia", "incidencia"]:
            flujos[ent] = {"tarea": HARDCODED_TAREA, "historia": HARDCODED_HISTORIA, "incidencia": HARDCODED_INCIDENCIA}[ent]
        preset_activo = "completo"

    roles_actuales = set(miembros.values_list("rol", flat=True))
    roles_necesarios = ROLES_POR_PRESET.get(preset_activo, ROLES_POR_PRESET["completo"])
    roles_faltantes = [r for r in roles_necesarios if r not in roles_actuales]
    roles_sobran = [r for r in roles_actuales if r not in roles_necesarios]
    miembros_sobran = [m for m in miembros if m.rol in roles_sobran]

    from apps.accounts.models import User
    usuarios = User.objects.filter(activo=True, is_active=True).filter(
        Q(rol__nombre__in=["Usuario", "Admin"]) | Q(roles_adicionales__nombre="Usuario")
    ).distinct()

    return render(request, "proyectos/proyecto_workflow.html", {
        "proyecto": proyecto,
        "flujos": flujos,
        "miembros": miembros,
        "miembros_sobran": miembros_sobran,
        "usuarios": usuarios,
        "roles_faltantes": roles_faltantes,
        "roles_sobran": roles_sobran,
        "preset_activo": preset_activo,
        "mostrar_actualizar": bool(preset_preview),
    })
