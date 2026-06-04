import django, os, sys
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()
from apps.gestion.models import AsignacionActividad

print('Todas las asignaciones:')
for a in AsignacionActividad.objects.all():
    pd = a.planificacion_detalle
    p_activo = pd.planificacion.activo if pd else 'N/A'
    pd_activo = pd.activo if pd else '?'
    print(f'id={a.pk} user={a.user.cedula} estado={a.estado} activo={a.activo} pd_activo={pd_activo} planif_activo={p_activo}')
