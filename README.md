# Kairos — Sistema de Gestión de Productividad

**Versión:** 3.0  
**Última actualización:** 24/05/2026  
**Framework:** Django 5.0.x (MVT)  
**Base de datos:** SQL Server (mssql-django)  
**Python:** 3.10+  

---

## Índice
1. [Descripción General](#descripción-general)
2. [Requisitos Previos](#requisitos-previos)
3. [Instalación y Configuración](#instalación-y-configuración)
4. [Configuración SQL Server](#configuración-sql-server)
5. [Semillas Iniciales (Seed Data)](#semillas-iniciales)
6. [Estructura del Proyecto](#estructura-del-proyecto)
7. [Roles y Permisos](#roles-y-permisos)
8. [URLs del Sistema](#urls-del-sistema)
9. [Tecnologías Utilizadas](#tecnologías-utilizadas)
10. [Comandos Útiles](#comandos-útiles)
11. [Variables de Entorno](#variables-de-entorno)

---

## Descripción General

Kairos es un sistema de gestión de productividad con **time-tracking** por evento. Los administradores planifican actividades y las asignan a usuarios, quienes las ejecutan en un tablero estilo Trello con cronometraje de tiempo activo y pausado.

### Características

- Multiempresa con jerarquía organizacional (Empresa → Área → SubÁrea)
- 3 roles: **Master**, **Admin**, **Usuario**
- Login con cédula + fecha de expedición (auth backend custom)
- Tablero estilo **Trello** con 4 columnas (Planificadas, En Curso, Pausadas, Finalizadas)
- Time-tracking por evento (Inicio, Pausa, Reanudación, Finalización, Traslado)
- Tiempo activo y pausado cronometrado por separado
- Prórroga de actividades (reprogramar pendientes al día siguiente)
- Traslado de actividades entre usuarios (solicitud pendiente → aceptar/rechazar)
- Dashboard con KPIs, gráficos (Chart.js) y filtros por subárea/usuario/fecha
- Línea de Tiempo visual con **vis-timeline** (Gantt por usuario con segmentos activo/pausado)
- Exportación Excel con 3 hojas (openpyxl)
- Importación de áreas/subáreas vía Excel con códigos automáticos
- Calendario con 3 vistas (Mes/Semana/Día) y timeline horario
- Notificaciones toast (Bootstrap, auto-dismiss 6s)
- Soft-delete en todos los modelos (campo `activo`)
- Auditoría HTTP (middleware)
- 15 reglas de negocio documentadas

---

## Requisitos Previos

| Componente | Requisito |
|-----------|----------|
| **Sistema Operativo** | Windows 10/11, Linux, macOS |
| **Python** | 3.10 o superior |
| **SQL Server** | 2017+ (Express, Developer, Standard) |
| **ODBC Driver 17** | Para conectar Python ↔ SQL Server |
| **Navegador** | Chrome, Firefox, Edge (últimas versiones) |

### Verificar Python
```bash
python --version   # Debe mostrar 3.10+
```

### Instalar ODBC Driver 17 for SQL Server
Descargar e instalar desde:  
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

---

## Instalación y Configuración

### 1. Clonar o copiar el proyecto

```bash
git clone <repo-url> kairos
cd kairos/viva1a
```

### 2. Crear entorno virtual

```bash
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Linux/Mac
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear archivo `.env` en la raíz del proyecto (`viva1a/`):

```env
DEBUG=True
SECRET_KEY=django-insecure-dev-key-change-in-production
ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=mssql
DB_NAME=viva1a_db
DB_HOST=localhost\SQLEXPRESS
DB_OPTIONS_TRUST_CERT=True
```

Si usas **Windows Authentication** (Trusted Connection) en vez de usuario/contraseña:

```env
DB_OPTIONS_DRIVER=ODBC Driver 17 for SQL Server
DB_OPTIONS_EXTRA_PARAMS=Trusted_Connection=yes;
```

### 5. Crear base de datos en SQL Server

```sql
CREATE DATABASE viva1a_db;
GO
```

### 6. Ejecutar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Cargar datos iniciales (seed)

```bash
python manage.py seed_data
```

Esto crea roles, empresa, áreas, subáreas, tipos de actividad y usuarios de prueba.

### 8. Iniciar servidor

```bash
python manage.py runserver
```

Abrir: **http://127.0.0.1:8000**

---

## Configuración SQL Server

### Opción A: SQL Server Express (Windows Auth)
```
Server: localhost\SQLEXPRESS
Database: viva1a_db
Trusted_Connection: yes
```

Configurar en `.env`:
```env
DB_HOST=localhost\SQLEXPRESS
DB_OPTIONS_EXTRA_PARAMS=Trusted_Connection=yes;
```

### Opción B: SQL Server con autenticación SQL
```env
DB_USER=sa
DB_PASSWORD=Admin1234!
DB_HOST=localhost
DB_PORT=1433
```

### Verificar conexión ODBC (PowerShell)
```powershell
$conn = New-Object System.Data.SqlClient.SqlConnection
$conn.ConnectionString = "Server=localhost\SQLEXPRESS;Database=viva1a_db;Trusted_Connection=True;TrustServerCertificate=True;"
$conn.Open(); $conn.Close()
Write-Host "OK"
```

---

## Semillas Iniciales

Al ejecutar `python manage.py seed_data` se crean:

### Usuarios de prueba

| Nombre | Rol | Cédula | Fecha Exp. | Password |
|--------|-----|--------|------------|----------|
| **Humberto Yanes** | Master | 1044432944 | 2020-01-01 | 1234 |
| **Andrea Chavez** | Admin | 200 | 2020-01-01 | 1234 |
| **Juan Perez** | Usuario | 300 | 2020-01-01 | 1234 |
| **Pedro Ramirez** | Usuario | 400 | 2020-01-01 | 1234 |

### Empresa
- VIVA1A SAS (NIT: 900123456-7)

### Estructura jerárquica
- Financiera → Contabilidad, Tesorería
- Talento Humano → Nómina, Selección
- Operaciones → Procesos

### Tipos de Actividad
- Programada
- No Programada
- Mejora
- Procesos

---

## Estructura del Proyecto

```
viva1a/
├── manage.py
├── requirements.txt
├── .env                          # Variables de entorno (NO versionar)
├── config/
│   ├── settings.py               # DB, apps, auth, CSRF, timezone
│   ├── urls.py                   # URL raíz + redirección por rol
│   ├── views.py                  # CSRF failure handler
│   └── wsgi.py
├── apps/
│   ├── accounts/                 # Usuarios, roles, empresas, login
│   │   ├── models.py             # Rol, User, Empresa, UserEmpresa
│   │   ├── backends.py           # Auth backend cédula+expedición
│   │   ├── views.py              # Login, CRUD usuarios (Master)
│   │   ├── forms.py
│   │   └── management/commands/seed_data.py
│   ├── estructura/               # Jerarquía organizacional
│   │   ├── models.py             # Area, SubArea, UserSubArea
│   │   ├── views.py              # CRUD + API busca + import/export
│   │   ├── forms.py
│   │   └── urls.py
│   ├── actividades/              # Catálogo de actividades
│   │   ├── models.py             # TipoActividad, Actividad
│   │   ├── views.py
│   │   └── forms.py
│   ├── planificacion/            # Planificaciones del Admin
│   │   ├── models.py             # Planificacion, PlanificacionDetalle
│   │   ├── views.py              # CRUD + prórroga/reasignar/cancelar
│   │   └── forms.py
│   ├── gestion/                  # Core: tablero, time-tracking
│   │   ├── models.py             # AsignacionActividad, RegistroTiempo,
│   │   │                           TrasladoActividad, Colaboracion, Comentario
│   │   ├── views.py              # Tablero, iniciar/pausar/finalizar,
│   │   │                           trasladar, calendario, perfil
│   │   ├── forms.py
│   │   └── urls.py
│   ├── dashboard/                # KPIs admin
│   │   ├── views.py              # Dashboard, Progreso, Línea de Tiempo
│   │   └── urls.py
│   ├── reportes/                 # Exportación Excel
│   │   ├── views.py              # Reportes con openpyxl
│   │   └── urls.py
│   ├── auditoria/                # Logs de acciones
│   │   ├── models.py             # AuditLog
│   │   └── middleware.py         # AuditMiddleware
│   └── core/                     # Utilidades
│       └── utils.py              # generar_codigo()
├── static/
│   ├── css/
│   │   ├── main.css
│   │   ├── sidebar.css
│   │   ├── gestion.css
│   │   ├── dashboard.css
│   │   ├── reportes.css
│   │   └── linea_tiempo.css
│   └── js/
│       ├── main.js
│       ├── sidebar.js
│       ├── dynamic-select.js
│       └── linea_tiempo.js
├── templates/
│   ├── base.html
│   ├── 403_csrf.html
│   ├── 404.html
│   ├── 500.html
│   ├── partials/
│   │   ├── sidebar_menu.html
│   │   └── pagination.html
│   ├── accounts/                 # login, usuarios, usuario_form
│   ├── estructura/               # empresas, areas, subareas, importar
│   ├── actividades/              # tipos, actividades
│   ├── planificacion/            # planificaciones
│   ├── gestion/                  # tablero, calendario, detalle, perfil
│   ├── dashboard/                # dashboard_admin, progreso, linea_tiempo
│   └── reportes/                 # reporte_list
└── media/                        # Archivos subidos (logos)
```

---

## Roles y Permisos

| | Master | Admin | Usuario |
|---|--------|-------|---------|
| **Empresas / Áreas / SubÁreas** | CRUD | Solo ve las suyas | Solo ve las suyas |
| **Usuarios** | CRUD + asignar | No | No |
| **Tipos / Actividades** | CRUD | CRUD en sus subáreas | No |
| **Planificaciones** | Crear + Gestionar | Crear + Gestionar | No |
| **Dashboard** | Global + filtros | Su equipo + filtros | No |
| **Línea de Tiempo** | Ver todos | Ver su equipo | No |
| **Progreso** | Todos | Su equipo | No |
| **Reportes** | Exportar Excel | Exportar Excel | No |
| **Importar Datos** | Sí | No | No |
| **Tablero Trello** | No (usa admin) | No | Sí |
| **Calendario** | No | No | Sí |
| **Perfil** | No | No | Sí |

---

## URLs del Sistema

### Públicas
| URL | Descripción |
|-----|------------|
| `/login/` | Login con cédula + fecha expedición |
| `/logout/` | Cerrar sesión |

### Master (`/master/`)
| URL | Descripción |
|-----|------------|
| `/master/empresas/` | CRUD Empresas |
| `/master/areas/` | CRUD Áreas |
| `/master/subareas/` | CRUD SubÁreas + asignar usuarios |
| `/master/usuarios/` | CRUD Usuarios |
| `/master/usuarios/crear/` | Crear usuario (formulario centrado) |
| `/master/importar/` | Importar áreas/subáreas vía Excel |
| `/master/api/buscar/<modelo>/` | API búsqueda dinámica (AJAX) |

### Admin (`/admin/`)
| URL | Descripción |
|-----|------------|
| `/admin/dashboard/` | Dashboard con KPIs, gráficos, filtros |
| `/admin/progreso/` | Progreso detallado con filtros y paginación |
| `/admin/linea-tiempo/` | Línea de tiempo visual (vis-timeline Gantt) |
| `/admin/tipos/` | CRUD Tipos de Actividad |
| `/admin/actividades/` | CRUD Actividades |
| `/admin/planificaciones/` | CRUD Planificaciones |
| `/admin/planificaciones/crear/` | Crear planificación (formulario con AJAX tipeo) |
| `/admin/planificaciones/<pk>/` | Detalle + Pendientes por Gestionar |
| `/admin/pendiente/<pk>/reprogramar/` | Prórroga (POST) |
| `/admin/pendiente/<pk>/reasignar/` | Reasignar usuario (POST) |
| `/admin/pendiente/<pk>/cancelar/` | Cancelar actividad (POST) |
| `/admin/reportes/` | Exportar reporte Excel con filtros |

### Usuario (`/usuario/`)
| URL | Descripción |
|-----|------------|
| `/usuario/tablero/` | Tablero Trello (4 columnas + Hoy + Traslados) |
| `/usuario/calendario/` | Calendario Mes / Semana / Día |
| `/usuario/perfil/` | Perfil con estadísticas personales |
| `/usuario/actividad/<pk>/iniciar/` | Iniciar actividad (POST) |
| `/usuario/actividad/<pk>/pausar/` | Pausar actividad (POST, overlay) |
| `/usuario/actividad/<pk>/finalizar/` | Finalizar actividad (POST, overlay con reemplazo) |
| `/usuario/actividad/<pk>/trasladar/` | Trasladar actividad (POST, overlay) |
| `/usuario/actividad/<pk>/detalle/` | Detalle con línea de tiempo y comentarios |
| `/usuario/actividad/no-programada/crear/` | Evento Flash (iniciar no programada) |

---

## Tecnologías Utilizadas

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Backend | Django | 5.0.14 |
| Base de Datos | SQL Server | 2017+ |
| Conector DB | mssql-django | 1.7.2 |
| Driver ODBC | pyodbc | 5.3.0 |
| Frontend CSS | Bootstrap 5 | 5.3.3 (CDN) |
| Iconos | Bootstrap Icons | 1.11.3 (CDN) |
| Gráficos | Chart.js | 4.4.7 (CDN) |
| Timeline | vis-timeline | 7.7.3 (CDN) |
| Fuente | Nunito (Google Fonts) | — (CDN) |
| Export Excel | openpyxl | 3.1.5 |
| Variables entorno | django-environ | 0.11.2 |
| Archivos estáticos | Whitenoise | 6.8.2 |
| Imágenes | Pillow | 11.0.0 |

---

## Comandos Útiles

```bash
# Activar entorno virtual (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Crear y aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# Ver migraciones pendientes
python manage.py showmigrations

# Cargar datos de prueba
python manage.py seed_data

# Iniciar servidor desarrollo
python manage.py runserver

# Iniciar en puerto específico
python manage.py runserver 0.0.0.0:8080

# Shell interactivo
python manage.py shell

# Recolectar estáticos (producción)
python manage.py collectstatic
```

---

## Variables de Entorno

Archivo `.env`:

| Variable | Descripción | Default |
|----------|------------|---------|
| `DEBUG` | Modo debug | `True` |
| `SECRET_KEY` | Clave secreta Django | *(requerido)* |
| `ALLOWED_HOSTS` | Hosts permitidos | `127.0.0.1,localhost` |
| `DB_ENGINE` | Motor de base de datos | `mssql` |
| `DB_NAME` | Nombre de la base de datos | `viva1a_db` |
| `DB_HOST` | Host SQL Server | `localhost\SQLEXPRESS` |
| `DB_USER` | Usuario SQL (opcional con Windows Auth) | *(vacío)* |
| `DB_PASSWORD` | Contraseña SQL (opcional) | *(vacío)* |
| `DB_PORT` | Puerto SQL Server | `1433` |
| `DB_OPTIONS_DRIVER` | Driver ODBC | `ODBC Driver 17 for SQL Server` |
| `DB_OPTIONS_TRUST_CERT` | Confiar certificado | `True` |
| `DB_OPTIONS_EXTRA_PARAMS` | Parámetros extra | `Trusted_Connection=yes;` |
