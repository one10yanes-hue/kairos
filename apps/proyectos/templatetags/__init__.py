"""Template tags para permisos de proyecto"""
from django import template
from apps.proyectos.decorators import ROLES_EDICION, ROLES_ADMIN

register = template.Library()


@register.filter
def puede_editar(usuario_proyecto):
    """¿Puede este miembro crear/editar contenido?"""
    if usuario_proyecto is None:
        return True  # Master/Admin sin membresía
    return usuario_proyecto.rol in ROLES_EDICION


@register.filter
def puede_administrar(usuario_proyecto):
    """¿Puede este miembro gestionar equipo, aprobar?"""
    if usuario_proyecto is None:
        return True
    return usuario_proyecto.rol in ROLES_ADMIN


@register.filter
def es_aprobador(usuario_proyecto):
    """¿Puede este miembro aprobar/rechazar?"""
    if usuario_proyecto is None:
        return True
    return usuario_proyecto.rol in ["lider", "responsable", "aprobador", "revisor"]
