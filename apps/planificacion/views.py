from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Min, Prefetch
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from apps.accounts.models import User
from apps.estructura.models import SubArea, UserSubArea
from apps.actividades.models import Actividad
from apps.gestion.models import AsignacionActividad
from .models import Planificacion, PlanificacionDetalle
from .forms import PlanificacionForm, PlanificacionDetalleForm
from datetime import date, timedelta


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.rol.nombre not in ["Admin", "Master"]:
            return redirect("root")
        return view_func(request, *args, **kwargs)
    return wrapper


def get_admin_subareas(user):
    if user.rol.nombre == "Master":
        return SubArea.objects.filter(activo=True)
    return SubArea.objects.filter(usuarios__user=user, activo=True)


@login_required
@admin_required
def planificacion_list(request):
    subareas = get_admin_subareas(request.user)
    q = request.GET.get("q", "")
    subarea_filter = request.GET.get("subarea", "")
    fecha_desde = request.GET.get("fecha_desde", "")
    fecha_hasta = request.GET.get("fecha_hasta", "")

    planificaciones = Planificacion.objects.filter(
        subarea__in=subareas, activo=True
    ).select_related("subarea__area", "admin").annotate(
        pen=Count("detalles__asignaciones", filter=Q(detalles__asignaciones__estado="Pendiente", detalles__asignaciones__activo=True)),
        cur=Count("detalles__asignaciones", filter=Q(detalles__asignaciones__estado="EnCurso", detalles__asignaciones__activo=True)),
        pau=Count("detalles__asignaciones", filter=Q(detalles__asignaciones__estado="Pausada", detalles__asignaciones__activo=True)),
        fin=Count("detalles__asignaciones", filter=Q(detalles__asignaciones__estado="Finalizada", detalles__asignaciones__activo=True)),
        total_act=Count("detalles__asignaciones", filter=Q(detalles__asignaciones__activo=True)),
        fecha_plan=Min("detalles__fecha_programada"),
        comentarios=Count("detalles__comentarios", filter=Q(detalles__comentarios__activo=True)),
    ).order_by("-fecha_creacion")

    base = planificaciones  # summary

    if q:
        planificaciones = planificaciones.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q)
        )
    if subarea_filter:
        planificaciones = planificaciones.filter(subarea_id=subarea_filter)
    if fecha_desde:
        planificaciones = planificaciones.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        planificaciones = planificaciones.filter(fecha_creacion__date__lte=fecha_hasta)

    paginator = Paginator(planificaciones, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, "planificacion/planificacion_list.html", {
        "planificaciones": page_obj, "page_obj": page_obj,
        "subareas": subareas,
        "q": q, "subarea_filter": subarea_filter,
        "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta,
        "total_base": base.count(),
        "cursos_count": base.filter(cur__gt=0).count(),
    })


@login_required
@admin_required
@ensure_csrf_cookie
def planificacion_create(request):
    subareas = get_admin_subareas(request.user)
    subarea_id = request.POST.get("subarea") if request.method == "POST" else None

    actividades = Actividad.objects.none()
    usuarios = User.objects.none()
    if subarea_id:
        actividades = Actividad.objects.filter(subarea_id=subarea_id, activo=True).select_related("tipo_actividad")
        usuarios = User.objects.filter(
            id__in=UserSubArea.objects.filter(subarea_id=subarea_id, activo=True).values_list("user_id", flat=True),
            activo=True
        ).filter(
            Q(rol__nombre__in=["Usuario", "Admin"]) | Q(roles_adicionales__nombre="Usuario")
        ).distinct()

    actividad_ids = []
    user_ids = []
    fecha_programada_value = ""
    fecha_vencimiento_value = ""
    nombre_value = ""
    descripcion_value = ""
    subarea_value = ""
    preserve_selection = False

    if request.method == "POST":
        form = PlanificacionForm(request.POST)
        form.fields["subarea"].queryset = subareas
        actividad_ids = [x for x in request.POST.getlist("actividades") if x]
        user_ids = [x for x in request.POST.getlist("users") if x]
        fecha_programada_value = request.POST.get("fecha_programada", "")
        fecha_vencimiento_value = request.POST.get("fecha_vencimiento", "")
        nombre_value = request.POST.get("nombre", "")
        descripcion_value = request.POST.get("descripcion", "")
        subarea_value = request.POST.get("subarea", "")

        if form.is_valid() and actividad_ids and user_ids:
            actividades_qs = Actividad.objects.filter(pk__in=actividad_ids, activo=True, subarea__in=subareas).select_related("tipo_actividad")

            requiere_fecha = actividades_qs.filter(tipo_actividad__requiere_fecha_limite=True).exists()
            if requiere_fecha and not fecha_vencimiento_value:
                messages.error(request, "Una o mas actividades requieren fecha de vencimiento.")
            else:
                if not fecha_programada_value:
                    fecha_programada = timezone.localtime(timezone.now()).strftime("%Y-%m-%d")
                else:
                    if fecha_programada_value < timezone.localtime(timezone.now()).strftime("%Y-%m-%d"):
                        messages.error(request, "La fecha programada no puede ser anterior a hoy.")
                        return redirect("planificacion:planificacion_create")
                    fecha_programada = fecha_programada_value

                if fecha_vencimiento_value and fecha_vencimiento_value < timezone.localtime(timezone.now()).strftime("%Y-%m-%d"):
                    messages.error(request, "La fecha de vencimiento no puede ser anterior a hoy.")
                    return redirect("planificacion:planificacion_create")

                planificacion = form.save(commit=False)
                planificacion.admin = request.user
                planificacion.cerrada = True
                planificacion.save()

                count = 0
                detalles_creados = []
                for actividad in actividades_qs:
                    for usuario in usuarios.filter(pk__in=user_ids):
                        if PlanificacionDetalle.objects.filter(
                            planificacion=planificacion, actividad=actividad, user=usuario, activo=True
                        ).exists():
                            continue
                        if AsignacionActividad.objects.filter(
                            user=usuario, actividad=actividad, activo=True
                        ).exclude(estado__in=["Finalizada", "Cancelada", "Trasladada"]).exists():
                            continue
                        detalles_creados.append((actividad, usuario))
                        count += 1

                if count == 0:
                    planificacion.delete()
                    messages.warning(request, "Todas las combinaciones ya estaban asignadas.")
                    return redirect("planificacion:planificacion_create")

                for actividad, usuario in detalles_creados:
                    detalle = PlanificacionDetalle.objects.create(
                        planificacion=planificacion,
                        actividad=actividad,
                        user=usuario,
                        fecha_asignacion=timezone.now(),
                        fecha_programada=fecha_programada or None,
                        fecha_vencimiento=fecha_vencimiento_value or None,
                    )
                    AsignacionActividad.objects.create(
                        planificacion_detalle=detalle,
                        user=usuario,
                        actividad=actividad,
                        estado="Pendiente",
                        origen="Planificacion",
                        origen_user=planificacion.admin,
                        nombre_actividad=actividad.nombre,
                        nombre_tipo=actividad.tipo_actividad.nombre,
                    )
                messages.success(request, f"Planificacion creada con {count} asignacion(es).")
                request.audit_record_id = planificacion.pk
                request.audit_modelo = "Planificacion"
                return redirect("planificacion:planificacion_detail", pk=planificacion.pk)
        elif not form.is_valid():
            messages.error(request, f"Revisa los campos del formulario: {', '.join(f'{k}: {v[0]}' for k, v in form.errors.items())}")
        else:
            messages.error(request, "Debes seleccionar al menos una actividad y un usuario.")

        preserve_selection = True

    else:
        form = PlanificacionForm()
        form.fields["subarea"].queryset = subareas
        if subareas.count() == 1:
            form.fields["subarea"].initial = subareas.first().pk
            form.fields["subarea"].empty_label = None

    return render(request, "planificacion/planificacion_form.html", {
        "form": form, "subareas": subareas,
        "actividades": actividades, "usuarios": usuarios,
        "actividad_ids": [int(x) for x in actividad_ids],
        "user_ids": [int(x) for x in user_ids],
        "fecha_programada_value": fecha_programada_value,
        "fecha_vencimiento_value": fecha_vencimiento_value,
        "nombre_value": nombre_value,
        "descripcion_value": descripcion_value,
        "subarea_value": subarea_value,
        "preserve_selection": preserve_selection,
    })


@login_required
@admin_required
@ensure_csrf_cookie
def planificacion_detail(request, pk):
    planificacion = get_object_or_404(Planificacion, pk=pk, activo=True)
    subarea = planificacion.subarea
    from apps.gestion.models import RegistroTiempo
    detalles = PlanificacionDetalle.objects.filter(
        planificacion=planificacion, activo=True
    ).select_related("actividad__tipo_actividad", "user").prefetch_related(
        Prefetch(
            "asignaciones",
            queryset=AsignacionActividad.objects.filter(activo=True).select_related("user").prefetch_related(
                Prefetch(
                    "registros",
                    queryset=RegistroTiempo.objects.filter(activo=True).order_by("fecha_hora"),
                )
            ),
        )
    )

    if request.method == "POST" and "add_detalle" in request.POST:
        if planificacion.cerrada:
            messages.error(request, "La planificacion esta cerrada. No se pueden agregar mas actividades.")
            return redirect("planificacion:planificacion_detail", pk=pk)
        actividad_ids = request.POST.getlist("actividades")
        user_ids = request.POST.getlist("users")
        fecha_programada = request.POST.get("fecha_programada")
        fecha_vencimiento = request.POST.get("fecha_vencimiento")

        if not actividad_ids or not user_ids:
            messages.error(request, "Debes seleccionar al menos una actividad y un usuario.")
            return redirect("planificacion:planificacion_detail", pk=pk)

        actividades_qs = Actividad.objects.filter(pk__in=actividad_ids, activo=True, subarea=subarea).select_related("tipo_actividad")
        requiere_fecha = actividades_qs.filter(tipo_actividad__requiere_fecha_limite=True).exists()

        if requiere_fecha and not fecha_vencimiento:
            messages.error(request, "Una o mas actividades requieren fecha de vencimiento.")
            return redirect("planificacion:planificacion_detail", pk=pk)

        if fecha_vencimiento and fecha_vencimiento < timezone.localtime(timezone.now()).strftime("%Y-%m-%d"):
            messages.error(request, "La fecha de vencimiento no puede ser anterior a hoy.")
            return redirect("planificacion:planificacion_detail", pk=pk)

        usuarios = User.objects.filter(pk__in=user_ids, activo=True).filter(
            Q(rol__nombre="Usuario") | Q(roles_adicionales__nombre="Usuario")
        ).distinct()

        if not usuarios.exists():
            messages.error(request, "No se encontraron usuarios validos.")
            return redirect("planificacion:planificacion_detail", pk=pk)

        contador = 0
        for actividad in actividades_qs:
            for usuario in usuarios:
                if PlanificacionDetalle.objects.filter(
                    planificacion=planificacion, actividad=actividad, user=usuario, activo=True
                ).exists():
                    continue
                if AsignacionActividad.objects.filter(
                    user=usuario, actividad=actividad, activo=True
                ).exclude(estado__in=["Finalizada", "Cancelada", "Trasladada"]).exists():
                    continue
                detalle = PlanificacionDetalle.objects.create(
                    planificacion=planificacion,
                    actividad=actividad,
                    user=usuario,
                    fecha_asignacion=timezone.now(),
                    fecha_programada=fecha_programada or None,
                    fecha_vencimiento=fecha_vencimiento or None,
                )
                AsignacionActividad.objects.create(
                    planificacion_detalle=detalle,
                    user=usuario,
                    actividad=actividad,
                    estado="Pendiente",
                    origen="Planificacion",
                    origen_user=planificacion.admin,
                    nombre_actividad=actividad.nombre,
                    nombre_tipo=actividad.tipo_actividad.nombre,
                )
                contador += 1

        if contador == 0:
            messages.warning(request, "Todas las combinaciones ya estaban asignadas.")
        else:
            messages.success(request, f"{contador} asignacion(es) creadas.")
        return redirect("planificacion:planificacion_detail", pk=pk)

    # Determinar estado general de la planificacion
    tiene_curso = False
    tiene_fin = False
    puede_inactivar = True
    for d in detalles:
        for a in d.asignaciones.all():
            if a.estado in ("EnCurso", "Pausada", "Cancelada", "Trasladada"):
                tiene_curso = True
                puede_inactivar = False
            if a.estado == "Finalizada":
                tiene_fin = True
                puede_inactivar = False

    if tiene_curso:
        estado_plan = "En curso"
    elif tiene_fin:
        estado_plan = "Finalizada"
    else:
        estado_plan = "Sin iniciar"

    from apps.gestion.models import Comentario

    return render(request, "planificacion/planificacion_detail.html", {
        "planificacion": planificacion,
        "detalles": detalles,
        "estado_plan": estado_plan,
        "puede_inactivar": puede_inactivar,
        "pendientes": AsignacionActividad.objects.filter(
            planificacion_detalle__planificacion=planificacion,
            activo=True, estado__in=["Pendiente", "Pausada"]
        ).select_related("user", "actividad", "planificacion_detalle"),
        "actividades_disponibles": Actividad.objects.filter(subarea=subarea, activo=True).select_related("tipo_actividad"),
        "usuarios_disponibles": User.objects.filter(
            id__in=UserSubArea.objects.filter(subarea=subarea, activo=True).values_list("user_id", flat=True),
            activo=True
        ).filter(
            Q(rol__nombre="Usuario") | Q(roles_adicionales__nombre="Usuario")
        ).distinct(),
        "comentarios_por_actividad": Comentario.objects.filter(
            detalle__planificacion=planificacion, activo=True
        ).select_related("user", "detalle__actividad").order_by("detalle__actividad__nombre", "fecha_creacion"),
        "now": timezone.now(),
    })


@login_required
@admin_required
def planificacion_delete(request, pk):
    planificacion = get_object_or_404(Planificacion, pk=pk)
    tiene_activo = planificacion.detalles.filter(
        activo=True, asignaciones__activo=True
    ).exclude(asignaciones__estado="Pendiente").exists()
    if tiene_activo:
        messages.error(request, "No se puede inactivar la planificacion porque tiene actividades en curso, pausadas o finalizadas.")
        return redirect("planificacion:planificacion_detail", pk=pk)
    for detalle in planificacion.detalles.filter(activo=True):
        AsignacionActividad.objects.filter(
            planificacion_detalle=detalle, activo=True
        ).update(activo=False, estado="Cancelada")
        detalle.activo = False
        detalle.save()
    planificacion.activo = False
    planificacion.save()
    messages.success(request, "Planificacion inactivada.")
    return redirect("planificacion:planificacion_list")


@login_required
@admin_required
def planificacion_detalle_remove(request, plan_pk, detalle_pk):
    detalle = get_object_or_404(PlanificacionDetalle, pk=detalle_pk, planificacion_id=plan_pk)
    detalle.activo = False
    detalle.save()

    AsignacionActividad.objects.filter(
        planificacion_detalle=detalle, activo=True
    ).update(activo=False, estado="Cancelada")

    messages.success(request, f"Asignacion de '{detalle.actividad.nombre}' a {detalle.user.get_full_name()} removida.")
    return redirect("planificacion:planificacion_detail", pk=plan_pk)


@login_required
@admin_required
def reprogramar_pendiente(request, pk):
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True)
    if asignacion.estado not in ["Pendiente", "Pausada"]:
        messages.error(request, "Solo actividades Pendientes o Pausadas pueden reprogramarse.")
        return redirect("planificacion:planificacion_detail", pk=asignacion.planificacion_detalle.planificacion_id)
    detalle = asignacion.planificacion_detalle
    if not detalle:
        messages.error(request, "Esta asignacion no tiene planificacion asociada.")
        return redirect("root")

    nueva_fecha = date.today() + timedelta(days=1)
    if request.POST.get("fecha_prorroga"):
        try:
            nueva_fecha = date.fromisoformat(request.POST["fecha_prorroga"])
        except ValueError:
            pass

    nueva_dt = timezone.make_aware(
        timezone.datetime.combine(nueva_fecha, timezone.datetime.min.time())
    )
    detalle.fecha_programada = nueva_dt
    detalle.fecha_vencimiento = nueva_dt
    detalle.save(update_fields=["fecha_programada", "fecha_vencimiento"])
    asignacion.prorroga_count += 1
    asignacion.save(update_fields=["prorroga_count"])
    messages.success(
        request,
        f"Actividad '{asignacion.actividad.nombre}' reprogramada para {nueva_fecha.strftime('%d/%m/%Y')}. "
        f"(Prorroga #{asignacion.prorroga_count})"
    )
    return redirect("planificacion:planificacion_detail", pk=detalle.planificacion_id)


@login_required
@admin_required
def reasignar_pendiente(request, pk):
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True)
    if asignacion.estado not in ["Pendiente", "Pausada"]:
        messages.error(request, "Solo actividades Pendientes o Pausadas pueden reasignarse.")
        return redirect("planificacion:planificacion_detail", pk=asignacion.planificacion_detalle.planificacion_id)
    nuevo_user_id = request.POST.get("user_id")
    if not nuevo_user_id:
        messages.error(request, "Selecciona un usuario destino.")
        return redirect("planificacion:planificacion_detail", pk=asignacion.planificacion_detalle.planificacion_id)
    nuevo_user = get_object_or_404(User, pk=nuevo_user_id, activo=True)

    old_user = asignacion.user
    asignacion.user = nuevo_user
    asignacion.estado = "Pendiente"
    asignacion.origen = "Reasignado"
    asignacion.origen_user = request.user
    asignacion.save()
    messages.success(
        request,
        f"'{asignacion.actividad.nombre}' reasignada de {old_user.get_full_name()} a {nuevo_user.get_full_name()}."
    )
    return redirect("planificacion:planificacion_detail", pk=asignacion.planificacion_detalle.planificacion_id)


@login_required
@admin_required
def cancelar_pendiente(request, pk):
    if request.method != "POST":
        return redirect("root")
    asignacion = get_object_or_404(AsignacionActividad, pk=pk, activo=True)
    if asignacion.estado not in ["Pendiente", "Pausada"]:
        messages.error(request, "Solo actividades Pendientes o Pausadas pueden cancelarse.")
        return redirect("planificacion:planificacion_detail", pk=asignacion.planificacion_detalle.planificacion_id)
    nombre = asignacion.actividad.nombre
    usuario = asignacion.user.get_full_name()
    asignacion.estado = "Cancelada"
    asignacion.save()
    messages.success(request, f"'{nombre}' de {usuario} cancelada.")
    return redirect("planificacion:planificacion_detail", pk=asignacion.planificacion_detalle.planificacion_id)
