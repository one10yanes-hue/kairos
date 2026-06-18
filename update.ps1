# Auto-elevar si no es admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell -ArgumentList "-File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Set-Location C:\inetpub\kairos

# --- Crear .env SOLO si no existe (NUNCA sobrescribir uno existente) ---
if (-not (Test-Path .env)) {
    Write-Host "Creando .env por primera vez..." -ForegroundColor Yellow
    $envContent = @"
SECRET_KEY=Kairos2026SuperSeguroClaveAleatoriaLarga50chars!!
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.200.93,kairos.viva1a.com.co
DB_ENGINE=mysql
DB_NAME=kairos
DB_USER=root
DB_PASSWORD=Viva2026
DB_HOST=localhost
DB_PORT=3306
"@
    Set-Content -Path .env -Value $envContent -Encoding ASCII
    Write-Host ".env creado. Revisalo y ajusta si es necesario." -ForegroundColor Green
}

# Limpiar procesos, locks y packs corruptos de Git
taskkill /F /IM git.exe 2>$null
Remove-Item -Force .git\index.lock -ErrorAction SilentlyContinue
Get-ChildItem .git\objects\pack\*.idx -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem .git\objects\pack\*.pack -ErrorAction SilentlyContinue | Remove-Item -Force

# Recuperar del remoto
git fetch origin

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KAIROS - Actualizar desde GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Mostrar rama actual
$currentBranch = git branch --show-current
Write-Host "Rama actual: $currentBranch" -ForegroundColor Yellow
Write-Host ""

# Si la rama local no existe en remoto, usar main
if (-not (git branch -r | Select-String "origin/$currentBranch")) {
    $currentBranch = "main"
    Write-Host "Rama local no tiene remoto. Usando: $currentBranch" -ForegroundColor Yellow
}

# Mostrar ramas disponibles
Write-Host "Ramas disponibles:" -ForegroundColor Cyan
git branch -r | ForEach-Object { Write-Host "  $_" }
Write-Host ""

# Preguntar rama
$rama = Read-Host "Rama a usar (Enter para '$currentBranch')"
if ([string]::IsNullOrWhiteSpace($rama)) {
    $rama = $currentBranch
}

Write-Host ""
Write-Host "Actualizando desde origin/$rama..." -ForegroundColor Cyan

# Resetear al estado exacto del remoto (evita conflictos de merge)
git fetch origin $rama
git checkout $rama 2>$null
git reset --hard "origin/$rama"

Write-Host "Instalando dependencias..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Migrando base de datos..." -ForegroundColor Cyan
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput

Write-Host "Reiniciando uvicorn..." -ForegroundColor Cyan
taskkill /F /IM python.exe 2>$null
taskkill /F /IM git.exe 2>$null
Start-Sleep -Seconds 2

# Limpiar locks
Remove-Item -Force .git\index.lock -ErrorAction SilentlyContinue
git gc --auto 2>$null

schtasks /Run /TN "Kairos"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Actualizacion completada desde $rama" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Start-Sleep -Seconds 3
