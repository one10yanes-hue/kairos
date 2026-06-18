# Auto-elevar si no es admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell -ArgumentList "-File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AGREGANDO .git a Kairos (sin mover)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Salir de la carpeta
Set-Location C:\

# Matar uvicorn
Write-Host "1/3 Deteniendo uvicorn..." -ForegroundColor Yellow
taskkill /F /IM python.exe 2>$null
Start-Sleep -Seconds 2

# Inicializar git dentro de la carpeta existente
Write-Host "2/3 Inicializando git..." -ForegroundColor Yellow
Set-Location C:\inetpub\kairos
git init
git remote add origin https://github.com/one10yanes-hue/kairos.git
git fetch origin v4.2.1
git checkout -B v4.2.1 origin/v4.2.1
git reset --hard origin/v4.2.1

# Reinstalar dependencias y reiniciar
Write-Host "3/3 Reinstalando y reiniciando..." -ForegroundColor Yellow
.\venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

Write-Host ""
Write-Host "Version:" -ForegroundColor Cyan
git log --oneline -1

schtasks /Run /TN "Kairos"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Listo. .git agregado sin mover nada." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Start-Sleep -Seconds 5
