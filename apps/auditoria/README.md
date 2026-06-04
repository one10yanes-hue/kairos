# VIVA1A - Sistema de Auditoria

## Estructura

Una sola tabla `audit_log` con:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `user` | FK→usuario | Quien ejecuto la accion |
| `accion` | VARCHAR(50) | CREATE / UPDATE / DELETE |
| `modelo_afectado` | VARCHAR(100) | Nombre del modelo (extraido de URL) |
| `id_registro` | INTEGER | PK del registro afectado (extraido de URL) |
| `detalle` | JSON | path, method, data, user_agent, referer |
| `ip_address` | IP | Direccion IP del usuario |
| `fecha_creacion` | DATETIME | Momento del evento |

## Comportamiento del Middleware

Se activa en toda request POST/PUT/PATCH/DELETE con usuario autenticado.

### Que NO se loguea
- `/login/`, `/logout/` (excluidos explicitamente)
- Archivos estaticos `/static/`, `/media/`
- Usuarios no autenticados

### Extraccion de `id_registro`
El middleware parsea la URL en busca de numeros. Ejemplos:

| URL | Modelo | id_registro |
|-----|--------|-------------|
| `/master/usuarios/editar/4/` | User | 4 |
| `/admin/planificaciones/3/` | Planificacion | 3 |
| `/admin/actividades/editar/1/` | Actividad | 1 |
| `/usuario/actividad/5/iniciar/` | AsignacionActividad | 5 |
| `/admin/importaciones/subir/` | Importacion | null |

### Datos capturados en POST
Se incluye el contenido del formulario (`request.POST`) con:
- Passwords y CSRF tokens reemplazados por `***FILTERED***`
- Valores largos (>200 chars) truncados
- Listas preservadas (ej: `empresas=[1,2,3]`)

### Metadata adicional
- `user_agent`: Browser del usuario (primeros 200 chars)
- `referer`: Pagina desde la que se envio el formulario

## Tablas faltantes (propuesta)

Para trazabilidad completa se recomienda agregar:

### `audit_log_change` (field-level diff)
```sql
CREATE TABLE audit_log_change (
    id BIGINT PK,
    log_id FK→audit_log,
    campo VARCHAR(100),
    valor_anterior TEXT,
    valor_nuevo TEXT
);
```
Almacena cada campo modificado en un UPDATE, con su valor anterior y nuevo. Permite responder "que cambio exactamente".

### `audit_session` (sesiones activas)
```sql
CREATE TABLE audit_session (
    id BIGINT PK,
    user_id FK→usuario,
    session_key VARCHAR(40),
    ip_address IP,
    user_agent TEXT,
    inicio DATETIME,
    fin DATETIME
);
```
Registra cada inicio/fin de sesion con IP y browser para trazabilidad de accesos.

## Integridad actual
- 55 registros en `audit_log` (26/05/2026)
- Sin soft-delete (logs inmutables)
- Sin FK violations
