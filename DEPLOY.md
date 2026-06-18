# Kairos v4.2.0 — Despliegue en Windows Server 2019 + MariaDB

> Commit: `2d9d4a4` — Kairos v4.2.0 - Eliminar archivos de despliegue (Docker, workflows) - 05/06/2026

---

## 1. Requisitos

| Software | Instalación |
|---|---|
| Python 3.12 | `https://python.org` (marcar "Add Python to PATH") |
| MariaDB 10.x | `https://mariadb.org/download` (MSI x64, puerto 3306) |
| Git | `https://git-scm.com/download/win` |

---

## 2. Descargar código

```bash
cd C:\
git clone https://github.com/one10yanes-hue/kairos.git C:\kairos
cd C:\kairos
git checkout 2d9d4a438241925b0f54fa5a0ba0cf3e20d7cd6a
```

---

## 3. Crear base de datos en MariaDB

```sql
CREATE DATABASE kairos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## 4. Modificaciones

### 4.1 `requirements.txt`

**Eliminar** estas 2 líneas:
```
mssql-django>=1.7
pyodbc>=5.3
```

**Agregar** al final:
```
PyMySQL>=1.1
uvicorn[standard]>=0.30
channels>=4.1
```

Archivo final `requirements.txt`:
```
Django>=5.0,<5.1
django-environ>=0.11
openpyxl>=3.1
Pillow>=11.0
whitenoise>=6.8
PyMySQL>=1.1
uvicorn[standard]>=0.30
channels>=4.1
```

---

### 4.2 `config/__init__.py`

Agregar al **inicio** del archivo:

```python
import pymysql

pymysql.install_as_MySQLdb()
```

---

### 4.3 `config/settings.py`

#### Cambio 1: Agregar soporte MySQL al bloque del motor

Buscar la línea:
```python
if db_engine in ["mssql", "sql_server"]:
    db_engine = "mssql"
```

Agregar **debajo**:
```python
elif db_engine in ["mysql", "mariadb"]:
    db_engine = "django.db.backends.mysql"
```

#### Cambio 2: Agregar credenciales MySQL

Buscar el bloque que cierra el `if db_engine == "mssql":` con `}` y `)`. Después de ese cierre, antes de `# Base de datos externa KACTUS`, agregar:

```python

elif db_engine == "django.db.backends.mysql":
    DATABASES["default"].update({
        "USER": env("DB_USER", default="root"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    })
```

---

### 4.4 Crear `.env`

```env
SECRET_KEY=Kairos2026SuperSeguroClaveAleatoriaLarga50chars!!
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=mariadb
DB_NAME=kairos
DB_USER=root
DB_PASSWORD=KairosDB2026!
DB_HOST=localhost
DB_PORT=3306
```

---

## 5. Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar (Git Bash)
source venv/Scripts/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Migrar base de datos
python manage.py migrate

# Recopilar archivos estáticos
python manage.py collectstatic --noinput

# Crear superusuario
python manage.py createsuperuser
```

---

## 6. Iniciar servidor

```bash
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --ws websockets
```

---

## 7. Probar

```
http://localhost:8000
```

Login con el superusuario creado en el paso 5.

---

## 8. Inicio automático (Tarea Programada de Windows)

Crear archivo `C:\kairos\start.bat`:

```bat
@echo off
cd /d C:\kairos
call venv\Scripts\activate
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --ws websockets
```

Configurar Tarea Programada:

```
1. Abrir "Programador de tareas"
2. Crear tarea básica: "Kairos Server"
3. Desencadenador: "Al iniciar el equipo"
4. Acción: "Iniciar un programa" → C:\kairos\start.bat
5. Marcar "Ejecutar con los privilegios más altos"
6. Pestaña "Configuración": marcar "Ejecutar si la tarea falla, reintentar cada 1 minuto"
```

---

## 9. Comandos útiles

```bash
# Ver logs del servidor
# (aparecen en la terminal donde corre uvicorn)

# Migrar después de cambios
python manage.py migrate

# Actualizar estáticos
python manage.py collectstatic --noinput

# Shell de Django
python manage.py shell

# Crear backup de BD
mysqldump -u root -p kairos > backup.sql
```

---

## Notas

- **WebSockets**: uvicorn con `--ws websockets` maneja HTTP + WebSocket en el mismo puerto 8000
- **Sin IIS**: no se necesita configurar IIS, uvicorn sirve directamente
- **Estáticos**: whiteNoise los sirve desde `/staticfiles/`
- **Media**: los archivos subidos se guardan en `C:\kairos\media\`
- **KACTUS**: la BD externa sigue configurada, requiere conexión al servidor `172.27.198.73`
