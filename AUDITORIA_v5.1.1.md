# Auditoria Modulo Proyectos — v5.1.1
> Fecha: 19/06/2026

---

## CRITICOS (5) — Correccion inmediata

### C1 — NameError en proyecto_workflow
**Archivo:** `apps/proyectos/views/proyecto_views.py:566`
**Causa:** `reverse()` usado sin importar (`from django.urls import reverse`)
**Fix:** Agregar `from django.urls import reverse` al inicio del archivo
**Impacto:** Crash total al aplicar preset con roles sobrantes

### C2 — sync_tarea_from_asignacion no mapea "Revision"
**Archivo:** `apps/proyectos/signals.py:15-18`
**Causa:** El dict `mapping` no tiene `"Revision": "revision"`
**Fix:** Agregar `"Revision": "revision"` al mapping
**Impacto:** Kanban↔Tarea roto para todo el flujo de revision

### C3 — actualizar_estado() roto con edge cases
**Archivo:** `apps/proyectos/models.py:181-194`
**Causa:**
- Cero tareas → retorna sin cambiar estado (nunca avanza)
- Tareas canceladas no se ignoran → bloquean todos los checks de `if estados == {...}`
- Mezcla `["revision", "pendiente"]` no tiene match en el if/elif
**Fix:** Ignorar `cancelada` en el set de estados, manejar todos los casos
**Impacto:** Historias atascadas en estado incorrecto permanentemente

### C4 — RegistroAvance tipo "tarea_creada" no valido
**Archivo:** `apps/proyectos/views/tarea_views.py:78` + `apps/proyectos/models.py:351-359`
**Causa:** `RegistroAvance.TIPOS` no incluye `"tarea_creada"` ni otros tipos usados en views
**Fix:** Agregar tipos faltantes: `tarea_creada`, `tarea_rechazada`, `incidencia_creada`, `historia_aprobada`, `historia_rechazada`, `miembro_agregado`, `miembro_removido`, `sprint_creado`
**Impacto:** `full_clean()` fallaria en cualquier RegistroAvance con tipo invalido

### C5 — tarea.tipo recibe valores fuera de TIPOS choices
**Archivo:** `apps/proyectos/views/tarea_views.py:66` + `:303`
**Causa:** `tp.nombre.lower().replace(" ", "_")[:20]` produce strings arbitrarios
**Fix:** Mapear el TipoActividad a uno de los valores validos de Tarea.TIPOS, o usar "tarea" como default
**Impacto:** Datos invalidos en BD — el campo `tipo` guarda valores no permitidos

---

## ALTOS (13) — Prioridad 2

| # | Archivo | Descripcion |
|---|---------|-------------|
| H1 | `proyecto_views.py:223` | `get_or_create` manager como lider no actualiza membresias existentes con rol diferente |
| H2 | `proyecto_views.py:348-366` | Cascade `.update()` bypasses `save()`, `clean()`, signals |
| H3 | `proyecto_views.py:340-381` | Sin cascade para proyecto estado `finalizado` |
| H4 | `tarea_views.py:219-221` | `tarea_mover` no valida transiciones workflow |
| H5 | `tarea_views.py:156-174` | Codigo duplicado en `tarea_rechazar` (doble save) |
| H6 | `sprint_views.py:55` | `sprint_iniciado` RegistroAvance se crea al CREAR sprint, no al INICIAR |
| H7 | `sprint_views.py:142-145` | Burndown sobre-conta puntos de historia (resta puntos completos por cada tarea, no por historia) |
| H8 | `backlog_views.py:80-86` | KPIs calculados con datos no filtrados vs tabla con datos filtrados |
| H9 | `signals.py:22` | `update_fields=["estado"]` bypasses `clean()` del modelo |
| H10 | `incidencia_views.py:80-84` | Cambios de estado sin validacion de workflow |
| H11 | `incidencia_views.py:77-78` | Sin restricciones de rol para transiciones de estado |
| H12 | `proyecto_views.py:572` | Preset destruye workflows custom sin confirmacion |
| H13 | `models.py:62` | `MiembroProyecto.rol` default `"developer"` no esta en ROLES |

---

## MEDIOS (18) — Prioridad 3

| # | Descripcion |
|---|-------------|
| M1 | Sin cascade de `cancelado`/`finalizado` → `activo` |
| M2 | `posted_subarea_ids` parsing sin manejo de ValueError |
| M3 | `tarea_edit` form no pre-selecciona `tipo_actividad_id` |
| M4 | `bloqueada` mapeado a `Pausada` en AsignacionActividad |
| M5 | `tarea_edit` permite editar tareas en `revision` |
| M6 | `sprint_create` .update() bypasses historia model validation |
| M7 | `sprint_iniciar` no crea RegistroAvance |
| M8 | `sprint_finalizar` sin `full_clean()` |
| M9 | `sprint_finalizar` no maneja tareas no finalizadas |
| M10 | `historia_edit` no auto-transiciona estado al asignar sprint |
| M11 | `historia_aprobar/rechazar` sin `full_clean()` |
| M12 | `filtro_estado` incompatible entre historia y tarea choices |
| M13 | `filtro_estado` no aplicado a incidencias |
| M14 | `total_i` KPI vs `incidencias` queryset inconsistente |
| M15 | Naming inconsistente `nombre_actividad` entre funciones |
| M16 | Old AsignacionActividad no limpiada al cambiar `asignado_a` |
| M17 | `incidencia_convertir` hardcodes `tipo="bug"` |
| M18 | `detectar_preset` heuristico fragil |

---

## BAJOS (16) — Prioridad 4

| # | Descripcion |
|---|-------------|
| L1 | Race condition en generacion de codigo hex |
| L2 | `tarea_mover` swallows exceptions with `pass` |
| L3 | `tarea_edit` no valida transiciones de estado |
| L4 | Sprint numero race condition |
| L5 | `sprint_finalizar` marca `revision` como `done` sin aprobacion |
| L6 | Sin vista directa para cancelar sprint |
| L7 | `historia_create` sin `full_clean()` |
| L8 | Busqueda inconsistente entre tipos de entidad |
| L9 | Sin filtro de severidad para incidencias en backlog |
| L10 | Signal dispara en cambios no-estado |
| L11 | Sin RegistroAvance en cambios de estado incidencia |
| L12 | Sin RegistroAvance en conversion incidencia→tarea |
| L13 | `full_clean()` no llamado en incidencia_convertir |
| L14 | CFD "En Curso" excluye bloqueada |
| L15 | Bitacora limitada a 50 registros sin paginacion |
| L16 | `Proyecto.avance` no cuenta tareas canceladas |

---

## Plan de Correccion

| Sprint | Alcance | Issues |
|--------|---------|--------|
| **Sprint Fix 1** | Criticos C1-C3 (1-2h) | C1, C2, C3 |
| **Sprint Fix 2** | Criticos C4-C5 + migracion (2-3h) | C4, C5 |
| **Sprint Fix 3** | Altos H1-H13 (4-6h) | H1-H13 |
| **Sprint Fix 4** | Medios + Bajos (6-8h) | M1-M18 + L1-L16 |

**Total estimado: 13-19 horas**
