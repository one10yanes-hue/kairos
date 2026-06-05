from django.db.models.signals import pre_save
from django.dispatch import receiver
from apps.gestion.models import AsignacionActividad, TrasladoActividad


@receiver(pre_save, sender=AsignacionActividad)
def cancelar_traslados_en_terminal(sender, instance, **kwargs):
    """Cuando una AsignacionActividad pasa a estado terminal (Finalizada,
       Cancelada, Trasladada, Revision), cancela automaticamente
       cualquier traslado pendiente asociado."""
    if instance.estado in ["Finalizada", "Cancelada", "Trasladada", "Revision"]:
        # Si es nuevo, no aplicar (no habia traslados previos)
        if instance._state.adding:
            return
        # Obtener el estado anterior desde la BD
        try:
            old = AsignacionActividad.objects.get(pk=instance.pk)
        except AsignacionActividad.DoesNotExist:
            return
        # Si ya estaba en terminal, no repetir
        if old.estado in ["Finalizada", "Cancelada", "Trasladada", "Revision"]:
            return
        # Cancelar traslados pendientes
        TrasladoActividad.objects.filter(
            asignacion_origen=instance, estado="Pendiente", activo=True
        ).update(estado="Cancelado")
