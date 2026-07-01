"""Senales que sincronizan Tarea ↔ AsignacionActividad.
   Cuando la AsignacionActividad cambia de estado en el Tablero,
   la Tarea del proyecto se actualiza automaticamente."""
from django.db.models.signals import pre_save, post_save
from django.db import transaction
from django.dispatch import receiver
from apps.gestion.models import AsignacionActividad
from apps.accounts.models import User


def _init_workflow_if_empty(proyecto):
    """Crea WorkflowConfig por defecto (revision) si el proyecto no tiene ninguno."""
    from apps.proyectos.models import WorkflowConfig
    from apps.proyectos.workflow_presets import PRESETS
    if WorkflowConfig.objects.filter(proyecto=proyecto).exists():
        return
    defaults = PRESETS.get("revision", {})
    for ent, transiciones in defaults.items():
        for origen, destino in transiciones:
            WorkflowConfig.objects.get_or_create(
                proyecto=proyecto, entidad=ent,
                estado_origen=origen, estado_destino=destino,
                defaults={"activo": True}
            )


@receiver(pre_save, sender=AsignacionActividad)
def _capturar_estado_previo(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_estado = AsignacionActividad.objects.get(pk=instance.pk).estado
        except AsignacionActividad.DoesNotExist:
            instance._old_estado = None
    else:
        instance._old_estado = None


@receiver(post_save, sender=AsignacionActividad, dispatch_uid="proyectos.sync_tarea")
def sync_tarea_from_asignacion(sender, instance, created, **kwargs):
    if not hasattr(instance, 'tarea_proyecto') or not instance.tarea_proyecto:
        return
    if hasattr(instance, '_old_estado') and instance._old_estado == instance.estado:
        return

    tarea = instance.tarea_proyecto
    _init_workflow_if_empty(tarea.proyecto)

    mapping = {
        "Pendiente": "pendiente", "EnCurso": "en_curso", "Pausada": "pausada",
        "Finalizada": "finalizada", "Cancelada": "cancelada",
        "Revision": "revision",
    }
    nuevo_estado = mapping.get(instance.estado, tarea.estado)
    if instance.estado == "Trasladada":
        return

    if tarea.estado != nuevo_estado:
        tarea.estado = nuevo_estado
        tarea.save(update_fields=["estado"])

        from apps.proyectos.models import RegistroAvance
        estado_label = dict(tarea.ESTADOS).get(nuevo_estado, nuevo_estado)
        RegistroAvance.objects.create(
            proyecto=tarea.proyecto, tipo="tarea_finalizada" if nuevo_estado == "finalizada" else "comentario",
            descripcion=f"Tarea {tarea.codigo} -> {estado_label} ({instance.user.get_full_name() if instance.user else 'Sistema'})",
            user=instance.user or tarea.creador, referencia_id=tarea.pk
        )

        if nuevo_estado == "finalizada":
            from apps.proyectos.models import _get_transiciones
            transiciones = _get_transiciones(tarea.proyecto, "tarea")
            if "revision" in transiciones.get("finalizada", []):
                tarea.estado = "revision"
                tarea.save(update_fields=["estado"])
                RegistroAvance.objects.create(
                    proyecto=tarea.proyecto, tipo="comentario",
                    descripcion=f"Tarea {tarea.codigo} -> En Revision (auto, pendiente de QA)",
                    user=instance.user or tarea.creador, referencia_id=tarea.pk
                )
                _crear_cards_revision_tarea(tarea)

        if tarea.historia:
            old_hist_estado = tarea.historia.estado
            tarea.historia.actualizar_estado()
            if tarea.historia.estado == "revision" and old_hist_estado != "revision":
                _crear_cards_aprobar_historia(tarea.historia, tarea.asignado_a or tarea.creador)


def _crear_cards_revision_tarea(tarea):
    """Crea cards [Revisar] T-NNN para los revisores cuando una tarea entra en revision."""
    import logging
    from apps.proyectos.models import MiembroProyecto
    from apps.actividades.models import Actividad, TipoActividad
    from apps.gestion.models import AsignacionActividad
    from apps.gestion.views import _notificar_usuario

    proyecto = tarea.proyecto
    subarea = proyecto.subareas.first()
    if not subarea:
        return

    tipo_rev, _ = TipoActividad.objects.get_or_create(
        subarea=subarea, nombre="Revision de Proyecto",
        defaults={"requiere_fecha_limite": False, "requiere_entregable": False, "es_flash": False}
    )
    act_rev, _ = Actividad.objects.get_or_create(
        subarea=subarea, tipo_actividad=tipo_rev,
        defaults={"nombre": f"Revision de Proyecto - {proyecto.codigo}"}
    )

    if tarea.revisor_id:
        revisores = [tarea.revisor]
    else:
        revisores = list(MiembroProyecto.objects.filter(
            proyecto=proyecto, activo=True, rol__in=["lider", "revisor"]
        ).select_related("user"))

    if not revisores:
        logging.getLogger("proyectos").warning(
            f"Tarea {tarea.codigo} entro revision sin revisores en {proyecto.codigo}"
        )
        return

    for m in revisores:
        user = m if isinstance(m, User) else m.user
        uid = m.pk if isinstance(m, User) else m.user_id
        _, created = AsignacionActividad.objects.get_or_create(
            user=user,
            nombre_actividad=f"[Revisar] {tarea.codigo}: {tarea.titulo[:80]}",
            origen="Revision",
            activo=True,
            defaults={
                "actividad": act_rev,
                "estado": "Pendiente",
                "origen_user": tarea.asignado_a or tarea.creador,
                "nombre_tipo": "Revision de Tarea",
            }
        )
        if created:
            _notificar_usuario(uid, "nueva_revision", {
                "tarea": tarea.titulo, "codigo": tarea.codigo,
                "proyecto": proyecto.codigo,
            })


def _crear_cards_aprobar_historia(historia, origen_user=None):
    """Crea cards [Aprobar] US-NNN cuando una historia entra en revision."""
    from apps.proyectos.models import MiembroProyecto
    from apps.actividades.models import Actividad, TipoActividad
    from apps.gestion.models import AsignacionActividad
    from apps.gestion.views import _notificar_usuario

    proyecto = historia.proyecto
    subarea = proyecto.subareas.first()
    if not subarea:
        return

    tipo_rev, _ = TipoActividad.objects.get_or_create(
        subarea=subarea, nombre="Revision de Proyecto",
        defaults={"requiere_fecha_limite": False, "requiere_entregable": False, "es_flash": False}
    )
    act_rev, _ = Actividad.objects.get_or_create(
        subarea=subarea, tipo_actividad=tipo_rev,
        defaults={"nombre": f"Revision de Proyecto - {proyecto.codigo}"}
    )

    if historia.aprobador_id:
        aprobadores = [historia.aprobador]
    else:
        aprobadores = list(MiembroProyecto.objects.filter(
            proyecto=proyecto, activo=True, rol__in=["lider", "responsable", "aprobador"]
        ).select_related("user"))

    for m in aprobadores:
        user = m if isinstance(m, User) else m.user
        uid = m.pk if isinstance(m, User) else m.user_id
        _, created = AsignacionActividad.objects.get_or_create(
            user=user,
            nombre_actividad=f"[Aprobar] {historia.codigo}: {historia.titulo[:80]}",
            origen="Revision",
            activo=True,
            defaults={
                "actividad": act_rev,
                "estado": "Pendiente",
                "origen_user": origen_user,
                "nombre_tipo": "Revision de Historia",
            }
        )
        if created:
            _notificar_usuario(uid, "nueva_revision", {
                "historia": historia.titulo,
                "codigo": historia.codigo,
                "proyecto": proyecto.codigo,
            })


def crear_asignacion_desde_tarea(tarea):
    """Crea una AsignacionActividad vinculada a una Tarea de proyecto."""
    from apps.gestion.models import AsignacionActividad
    from apps.actividades.models import Actividad, TipoActividad

    if tarea.asignacion or not tarea.asignado_a:
        return None

    from apps.proyectos.models import MiembroProyecto
    if not MiembroProyecto.objects.filter(proyecto=tarea.proyecto, user=tarea.asignado_a, activo=True, rol="ejecutor").exists():
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
