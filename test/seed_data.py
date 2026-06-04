import sqlite3
conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
now = '2026-05-28 00:00:00'

c.execute("INSERT INTO tipo_actividad (id, nombre, subarea_id, requiere_fecha_limite, activo, fecha_creacion, fecha_update) VALUES (1,'Programada',1,0,1,?,?)", [now,now])
c.execute("INSERT INTO tipo_actividad (id, nombre, subarea_id, requiere_fecha_limite, activo, fecha_creacion, fecha_update) VALUES (2,'No Programada',1,0,1,?,?)", [now,now])

c.execute("INSERT INTO actividad (id, nombre, subarea_id, tipo_actividad_id, activo, fecha_creacion, fecha_update) VALUES (1,'Informe AF',1,1,1,?,?)", [now,now])
c.execute("INSERT INTO actividad (id, nombre, subarea_id, tipo_actividad_id, activo, fecha_creacion, fecha_update) VALUES (2,'Causacion Viaticos',1,1,1,?,?)", [now,now])
c.execute("INSERT INTO actividad (id, nombre, subarea_id, tipo_actividad_id, activo, fecha_creacion, fecha_update) VALUES (3,'Reunion Gerencia',1,2,1,?,?)", [now,now])

conn.commit()
c.execute('SELECT id, nombre, tipo_actividad_id FROM actividad')
print('Actividades:')
for r in c.fetchall():
    print(f'  id={r[0]} nombre={r[1]} tipo={r[2]}')
c.execute('SELECT id, nombre FROM tipo_actividad')
print('Tipos:')
for r in c.fetchall():
    print(f'  id={r[0]} nombre={r[1]}')
conn.close()
print('OK')
