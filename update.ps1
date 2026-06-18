# Auto-elevar si no es admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell -ArgumentList "-File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Set-Location C:\inetpub\kairos

# --- Crear .env SOLO si no existe (NUNCA sobrescribir) ---
if (-not (Test-Path .env)) {
    Write-Host "Creando .env por primera vez..." -ForegroundColor Yellow
    @"
SECRET_KEY=Kairos2026SuperSeguroClaveAleatoriaLarga50chars!!
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.200.93,kairos.viva1a.com.co
DB_ENGINE=mysql
DB_NAME=kairos
DB_USER=root
DB_PASSWORD=Viva2026
DB_HOST=localhost
DB_PORT=3306
"@ | Set-Content -Path .env -Encoding ASCII
    Write-Host ".env creado. Ajustalo si es necesario." -ForegroundColor Green
}

# --- PyMySQL bridge (por si no existe) ---
if (-not (Test-Path config\__init__.py)) {
    Write-Host "Creando config\__init__.py con PyMySQL bridge..." -ForegroundColor Yellow
    @"
import pymysql
pymysql.install_as_MySQLdb()
"@ | Set-Content -Path config\__init__.py -Encoding ASCII
}

# Limpiar locks y procesos
taskkill /F /IM git.exe 2>$null
taskkill /F /IM python.exe 2>$null
Remove-Item -Force .git\index.lock -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KAIROS - Actualizar desde GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Fetch fresco
git fetch origin produccion 2>$null

# Mostrar rama actual
$currentBranch = git branch --show-current
Write-Host "Rama actual: $currentBranch" -ForegroundColor Yellow
Write-Host ""

# Siempre usar produccion
$rama = "produccion"
Write-Host "Actualizando desde origin/$rama..." -ForegroundColor Cyan

# Reset al estado exacto del remoto
git fetch origin $rama
git checkout -B $rama origin/$rama 2>$null
git reset --hard origin/$rama

Write-Host "Instalando dependencias..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install -r requirements.txt PyMySQL --quiet

Write-Host "Migrando base de datos..." -ForegroundColor Cyan
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput

Write-Host "Reiniciando uvicorn..." -ForegroundColor Cyan
taskkill /F /IM python.exe 2>$null
Start-Sleep -Seconds 2

Remove-Item -Force .git\index.lock -ErrorAction SilentlyContinue
git gc --auto 2>$null

schtasks /Run /TN "Kairos"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Kairos v4.2.x actualizado desde $rama" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Start-Sleep -Seconds 3
