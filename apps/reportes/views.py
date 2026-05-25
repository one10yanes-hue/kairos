from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q, Count
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from apps.gestion.models import AsignacionActividad, RegistroTiempo
from apps.accounts.models import User
from apps.estructura.models import Area, SubArea, UserSubArea
from apps.actividades.models import Actividad


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


HF = Font(bold=True, color="FFFFFF", size=11)
HFILL = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
AL = Alignment(horizontal="center", vertical="center", wrap_text=True)
TB = Border(
    left=Side(style="thin", color="e2e8f0"),
    right=Side(style="thin", color="e2e8f0"),
    top=Side(style="thin", color="e2e8f0"),
    bottom=Side(style="thin", color="e2e8f0"),
)


def _style_header(ws, headers):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = HF; c.fill = HFILL; c.alignment = AL; c.border = TB


def _auto_width(ws):
    for col in ws.columns:
        ml = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(ml + 3, 45)


@login_required
@admin_required
def reporte_list(request):
    subareas = get_admin_subareas(request.user)
    empresas = Area.objects.filter(subareas__in=subareas).values_list("empresa__nombre", flat=True).distinct()
    areas = Area.objects.filter(subareas__in=subareas)
    users = User.objects.filter(
        id__in=UserSubArea.objects.filter(subarea__in=subareas, activo=True).values_list("user_id", flat=True),
        activo=True
    ).exclude(rol__nombre="Master")
    if request.user.rol.nombre != "Master":
        users = users.exclude(id=request.user.id).filter(rol__nombre="Usuario")

    qs = AsignacionActividad.objects.filter(actividad__subarea__in=subareas, activo=True)
    return render(request, "reportes/reporte_list.html", {
        "subareas": subareas, "empresas": empresas, "areas": areas, "users": users,
        "total_act": qs.count(),
        "total_fin": qs.filter(estado="Finalizada").count(),
        "total_curso": qs.filter(estado="EnCurso").count(),
        "total_pausa": qs.filter(estado="Pausada").count(),
        "total_pen": qs.filter(estado="Pendiente").count(),
    })


@login_required
@admin_required
def exportar_completo(request):
    subareas = get_admin_subareas(request.user)
    q = request.GET.get("q", "")
    empresa_nombre = request.GET.get("empresa", "")
    area_id = request.GET.get("area", "")
    subarea_id = request.GET.get("subarea", "")
    user_id = request.GET.get("user", "")
    estado = request.GET.get("estado", "")
    fecha_desde = request.GET.get("fecha_desde", "")
    fecha_hasta = request.GET.get("fecha_hasta", "")

    asignaciones = AsignacionActividad.objects.filter(
        actividad__subarea__in=subareas, activo=True
    ).select_related(
        "user", "actividad", "actividad__tipo_actividad",
        "actividad__subarea", "actividad__subarea__area",
        "actividad__subarea__area__empresa",
        "planificacion_detalle__planificacion__admin"
    ).prefetch_related("registros")

    if q:
        asignaciones = asignaciones.filter(
            Q(actividad__nombre__icontains=q) |
            Q(user__nombre__icontains=q) |
            Q(user__apellido__icontains=q)
        )
    if empresa_nombre:
        asignaciones = asignaciones.filter(actividad__subarea__area__empresa__nombre=empresa_nombre)
    if area_id:
        asignaciones = asignaciones.filter(actividad__subarea__area_id=area_id)
    if subarea_id:
        asignaciones = asignaciones.filter(actividad__subarea_id=subarea_id)
    if user_id:
        asignaciones = asignaciones.filter(user_id=user_id)
    if estado:
        asignaciones = asignaciones.filter(estado=estado)
    if fecha_desde:
        asignaciones = asignaciones.filter(fecha_asignacion__date__gte=fecha_desde)
    if fecha_hasta:
        asignaciones = asignaciones.filter(fecha_asignacion__date__lte=fecha_hasta)

    wb = Workbook()

    # ---- SHEET 1: Actividades ----
    ws = wb.active; ws.title = "Actividades"
    headers = [
        "ID Asig", "Cod. Empresa", "Empresa",
        "Cod. Area", "Area",
        "Cod. SubArea", "SubArea",
        "Cod. Actividad", "Actividad",
        "Cod. Tipo", "Tipo",
        "Usuario", "Cedula", "Email",
        "Estado", "Origen", "Asignado por",
        "Fecha Asignacion", "Tiempo Efectivo",
        "Fecha Primer Inicio", "Fecha Ultimo Evento",
        "Nro Actividad", "Total Pausas",
    ]
    _style_header(ws, headers)

    for row_num, a in enumerate(asignaciones, 2):
        r = list(a.registros.filter(activo=True).order_by("fecha_hora"))
        tz = timezone.get_current_timezone()
        inicio = r[0].fecha_hora.astimezone(tz).strftime("%Y-%m-%d %H:%M") if r and r[0].evento == "Inicio" else ""
        ultimo = r[-1].fecha_hora.astimezone(tz).strftime("%Y-%m-%d %H:%M") if r else ""
        nros = ", ".join(filter(None, (x.nro_actividad for x in r if x.nro_actividad)))
        pausas = sum(1 for x in r if x.evento == "Pausa")

        sub = a.actividad.subarea
        row = [
            a.pk,
            sub.area.empresa.codigo, sub.area.empresa.nombre,
            sub.area.codigo, sub.area.nombre,
            sub.codigo, sub.nombre,
            a.actividad.codigo, a.actividad.nombre,
            a.actividad.tipo_actividad.codigo, a.actividad.tipo_actividad.nombre,
            a.user.get_full_name(), a.user.cedula, a.user.email or "",
            a.get_estado_display(), a.origen or "Manual",
            a.origen_user.get_full_name() if a.origen_user else "-",
            a.fecha_asignacion.astimezone(tz).strftime("%Y-%m-%d %H:%M") if a.fecha_asignacion else "",
            a.tiempo_formateado(),
            inicio, ultimo,
            nros, pausas,
        ]
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=row_num, column=c, value=v)
            cell.border = TB
            if c in (2, 11, 15, 16, 17):
                cell.alignment = Alignment(horizontal="left")
    _auto_width(ws)

    # ---- SHEET 2: Registros de Tiempo ----
    ws2 = wb.create_sheet("Registros Tiempo")
    headers2 = [
        "ID Asig", "ID Evento", "Empresa", "Area", "SubArea", "Actividad", "Tipo",
        "Usuario", "Cedula",
        "Evento", "Fecha/Hora", "Motivo Pausa", "Comentario", "Nro Actividad",
    ]
    _style_header(ws2, headers2)

    registros = RegistroTiempo.objects.filter(
        asignacion__actividad__subarea__in=subareas, activo=True
    ).select_related(
        "asignacion__user", "asignacion__actividad",
        "asignacion__actividad__subarea__area__empresa",
    ).order_by("-fecha_hora")

    if fecha_desde:
        registros = registros.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        registros = registros.filter(fecha_hora__date__lte=fecha_hasta)
    if user_id:
        registros = registros.filter(asignacion__user_id=user_id)
    if subarea_id:
        registros = registros.filter(asignacion__actividad__subarea_id=subarea_id)

    tz2 = timezone.get_current_timezone()
    for row_num, r in enumerate(registros, 2):
        sub = r.asignacion.actividad.subarea
        row = [
            r.asignacion_id, r.pk,
            sub.area.empresa.nombre, sub.area.nombre, sub.nombre,
            r.asignacion.actividad.nombre,
            r.asignacion.actividad.tipo_actividad.nombre,
            r.asignacion.user.get_full_name(), r.asignacion.user.cedula,
            r.get_evento_display(),
            r.fecha_hora.astimezone(tz2).strftime("%Y-%m-%d %H:%M:%S"),
            r.motivo_pausa or "", r.comentario or "", r.nro_actividad or "",
        ]
        for c, v in enumerate(row, 1):
            cell = ws2.cell(row=row_num, column=c, value=v)
            cell.border = TB
    _auto_width(ws2)

    # ---- SHEET 3: Resumen por Usuario ----
    ws3 = wb.create_sheet("Resumen por Usuario")
    headers3 = [
        "Usuario", "Empresa", "Total Asignaciones",
        "Finalizadas", "En Curso", "Pausadas", "Pendientes",
        "Tiempo Total", "Nro Actividad Total",
    ]
    _style_header(ws3, headers3)

    for row_num, a in enumerate(asignaciones.values("user__pk").annotate(total=Count("id")), 2):
        pk = a["user__pk"]
        asign_user = asignaciones.filter(user__pk=pk)
        user = asign_user.first().user
        empresas = set(
            usa.subarea.area.empresa.nombre
            for usa in UserSubArea.objects.filter(user=user, activo=True).select_related("subarea__area__empresa")
        )
        total_tiempo = sum(x.tiempo_efectivo() for x in asign_user)
        row = [
            user.get_full_name(),
            ", ".join(empresas),
            a["total"],
            asign_user.filter(estado="Finalizada").count(),
            asign_user.filter(estado="EnCurso").count(),
            asign_user.filter(estado="Pausada").count(),
            asign_user.filter(estado="Pendiente").count(),
            f"{int(total_tiempo // 3600):02d}:{int((total_tiempo % 3600) // 60):02d}",
            sum(
                int(x.nro_actividad) for x in
                RegistroTiempo.objects.filter(
                    asignacion__in=asign_user, nro_actividad__isnull=False, activo=True
                ) if x.nro_actividad.isdigit()
            ),
        ]
        for c, v in enumerate(row, 1):
            ws3.cell(row=row_num, column=c, value=v).border = TB
    _auto_width(ws3)

    now = timezone.now().strftime("%Y%m%d_%H%M")
    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="reporte_completo_{now}.xlsx"'
    wb.save(resp)
    return resp
