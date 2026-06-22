# PENDIENTE — Cherry-pick fixes compartidos a produccion
> Fecha: 21/06/2026 | Solo documentacion, no ejecutar aun

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

## 15. `static/css/main.css` — Navy branding global (#05053c)

```powershell
git checkout produccion
# Copiar SOLO los cambios de main.css (NO todo el archivo si difiere mucho)
git checkout mejoras -- static/css/main.css
git add static/css/main.css
git commit -m "v4.2.x: Navy #05053c global -- accent, brand vars, btn-primary, text-primary"
```
**Cambios clave en :root:**
- `--accent: #05053c` (antes `#3b82f6`)
- `--accent-light: #eef0f8` (antes `#eff6ff`)
- `--accent-dark: #030330` (antes `#1d4ed8`)
- `--brand-green: #35df6d`, `--brand-purple: #8a1fcf`, `--brand-dark: #05053c` (nuevas vars)

---

## 16. `static/css/sidebar.css` — Navy sidebar accents

```powershell
git checkout produccion
git checkout mejoras -- static/css/sidebar.css
git add static/css/sidebar.css
git commit -m "v4.2.x: Sidebar usa var(--accent) navy para avatar, active items, iconos"
```
**Cambios:** `.sidebar-user-avatar`, `.nav-item.active`, `.sidebar-brand i` usan `var(--accent)` = navy.

---

## 17. `templates/accounts/login.html` — Logo KAIROS navy + boton solido

```powershell
git checkout produccion
git checkout mejoras -- templates/accounts/login.html
git add templates/accounts/login.html
git commit -m "v4.2.x: Login KAIROS #05053c solido, boton #05053c, logo shadow navy"
```
**Cambios:**
- KAIROS titulo: `color:#05053c` (antes `var(--slate-800)`)
- Boton Ingresar: `background:#05053c` solid, `text-white`, `border:none` (antes `btn-primary`)
- Logo shadow: `rgba(5,5,60,0.12)` (antes `rgba(59,130,246,0.15)`)
- Version text: `color:var(--slate-400)` (antes `text-muted`)

---

## 18. `templates/base.html` — KAIROS sidebar navy

```powershell
# MANUAL: Solo cambiar el span de KAIROS en el sidebar-brand
# Buscar: <span class="sidebar-brand-text" style="...">
# Cambiar style a: font-family:'Nunito',sans-serif;font-weight:700;letter-spacing:1px;color:#05053c;
# Agregar al img: style="...box-shadow:0 2px 8px rgba(5,5,60,0.10);"
git add templates/base.html
git commit -m "v4.2.x: Sidebar KAIROS texto #05053c + logo shadow navy"
```
**NO copiar base.html completo** — la version de `mejoras` puede tener diferencias estructurales.

---

## 19. `templates/gestion/calendario.html` — FullCalendar active button navy

```powershell
# MANUAL: Buscar .fc-button-active y cambiar:
# background-color:#2563eb !important; border-color:#2563eb !important;
# --- POR ---
# background-color:var(--accent-dark) !important; border-color:var(--accent-dark) !important;
git add templates/gestion/calendario.html
git commit -m "v4.2.x: FullCalendar active button usa var(--accent-dark) navy"
```

---

## 20. `templates/404.html` + `templates/500.html` + `templates/403_csrf.html` — Error pages navy

```powershell
git checkout produccion
git checkout mejoras -- templates/404.html templates/500.html templates/403_csrf.html
git add templates/404.html templates/500.html templates/403_csrf.html
git commit -m "v4.2.x: Error pages cargan main.css + accent navy #05053c"
```
**Cambios:**
- Eliminado `:root { --accent: #3b82f6; }` inline
- Agregado `<link href="{% static 'css/main.css' %}">` (heredan `--accent: #05053c`)
- `btn-primary` ahora es navy via `main.css`

---

## 21. `apps/dashboard/views.py` — Fix UnboundLocalError + import limpio

```powershell
git checkout produccion
git checkout mejoras -- apps/dashboard/views.py
# Verificar diff: solo deberia cambiar get_admin_subareas
git diff --cached apps/dashboard/views.py
git add apps/dashboard/views.py
git commit -m "v4.2.x: Fix UnboundLocalError linea-tiempo - import get_admin_subareas al top"
```
**Cambios:**
- Agregado `from apps.estructura.utils import get_admin_subareas` al top
- Eliminada funcion local `def get_admin_subareas(user)` duplicada
- Eliminado import inline dentro de `linea_tiempo` (causaba UnboundLocalError)
- **PREREQUISITO:** `apps/estructura/utils.py` debe existir (seccion 8)

---

## Orden recomendado de aplicacion

| Orden | Que | Commando |
|-------|-----|----------|
| 1 | `utils.py` (prerequisito) | `git checkout mejoras -- apps/estructura/utils.py` |
| 2 | `settings.py` (DB engine) | Manual |
| 3 | `config/__init__.py` (PyMySQL) | Manual |
| 4 | `main.css` (navy accent global) | `git checkout mejoras -- static/css/main.css` |
| 5 | `sidebar.css` (navy sidebar) | `git checkout mejoras -- static/css/sidebar.css` |
| 6 | `consumers.py` | `git checkout mejoras -- apps/gestion/consumers.py` |
| 7 | `gestion_extras.py` (typo) | `git checkout mejoras -- apps/gestion/templatetags/gestion_extras.py` |
| 8 | `login.html` (logo + boton navy) | `git checkout mejoras -- templates/accounts/login.html` |
| 9 | `base.html` (sidebar KAIROS navy) | Manual |
| 10 | `detalle_actividad.html` | `git checkout mejoras -- templates/gestion/detalle_actividad.html` |
| 11 | `actividad_form.html` | `git checkout mejoras -- templates/actividades/actividad_form.html` |
| 12 | Error pages `404/500/403` | `git checkout mejoras -- templates/404.html templates/500.html templates/403_csrf.html` |
| 13 | `calendario.html` (FC navy) | Manual |
| 14 | `planificacion/views.py` | Manual (solo 3a-3d) |
| 15 | `gestion/views.py` | Manual (solo 4a-4d) |
| 16 | `dashboard/views.py` (UnboundLocalError) | `git checkout mejoras -- apps/dashboard/views.py` |
| 17 | `actividades/models.py` | Manual (unique + clean) |

Despues de cada paso:
```powershell
git add <archivos>
git commit -m "v4.2.x: <descripcion>"
```

Al final:
```powershell
git push origin produccion
```
