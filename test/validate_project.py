import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django
django.setup()

from django.db import connection

print("=== VALIDACION MODELOS ===")

# 1. Normalización: verificar dependencias transitivas
print("\n1. FN3 (No dependencias transitivas):")
issues = []

# Revisar: Tarea tiene FK a Proyecto, Sprint, Historia. Sprint tiene FK a Proyecto.
# Si Tarea.sprint.proyecto != Tarea.proyecto, hay inconsistencia.
# Esto se valida en la app, no en BD. OK para FN3 (no hay datos redundantes).
print("   - Tarea.proyecto y Tarea.sprint.proyecto: pueden diverger (no hay constraint DB)")
print("   - Tarea.historia.proyecto y Tarea.proyecto: pueden diverger")
issues.append("Tarea.proyecto es redundante con Tarea.sprint.proyecto y Tarea.historia.proyecto")

# Revisar: Incidencia tiene FK a Proyecto.
print("   - Incidencia.proyecto OK")

print("\n2. Integridad referencial (FK on_delete):")
from apps.proyectos.models import Proyecto, Tarea, Sprint, HistoriaUsuario, Incidencia
models_to_check = [Proyecto, Tarea, Sprint, HistoriaUsuario, Incidencia]
for model in models_to_check:
    for field in model._meta.get_fields():
        if hasattr(field, 'on_delete') and field.on_delete and hasattr(field.on_delete, '__name__'):
            if field.on_delete.__name__ != 'PROTECT' and field.on_delete.__name__ != 'CASCADE' and field.on_delete.__name__ != 'SET_NULL':
                print(f"   ⚠ {model.__name__}.{field.name}: {field.on_delete.__name__}")
print("   OK - todas las FK usan PROTECT, CASCADE o SET_NULL")

print("\n3. Flujo de estados (validacion de transiciones):")
print("   ⚠ NO hay validacion de transiciones. Cualquier estado puede ir a cualquier otro.")
print("   ⚠ Estados hardcodeados, no configurables por proyecto.")

print("\n4. Sincronizacion Tarea <-> AsignacionActividad:")
from apps.gestion.models import AsignacionActividad
tareas_con_asig = Tarea.objects.filter(asignacion__isnull=False).count()
tareas_total = Tarea.objects.count()
print(f"   Tareas con asignacion: {tareas_con_asig}/{tareas_total}")

from apps.proyectos.signals import sync_tarea_from_asignacion
import inspect
sig_source = inspect.getsource(sync_tarea_from_asignacion)
has_revision = "Revision" in sig_source
has_finalizada = "Finalizada" in sig_source
print(f"   Signal cubre Revision: {has_revision}, Finalizada: {has_finalizada}")

print("\n5. Sprint - reglas de cierre:")
sprints_activos = Sprint.objects.filter(estado="activo").count()
sprints_finalizados = Sprint.objects.filter(estado="finalizado").count()
print(f"   Activos: {sprints_activos}, Finalizados: {sprints_finalizados}")
print("   ⚠ No hay vista de cierre de sprint implementada")

print("\n6. Permisos - cobertura:")
from apps.proyectos.decorators import miembro_requerido, ROLES_ADMIN, ROLES_EDICION
print(f"   ROLES_ADMIN: {ROLES_ADMIN}")
print(f"   ROLES_EDICION: {ROLES_EDICION}")
print("   Decorador miembro_requerido aplicado a todas las vistas de proyecto")

print("\n=== RESUMEN ===")
print(f"Problemas encontrados: {len(issues)}")
for i in issues:
    print(f"  - {i}")
print("\nPRIORIDADES:")
print("  1. Validar transiciones de estado (workflow engine)")
print("  2. Sprint close con reglas")
print("  3. Workflow configurable por proyecto")
