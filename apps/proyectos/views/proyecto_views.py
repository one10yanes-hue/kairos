from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Proyecto, MiembroProyecto
from ..decorators import miembro_requerido, ROLES_ADMIN, ROLES_EDICION
from apps.accounts.models import User
from apps.estructura.models import SubArea


def _get_subareas(user):
    if user.rol.nombre == "Master":
        return SubArea.objects.filter(activo=True)
    return SubArea.objects.filter(usuarios__user=user, activo=True)


@login_required
def proyecto_list(request):
    subareas = _get_subareas(request.user)
    # Mostrar proyectos donde el usuario es miembro o es Admin/Master
    if request.user.rol.nombre in ["Master", "Admin"]:
        proyectos = Proyecto.objects.filter(subareas__in=subareas, activo=True).distinct()
    else:
        proyectos = Proyecto.objects.filter(
            membresias__user=request.user, membresias__activo=True, activo=True
        ).distinct()
    proyectos = proyectos.prefetch_related("subareas__area", "subareas")
    return render(request, "proyectos/proyecto_list.html", {"proyectos": proyectos})


@login_required
def proyecto_create(request):
    subareas = _get_subareas(request.user)
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        objetivo = request.POST.get("objetivo", "").strip()
        subarea_ids = request.POST.getlist("subareas")
        manager_id = request.POST.get("manager")
        fecha_inicio = request.POST.get("fecha_inicio") or None
        fecha_fin = request.POST.get("fecha_fin_estimada") or None

        if not nombre or not manager_id:
            messages.error(request, "Nombre y manager son obligatorios.")
            return redirect("proyectos:proyecto_create")

        manager = get_object_or_404(User, pk=manager_id, activo=True)

        proyecto = Proyecto.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            objetivo=objetivo,
            manager=manager,
            fecha_inicio=fecha_inicio,
            fecha_fin_estimada=fecha_fin,
        )
        proyecto.codigo = f"PRJ-{proyecto.pk:04d}"
        proyecto.save()
        if subarea_ids:
            proyecto.subareas.set(subarea_ids)

        MiembroProyecto.objects.get_or_create(proyecto=proyecto, user=manager, defaults={"rol": "lider"})
        messages.success(request, f"Proyecto '{proyecto.codigo}' creado.")
        return redirect("proyectos:proyecto_detail", pk=proyecto.pk)

    usuarios = User.objects.filter(activo=True, is_active=True).exclude(rol__nombre="Master")
    return render(request, "proyectos/proyecto_form.html", {"subareas": subareas, "usuarios": usuarios})


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

    context = {
        "proyecto": proyecto,
        "tareas_pend": tareas.filter(estado="pendiente").count(),
        "tareas_curso": tareas.filter(estado__in=["en_curso", "pausada"]).count(),
        "tareas_fin": tareas.filter(estado="finalizada").count(),
        "inc_abiertas": incidencias.filter(estado__in=["abierta", "triaged", "en_progreso"]).count(),
        "sprints_activos": proyecto.sprints.filter(activo=True, estado="activo").count(),
        "sprints_finalizados": sprints_hist.count(),
        "velocidad_prom": round(sum(velocidades) / len(velocidades), 1) if velocidades else 0,
        "tareas_aging": tareas_aging,
        "avances": proyecto.avances.order_by("-fecha")[:5],
        # CFD: contar tareas por estado para el grafico
        "cfd_backlog": tareas.filter(estado="pendiente").count(),
        "cfd_progreso": tareas.filter(estado__in=["en_curso","pausada"]).count(),
        "cfd_revision": tareas.filter(estado="revision").count(),
        "cfd_done": tareas.filter(estado="finalizada").count(),
    }
    return render(request, "proyectos/proyecto_detail.html", context)


@login_required
@miembro_requerido(ROLES_ADMIN)
def proyecto_edit(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    subareas = _get_subareas(request.user)
    if request.method == "POST":
        proyecto.nombre = request.POST.get("nombre", proyecto.nombre)
        proyecto.descripcion = request.POST.get("descripcion", proyecto.descripcion)
        proyecto.objetivo = request.POST.get("objetivo", proyecto.objetivo)
        proyecto.estado = request.POST.get("estado", proyecto.estado)
        manager_id = request.POST.get("manager")
        if manager_id:
            proyecto.manager = get_object_or_404(User, pk=manager_id, activo=True)
        proyecto.fecha_inicio = request.POST.get("fecha_inicio") or None
        proyecto.fecha_fin_estimada = request.POST.get("fecha_fin_estimada") or None
        proyecto.save()
        messages.success(request, "Proyecto actualizado.")
        return redirect("proyectos:proyecto_detail", pk=proyecto.pk)
    usuarios = User.objects.filter(activo=True, is_active=True).exclude(rol__nombre="Master")
    return render(request, "proyectos/proyecto_form.html", {
        "proyecto": proyecto, "subareas": subareas, "usuarios": usuarios, "editando": True
    })


@login_required
@miembro_requerido(ROLES_ADMIN)
def proyecto_equipo(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    miembros = MiembroProyecto.objects.filter(proyecto=proyecto, activo=True).select_related("user")
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        rol = request.POST.get("rol", "ejecutor")
        accion = request.POST.get("accion")
        if accion == "agregar" and user_id:
            MiembroProyecto.objects.update_or_create(
                proyecto=proyecto, user_id=user_id,
                defaults={"rol": rol, "activo": True}
            )
            messages.success(request, "Miembro agregado.")
        elif accion == "remover" and user_id:
            MiembroProyecto.objects.filter(proyecto=proyecto, user_id=user_id).update(activo=False)
            messages.success(request, "Miembro removido.")
        return redirect("proyectos:proyecto_equipo", pk=proyecto.pk)
    from django.db.models import Q
    usuarios = User.objects.filter(activo=True, is_active=True).filter(
        Q(rol__nombre__in=["Usuario", "Admin"]) | Q(roles_adicionales__nombre="Usuario")
    ).distinct()
    return render(request, "proyectos/proyecto_equipo.html", {
        "proyecto": proyecto, "miembros": miembros, "usuarios": usuarios
    })


@login_required
def proyecto_gantt(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    sprints = proyecto.sprints.filter(activo=True).order_by("numero")
    items = []
    for sp in sprints:
        items.append({
            "id": f"sprint-{sp.pk}",
            "content": f"Sprint {sp.numero}: {sp.nombre}",
            "start": sp.fecha_inicio.isoformat() if sp.fecha_inicio else None,
            "end": sp.fecha_fin.isoformat() if sp.fecha_fin else None,
            "group": "sprints",
            "className": "bg-primary text-white",
        })
        for t in sp.tareas.filter(activo=True).select_related("asignado_a"):
            if t.fecha_creacion:
                items.append({
                    "id": f"tarea-{t.pk}",
                    "content": t.titulo[:40],
                    "start": t.fecha_creacion.date().isoformat(),
                    "end": (t.fecha_update.date() if t.estado == "finalizada" else None),
                    "group": f"sprint-{sp.pk}",
                })
    return render(request, "proyectos/proyecto_gantt.html", {
        "proyecto": proyecto, "items": items
    })
