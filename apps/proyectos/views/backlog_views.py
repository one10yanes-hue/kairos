from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.utils import timezone
from ..models import Proyecto, HistoriaUsuario, Tarea, Incidencia, Sprint, RegistroAvance
from ..decorators import miembro_requerido, ROLES_EDICION, ROLES_REVISION
import json


@miembro_requerido(ROLES_REVISION)
def historia_aprobar(request, pk, hid):
    proyecto = request.proyecto
    historia = get_object_or_404(HistoriaUsuario, pk=hid, proyecto=proyecto, activo=True)
    if historia.estado == "revision":
        historia.estado = "done"
        historia.full_clean()
        historia.save()
        RegistroAvance.objects.create(proyecto=proyecto, tipo="historia_completada",
            descripcion=f"Historia {historia.codigo} aprobada como Done por {request.user.get_full_name()}", user=request.user)
    referer = request.META.get("HTTP_REFERER", "")
    if referer and "/usuario/tablero" in referer:
        return redirect("gestion:tablero")
    return redirect("proyectos:backlog", pk=proyecto.pk)


@miembro_requerido(ROLES_REVISION)
def historia_rechazar(request, pk, hid):
    proyecto = request.proyecto
    historia = get_object_or_404(HistoriaUsuario, pk=hid, proyecto=proyecto, activo=True)
    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo del rechazo.")
            return redirect("proyectos:backlog", pk=proyecto.pk)
        if historia.estado == "revision":
            historia.estado = "en_progreso"
            historia.full_clean()
            historia.save()
            RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
                descripcion=f"Historia {historia.codigo} rechazada por {request.user.get_full_name()}: {motivo}", user=request.user)
            messages.warning(request, f"Historia {historia.codigo} rechazada: {motivo}")
        referer = request.META.get("HTTP_REFERER", "")
        if referer and "/usuario/tablero" in referer:
            return redirect("gestion:tablero")
        return redirect("proyectos:backlog", pk=proyecto.pk)
    return redirect("proyectos:backlog", pk=proyecto.pk)


@miembro_requerido()
def backlog_view(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)

    # Filtros
    q = request.GET.get("q", "").strip()
    filtro_tipo = request.GET.get("tipo", "")
    filtro_estado = request.GET.get("estado", "")
    filtro_prioridad = request.GET.get("prioridad", "")

    # Historias (todas, con sprint opcional)
    historias = proyecto.historias.filter(activo=True).prefetch_related(
        "tareas__incidencias", "tareas__asignacion__registros", "tareas__asignado_a", "creador", "sprint"
    ).order_by("orden")
    # Tareas sueltas (sin historia, puede tener sprint o no)
    tareas_sueltas = proyecto.tareas.filter(activo=True, historia__isnull=True).select_related("asignado_a", "creador", "sprint").order_by("-fecha_creacion")
    # Incidencias sueltas (sin tarea asociada, o con tarea sin historia)
    incidencias = proyecto.incidencias.filter(activo=True, tarea__isnull=True).select_related("reportado_por", "asignado_a").order_by("-fecha_creacion")

    if q:
        historias = historias.filter(Q(titulo__icontains=q) | Q(codigo__icontains=q) | Q(descripcion__icontains=q) | Q(criterios_aceptacion__icontains=q))
        tareas_sueltas = tareas_sueltas.filter(Q(titulo__icontains=q) | Q(codigo__icontains=q))
        incidencias = incidencias.filter(Q(titulo__icontains=q) | Q(codigo__icontains=q))
    if filtro_estado:
        historias = historias.filter(estado=filtro_estado)
        tareas_sueltas = tareas_sueltas.filter(estado=filtro_estado)
    if filtro_prioridad:
        historias = historias.filter(prioridad=filtro_prioridad)
        tareas_sueltas = tareas_sueltas.filter(prioridad=filtro_prioridad)
    # Severidad aplica solo a incidencias
    filtro_severidad = request.GET.get("severidad", "")
    if filtro_severidad:
        incidencias = incidencias.filter(severidad=filtro_severidad)

    # KPIs
    total_h = proyecto.historias.filter(activo=True).count()
    total_t = proyecto.tareas.filter(activo=True).count()
    total_i = proyecto.incidencias.filter(activo=True).exclude(estado__in=["cerrada","resuelta","duplicada"]).count()
    must_count = proyecto.historias.filter(activo=True, prioridad="must").count()
    puntos_total = proyecto.historias.filter(activo=True).aggregate(s=Sum("puntos_historia"))["s"] or 0
    sprints_activos = proyecto.sprints.filter(activo=True).order_by("numero")
    sprint_count = sprints_activos.count()

    return render(request, "proyectos/backlog.html", {
        "proyecto": proyecto,
        "historias": historias,
        "tareas_sueltas": tareas_sueltas,
        "incidencias": incidencias,
        "total_h": total_h, "total_t": total_t, "total_i": total_i,
        "must_count": must_count, "puntos_total": puntos_total,
        "sprints_activos": sprints_activos, "sprint_count": sprint_count,
        "sprints": sprints_activos,
        "q": q, "filtro_estado": filtro_estado, "filtro_prioridad": filtro_prioridad,
        "today": timezone.now().date(),
    })


@miembro_requerido(ROLES_EDICION)
def backlog_reordenar(request, pk):
    if request.method == "POST":
        try:
            raw = request.POST.get("ordenes_json", "")
            if not raw:
                return redirect("proyectos:backlog", pk=pk)
            data = json.loads(raw)
            items = data.get("ordenes", [])
            for item in items:
                HistoriaUsuario.objects.filter(
                    pk=item["id"], proyecto_id=pk
                ).update(orden=item["orden"])
            messages.success(request, "Orden del backlog actualizado.")
        except Exception as e:
            messages.error(request, f"Error al reordenar: {e}")
    return redirect("proyectos:backlog", pk=pk)


@miembro_requerido(ROLES_EDICION)
def historia_create(request, pk):
    proyecto = request.proyecto
    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        if not titulo:
            messages.error(request, "El titulo es obligatorio.")
            return redirect("proyectos:backlog", pk=proyecto.pk)
        historia = HistoriaUsuario.objects.create(
            proyecto=proyecto,
            titulo=titulo,
            descripcion=request.POST.get("descripcion", ""),
            criterios_aceptacion=request.POST.get("criterios", ""),
            prioridad=request.POST.get("prioridad", "should"),
            puntos_historia=int(request.POST.get("puntos", 0) or 0),
            creador=request.user,
        )
        historia.codigo = f"{proyecto.codigo}-US-{historia.pk:03d}"
        historia.full_clean()
        historia.save()
        RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
            descripcion=f"Historia {historia.codigo} creada: {historia.titulo[:60]}", user=request.user)
        messages.success(request, f"Historia {historia.codigo} creada.")
        return redirect("proyectos:backlog", pk=proyecto.pk)
    return render(request, "proyectos/historia_form.html", {"proyecto": proyecto})


@miembro_requerido(ROLES_EDICION)
def historia_edit(request, pk, hid):
    proyecto = request.proyecto
    historia = get_object_or_404(HistoriaUsuario, pk=hid, proyecto=proyecto, activo=True)
    if request.method == "POST":
        historia.titulo = request.POST.get("titulo", historia.titulo)
        historia.descripcion = request.POST.get("descripcion", historia.descripcion)
        historia.criterios_aceptacion = request.POST.get("criterios", historia.criterios_aceptacion)
        historia.prioridad = request.POST.get("prioridad", historia.prioridad)
        historia.puntos_historia = int(request.POST.get("puntos", 0) or 0)
        historia.estado = request.POST.get("estado", historia.estado)
        sprint_id = request.POST.get("sprint_id")
        if sprint_id:
            from ..models import Sprint
            historia.sprint = get_object_or_404(Sprint, pk=sprint_id, proyecto=proyecto)
            if historia.estado == "backlog":
                historia.estado = "sprint_backlog"
        else:
            historia.sprint = None
            if historia.estado == "sprint_backlog":
                historia.estado = "backlog"
        historia.full_clean()
        historia.save()
        RegistroAvance.objects.create(proyecto=proyecto, tipo="comentario",
            descripcion=f"Historia {historia.codigo} editada por {request.user.get_full_name()}", user=request.user)
        messages.success(request, "Historia actualizada.")
        return redirect("proyectos:backlog", pk=proyecto.pk)
    return render(request, "proyectos/historia_form.html", {"proyecto": proyecto, "historia": historia, "editando": True})


@miembro_requerido()
def historia_comentarios(request, pk, hid):
    proyecto = request.proyecto
    historia = get_object_or_404(HistoriaUsuario, pk=hid, proyecto=proyecto, activo=True)
    if request.method == "POST":
        texto = request.POST.get("texto", "").strip()
        if texto:
            from ..models import ComentarioHistoria
            c = ComentarioHistoria.objects.create(historia=historia, user=request.user, texto=texto)
            return JsonResponse({"ok": True, "historia_id": historia.pk,
                "user": request.user.get_full_name(), "texto": texto, "fecha": c.fecha_creacion.strftime("%d/%m %H:%M")})
        return JsonResponse({"ok": False}, status=400)
    comentarios = ComentarioHistoria.objects.filter(historia=historia, activo=True).order_by("fecha_creacion")
    return JsonResponse([{
        "user": c.user.get_full_name(), "texto": c.texto,
        "fecha": c.fecha_creacion.strftime("%d/%m %H:%M")
    } for c in comentarios], safe=False)
