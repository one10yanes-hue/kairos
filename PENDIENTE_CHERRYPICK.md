# PENDIENTE — Cherry-pick fixes compartidos a produccion
> Fecha: 20/06/2026 | Solo documentacion, no ejecutar aun

## Archivos que necesitan cherry-pick a `produccion` (v4.2.x)

Estos archivos recibieron fixes en `mejoras` que tambien aplican a `produccion`.
**NO copiar archivos completos** — contienen codigo de proyectos que no existe en produccion.

---

## 1. `config/settings.py` — DB_ENGINE mariadb/mysql mapping

```powershell
git checkout produccion
# Linea a agregar despues de "if db_engine in ['mssql','sql_server']: db_engine='mssql'":
# if db_engine in ["mariadb", "mysql"]:
#     db_engine = "django.db.backends.mysql"
```

## 2. `config/__init__.py` — PyMySQL bridge (try/except seguro)

```powershell
# Crear o reemplazar con:
# try:
#     import pymysql
#     pymysql.install_as_MySQLdb()
# except ImportError:
#     pass
```

---

## 3. `apps/planificacion/views.py` — Fixes (SIN codigo de proyectos)

Editores a aplicar MANUALMENTE (linea por linea):

### 3a. Validacion duplicados mismo dia
**Ubicacion:** `planificacion_create`, despues de `if PlanificacionDetalle.objects.filter(...)`
```python
# Cambiar:
# user=usuario, actividad=actividad, activo=True
# --- POR ---
# user=usuario, actividad=actividad, activo=True,
# planificacion_detalle__fecha_programada=fecha_programada,
```

### 3b. Validacion en prorroga (reprogramar_pendiente)
**Ubicacion:** `reprogramar_pendiente`, despues de `nueva_dt = timezone.make_aware(...)`
```python
# Agregar antes de "detalle.fecha_programada = nueva_dt":
# if AsignacionActividad.objects.filter(
#     user=asignacion.user, actividad=asignacion.actividad, activo=True,
#     planificacion_detalle__fecha_programada=nueva_fecha,
# ).exclude(pk=asignacion.pk).exclude(estado__in=["Finalizada","Cancelada","Trasladada"]).exists():
#     messages.error(...)
#     return redirect(...)
```

### 3c. Validacion en reasignar (reasignar_pendiente)
**Ubicacion:** `reasignar_pendiente`, despues de `nuevo_user = get_object_or_404(...)`
```python
# Agregar:
# fecha_prog = asignacion.planificacion_detalle.fecha_programada if asignacion.planificacion_detalle else None
# if fecha_prog and AsignacionActividad.objects.filter(
#     user=nuevo_user, actividad=asignacion.actividad, activo=True,
#     planificacion_detalle__fecha_programada=fecha_prog,
# ).exclude(pk=asignacion.pk).exclude(estado__in=["Finalizada","Cancelada","Trasladada"]).exists():
#     messages.error(...)
#     return redirect(...)
```

### 3d. Subarea check en planificacion_detail
**Ubicacion:** `planificacion_detail`, despues de `planificacion = get_object_or_404(...)`
```python
# Agregar:
# from apps.estructura.utils import get_admin_subareas
# subareas_user = get_admin_subareas(request.user)
# if planificacion.subarea_id not in [s.pk for s in subareas_user]:
#     messages.error(request, "No tienes acceso a esta planificacion.")
#     return redirect("planificacion:planificacion_list")
```
**Nota:** Requiere crear `apps/estructura/utils.py` primero (ver seccion 8).

---

## 4. `apps/gestion/views.py` — Fixes

### 4a. Entregable check en finalizar_actividad
**Ubicacion:** `finalizar_actividad`, despues del check de `estado not in ["EnCurso","Pausada"]`
```python
# Agregar:
# if hasattr(asignacion, 'tarea_proyecto') and asignacion.tarea_proyecto:
#     tarea = asignacion.tarea_proyecto
#     if tarea.actividad_catalogo and tarea.actividad_catalogo.tipo_actividad.requiere_entregable:
#         if not asignacion.entregable:
#             messages.error(request, "Este tipo...")
#             return redirect("gestion:detalle_actividad", pk=asignacion.pk)
```

### 4b. Detalle_actividad timeline unificado
**Ubicacion:** `detalle_actividad`, remplazar el bloque de `context = {` completo
```python
# Agregar timeline unificado (creacion + registros + comentarios + traslados + historial)
# Ver commit efed496 en mejoras
```

### 4c. Subarea scoping en detalle_actividad
**Ubicacion:** `detalle_actividad`, despues del check `asignacion.user != request.user`
```python
# Agregar para Admin:
# if asignacion.user != request.user and request.user.rol.nombre == "Admin":
#     from apps.estructura.utils import get_admin_subareas
#     admin_subareas = get_admin_subareas(request.user)
#     if asignacion.actividad.subarea_id not in [s.pk for s in admin_subareas]:
#         messages.error(request, "No tienes acceso...")
#         return redirect("gestion:tablero")
```

### 4d. Subarea scoping en buscar_usuarios_traslado
**Ubicacion:** `buscar_usuarios_traslado`, dentro del `if proyecto_id:` block
```python
# Agregar antes de miembros_ids:
# if request.user.rol.nombre == "Admin":
#     from apps.estructura.utils import get_admin_subareas
#     admin_subareas = get_admin_subareas(request.user)
#     from apps.proyectos.models import Proyecto
#     proyecto = Proyecto.objects.filter(pk=proyecto_id, subareas__in=admin_subareas).first()
#     if not proyecto:
#         return JsonResponse([], safe=False)
```
**Nota:** Este si requiere `apps.proyectos.models.Proyecto` — solo funciona si proyectos existe.

---

## 5. `apps/gestion/consumers.py` — Nuevos handlers WebSocket

```powershell
git checkout produccion
git checkout mejoras -- apps/gestion/consumers.py
# Verificar que no hay referencias a proyectos (no deberia)
git diff --cached apps/gestion/consumers.py
git add apps/gestion/consumers.py
git commit -m "v4.2.x: WebSocket handlers - sprint_iniciado, sprint_finalizado, incidencia_reportada"
```

---

## 6. `apps/gestion/templatetags/gestion_extras.py` — Typo mañana

```powershell
git checkout produccion
git checkout mejoras -- apps/gestion/templatetags/gestion_extras.py
git add apps/gestion/templatetags/gestion_extras.py
git commit -m "v4.2.x: Fix typo manana -> mañana en deadline_label"
```

---

## 7. `apps/dashboard/views.py` — Subarea scoping en linea_tiempo

```powershell
# Manual: en la seccion Gantt (si existe en produccion), cambiar:
# elif request.user.rol.nombre == "Admin" and request.user.maneja_proyectos:
#     proyectos_qs = Proyecto.objects.filter(activo=True)
# --- POR ---
# elif request.user.rol.nombre == "Admin" and request.user.maneja_proyectos:
#     from apps.estructura.utils import get_admin_subareas
#     admin_subareas = get_admin_subareas(request.user)
#     proyectos_qs = Proyecto.objects.filter(subareas__in=admin_subareas, activo=True).distinct()
```
**Nota:** Solo si la seccion Gantt de proyectos existe en produccion (probablemente no).

---

## 8. `apps/estructura/utils.py` — NUEVO archivo (PREREQUISITO)

```powershell
git checkout produccion
git checkout mejoras -- apps/estructura/utils.py
git add apps/estructura/utils.py
git commit -m "v4.2.x: get_admin_subareas compartida (roles_adicionales + DB check)"
```
**Este archivo es REQUISITO para los fixes 3d, 4c, 4d y 7.**

---

## 9. `apps/actividades/models.py` — Unique constraint + clean()

```powershell
# Manual: agregar a Actividad.Meta:
# unique_together = [["nombre", "subarea", "tipo_actividad"]]
# 
# Agregar a Actividad.clean():
# qs = Actividad.objects.filter(nombre=self.nombre, subarea=self.subarea, tipo_actividad=self.tipo_actividad, activo=True)
# if self.pk: qs = qs.exclude(pk=self.pk)
# if qs.exists(): raise ValidationError(f"Ya existe...")
```

---

## 10. `templates/accounts/login.html` — Logo KAIROS + diseno

```powershell
git checkout produccion
git checkout mejoras -- templates/accounts/login.html static/img/kairos_logo.png
# La version del login no tiene referencias a proyectos, es seguro
git add templates/accounts/login.html static/img/kairos_logo.png
git commit -m "v4.2.x: Logo KAIROS en login"
```

---

## 11. `templates/actividades/actividad_form.html` — Centrado

```powershell
git checkout produccion
git checkout mejoras -- templates/actividades/actividad_form.html
git add templates/actividades/actividad_form.html
git commit -m "v4.2.x: Formulario actividad centrado"
```

---

## 12. `templates/gestion/detalle_actividad.html` — Timeline unificado

```powershell
git checkout produccion
git checkout mejoras -- templates/gestion/detalle_actividad.html
git add templates/gestion/detalle_actividad.html
git commit -m "v4.2.x: Timeline unificado en detalle actividad"
```

---

## 13. `templates/dashboard/linea_tiempo.html` — Typo Mañana

```powershell
# Manual: cambiar "Manana" por "Ma&ntilde;ana" en el boton de navegacion
```

---

## 14. `config/settings.py` — DB credentials para mysql

```powershell
# Agregar despues del bloque mssql:
# if db_engine == "django.db.backends.mysql":
#     DATABASES["default"].update({
#         "HOST": env("DB_HOST", default="localhost"),
#         "PORT": env("DB_PORT", default="3306"),
#         "USER": env("DB_USER", default="root"),
#         "PASSWORD": env("DB_PASSWORD", default=""),
#     })
```

---

## Orden recomendado de aplicacion

| Orden | Que | Commando |
|-------|-----|----------|
| 1 | `utils.py` (prerequisito) | `git checkout mejoras -- apps/estructura/utils.py` |
| 2 | `settings.py` (DB engine) | Manual |
| 3 | `config/__init__.py` (PyMySQL) | Manual |
| 4 | `consumers.py` | `git checkout mejoras -- apps/gestion/consumers.py` |
| 5 | `gestion_extras.py` (typo) | `git checkout mejoras -- apps/gestion/templatetags/gestion_extras.py` |
| 6 | `login.html` + logo | `git checkout mejoras -- templates/accounts/login.html static/img/kairos_logo.png` |
| 7 | `detalle_actividad.html` | `git checkout mejoras -- templates/gestion/detalle_actividad.html` |
| 8 | `actividad_form.html` | `git checkout mejoras -- templates/actividades/actividad_form.html` |
| 9 | `planificacion/views.py` | Manual (solo 3a-3d) |
| 10 | `gestion/views.py` | Manual (solo 4a-4d) |
| 11 | `dashboard/views.py` | Manual (solo item 7) |
| 12 | `actividades/models.py` | Manual (unique + clean) |

Despues de cada paso:
```powershell
git add <archivos>
git commit -m "v4.2.x: <descripcion>"
```

Al final:
```powershell
git push origin produccion
```
