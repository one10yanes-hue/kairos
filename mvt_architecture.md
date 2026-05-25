# Kairos - Arquitectura MVT (Model-View-Template)

**Ultima actualizacion**: 24/05/2026
**Version**: 2.0
**Framework**: Django 5.0.x
**Base de datos**: SQL Server via mssql-django

---

## Indice
1. [¿Que es MVT?](#que-es-mvt)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Apps y sus Responsabilidades](#apps-y-sus-responsabilidades)
4. [Mapeo Completo de Rutas (Model → View → Template)](#mapeo-completo-de-rutas)
5. [Flujo de Datos](#flujo-de-datos)
6. [Seguridad por Ruta](#seguridad-por-ruta)

---

## ¿Que es MVT?

Django sigue el patron **MVT** (Model-View-Template), una variante del clasico MVC:

| Componente | Rol | Analogia MVC |
|-----------|-----|-------------|
| **Model** | Define la estructura de datos en BD (ORM) | Model |
| **View** | Contiene la logica de negocio y orquesta la respuesta | Controller |
| **Template** | Renderiza la interfaz de usuario (HTML + CSS + JS) | View |

**Flujo tipico en VIVA1A:**
```
Usuario → URL → View (consulta Model) → Template (renderiza HTML) → Usuario
```

---

## Estructura del Proyecto

```
viva1a/
├── config/                       # Configuracion global Django
│   ├── settings.py               # Settings (DB, apps instaladas, middleware)
│   ├── urls.py                   # URL raiz (redireccion por rol)
│   └── wsgi.py / asgi.py         # Entry points WSGI/ASGI
├── apps/
│   ├── accounts/                 # Autenticacion y usuarios
│   ├── estructura/               # Jerarquia Empresa → Area → SubArea
│   ├── actividades/              # Tipos de actividad y actividades
│   ├── planificacion/            # Planificaciones del admin
│   ├── gestion/                  # Core: Trello, time-tracking, traslados
│   ├── dashboard/                # Dashboard admin con indicadores
│   ├── reportes/                 # Exportacion Excel
│   ├── auditoria/                # Logs de trazabilidad
│   └── core/                     # Utilidades compartidas (generacion de IDs)
├── static/                       # Archivos estaticos
│   ├── css/                      # main.css, sidebar.css, gestion.css, etc.
│   ├── js/                       # sidebar.js, dynamic-select.js, main.js
│   └── img/
└── templates/                    # Templates HTML por modulo
    ├── base.html                 # Layout base con sidebar
    ├── partials/                 # Fragmentos reutilizables
    └── {cada_app}/               # Templates especificos de cada app
```

---

## Apps y sus Responsabilidades

| App | Modelos | Vistas | Templates | Rol |
|-----|---------|--------|-----------|-----|
| **accounts** | `Rol`, `User`, `Empresa`, `UserEmpresa` | Login/logout, CRUD usuarios, asignar empresas | login.html, usuarios.html, usuario_form.html | Autenticacion + usuarios |
| **estructura** | `Area`, `SubArea`, `UserSubArea` | CRUD areas/subareas, asignar usuarios a subareas, importacion Excel | area_list.html, subarea_list.html, importar.html | Jerarquia organizacional |
| **actividades** | `TipoActividad`, `Actividad` | CRUD tipos y actividades | tipo_list.html, actividad_list.html | Catalogo de actividades |
| **planificacion** | `Planificacion`, `PlanificacionDetalle` | Crear planificaciones, asignar actividades a usuarios | planificacion_list.html, planificacion_detail.html | Planificacion admin |
| **gestion** | `AsignacionActividad`, `RegistroTiempo`, `TrasladoActividad`, `Colaboracion`, `Comentario` | Tablero Trello, time-tracking, traslados, calendario | tablero.html, detalle_actividad.html, calendario.html | Core del sistema |
| **dashboard** | (usa modelos de gestion) | Dashboard admin, progreso equipo | dashboard_admin.html, progreso.html | Indicadores |
| **reportes** | (usa modelos de gestion/estructura) | Exportacion Excel | reporte_list.html | Exportacion |
| **auditoria** | `AuditLog` | (middleware automatico) | - | Logs |
| **core** | - | `generar_codigo()` | - | Utilidades |

---

## Mapeo Completo de Rutas (Model → View → Template)

### Leyenda
- `🔓` = Acceso publico
- `🔐` = Requiere autenticacion
- `👑` = Solo Master
- `🛡️` = Admin + Master
- `👤` = Cualquier autenticado (usuario tipicamente)

---

### `/login/`, `/logout/` — Autenticacion

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET/POST | `/login/` | `accounts.views.login_view` | `accounts/login.html` | `User` | 🔓 |
| GET | `/logout/` | `accounts.views.logout_view` | redirect | - | 🔓 |

**Logica**: El login usa cedula + fecha_expedicion (no password). Backend custom: `CedulaExpedicionBackend`.

---

### `/master/` — Rutas de Master (Jerarquia + Usuarios)

#### Empresas

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/master/empresas/` | `estructura.views.empresa_list` | `estructura/empresa_list.html` | `Empresa` | 👑 |
| GET/POST | `/master/empresas/crear/` | `estructura.views.empresa_create` | `estructura/empresa_form.html` | `Empresa` | 👑 |
| GET/POST | `/master/empresas/editar/<pk>/` | `estructura.views.empresa_edit` | `estructura/empresa_form.html` | `Empresa` | 👑 |
| GET | `/master/empresas/eliminar/<pk>/` | `estructura.views.empresa_delete` | redirect | `Empresa` | 👑 |

#### Areas

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/master/areas/` | `estructura.views.area_list` | `estructura/area_list.html` | `Area`, `Empresa` | 👑 |
| GET/POST | `/master/areas/crear/` | `estructura.views.area_create` | `estructura/area_form.html` | `Area`, `Empresa` | 👑 |
| GET/POST | `/master/areas/editar/<pk>/` | `estructura.views.area_edit` | `estructura/area_form.html` | `Area` | 👑 |
| GET | `/master/areas/eliminar/<pk>/` | `estructura.views.area_delete` | redirect | `Area` | 👑 |

#### SubAreas

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/master/subareas/` | `estructura.views.subarea_list` | `estructura/subarea_list.html` | `SubArea`, `Area`, `Empresa` | 👑 |
| GET/POST | `/master/subareas/crear/` | `estructura.views.subarea_create` | `estructura/subarea_form.html` | `SubArea`, `User` | 👑 |
| GET/POST | `/master/subareas/editar/<pk>/` | `estructura.views.subarea_edit` | `estructura/subarea_form.html` | `SubArea`, `User` | 👑 |
| GET | `/master/subareas/eliminar/<pk>/` | `estructura.views.subarea_delete` | redirect | `SubArea` | 👑 |
| GET/POST | `/master/subareas/<pk>/usuarios/` | `estructura.views.subarea_usuarios` | `estructura/subarea_usuarios.html` | `UserSubArea`, `User` | 👑 |
| GET | `/master/subareas/<pk>/usuarios/<upk>/remover/` | `estructura.views.subarea_usuario_remove` | redirect | `UserSubArea` | 👑 |

#### Importacion/Exportacion (Master)

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/master/importar/` | `estructura.views.importar_exportar` | `estructura/importar.html` | - | 👑 |
| GET | `/master/importar/template/` | `estructura.views.descargar_template` | Excel file | `Empresa`, `Area`, `SubArea`, `User`, `TipoActividad`, `Actividad` | 👑 |
| POST | `/master/importar/subir/` | `estructura.views.importar_datos` | redirect | Todos los anteriores | 👑 |

#### Usuarios (via accounts)

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/master/usuarios/` | `accounts.views.master_usuarios` | `accounts/usuarios.html` | `User`, `Rol` | 👑 |
| GET/POST | `/master/usuarios/crear/` | `accounts.views.master_usuario_create` | `accounts/usuario_form.html` | `User`, `UserEmpresa`, `UserSubArea` | 👑 |
| GET/POST | `/master/usuarios/editar/<pk>/` | `accounts.views.master_usuario_edit` | `accounts/usuario_form.html` | `User`, `UserEmpresa`, `UserSubArea` | 👑 |
| GET | `/master/usuarios/eliminar/<pk>/` | `accounts.views.master_usuario_delete` | redirect | `User` | 👑 |
| GET/POST | `/master/usuarios/<pk>/empresas/` | `accounts.views.master_usuario_empresas` | `accounts/usuario_empresas.html` | `UserEmpresa`, `Empresa` | 👑 |
| GET | `/master/usuarios/<pk>/empresas/<epk>/remover/` | `accounts.views.master_usuario_empresa_remove` | redirect | `UserEmpresa` | 👑 |

#### API (usada por todos los roles via AJAX)

| Metodo | URL | View | Modelos | Proteccion |
|--------|-----|------|---------|------------|
| GET | `/master/api/buscar/<modelo>/` | `estructura.views.api_buscar` | Segun modelo | 🔐 (scope por rol) |

**Nota**: Aunque la URL esta bajo `/master/`, la API es accesible por cualquier usuario autenticado. El scope se ajusta segun el rol (Admin solo ve sus subareas, Usuario solo ve sus datos).

---

### `/admin/` — Rutas de Admin + Master

#### Dashboard

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/admin/dashboard/` | `dashboard.views.dashboard_admin` | `dashboard/dashboard_admin.html` | `AsignacionActividad`, `User`, `SubArea` | 🛡️ |
| GET | `/admin/progreso/` | `dashboard.views.progreso` | `dashboard/progreso.html` | `AsignacionActividad` | 🛡️ |

#### Tipos de Actividad

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/admin/tipos/` | `actividades.views.tipo_actividad_list` | `actividades/tipo_list.html` | `TipoActividad` | 🛡️ |
| GET/POST | `/admin/tipos/crear/` | `actividades.views.tipo_actividad_create` | `actividades/tipo_form.html` | `TipoActividad` | 🛡️ |
| GET/POST | `/admin/tipos/editar/<pk>/` | `actividades.views.tipo_actividad_edit` | `actividades/tipo_form.html` | `TipoActividad` | 🛡️ |
| GET | `/admin/tipos/eliminar/<pk>/` | `actividades.views.tipo_actividad_delete` | redirect | `TipoActividad` | 🛡️ |

#### Actividades

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/admin/actividades/` | `actividades.views.actividad_list` | `actividades/actividad_list.html` | `Actividad`, `TipoActividad` | 🛡️ |
| GET/POST | `/admin/actividades/crear/` | `actividades.views.actividad_create` | `actividades/actividad_form.html` | `Actividad` | 🛡️ |
| GET/POST | `/admin/actividades/editar/<pk>/` | `actividades.views.actividad_edit` | `actividades/actividad_form.html` | `Actividad` | 🛡️ |
| GET | `/admin/actividades/eliminar/<pk>/` | `actividades.views.actividad_delete` | redirect | `Actividad` | 🛡️ |

#### Planificaciones

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/admin/planificaciones/` | `planificacion.views.planificacion_list` | `planificacion/planificacion_list.html` | `Planificacion`, `SubArea` | 🛡️ |
| GET/POST | `/admin/planificaciones/crear/` | `planificacion.views.planificacion_create` | `planificacion/planificacion_form.html` | `Planificacion`, `PlanificacionDetalle`, `AsignacionActividad` | 🛡️ |
| GET | `/admin/planificaciones/<pk>/` | `planificacion.views.planificacion_detail` | `planificacion/planificacion_detail.html` | `PlanificacionDetalle` | 🛡️ |
| GET | `/admin/planificaciones/<pk>/eliminar/` | `planificacion.views.planificacion_delete` | redirect | `Planificacion` | 🛡️ |
| GET | `/admin/planificaciones/<plan_pk>/detalle/<det_pk>/eliminar/` | `planificacion.views.planificacion_detalle_remove` | redirect | `PlanificacionDetalle`, `AsignacionActividad` | 🛡️ |
| POST | `/admin/pendiente/<pk>/reprogramar/` | `planificacion.views.reprogramar_pendiente` | redirect | `AsignacionActividad`, `PlanificacionDetalle` | 🛡️ |
| POST | `/admin/pendiente/<pk>/reasignar/` | `planificacion.views.reasignar_pendiente` | redirect | `AsignacionActividad`, `User` | 🛡️ |
| POST | `/admin/pendiente/<pk>/cancelar/` | `planificacion.views.cancelar_pendiente` | redirect | `AsignacionActividad` | 🛡️ |

#### Reportes

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/admin/reportes/` | `reportes.views.reporte_list` | `reportes/reporte_list.html` | `AsignacionActividad`, `RegistroTiempo` | 🛡️ |
| GET | `/admin/reportes/exportar/` | `reportes.views.exportar_completo` | Excel file | Todos | 🛡️ |

---

### `/usuario/` — Rutas de Usuario

#### Tablero Trello

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/usuario/tablero/` | `gestion.views.tablero` | `gestion/tablero.html` | `AsignacionActividad`, `UserSubArea` | 👤 |
| GET/POST | `/usuario/actividad/no-programada/crear/` | `gestion.views.crear_no_programada` | `gestion/crear_no_programada.html` | `Actividad`, `AsignacionActividad` | 👤 |

#### Acciones sobre Actividades

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| POST | `/usuario/actividad/<pk>/iniciar/` | `gestion.views.activar_actividad` | redirect | `AsignacionActividad`, `RegistroTiempo` | 👤 |
| POST | `/usuario/actividad/<pk>/pausar/` | `gestion.views.pausar_actividad` | redirect | `AsignacionActividad`, `RegistroTiempo` | 👤 |
| POST | `/usuario/actividad/<pk>/finalizar/` | `gestion.views.finalizar_actividad` | redirect | `AsignacionActividad`, `RegistroTiempo` | 👤 |
| POST | `/usuario/actividad/<pk>/trasladar/` | `gestion.views.trasladar_actividad` | redirect | `TrasladoActividad` | 👤 |
| POST | `/usuario/actividad/<pk>/comentar/` | `gestion.views.agregar_comentario` | redirect | `Comentario` | 👤 |
| GET | `/usuario/actividad/<pk>/detalle/` | `gestion.views.detalle_actividad` | `gestion/detalle_actividad.html` | `RegistroTiempo`, `Comentario`, `TrasladoActividad` | 👤 |

#### Traslados (Aceptar/Rechazar)

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| POST | `/usuario/traslado/<pk>/aceptar/` | `gestion.views.aceptar_traslado` | redirect | `TrasladoActividad`, `AsignacionActividad` | 👤 |
| POST | `/usuario/traslado/<pk>/cancelar/` | `gestion.views.cancelar_traslado` | redirect | `TrasladoActividad` | 👤 |

#### Calendario

| Metodo | URL | View | Template | Modelos | Proteccion |
|--------|-----|------|----------|---------|------------|
| GET | `/usuario/calendario/` | `gestion.views.calendario` | `gestion/calendario.html` | `AsignacionActividad` | 👤 |

#### API (usuario)

| Metodo | URL | View | Modelos | Proteccion |
|--------|-----|------|---------|------------|
| GET | `/usuario/api/usuarios/buscar/` | `gestion.views.buscar_usuarios_traslado` | `User` | 👤 |
| GET | `/usuario/api/actividades/buscar/` | `gestion.views.buscar_actividades_reemplazo` | `Actividad` | 👤 |

---

## Flujo de Datos

### Ejemplo 1: Login

```
1. Usuario ingresa cedula + fecha_expedicion en login.html
2. POST a login_view
3. View llama a authenticate(cedula=..., fecha_expedicion=...)
4. CedulaExpedicionBackend busca User.cedula y compara fecha_expedicion
5. Si coincide: auth_login() crea sesion, redirect segun rol
6. Si no: messages.error, vuelve a login.html
```

```
Model: User.objects.get(cedula=...)
View:  accounts.views.login_view
Template: accounts/login.html
```

### Ejemplo 2: Usuario inicia actividad

```
1. Usuario hace clic en "Iniciar" en tablero.html
2. POST a /usuario/actividad/<pk>/iniciar/
3. activar_actividad:
   a. Verifica que la asignacion pertenezca al usuario
   b. Verifica estado = Pendiente o Pausada
   c. _pausar_activas() - pausa cualquier otra EnCurso
   d. Estado → EnCurso
   e. Crea RegistroTiempo(evento="Inicio")
4. redirect a tablero
```

```
Model: AsignacionActividad, RegistroTiempo
View:  gestion.views.activar_actividad
Template: gestion/tablero.html (via redirect)
```

### Ejemplo 3: Admin crea planificacion

```
1. Admin llena formulario con subarea, actividades, usuarios, fecha_limite en planificacion_form.html
2. POST a /admin/planificaciones/crear/
3. planificacion_create:
   a. Valida formulario + actividades + usuarios
   b. Crea Planificacion(cerrada=True)
   c. Por cada actividad × usuario:
      - Crea PlanificacionDetalle
      - Crea AsignacionActividad(origen="Planificacion")
4. redirect a planificacion_detail
```

```
Model: Planificacion, PlanificacionDetalle, AsignacionActividad
View:  planificacion.views.planificacion_create
Template: planificacion/planificacion_form.html
```

---

## Seguridad por Ruta

| Decorator | Permite | Lo usan |
|-----------|---------|---------|
| `@login_required` | Cualquier user autenticado | `gestion/*`, `accounts/master/usuarios/*` |
| `@login_required` + `@master_required` | Solo `rol=Master` | `estructura/*`, `accounts/master/usuarios/*` |
| `@login_required` + `@admin_required` | `rol=Admin` o `rol=Master` | `actividades/*`, `planificacion/*`, `dashboard/*`, `reportes/*` |
| `@login_required` + `@admin_required` + `@ensure_csrf_cookie` | Admin/Master + CSRF | `planificacion_create`, `planificacion_detail` |
| `@login_required` + owner check | Solo el propietario de la asignacion | `activar_actividad`, `pausar_actividad`, etc. |

**Regla general:**
- 👑 **Master** → todo (`/master/*`, `/admin/*`, `/usuario/*`)
- 🛡️ **Admin** → `/admin/*` (sus subareas) + `/usuario/*` (su propio tablero)
- 👤 **Usuario** → solo `/usuario/*`
- API (`/master/api/buscar/`) → todos autenticados, con scope segun rol

---

## Resumen de Archivos

| Tipo | Cantidad | Descripcion |
|------|----------|-------------|
| Modelos (models.py) | 17 clases en 7 archivos | Toda la logica de datos |
| Vistas (views.py) | ~60 funciones en 8 archivos | Toda la logica de negocio |
| Templates (HTML) | 30 archivos | Interfaz de usuario |
| CSS | 5 archivos | Estilos separados por modulo |
| JS | 4 archivos | Scripts separados por modulo |
| URL config | 10 archivos (1 principal + 9 por app) | Enrutamiento completo |
