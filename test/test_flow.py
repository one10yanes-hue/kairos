"""
TEST: Flujo completo de la aplicacion.
Prueba cada ruta con cada rol y documenta resultados.
"""
import os, sys, json

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
proj_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj_path)
import django
django.setup()

from django.test import Client
from django.urls import reverse
from apps.accounts.models import User

client = Client()
report = []
errors = []

def test(name, url_or_callable, expected_status, method='GET', data=None, login_as=None):
    """Test a route and record the result."""
    try:
        if login_as:
            user = User.objects.filter(cedula=login_as).first()
            if user:
                client.force_login(user)
            else:
                report.append(f'❌ {name}: usuario no encontrado ({login_as})')
                errors.append(name)
                return

        if callable(url_or_callable):
            resp = url_or_callable()
        elif method == 'GET':
            resp = client.get(url_or_callable)
        elif method == 'POST':
            resp = client.post(url_or_callable, data or {})

        if isinstance(expected_status, list):
            ok = resp.status_code in expected_status
            status = resp.status_code
        else:
            ok = resp.status_code == expected_status
            status = f"{resp.status_code} (expected {expected_status})"

        if ok:
            report.append(f'✅ {name} → {status}')
        else:
            if hasattr(resp, 'context'):
                err = resp.context[-1] if resp.context else '?'
            else:
                err = resp.content[:200] if hasattr(resp, 'content') else '?'
            report.append(f'❌ {name} → {status} | {err}')
            errors.append(name)
    except Exception as e:
        report.append(f'💥 {name} → EXCEPTION: {str(e)[:150]}')
        errors.append(name)

    client.logout()

# ============ 1. LOGIN ============
report.append('\n=== 1. LOGIN ===')

# Login test
resp = client.post(reverse('accounts:login'), {'cedula': '1044432944', 'fecha_expedicion': '2020-01-01'})
report.append(f"{'✅' if resp.status_code == 302 else '❌'} Login Master → {resp.status_code}")
client.logout()

resp = client.post(reverse('accounts:login'), {'cedula': '1067724950', 'fecha_expedicion': '2020-01-01'})
report.append(f"{'✅' if resp.status_code == 302 else '❌'} Login Admin → {resp.status_code}")
client.logout()

resp = client.post(reverse('accounts:login'), {'cedula': '1014657107', 'fecha_expedicion': '2020-01-01'})
report.append(f"{'✅' if resp.status_code == 302 else '❌'} Login Usuario → {resp.status_code}")
client.logout()

# ============ 2. ROUTES MASTER ============
report.append('\n=== 2. MASTER ROUTES ===')
m = '1044432944'

test('Root (Master)', '/', 302, login_as=m)
test('Organizacion / Empresas', reverse('estructura:empresa_list'), 200, login_as=m)
test('Organizacion / Areas', reverse('estructura:area_list'), 200, login_as=m)
test('Organizacion / SubAreas', reverse('estructura:subarea_list'), 200, login_as=m)
test('Gestionar Usuarios', reverse('accounts:master_usuarios'), 200, login_as=m)
test('Crear Usuario', reverse('accounts:master_usuario_create'), 200, login_as=m)
test('Editar Usuario', reverse('accounts:master_usuario_edit', args=[1]), 200, login_as=m)
test('Parametros / Tipos', reverse('actividades:tipo_list'), 200, login_as=m)
test('Parametros / Crear Tipo', reverse('actividades:tipo_create'), 200, login_as=m)
test('Parametros / Actividades', reverse('actividades:actividad_list'), 200, login_as=m)
test('Parametros / Crear Actividad', reverse('actividades:actividad_create'), 200, login_as=m)
test('Dashboard', reverse('dashboard:dashboard_admin'), 200, login_as=m)
test('Progreso', reverse('dashboard:progreso'), 200, login_as=m)
test('Linea de Tiempo', reverse('dashboard:linea_tiempo'), 200, login_as=m)
test('Planificaciones', reverse('planificacion:planificacion_list'), 200, login_as=m)
test('Crear Planificacion', reverse('planificacion:planificacion_create'), 200, login_as=m)
test('Reportes', reverse('reportes:reporte_list'), 200, login_as=m)
test('Importaciones / Areas', reverse('estructura:importar_exportar'), 200, login_as=m)
test('Importaciones / Usuarios', reverse('estructura:importar_usuarios'), 200, login_as=m)
test('Integracion / Habilitaciones', reverse('estructura:integracion_cargo'), 200, login_as=m)
test('Integracion / Sync', reverse('estructura:sync_cargo'), 200, login_as=m)

# ============ 3. ROUTES ADMIN ============
report.append('\n=== 3. ADMIN ROUTES ===')
a = '1067724950'

test('Root (Admin)', '/', 302, login_as=a)
test('Dashboard (Admin)', reverse('dashboard:dashboard_admin'), 200, login_as=a)
test('Progreso (Admin)', reverse('dashboard:progreso'), 200, login_as=a)
test('Parametros/Tipos (Admin)', reverse('actividades:tipo_list'), 200, login_as=a)
test('Actividades (Admin)', reverse('actividades:actividad_list'), 200, login_as=a)
test('Planificaciones (Admin)', reverse('planificacion:planificacion_list'), 200, login_as=a)
test('Crear Planif (Admin)', reverse('planificacion:planificacion_create'), 200, login_as=a)
test('Habilitaciones (Admin)', reverse('estructura:integracion_cargo'), 200, login_as=a)
# Admin NO debe poder acceder a sync
test('Sync (Admin - denied)', reverse('estructura:sync_cargo'), 302, login_as=a)
# Admin NO debe ver Organizacion
test('Empresas (Admin - denied)', reverse('estructura:empresa_list'), 302, login_as=a)
test('Areas (Admin - denied)', reverse('estructura:area_list'), 302, login_as=a)

# ============ 4. ROUTES USUARIO ============
report.append('\n=== 4. USUARIO ROUTES ===')
u = '1014657107'

test('Root (Usuario)', '/', 302, login_as=u)
test('Tablero', reverse('gestion:tablero'), 200, login_as=u)
test('Calendario', reverse('gestion:calendario'), 200, login_as=u)
test('Perfil', reverse('gestion:perfil'), 200, login_as=u)
test('Crear No Programada', reverse('gestion:crear_no_programada'), 200, login_as=u)
# Usuario NO puede ver admin routes
test('Dashboard (Usuario - denied)', reverse('dashboard:dashboard_admin'), 302, login_as=u)
test('Planificaciones (Usuario - denied)', reverse('planificacion:planificacion_list'), 302, login_as=u)

# ============ 5. API ENDPOINTS ============
report.append('\n=== 5. API ENDPOINTS ===')
m = '1044432944'

test('API Subarea', reverse('estructura:api_buscar', kwargs={'modelo':'subarea'}), 200, login_as=m)
test('API Empresa', reverse('estructura:api_buscar', kwargs={'modelo':'empresa'}), 200, login_as=m)
test('API User', reverse('estructura:api_buscar', kwargs={'modelo':'user'}), 200, login_as=m)
test('API Actividad', reverse('estructura:api_buscar', kwargs={'modelo':'actividad'}), 200, login_as=m)
test('API Tipo Actividad', reverse('estructura:api_buscar', kwargs={'modelo':'tipo_actividad'}), 200, login_as=m)
# KACTUS API calls skipped (require SQL Server connection)
# test('API Integracion Subareas', reverse('estructura:api_integracion_subareas') + '?empresa=600', 200, login_as=m)
# test('API Integracion Cargos', reverse('estructura:api_integracion_cargos') + '?empresa=600', 200, login_as=m)
# test('API Sync Comparar', reverse('estructura:api_sync_comparar') + '?empresa=600', [200,500], login_as=m)
# test('API Sync Comparar (Admin denied)', reverse('estructura:api_sync_comparar'), 403, login_as=a)
report.append('[SKIP] KACTUS API calls (SQL Server not available)')

# ============ 6. PLANIFICACION FLOW ============
report.append('\n=== 6. PLANIFICACION FLOW ===')
m = '1044432944'

# Crear planificacion via POST
test('POST Crear Planif', 
    lambda: client.post(reverse('planificacion:planificacion_create'), {
        'subarea': '1', 'nombre': 'Test Plan', 'descripcion': 'Test',
        'actividades': ['1', '2'], 'users': ['3'],
        'fecha_programada': '', 'fecha_vencimiento': '',
        'csrfmiddlewaretoken': 'x',
    }, follow=True),
    [200, 302], login_as=m
)

# ============ 7. DB INTEGRITY CHECK ============
report.append('\n=== 7. DB INTEGRITY ===')
import sqlite3
conn = sqlite3.connect(os.path.join(proj_path, 'db.sqlite3'))
c = conn.cursor()
c.execute('PRAGMA foreign_key_check')
fks = len(c.fetchall())
report.append(f"{'✅' if fks == 0 else '❌'} FK violations: {fks}")
c.execute('PRAGMA integrity_check')
report.append(f"✅ Integrity: {c.fetchone()[0]}")
conn.close()

# ============ SUMMARY ============
print('\n'.join(report))
print(f'\n=== SUMMARY ===')
print(f'Total: {len(report) - report.count("")}, Errors: {len(errors)}, OK: {len(report) - len(errors) - [r for r in report if r.startswith("===")].__len__() - [r for r in report if r==""].__len__()}')

# Write MD
md = "# VIVA1A - Test de Flujo Completo\n\n"
md += f"**Fecha:** 28/05/2026\n"
md += f"**Errores:** {len(errors)}\n\n"
md += "## Resultados por seccion\n\n"
for r in report:
    if r:
        md += f'- {r}\n'
md += f'\n## Resumen\n\n'
md += f'- Total pruebas: {len(report) - report.count("")}\n'
md += f'- Errores: {len(errors)}\n'
md += f'- Exitos: {len(report) - len(errors) - report.count("")}\n'
md += f'- FK violations: {fks}\n'

with open(os.path.join(proj_path, 'test', 'test_reporte.md'), 'w', encoding='utf-8') as f:
    f.write(md)
print('\nReporte escrito: test/test_reporte.md')
