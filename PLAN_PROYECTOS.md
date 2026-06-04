# Plan de Acoplamiento · Gestión de Proyectos Ágil + Productividad

## Visión General

VIVA1A opera con **dos caras de una misma moneda**, unidas por un único motor de trabajo:

```
                    ┌─────────────────────────┐
                    │   AsignacionActividad   │  ← MOTOR ÚNICO
                    │   (Pendiente→EnCurso→   │
                    │   Pausada→Finalizada/   │
                    │   Revision→...)         │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
   │ Planificacion│    │   Proyecto   │    │  No Programada   │
   │ (lote masivo)│    │  (ágil)      │    │  (flash/evento)  │
   └──────────────┘    └──────────────┘    └──────────────────┘
```

**Regla de oro**: El usuario trabaja SIEMPRE en su Tablero Kanban. No importa si la tarea vino de una planificación, de un sprint de proyecto, o la creó manualmente. El flujo es idéntico: Iniciar → Pausar → Finalizar → (Revision si entregable).

---

## 1. Lo que YA existe (y NO se toca)

```
APPS EXISTENTES                    FLUJO QUE PERMANECE INTACTO
─────────────────────────         ─────────────────────────────
apps/accounts/                    · Login, roles, usuarios, empresas
apps/estructura/                  · Áreas, SubÁreas, UserSubArea
apps/actividades/                 · Catálogo: TipoActividad + Actividad
apps/planificacion/               · Planificación masiva × usuarios
apps/gestion/                     · Tablero Kanban, tiempos, traslados, revisiones, comentarios
apps/dashboard/                   · KPIs, progreso, línea de tiempo, inactividad
apps/reportes/                    · Export Excel (4 sheets)
```

### Catálogo de Actividades (la base reutilizada)

```
TipoActividad                     Actividad
├── nombre                       ├── nombre
├── requiere_fecha_limite        ├── subarea (FK)
├── requiere_entregable          └── tipo_actividad (FK)
├── es_flash
└── subarea (FK)
```

Estos flags YA controlan el comportamiento en el Tablero:
- `requiere_fecha_limite=True` → se muestra fecha de vencimiento, badge de "Vence en Xd", filtro de vencidas
- `requiere_entregable=True` → al Finalizar pide archivo, va a estado "Revision", no se puede Trasladar
- `es_flash=True` → aparece en modales de Pausa/Finalizar como actividad de reemplazo

**El proyecto reutiliza TODO esto sin modificarlo.**

---

## 2. Modelos Nuevos (`apps/proyectos/`)

### 2.1 `Proyecto`

```python
class Proyecto(models.Model):
    ESTADOS = [
        ("activo", "Activo"),
        ("pausado", "Pausado"),
        ("finalizado", "Finalizado"),
        ("cancelado", "Cancelado"),
    ]
    codigo = CharField(max_length=8, unique=True)     # PRJ-0001 (auto-generado)
    nombre = CharField(max_length=300)
    descripcion = TextField(blank=True)
    objetivo = TextField(blank=True)

    # Alcance organizacional (hereda de estructura existente)
    area = FK("estructura.Area", PROTECT, related_name="proyectos")
    subarea = FK("estructura.SubArea", PROTECT, related_name="proyectos")

    # Gestión
    manager = FK(User, PROTECT, related_name="proyectos_gestionados")
    estado = CharField(max_length=20, choices=ESTADOS, default="activo")

    # Fechas
    fecha_inicio = DateField(null=True, blank=True)
    fecha_fin_estimada = DateField(null=True, blank=True)
    fecha_fin_real = DateField(null=True, blank=True)

    activo = BooleanField(default=True)
    fecha_creacion = DateTimeField(auto_now_add=True)
    fecha_update = DateTimeField(auto_now=True)

    class Meta:
        db_table = "proyecto"
        ordering = ["-fecha_creacion"]

    @property
    def avance_porcentaje(self):
        """Calculado: tareas finalizadas / tareas totales * 100"""
        total = self.tareas.filter(activo=True).count()
        if total == 0: return 0
        finalizadas = self.tareas.filter(activo=True, estado="finalizada").count()
        return int(finalizadas / total * 100)

    @property
    def tareas_pendientes(self):
        return self.tareas.filter(activo=True, estado__in=["pendiente"]).count()

    @property
    def tareas_en_curso(self):
        return self.tareas.filter(activo=True, estado__in=["en_curso", "pausada"]).count()

    @property
    def tareas_finalizadas(self):
        return self.tareas.filter(activo=True, estado="finalizada").count()
```

### 2.2 `MiembroProyecto`

```python
class MiembroProyecto(models.Model):
    ROLES = [
        ("manager", "Project Manager"),
        ("product_owner", "Product Owner"),
        ("scrum_master", "Scrum Master"),
        ("developer", "Developer"),
        ("tester", "QA / Tester"),
        ("viewer", "Observador"),
    ]
    proyecto = FK(Proyecto, CASCADE, related_name="membresias")
    user = FK(User, CASCADE, related_name="proyectos_miembro")
    rol = CharField(max_length=20, choices=ROLES, default="developer")
    activo = BooleanField(default=True)
    fecha_ingreso = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "miembro_proyecto"
        unique_together = ["proyecto", "user"]
```

### 2.3 `Etiqueta`

```python
class Etiqueta(models.Model):
    proyecto = FK(Proyecto, CASCADE, related_name="etiquetas")
    nombre = CharField(max_length=50)
    color = CharField(max_length=7, default="#6b7280")
    activo = BooleanField(default=True)

    class Meta:
        db_table = "etiqueta"
        unique_together = ["proyecto", "nombre"]
```

### 2.4 `Sprint` (Iteración)

```python
class Sprint(models.Model):
    ESTADOS = [
        ("planificado", "Planificado"),
        ("activo", "Activo"),
        ("finalizado", "Finalizado"),
    ]
    proyecto = FK(Proyecto, CASCADE, related_name="sprints")
    nombre = CharField(max_length=200)
    objetivo = TextField(blank=True)
    estado = CharField(max_length=20, choices=ESTADOS, default="planificado")
    numero = IntegerField()

    fecha_inicio = DateField(null=True, blank=True)
    fecha_fin = DateField(null=True, blank=True)

    activo = BooleanField(default=True)
    fecha_creacion = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sprint"
        ordering = ["proyecto", "numero"]
        unique_together = ["proyecto", "numero"]

    @property
    def velocidad(self):
        """Story points completados en este sprint"""
        return self.historias.filter(estado="done").aggregate(
            total=Sum("puntos_historia")
        )["total"] or 0

    @property
    def puntos_comprometidos(self):
        return self.historias.filter(activo=True).aggregate(
            total=Sum("puntos_historia")
        )["total"] or 0
```

### 2.5 `HistoriaUsuario` (User Story)

```python
class HistoriaUsuario(models.Model):
    ESTADOS = [
        ("backlog", "Backlog"),
        ("sprint_backlog", "Sprint Backlog"),
        ("en_progreso", "En Progreso"),
        ("revision", "En Revisión"),
        ("done", "Done"),
    ]
    PRIORIDADES = [                                     # MoSCoW
        ("must", "Must Have"),
        ("should", "Should Have"),
        ("could", "Could Have"),
        ("wont", "Won't Have"),
    ]

    proyecto = FK(Proyecto, CASCADE, related_name="historias")
    sprint = FK(Sprint, SET_NULL, null=True, blank=True, related_name="historias")
    etiquetas = M2M(Etiqueta, blank=True)

    codigo = CharField(max_length=16, unique=True)      # PRJ-0001-US-001
    titulo = CharField(max_length=300)
    descripcion = TextField(blank=True)
    criterios_aceptacion = TextField(blank=True)

    prioridad = CharField(max_length=10, choices=PRIORIDADES, default="should")
    puntos_historia = IntegerField(default=0)
    estado = CharField(max_length=20, choices=ESTADOS, default="backlog")
    orden = IntegerField(default=0)                     # posición en backlog (drag & drop)

    creador = FK(User, PROTECT, related_name="historias_creadas")

    activo = BooleanField(default=True)
    fecha_creacion = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historia_usuario"
        ordering = ["proyecto", "orden", "-fecha_creacion"]

    def actualizar_estado_por_tareas(self):
        """El estado de la historia se deriva del estado de sus tareas"""
        tareas = self.tareas.filter(activo=True)
        if not tareas.exists():
            return
        estados = set(tareas.values_list("estado", flat=True))
        if estados == {"finalizada"}:
            self.estado = "revision"
        elif "en_curso" in estados or "pausada" in estados:
            self.estado = "en_progreso"
        elif "pendiente" in estados and "finalizada" in estados:
            self.estado = "en_progreso"
        elif estados == {"pendiente"}:
            self.estado = "sprint_backlog" if self.sprint else "backlog"
        self.save(update_fields=["estado"])
```

### 2.6 `Tarea` — EL PUNTO DE ACOPLAMIENTO

```python
class Tarea(models.Model):
    TIPOS = [
        ("tarea", "Tarea"),
        ("bug", "Bug"),
        ("mejora", "Mejora"),
        ("documentacion", "Documentación"),
        ("prueba", "Prueba"),
        ("diseno", "Diseño"),
        ("reunion", "Reunión"),
    ]
    # ── MISMO CICLO DE VIDA QUE AsignacionActividad ──
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("en_curso", "En Curso"),
        ("pausada", "Pausada"),
        ("finalizada", "Finalizada"),
        ("revision", "En Revisión"),     # ⬅ refleja estado Revision de AsignacionActividad
        ("cancelada", "Cancelada"),
    ]

    proyecto = FK(Proyecto, CASCADE, related_name="tareas")
    historia = FK(HistoriaUsuario, CASCADE, null=True, blank=True, related_name="tareas")
    sprint = FK(Sprint, SET_NULL, null=True, blank=True, related_name="tareas")
    etiquetas = M2M(Etiqueta, blank=True)
    bloqueada_por = M2M("self", symmetrical=False, blank=True, related_name="bloquea_a")

    # ── ACOPLAMIENTO: vínculo 1:1 con el motor de trabajo ──
    asignacion = models.OneToOneField(
        "gestion.AsignacionActividad", SET_NULL, null=True, blank=True,
        related_name="tarea_proyecto"
    )
    # Catálogo de actividad (reutiliza el existente). Si es null, se usa
    # una actividad genérica "Tarea de Proyecto" del proyecto.
    actividad_catalogo = FK("actividades.Actividad", PROTECT, null=True, blank=True,
                            related_name="tareas_proyecto")

    codigo = CharField(max_length=16, unique=True)      # PRJ-0001-T-001
    titulo = CharField(max_length=300)
    descripcion = TextField(blank=True)
    tipo = CharField(max_length=20, choices=TIPOS, default="tarea")
    estado = CharField(max_length=20, choices=ESTADOS, default="pendiente")

    asignado_a = FK(User, PROTECT, null=True, blank=True, related_name="tareas_asignadas")
    creador = FK(User, PROTECT, related_name="tareas_creadas")
    estimacion_horas = DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)

    activo = BooleanField(default=True)
    fecha_creacion = DateTimeField(auto_now_add=True)
    fecha_update = DateTimeField(auto_now=True)

    class Meta:
        db_table = "tarea"
        ordering = ["proyecto", "sprint", "historia__orden", "fecha_creacion"]
```

### 2.7 `Incidencia` (Issue / Bug Tracker)

```python
class Incidencia(models.Model):
    TIPOS = [
        ("bug", "Bug"),
        ("mejora", "Mejora"),
        ("pregunta", "Pregunta / Soporte"),
        ("riesgo", "Riesgo"),
        ("bloqueo", "Bloqueo"),
    ]
    SEVERIDAD = [
        ("critica", "Crítica — Bloquea trabajo"),
        ("alta", "Alta — Impacto mayor"),
        ("media", "Media — Impacto moderado"),
        ("baja", "Baja — Cosmético / Menor"),
    ]
    ESTADOS = [
        ("abierta", "Abierta"),
        ("triaged", "En Triage"),
        ("en_progreso", "En Progreso"),
        ("resuelta", "Resuelta"),
        ("cerrada", "Cerrada"),
        ("duplicada", "Duplicada"),
    ]

    proyecto = FK(Proyecto, CASCADE, related_name="incidencias")
    etiquetas = M2M(Etiqueta, blank=True)

    # Vínculos de trazabilidad
    tarea = FK(Tarea, SET_NULL, null=True, blank=True, related_name="incidencias")
    historia = FK(HistoriaUsuario, SET_NULL, null=True, blank=True,
                  related_name="incidencias")
    asignacion = models.OneToOneField(
        "gestion.AsignacionActividad", SET_NULL, null=True, blank=True,
        related_name="incidencia"
    )

    codigo = CharField(max_length=16, unique=True)      # PRJ-0001-INC-001
    titulo = CharField(max_length=300)
    descripcion = TextField(blank=True)
    pasos_reproducir = TextField(blank=True)

    tipo = CharField(max_length=20, choices=TIPOS, default="bug")
    severidad = CharField(max_length=10, choices=SEVERIDAD, default="media")
    estado = CharField(max_length=20, choices=ESTADOS, default="abierta")

    reportado_por = FK(User, PROTECT, related_name="incidencias_reportadas")
    asignado_a = FK(User, SET_NULL, null=True, blank=True,
                    related_name="incidencias_asignadas")

    activo = BooleanField(default=True)
    fecha_creacion = DateTimeField(auto_now_add=True)
    fecha_resolucion = DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "incidencia"
        ordering = ["-fecha_creacion"]
```

### 2.8 `ComentarioIncidencia`

```python
class ComentarioIncidencia(models.Model):
    incidencia = FK(Incidencia, CASCADE, related_name="comentarios")
    user = FK(User, PROTECT, related_name="comentarios_incidencias")
    texto = TextField()
    fecha = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comentario_incidencia"
        ordering = ["fecha"]
```

### 2.9 `RegistroAvance` (Bitácora de eventos del proyecto)

```python
class RegistroAvance(models.Model):
    TIPOS = [
        ("historia_completada", "Historia completada"),
        ("sprint_iniciado", "Sprint iniciado"),
        ("sprint_finalizado", "Sprint finalizado"),
        ("incidencia_resuelta", "Incidencia resuelta"),
        ("comentario", "Comentario"),
        ("bloqueo", "Bloqueo reportado"),
    ]
    proyecto = FK(Proyecto, CASCADE, related_name="avances")
    tipo = CharField(max_length=30, choices=TIPOS)
    descripcion = TextField()
    user = FK(User, PROTECT)
    referencia_id = IntegerField(null=True, blank=True)

    fecha = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "registro_avance"
        ordering = ["-fecha"]
```

---

## 3. Extensión Mínima a Modelos Existentes

### 3.1 `Planificacion` — FK opcional a Proyecto

```python
# apps/planificacion/models.py — AÑADIR:
proyecto = FK("proyectos.Proyecto", SET_NULL, null=True, blank=True,
              related_name="planificaciones",
              help_text="Vincula esta planificación a un proyecto")
```
**Si es null** → la planificación funciona exactamente como ahora.
**Si está seteado** → la planificación aparece en el dashboard del proyecto, y opcionalmente las `AsignacionActividad` generadas pueden crear `Tarea` records asociados.

### 3.2 `AsignacionActividad` — sin cambios estructurales

El modelo YA tiene todos los campos necesarios: `estado`, `user`, `actividad`, `planificacion_detalle`, `origen`, `nombre_actividad`, `nombre_tipo`, `entregable`, `estado_revision`, `prorroga_count`.

Lo ÚNICO nuevo es que `Tarea` y `Incidencia` pueden tener un `OneToOneField` apuntando a ella (`tarea_proyecto` e `incidencia` como related_name).

---

## 4. El Motor de Sincronización: Tarea ↔ AsignacionActividad

Este es el corazón del acoplamiento. Se implementa vía **señales Django** para mantener ambos lados sincronizados sin tocar ninguna vista existente.

### 4.1 Creación de AsignacionActividad desde Tarea

```python
# apps/proyectos/signals.py

def crear_asignacion_desde_tarea(tarea, user_creador):
    """Crea una AsignacionActividad para una Tarea de proyecto.
       Se llama cuando la tarea se asigna a un usuario y el sprint está activo."""

    if tarea.asignacion:
        return tarea.asignacion  # ya existe

    if not tarea.asignado_a:
        return None  # sin usuario asignado

    # Determinar la Actividad del catálogo
    actividad = tarea.actividad_catalogo
    if not actividad:
        actividad = _get_or_create_actividad_generica(tarea.proyecto)

    # Congelar nombres como lo hace Planificacion
    asignacion = AsignacionActividad.objects.create(
        user=tarea.asignado_a,
        actividad=actividad,
        estado="Pendiente",
        origen="Proyecto",
        origen_user=user_creador,
        nombre_actividad=tarea.titulo,
        nombre_tipo=actividad.tipo_actividad.nombre,
        planificacion_detalle=None,    # no viene de planificación
    )
    tarea.asignacion = asignacion
    tarea.save(update_fields=["asignacion"])
    return asignacion


def _get_or_create_actividad_generica(proyecto):
    """Obtiene o crea una Actividad genérica 'Tarea de Proyecto' para el proyecto."""
    from apps.actividades.models import TipoActividad, Actividad

    tipo, _ = TipoActividad.objects.get_or_create(
        subarea=proyecto.subarea,
        nombre="Tarea de Proyecto",
        defaults={
            "descripcion": f"Actividad genérica para tareas del proyecto {proyecto.codigo}",
            "requiere_fecha_limite": False,
            "requiere_entregable": False,
            "es_flash": False,
        }
    )
    actividad, _ = Actividad.objects.get_or_create(
        subarea=proyecto.subarea,
        tipo_actividad=tipo,
        nombre=f"Tarea de Proyecto - {proyecto.codigo}",
    )
    return actividad
```

### 4.2 Sincronización de Estado (Señal)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=AsignacionActividad)
def sync_tarea_from_asignacion(sender, instance, created, **kwargs):
    """Cuando una AsignacionActividad cambia de estado, reflejarlo en la Tarea."""
    if not created and hasattr(instance, 'tarea_proyecto') and instance.tarea_proyecto:
        tarea = instance.tarea_proyecto
        # Mapear estado (incluye Revision → revision)
        if instance.estado == "Revision":
            tarea.estado = "revision"
        else:
            tarea.estado = instance.estado.lower() if instance.estado != "EnCurso" else "en_curso"
        tarea.save(update_fields=["estado"])

        # Actualizar estado de la HistoriaUsuario padre
        if tarea.historia:
            tarea.historia.actualizar_estado_por_tareas()

        # Si se finalizó, registrar avance y recalcular % proyecto
        if instance.estado == "Finalizada":
            RegistroAvance.objects.create(
                proyecto=tarea.proyecto,
                tipo="historia_completada" if tarea.historia and tarea.historia.tareas.filter(
                    activo=True).exclude(estado="finalizada").count() == 0 else "comentario",
                descripcion=f"Tarea '{tarea.titulo}' finalizada por {instance.user.get_full_name()}",
                user=instance.user,
                referencia_id=tarea.pk
            )
```

### 4.3 Flujo de Revision INTEGRADO con Proyectos

Cuando una Tarea del proyecto está vinculada a una Actividad con `requiere_entregable=True`:

```
1. Usuario trabaja la tarea en su Tablero (igual que siempre)
2. Usuario hace clic en Finalizar
3. Como la actividad requiere entregable → modal pide archivo + comentario
4. AsignacionActividad pasa a estado="Revision"
5. SEÑAL sync_tarea_from_asignacion → Tarea.estado = "revision"
6. Admin/PM ve la tarea en /proyectos/<pk>/ → badge "En Revisión"
7. Admin revisa en /admin/revisiones/ (flujo existente)
8a. APRUEBA → AsignacionActividad a "Finalizada", estado_revision="aprobado"
    → SEÑAL → Tarea.estado = "finalizada"
    → HistoriaUsuario.actualizar_estado_por_tareas()
    → RegistroAvance: "Historia completada" (si todas las tareas de la historia están done)

8b. RECHAZA → AsignacionActividad a "Pendiente", estado_revision="rechazado"
    → prorroga_count += 1
    → RevisionHistorial registra el rechazo con comentario obligatorio
    → SEÑAL → Tarea.estado = "pendiente" (la tarea vuelve a estar pendiente)
    → El usuario ve en su Tablero: badge rojo 🔴 con comentarios de revisión
    → El PM ve en el proyecto: la tarea volvió a "Pendiente"
```

**El flujo de Revision NO CAMBIA.** Solo se agrega la sincronización bidireccional vía señal.

---

## 5. Flujo Completo de Principio a Fin

```
FASE 0: CATÁLOGO (existente, sin cambios)
──────────────────────────────────────────
Admin crea TipoActividad "Desarrollo" con flags:
  - requiere_entregable = True
  - requiere_fecha_limite = True

Admin crea Actividad "API REST" vinculada al TipoActividad "Desarrollo"
  └── subarea: Aplicaciones Corporativas

FASE 1: PROYECTO (nuevo)
─────────────────────────
Manager crea Proyecto "Portal de Clientes"
  ├── Area: Tecnologia
  ├── SubArea: Aplicaciones Corporativas
  ├── Manager: Angie
  └── Miembros: Cynthia (dev), Jerson (dev), Valentina (QA)

FASE 2: BACKLOG (nuevo)
────────────────────────
PO/Manager crea HistoriasUsuario en el backlog:

  US-001 "Ver facturas"     Must Have  8 pts
  US-002 "Pagar en línea"   Must Have  13 pts
  US-003 "Reportes admin"   Should Have  5 pts
  US-004 "Chat de soporte"  Could Have  3 pts

Backlog ordenado vía drag & drop.

FASE 3: SPRINT PLANNING (nuevo)
────────────────────────────────
Manager crea Sprint 1:
  ├── 2 semanas (1 Jun - 14 Jun)
  ├── Objetivo: "Módulo de facturación y pagos"
  └── Historias seleccionadas: US-001 (8) + US-002 (13) = 21 pts

Cada historia se descompone en Tareas:

  US-001 "Ver facturas" (8 pts)
  ├── T-001 "Diseñar UI"        → Cynthia,  Actividad="UI/UX"
  ├── T-002 "API facturas"      → Jerson,   Actividad="API REST"  ⬅ usa catálogo
  └── T-003 "Pruebas unitarias" → Valentina, Actividad="Testing"

  US-002 "Pagar en línea" (13 pts)
  ├── T-004 "Integración pasarela" → Jerson,   Actividad="API REST"  ⬅ requiere_entregable=True
  ├── T-005 "UI formulario pago"   → Cynthia,  Actividad="UI/UX"
  └── T-006 "Pruebas integración"  → Valentina, Actividad="Testing"

FASE 4: ACTIVACIÓN DE TAREAS (acoplamiento: nuevo → existente)
───────────────────────────────────────────────────────────────
Al iniciar el sprint, para cada Tarea asignada:

  T-001 → crea AsignacionActividad {
      user=Cynthia, actividad=UI/UX, estado="Pendiente",
      origen="Proyecto", nombre_actividad="Diseñar UI",
      nombre_tipo="UI/UX"
  }
  T-002 → crea AsignacionActividad {user=Jerson, ...}
  T-003 → crea AsignacionActividad {user=Valentina, ...}
  T-004 → crea AsignacionActividad {
      user=Jerson, actividad=API REST,   ⬅ requiere_entregable=True
      ...
  }
  T-005 → crea AsignacionActividad {user=Cynthia, ...}
  T-006 → crea AsignacionActividad {user=Valentina, ...}

FASE 5: TRABAJO DIARIO (existente, SIN cambios)
────────────────────────────────────────────────
USUARIO CYNTHIA ve su Tablero Kanban:

┌──────────────────────────────────────────────────────────────┐
│ PLANIFICADAS                                                 │
│ ┌────────────────────────────────────────────┐               │
│ │ UI/UX                    🔴 Proyecto X     │ ← badge sutil│
│ │ Diseñar UI                                 │               │
│ │ Tecnologia > Aplicaciones Corporativas     │               │
│ │ 01/06                      [▶] [↗] [👁]   │               │
│ └────────────────────────────────────────────┘               │
│ ┌────────────────────────────────────────────┐               │
│ │ UI/UX                    🔴 Proyecto X     │               │
│ │ UI formulario pago                         │               │
│ │ ...                          [▶] [↗] [👁]  │               │
│ └────────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────┘

Cynthia trabaja normalmente:
  · Inicia "Diseñar UI" → En Curso (timer corre)
  · Pausa → va a almorzar (TiempoInactividad trackea)
  · Reanuda → sigue trabajando
  · Finaliza → si no requiere entregable: Finalizada

FASE 6: REVISIÓN DE ENTREGABLE (existente, se refleja en proyecto)
───────────────────────────────────────────────────────────────────
Jerson trabaja T-004 "Integración pasarela" (Actividad="API REST" con requiere_entregable=True)

  1. Jerson finaliza → modal pide:
     · Comentario: "Integración completada con pruebas"
     · Archivo entregable: api_docs.pdf
  2. AsignacionActividad → estado="Revision", estado_revision="pendiente"
  3. SEÑAL → Tarea.estado = "revision"
  4. Admin ve en /admin/revisiones/:
     ┌────────────────────────────────────────────────────────┐
     │ Jerson | Integración pasarela | api_docs.pdf | Pendiente│
     │                                          [✓ Aprobar] [✗ Rechazar] │
     └────────────────────────────────────────────────────────┘

  CASO A: APROBADO
    5a. Admin hace clic en Aprobar (comentario opcional)
    6a. AsignacionActividad → estado="Finalizada", estado_revision="aprobado"
    7a. RevisionHistorial: {accion="aprobado", user=Admin, comentario="..."}
    8a. SEÑAL → Tarea.estado = "finalizada"
    9a. HistoriaUsuario.actualizar_estado_por_tareas()
    10a. Si todas las tareas de US-002 están finalizadas → US-002.estado = "revision"
    11a. PO revisa US-002, si OK → US-002.estado = "done"
    12a. Sprint.burndown refleja 13 pts completados

  CASO B: RECHAZADO
    5b. Admin hace clic en Rechazar → modal pide motivo (obligatorio)
    6b. Admin escribe: "Falta documentación de endpoints"
    7b. AsignacionActividad → estado="Pendiente", estado_revision="rechazado"
    8b. RevisionHistorial: {accion="rechazado", user=Admin, comentario="Falta..."}
    9b. prorroga_count += 1
    10b. SEÑAL → Tarea.estado = "pendiente"
    11b. Jerson ve en su Tablero la card de nuevo en Planificadas con:
        🔴 badge rojo "chat-dots 1" indicando que hay comentarios de revisión
    12b. Jerson abre detalle → ve el motivo del rechazo → corrige → vuelve a finalizar

FASE 7: INCIDENCIA (nuevo, parcialmente se convierte en trabajo existente)
──────────────────────────────────────────────────────────────────────────
Valentina (QA) encuentra un bug durante las pruebas:

  1. Crea Incidencia INC-001:
     · Título: "Error 500 al procesar pago con tarjeta débito"
     · Tipo: Bug, Severidad: Alta
     · Pasos: "1. Ir a pagos, 2. Seleccionar débito, 3. Confirmar → Error 500"

  2. PM hace triage: asigna a Jerson, estado → "en_progreso"

  3. Jerson determina que requiere código → convierte la incidencia en Tarea:
     · Crea T-007 vinculada a INC-001 y US-002
     · Al asignar a Jerson → crea AsignacionActividad (aparece en su Tablero)
     · INC-001.tarea = T-007

  4. Jerson trabaja T-007 en su Tablero (igual que cualquier tarea)

  5. Al finalizar T-007:
     · INC-001 pasa a "resuelta"
     · Valentina (QA) verifica → INC-001 pasa a "cerrada"
     · ComentarioIncidencia registra la resolución

FASE 8: CIERRE DE SPRINT (nuevo)
─────────────────────────────────
Manager finaliza Sprint 1:

  1. US-001: todas las tareas finalizadas, PO aceptó → Done (8 pts) ✓
  2. US-002: T-004 rechazada → pendiente. T-005 y T-006 finalizadas.
     → US-002 NO está done → vuelve al backlog o se mueve al siguiente sprint
  3. Velocidad del equipo: 8 pts (solo US-001 completada)

  4. Sprint Review:
     · Demo de US-001 funcional
     · US-002 se reprograma para Sprint 2

  5. Burndown chart muestra:
     · Ideal: línea recta de 21 a 0
     · Real: cayó a 13 (cuando T-001→T-003,T-005,T-006 finalizaron) y se estancó

FASE 9: REPORTES DE AVANCE (nuevo)
───────────────────────────────────
Dashboard del proyecto muestra:
  · % Avance general: tareas finalizadas / totales
  · Burndown del sprint activo
  · Cumulative Flow: backlog → en progreso → done
  · Velocidad histórica: [8 pts] [13 pts] [21 pts] ...
  · Incidencias: 2 abiertas, 5 cerradas, tiempo medio resolución: 3.2 días

Export Excel (extensión del reporte existente):
  · Nueva pestaña "Proyectos": resumen por proyecto
  · Nueva pestaña "Tareas": detalle de tareas con su estado
  · Los filtros existentes (subarea, user, estado, fecha) aplican también
```

---

## 6. Vistas Nuevas (URLs)

### Panel de Proyectos

| URL | Vista | Rol | Descripción |
|-----|-------|-----|-------------|
| `/proyectos/` | `proyecto_list` | Master, Admin, PM | Lista de proyectos (tarjetas) con filtros |
| `/proyectos/crear/` | `proyecto_create` | Master, Admin | Crear proyecto |
| `/proyectos/<pk>/` | `proyecto_detail` | Master, Admin, PM | Dashboard con KPIs + resumen |
| `/proyectos/<pk>/editar/` | `proyecto_edit` | Master, Admin | Editar metadata |
| `/proyectos/<pk>/equipo/` | `proyecto_equipo` | Master, Admin | Gestionar miembros y roles |

### Backlog & Historias

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/proyectos/<pk>/backlog/` | `backlog_view` | Backlog drag & drop (priorizar, ordenar) |
| `/proyectos/<pk>/historias/crear/` | `historia_create` | Crear historia |
| `/proyectos/<pk>/historias/<hid>/editar/` | `historia_edit` | Editar historia |
| `/proyectos/<pk>/historias/<hid>/mover/` | `historia_mover` | POST: mover a sprint / cambiar estado |
| `/proyectos/<pk>/historias/<hid>/done/` | `historia_done` | PO marca historia como aceptada |

### Sprints

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/proyectos/<pk>/sprints/` | `sprint_list` | Lista de sprints |
| `/proyectos/<pk>/sprints/crear/` | `sprint_create` | Crear sprint (seleccionar historias del backlog) |
| `/proyectos/<pk>/sprints/<spk>/` | `sprint_board` | Sprint Board Kanban (tareas del sprint por estado) |
| `/proyectos/<pk>/sprints/<spk>/burndown/` | `sprint_burndown` | Gráfico burndown (Chart.js) |
| `/proyectos/<pk>/sprints/<spk>/iniciar/` | `sprint_iniciar` | Activar sprint (crea AsignacionActividad para tareas) |
| `/proyectos/<pk>/sprints/<spk>/finalizar/` | `sprint_finalizar` | Cerrar sprint |

### Tareas

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/proyectos/<pk>/tareas/` | `tarea_list` | Lista de tareas con filtros |
| `/proyectos/<pk>/tareas/crear/` | `tarea_create` | Crear tarea (asignar usuario, vincular a historia) |
| `/proyectos/<pk>/tareas/<tid>/` | `tarea_detail` | Detalle de tarea + historial |
| `/proyectos/<pk>/tareas/<tid>/editar/` | `tarea_edit` | Reasignar, cambiar historia/sprint |
| `/proyectos/<pk>/tareas/<tid>/activar/` | `tarea_activar` | POST: crear AsignacionActividad y activar para el usuario |

### Incidencias

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/proyectos/<pk>/incidencias/` | `incidencia_list` | Lista con filtros (estado, severidad, asignado) |
| `/proyectos/<pk>/incidencias/crear/` | `incidencia_create` | Reportar nueva incidencia |
| `/proyectos/<pk>/incidencias/<iid>/` | `incidencia_detail` | Detalle con comentarios y transiciones |
| `/proyectos/<pk>/incidencias/<iid>/transicion/` | `incidencia_transicion` | POST: cambiar estado |
| `/proyectos/<pk>/incidencias/<iid>/convertir/` | `incidencia_convertir` | POST: convierte a Tarea |

### Reportes

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/proyectos/<pk>/reportes/` | `proyecto_reportes` | Burndown, CFD, velocidad, incidencias |
| `/proyectos/<pk>/gantt/` | `proyecto_gantt` | Vista Gantt del proyecto (vis-timeline) |

---

## 7. Sidebar y Navegación

```
Sección NUEVA en sidebar (Master y Admin):
┌──────────────────────────┐
│ 📋 Proyectos             │
│   Lista de Proyectos     │
│   + Nuevo Proyecto       │
└──────────────────────────┘

El usuario normal NO ve esta sección. Solo ve su Tablero.
```

Cuando un Admin/PM está dentro de un proyecto, la sidebar podría mostrar sub-navegación contextual:
```
┌──────────────────────────┐
│ 📋 Portal de Clientes    │  ← nombre del proyecto activo
│   Dashboard              │
│   Backlog                │
│   Sprint Board           │
│   Tareas                 │
│   Incidencias (3)        │  ← contador
│   Reportes               │
│   ← Volver a proyectos   │
└──────────────────────────┘
```

---

## 8. Reportes y Dashboards

### 8.1 Burndown del Sprint (Chart.js)

```
Story Points  │  Ideal ─── · Real
    21 ┤●
    18 ┤ ▓●
    15 ┤  ▓▓●
    12 ┤   ▓▓▓●
     9 ┤    ▓▓▓ ▓●
     6 ┤     ▓▓  ▓▓●
     3 ┤      ▓   ▓ ▓●
     0 ┤──────▓───▓─▓─▓▓●── Días
         1  2  3  4  5  6  7  8  9  10
```

### 8.2 Cumulative Flow Diagram (stacked area)

```
Tareas │  ░░░░░░░░░░░░ Done
  20   │ ▓▓▓▓▓▓▓░░░░░ En Progreso
  15   │████████▓▓▓▓░░ Backlog
  10   │████████████▓▓
   5   │██████████████
   0   └──────────────── Días
```

### 8.3 Velocidad del Equipo

```
Pts │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  21
    │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓           13
    │  ▓▓▓▓▓▓▓▓                    8
    │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓          18
    └──────────────────────── Sprint 1  2  3  4
```

### 8.4 Métricas de Incidencias

- Tortuga: distribución por severidad
- Barras: abiertas vs cerradas por sprint
- Línea: tiempo medio de resolución (días)

### 8.5 Excel de Reportes (extensión)

```
Sheet 5: "Proyectos"
  Columnas: Código, Nombre, Estado, % Avance, Manager,
            Tareas Total, Pendientes, En Curso, Finalizadas,
            Incidencias Abiertas, Incidencias Cerradas,
            Fecha Inicio, Fecha Fin Estimada

Sheet 6: "Tareas por Proyecto"
  Columnas: Código Tarea, Proyecto, Historia, Tipo, Estado,
            Asignado A, Actividad Catálogo, Horas Estimadas,
            Fecha Creación, ID AsignacionActividad
```

Los filtros existentes del formulario (subarea, user, fecha_desde, fecha_hasta) se aplican también a estas pestañas.

---

## 9. Permisos y Roles

| Rol | Permisos en Proyectos |
|-----|----------------------|
| **Master** | CRUD sobre TODOS los proyectos. Ve todo. |
| **Admin** | CRUD sobre proyectos en sus subáreas asignadas (get_admin_subareas). |
| **Project Manager** | Ver/editar backlog, sprints, tareas e incidencias de sus proyectos. NO puede crear/eliminar proyectos. |
| **Usuario normal** | NO ve la sección Proyectos. Solo trabaja en su Tablero, donde las tareas de proyecto aparecen como AsignacionActividad normales. |

La función `get_admin_subareas` (ya existente en dashboard y reportes) se reutiliza para limitar el alcance de las vistas de proyecto.

---

## 10. Estructura de Archivos (Nuevo)

```
apps/proyectos/
├── __init__.py
├── apps.py
├── models.py              # Proyecto, MiembroProyecto, Etiqueta, Sprint,
│                          #   HistoriaUsuario, Tarea, Incidencia,
│                          #   ComentarioIncidencia, RegistroAvance
├── signals.py             # sync_tarea_from_asignacion, crear_asignacion_desde_tarea
├── views/
│   ├── __init__.py
│   ├── proyecto_views.py   # CRUD proyecto, dashboard, equipo
│   ├── backlog_views.py    # backlog drag-drop, historias CRUD
│   ├── sprint_views.py     # sprint CRUD, board, burndown
│   ├── tarea_views.py      # tarea CRUD, activacion
│   ├── incidencia_views.py # incidencia CRUD, transiciones, conversion
│   └── reportes_views.py   # reportes, Gantt, export
├── urls.py                # namespace "proyectos"
├── admin.py
└── migrations/
    └── 0001_initial.py

templates/proyectos/
├── proyecto_list.html
├── proyecto_form.html
├── proyecto_detail.html
├── proyecto_equipo.html
├── backlog.html
├── historia_form.html
├── sprint_list.html
├── sprint_form.html
├── sprint_board.html         # Sprint Kanban Board
├── sprint_burndown.html
├── tarea_list.html
├── tarea_form.html
├── tarea_detail.html
├── incidencia_list.html
├── incidencia_form.html
├── incidencia_detail.html
├── proyecto_reportes.html
└── proyecto_gantt.html

# Migraciones en apps existentes:
apps/planificacion/migrations/XXXX_add_proyecto_fk.py
```

---

## 11. Plan de Implementación

### Fase 1: Fundación (3 días)
- Crear app `proyectos`
- Modelos: `Proyecto`, `MiembroProyecto`, `Etiqueta`
- Migración: FK `proyecto` en `Planificacion`
- `proyecto_list`, `proyecto_create`, `proyecto_detail`, `proyecto_edit`
- `proyecto_equipo` (gestionar miembros)
- Sidebar: sección "Proyectos"
- Actividad genérica automática por proyecto

### Fase 2: Backlog e Historias (3 días)
- Modelo `HistoriaUsuario`
- `backlog_view` con drag & drop (SortableJS)
- `historia_create`, `historia_edit`, `historia_mover`
- `historia_done` (PO acepta)
- Actualizar `orden` al reordenar backlog

### Fase 3: Sprints (3 días)
- Modelo `Sprint`
- `sprint_list`, `sprint_create` (seleccionar historias del backlog)
- `sprint_board` (Kanban de tareas del sprint por estado)
- `sprint_iniciar` (activa tareas → crea AsignacionActividad)
- `sprint_finalizar` (mueve historias no completadas al backlog, calcula velocidad)
- `sprint_burndown` (Chart.js)

### Fase 4: Tareas + Acoplamiento (3 días)
- Modelo `Tarea` con `OneToOneField` a `AsignacionActividad`
- `tarea_list`, `tarea_create`, `tarea_detail`, `tarea_edit`
- `tarea_activar` → llama a `crear_asignacion_desde_tarea()`
- `signals.py` → `sync_tarea_from_asignacion`
- Actividad genérica automática: `_get_or_create_actividad_generica()`
- Badge opcional de proyecto en el Tablero (`tablero.html`)
- Sincronización de estado probada en ambos sentidos

### Fase 5: Incidencias (2 días)
- Modelos: `Incidencia`, `ComentarioIncidencia`
- `incidencia_list` con filtros (estado, severidad, asignado, etiquetas)
- `incidencia_create`, `incidencia_detail`
- `incidencia_transicion` (máquina de estados: abierta → triaged → en_progreso → resuelta → cerrada)
- `incidencia_convertir` (crea Tarea vinculada)

### Fase 6: Reportes + Gantt + Pulido (3 días)
- `proyecto_reportes` con gráficos (Chart.js):
  - Burndown del sprint activo
  - Cumulative Flow Diagram (stacked area)
  - Velocidad del equipo (barras)
  - Incidencias por severidad (torta)
- `proyecto_gantt` con `vis-timeline` (ya incluido en el proyecto)
- `RegistroAvance` para bitácora de eventos
- Extender Excel: Sheet 5 "Proyectos", Sheet 6 "Tareas"
- Testing integral de todos los flujos

**Tiempo total estimado: 17 días (3-4 semanas)**

---

## 12. Lo que NO cambia (garantizado)

| Componente | Impacto |
|---|---|
| `TipoActividad` / `Actividad` (catálogo) | Sin cambios. Las tareas de proyecto las referencian opcionalmente |
| `Planificacion` | Solo se añade FK `proyecto` (nullable). Sin proyecto = funciona igual |
| `AsignacionActividad` | Sin cambios de modelo. Solo nuevo `related_name` desde Tarea/Incidencia |
| Tablero Kanban del usuario | **Idéntico** (solo badge opcional de proyecto) |
| Flujo Iniciar → Pausar → Finalizar | **Idéntico** |
| Tiempo, RegistroTiempo | **Idéntico** |
| Revisiones (aprobar/rechazar) | **Idéntico**. El proyecto solo observa vía señal |
| Traslados | **Idéntico** |
| Tiempo Inactividad | **Idéntico** |
| Dashboard productividad | **Idéntico**. Se puede filtrar por proyecto (opcional) |
| Reportes productividad | **Idéntico**. Solo se añaden pestañas de proyecto |
| KACTUS (habilitaciones/sync) | **Idéntico** |
| Comentario existente | **Idéntico** |
| RevisionHistorial | **Idéntico** |

---

## 13. Resumen de Puntos de Integración

| # | Punto | Mecanismo | Qué reutiliza |
|---|-------|-----------|---------------|
| 1 | Catálogo de trabajo | `Tarea.actividad_catalogo` → FK a `Actividad` | TipoActividad, flags (requiere_entregable, requiere_fecha_limite) |
| 2 | Motor de trabajo | `Tarea.asignacion` → OneToOne a `AsignacionActividad` | Tablero Kanban, tiempos, pausas, traslados |
| 3 | Sincronización de estado | `signals.py` → `post_save` en `AsignacionActividad` | Todo el ciclo de vida (Pendiente→EnCurso→Pausada→Finalizada→Revision) |
| 4 | Revisiones | `revision_aprobar` / `revision_rechazar` existentes | `RevisionHistorial`, `prorroga_count`, badge de comentarios |
| 5 | Comentarios | `Comentario` existente + `ComentarioIncidencia` nuevo | `Comentario` (asignacion + detalle), `RevisionHistorial` |
| 6 | Alcance organizacional | `get_admin_subareas()` (ya existente) | `Area`, `SubArea`, `UserSubArea` |
| 7 | Planificación masiva | FK `proyecto` opcional en `Planificacion` | `PlanificacionDetalle`, `AsignacionActividad` |
| 8 | Filtros | Mismos parámetros GET (`subarea_id`, `user_id`, `fecha_desde`, `fecha_hasta`) | Vistas de dashboard, progreso, reportes |
| 9 | Excel | Nuevas pestañas en `exportar_completo` | Estructura existente de `Workbook`, `_style_header`, `_auto_width` |
| 10 | Gantt | `vis-timeline` (ya en `linea_tiempo.html`) | Biblioteca JS incluida en `base.html` |
| 11 | Drag & drop | SortableJS (CDN) para backlog | No existía, es nuevo |
| 12 | Gráficos | Chart.js (ya en dashboard) | `Chart.js` cargado en `base.html` |
