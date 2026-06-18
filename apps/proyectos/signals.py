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

    mapping = {
        "Pendiente": "pendiente", "EnCurso": "en_curso", "Pausada": "pausada",
        "Finalizada": "finalizada", "Cancelada": "cancelada", "Trasladada": "finalizada",
    }
    nuevo_estado = mapping.get(instance.estado, tarea.estado)
    if tarea.estado != nuevo_estado:
        tarea.estado = nuevo_estado
        tarea.save(update_fields=["estado"])

        # Actualizar historia padre
        if tarea.historia:
            old_hist_estado = tarea.historia.estado
            tarea.historia.actualizar_estado()
            # Cuando la historia recien llega a revision, crear actividad para cada revisor
            if tarea.historia.estado == "revision" and old_hist_estado != "revision":
                from apps.proyectos.models import MiembroProyecto
                from apps.proyectos.decorators import ROLES_REVISION
                from apps.gestion.views import _notificar_usuario
                from apps.actividades.models import Actividad, TipoActividad

                subarea = tarea.proyecto.subareas.first()
                if subarea:
                    tipo_rev, _ = TipoActividad.objects.get_or_create(
                        subarea=subarea, nombre="Revision de Proyecto",
                        defaults={"requiere_fecha_limite": False, "requiere_entregable": False, "es_flash": False}
                    )
                    act_rev, _ = Actividad.objects.get_or_create(
                        subarea=subarea, tipo_actividad=tipo_rev,
                        defaults={"nombre": f"Revision de Proyecto - {tarea.proyecto.codigo}"}
                    )
                    historia = tarea.historia
                    revisores = MiembroProyecto.objects.filter(
                        proyecto=tarea.proyecto, activo=True, rol__in=ROLES_REVISION
                    )
                    for m in revisores:
                        AsignacionActividad.objects.get_or_create(
                            user=m.user,
                            nombre_actividad=f"[Revision] {historia.codigo}: {historia.titulo[:80]}",
                            origen="Revision",
                            activo=True,
                            defaults={
                                "actividad": act_rev,
                                "estado": "Pendiente",
                                "origen_user": tarea.asignado_a or tarea.creador,
                                "nombre_tipo": "Revision de Historia",
                            }
                        )
                        _notificar_usuario(m.user_id, "nueva_revision", {
                            "historia": historia.titulo,
                            "codigo": historia.codigo,
                            "proyecto": tarea.proyecto.codigo,
                        })


def crear_asignacion_desde_tarea(tarea):
    """Crea una AsignacionActividad vinculada a una Tarea de proyecto."""
    from apps.gestion.models import AsignacionActividad
    from apps.actividades.models import Actividad, TipoActividad

    if tarea.asignacion or not tarea.asignado_a:
        return None

    actividad = tarea.actividad_catalogo
    if not actividad:
        subarea = tarea.proyecto.subareas.first()
        if not subarea:
            return None
        tipo, _ = TipoActividad.objects.get_or_create(
            subarea=subarea,
            nombre="Tarea de Proyecto",
            defaults={"requiere_fecha_limite": False, "requiere_entregable": False, "es_flash": False}
        )
        actividad, _ = Actividad.objects.get_or_create(
            subarea=subarea, tipo_actividad=tipo,
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
