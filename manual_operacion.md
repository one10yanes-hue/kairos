# Kairos - Manual de Operacion y Flujo de la Aplicacion

**Version**: 3.0
**Ultima actualizacion**: 24/05/2026
**Autor**: Documentacion del sistema

---

## Indice
1. [Introduccion](#introduccion)
2. [Roles y Alcance](#roles-y-alcance)
3. [Flujo General de Operacion](#flujo-general-de-operacion)
4. [Flujo Master](#flujo-master)
5. [Flujo Admin](#flujo-admin)
6. [Flujo Usuario](#flujo-usuario)
7. [Ciclo de Vida de una Actividad](#ciclo-de-vida-de-una-actividad)
8. [Diagrama de Navegacion](#diagrama-de-navegacion)
9. [Casos de Uso Transversales](#casos-de-uso-transversales)
10. [Reglas de Negocio](#reglas-de-negocio)
11. [Gestion de Pendientes (Prórroga)](#gestion-de-pendientes-prorroga)
12. [Limitaciones Conocidas](#limitaciones-conocidas)

---

## Introduccion

Kairos es un sistema de gestion de productividad donde los administradores planifican actividades y las asignan a usuarios, quienes las ejecutan y registran su tiempo. El sistema sigue una jerarquia organizacional estricta:

```
Empresa → Area → SubArea
```

Cada usuario pertenece a una o mas SubAreas, y cada Admin administra una o mas SubAreas. El Master administra todo el sistema.

---

## Roles y Alcance

### Rol: Master

| Caracteristica | Descripcion |
|---------------|-------------|
| **Acceso** | Total. Ve todas las empresas, areas, subareas, usuarios y datos de todas las subareas |
| **Sidebar** | ORGANIZACION + USUARIOS + GESTION + Importar Datos |
| **Puede ver** | Todo el sistema sin restriccion de jerarquia |
| **Puede crear** | Empresas, Areas, SubAreas, Usuarios (cualquier rol), Tipos de Actividad, Actividades, Planificaciones |
| **Puede asignar** | Usuarios a empresas, usuarios a subareas, actividades a usuarios |
| **Gestion de pendientes** | Puede reprogramar (prórroga), reasignar usuario o cancelar actividades pendientes desde el detalle de cada planificacion |
| **Importacion** | Descarga plantilla Excel (empresa pre-seleccionada), llena area+subarea por fila, importa con codigos automaticos |

### Rol: Admin

| Caracteristica | Descripcion |
|---------------|-------------|
| **Acceso** | Solo a sus SubAreas asignadas via `UserSubArea` |
| **Sidebar** | DASHBOARD + ADMINISTRAR |
| **Puede ver** | Solo datos de sus subareas: tipos de actividad, actividades, usuarios de su equipo, planificaciones |
| **Puede crear** | Tipos de Actividad, Actividades, Planificaciones (solo en sus subareas) |
| **Dashboard** | Ve KPIs de su equipo: total, pendientes, en curso, pausadas, finalizadas, prorrogas, tiempo total, items finalizados, promedio por item, productividad — con filtros de subarea, usuario y fecha |
| **Reportes** | Puede exportar Excel con datos de sus subareas |
| **No puede** | Ver empresas/areas de otras subareas, crear usuarios, modificar la jerarquia |

### Rol: Usuario

| Caracteristica | Descripcion |
|---------------|-------------|
| **Acceso** | Solo a su tablero personal y calendario |
| **Sidebar** | MI GESTION: Tablero, Calendario, Mi Perfil, Evento Flash |
| **Puede ver** | Solo sus propias actividades asignadas |
| **Puede hacer** | Iniciar, Pausar, Reanudar, Finalizar, Trasladar, Comentar actividades |
| **No puede** | Ver datos de otros usuarios, crear actividades/tipos, acceder a reportes |

---

## Flujo General de Operacion

### Paso 1: Configuracion Inicial (Master)
```
Master crea Empresas → Areas → SubAreas → Usuarios → los asigna a empresas y subareas
```
Los codigos (EMxxx, ARxxx, SBxxx) se generan automaticamente al guardar.

### Paso 2: Catalogos (Admin)
```
Admin crea Tipos de Actividad → Actividades (dentro de su subarea)
```
- Tipos: "Programada", "No Programada", "Mejora", "Procesos" (el admin puede crear mas)
- Cada Actividad se asocia a un Tipo y una SubArea
- La validacion asegura que Actividad.subarea == TipoActividad.subarea

### Paso 3: Planificacion (Admin)
```
Admin crea Planificacion → selecciona SubArea → Actividades → Usuarios → Fecha de Planificacion (obligatoria)
```
- Fecha de planificacion: determina cuando aparece la actividad en el tablero/calendario del usuario
- Al crear, la planificacion se cierra automaticamente (no se agregan mas actividades)
- Se crean `AsignacionActividad(estado="Pendiente", origen="Planificacion")` para cada usuario
- Las actividades aparecen en el tablero de los usuarios en la columna "Planificadas"

### Paso 4: Ejecucion (Usuario)
```
Usuario ve actividades en su Tablero Trello →
  Inicia → Pausa (con motivo) → Reanuda → Finaliza (con nro_actividad obligatorio)
  o Traslada a otro usuario via solicitud
  o Crea actividad No Programada (Evento Flash)
```
- Solo 1 actividad "En Curso" a la vez
- Al pausar se registra el motivo y el sistema cronometra el tiempo de pausa
- Al finalizar, el usuario debe ingresar el nro de items realizados (comentario opcional)

### Paso 5: Monitoreo (Admin)
```
Admin revisa Dashboard → Progreso del equipo → Exporta reportes Excel
```
- Dashboard con filtros de subarea, usuario y rango de fechas
- KPI de prorrogas, tiempo activo vs pausado, items por minuto

### Paso 6: Gestion de Pendientes (Admin)
```
Admin revisa detalle de planificacion → Pendientes por Gestionar →
  Reprograma (prórroga al dia siguiente) | Reasigna usuario | Cancela
```
- Cada prórroga incrementa el contador `prorroga_count`
- Al reasignar se cambia el usuario y se marca `origen="Reasignado"`
- El dashboard refleja las prorrogas por usuario

---

## Flujo Master

```
INICIO: Login con cedula + fecha_expedicion
  │
  ├── [ORGANIZACION]
  │   ├── Empresas → CRUD (nombre, NIT, direccion, telefono) — lista en tabla con codigo
  │   ├── Areas → CRUD (nombre, empresa a la que pertenece)
  │   └── SubAreas → CRUD (nombre, area + usuarios asignados)
  │
  ├── [USUARIOS]
  │   └── Usuarios → CRUD (cedula, nombre, rol + empresas + subareas)
  │
  └── [GESTION]
      ├── Dashboard (ve datos de todas las subareas, con filtros de usuario y fecha)
      ├── Progreso (ve asignaciones de todo el sistema)
      ├── Tipos Actividad → CRUD
      ├── Actividades → CRUD
      ├── Planificaciones → Crear, Ver (con gestion de pendientes), Inactivar
      ├── Reportes → Exportar Excel completo
      └── Importar Datos → Descargar plantilla + Importar Excel
```

---

## Flujo Admin

```
INICIO: Login con cedula + fecha_expedicion
  │
  ├── [DASHBOARD]
  │   ├── Dashboard → KPIs con filtros de subarea/usuario/fecha
  │   └── Progreso → Listado detallado de asignaciones
  │
  └── [ADMINISTRAR]
      ├── Tipos Actividad → CRUD (solo en sus subareas)
      ├── Actividades → CRUD (solo en sus subareas)
      ├── Planificaciones → Crear (con fecha obligatoria) / Ver (gestionar pendientes)
      └── Reportes → Exportar Excel con filtros
```

---

## Flujo Usuario

```
INICIO: Login con cedula + fecha_expedicion
  │
  └── [MI GESTION]
      ├── Tablero Trello (vista principal)
      │   ├── Mis actividades - Hoy (tarjetas resumen del dia)
      │   ├── Traslados pendientes (entrantes y salientes)
      │   └── 4 columnas:
      │       ├── Planificadas (Pendientes)
      │       ├── En Curso (solo 1, con timer en vivo)
      │       ├── Pausadas (con botones Reanudar, Finalizar, Trasladar, Detalle)
      │       └── Finalizadas (solo las del dia actual)
      │
      ├── Calendario (vista Mes / Semana / Dia con timeline horario)
      │
      ├── Mi Perfil (resumen: asignaciones, horas, actividad hoy)
      │
      └── Evento Flash (iniciar actividad no programada)
```

---

## Ciclo de Vida de una Actividad

```
                    ┌──────────────────┐
                    │   Planificacion  │ (Admin crea con fecha)
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   Pendiente      │ ← Columna "Planificadas"
                    └────────┬─────────┘
                             │ Iniciar
                    ┌────────▼─────────┐
             ┌──────│   En Curso       │ (solo 1, timer en vivo)
             │      └────────┬─────────┘
             │               │
      Pausar │        ┌──────┴──────┐
             │        │             │
             ▼        ▼             │
     ┌──────────┐  Reanudar         │
     │ Pausada  │───────────────────┘
     │(cronometra│    Finalizar
     │ pausa)   │──────────────┐
     └──────────┘              │
                               ▼
                    ┌──────────────────┐
                    │   Finalizada     │ (dia actual en tablero)
                    └──────────────────┘

ADMIN: Si queda Pendiente al final del dia →
  Reprogramar (prórroga +1) | Reasignar | Cancelar
```

---

## Diagrama de Navegacion

```
Login
├── Master ──→ /master/empresas/
│                ├── Empresas (tabla con codigo)
│                ├── Areas (tabla)
│                ├── SubAreas (tabla + usuarios)
│                ├── Usuarios (CRUD + empresas)
│                ├── Dashboard (filtros fecha/usuario)
│                ├── Progreso
│                ├── Tipos Actividad
│                ├── Actividades
│                ├── Planificaciones (crear con fecha / ver + gestionar pendientes: prórroga, reasignar, cancelar)
│                ├── Reportes
│                └── Importar Datos (empresa → plantilla → importar)
│
├── Admin ──→ /admin/dashboard/
│                ├── Dashboard (filtrable por subarea/usuario/fecha)
│                ├── Progreso
│                ├── Tipos Actividad
│                ├── Actividades
│                ├── Planificaciones (crear con fecha obligatoria / ver + gestionar pendientes)
│                └── Reportes
│
└── Usuario ──→ /usuario/tablero/
                     ├── Tablero (Hoy + Traslados + 4 columnas con scroll interno)
                     ├── Calendario (Mes/Semana/Dia)
                     ├── Mi Perfil
                     └── Evento Flash
```

---

## Casos de Uso Transversales

### Colaboracion
Dos usuarios pueden colaborar en la misma actividad. El colaborador no afecta su propio time tracking.

### Traslado (solicitud)
Un usuario puede transferir una actividad a otro mediante solicitud. El destino debe aceptar/rechazar. Hasta entonces, nada cambia.

### Prórroga (Reprogramacion por Admin)
El admin puede reprogramar una actividad pendiente al dia siguiente. Cada reprogramacion incrementa el contador `prorroga_count` visible en dashboard y reportes.

### Reasignacion Directa
El admin puede cambiar el usuario asignado a una actividad pendiente. Se marca `origen="Reasignado"` y se registra quien hizo el cambio.

### Multiempresa
Un usuario puede pertenecer a varias empresas y subareas simultaneamente. El tablero filtra por subarea seleccionada.

### Evento Flash
Cuando un usuario necesita hacer algo no previsto, selecciona de las actividades ya creadas por el admin.

### Tiempo Efectivo y Pausado
- **Tiempo activo:** intervalos Inicio→Pausa + Reanudacion→Fin
- **Tiempo pausado:** intervalos Pausa→Reanudacion (o Pausa→ahora si sigue pausada)
- Ambos visibles en dashboard y tablero

### Unico EnCurso
Un usuario solo puede tener UNA actividad "En Curso" a la vez. La anterior se pausa automaticamente.

### Finalizadas del Dia
La columna "Finalizadas" solo muestra las completadas hoy. Las de dias anteriores no se acumulan.

---

## Gestion de Pendientes (Prórroga)

Al final del dia, el admin puede gestionar actividades que quedaron Pendientes o Pausadas desde el detalle de cada planificacion:

### Tabla "Pendientes por Gestionar"
Columnas: Actividad | Usuario | Estado | Limite | Prorr (contador) | Acciones

### Acciones Disponibles

| Accion | Boton | Efecto |
|--------|-------|--------|
| **Prórroga** | `[+]` amarillo | `fecha_limite` → mañana, `prorroga_count++` |
| **Reasignar** | select usuario + `[→]` | Cambia `user`, `origen="Reasignado"`, `estado="Pendiente"` |
| **Cancelar** | `[x]` rojo | `estado="Cancelada"` |

### Trazabilidad
- `prorroga_count`: cuantas veces se reprogramo
- `origen` y `origen_user`: quien y como se origino la asignacion
- `RegistroTiempo`: solo se afecta por acciones del usuario (iniciar, pausar, finalizar), no por prorrogas del admin

---

## Reglas de Negocio

| # | Regla | Implementacion |
|---|-------|----------------|
| 1 | Un usuario solo puede tener 1 actividad "EnCurso" | UniqueConstraint en BD + `_pausar_activas()` |
| 2 | No hay 2 traslados pendientes para la misma (origen, destino) | UniqueConstraint condicional |
| 3 | Planificacion se cierra al crearse | `cerrada=True` en `save()` |
| 4 | Actividad.subarea debe coincidir con TipoActividad.subarea | `clean()` en modelo Actividad |
| 5 | Login con cedula + fecha_expedicion | Custom auth backend |
| 6 | Soft-delete en todas las tablas de negocio | Campo `activo=True/False` |
| 7 | Admin solo ve sus subareas | `get_admin_subareas()` filtra queries |
| 8 | Usuario solo ve usuarios mismo nivel en traslados | Filtro por rol en busqueda |
| 9 | Codigos unicos 6 chars auto-generados | `generar_codigo()` en `save()` |
| 10 | Fecha de planificacion obligatoria | `required` en HTML + validacion backend |
| 11 | Finalizadas solo del dia actual | `registros__fecha_hora__date=hoy` en tablero |
| 12 | Tiempo de pausa cronometrado | `tiempo_pausado_segundos` + `tiempo_pausado()` |
| 13 | Prorroga contabilizada | `prorroga_count` en AsignacionActividad |
| 14 | Notificaciones toast no desplazan contenido | `position:fixed` + auto-dismiss 6s Bootstrap |
| 15 | Errores de login se consumen en login | `{% if messages %}` en `content_auth` |

---

## Limitaciones Conocidas

| Limitacion | Descripcion | Impacto |
|-----------|-------------|---------|
| Sin notificaciones en tiempo real | Las solicitudes de traslado requieren recargar la pagina (polling JS cada 30s atenua) | Bajo |
| Sin validacion de fecha limite vencida | Actividades con fecha vencida no cambian estado automaticamente | Bajo |
| Sin colaboracion via time tracking | `Colaboracion` existe pero el tiempo del colaborador no se registra | Medio |
| Sin exportacion PDF | Solo Excel | Bajo |
| Sin recuperacion de contrasena | Login solo con cedula+expedicion | Bajo |
| Sin tests automatizados | No hay tests unitarios ni de integracion | Alto |
| Sin paginacion en detalle de planificacion | Muchos detalles pueden alargar la pagina | Bajo |
