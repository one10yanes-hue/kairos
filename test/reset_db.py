"""
SCRIPT: Reset total de la BD. Solo deja usuario Master + estructura minima.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

import sqlite3
from pathlib import Path
from apps.core.utils import generar_codigo

db_path = Path(__file__).resolve().parent.parent / 'db.sqlite3'
conn = sqlite3.connect(str(db_path))
c = conn.cursor()
c.execute('PRAGMA foreign_keys = OFF')

tables = [
    'sync_log', 'audit_log_change', 'audit_log', 'audit_session',
    'registro_tiempo', 'colaboracion', 'comentario', 'traslado_actividad',
    'asignacion_actividad', 'planificacion_detalle', 'planificacion',
    'actividad', 'tipo_actividad',
    'user_subarea', 'user_empresa',
    'subarea', 'empresa_area', 'area', 'empresa',
    'usuario_groups', 'usuario_user_permissions',
    'usuario', 'rol',
]

for t in tables:
    try:
        c.execute(f'DELETE FROM {t}')
    except sqlite3.OperationalError:
        pass

c.execute("DELETE FROM sqlite_sequence")

# Roles
now = 'datetime(\'now\')'
c.execute(f"INSERT INTO rol (id, nombre, descripcion, activo, fecha_creacion, fecha_update) VALUES (1,'Master','Super administrador',1,{now},{now})")
c.execute(f"INSERT INTO rol (id, nombre, descripcion, activo, fecha_creacion, fecha_update) VALUES (2,'Admin','Administrador de subarea',1,{now},{now})")
c.execute(f"INSERT INTO rol (id, nombre, descripcion, activo, fecha_creacion, fecha_update) VALUES (3,'Usuario','Operativo',1,{now},{now})")

# Empresa VIVA 1A IPS S.A. (homologada KACTUS codigo=600)
c.execute(f"INSERT INTO empresa (id, nombre, nit, codigo, direccion, telefono, activo, fecha_creacion, fecha_update) VALUES (1,'VIVA 1A IPS S.A.','900219120','600','CALLE 100 # 15-30','6012345678',1,{now},{now})")

# Area
cod_area = generar_codigo()
c.execute(f"INSERT INTO area (id, codigo, nombre, activo, fecha_creacion, fecha_update) VALUES (1,'{cod_area}','Tecnologia',1,{now},{now})")
c.execute(f"INSERT INTO empresa_area (empresa_id, area_id, activo, fecha_creacion, fecha_update) VALUES (1,1,1,{now},{now})")
# SubArea
cod_sub = generar_codigo()
c.execute(f"INSERT INTO subarea (id, codigo, nombre, area_id, activo, fecha_creacion, fecha_update) VALUES (1,'{cod_sub}','Aplicaciones Corporativas',1,1,{now},{now})")

# Solo usuario Master
fexp = '2020-01-01'
c.execute(
    "INSERT INTO usuario (id, password, cedula, fecha_expedicion, nombre, apellido, email, cargo, rol_id, "
    "is_active, is_staff, is_superuser, activo, fecha_creacion, fecha_update) "
    "VALUES (1,'','1044432944',?,'Humberto','Yanes','humberto@viva1a.com','Super Administrador',1,1,0,0,1,?,?)",
    (fexp, fexp, fexp)
)
# UserEmpresa NO se crea — la empresa del usuario viene de KACTUS via sync/habilitacion
c.execute(
    "INSERT INTO user_subarea (user_id, subarea_id, activo, fecha_creacion, fecha_update) VALUES (1,1,1,?,?)",
    (fexp, fexp)
)

conn.commit()
c.execute('PRAGMA foreign_keys = ON')

print('=== VERIFICACION ===')
for t in tables:
    try:
        c.execute(f'SELECT COUNT(*) FROM {t}')
        count = c.fetchone()[0]
        if count > 0:
            print(f'  {t}: {count}')
    except Exception:
        pass

print('\n--- Usuarios ---')
c.execute('SELECT id, cedula, nombre, apellido, rol_id, cargo FROM usuario ORDER BY id')
for r in c.fetchall():
    print(f'  [{r[4]}] {r[1]} - {r[2]} {r[3]} ({r[5]})')

print('\n--- Estructura ---')
c.execute('SELECT e.nombre, a.nombre, s.nombre FROM empresa_area ea JOIN empresa e ON e.id=ea.empresa_id JOIN area a ON a.id=ea.area_id JOIN subarea s ON s.area_id=a.id')
for r in c.fetchall():
    print(f'  {r[0]} > {r[1]} > {r[2]}')

print('\n--- Asignaciones ---')
c.execute('SELECT u.cedula, e.nombre, s.nombre FROM usuario u JOIN user_empresa ue ON ue.user_id=u.id JOIN empresa e ON e.id=ue.empresa_id JOIN user_subarea us ON us.user_id=u.id JOIN subarea s ON s.id=us.subarea_id')
for r in c.fetchall():
    print(f'  {r[0]} -> {r[1]} / {r[2]}')

conn.close()
print('\nDB reseteada. Solo usuario Master.')
