import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django
django.setup()

from django.utils import timezone
from apps.proyectos.models import Proyecto, MiembroProyecto, Sprint, HistoriaUsuario, Tarea, Incidencia
from apps.estructura.models import SubArea
from apps.accounts.models import User
from apps.gestion.models import RegistroTiempo
from apps.proyectos.signals import crear_asignacion_desde_tarea

sub = SubArea.objects.filter(activo=True).first()
mgr = User.objects.filter(activo=True, rol__nombre="Admin").first() or User.objects.filter(activo=True).first()
member = User.objects.filter(activo=True).exclude(pk=mgr.pk).first()

import uuid
uid = uuid.uuid4().hex[:4].upper()
codigo = f"PRJ-{uid}"

p = Proyecto.objects.create(nombre=f"Test Integral {uid}", codigo=codigo, area=sub.area, subarea=sub, manager=mgr)
MiembroProyecto.objects.create(proyecto=p, user=mgr, rol="manager")
MiembroProyecto.objects.create(proyecto=p, user=member, rol="developer")
print("Proyecto creado:", p.codigo, p.nombre)

h1 = HistoriaUsuario.objects.create(proyecto=p, titulo="Historia 1 - Login", codigo=codigo+"-US-001", prioridad="must", puntos_historia=5, creador=mgr)
h2 = HistoriaUsuario.objects.create(proyecto=p, titulo="Historia 2 - Dashboard", codigo=codigo+"-US-002", prioridad="should", puntos_historia=8, creador=mgr)
print("Historias:", h1.codigo, h2.codigo)

s = Sprint.objects.create(proyecto=p, nombre="Sprint 1", numero=1, estado="activo")
h1.sprint = s; h1.estado = "sprint_backlog"; h1.save()
h2.sprint = s; h2.estado = "sprint_backlog"; h2.save()
print("Sprint:", s.numero, "historias:", s.historias.count(), "pts:", s.puntos_comprometidos)

t1 = Tarea.objects.create(proyecto=p, titulo="Tarea 1 - Disenar UI", tipo="tarea", asignado_a=member, creador=mgr, sprint=s, historia=h1)
t1.codigo = p.codigo + "-T-" + str(t1.pk).zfill(3)
t1.save()
a1 = crear_asignacion_desde_tarea(t1)
print("Tarea:", t1.codigo, "Asignacion:", a1.pk if a1 else None, "estado:", a1.estado if a1 else None)

a1.estado = "EnCurso"
a1.save()
RegistroTiempo.objects.create(asignacion=a1, evento="Inicio", fecha_hora=timezone.now())
t1.refresh_from_db()
print("Tras Iniciar - Tarea estado:", t1.estado)

a1.estado = "Finalizada"
a1.save()
RegistroTiempo.objects.create(asignacion=a1, evento="Finalizacion", fecha_hora=timezone.now())
t1.refresh_from_db()
h1.refresh_from_db()
print("Tras Finalizar - Tarea estado:", t1.estado, "Historia estado:", h1.estado)

inc = Incidencia.objects.create(proyecto=p, titulo="Bug en login", tipo="bug", severidad="alta", reportado_por=member, asignado_a=mgr)
inc.codigo = p.codigo + "-INC-" + str(inc.pk).zfill(3)
inc.save()
print("Incidencia:", inc.codigo, "estado:", inc.estado)

print("\n--- RESUMEN ---")
print("Proyecto avance:", p.avance, "%")
print("Tareas total:", p.tareas.count(), "finalizadas:", p.tareas.filter(estado="finalizada").count())
print("Incidencias:", p.incidencias.count())
print("FLUJO COMPLETO OK")
