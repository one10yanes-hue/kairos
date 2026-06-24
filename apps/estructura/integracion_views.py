from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import connections, transaction
from apps.accounts.models import User, Empresa, Rol, UserEmpresa
from apps.estructura.models import Area, SubArea, UserSubArea, EmpresaArea
from apps.gestion.models import AsignacionActividad, RegistroTiempo
from apps.planificacion.models import PlanificacionDetalle
from apps.auditoria.models import SyncLog


def _get_kactus_empresas():
    """Obtener empresas desde KACTUS y asegurar que existan en BD local."""
    kactus_rows = []
    kactus_error = False
    try:
        with connections["kactus"].cursor() as c:
            c.execute("SELECT cod_empr, nom_empr, nit_empr, dir_empr, tel_empr FROM gn_empre")
            kactus_rows = c.fetchall()
    except Exception:
        kactus_error = True

    resultados = []
    codigos_vistos = set()

    for r in kactus_rows:
        cod = str(r[0]).strip() if r[0] is not None else ""
        nom = str(r[1]).strip() if r[1] is not None else ""
        nit = str(r[2]).strip() if r[2] is not None else ""
        dir_ = str(r[3]).strip() if r[3] is not None else ""
        tel = str(r[4]).strip() if r[4] is not None else ""
        emp_local = Empresa.objects.filter(nit=nit, activo=True).first() if nit else None
        if not emp_local and nom:
            emp_local, _ = Empresa.objects.get_or_create(
                nombre=nom,
                defaults={
                    "nit": nit,
                    "codigo": cod,
                    "direccion": dir_,
                    "telefono": tel,
                },
            )
        has_subs = EmpresaArea.objects.filter(empresa=emp_local, area__subareas__activo=True).exists() if emp_local else False
        codigos_vistos.add(cod)
        resultados.append({
            "codigo": cod,
            "nombre": nom,
            "nit": nit,
            "direccion": dir_,
            "telefono": tel,
            "local_id": emp_local.pk if emp_local else None,
            "has_subareas": has_subs,
            "origen": "kactus",
        })

    if kactus_error or not kactus_rows:
        for emp in Empresa.objects.filter(activo=True):
            if emp.codigo and emp.codigo not in codigos_vistos:
                codigos_vistos.add(emp.codigo)
                resultados.append({
                    "codigo": emp.codigo,
                    "nombre": emp.nombre,
                    "nit": emp.nit or "",
                    "direccion": emp.direccion or "",
                    "telefono": emp.telefono or "",
                    "local_id": emp.pk,
                    "has_subareas": EmpresaArea.objects.filter(empresa=emp, area__subareas__activo=True).exists(),
                    "origen": "local",
                })

    return resultados


@login_required
def integracion_cargo(request):
    if request.user.rol.nombre != "Master":
        return redirect("root")

    kactus_empresas = _get_kactus_empresas()
    roles = Rol.objects.filter(activo=True).order_by("id")

    if request.method == "POST":
        empleados_raw = request.POST.get("empleados", "")
        empleados = [x.strip() for x in empleados_raw.split(",") if x.strip()]
        rol_id = request.POST.get("rol_id")
        subarea_id = request.POST.get("subarea_id", "")
        empresa_kactus = request.POST.get("empresa_kactus")
        area_nombre = request.POST.get("area_nombre", "").strip()
        subarea_nombre = request.POST.get("subarea_nombre", "").strip()

        if not empleados or not rol_id:
            messages.error(request, "Debes seleccionar empleados y rol.")
        elif not subarea_id and not (area_nombre and subarea_nombre):
            messages.error(request, "Debes seleccionar una subarea existente o crear una nueva.")
        else:
            if area_nombre and subarea_nombre:
                empresa = None
                if empresa_kactus:
                    empresa = Empresa.objects.filter(codigo=empresa_kactus, activo=True).first()
                if not empresa:
                    empresa = Empresa.objects.filter(activo=True).first()
                if empresa:
                    area, _ = Area.objects.get_or_create(nombre=area_nombre)
                    EmpresaArea.objects.get_or_create(area=area, empresa=empresa)
                    subarea, _ = SubArea.objects.get_or_create(nombre=subarea_nombre, area=area)
                    subarea_id = subarea.pk
                else:
                    messages.error(request, "No hay empresas disponibles en el sistema.")
                    return redirect("estructura:integracion_cargo")

            subarea = SubArea.objects.filter(pk=subarea_id).first()
            if not subarea:
                messages.error(request, "Subarea no valida.")
                return redirect("estructura:integracion_cargo")

            creados = 0
            try:
                with connections["kactus"].cursor() as c:
                    placeholders = ",".join(["%s"] * len(empleados))
                    c.execute(
                        f"SELECT e.cod_empl, e.nom_empl, e.ape_empl, e.FEC_EXPE, e.box_mail, e.eee_mail, "
                        f"       ca.nom_carg, e.cod_empr, em.nom_empr "
                        f"FROM dbo.bi_emple e "
                        f"INNER JOIN dbo.nm_contr ct ON e.cod_empl = ct.cod_empl AND e.cod_empr = ct.cod_empr "
                        f"INNER JOIN dbo.bi_cargo ca ON ct.cod_carg = ca.cod_carg AND ct.cod_empr = ca.cod_empr "
                        f"INNER JOIN dbo.gn_empre em ON e.cod_empr = em.cod_empr "
                        f"WHERE ct.ind_acti = 'A' AND e.cod_empl IN ({placeholders})",
                        empleados,
                    )
                    empleados_data = {str(r[0]): r for r in c.fetchall()}
            except Exception as e:
                messages.error(request, f"Error al consultar KACTUS: {e}")
                return redirect("estructura:integracion_cargo")

            rol = Rol.objects.filter(pk=rol_id).first()
            errores = []

            for cod_empl in empleados:
                emp = empleados_data.get(cod_empl)
                if not emp:
                    continue
                cedula = str(cod_empl)
                user = User.objects.filter(cedula=cedula).first()
                if user:
                    # Usuario ya existe: asociarlo a la subarea si no lo esta
                    UserSubArea.objects.get_or_create(user=user, subarea=subarea, defaults={"activo": True})
                    creados += 1
                    continue
                try:
                    with transaction.atomic():
                        fecha_exp = emp[3]
                        if hasattr(fecha_exp, "strftime"):
                            fecha_exp = fecha_exp.strftime("%Y-%m-%d")
                        if not fecha_exp:
                            errores.append(f"{cedula}: fecha de expedicion vacia en KACTUS")
                            continue
                        emp_cod_empr = str(emp[7] or "").strip() if len(emp) > 7 else ""
                        emp_nom_empr = str(emp[8] or "").strip() if len(emp) > 8 else ""
                        empresa_local = Empresa.objects.filter(codigo=emp_cod_empr, activo=True).first()
                        user = User.objects.create(
                            cedula=cedula,
                            fecha_expedicion=fecha_exp,
                            nombre=str(emp[1] or "").strip(),
                            apellido=str(emp[2] or "").strip(),
                            email=str(emp[4] or emp[5] or "").strip(),
                            cargo=str(emp[6] or "").strip(),
                            telefono=empresa_local.telefono or "" if empresa_local else "",
                            rol=rol,
                        )
                        user.set_unusable_password()
                        user.save()
                        if empresa_local:
                            UserEmpresa.objects.get_or_create(user=user, empresa=empresa_local, defaults={"activo": True})
                        UserSubArea.objects.create(user=user, subarea=subarea)
                        creados += 1
                except Exception as e:
                    errores.append(f"{cedula}: {e}")

            if creados > 0:
                messages.success(request, f"{creados} empleado(s) habilitado(s) exitosamente.")
            if errores:
                messages.warning(request, f"Errores: {'; '.join(errores[:3])}")
            if not creados and not errores:
                messages.warning(request, "No se habilito ningun empleado (cedulas existentes o error).")
        return redirect("estructura:integracion_cargo")

    return render(request, "estructura/integracion_cargo.html", {
        "kactus_empresas": kactus_empresas,
        "roles": roles,
    })


@login_required
def api_integracion_cargos(request):
    if request.user.rol.nombre not in ["Master", "Admin"]:
        return JsonResponse([], safe=False)
    empresa_cod = request.GET.get("empresa", "").strip()
    q = request.GET.get("q", "").strip()
    try:
        with connections["kactus"].cursor() as c:
            sql = """
                SELECT ca.cod_carg, ca.nom_carg, COUNT(ct.cod_empl) as total
                FROM dbo.bi_cargo ca
                INNER JOIN dbo.nm_contr ct ON ca.cod_carg = ct.cod_carg AND ca.cod_empr = ct.cod_empr
                WHERE ca.ind_acti = 'A' AND ct.ind_acti = 'A'
            """
            params = []
            if q:
                sql += " AND ca.nom_carg LIKE %s"
                params.append(f"%{q}%")
            sql += " GROUP BY ca.cod_carg, ca.nom_carg ORDER BY ca.nom_carg"
            c.execute(sql, params)
            rows = c.fetchall()
    except Exception:
        return JsonResponse([], safe=False)
    return JsonResponse([{
        "cod": str(r[0]).strip(),
        "nom": str(r[1]).strip(),
        "total": r[2],
    } for r in rows], safe=False)


@login_required
def api_integracion_empleados(request):
    if request.user.rol.nombre not in ["Master", "Admin"]:
        return JsonResponse([], safe=False)
    empresa_cod = request.GET.get("empresa", "")
    cargo_cod = request.GET.get("cargo", "")
    cargos_param = request.GET.get("cargos", "").strip()

    cargos_list = []
    if cargos_param:
        cargos_list = [c.strip() for c in cargos_param.split(",") if c.strip()]
    elif cargo_cod:
        cargos_list = [cargo_cod]
    if empresa_cod and not cargos_list:
        return JsonResponse([], safe=False)

    try:
        with connections["kactus"].cursor() as c:
            if cargos_list:
                placeholders = ",".join(["%s"] * len(cargos_list))
                params = []
                sql = f"""
                    SELECT e.cod_empl, e.nom_empl, e.ape_empl, e.FEC_EXPE, e.box_mail, e.eee_mail,
                           c.cod_area, a.NOM_AREA, ca.nom_carg, ca.cod_carg
                    FROM dbo.bi_emple e
                    INNER JOIN dbo.nm_contr c ON e.cod_empl = c.cod_empl AND e.cod_empr = c.cod_empr
                    INNER JOIN dbo.bi_cargo ca ON c.cod_carg = ca.cod_carg AND c.cod_empr = ca.cod_empr
                    INNER JOIN SO_AREAS a ON c.cod_area = a.COD_AREA AND c.cod_empr = a.COD_EMPR
                    WHERE c.ind_acti = 'A' AND c.cod_carg IN ({placeholders})
                """
                if empresa_cod:
                    sql += " AND c.cod_empr = %s"
                    params.append(empresa_cod)
                sql += " ORDER BY e.nom_empl, e.ape_empl"
                c.execute(sql, cargos_list + params)
            else:
                return JsonResponse([], safe=False)
            rows = c.fetchall()
    except Exception:
        return JsonResponse([], safe=False)

    cods = [str(r[0]).strip() for r in rows if r[0] is not None]
    habilitados = set(User.objects.filter(cedula__in=cods).values_list("cedula", flat=True))

    return JsonResponse([{
        "cod": str(r[0]).strip() if r[0] is not None else "",
        "nom": str(r[1]).strip() if r[1] is not None else "",
        "ape": str(r[2]).strip() if r[2] is not None else "",
        "fecha": str(r[3])[:10] if r[3] else "",
        "email": str(r[4] or r[5] or "").strip(),
        "area": str(r[7]).strip() if r[7] is not None else "",
        "cargo_nom": str(r[8]).strip() if r[8] is not None else "",
        "cargo_cod": str(r[9]).strip() if r[9] is not None else "",
        "habilitado": str(r[0]).strip() in habilitados,
    } for r in rows], safe=False)


@login_required
def api_integracion_subareas(request):
    if request.user.rol.nombre not in ["Master", "Admin"]:
        return JsonResponse([], safe=False)
    subareas = SubArea.objects.filter(activo=True).select_related("area")
    return JsonResponse({
        "has_subareas": subareas.exists(),
        "items": [{"id": s.pk, "nombre": s.nombre, "area": s.area.nombre} for s in subareas],
    })


@login_required
def sync_cargo(request):
    """Sincronizar cambios de cargo/empresa desde KACTUS. Solo Master."""
    if request.user.rol.nombre != "Master":
        return redirect("root")

    kactus_empresas = _get_kactus_empresas()
    kactus_disponible = any(e.get("origen") == "kactus" for e in kactus_empresas)
    roles = Rol.objects.filter(activo=True).order_by("id")

    if request.method == "POST":
        accion = request.POST.get("accion", "")
        cedulas = [x.strip() for x in request.POST.get("cedulas", "").split(",") if x.strip()]
        empresa_kactus = request.POST.get("empresa_kactus", "")
        rol_id = request.POST.get("rol_id", "")
        subarea_id = request.POST.get("subarea_id", "")

        if not cedulas:
            messages.error(request, "Debes seleccionar al menos un empleado.")
        elif accion == "crear":
            return _batch_create(request, cedulas, empresa_kactus, rol_id, subarea_id)
        elif accion == "sincronizar":
            return _batch_sync(request, cedulas, empresa_kactus)
        elif accion == "desactivar":
            return _batch_desactivar(request, cedulas)
        else:
            messages.error(request, "Accion no valida.")
        return redirect("estructura:sync_cargo")

    return render(request, "estructura/integracion_sync.html", {
        "kactus_empresas": kactus_empresas,
        "kactus_disponible": kactus_disponible,
        "roles": roles,
    })


@login_required
def api_sync_comparar(request):
    """API: valida TODOS los usuarios locales contra KACTUS por cedula. Solo Master."""
    if request.user.rol.nombre != "Master":
        return JsonResponse({"error": "Acceso denegado"}, status=403)

    # 1. Obtener TODOS los usuarios locales activos
    local_users = User.objects.filter(activo=True)
    local_map = {}
    for u in local_users:
        local_map[u.cedula] = {
            "cedula": u.cedula,
            "nombre": (u.nombre or "").strip(),
            "apellido": (u.apellido or "").strip(),
            "cargo": (u.cargo or "").strip(),
            "email": (u.email or "").strip(),
            "fecha_exp": u.fecha_expedicion.strftime("%Y-%m-%d") if u.fecha_expedicion else "",
            "telefono": (u.telefono or "").strip(),
        }

    cedulas_locales = list(local_map.keys())

    resultado = {"nuevos": [], "cambios": [], "sin_cambios": [], "desvinculados": [],
                  "kactus_disponible": True, "total_local": len(local_map), "total_kactus": 0}

    if not cedulas_locales:
        return JsonResponse(resultado)

    # 2. Consultar KACTUS por cedula (sin filtrar por empresa)
    kactus_emps = {}
    kactus_error = None

    try:
        with connections["kactus"].cursor() as c:
            placeholders = ",".join(["%s"] * len(cedulas_locales))
            c.execute(f"""
                SELECT e.cod_empl, e.nom_empl, e.ape_empl, e.FEC_EXPE, e.box_mail, e.eee_mail,
                       ca.nom_carg, em.cod_empr, em.nom_empr, em.tel_empr
                FROM dbo.bi_emple e
                INNER JOIN dbo.nm_contr ct ON e.cod_empl = ct.cod_empl AND e.cod_empr = ct.cod_empr
                INNER JOIN dbo.bi_cargo ca ON ct.cod_carg = ca.cod_carg AND ct.cod_empr = ca.cod_empr
                INNER JOIN dbo.gn_empre em ON e.cod_empr = em.cod_empr
                WHERE ct.ind_acti = 'A' AND e.cod_empl IN ({placeholders})
                ORDER BY e.nom_empl, e.ape_empl
            """, cedulas_locales)
            rows = c.fetchall()

            for r in rows:
                cod = str(r[0]).strip() if r[0] is not None else ""
                kactus_emps[cod] = {
                    "cod_empl": cod,
                    "nom_empl": str(r[1] or "").strip(),
                    "ape_empl": str(r[2] or "").strip(),
                    "fecha_exp": str(r[3])[:10] if r[3] else "",
                    "email": str(r[4] or r[5] or "").strip(),
                    "cargo_kactus": str(r[6] or "").strip(),
                    "empresa_cod": str(r[7] or "").strip(),
                    "empresa_nom": str(r[8] or "").strip(),
                    "tel_empresa": str(r[9] or "").strip(),
                }
    except Exception as e:
        kactus_error = str(e)

    resultado["total_kactus"] = len(kactus_emps)
    resultado["kactus_disponible"] = kactus_error is None

    # 3. Comparar cada usuario local contra KACTUS
    for ced, local in local_map.items():
        kemp = kactus_emps.get(ced)

        if not kemp:
            if kactus_error:
                resultado["desvinculados"].append({
                    "cedula": ced,
                    "nombre": local["nombre"],
                    "apellido": local["apellido"],
                    "cargo": local["cargo"] or "-",
                    "motivo": f"KACTUS no disponible: {kactus_error[:100]}",
                })
            else:
                resultado["desvinculados"].append({
                    "cedula": ced,
                    "nombre": local["nombre"],
                    "apellido": local["apellido"],
                    "cargo": local["cargo"] or "-",
                })
            continue

        cambios = []
        if local["nombre"] != kemp["nom_empl"]:
            cambios.append(f"Nombre: {local['nombre']} → {kemp['nom_empl']}")
        if local["apellido"] != kemp["ape_empl"]:
            cambios.append(f"Apellido: {local['apellido']} → {kemp['ape_empl']}")
        if local["cargo"] != kemp["cargo_kactus"]:
            cambios.append(f"Cargo: {local['cargo'] or '-'} → {kemp['cargo_kactus']}")
        if local["email"] != kemp["email"]:
            cambios.append(f"Email: {local['email'] or '-'} → {kemp['email']}")
        if local["fecha_exp"] != kemp["fecha_exp"]:
            cambios.append(f"F.Exp: {local['fecha_exp'] or '-'} → {kemp['fecha_exp']}")
        if kemp["tel_empresa"] and local["telefono"] != kemp["tel_empresa"]:
            cambios.append(f"Tel: {local['telefono'] or '-'} → {kemp['tel_empresa']}")

        if cambios:
            user_obj = User.objects.filter(cedula=ced).first()
            pendientes = AsignacionActividad.objects.filter(
                user=user_obj, activo=True, estado__in=["Pendiente", "EnCurso", "Pausada"]
            ).count() if user_obj else 0
            resultado["cambios"].append({
                "cedula": ced,
                "nombre": local["nombre"],
                "apellido": local["apellido"],
                "cambios": cambios,
                "pendientes": pendientes,
                "bloqueado": pendientes > 0,
                "kactus_data": kemp,
            })
        else:
            resultado["sin_cambios"].append({
                "cedula": ced, "nombre": local["nombre"], "apellido": local["apellido"],
            })

    return JsonResponse(resultado)


def _batch_create(request, cedulas, empresa_kactus, rol_id, subarea_id):
    """Crear usuarios nuevos desde KACTUS. Reutiliza lógica de habilitacion."""
    try:
        with connections["kactus"].cursor() as c:
            placeholders = ",".join(["%s"] * len(cedulas))
            c.execute(
                f"SELECT cod_empl, nom_empl, ape_empl, FEC_EXPE, box_mail, eee_mail, ca.nom_carg "
                f"FROM dbo.bi_emple e "
                f"INNER JOIN dbo.nm_contr ct ON e.cod_empl=ct.cod_empl AND e.cod_empr=ct.cod_empr "
                f"INNER JOIN dbo.bi_cargo ca ON ct.cod_carg=ca.cod_carg AND ct.cod_empr=ca.cod_empr "
                f"WHERE ct.ind_acti='A' AND ct.cod_empr=%s AND e.cod_empl IN ({placeholders})",
                [empresa_kactus] + cedulas,
            )
            empleados_data = {str(r[0]): r for r in c.fetchall()}
    except Exception as e:
        messages.error(request, f"Error KACTUS: {e}")
        return redirect("estructura:sync_cargo")

    empresa_local = Empresa.objects.filter(codigo=empresa_kactus, activo=True).first()
    rol = Rol.objects.filter(pk=rol_id).first()
    subarea = SubArea.objects.filter(pk=subarea_id).first() if subarea_id else None
    creados = 0

    for ced in cedulas:
        emp = empleados_data.get(ced)
        if not emp or User.objects.filter(cedula=ced).exists():
            continue
        try:
            fexp = str(emp[3])[:10] if emp[3] else ""
            if not fexp:
                messages.warning(request, f"{ced}: fecha de expedicion vacia en KACTUS, se omite.")
                continue
            with transaction.atomic():
                user = User.objects.create(
                    cedula=ced,
                    fecha_expedicion=fexp,
                    nombre=str(emp[1] or "").strip(),
                    apellido=str(emp[2] or "").strip(),
                    email=str(emp[4] or emp[5] or "").strip(),
                    cargo=str(emp[6] or "").strip(),
                    telefono=empresa_local.telefono or "" if empresa_local else "",
                    rol=rol,
                )
                user.set_unusable_password()
                user.save()
                if empresa_local:
                    UserEmpresa.objects.update_or_create(user=user, empresa=empresa_local, defaults={"activo": True})
                if subarea:
                    UserSubArea.objects.create(user=user, subarea=subarea)
                SyncLog.objects.create(
                    user=user, accion="CREATE",
                    valor_nuevo={"cedula": ced, "cargo": str(emp[6] or "").strip()},
                    ejecutado_por=request.user,
                )
                creados += 1
        except Exception as e:
            messages.warning(request, f"Error con {ced}: {e}")

    if creados:
        messages.success(request, f"{creados} empleado(s) creado(s).")
    return redirect("estructura:sync_cargo")


def _batch_sync(request, cedulas, empresa_kactus=None):
    """Sincronizar TODOS los campos desde KACTUS: nombre, apellido, email, fecha, cargo, tel, empresa.
       Si no se especifica empresa, se obtiene desde KACTUS."""
    actualizados = 0
    bloqueados = 0

    for ced in cedulas:
        user = User.objects.filter(cedula=ced, activo=True).first()
        if not user:
            continue

        pendientes = AsignacionActividad.objects.filter(
            user=user, activo=True, estado__in=["Pendiente", "EnCurso", "Pausada"]
        ).count()
        if pendientes > 0:
            bloqueados += 1
            messages.warning(request, f"{user.get_full_name()} bloqueado: {pendientes} pendientes.")
            continue

        try:
            with connections["kactus"].cursor() as c:
                c.execute(
                    "SELECT e.nom_empl, e.ape_empl, e.FEC_EXPE, e.box_mail, e.eee_mail, "
                    "ca.nom_carg, em.cod_empr, em.tel_empr "
                    "FROM dbo.bi_emple e "
                    "INNER JOIN dbo.nm_contr ct ON e.cod_empl=ct.cod_empl AND e.cod_empr=ct.cod_empr "
                    "INNER JOIN dbo.bi_cargo ca ON ct.cod_carg=ca.cod_carg AND ct.cod_empr=ca.cod_empr "
                    "INNER JOIN dbo.gn_empre em ON e.cod_empr=em.cod_empr "
                    "WHERE ct.ind_acti='A' AND ct.cod_empl=%s",
                    [ced],
                )
                krow = c.fetchone()

            if not krow:
                messages.warning(request, f"{user.get_full_name()}: no encontrado en KACTUS activo.")
                continue

            kactus_cod_empr = str(krow[6] or "").strip() if krow[6] is not None else ""
            tel_kactus = str(krow[7] or "").strip() if krow[7] is not None else ""

            # Buscar o crear empresa local
            emp_local = Empresa.objects.filter(codigo=kactus_cod_empr, activo=True).first() if kactus_cod_empr else None

            with transaction.atomic():
                anterior = {
                    "nombre": user.nombre, "apellido": user.apellido, "cargo": user.cargo,
                    "email": user.email, "fecha_exp": str(user.fecha_expedicion or ""),
                    "telefono": user.telefono or "",
                }
                nuevo = {
                    "nombre": str(krow[0] or "").strip(),
                    "apellido": str(krow[1] or "").strip(),
                    "fecha_exp": str(krow[2])[:10] if krow[2] else "",
                    "email": str(krow[3] or krow[4] or "").strip(),
                    "cargo": str(krow[5] or "").strip(),
                    "telefono": tel_kactus,
                }

                user.nombre = nuevo["nombre"]
                user.apellido = nuevo["apellido"]
                if nuevo["fecha_exp"]:
                    from datetime import date as dt_date
                    try:
                        user.fecha_expedicion = dt_date.fromisoformat(nuevo["fecha_exp"])
                    except (ValueError, TypeError):
                        pass
                user.email = nuevo["email"]
                user.cargo = nuevo["cargo"]
                if nuevo["telefono"]:
                    user.telefono = nuevo["telefono"]
                user.save()

                if emp_local:
                    UserEmpresa.objects.update_or_create(user=user, empresa=emp_local, defaults={"activo": True})
                    UserEmpresa.objects.filter(user=user).exclude(empresa=emp_local).update(activo=False)

                SyncLog.objects.create(
                    user=user, accion="UPDATE",
                    valor_anterior=anterior,
                    valor_nuevo=nuevo,
                    ejecutado_por=request.user,
                )
                actualizados += 1
                messages.info(request, f"{user.get_full_name()} actualizado.")
        except Exception as e:
            messages.warning(request, f"Error con {user.get_full_name()}: {e}")

    if actualizados:
        messages.success(request, f"{actualizados} usuario(s) actualizado(s).")
    if bloqueados:
        messages.warning(request, f"{bloqueados} usuario(s) bloqueado(s) por pendientes.")
    return redirect("estructura:sync_cargo")


def _batch_desactivar(request, cedulas):
    """Desactivar usuarios no presentes en KACTUS."""
    desactivados = 0
    from django.utils import timezone

    for ced in cedulas:
        user = User.objects.filter(cedula=ced, activo=True).first()
        if not user:
            continue
        try:
            with transaction.atomic():
                stats = {"en_curso": 0, "pausadas": 0, "pendientes": 0}
                for a in AsignacionActividad.objects.filter(user=user, activo=True, estado="EnCurso"):
                    a.estado = "Finalizada"
                    a.save()
                    RegistroTiempo.objects.create(
                        asignacion=a, evento="Finalizacion", fecha_hora=timezone.now(),
                        comentario="Cerrado - usuario desvinculado KACTUS",
                    )
                    stats["en_curso"] += 1
                for a in AsignacionActividad.objects.filter(user=user, activo=True, estado="Pausada"):
                    a.estado = "Finalizada"
                    a.save()
                    RegistroTiempo.objects.create(
                        asignacion=a, evento="Finalizacion", fecha_hora=timezone.now(),
                        comentario="Cerrado - usuario desvinculado KACTUS",
                    )
                    stats["pausadas"] += 1
                stats["pendientes"] = AsignacionActividad.objects.filter(
                    user=user, activo=True, estado="Pendiente"
                ).update(activo=False, estado="Cancelada")
                PlanificacionDetalle.objects.filter(user=user, activo=True).update(activo=False)
                user.activo = False
                user.save()
                SyncLog.objects.create(
                    user=user, accion="DEACTIVATE",
                    valor_anterior={"activo": True},
                    valor_nuevo={"activo": False, **stats},
                    ejecutado_por=request.user,
                )
                desactivados += 1
        except Exception as e:
            messages.warning(request, f"Error con {user.get_full_name()}: {e}")

    if desactivados:
        messages.success(request, f"{desactivados} usuario(s) desactivado(s).")
    return redirect("estructura:sync_cargo")
