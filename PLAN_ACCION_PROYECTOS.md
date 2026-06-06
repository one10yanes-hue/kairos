# Plan de Acción · Evolución de Gestión de Proyectos y Productividad

## Objetivo

Convertir la capa actual de proyectos en un flujo profesional tipo Jira/Kanban sin romper el motor operativo existente. La regla central se mantiene: `AsignacionActividad` sigue siendo el núcleo de ejecución, pero ahora el proyecto gana una capa formal de planificación, priorización, trazabilidad, permisos y analítica.

## Diagnóstico Ejecutivo

El proyecto ya tiene una base funcional sólida:

- `apps/gestion/` resuelve la ejecución real: tablero, tiempos, pausas, finalización, revisión, traslados, comentarios e inactividad.
- `apps/proyectos/` ya modela proyecto, membresía, sprint, historia, tarea, incidencia y bitácora.
- `apps/planificacion/` crea trabajo masivo desde estructura y catálogo.
- `apps/dashboard/` y `apps/reportes/` ya muestran indicadores, pero aún operan más como seguimiento que como inteligencia de producto.

Lo que hoy se siente corto no es la base técnica, sino el flujo profesional alrededor de esa base:

- faltan permisos de proyecto realmente aplicados,
- falta una experiencia de backlog y sprint más madura,
- falta cerrar el ciclo de vida de las historias y tareas con reglas claras,
- falta analítica de producto y de flujo,
- falta cobertura de pruebas para sostener el crecimiento.

## Principio De Diseño

No crear dos motores paralelos.

- `gestion` continúa siendo el motor transaccional.
- `proyectos` se convierte en la capa de orquestación del trabajo.
- `planificacion` alimenta la demanda.
- `dashboard` y `reportes` consumen métricas del ciclo completo.

## Estado Actual Que Debe Preservarse

No se debe romper ni reescribir lo siguiente:

- `apps/gestion/models.py` como fuente de verdad del estado operativo.
- `apps/proyectos/signals.py` como punto de sincronización entre historia/tarea y asignación operativa.
- `apps/actividades/` como catálogo reutilizable de tipos y actividades.
- `apps/planificacion/` como generador de carga masiva.
- Los tableros ya existentes en `templates/gestion/` y `templates/proyectos/` como base visual.

## Brechas Prioritarias

### 1. Permisos de proyecto demasiado blandos

Hoy la membresía existe, pero no gobierna suficientemente el acceso real a las vistas y acciones.

Impacto:

- cualquier usuario autenticado puede llegar a pantallas que deberían ser de equipo,
- se diluye la separación entre observador, miembro, líder y ejecutor,
- el sistema se vuelve difícil de auditar.

### 2. Backlog y sprint todavía no se sienten como producto maduro

Hay historias, tareas, sprint y tablero, pero falta una capa más profesional de:

- orden explícito de backlog,
- épicas o agrupaciones superiores,
- dependencias visibles,
- bloqueo real,
- transición de estados más estricta,
- cierre de sprint con arrastre y compromiso.

### 3. El puente entre planificación y ejecución no está cerrado del todo

`Planificacion` ya puede generar asignaciones, pero el flujo ideal debería permitir:

- planificar,
- convertir en historia/tarea si aplica,
- ejecutar en tablero,
- medir resultados por proyecto y sprint.

### 4. La analítica todavía es más operativa que directiva

Faltan métricas de gestión que un sistema robusto debe mostrar:

- lead time,
- cycle time,
- throughput por sprint,
- aging de historias/tareas,
- trabajo bloqueado,
- cumplimiento de compromiso vs entregado,
- capacidad por miembro y por sprint.

### 5. La regresión funcional tiene poca cobertura

El flujo ya es suficientemente grande como para depender de scripts manuales. Se necesita cobertura formal de:

- permisos,
- sincronización entre modelos,
- cambios de estado,
- cierre de sprint,
- backlog ordering,
- traslados y revisiones,
- casos borde de planificacion ↔ proyecto ↔ gestion.

## Ruta Objetivo

### Flujo deseado

1. Se define el proyecto y su equipo.
2. Se ingresa demanda al backlog como historias, tareas o incidencias.
3. Se prioriza por valor, urgencia y dependencia.
4. Se arma sprint o lote de trabajo.
5. Al asignarse una tarea, esta se sincroniza con `AsignacionActividad`.
6. El usuario trabaja desde el tablero operativo.
7. El equipo revisa, aprueba o cierra.
8. El sistema deja métricas útiles para dirección.

## Plan De Acción Por Fases

### Fase 0 · Alineación de dominio y reglas

Objetivo: fijar el contrato funcional del sistema antes de ampliar pantallas.

Entregables:

- matriz clara de qué gobierna `gestion`, qué gobierna `proyectos` y qué gobierna `planificacion`,
- definición formal de roles de proyecto,
- reglas de transición de estado por entidad,
- definición del ciclo de vida de historia, tarea, incidencia y sprint.

Acciones:

- documentar la matriz de responsabilidad por app,
- estandarizar los estados y sus transiciones permitidas,
- decidir qué campos son de negocio y cuáles son solo de sincronización,
- fijar reglas para trabajo bloqueado, revisión y cierre.

### Fase 1 · Seguridad y acceso

Objetivo: que el proyecto tenga un perímetro real.

Entregables:

- verificación de membresía en todas las vistas de proyecto,
- decoradores o mixins de acceso reutilizables,
- separación entre `viewer`, miembro operativo y responsables,
- validación por proyecto en acciones de edición, cierre, asignación y reordenamiento.

Acciones:

- crear un helper único de autorización de proyecto,
- reemplazar accesos directos por validaciones de membresía,
- restringir operaciones sensibles a roles definidos,
- auditar qué vistas deben ser solo lectura.

### Fase 2 · Backlog profesional

Objetivo: hacer que el backlog se comporte como una cola de producto real.

Entregables:

- orden persistente por prioridad,
- reordenamiento drag & drop,
- etiquetas de negocio consistentes,
- bloqueo y dependencias visibles,
- agrupación superior para trabajo grande si el dominio lo requiere,
- vista unificada de historias, tareas e incidencias.

Acciones:

- consolidar el modelo de prioridad y orden,
- exponer dependencias y bloqueos en la UI,
- permitir filtros por sprint, estado, responsable, etiqueta y severidad,
- definir una vista de backlog que sirva tanto para producto como para ejecución.

### Fase 3 · Sprint y ejecución

Objetivo: cerrar el ciclo de planificación a ejecución con una experiencia consistente.

Entregables:

- inicio y cierre formal de sprint,
- compromiso de puntos,
- arrastre de trabajo no terminado,
- burndown confiable,
- estados más claros para revisión y done,
- trazabilidad historia → tarea → asignación.

Acciones:

- añadir reglas de apertura y cierre del sprint,
- fijar qué sucede con historias y tareas incompletas,
- registrar quién comprometió y quién cerró,
- asegurar que `AsignacionActividad` siga sincronizada con la tarea del proyecto,
- conectar las incidencias al ciclo del sprint cuando aplique.

### Fase 4 · Integración con planificación y tablero operativo

Objetivo: que la planificación no sea un sistema paralelo, sino el origen de carga.

Entregables:

- vínculo visible entre planificaciones y proyecto,
- conversión controlada de trabajo planificado a elementos de backlog,
- trazabilidad de origen,
- consistencia entre actividad catalogada y tarea de proyecto.

Acciones:

- permitir que `Planificacion` se asocie al proyecto de forma explícita,
- definir cuándo una planificación genera historia, tarea o asignación directa,
- preservar el tablero operativo como destino final del trabajo,
- evitar duplicidad de flujos que confundan al usuario.

### Fase 5 · Analítica de producto y productividad

Objetivo: pasar de reportes descriptivos a analítica útil para gestión.

Entregables:

- métricas por sprint,
- métricas por usuario y por proyecto,
- aging de trabajo,
- bloqueos y cuellos de botella,
- cumplimiento de compromiso,
- historial de avance del proyecto.

Acciones:

- ampliar `dashboard` con métricas de ciclo,
- enriquecer `reportes` con indicadores de sprint y backlog,
- crear vistas por proyecto con avances, burn-up o burndown y estado de incidencias,
- mostrar alertas de trabajo envejecido o bloqueado.

### Fase 6 · Calidad, pruebas y estabilidad

Objetivo: proteger el sistema mientras crece la complejidad.

Entregables:

- pruebas de acceso,
- pruebas de transición de estados,
- pruebas de sincronización entre modelos,
- pruebas de cierre de sprint,
- pruebas de regresión para flujos de planificacion y tablero.

Acciones:

- convertir los scripts de `test/` en pruebas formales donde aporte valor,
- cubrir los casos de sincronización `Tarea ↔ AsignacionActividad`,
- validar reordenamiento, bloqueo y revisión,
- probar permisos por rol y por membresía.

## Prioridad De Implementación

### Corto plazo

1. Cerrar permisos de proyecto.
2. Formalizar backlog con orden y filtros.
3. Asegurar el flujo sprint con reglas de inicio y cierre.

### Mediano plazo

1. Integrar mejor planificación con proyecto.
2. Mejorar métricas de producto.
3. Consolidar la trazabilidad entre historia, tarea, incidencia y asignación.

### Largo plazo

1. Añadir analítica histórica avanzada.
2. Profundizar automatizaciones.
3. Fortalecer tests y validaciones de dominio.

## Criterios De Éxito

El cambio estará bien ejecutado si se cumple lo siguiente:

- el usuario entiende con claridad dónde planifica y dónde ejecuta,
- un proyecto no expone datos a personas sin membresía,
- un sprint puede iniciarse, ejecutarse y cerrarse sin ambigüedad,
- una tarea de proyecto y su asignación operativa siempre conservan coherencia,
- el dashboard responde preguntas de gestión y no solo de actividad,
- el sistema tiene pruebas suficientes para evitar regresiones obvias.

## Riesgos

- duplicar lógica entre `gestion` y `proyectos`,
- endurecer permisos sin definir bien roles,
- añadir más estados sin una matriz de transición clara,
- convertir el backlog en un CRUD sin valor operativo,
- sobrecargar el tablero con métricas que no ayuden a decidir.

## Recomendación Final

La mejor evolución no es “hacer más pantallas”, sino convertir la capa de proyectos en una verdadera capa de gobierno del trabajo. El motor actual ya sirve; el siguiente paso es profesionalizar el flujo con permisos, backlog, sprint, métricas y pruebas. Si eso se hace bien, el sistema deja de verse como un tablero adaptado y empieza a comportarse como una plataforma de gestión robusta.
