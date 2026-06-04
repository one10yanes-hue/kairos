# VIVA1A - Documentacion de Base de Datos

**Ultima actualizacion**: 26/05/2026
**Version**: 3.0
**Motor**: SQLite3 (dev) / MSSQL (prod via mssql-django)
**Timezone**: America/Bogota (UTC-5)

---

## Indice
1. [Convenciones](#convenciones)
2. [Diagrama de Relaciones](#diagrama-de-relaciones)
3. [Tablas por App](#tablas-por-app)
   - [accounts](#accounts-4-tablas)
   - [estructura](#estructura-3-tablas)
   - [actividades](#actividades-2-tablas)
   - [planificacion](#planificacion-2-tablas)
   - [gestion](#gestion-6-tablas)
   - [auditoria](#auditoria-1-tabla)
4. [Resumen de Normalizacion](#resumen-de-normalizacion)
5. [Reglas de Negocio en BD](#reglas-de-negocio-en-bd)
6. [Historial de Cambios](#historial-de-cambios)

---

## Convenciones

- `PK` = Primary Key (siempre `id` autoincremental)
- `FK` = Foreign Key con `on_delete` especificado
- `🔒` = Unique constraint o UniqueConstraint
- `🗑` = Soft-delete via campo `activo`
- `📅` = Campos `fecha_creacion` + `fecha_update` (auto_now_add / auto_now)
- `⚡` = Auto-generado via `save()` override
- `🔍` = Indice de busqueda (`db_index=True`)
- Todas las tablas tienen `id` como PK, `fecha_creacion` y `fecha_update` excepto donde se indique

---

## Diagrama de Relaciones

```
Empresa ──1:N── Area ──1:N── SubArea
           │                          │
           │                     ┌────┴────┬────────┐
           │                     │         │        │
           │                TipoActividad  │   UserSubArea
           │                     │         │        │
           │                Actividad      │   Usuario──Rol
           │                     │         │     │  │
           │                     │    Planificacion│  │
           │                     │         │     │  │
           │                     │   PlanificacionDetalle
           │                     │         │     │
UserEmpresa─┘                     │   AsignacionActividad
                                  │    ├── RegistroTiempo
                                  │    ├── TrasladoActividad
                                  │    ├── Comentario
                                  │    └── Colaboracion

AuditLog ── Usuario
```

---

## Tablas por App

---

### accounts (4 tablas)

#### `rol` — Roles del sistema

> **Logica**: Almacena los 3 roles fijos del sistema: `Master` (super-admin), `Admin` (administrador de subarea), `Usuario` (operativo). Cada usuario tiene un rol FK que determina sus permisos y lo que ve en la aplicacion.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| nombre | VARCHAR(50) | | NO | | 🔒 Unique |
| descripcion | TEXT | | SI | NULL | |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**Valores**: 1=Master, 2=Admin, 3=Usuario

---

#### `usuario` — Usuarios del sistema (Custom User Model)

> **Logica**: Almacena todos los usuarios del sistema. El login se hace con `cedula` + `fecha_expedicion` (no con email/password tradicional). Cada usuario pertenece a un `Rol` y puede estar asignado a multiples `Empresa` y `SubArea` a traves de las tablas puente `UserEmpresa` y `UserSubArea`. El campo `is_active` se sincroniza automaticamente con `activo` al guardar.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| cedula | VARCHAR(20) | | NO | | 🔒 Unique, USERNAME_FIELD |
| fecha_expedicion | DATE | | NO | | Requerido para login |
| nombre | VARCHAR(100) | | NO | | 🔍 db_index |
| apellido | VARCHAR(100) | | NO | | 🔍 db_index |
| email | EMAIL | | SI | NULL | |
| telefono | VARCHAR(20) | | SI | NULL | 🔍 db_index |
| cargo | VARCHAR(200) | | SI | NULL | Cargo del usuario en la empresa |
| rol_id | BIGINT | FK→rol | SI | NULL | 🔗 on_delete=PROTECT, related_name="usuarios" |
| is_active | BOOLEAN | | NO | TRUE | ⚠️ Sincronizado via `save()`: `is_active = activo` |
| is_staff | BOOLEAN | | NO | FALSE | Django admin |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| password | VARCHAR(128) | | SI | | Django auth |
| last_login | DATETIME | | SI | NULL | |
| is_superuser | BOOLEAN | | NO | FALSE | |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `empresa` — Empresas / Unidades de Negocio

> **Logica**: Almacena las empresas o unidades de negocio. Cada empresa tiene un `codigo` unico de 6 caracteres (auto-generado) para identificacion rapida. Las empresas son el nivel maximo de la jerarquia organizacional. Un Master puede crear empresas, y los Admins/Usuarios se asignan a ellas via `UserEmpresa`.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| codigo | VARCHAR(6) | | SI | NULL | 🔒 Unique, ⚡ auto-generado via `save()` |
| nombre | VARCHAR(200) | | NO | | 🔍 db_index |
| nit | VARCHAR(50) | | NO | | 🔒 Unique |
| direccion | TEXT | | SI | NULL | |
| telefono | VARCHAR(20) | | SI | NULL | 🔍 db_index |
| logo | VARCHAR(100) | | SI | NULL | ImageField |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `user_empresa` — Relacion Usuario-Empresa (N:M)

> **Logica**: Tabla puente que asigna usuarios a empresas. Un usuario puede estar en varias empresas, y una empresa tiene varios usuarios. La combinacion (user, empresa) es unica.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| user_id | BIGINT | FK→usuario | NO | | 🔗 on_delete=PROTECT, related_name="empresas" |
| empresa_id | BIGINT | FK→empresa | NO | | 🔗 on_delete=PROTECT, related_name="usuarios" |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 Unique**: `(user, empresa)`

---

### estructura (3 tablas)

#### `area` — Areas organizacionales

> **Logica**: Segundo nivel jerarquico. Cada Area pertenece a una Empresa. Ej: "Financiera", "Operaciones", "TI". Las areas agrupan SubAreas.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| codigo | VARCHAR(6) | | SI | NULL | 🔒 Unique, ⚡ auto-generado |
| empresa_id | BIGINT | FK→empresa | NO | | 🔗 on_delete=PROTECT, related_name="areas" |
| nombre | VARCHAR(200) | | NO | | 🔍 db_index |
| descripcion | TEXT | | SI | NULL | |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `subarea` — Subareas / Departamentos

> **Logica**: Tercer nivel jerarquico. Cada SubArea pertenece a un Area. Ej: "Contabilidad" (dentro de "Financiera"), "Tesoreria", "Nomina". Las SubAreas son el nivel donde se asignan los usuarios (`UserSubArea`) y donde se crean los Tipos de Actividad y Actividades.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| codigo | VARCHAR(6) | | SI | NULL | 🔒 Unique, ⚡ auto-generado |
| area_id | BIGINT | FK→area | NO | | 🔗 on_delete=PROTECT, related_name="subareas" |
| nombre | VARCHAR(200) | | NO | | 🔍 db_index |
| descripcion | TEXT | | SI | NULL | |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `user_subarea` — Relacion Usuario-SubArea (N:M)

> **Logica**: Tabla puente que asigna usuarios a subareas. Un usuario puede estar en varias subareas (y por ende en varias empresas). Esta relacion determina el alcance (scope) de cada usuario: los Admins solo ven datos de sus subareas, los Usuarios solo ven actividades de sus subareas.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| user_id | BIGINT | FK→usuario | NO | | 🔗 on_delete=PROTECT, related_name="subareas" |
| subarea_id | BIGINT | FK→subarea | NO | | 🔗 on_delete=PROTECT, related_name="usuarios" |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 Unique**: `(user, subarea)`

---

### actividades (2 tablas)

#### `tipo_actividad` — Tipos de actividad

> **Logica**: Clasificacion de actividades. Ej: "Programada" (planificada por admin), "No Programada" (surge espontaneamente). Cada tipo pertenece a una SubArea. El campo `requiere_fecha_limite` controla si al planificar actividades de este tipo, la **fecha de vencimiento** (`fecha_vencimiento` en PlanificacionDetalle) es obligatoria.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| codigo | VARCHAR(6) | | SI | NULL | 🔒 Unique, ⚡ auto-generado |
| subarea_id | BIGINT | FK→subarea | NO | | 🔗 related_name="tipos_actividad" |
| nombre | VARCHAR(200) | | NO | | 🔍 db_index |
| descripcion | TEXT | | SI | NULL | |
| requiere_fecha_limite | BOOLEAN | | NO | TRUE | Si TRUE, `fecha_vencimiento` obligatoria |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `actividad` — Actividades operativas

> **Logica**: Las actividades concretas que los usuarios ejecutan. Ej: "Causacion de Viaticos", "Informe AF", "Reunion Gerencia". Cada actividad pertenece a una SubArea y a un TipoActividad. La validacion `clean()` asegura que la actividad este en la misma subarea que su tipo (consistencia jerarquica).

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| codigo | VARCHAR(6) | | SI | NULL | 🔒 Unique, ⚡ auto-generado |
| subarea_id | BIGINT | FK→subarea | NO | | 🔗 related_name="actividades" |
| tipo_actividad_id | BIGINT | FK→tipo_actividad | NO | | 🔗 related_name="actividades" |
| nombre | VARCHAR(300) | | NO | | 🔍 db_index |
| descripcion | TEXT | | SI | NULL | |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**⚠️ Validacion**: `clean()` asegura `subarea_id == tipo_actividad.subarea_id`

---

### planificacion (2 tablas)

#### `planificacion` — Planificaciones creadas por Admin

> **Logica**: Representa una "planificacion" o "sprint" creado por un Admin/Master para asignar actividades a usuarios de su subarea. Al crearse, se cierra automaticamente (`cerrada=True`). Si todas las actividades estan Pendiente, el admin puede inactivar la planificacion. Si alguna actividad fue iniciada (EnCurso, Pausada, Finalizada), la planificacion no se puede inactivar.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| admin_id | BIGINT | FK→usuario | NO | | 🔗 related_name="planificaciones" |
| subarea_id | BIGINT | FK→subarea | NO | | 🔗 |
| nombre | VARCHAR(300) | | NO | | |
| descripcion | TEXT | | SI | NULL | |
| cerrada | BOOLEAN | | NO | FALSE | Si TRUE, no se aceptan mas asignaciones |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `planificacion_detalle` — Actividades asignadas dentro de una planificacion

> **Logica**: Cada registro vincula una actividad especifica a un usuario dentro de una planificacion. La combinacion (planificacion, actividad, user) es unica. Al crear un detalle, el sistema crea automaticamente una `AsignacionActividad` para que la actividad aparezca en el tablero del usuario.

> **Dos fechas de control**:
> - `fecha_limite`: **Fecha de planificacion** (opcional). Controla cuando la actividad aparece en el tablero del usuario. Si es null o pasada, aparece inmediatamente.
> - `fecha_vencimiento`: **Fecha limite / deadline** (obligatoria si el tipo `requiere_fecha_limite=True`). Controla la fecha maxima de entrega. Se usa para el badge de proximidad/vencimiento en el tablero y dashboard, y para el indicador "Vencidas". El admin puede extenderla via `reprogramar_pendiente`, que incrementa `prorroga_count`.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| planificacion_id | BIGINT | FK→planificacion | NO | | 🔗 related_name="detalles" |
| actividad_id | BIGINT | FK→actividad | NO | | 🔗 |
| user_id | BIGINT | FK→usuario | NO | | 🔗 |
| fecha_asignacion | DATETIME | | NO | now() | |
| fecha_limite | DATETIME | | SI | NULL | Aparece en tablero (planning date) |
| fecha_vencimiento | DATETIME | | SI | NULL | Deadline / vencimiento (obligatorio si tipo lo requiere) |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 Unique**: `(planificacion, actividad, user)`

---

### gestion (6 tablas) — Nucleo del sistema

#### `asignacion_actividad` — Asignaciones activas en el tablero del usuario

> **Logica**: Tabla central del sistema. Cada registro representa una actividad que un usuario tiene en su tablero. El `estado` determina en que columna aparece: Pendiente, EnCurso, Pausada, Finalizada, Cancelada o Trasladada. La constraint `unique_en_curso_por_usuario` garantiza que un usuario solo tenga UNA actividad en curso simultaneamente. `tiempo_total_segundos` y `tiempo_pausado_segundos` cachean los tiempos para rendimiento. `prorroga_count` cuenta reprogramaciones del admin sobre la `fecha_vencimiento`.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| planificacion_detalle_id | BIGINT | FK→planificacion_detalle | SI | NULL | 🔗 SET_NULL |
| user_id | BIGINT | FK→usuario | NO | | 🔗 related_name="asignaciones" |
| actividad_id | BIGINT | FK→actividad | NO | | 🔗 |
| estado | VARCHAR(20) | | NO | Pendiente | Pendiente/EnCurso/Pausada/Finalizada/Cancelada/Trasladada |
| origen | VARCHAR(20) | | SI | NULL | Planificacion / Traslado / Manual / Reasignado |
| origen_user_id | BIGINT | FK→usuario | SI | NULL | 🔗 SET_NULL — Quien origino la asignacion |
| fecha_asignacion | DATETIME | | NO | now() | |
| tiempo_total_segundos | INTEGER | | NO | 0 | Cache: tiempo activo acumulado |
| tiempo_pausado_segundos | INTEGER | | NO | 0 | Cache: tiempo en pausa acumulado |
| prorroga_count | INTEGER | | NO | 0 | Veces reprogramado (fecha_vencimiento extendida) |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 UniqueConstraint**: `fields=["user"], condition=Q(estado="EnCurso", activo=True)` — Un usuario solo puede tener 1 EnCurso

---

#### `registro_tiempo` — Time tracking por evento

> **Logica**: Registra cada evento de tiempo: `Inicio`, `Pausa` (con motivo), `Reanudacion`, `Finalizacion` (con nro_actividad), `Traslado`. Con estos registros se calcula el tiempo efectivo y tiempo pausado. Cada `save()` recalcula y cachea en `AsignacionActividad` via `recalcular_tiempo()`.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| asignacion_id | BIGINT | FK→asignacion_actividad | NO | | 🔗 related_name="registros" |
| evento | VARCHAR(20) | | NO | | Inicio/Pausa/Reanudacion/Finalizacion/Traslado |
| motivo_pausa | VARCHAR(50) | | SI | NULL | Almuerzo / Interrupcion / Cambio de prioridad / Otro |
| fecha_hora | DATETIME | | NO | now() | |
| comentario | TEXT | | SI | NULL | |
| nro_actividad | VARCHAR(50) | | SI | NULL | Cantidad realizada (ingresada por usuario al finalizar) |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `traslado_actividad` — Solicitudes de traslado entre usuarios

> **Logica**: Un usuario transfiere una actividad a otro. Estado `Pendiente` hasta que el destino Acepte o Rechace. Al aceptar, el origen obtiene una actividad de reemplazo. No puede haber 2 solicitudes pendientes para la misma (origen, destino).

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| asignacion_origen_id | BIGINT | FK→asignacion_actividad | NO | | 🔗 related_name="traslados_origen" |
| asignacion_destino_id | BIGINT | FK→asignacion_actividad | SI | NULL | 🔗 SET_NULL |
| user_origen_id | BIGINT | FK→usuario | NO | | 🔗 related_name="traslados_hechos" |
| user_destino_id | BIGINT | FK→usuario | NO | | 🔗 related_name="traslados_recibidos" |
| actividad_reemplazo_id | BIGINT | FK→actividad | SI | NULL | 🔗 |
| estado | VARCHAR(20) | | NO | Pendiente | Pendiente/Aceptado/Cancelado/Rechazado |
| motivo | TEXT | | SI | NULL | |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 UniqueConstraint**: `fields=["asignacion_origen", "user_destino"], condition=Q(estado="Pendiente", activo=True)`

---

#### `colaboracion` — Colaboracion entre usuarios en una asignacion

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| asignacion_id | BIGINT | FK→asignacion_actividad | NO | | 🔗 related_name="colaboraciones" |
| user_colaborador_id | BIGINT | FK→usuario | NO | | 🔗 related_name="colaboraciones" |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 Unique**: `(asignacion, user_colaborador)`

---

#### `comentario` — Comentarios en asignaciones

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| asignacion_id | BIGINT | FK→asignacion_actividad | NO | | 🔗 related_name="comentarios" |
| user_id | BIGINT | FK→usuario | NO | | 🔗 related_name="comentarios" |
| texto | TEXT | | NO | | |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

### auditoria (1 tabla)

#### `audit_log` — Log de auditoria de acciones

> **Logica**: Registra via middleware todas las acciones POST/PUT/DELETE. Inmutable (sin soft-delete ni fecha_update).

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| user_id | BIGINT | FK→usuario | SI | NULL | 🔗 SET_NULL |
| accion | VARCHAR(50) | | NO | | CREATE / UPDATE / DELETE |
| modelo_afectado | VARCHAR(100) | | NO | | Nombre del modelo |
| id_registro | INTEGER | | SI | NULL | PK del registro afectado |
| detalle | TEXT | | NO | | Metadata |
| ip_address | CHAR(39) | | SI | NULL | |
| fecha_creacion | DATETIME | | NO | now() | 📅 (sin update) |

---

## Resumen de Normalizacion

### 1FN (Atomicidad) ✅
Todas las columnas son atomicas. Sin grupos repetidos.

### 2FN (Dependencia parcial) ✅
PK simple (`id`). Sin dependencias parciales.

### 3FN (Dependencia transitiva) ⚠️

| Tabla | Columna | Dependencia | Estado |
|-------|---------|------------|--------|
| `actividad` | `subarea_id` | Derivable de `tipo_actividad.subarea_id` | ⚠️ Aceptable (performance). Validada por `clean()`. |
| `traslado_actividad` | `user_origen_id` | Derivable de `asignacion_origen.user_id` | ⚠️ Aceptable (auditoria historica). |
| `asignacion_actividad` | `actividad_id` | Derivable de `planificacion_detalle.actividad_id` | ⚠️ Aceptable (FK directa para asignaciones sin plan_detalle). |
| `asignacion_actividad` | `tiempo_total_segundos` + `tiempo_pausado_segundos` | Calculables desde `registro_tiempo` | ⚠️ Aceptable (cache para rendimiento). Recalculado via `recalcular_tiempo()`. |

### Totales — Auditoria 26/05/2026

| Metrica | Valor |
|---------|-------|
| Tablas totales | **26** (18 app + 8 Django) |
| Tablas de aplicacion | 18 |
| Apps | 7 |
| Foreign Keys | **37** (app-to-app) |
| Indexes (app) | 45 |
| Unique Constraints | **11** (incluyendo 3 condicionales) |
| Soft-delete | 16/18 tablas |
| Campos `codigo` auto-generados | 5 tablas |
| Indices de busqueda (`db_index`) | 9 |
| FK violations | **0** |
| DB integrity | **ok** |

---

## Reglas de Negocio en BD

1. **Unico EnCurso**: Un usuario no puede tener mas de una actividad "EnCurso" simultaneamente (UniqueConstraint condicional)
2. **Unico Traslado Pendiente**: No puede haber 2 solicitudes de traslado pendientes para la misma (origen, destino)
3. **Unico (plan, act, user)**: No se puede asignar la misma actividad al mismo usuario dos veces en la misma planificacion
4. **Validacion Jerarquica**: `Actividad.subarea_id == Actividad.tipo_actividad.subarea_id` (validado via `clean()`)
5. **Sincronizacion is_active**: `User.save()` sincroniza `is_active = activo`
6. **Soft-delete**: Ningun registro se elimina fisicamente, solo se marca `activo=False`
7. **Auditoria**: Toda accion POST/PUT/DELETE queda registrada en `audit_log`
8. **Cache de Tiempo**: Cada `RegistroTiempo.save()` recalcula `tiempo_total_segundos` y `tiempo_pausado_segundos` en la `AsignacionActividad`
9. **Prorroga**: El admin reprograma `fecha_vencimiento` e incrementa `prorroga_count`
10. **Reasignacion**: El admin reasigna actividad a otro usuario. Se marca `origen="Reasignado"`
11. **Fecha de Planificacion vs Vencimiento**: `fecha_limite` controla cuando aparece en el tablero (opcional, si vacia = inmediato). `fecha_vencimiento` es el deadline (obligatorio si `requiere_fecha_limite=True` en el TipoActividad)
12. **Inactivar Planificacion**: Solo si todas las actividades estan "Pendiente" (sin iniciar, pausar, finalizar). Backend bloquea via `planificacion_delete`
13. **Tiempo muerto**: Calculado en dashboard como gaps entre `Finalizacion/Traslado` y `Inicio/Reanudacion` del mismo dia. Excluye gaps entre dias diferentes.
14. **Importaciones**: Importacion masiva de Areas/SubAreas y Usuarios via Excel con validacion de codigos (empresa_codigo, area_codigo, subarea_codigo, rol_id)

---

## Historial de Cambios

| Fecha | Version | Cambio |
|------|---------|--------|
| 23/05/2026 | 1.0 | Documentacion inicial completa de las 17 tablas |
| 24/05/2026 | 2.0 | Kairos rebrand. `cargo` en usuario, `tiempo_total_segundos`, `tiempo_pausado_segundos`, `prorroga_count` en asignacion_actividad. `db_index` en 9 campos. Cache de tiempo. Reglas 8-10. |
| 26/05/2026 | 3.0 | **VIVA1A rebrand**. +`fecha_vencimiento` en PlanificacionDetalle (separacion planificacion vs vencimiento). Removido `django.contrib.admin`. Auditoria completa de BD (26 tablas, 37 FK, 0 violaciones). Reglas 11-14 (fecha_planificacion/vencimiento, inactivar planificacion, tiempo muerto, importaciones). Actualizados conteos y diagrama. |

