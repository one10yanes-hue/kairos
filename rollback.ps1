# Auto-elevar si no es admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell -ArgumentList "-File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Set-Location C:\inetpub\kairos

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  ROLLBACK - Kairos" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Limpiar Git
taskkill /F /IM git.exe 2>$null
Remove-Item -Force .git\index.lock -ErrorAction SilentlyContinue
git fetch origin --all

# Mostrar rama actual
$currentBranch = git branch --show-current
Write-Host "Rama actual: $currentBranch" -ForegroundColor Yellow
Write-Host ""

# Mostrar ramas disponibles
Write-Host "Ramas disponibles:" -ForegroundColor Cyan
git branch -r | ForEach-Object { Write-Host "  $_" }
Write-Host ""

# Preguntar rama
$rama = Read-Host "Rama (Enter para '$currentBranch')"
if ([string]::IsNullOrWhiteSpace($rama)) {
    $rama = $currentBranch
}

# Cambiar de rama si es diferente
if ($rama -ne $currentBranch) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ATENCION: Cambio de rama detectado" -ForegroundColor Red
    Write-Host "  De '$currentBranch' -> '$rama'" -ForegroundColor Red
    Write-Host "  Esto puede romper la BD si las ramas" -ForegroundColor Red
    Write-Host "  tienen esquemas incompatibles." -ForegroundColor Red
    Write-Host "  Solo continua si sabes lo que haces." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    $confirmBranch = Read-Host "Estas SEGURO de cambiar de rama? (s/n)"
    if ($confirmBranch -ne "s") {
        Write-Host "Cancelado." -ForegroundColor Red
        exit
    }
    Write-Host "Cambiando a rama $rama..." -ForegroundColor Cyan
    git checkout -B $rama origin/$rama 2>$null
    git reset --hard origin/$rama
}

Write-Host ""
Write-Host "Ultimos 10 commits en $rama :" -ForegroundColor Cyan
git log --oneline -10
Write-Host ""

$target = Read-Host "Hash del commit (o 'anterior' para 1 atras, o 'ultimo' para el mas reciente)"

if ($target -eq "" -or $target -eq "ultimo") {
    $target = $(git log --oneline -1).Split(" ")[0]
    Write-Host "Usando el commit mas reciente: $target" -ForegroundColor Yellow
} elseif ($target -eq "anterior") {
    $lines = @(git log --oneline -2)
    if ($lines.Count -ge 2) {
        $target = $lines[1].Split(" ")[0]
        Write-Host "Volviendo al commit anterior: $target" -ForegroundColor Yellow
    } else {
        Write-Host "No hay commit anterior." -ForegroundColor Red
        pause
        exit
    }
}

Write-Host ""
$confirm = Read-Host "Estas seguro? (s/n)"

if ($confirm -ne "s") {
    Write-Host "Cancelado." -ForegroundColor Red
    exit
}

Write-Host "Ejecutando rollback a $target..." -ForegroundColor Cyan

# Matar python antes de tocar archivos
taskkill /F /IM python.exe 2>$null
Start-Sleep -Seconds 2

git reset --hard $target

Write-Host "Reinstalando dependencias..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Aplicando migraciones..." -ForegroundColor Cyan
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput

Write-Host "Reiniciando uvicorn..." -ForegroundColor Cyan
schtasks /Run /TN "Kairos"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Rollback completado a rama $rama, commit $target" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Start-Sleep -Seconds 3
