"""Señales que sincronizan Tarea ↔ AsignacionActividad.
   Cuando la AsignacionActividad cambia de estado en el Tablero,
   la Tarea del proyecto se actualiza automáticamente."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.gestion.models import AsignacionActividad


@receiver(post_save, sender=AsignacionActividad)
def sync_tarea_from_asignacion(sender, instance, created, **kwargs):
    if not hasattr(instance, 'tarea_proyecto') or not instance.tarea_proyecto:
        return
    tarea = instance.tarea_proyecto
    # Mapear estado AsignacionActividad → Tarea
    mapping = {
        "Pendiente": "pendiente", "EnCurso": "en_curso", "Pausada": "pausada",
        "Finalizada": "finalizada", "Revision": "revision", "Cancelada": "cancelada",
        "Trasladada": "finalizada",
    }
    nuevo_estado = mapping.get(instance.estado, tarea.estado)
    if tarea.estado != nuevo_estado:
        tarea.estado = nuevo_estado
        tarea.save(update_fields=["estado"])

    # Actualizar estado de la historia padre
    if tarea.historia:
        tarea.historia.actualizar_estado()


def crear_asignacion_desde_tarea(tarea):
    """Crea una AsignacionActividad vinculada a una Tarea de proyecto."""
    from apps.gestion.models import AsignacionActividad
    from apps.actividades.models import Actividad, TipoActividad

    if tarea.asignacion or not tarea.asignado_a:
        return None

    actividad = tarea.actividad_catalogo
    if not actividad:
        tipo, _ = TipoActividad.objects.get_or_create(
            subarea=tarea.proyecto.subarea,
            nombre="Tarea de Proyecto",
            defaults={"requiere_fecha_limite": False, "requiere_entregable": False, "es_flash": False}
        )
        actividad, _ = Actividad.objects.get_or_create(
            subarea=tarea.proyecto.subarea, tipo_actividad=tipo,
            defaults={"nombre": f"Tarea de Proyecto - {tarea.proyecto.codigo}"}
        )

    asignacion = AsignacionActividad.objects.create(
        user=tarea.asignado_a,
        actividad=actividad,
        estado="Pendiente",
        origen="Proyecto",
        origen_user=tarea.creador,
        nombre_actividad=tarea.titulo,
        nombre_tipo=actividad.tipo_actividad.nombre,
    )
    tarea.asignacion = asignacion
    tarea.save(update_fields=["asignacion"])
    return asignacion
