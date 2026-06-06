# FLUJO COMPLETO · Productividad + Gestión de Proyectos

## Índice
- [Flujo Planificación (Productividad)](#1-flujo-planificacin-productividad)
- [Flujo Proyecto (Gestión Ágil)](#2-flujo-proyecto-gestin-gil)
- [Enlace entre Planificación y Proyecto](#3-enlace-entre-planificacin-y-proyecto)
- [Puntos de Intervención (Aprobaciones/Rechazos)](#4-puntos-de-intervencin-aprobacionesrechazos)
- [Matriz de Roles y Acciones](#5-matriz-de-roles-y-acciones)
- [Vista por Rol](#6-vista-por-rol)
- [Resumen del Ciclo Completo](#7-resumen-del-ciclo-completo)

---

## 1. Flujo Planificación (Productividad)

```
Admin/Master
    │
    ├── [1] Crear TipoActividad (catálogo)
    │       ├── nombre, subarea
    │       ├── requiere_fecha_limite (True/False)
    │       ├── requiere_entregable (True/False)
    │       └── es_flash (True/False)
    │
    ├── [2] Crear Actividad (catálogo)
    │       ├── nombre, subarea, tipo_actividad
    │       └── clean: actividad.subarea == tipo_actividad.subarea
    │
    ├── [3] Crear Planificación
    │       ├── Seleccionar subarea
    │       ├── Seleccionar actividades × usuarios (producto cruzado)
    │       ├── [OPCIONAL] Vincular a Proyecto existente
    │       ├── fecha_programada (cuando aparece en tablero)
    │       └── fecha_vencimiento (deadline, obligatorio si requiere_fecha_limite)
    │
    └── [4] Planificación → genera:
            ├── PlanificacionDetalle (1 por par actividad×usuario)
            └── AsignacionActividad (estado = "Pendiente")
                    │
                    ▼
                [5] TABLERO KANBAN DEL USUARIO
                    │
                    ├── Pendiente
                    │   └── [▶ Iniciar] → EnCurso (timer corre)
                    │
                    ├── EnCurso
                    │   ├── [⏸ Pausar] → Pausada
                    │   │   ├── Almuerzo / Descanso
                    │   │   ├── Interrupción
                    │   │   ├── Cambio de prioridad → selecciona nueva actividad
                    │   │   └── Otro
                    │   │
                    │   └── [✓ Finalizar] → si requiere_entregable?
                    │           ├── NO → Finalizada (FIN)
                    │           └── SÍ → Revision
                    │
                    ├── Pausada
                    │   ├── [▶ Reanudar] → EnCurso
                    │   ├── [✓ Finalizar] → ver EnCurso
                    │   └── [↗ Trasladar] → envía a otro usuario
                    │
                    ├── Revision (si requiere_entregable=True)
                    │   ├── [✓ Aprobar] Admin/Master → Finalizada (FIN)
                    │   └── [✗ Rechazar] Admin/Master → Pendiente (prorroga+1)
                    │
                    └── Finalizada (FIN)
```

### 1.1 Traslado entre usuarios

```
Usuario A → [↗ Trasladar] → Usuario B
    │
    ├── Selecciona usuario destino
    ├── Opcional: selecciona actividad de reemplazo
    └── Motivo (opcional)
          │
          ▼
    Usuario B recibe notificación en tiempo real (WebSocket)
          │
          ├── [Aceptar] → A pasa a Trasladada, B recibe AsignacionActividad
          │                Si había reemplazo → se crea para A
          │
          └── [Rechazar] → Traslado cancelado, A mantiene su actividad
```

### 1.2 Tiempo de Inactividad

```
Cuando usuario NO tiene actividad EnCurso:
    └── Se crea automáticamente TiempoInactividad
        ├── Inicio = último evento conocido
        └── Fin = cuando retoma actividad (EnCurso)
```

---

## 2. Flujo Proyecto (Gestión Ágil)

```
Master/Admin
    │
    ├── [1] Crear Proyecto
    │       ├── código (PRJ-0001)
    │       ├── nombre, descripción, objetivo
    │       ├── area, subarea
    │       ├── manager (líder)
    │       └── fechas (inicio, fin estimada)
    │
    ├── [2] Asignar Equipo
    │       └── /proyectos/<pk>/equipo/
    │           ├── Líder
    │           ├── Responsable
    │           ├── Revisor / QA
    │           ├── Aprobador
    │           ├── Ejecutor
    │           └── Observador
    │
    ├── [3] Crear Backlog (Historias de Usuario)
    │       /proyectos/<pk>/backlog/
    │       ├── título + descripción + criterios de aceptación
    │       ├── prioridad (Must/Should/Could/Won't)
    │       ├── story points (Fibonacci: 1,2,3,5,8,13,21)
    │       └── orden drag & drop (SortableJS)
    │
    ├── [4] Crear Sprint
    │       /proyectos/<pk>/sprints/crear/
    │       ├── nombre, objetivo
    │       ├── fechas de inicio y fin
    │       └── seleccionar historias del backlog
    │
    ├── [5] Crear Tareas (asignar a miembros)
    │       /proyectos/<pk>/tareas/crear/
    │       ├── título, tipo (tarea/bug/mejora/docs/prueba/diseño)
    │       ├── asignado a → usuario del equipo
    │       ├── historia (opcional, para agrupar)
    │       ├── sprint (opcional)
    │       └── actividad del catálogo (opcional)
    │
    ├── [6] ACTIVAR Tarea (automático si se asigna usuario)
    │       └── crear_asignacion_desde_tarea()
    │           └── Crea AsignacionActividad (Pendiente)
    │                   │
    │                   ▼
    │               TABLERO KANBAN DEL USUARIO
    │               (mismo tablero que planificación)
    │
    ├── [7] Seguimiento en Sprint Board
    │       /proyectos/<pk>/sprints/<spk>/
    │       └── Kanban: Pendientes | En Curso | Finalizadas
    │
    ├── [8] Cierre de Sprint
    │       /proyectos/<pk>/sprints/<spk>/finalizar/
    │       ├── Historias completadas (revision/done) → done
    │       ├── Historias incompletas → vuelven al backlog
    │       └── RegistroAvance: velocidad calculada
    │
    └── [9] Incidencias
            /proyectos/<pk>/incidencias/crear/
            ├── tipo (bug/mejora/pregunta/riesgo)
            ├── severidad (crítica/alta/media/baja)
            ├── asignado a
            └── [Opcional] convertir a Tarea → genera AsignacionActividad

```

### 2.1 Flujo de Estados de Historia

```
backlog → sprint_backlog → en_progreso → revision → done
    ↑                          ↓                  ↑
    └──────────────────────────┘                  │
      (si vuelve al backlog)                      │
                                                   └── solo vía "Aprobar"
```

**Transiciones válidas**:
| Desde | Hacia |
|-------|-------|
| backlog | sprint_backlog |
| sprint_backlog | en_progreso, backlog |
| en_progreso | revision, backlog, sprint_backlog |
| revision | done, en_progreso |
| done | backlog |

### 2.2 Flujo de Estados de Tarea

```
pendiente → en_curso → finalizada (FIN)
    │           │
    │           └→ pausada → en_curso → finalizada (FIN)
    │
    └→ cancelada (FIN)
              │
              └→ revision → finalizada (FIN)
                          → pendiente (si rechazada)
```

### 2.3 Flujo de Estados de Incidencia

```
abierta → triaged → en_progreso → resuelta → cerrada (FIN)
   ↑         │           │            │
   │         └→ cerrada  └→ cerrada   └→ en_progreso (reabrir)
   │                                                   
   └→ duplicada → abierta (reabrir)
```

---

## 3. Enlace entre Planificación y Proyecto

### 3.1 Planificación → Proyecto (opcional)

```
Planificación
    ├── sin proyecto → funciona exactamente como antes
    │                    genera solo AsignacionActividad
    │
    └── CON proyecto vinculado
            │
            └── Por cada par (actividad × usuario):
                    ├── AsignacionActividad (aparece en tablero)  
                    └── Tarea (vinculada al proyecto)
                            ├── Título = nombre de la actividad
                            ├── Asignado a = usuario
                            ├── Actividad catálogo = actividad
                            └── Badge [PRJ-XXXX] en la card del tablero
```

### 3.2 Proyecto → Planificación (tarea genera trabajo)

```
Tarea de Proyecto
    └── asignado_a = usuario + creada
            │
            └── crear_asignacion_desde_tarea()
                    │
                    └── Crea AsignacionActividad
                            ├── user = tarea.asignado_a
                            ├── actividad = tarea.actividad_catalogo (o genérica)
                            ├── estado = Pendiente
                            ├── origen = "Proyecto"
                            ├── nombre_actividad = tarea.titulo
                            └── tarea.asignacion = asignacion (OneToOne)
                                    │
                                    ▼
                              TABLERO KANBAN
```

### 3.3 Sincronización Bidireccional

```
TABLERO (AsignacionActividad)          PROYECTO (Tarea)
─────────────────────────────          ────────────────
    usuario inicia           ─────→    tarea.estado = "en_curso"
                                                          
    usuario finaliza          ─────→    tarea.estado = "finalizada"
                                        historia.estado = "revision" (si todas las tareas)
                                                          
    usuario finaliza         ─────→    tarea.estado = "revision"
    (entregable)                         (espera aprobación)
                                                          
    Admin aprueba            ─────→    tarea.estado = "finalizada"
    (en /admin/revisiones/)              
                                                          
    Admin rechaza            ─────→    tarea.estado = "pendiente"
    (en /admin/revisiones/)             vuelve a planificadas
```

**Implementación**: Señal `post_save` en `AsignacionActividad` → `sync_tarea_from_asignacion` en `apps/proyectos/signals.py`

---

## 4. Puntos de Intervención (Aprobaciones/Rechazos)

### 4.1 Revisión de Entregable (Productividad)

```
Usuario finaliza actividad con requiere_entregable=True
    → estado = "Revision"
    → Sube archivo entregable
          │
          ▼
    Admin/Master ve en /admin/revisiones/
          │
          ├── [✓ Aprobar]
          │       → AsignacionActividad = "Finalizada"
          │       → Tarea (si existe) = "finalizada"
          │       → Historia (si aplica) = actualizar_estado()
          │       → RevisionHistorial registra aprobación
          │
          └── [✗ Rechazar] (motivo obligatorio)
                  → AsignacionActividad = "Pendiente"
                  → prorroga_count += 1
                  → Tarea (si existe) = "pendiente"
                  → RevisionHistorial registra rechazo
                  → Badge rojo 🔴 en card del tablero
                  → Usuario corrige y vuelve a finalizar
```

### 4.2 Aprobación de Historia (Proyecto)

```
Historia en estado "revision" (todas las tareas finalizadas)
    │
    ▼
    Líder / Responsable / Aprobador
    en /proyectos/<pk>/backlog/
    │
    ├── [✓ Aprobar] → historia.estado = "done" (FIN)
    │
    └── Falta botón de Rechazar (pendiente)
```

### 4.3 Aprobación de Tarea (Proyecto)

```
Si la tarea usa actividad con requiere_entregable=True:
    → La tarea va a "revision" (via sync desde AsignacionActividad)
    → Admin/Master aprueba/rechaza en /admin/revisiones/
    → La tarea se sincroniza automáticamente (via señal)
```

### 4.4 Aceptación/Rechazo de Traslado

```
Usuario A envía traslado a Usuario B
    │
    ▼
    Usuario B recibe notificación WebSocket
    │
    ├── [Aceptar]
    │       → Actividad de A: "Trasladada"
    │       → Nueva AsignacionActividad para B: "EnCurso" o "Pendiente"
    │       → Si hay reemplazo: se crea para A
    │       → Se notifica a A que el traslado fue aceptado
    │
    └── [Rechazar]
            → Traslado: "Rechazado"
            → A mantiene su actividad
            → Se notifica a A que el traslado fue rechazado
```

---

## 5. Matriz de Roles y Acciones

### 5.1 Roles del Sistema (globales)

| Rol | Acceso | Descripción |
|-----|--------|-------------|
| **Master** | TODO | Super-admin. Ve todos los proyectos, usuarios, áreas. |
| **Admin** | Subareas asignadas | CRUD de su subarea. Ve proyectos de su subarea. |
| **Usuario** | Solo su tablero | Solo ve AsignacionActividad de su user. NO ve proyectos. |

### 5.2 Roles de Proyecto (MiembroProyecto)

| Rol en Proyecto | Ver | Crear/Editar | Aprobar | Gestionar Equipo |
|----------------|-----|-------------|---------|-----------------|
| **Líder** | ✅ Todo | ✅ Todo | ✅ Historias, Tareas | ✅ |
| **Responsable** | ✅ Todo | ✅ Todo | ✅ Historias, Tareas | ✅ |
| **Revisor / QA** | ✅ Todo | ❌ | ✅ Historias | ❌ |
| **Aprobador** | ✅ Todo | ❌ | ✅ Historias | ❌ |
| **Ejecutor** | ✅ Todo | ✅ Tareas propias | ❌ | ❌ |
| **Observador** | ✅ Todo (solo lectura) | ❌ | ❌ | ❌ |

### 5.3 Perímetros de Acceso

```
SIN autenticar → login
    │
    ├── Usuario normal → solo su Tablero, Perfil, Calendario
    │                    NO ve /proyectos/
    │
    ├── Miembro de proyecto → ve /proyectos/<su-proyecto>/
    │   └── Solo ve los proyectos donde tiene membresía
    │
    ├── Admin → ve /proyectos/ de sus subareas
    │   └── Sin membresía → acceso completo como admin
    │
    └── Master → ve TODOS los proyectos
        └── Sin restricciones
```

---

## 6. Vista por Rol

### 6.1 Ejecutor

```
Vista:
    /proyectos/<pk>/  → Dashboard con KPIs
    /backlog/         → Ver backlog (no puede crear historias)
    /sprints/         → Ver sprint board, su board de tareas
    /tareas/          → Ver tareas, crear tareas propias
    /incidencias/     → Reportar incidencias
    /equipo/          → Ver equipo (no gestionar)

    /usuario/tablero/ → Su tablero Kanban con tareas de proyecto
```

### 6.2 Revisor / QA

```
Vista: Igual que Ejecutor, PERO:
    /backlog/         → Botón "Aprobar" en historias en "revision"
    NO puede crear tareas
    NO puede gestionar equipo
    
    /admin/revisiones/ → Lista de revisiones pendientes
```

### 6.3 Líder / Responsable

```
Vista: ACCESO COMPLETO
    /proyectos/<pk>/backlog/      → Crear historias, aprobar
    /proyectos/<pk>/equipo/       → Agregar/remover miembros
    /proyectos/<pk>/sprints/      → Crear, finalizar sprints
    /proyectos/<pk>/editar/       → Editar proyecto, cambiar estado
```

---

## 7. Resumen del Ciclo Completo

### 7.1 Ciclo Planificación (Productividad)

```
[1] Crear TipoActividad (Admin/Master)
    └── [2] Crear Actividad
        └── [3] Crear Planificación
            └── [4] AsignacionActividad → Tablero
                ├── [5] Usuario Inicia → EnCurso
                ├── [6] Usuario Pausa → Pausada
                ├── [7] Usuario Finaliza
                │       ├── Sin entregable → Finalizada ✓
                │       └── Con entregable → Revision
                │               ├── Admin Aprueba → Finalizada ✓
                │               └── Admin Rechaza → Pendiente ↻
                ├── [8] Usuario Traslada → Otro usuario
                └── [9] Usuario Finaliza (corregido) → va a revision
                    └── Admin Aprueba → Finalizada ✓
```

### 7.2 Ciclo Proyecto (Gestión Ágil)

```
[1] Crear Proyecto (Master/Admin)
    ├── [2] Asignar Equipo
    │       └── Definir roles
    │
    ├── [3] Backlog → Historias de Usuario
    │       └── Priorizar (MoSCoW + Story Points)
    │
    ├── [4] Sprint Planning
    │       └── Seleccionar historias del backlog
    │
    ├── [5] Descomponer en Tareas
    │       └── Asignar a miembros del equipo
    │
    ├── [6] Activación → AsignacionActividad → TABLERO
    │
    ├── [7] TABLERO (igual que planificación)
    │       └── Usuario trabaja: Iniciar/Pausar/Finalizar
    │
    ├── [8] Revisión y Aprobaciones
    │       ├── Tarea con entregable → /admin/revisiones/
    │       ├── Historia "revision" → Aprobador ✓
    │       └── Sprint Review → Líder cierra sprint
    │
    └── [9] Cierre de Sprint
            ├── Historias completadas → Done
            ├── Incompletas → Backlog
            ├── Velocidad calculada
            └── RegistroAvance guardado
```

### 7.3 Puntos de Enlace Planificación ↔ Proyecto

```
PLANIFICACIÓN                          PROYECTO
══════════════                          ════════
Actividad (catálogo)  ←──── usado por → Tarea.actividad_catalogo
                    ───── crea ─────→  Tarea (si proyecto vinculado)
AsignacionActividad  ←──── señal ───→  Tarea.estado sync
                    ───── badge ────→  Card tablero con [PRJ-XXXX]
Planificacion.proyecto_id  ──── FK →  Proyecto.pk
```

### 7.4 Notificaciones en Tiempo Real

```
Evento                              Destino
────────────────────────────────────────────────────
Nuevo traslado (enviado a otro)     Destinatario recibe toast + actualiza sección
Traslado aceptado/rechazado         Originador recibe notificación + recarga
Nueva asignación (planificación)    Usuario recibe toast + recarga tablero
Revisión aprobada/rechazada         Usuario recibe notificación + recarga
```

---

## Diagrama Visual Simplificado

```
                    ┌──────────────────────────────────────────────────┐
                    │              CATÁLOGO (TipoActividad/Actividad)   │
                    └────────────┬────────────────────┬────────────────┘
                                 │                    │
                   ┌─────────────▼──────┐    ┌─────────▼──────────┐
                   │   PLANIFICACIÓN    │    │     PROYECTO       │
                   │                    │    │                    │
                   │  Actividades ×      │    │  Backlog → Sprint  │
                   │  Usuarios          │    │  → Tareas          │
                   │  Fechas            │    │  → Miembros        │
                   └──────────┬─────────┘    └──────────┬──────────┘
                              │                         │
                              │   ┌─────────────────┐   │
                              │   │ FK opcional     │   │
                              └──→│ proyecto         │←──┘
                                  └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌──────────────────────────────────────────┐
                    │        AsignacionActividad               │
                    │        (MOTOR ÚNICO)                      │
                    │                                          │
                    │  Pendiente → EnCurso → Pausada            │
                    │  → Finalizada / Revision                  │
                    └──────────────────┬───────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  TABLERO KANBAN  │
                              │  (Usuario Final) │
                              └─────────────────┘
```

**Regla de oro**: El usuario SIEMPRE trabaja en su Tablero Kanban. No importa si la tarea vino de planificación o de proyecto. El flujo de trabajo es idéntico.
