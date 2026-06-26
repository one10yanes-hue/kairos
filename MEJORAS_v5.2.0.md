# Mejoras v5.2.0 — Plan de trabajo

## Flujo de proyecto completo

```
Líder/Responsable
    │
    ├── Crea proyecto, historias, tareas
    ├── Asigna ejecutores
    ├── Define sprints
    └── Puede revisar y aprobar si se le asigna ese rol

Ejecutor
    │
    ├── Trabaja la tarea (inicia → pausa → finaliza)
    ├── Adjunta entregable (si el tipo lo requiere)
    └── Si hay bug → se crea tarea hija desde la incidencia

Revisor (QA)
    │
    ├── Ve la card [Revisar] T-NNN en su Kanban
    ├── Descarga entregable del ejecutor
    ├── APRUEBA → tarea queda como Finalizada
    └── RECHAZA →
           ├── Sin bug → tarea vuelve a Pendiente (historial intacto)
           └── Con bug  → crea Incidencia + Tarea hija asignada al ejecutor

Historia (automático)
    │
    └── Cuando TODAS las tareas están finalizadas →
        historia.estado = "revision"
        Se crean cards [Aprobar] US-NNN para los aprobadores

Aprobador
    │
    ├── Ve la card [Aprobar] US-NNN en su Kanban
    ├── Ve el resumen de la historia:
    │      • Timeline compilado de todas las tareas
    │      • Entregables de cada tarea (ejecutor + revisor)
    │      • Incidencias/bugs creados
    │      • Quién trabajó, cuánto tiempo
    ├── APRUEBA → historia = "done", todo queda cerrado
    └── RECHAZA → TODAS las tareas vuelven a "pendiente"
                  (ejecutor corrige → revisor revisa → aprobador aprueba)
```

---

## ✅ YA IMPLEMENTADO

### Kanban / Tablero
- [x] Date picker en "Mis actividades" (filtra por fecha seleccionada)
- [x] Vencimiento badges en las 4 columnas Kanban (`⏰ Vence en 3d`)
- [x] Cards uniformes: `height: 125px`, `flex-wrap: nowrap`, scroll invisible
- [x] Botones 26×24px fijos con `display: inline-flex`
- [x] Título y subárea truncados a 1 línea con ellipsis

### Modal Finalizar
- [x] Botones inferiores: `[Cancelar] [Rechazar] [Aprobar]` para revisiones
- [x] Rechazo: primer clic muestra textarea de motivo, segundo confirma
- [x] Archivo entregable sin asterisco para revisores (opcional)
- [x] Nro. Actividad oculto para tareas de revisión
- [x] Planificadas en modales con formato detallado (📅 nombre, tipo, fecha)
- [x] Planificadas usan `planificadas_todas` (todas las pendientes, sin filtro `detalle__isnull`)
- [x] Checkbox "Crear incidencia de bug" al rechazar

### Flujo de rechazo con bug
- [x] Rechazo CON bug: crea Incidencia + Tarea hija asignada al ejecutor (la original NO se devuelve)
- [x] Rechazo SIN bug: tarea original vuelve a Pendiente con historial y tiempo intactos

### Detalle de Actividad
- [x] Layout compacto y profesional (copiado de produccion)
- [x] Sección "Informacion" con badges de origen, fechas, área
- [x] Sección Entregables con árbol de archivos (ejecutor + revisor)
- [x] Timeline con eventos de entregable adjuntado
- [x] `orig_entregable` lookup para tareas `[Revisar]` (entregable del ejecutor original)
- [x] Colores en timeline para tipo `entregable` (morado ejecutor, verde revisor)

### Revisiones (`/admin/revisiones/`)
- [x] Campo file al aprobar (solo si el TipoActividad `requiere_entregable=True`)
- [x] Muestra entregable del ejecutor + revisor en tabla
- [x] Modelo `revision_entregable` guardado (migración 0018)

### Sidebar
- [x] Sección Proyectos visible para Master, Admin y miembros de proyecto
- [x] Sub-enlaces (Dashboard, Backlog, Sprints, Tareas, Incidencias, Estructura) solo cuando `proyecto_ctx`
- [x] Planificación arriba de Evento Flash
- [x] Título "Planificaciones equipos de trabajos" en admin

### Planificación self (`/usuario/planificaciones/`)
- [x] Filtros: búsqueda, subárea, rango de fechas
- [x] KPIs: Total, Con Activos, Mostrando
- [x] Columnas: Nombre, SubArea, Estado, F. Planif., Creado, Acciones
- [x] Paginación
- [x] Vista detalle: tabla de actividades con modal de prorrogar
- [x] Prorrogar solo para estado Pendiente (no EnCurso/Pausada)
- [x] Campos fecha más angostos (`col-md-4`)

### Incidencias
- [x] Campo `adjunto` (FileField, opcional) en modelo Incidencia
- [x] Formulario `incidencia_form.html` con `enctype="multipart/form-data"`
- [x] Selector de usuarios solo miembros del proyecto (excluye observadores)
- [x] Descargar adjunto en detalle de incidencia

### Formularios varios
- [x] Centrados: tipo_form, actividad_form, subarea_form (`mx-auto`, `justify-content-center`)

### Sidebar / Branding
- [x] Colores corporativos: navy `#05053c`, purple `#8a1fcf`, green `#35df6d`
- [x] Sidebar estilo dock: colapsado por defecto, hover expande, Ctrl+B fija
- [x] `scrollToActive()` centra ítem activo
- [x] Tooltips en iconos modo colapsado

---

## 🚧 PENDIENTE

### Alta prioridad

#### 1. Renombrar `[Revision]` → `[Aprobar]`

**Motivo:** El aprobador no "revisa", "aprueba". El nombre `[Revision]` es confuso porque el revisor/QA ya usa "Revisión".

**Archivos a modificar:**
- `apps/proyectos/signals.py` — al crear la card para aprobador: `[Revision]` → `[Aprobar]`
- `apps/gestion/views.py` — en `finalizar_actividad`, el regex/match para historias: `[Revision]` → `[Aprobar]`
- `apps/proyectos/views/tarea_views.py` — idem en rechazo de historia

#### 2. Timeline compilado en detalle de `[Aprobar]`

**Motivo:** El aprobador necesita ver el historial completo de la historia, no solo su card.

**Archivos a modificar:**
- `apps/gestion/views.py:detalle_actividad` — detectar prefix `[Aprobar]`, buscar la historia, traer todas sus tareas con sus asignaciones, registros, entregables, incidencias
- `templates/gestion/detalle_actividad.html` — crear sección "Tareas de la Historia" con timeline compilado:
  - Por cada tarea: estado final, quién trabajó, tiempo
  - Entregables de cada tarea (ejecutor + revisor)
  - Incidencias/bugs asociados
  - Eventos de revisión (aprobación/rechazo por tarea)

#### 3. Restringir creación de tareas en historias `done` / `revision`

**Motivo:** Evitar el círculo vicioso de crear tareas en historias ya cerradas.

**Archivos a modificar:**
- `apps/proyectos/views/tarea_views.py:tarea_create` — validar:
  ```python
  if historia and historia.estado in ["revision", "done"]:
      messages.error(request, f"No se pueden agregar tareas a una historia en estado '{historia.get_estado_display()}'.")
      return redirect(...)
  ```
- Si el líder necesita agregar trabajo: debe devolver la historia a `backlog` (única transición desde `done`)

#### 4. Modal Finalizar para `[Aprobar]`

**Motivo:** La card `[Aprobar]` muestra campos irrelevantes (Nro Actividad, entregable obligatorio).

**Archivos a modificar:**
- `templates/gestion/tablero.html` (JS `abrirFinalizar`) — detectar `[Aprobar]` y:
  - Ocultar Nro Actividad
  - Ocultar asterisco de entregable
  - Mostrar solo Aprobar/Rechazar (igual que `[Revisar]`)

---

### Media prioridad

#### 5. Entregables visibles para aprobador

**Archivos a modificar:**
- `templates/gestion/detalle_actividad.html` — mostrar árbol de entregables de TODAS las tareas de la historia (no solo de la card actual)

#### 6. Bug en rechazo de historia

**Archivos a modificar:**
- `apps/gestion/views.py:finalizar_actividad` — agregar checkbox "Crear bug" en el rechazo de `[Aprobar]`, igual que en `[Revisar]`

---

### Restricciones por rol en el proyecto

#### 7. Asignación de tareas: solo ejecutores del proyecto

**Estado actual:**
- `tarea_create` (tarea_views.py): Asigna a cualquier usuario miembro del proyecto (`miembros` query), sin filtrar por rol `ejecutor`
- `crear_asignacion_desde_tarea` (signals.py): Crea la `AsignacionActividad` para el usuario asignado sin validar rol

**Archivos a modificar:**
- `apps/proyectos/views/tarea_views.py:tarea_create` — línea 66: filtrar `miembros` solo con `rol='ejecutor'`
- `apps/proyectos/views/tarea_views.py:tarea_edit` — mismo filtro
- `apps/proyectos/signals.py:crear_asignacion_desde_tarea` — agregar validación: si `tarea.asignado_a` no es `ejecutor`, no crear asignación

**Efecto:**
- Solo Ejecutores pueden ser asignados a tareas
- La tarea aparece en su tablero Kanban personal
- Líder/Responsable/Revisor/Aprobador NO reciben tareas de ejecución

#### 8. Cards `[Revisar]`: solo para Revisores/QA (y líder)

**Estado actual:**
- `tarea_views.py` (línea 260-262): Crea `[Revisar]` para TODOS los miembros con `rol__in=ROLES_REVISION` = `["lider", "responsable", "revisor", "aprobador"]`
- Esto significa que líder, responsable, revisor Y aprobador reciben la card de revisión de tarea

**Archivos a modificar:**
- `apps/proyectos/views/tarea_views.py` — cambiar filtro a solo `rol__in=["lider", "revisor"]`:
  ```python
  revisores = MiembroProyecto.objects.filter(
      proyecto=proyecto, activo=True, rol__in=["lider", "revisor"]  # ya no incluye responsable ni aprobador
  )
  ```
- `apps/proyectos/signals.py:sync_tarea_from_asignacion` — mismo cambio en la creación de `[Revisar]` para tareas

**Efecto:**
- Revisor/QA ve `[Revisar]` en su Kanban
- Líder también (puede revisar si quiere)
- Responsable: NO recibe cards de revisión (puede ver en proyecto si necesita)
- Aprobador: NO recibe cards de revisión de tareas (solo ve historias)

#### 9. Cards `[Aprobar]` (ex `[Revision]`): solo para Aprobadores (y líder/responsable)

**Estado actual:**
- `signals.py` (línea 47-62): Crea `[Revision]` para TODOS los miembros con `rol__in=ROLES_REVISION`
- Todos ven la card de aprobación de historia

**Archivos a modificar:**
- `apps/proyectos/signals.py` — cambiar filtro a solo aprobadores + líder/responsable:
  ```python
  aprobadores = MiembroProyecto.objects.filter(
      proyecto=tarea.proyecto, activo=True, rol__in=["lider", "responsable", "aprobador"]
  )
  ```

**Efecto:**
- Aprobador ve `[Aprobar] US-NNN` en su Kanban
- Líder/Responsable también (pueden aprobar si necesitan)
- Revisor: NO ve cards de aprobación
- Ejecutor: NO ve cards de aprobación

#### 10. Traslado restringido por rol

**Estado actual:**
- `trasladar_actividad` (gestion/views.py línea 645-655): Si es tarea de proyecto, valida que el destino sea `ejecutor`
- Pero cuando se traslada una card `[Revisar]` o `[Aprobar]`, el destino debería ser revisor/aprobador, no ejecutor

**Archivos a modificar:**
- `apps/gestion/views.py:trasladar_actividad` — detectar el tipo de card:
  ```python
  if nombre_actividad.startswith("[Revisar]"):
      # Destino debe ser revisor
      validar_rol = "revisor"
  elif nombre_actividad.startswith("[Aprobar]"):
      # Destino debe ser aprobador
      validar_rol = "aprobador"
  else:
      # Tarea normal de ejecutor
      validar_rol = "ejecutor"
  ```
- `apps/gestion/views.py:buscar_usuarios_traslado` — mismo filtro dinámico según tipo de card

**Efecto:**
- Traslado de tarea normal → solo ejecutores
- Traslado de `[Revisar]` → solo revisores/QA
- Traslado de `[Aprobar]` → solo aprobadores

#### 11. Historia: asignar aprobador al crearla

**Estado actual:**
- `HistoriaUsuario` no tiene campo `aprobador`
- Al crear `[Aprobar]`, se crea una card para CADA miembro con `rol__in=["lider","responsable","aprobador"]`
- No hay un responsable único por historia

**Archivos a modificar:**
- `apps/proyectos/models.py` — agregar campo:
  ```python
  aprobador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="historias_aprobadas")
  ```
- `apps/proyectos/migrations/0011_historiausuario_aprobador.py` — migración
- `templates/proyectos/historia_form.html` — agregar selector de aprobador (solo miembros con rol `aprobador`)
- `apps/proyectos/views/backlog_views.py:historia_create` y `historia_edit` — guardar el aprobador
- `apps/proyectos/signals.py` — al crear `[Aprobar]`:
  ```python
  if historia.aprobador:
      # Crear solo para el aprobador asignado
      aprobadores = [historia.aprobador]
  else:
      # Fallback: todos los aprobadores del proyecto
      aprobadores = MiembroProyecto.objects.filter(...)
  ```

**Efecto:**
- Al crear historia, líder/responsable asigna un aprobador específico
- La card `[Aprobar]` solo llega a ESE aprobador
- Si hay múltiples aprobadores, cada historia se asigna a uno distinto
- Traslado de `[Aprobar]` permite reasignar a otro aprobador

#### 12. Tarea: asignar revisor al crearla

**Estado actual:**
- `Tarea.asignado_a` solo asigna el ejecutor
- Al crear `[Revisar]`, se crea una card para CADA revisor del proyecto
- No hay un revisor responsable por tarea

**Archivos a modificar:**
- `apps/proyectos/models.py` — agregar campo:
  ```python
  revisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tareas_revisadas")
  ```
- `apps/proyectos/migrations/0012_tarea_revisor_tarea_revisor.py` — migración
- `templates/proyectos/tarea_form.html` — agregar selector de revisor (solo miembros con rol `revisor`)
- `apps/proyectos/views/tarea_views.py:tarea_create` y `tarea_edit` — guardar el revisor
- `apps/proyectos/views/tarea_views.py` — al crear `[Revisar]`:
  ```python
  if tarea.revisor:
      revisores = [tarea.revisor]
  else:
      revisores = MiembroProyecto.objects.filter(proyecto=proyecto, activo=True, rol__in=["lider", "revisor"])
  ```

**Efecto:**
- Al crear tarea, líder/responsable asigna ejecutor + revisor
- La card `[Revisar]` solo llega a ESE revisor
- El revisor sabe qué tareas le corresponden
- Traslado de `[Revisar]` permite reasignar a otro revisor

#### 13. En cascada: historia → tarea → revisión → aprobación

**Estado actual:**
- No hay relación directa entre el aprobador de la historia y la creación de tareas

**Propuesta:**
- Cuando se crea una tarea dentro de una historia que tiene `aprobador` asignado:
  - La tarea hereda automáticamente el `revisor` de la historia? No, el revisor es por tarea.
  - Pero el aprobador de la historia se muestra en el detalle de la tarea
  - El flujo en cascada es:
    ```
    Historia (aprobador asignado)
      └── Tarea 1 (ejecutor + revisor)
      └── Tarea 2 (ejecutor + revisor)
      └── Tarea 3 (ejecutor + revisor)
      └── ...todas finalizadas → [Aprobar] para el aprobador de la historia
    ```

**No requiere cambios de código.** Es flujo lógico que ya funciona:
- Las tareas se crean con ejecutor + revisor
- Cuando todas finalizan, la historia pasa a revisión
- La card `[Aprobar]` se crea para el `aprobador` asignado a la historia

#### 14. Múltiples miembros por rol

**Estado actual:**
- El modelo `MiembroProyecto` ya permite varios usuarios con el mismo rol en un proyecto
- Al crear `[Revisar]`, se crea una card para CADA revisor
- Al crear `[Aprobar]`, se crea una card para CADA aprobador

**No requiere cambios de modelo.** Solo asegurar que:
- La UI de equipo (`proyecto_equipo.html`) permita agregar múltiples usuarios por rol
- Al asignar tarea, se muestre solo ejecutores (ya filtrado por rol)
- Al asignar en incidencia, se muestre solo ejecutores (ya implementado)

✅ Ya funciona: El proyecto puede tener N ejecutores, N revisores, N aprobadores.

---

### Baja prioridad

#### 15. Workflow engine: `WorkflowConfig` por proyecto

- Ya existe el modelo `WorkflowConfig` y las transiciones hardcodeadas
- Pendiente: interfaz para que el líder/responsable configure workflows personalizados por proyecto

#### 16. Dashboard de proyecto para líder/responsable

- KPIs: tareas por estado, incidencias abiertas, avance por sprint
- Burndown chart
- Gantt (ya existe)

---

## 🧩 ONBOARDING Y CONFIGURACIÓN DE PROYECTO

### 17. Onboarding al crear proyecto (multi-paso)

**Motivo:** Actualmente al crear proyecto solo pide nombre, manager y subareas. No guía al usuario a configurar el flujo de trabajo ni el equipo.

**Propuesta de flujo onboarding:**

```
Paso 1: Datos básicos
├── Nombre, descripción, objetivo
├── Manager (se convierte en Líder automáticamente)
└── Áreas/Subareas interesadas
       ↓
Paso 2: Plantilla de flujo
├── Simple / Con Revisión / Completo
├── Muestra resumen de roles que requiere
└── Confirma
       ↓
Paso 3: Equipo mínimo
├── Asignar Ejecutores (mínimo 1)
├── Asignar Revisores/QA (solo si flujo = revisión o completo)
├── Asignar Aprobadores (solo si flujo = revisión o completo)
└── Asignar Responsables, Observadores (opcional)
       ↓
Paso 4: Confirmación y creación
├── Resumen: proyecto + flujo + equipo
├── Botón "Crear Proyecto"
└── Redirige a Dashboard del proyecto
```

**Archivos a modificar:**
- `templates/proyectos/proyecto_form.html` — convertir en wizard multi-paso con JS (preferible) o vistas separadas
- `apps/proyectos/views/proyecto_views.py:proyecto_create` — manejar los 3 pasos, crear proyecto, aplicar workflow, agregar miembros

**Validaciones:**
- Si flujo `revision` o `completo`: al menos 1 revisor y 1 aprobador requeridos
- Si flujo `completo`: al menos 1 observador (opcional)

### 18. Bloqueo de plantilla de flujo post-creación

**Estado actual:**
- `/proyectos/{pk}/workflow/` permite aplicar CUALQUIER plantilla en cualquier momento
- Esto puede romper el flujo si hay tareas/historias en estados que la nueva plantilla no contempla

**Propuesta:**
- La plantilla de flujo se selecciona **solo durante el onboarding**
- Una vez creado el proyecto, la sección de flujo en `/workflow/` solo permite:
  - **Ver** las transiciones actuales (solo lectura)
  - **Gestionar equipo**: agregar/remover miembros por rol
  - **NO** cambiar la plantilla

**Archivos a modificar:**
- `templates/proyectos/proyecto_workflow.html` — ocultar selector de preset si ya fue aplicado; solo mostrar tabla de miembros + botón agregar/remover
- `apps/proyectos/models.py` — agregar campo:
  ```python
  Proyecto.workflow_bloqueado = models.BooleanField(default=False, help_text="Si True, no se puede cambiar la plantilla de flujo")
  ```
- `apps/proyectos/views/proyecto_views.py:proyecto_workflow` — si `workflow_bloqueado=True` y se intenta cambiar preset, rechazar

**Excepción:**
- Master puede desbloquear y cambiar la plantilla (fuerza bruta si es necesario)

### 19. Gestión de subareas del proyecto

**Estado actual:**
- Al crear proyecto se seleccionan subareas
- No hay UI para agregar/remover subareas después de la creación

**Propuesta:**
- En la configuración del proyecto (`/proyectos/{pk}/estructura/` o una nueva sección "Configuración"):
  - Mostrar subareas actuales
  - Permitir agregar nuevas subareas
  - Permitir remover subareas (solo si no hay tareas activas en ellas)

**Archivos a modificar:**
- `templates/proyectos/proyecto_estructura.html` — actualizar con checkboxes para modificar subareas
- `apps/proyectos/views/proyecto_views.py:proyecto_estructura` — manejar POST para agregar/remover subareas

### 20. Validación de roles mínimos al aplicar flujo

**Estado actual:**
- `proyecto_workflow` (línea 654-656) auto-agrega el manager como rol faltante
- NO valida que haya al menos 1 ejecutor, 1 revisor, 1 aprobador según el flujo

**Archivos a modificar:**
- `apps/proyectos/views/proyecto_views.py:proyecto_workflow` — al aplicar un preset, validar:

| Preset | Roles requeridos (mínimo) |
|--------|--------------------------|
| Simple | 1 ejecutor |
| Con Revisión | 1 ejecutor + 1 revisor + 1 aprobador |
| Completo | 1 ejecutor + 1 revisor + 1 aprobador |

  ```python
  roles_requeridos = {
      "simple": ["ejecutor"],
      "revision": ["ejecutor", "revisor", "aprobador"],
      "completo": ["ejecutor", "revisor", "aprobador"],
  }
  for rol in roles_requeridos.get(preset, []):
      if not miembros_activos.filter(rol=rol).exists():
          messages.error(request, f"Se requiere al menos 1 '{rol}' para el flujo '{preset}'.")
          return redirect(...)
  ```

---

## Roles del proyecto y sus permisos

| Rol | `ROLES_EDICION` | `ROLES_REVISION` | `ROLES_MOVER` | `ROLES_ADMIN` | Recibe `[Revisar]` | Recibe `[Aprobar]` |
|-----|:-:|:-:|:-:|:-:|:-:|:-:|
| Líder | ✅ | ✅ | ✅ | ✅ | ✅ (opcional) | ✅ |
| Responsable | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Ejecutor | — | — | ✅ | — | ❌ | ❌ |
| Revisor | — | ✅ | — | — | ✅ | ❌ |
| Aprobador | — | ✅ | — | — | ❌ | ✅ |
| Observador | — | — | — | — | ❌ | ❌ |

### Asignación de cards por rol (propuesto)

```
Roll              Tarea creada    [Revisar]      [Aprobar]
                  (ejecutor)      (revisor QA)   (historia)
──────────────────────────────────────────────────────────
Líder             ❌              ✅             ✅
Responsable       ❌              ❌             ✅
Ejecutor          ✅              ❌             ❌
Revisor/QA        ❌              ✅             ❌
Aprobador         ❌              ❌             ✅
Observador        ❌              ❌             ❌
```

### Traslado según tipo de card (propuesto)

```
Card origen          Destino permitido
──────────────────────────────────────
Tarea normal         → Ejecutor
[Revisar] T-NNN      → Revisor/QA
[Aprobar] US-NNN     → Aprobador
```

---

## Estados y transiciones de Historia

```
backlog → sprint_backlog → en_progreso → revision → done
   ↑           ↑               ↑            ↓
   └───────────┴───────────────┴────────────┘
                                        (solo a backlog)
```

---

## Cómo levantar el entorno

```bash
# Terminal 1: servidor Django
cd viva1a-stg
.\venv\Scripts\activate
python manage.py runserver

# Terminal 2: websocket (opcional)
python manage.py runworker tablero
```
