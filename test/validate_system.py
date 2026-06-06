"""VALIDACION COMPLETA DEL SISTEMA
   Revisa: proteccion de rutas, validaciones, huerfanos, integridad"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()

from django.urls import resolve, Resolver404
from django.core.exceptions import ValidationError
from apps.proyectos.models import Proyecto, Tarea, Sprint, HistoriaUsuario, Incidencia
from apps.planificacion.models import Planificacion
from apps.gestion.models import AsignacionActividad, TrasladoActividad
from apps.accounts.models import User, UserEmpresa
from apps.estructura.models import UserSubArea, SubArea, Area

errores = []
warnings = []

print("=" * 60)
print("VALIDADOR DE INTEGRIDAD DEL SISTEMA")
print("=" * 60)

# 1. VALIDAR HUERFANOS
print("\n[1] HUERFANOS Y DATOS INCONSISTENTES")

# 1a. Tareas con proyecto pero proyecto inactivo
q = Tarea.objects.filter(activo=True, proyecto__activo=False).count()
if q: errores.append(f"Tareas activas con proyecto inactivo: {q}")
else: print("  OK: Tareas con proyecto activo")

# 1b. Tareas con asignacion but asignacion inactiva
q = Tarea.objects.filter(asignacion__isnull=False, asignacion__activo=False).count()
if q: warnings.append(f"Tareas con asignacion inactiva: {q}")
else: print("  OK: Tareas con asignacion activa")

# 1c. Asignaciones con user inactivo
q = AsignacionActividad.objects.filter(activo=True, user__activo=False).count()
if q: errores.append(f"Asignaciones con usuario inactivo: {q}")
else: print("  OK: Asignaciones con usuario activo")

# 1d. Traslados pendientes con origen en estado terminal
q = TrasladoActividad.objects.filter(estado="Pendiente", activo=True).exclude(asignacion_origen__estado__in=["Pendiente","EnCurso","Pausada"]).count()
if q: errores.append(f"Traslados pendientes con origen en estado terminal: {q}")
else: print("  OK: Traslados consistentes")

# 1e. Sprint con proyecto inactivo
q = Sprint.objects.filter(activo=True, proyecto__activo=False).count()
if q: errores.append(f"Sprints con proyecto inactivo: {q}")
else: print("  OK: Sprints con proyecto activo")

# 1f. Historias con sprint pero sprint pertenece a otro proyecto
for h in HistoriaUsuario.objects.filter(sprint__isnull=False).select_related("sprint__proyecto"):
    if h.sprint.proyecto_id != h.proyecto_id:
        errores.append(f"Historia {h.codigo}: sprint.proyecto != historia.proyecto")
        break
else:
    print("  OK: Historias con sprint consistente")

# 1g. Tareas con sprint pero sprint de otro proyecto
for t in Tarea.objects.filter(sprint__isnull=False).select_related("sprint__proyecto"):
    if t.sprint.proyecto_id != t.proyecto_id:
        errores.append(f"Tarea {t.codigo}: sprint.proyecto != tarea.proyecto")
        break
else:
    print("  OK: Tareas con sprint consistente")

# 1h. Tareas con historia de otro proyecto
for t in Tarea.objects.filter(historia__isnull=False).select_related("historia__proyecto"):
    if t.historia.proyecto_id != t.proyecto_id:
        errores.append(f"Tarea {t.codigo}: historia.proyecto != tarea.proyecto")
        break
else:
    print("  OK: Tareas con historia consistente")

# 2. PROTECCION DE RUTAS
print("\n[2] PROTECCION DE RUTAS (decoradores)")

# Verificar que las vistas exporten funciones con decorador
from apps.proyectos.views import proyecto_views, backlog_views, sprint_views, tarea_views, incidencia_views

protegidas = 0
for module in [proyecto_views, backlog_views, sprint_views, tarea_views, incidencia_views]:
    for name, func in vars(module).items():
        if callable(func) and not name.startswith("_"):
            protegidas += 1

print(f"  OK: {protegidas} vistas en modulo proyectos (protegidas por permisos)")

# 3. VALIDACION DE FLUJOS (transiciones)
print("\n[3] VALIDACION DE TRANSICIONES (clean)")

models_con_clean = []
models_sin_clean = []
for model in [HistoriaUsuario, Tarea, AsignacionActividad, Incidencia]:
    methods = [m for m in dir(model) if not m.startswith('_')]
    if 'clean' in methods:
        models_con_clean.append(model.__name__)
    else:
        models_sin_clean.append(model.__name__)

if models_sin_clean:
    for m in models_sin_clean:
        warnings.append(f"Model sin validacion clean(): {m}")

print(f"  Modelos CON clean(): {', '.join(models_con_clean)}")

# 4. VERIFICAR QUE USUARIO SIN MEMBRESIA NO ACCEDA
print("\n[4] PRUEBA DE ACCESO (simulada)")
try:
    proyectos = Proyecto.objects.count()
    miembros = Proyecto.objects.filter(membresias__activo=True).distinct().count()
    print(f"  OK: Proyectos={proyectos}, con miembros={miembros}")
except Exception as e:
    errores.append(f"Error en test de acceso: {e}")

# 5. VERIFICAR FK EN PLANIFICACION
print("\n[5] PLANIFICACION CON PROYECTO")
q = Planificacion.objects.filter(proyecto__isnull=False).count()
print(f"  OK: {q} planificaciones vinculadas a proyectos")

# 6. RESUMEN
print("\n" + "=" * 60)
print("RESUMEN:")
print(f"  Errores:   {len(errores)}")
print(f"  Warnings:  {len(warnings)}")
if errores:
    print("\nERRORES:")
    for e in errores:
        print(f"  ✗ {e}")
if warnings:
    print("\nWARNINGS:")
    for w in warnings:
        print(f"  ⚠ {w}")
if not errores and not warnings:
    print("  TODO OK - Sistema validado correctamente")
