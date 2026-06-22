from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, Sprint
from ..decorators import miembro_requerido, ROLES_EDICION


@miembro_requerido()
def sprint_list(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprints = proyecto.sprints.filter(activo=True).prefetch_related("historias", "tareas")
    from django.utils import timezone
    return render(request, "proyectos/sprint_list.html", {
        "proyecto": proyecto, "sprints": sprints, "today": timezone.now().date()
    })


@miembro_requerido(ROLES_EDICION)
def sprint_create(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if not nombre:
            messages.error(request, "El nombre es obligatorio.")
            return redirect("proyectos:sprint_list", pk=proyecto.pk)
        fi = request.POST.get("fecha_inicio") or None
        ff = request.POST.get("fecha_fin") or None
        if fi and ff and fi > ff:
            messages.error(request, "Fecha de inicio no puede ser posterior a la fecha fin.")
            return redirect("proyectos:sprint_list", pk=proyecto.pk)
        from django.utils import timezone
        if fi and fi < str(timezone.now().date()):
            messages.error(request, "La fecha de inicio no puede ser anterior a hoy.")
            return redirect("proyectos:sprint_list", pk=proyecto.pk)
        # Advertencia si fechas sprint fuera del rango del proyecto
        if fi and proyecto.fecha_inicio and fi < str(proyecto.fecha_inicio):
            messages.warning(request, f"El sprint empieza antes que el proyecto ({proyecto.fecha_inicio}).")
        if ff and proyecto.fecha_fin_estimada and ff > str(proyecto.fecha_fin_estimada):
            messages.warning(request, f"El sprint termina despues del proyecto ({proyecto.fecha_fin_estimada}).")
        from django.db.models import Max
        ultimo = Sprint.objects.filter(proyecto=proyecto).aggregate(m=Max("numero"))["m"] or 0
        sprint = Sprint(
            proyecto=proyecto,
            nombre=nombre,
            objetivo=request.POST.get("objetivo", ""),
            numero=ultimo + 1,
            fecha_inicio=fi,
            fecha_fin=ff,
        )
        sprint.full_clean()
        sprint.save()
        historias_ids = request.POST.getlist("historias")
        if historias_ids:
            proyecto.historias.filter(pk__in=historias_ids).update(sprint=sprint, estado="sprint_backlog")
        from ..models import RegistroAvance
        RegistroAvance.objects.create(proyecto=proyecto, tipo="sprint_creado",
            descripcion=f"Sprint {sprint.numero} creado por {request.user.get_full_name()}", user=request.user, referencia_id=sprint.pk)
        messages.success(request, f"Sprint {sprint.numero} creado.")
        return redirect("proyectos:sprint_list", pk=proyecto.pk)
    historias = proyecto.historias.filter(activo=True, estado="backlog")
    return render(request, "proyectos/sprint_form.html", {"proyecto": proyecto, "historias": historias})


@miembro_requerido(ROLES_EDICION)
def sprint_edit(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    if sprint.estado != "planificado":
        messages.error(request, "Solo se pueden editar sprints planificados.")
        return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if not nombre:
            messages.error(request, "El nombre es obligatorio.")
            return redirect("proyectos:sprint_list", pk=proyecto.pk)
        sprint.nombre = nombre
        sprint.objetivo = request.POST.get("objetivo", "")
        fi = request.POST.get("fecha_inicio") or None
        ff = request.POST.get("fecha_fin") or None
        if fi and ff and fi > ff:
            messages.error(request, "Fecha de inicio no puede ser posterior a la fecha fin.")
            return redirect("proyectos:sprint_edit", pk=proyecto.pk, spk=sprint.pk)
        # Advertencia si fechas sprint fuera del rango del proyecto
        if fi and proyecto.fecha_inicio and fi < str(proyecto.fecha_inicio):
            messages.warning(request, f"El sprint empieza antes que el proyecto ({proyecto.fecha_inicio}).")
        if ff and proyecto.fecha_fin_estimada and ff > str(proyecto.fecha_fin_estimada):
            messages.warning(request, f"El sprint termina despues del proyecto ({proyecto.fecha_fin_estimada}).")
        sprint.fecha_inicio = fi
        sprint.fecha_fin = ff
        sprint.full_clean()
        sprint.save()
        # Actualizar historias: desvincular las que ya no están, vincular nuevas
        nuevas_ids = [int(x) for x in request.POST.getlist("historias")]
        sprint.historias.filter(activo=True).update(sprint=None, estado="backlog")
        proyecto.historias.filter(pk__in=nuevas_ids).update(sprint=sprint, estado="sprint_backlog")
        messages.success(request, f"Sprint {sprint.numero} actualizado.")
        return redirect("proyectos:sprint_list", pk=proyecto.pk)
    historias_del_proyecto = proyecto.historias.filter(activo=True, sprint__isnull=True).exclude(estado="done")
    historias_del_sprint = sprint.historias.filter(activo=True)
    historias_ids_sprint = set(historias_del_sprint.values_list("pk", flat=True))
    return render(request, "proyectos/sprint_form.html", {
        "proyecto": proyecto, "sprint": sprint, "editando": True,
        "historias": historias_del_proyecto,
        "historias_ids_sprint": historias_ids_sprint,
        "historias_sprint": historias_del_sprint,
    })


@miembro_requerido()
def sprint_board(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    tareas = sprint.tareas.filter(activo=True).select_related("asignado_a", "historia")
    from django.utils import timezone
    return render(request, "proyectos/sprint_board.html", {
        "proyecto": proyecto, "sprint": sprint, "tareas": tareas,
        "pendientes": tareas.filter(estado="pendiente"),
        "en_curso": tareas.filter(estado__in=["en_curso", "pausada", "bloqueada"]),
        "finalizadas": tareas.filter(estado="finalizada"),
        "today": timezone.now().date(),
    })


@miembro_requerido()
def sprint_burndown(request, pk, spk):
    proyecto = request.proyecto
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    from django.utils import timezone
    from datetime import timedelta
    hoy = timezone.now().date()
    dias_labels = []
    ideal = []
    real = []
    pts = sprint.puntos_comprometidos
    if sprint.fecha_inicio and sprint.fecha_fin:
        total_dias = max((sprint.fecha_fin - sprint.fecha_inicio).days + 1, 1)
        dias_labels = [(sprint.fecha_inicio + timedelta(days=i)).strftime("%d/%m") for i in range(total_dias)]
        paso = pts / max(total_dias - 1, 1) if total_dias > 1 else 0
        ideal = [max(0, round(pts - paso * i, 1)) for i in range(total_dias)]
        # Datos reales: puntos quemados por dia segun tareas finalizadas
        tareas_fin = sprint.tareas.filter(activo=True, estado="finalizada").select_related("historia")
        pts_por_dia = {}
        historias_por_dia = {}
        for t in tareas_fin:
            dia = t.fecha_update.date()
            if t.historia:
                if dia not in historias_por_dia:
                    historias_por_dia[dia] = set()
                # Solo contar una vez por historia por dia (evita sobre-conteo)
                if t.historia_id not in historias_por_dia[dia]:
                    historias_por_dia[dia].add(t.historia_id)
                    pts_por_dia[dia] = pts_por_dia.get(dia, 0) + t.historia.puntos_historia
            else:
                # Tarea sin historia cuenta 1 punto
                pts_por_dia[dia] = pts_por_dia.get(dia, 0) + 1
        acum = pts
        for d in [sprint.fecha_inicio + timedelta(days=i) for i in range(total_dias)]:
            if d in pts_por_dia:
                acum -= pts_por_dia[d]
            real.append(max(0, acum))
    return render(request, "proyectos/sprint_burndown.html", {
        "proyecto": proyecto, "sprint": sprint,
        "dias": dias_labels, "ideal": ideal, "real": real, "pts_inicio": pts,
    })


@miembro_requerido(ROLES_EDICION)
def sprint_finalizar(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    if sprint.estado != "activo":
        messages.error(request, "Solo se pueden finalizar sprints activos.")
        return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
    if request.method == "POST":
        from ..models import RegistroAvance
        sprint.estado = "finalizado"
        sprint.full_clean()
        sprint.save()
        tareas_no_fin = sprint.tareas.filter(activo=True).exclude(estado__in=["finalizada","cancelada"])
        tareas_no_fin.update(estado="cancelada", activo=False)
        for h in sprint.historias.filter(activo=True):
            if h.estado == "done":
                RegistroAvance.objects.create(proyecto=proyecto, tipo="historia_completada",
                    descripcion=f"Historia {h.codigo} completada en Sprint {sprint.numero}", user=request.user, referencia_id=h.pk)
            else:
                h.estado = "backlog"
                h.sprint = None
                h.save()
        RegistroAvance.objects.create(proyecto=proyecto, tipo="sprint_finalizado",
            descripcion=f"Sprint {sprint.numero} finalizado. Velocidad: {sprint.velocidad} pts.", user=request.user, referencia_id=sprint.pk)
        messages.success(request, f"Sprint {sprint.numero} finalizado. Velocidad: {sprint.velocidad} pts.")
        return redirect("proyectos:sprint_list", pk=proyecto.pk)
    return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)


@miembro_requerido(ROLES_EDICION)
def sprint_iniciar(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    if sprint.estado != "planificado":
        messages.error(request, "Solo se pueden iniciar sprints planificados.")
        return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
    if request.method == "POST":
        from django.utils import timezone
        sprint.estado = "activo"
        sprint.fecha_inicio = sprint.fecha_inicio or timezone.now().date()
        sprint.save()
        from ..signals import crear_asignacion_desde_tarea
        from apps.gestion.views import _notificar_usuario
        activadas = 0
        sin_asignar = 0
        ya_activas = 0
        for t in sprint.tareas.filter(activo=True):
            if t.asignacion:
                ya_activas += 1
                continue
            if not t.asignado_a:
                sin_asignar += 1
                continue
            asig = crear_asignacion_desde_tarea(t)
            if asig:
                _notificar_usuario(t.asignado_a.pk, "nueva_asignacion", {"actividad": t.titulo})
                activadas += 1
        total = sprint.tareas.filter(activo=True).count()
        msg = f"Sprint {sprint.numero} iniciado. {activadas} tareas activadas"
        if ya_activas: msg += f", {ya_activas} ya estaban activas"
        if sin_asignar: msg += f". {sin_asignar} tareas sin asignar no se activaron (asigna un ejecutor)"
        from ..models import RegistroAvance
        RegistroAvance.objects.create(proyecto=proyecto, tipo="sprint_iniciado",
            descripcion=msg, user=request.user, referencia_id=sprint.pk)
        # Notificar a todos los miembros del proyecto
        for m in proyecto.membresias.filter(activo=True):
            _notificar_usuario(m.user_id, "sprint_iniciado", {
                "sprint": sprint.nombre, "proyecto": proyecto.codigo
            })
        messages.success(request, msg)
        return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
    return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)


@miembro_requerido(ROLES_EDICION)
def sprint_cancelar(request, pk, spk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprint = get_object_or_404(Sprint, pk=spk, proyecto=proyecto)
    if sprint.estado not in ["planificado", "activo"]:
        messages.error(request, "Solo se pueden cancelar sprints planificados o activos.")
        return redirect("proyectos:sprint_board", pk=proyecto.pk, spk=sprint.pk)
    if request.method == "POST":
        sprint.estado = "cancelado"
        sprint.save()
        sprint.tareas.filter(activo=True).exclude(estado__in=["finalizada","cancelada"]).update(estado="cancelada", activo=False)
        from ..models import RegistroAvance
        RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
            descripcion=f"Sprint {sprint.numero} cancelado por {request.user.get_full_name()}", user=request.user, referencia_id=sprint.pk)
        messages.success(request, f"Sprint {sprint.numero} cancelado. Tareas devueltas al backlog.")
    return redirect("proyectos:sprint_list", pk=proyecto.pk)
