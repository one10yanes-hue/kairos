"""Template tags para permisos de proyecto"""
from django import template
from apps.proyectos.decorators import ROLES_EDICION, ROLES_ADMIN, ROLES_REVISION

register = template.Library()


@register.filter
def puede_editar(usuario_proyecto):
    """Puede crear/editar contenido (Lider o Responsable)?"""
    if usuario_proyecto is None:
        return True  # Master/Admin sin membresia
    return usuario_proyecto.rol in ROLES_EDICION


@register.filter
def puede_administrar(usuario_proyecto):
    """Puede gestionar equipo, aprobar?"""
    if usuario_proyecto is None:
        return True
    return usuario_proyecto.rol in ROLES_ADMIN


@register.filter
def es_aprobador(usuario_proyecto):
    """Puede aprobar/rechazar historias?"""
    if usuario_proyecto is None:
        return True
    return usuario_proyecto.rol in ROLES_REVISION
