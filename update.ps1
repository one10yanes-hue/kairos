# Auto-elevar si no es admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell -ArgumentList "-File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Set-Location C:\inetpub\kairos

# Limpiar procesos, locks y packs corruptos de Git
taskkill /F /IM git.exe 2>$null
Remove-Item -Force .git\index.lock -ErrorAction SilentlyContinue
Get-ChildItem .git\objects\pack\*.idx -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem .git\objects\pack\*.pack -ErrorAction SilentlyContinue | Remove-Item -Force

# Recuperar del remoto (fresh fetch)
git fetch origin

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KAIROS - Actualizar desde GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Mostrar rama actual
$currentBranch = git branch --show-current
Write-Host "Rama actual: $currentBranch" -ForegroundColor Yellow
Write-Host ""

# Mostrar ramas disponibles
Write-Host "Ramas disponibles:" -ForegroundColor Cyan
git branch -r | ForEach-Object { Write-Host "  $_" }
Write-Host ""

# Preguntar rama
$rama = Read-Host "Rama a usar (Enter para '$currentBranch')"
if ([string]::IsNullOrWhiteSpace($rama)) {
    $rama = $currentBranch
}

# Si la rama es local, usarla directo. Si es remota, usar origin/
if ($rama -notmatch "^origin/") {
    $remoteCheck = git branch -r | Select-String "origin/$rama"
    if ($remoteCheck) {
        $pullRef = "origin/$rama"
    } else {
        $pullRef = $rama
    }
} else {
    $pullRef = $rama
}

Write-Host ""
Write-Host "Actualizando desde $pullRef..." -ForegroundColor Cyan
$env:GIT_ASK_YESNO = "false"
echo n | git pull origin $rama
Remove-Item Env:\GIT_ASK_YESNO -ErrorAction SilentlyContinue
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: git pull fallo. Revisa la conexion o el nombre de la rama." -ForegroundColor Red
    pause
    exit
}

Write-Host "Instalando dependencias..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Migrando base de datos..." -ForegroundColor Cyan
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput

Write-Host "Reiniciando uvicorn..." -ForegroundColor Cyan
taskkill /F /IM python.exe 2>$null
taskkill /F /IM git.exe 2>$null
Start-Sleep -Seconds 2

# Limpiar locks y compactar git
Remove-Item -Force .git\index.lock -ErrorAction SilentlyContinue
git gc --auto 2>$null

schtasks /Run /TN "Kairos"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Actualizacion completada desde $rama" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Start-Sleep -Seconds 3
