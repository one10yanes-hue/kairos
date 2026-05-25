# Kairos - Documentacion de Base de Datos

**Ultima actualizacion**: 24/05/2026
**Version**: 2.0
**Motor**: SQL Server via mssql-django
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
Empresa ──1:N── Area ──1:N── SubArea ──1:N── TipoActividad
                                          └──1:N── Actividad
                                                       │
User ──N:M── Empresa (via UserEmpresa)                  │
User ──N:M── SubArea (via UserSubArea)                  │
User ──1:N── Planificacion                              │
                │                                       │
                └──1:N── PlanificacionDetalle ──1:N── AsignacionActividad
                                                            │
                                                            ├──1:N── RegistroTiempo
                                                            ├──1:N── Comentario
                                                            ├──1:N── Colaboracion
                                                            ├──1:N── TrasladoActividad
                                                            │
User ──1:N── Rol
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

**Valores**: Master, Admin, Usuario

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

> **Logica**: Clasificacion de actividades. Ej: "Programada" (planificada por admin), "No Programada" (surge espontaneamente), "Mejora", "Procesos". Cada tipo pertenece a una SubArea. El campo `requiere_fecha_limite` controla si al planificar actividades de este tipo, la fecha limite es obligatoria u opcional.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| codigo | VARCHAR(6) | | SI | NULL | 🔒 Unique, ⚡ auto-generado |
| subarea_id | BIGINT | FK→subarea | NO | | 🔗 related_name="tipos_actividad" |
| nombre | VARCHAR(200) | | NO | | 🔍 db_index |
| descripcion | TEXT | | SI | NULL | |
| requiere_fecha_limite | BOOLEAN | | NO | TRUE | Si TRUE, fecha limite obligatoria en planificacion |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `actividad` — Actividades operativas

> **Logica**: Las actividades concretas que los usuarios ejecutan. Ej: "Causacion de Viaticos", "Programacion de Pagos", "Informe Mensual". Cada actividad pertenece a una SubArea y a un TipoActividad. La validacion `clean()` asegura que la actividad este en la misma subarea que su tipo (consistencia jerarquica).

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

> **Logica**: Representa una "planificacion" o "sprint" creado por un Admin para asignar actividades a usuarios de su subarea. Al crearse, se cierra automaticamente (`cerrada=True`) y no se pueden agregar mas actividades. Cada planificacion pertenece a una SubArea y tiene un Admin responsable. Las actividades asignadas se almacenan en `PlanificacionDetalle`.

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

> **Logica**: Cada registro vincula una actividad especifica a un usuario dentro de una planificacion, con una fecha limite opcional. La combinacion (planificacion, actividad, user) es unica para evitar duplicados. Al crear un detalle, el sistema crea automaticamente una `AsignacionActividad` para que la actividad aparezca en el tablero del usuario.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| planificacion_id | BIGINT | FK→planificacion | NO | | 🔗 related_name="detalles" |
| actividad_id | BIGINT | FK→actividad | NO | | 🔗 |
| user_id | BIGINT | FK→usuario | NO | | 🔗 |
| fecha_asignacion | DATETIME | | NO | now() | |
| fecha_limite | DATETIME | | SI | NULL | Nullable segun `requiere_fecha_limite` |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 Unique**: `(planificacion, actividad, user)` — No se puede asignar la misma actividad al mismo usuario en la misma planificacion

---

### gestion (6 tablas) — Nucleo del sistema

#### `asignacion_actividad` — Asignaciones activas en el tablero del usuario

> **Logica**: Tabla central del sistema. Cada registro representa una actividad que un usuario tiene en su tablero Trello. El `estado` determina en que columna aparece: Pendiente (Planificadas), EnCurso (En Curso), Pausada, Finalizada, Cancelada o Trasladada. El campo `origen` indica como llego: "Planificacion" (asignada por admin), "Traslado" (recibida de otro usuario), "Manual" (iniciada por el usuario mismo), "Reasignado" (cambiada por admin). `origen_user` es quien la asigno/traslado/reasigno. La constraint `unique_en_curso_por_usuario` garantiza que un usuario solo tenga UNA actividad en curso simultaneamente. Los campos `tiempo_total_segundos` y `tiempo_pausado_segundos` cachean los tiempos calculados para rendimiento. `prorroga_count` cuenta cuantas veces fue reprogramada por el admin.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| planificacion_detalle_id | BIGINT | FK→planificacion_detalle | SI | NULL | 🔗 SET_NULL |
| user_id | BIGINT | FK→usuario | NO | | 🔗 related_name="asignaciones" |
| actividad_id | BIGINT | FK→actividad | NO | | 🔗 |
| estado | VARCHAR(20) | | NO | Pendiente | Pendiente/EnCurso/Pausada/Finalizada/Cancelada/Trasladada |
| origen | VARCHAR(20) | | SI | NULL | Planificacion / Traslado / Manual |
| origen_user_id | BIGINT | FK→usuario | SI | NULL | 🔗 SET_NULL — Quien origino la asignacion |
| fecha_asignacion | DATETIME | | NO | now() | |
| tiempo_total_segundos | INTEGER | | NO | 0 | Cache: tiempo activo acumulado |
| tiempo_pausado_segundos | INTEGER | | NO | 0 | Cache: tiempo en pausa acumulado |
| prorroga_count | INTEGER | | NO | 0 | Veces reprogramado por admin |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 UniqueConstraint**: `fields=["user"], condition=Q(estado="EnCurso", activo=True)` — Un usuario solo puede tener 1 actividad EnCurso

---

#### `registro_tiempo` — Time tracking por evento

> **Logica**: Almacena cada evento de tiempo de una asignacion: cuando se inicio (`Inicio`), cuando se pauso (`Pausa` con motivo), cuando se reanudo (`Reanudacion`), cuando se finalizo (`Finalizacion` con comentario y nro_actividad), y cuando se traslado (`Traslado`). Con estos registros se calcula el tiempo efectivo (Inicio→Pausa + Reanudacion→Fin) y el tiempo pausado (Pausa→Reanudacion). Cada vez que se guarda un `RegistroTiempo`, se recalcula y cachea el tiempo en `AsignacionActividad` via `recalcular_tiempo()`.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| asignacion_id | BIGINT | FK→asignacion_actividad | NO | | 🔗 related_name="registros" |
| evento | VARCHAR(20) | | NO | | Inicio/Pausa/Reanudacion/Finalizacion/Traslado |
| motivo_pausa | VARCHAR(50) | | SI | NULL | Almuerzo/Descanso / Interrupcion / Cambio de prioridad / Otro |
| fecha_hora | DATETIME | | NO | now() | |
| comentario | TEXT | | SI | NULL | |
| nro_actividad | VARCHAR(50) | | SI | NULL | Cantidad realizada (ingresada manual por usuario) |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

---

#### `traslado_actividad` — Solicitudes de traslado entre usuarios

> **Logica**: Cuando un usuario quiere transferir una actividad a otro usuario, se crea una solicitud con estado `Pendiente`. El usuario destino ve la solicitud en su tablero y puede Aceptar (la actividad se transfiere, el origen inicia su reemplazo) o Rechazar (la solicitud se cancela). El origen tambien puede Cancelar la solicitud en cualquier momento. La constraint `unique_traslado_pendiente` evita multiples solicitudes pendientes para la misma combinacion (actividad_origen, usuario_destino).

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| asignacion_origen_id | BIGINT | FK→asignacion_actividad | NO | | 🔗 related_name="traslados_origen" |
| asignacion_destino_id | BIGINT | FK→asignacion_actividad | SI | NULL | 🔗 SET_NULL — Se setea al aceptar |
| user_origen_id | BIGINT | FK→usuario | NO | | 🔗 related_name="traslados_hechos" |
| user_destino_id | BIGINT | FK→usuario | NO | | 🔗 related_name="traslados_recibidos" |
| actividad_reemplazo_id | BIGINT | FK→actividad | SI | NULL | 🔗 — Actividad que el origen iniciara al aceptarse |
| estado | VARCHAR(20) | | NO | Pendiente | Pendiente/Aceptado/Cancelado/Rechazado |
| motivo | TEXT | | SI | NULL | |
| activo | BOOLEAN | | NO | TRUE | 🗑 |
| fecha_creacion | DATETIME | | NO | now() | 📅 |
| fecha_update | DATETIME | | NO | now() | 📅 |

**🔒 UniqueConstraint**: `fields=["asignacion_origen", "user_destino"], condition=Q(estado="Pendiente", activo=True)` — No hay 2 traslados pendientes para la misma (origen, destino)

---

#### `colaboracion` — Colaboracion entre usuarios en una asignacion

> **Logica**: Permite que un usuario colabore en la actividad de otro. No afecta el time tracking del colaborador, solo esta registrado como ayuda. La combinacion (asignacion, user_colaborador) es unica para evitar duplicados.

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

> **Logica**: Almacena los comentarios que los usuarios hacen sobre una asignacion especifica, visibles en el detalle de la actividad. Cada comentario tiene un autor (user_id) y pertenece a una asignacion.

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

> **Logica**: Registra automaticamente via middleware todas las acciones POST/PUT/DELETE del sistema. Almacena que usuario hizo que accion sobre que modelo, con detalle JSON adicional y direccion IP. Los logs son inmutables (no tienen soft-delete ni fecha_update). Sirven para trazabilidad y auditoria.

| Columna | Tipo | PK/FK | Null | Default | Constraint |
|---------|------|-------|------|---------|------------|
| id | BIGINT | PK | NO | AUTO | |
| user_id | BIGINT | FK→usuario | SI | NULL | 🔗 SET_NULL |
| accion | VARCHAR(50) | | NO | | CREATE / UPDATE / DELETE |
| modelo_afectado | VARCHAR(100) | | NO | | Nombre del modelo |
| id_registro | INTEGER | | SI | NULL | PK del registro afectado |
| detalle | JSON | | NO | {} | Metadata adicional |
| ip_address | GENERIC_IP | | SI | NULL | |
| fecha_creacion | DATETIME | | NO | now() | 📅 (sin update) |

**Sin soft-delete**: Los logs de auditoria nunca se eliminan

---

## Resumen de Normalizacion

### 1FN (Atomicidad) ✅
Todas las columnas son atomicas. No hay arreglos ni JSON para datos de negocio (JSONField solo en auditoria).

### 2FN (Dependencia parcial) ✅
Todas las tablas tienen PK simple (`id`). Ninguna dependencia parcial.

### 3FN (Dependencia transitiva) ⚠️

| Tabla | Columna | Dependencia | Estado |
|-------|---------|------------|--------|
| `actividad` | `subarea_id` | Derivable de `tipo_actividad.subarea_id` | ⚠️ Denormalizacion aceptable (performance). Validada por `clean()`. |
| `traslado_actividad` | `user_origen_id` | Derivable de `asignacion_origen.user_id` | ⚠️ Denormalizacion aceptable (auditoria historica). |
| `asignacion_actividad` | `actividad_id` | Derivable de `planificacion_detalle.actividad_id` | ⚠️ Denormalizacion aceptable (existe sin plan_detalle). |

### Totales

| Metrica | Valor |
|---------|-------|
| Tablas | 17 |
| Apps | 7 |
| Foreign Keys | 35 |
| Unique Constraints | 9 (incluyendo 2 condicionales) |
| Soft-delete | 15/17 tablas |
| Campos `codigo` auto-generados | 5 tablas |
| Indices de busqueda (`db_index`) | 9 campos |
| Cache de tiempo | `tiempo_total_segundos` + `tiempo_pausado_segundos` (AsignacionActividad) |

---

## Reglas de Negocio en BD

1. **Unico EnCurso**: Un usuario no puede tener mas de una actividad "EnCurso" simultaneamente (UniqueConstraint condicional)
2. **Unico Traslado Pendiente**: No puede haber 2 solicitudes de traslado pendientes para la misma combinacion (origen, destino)
3. **Unico (plan, act, user)**: En una planificacion, no se puede asignar la misma actividad al mismo usuario dos veces
4. **Validacion Jerarquica**: Actividad.subarea debe coincidir con TipoActividad.subarea (validacion via clean())
5. **Sincronizacion is_active**: `User.save()` sincroniza `is_active = activo`
6. **Soft-delete**: Ningun registro se elimina fisicamente, solo se marca `activo=False`
7. **Auditoria**: Toda accion POST/PUT/DELETE queda registrada en `audit_log`
8. **Cache de Tiempo**: Cada `RegistroTiempo.save()` recalcula `tiempo_total_segundos` y `tiempo_pausado_segundos` en la `AsignacionActividad` correspondiente
9. **Prorroga**: El admin puede reprogramar una actividad pendiente. Cada reprogramacion incrementa `prorroga_count`
10. **Reasignacion**: El admin puede reasignar una actividad a otro usuario. Se marca `origen="Reasignado"` y `origen_user=admin`

---

## Historial de Cambios

| Fecha | Version | Cambio |
|------|---------|--------|
| 23/05/2026 | 1.0 | Documentacion inicial completa de las 17 tablas |
| 24/05/2026 | 2.0 | Kairos rebrand. Agregados: `cargo` en usuario, `tiempo_total_segundos`, `tiempo_pausado_segundos`, `prorroga_count` en asignacion_actividad. `db_index=True` en 9 campos de busqueda. `Empresa.save()` ahora auto-genera codigo. Cache de tiempo activo/pausado con `recalcular_tiempo()`. Reglas de negocio 8-10 (cache, prorroga, reasignacion). |
