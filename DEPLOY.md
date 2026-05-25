# Guía de Despliegue en Producción — Windows Server

**Kairos** — Django 5.0 + SQL Server

---

## 📦 Opción 1: Docker (Recomendado)

**Ventajas**: entorno aislado, auto-actualización vía GitHub, sin instalar Python/ODBC manualmente.

### Requisitos en el servidor

```powershell
# Instalar Docker Desktop (Windows) o Docker Engine (Linux)
# https://docs.docker.com/desktop/install/windows-install/

# Verificar
docker --version
docker compose version
```

### Desplegar por primera vez

```powershell
# Clonar proyecto
mkdir C:\Apps
cd C:\Apps
git clone https://github.com/TU_USUARIO/kairos.git
cd kairos\viva1a

# Crear archivo .env con variables de producción
# (SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS, etc.)

# Construir e iniciar
docker compose up -d --build
```

Esto levanta:
- **kairos-web** (Django + Waitress) en puerto `8000`
- **kairos-db** (SQL Server 2022) en puerto `1433`
- **kairos-watchtower** (auto-actualización cada 60s)

### Después del primer deploy, ejecutar semillas

```powershell
docker compose exec web python manage.py seed_data
```

### Conectar con GitHub para auto-deploy

Cada vez que hagas `git push`, el servidor se actualiza automáticamente:

1. **En GitHub** → Settings → Secrets → Actions → agregar:

| Secret | Valor |
|--------|-------|
| `SSH_HOST` | IP del servidor |
| `SSH_USER` | Usuario del servidor |
| `SSH_PRIVATE_KEY` | Clave SSH privada |

2. **En el servidor**, autorizar la clave pública para SSH:

```powershell
# Agregar la clave pública de GitHub Actions en:
# C:\Users\TU_USUARIO\.ssh\authorized_keys
```

3. **Configurar el servidor para aceptar SSH** (OpenSSH Server en Windows):

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

### Flujo de auto-deploy

```
git push → GitHub Actions → SSH al servidor → git pull → docker compose build → deploy
```

### Comandos Docker útiles

```powershell
# Ver contenedores
docker compose ps

# Ver logs
docker compose logs -f web

# Reiniciar
docker compose restart web

# Actualizar manualmente
docker compose pull
docker compose up -d

# Migrar BD después de cambios
docker compose exec web python manage.py migrate

# Entrar al shell de Django
docker compose exec web python manage.py shell

# Respaldar BD
docker compose exec db /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "$DB_PASSWORD" -Q "BACKUP DATABASE viva1a_db TO DISK='/var/opt/mssql/backup.bak' WITH FORMAT"
```

---

## 🔧 Opción 2: Instalación tradicional (Waitress + IIS)

Si prefieres no usar Docker, aquí está el stack nativo para Windows Server.

```
Cliente → IIS (puerto 80/443) → localhost:8000 → Waitress (WSGI)
                                              ↑
                                         Django + Whitenoise (estáticos)
```

**¿Por qué este stack?**
- **Waitress** es el servidor WSGI recomendado para Windows. Gunicorn y uWSGI no funcionan en Windows.
- **IIS** como proxy reverso maneja HTTPS, dominios, y sirve estáticos directamente.
- **NSSM** convierte Waitress en un servicio de Windows que arranca con el sistema.
- **Whitenoise** sirve estáticos desde Django (sin depender de IIS para eso).

---

## 1. Preparar el servidor (30 min)

```powershell
# 1. Instalar Python 3.10+ (marcar "Add to PATH")
# https://python.org

# 2. Instalar ODBC Driver 17 for SQL Server
# https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

# 3. Instalar IIS y módulo ARR (para proxy reverso)
Install-WindowsFeature -Name Web-Server, Web-WebServer -IncludeManagementTools
# Descargar e instalar manualmente:
#   - URL Rewrite: https://www.iis.net/downloads/microsoft/url-rewrite
#   - ARR v3: https://www.iis.net/downloads/microsoft/application-request-routing
```

## 2. Copiar e instalar el proyecto (10 min)

```powershell
# Copiar proyecto al servidor
mkdir C:\Apps
xcopy /E /I "\\origen\kairos" "C:\Apps\kairos"

# Crear virtualenv e instalar
cd C:\Apps\kairos\viva1a
python -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m pip install waitress

# Probar que funciona el proyecto
venv\Scripts\python.exe manage.py check --deploy
```

## 3. Configurar `.env` para producción (5 min)

```env
DEBUG=False
SECRET_KEY=<generar con: python -c "import secrets; print(secrets.token_urlsafe(50))">
ALLOWED_HOSTS=localhost,127.0.0.1,MI_SERVIDOR,192.168.x.x

DB_ENGINE=mssql
DB_NAME=viva1a_db
DB_HOST=localhost\SQLEXPRESS
DB_OPTIONS_DRIVER=ODBC Driver 17 for SQL Server
DB_OPTIONS_TRUST_CERT=True
DB_OPTIONS_EXTRA_PARAMS=Trusted_Connection=yes;

TIME_ZONE=America/Bogota
```

## 4. Migrar y recolectar estáticos (5 min)

```powershell
cd C:\Apps\kairos\viva1a
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py seed_data
venv\Scripts\python.exe manage.py collectstatic --noinput
```

## 5. Crear servicio de Windows con NSSM (5 min)

NSSM (Non-Sucking Service Manager) envuelve Waitress como servicio de Windows:

```powershell
# Descargar NSSM
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "$env:TEMP\nssm.zip"
Expand-Archive "$env:TEMP\nssm.zip" -DestinationPath "C:\Apps\nssm" -Force

# Crear servicio (PowerShell como Administrador)
C:\Apps\nssm\nssm-2.24\win64\nssm.exe install Kairos

# En la GUI de NSSM, configurar:
#   Application Path: C:\Apps\kairos\viva1a\venv\Scripts\waitress-serve.exe
#   Arguments: --host=127.0.0.1 --port=8000 --threads=8 config.wsgi:application
#   Startup Dir: C:\Apps\kairos\viva1a
#
# Pestaña "Details": Start = SERVICE_AUTO_START
# Pestaña "Exit": Default action = Restart

# Iniciar el servicio
C:\Apps\nssm\nssm-2.24\win64\nssm.exe start Kairos
```

Alternativa sin GUI (todo por línea):
```powershell
$nssm = "C:\Apps\nssm\nssm-2.24\win64\nssm.exe"
& $nssm install Kairos "C:\Apps\kairos\viva1a\venv\Scripts\waitress-serve.exe"
& $nssm set Kairos AppParameters "--host=127.0.0.1 --port=8000 --threads=8 config.wsgi:application"
& $nssm set Kairos AppDirectory "C:\Apps\kairos\viva1a"
& $nssm set Kairos Start SERVICE_AUTO_START
& $nssm set Kairos AppExit Default Restart
& $nssm start Kairos
```

Verificar:
```powershell
Get-Service Kairos       # Debe mostrar "Running"
curl http://127.0.0.1:8000 -UseBasicParsing   # Debe responder 200/302
```

## 6. Configurar IIS como proxy reverso (10 min)

### Activar ARR como proxy

En IIS Manager:
1. Hacer clic en el servidor (nodo raíz)
2. Abrir **Application Request Routing Cache**
3. Panel derecho → **Server Proxy Settings**
4. Marcar **Enable proxy** → **Apply**

### Crear sitio en IIS

```powershell
Import-Module WebAdministration

# Pool de aplicaciones
New-WebAppPool -Name "KairosPool"
Set-ItemProperty -Path "IIS:\AppPools\KairosPool" -Name managedRuntimeVersion -Value ""

# Sitio web
New-Website -Name "Kairos" `
    -PhysicalPath "C:\Apps\kairos\viva1a\staticfiles" `
    -ApplicationPool "KairosPool" `
    -Port 80 `
    -HostHeader ""
```

### Crear regla de URL Rewrite

Crear archivo `C:\Apps\kairos\viva1a\web.config`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="DjangoReverseProxy" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions logicalGrouping="MatchAll">
                        <add input="{REQUEST_URI}" pattern="^/static/" negate="true" />
                        <add input="{REQUEST_URI}" pattern="^/media/" negate="true" />
                    </conditions>
                    <action type="Rewrite" url="http://127.0.0.1:8000/{R:1}" />
                </rule>
            </rules>
        </rewrite>
    </system.webServer>
</configuration>
```

Ya está. IIS en puerto 80 → reverse proxy a Waitress en 8000. Estáticos los sirve IIS directamente desde `staticfiles/`.

## 7. Firewall

```powershell
New-NetFirewallRule -DisplayName "HTTP 80" -Direction Inbound -Port 80 -Protocol TCP -Action Allow
```

(Solo necesitas abrir el 80. El 8000 solo es interno/localhost.)

## 8. HTTPS (opcional)

Para HTTPS gratis, usar **win-acme** (Let's Encrypt para Windows):

```powershell
# Descargar win-acme
Invoke-WebRequest -Uri "https://github.com/win-acme/win-acme/releases/latest/download/win-acme.v2.x64.pluggable.zip" -OutFile "$env:TEMP\winacme.zip"
Expand-Archive "$env:TEMP\winacme.zip" -DestinationPath "C:\Apps\winacme" -Force
cd C:\Apps\winacme

# Ejecutar (genera certificado y configura IIS automáticamente)
.\wacs.exe --target iissite --siteid 1 --installation iis --validation selfhosting
```

## Comandos de mantenimiento

```powershell
# Ver estado
Get-Service Kairos

# Reiniciar aplicación
Restart-Service Kairos

# Actualizar código
Stop-Service Kairos
# (copiar archivos nuevos o git pull)
Start-Service Kairos

# Respaldar BD
sqlcmd -S localhost\SQLEXPRESS -E -Q "BACKUP DATABASE viva1a_db TO DISK='C:\Backups\viva1a_db.bak' WITH FORMAT"

# Migrar después de cambios
cd C:\Apps\kairos\viva1a
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py collectstatic --noinput
Restart-Service Kairos
```

---

## ¿Por qué Waitress y no Apache/mod_wsgi?

| Servidor | Windows | Motivo |
|----------|---------|--------|
| **Waitress** | ✅ Nativo | WSGI puro en Python. Recomendado para Windows. |
| **Gunicorn** | ❌ | Solo Linux. Usa `fork()` que no existe en Windows. |
| **uWSGI** | ❌ | No compila en Windows. |
| **mod_wsgi** | ⚠️ | Funciona pero requiere Apache + compilación C. Más pesado. |
| **Hypercorn** | ✅ | Soporta Windows pero es más para ASGI. |

Waitress es la opción correcta para Django en Windows Server.
