"""Context processor para sidebar contextual de proyectos"""
import re
from apps.proyectos.models import Proyecto


def proyecto_contexto(request):
    """Detecta si estamos en una URL de proyecto y agrega info al contexto."""
    match = re.match(r"^/proyectos/(\d+)/", request.path)
    if match and request.user.is_authenticated:
        proyecto = Proyecto.objects.filter(pk=int(match.group(1)), activo=True).first()
        if proyecto:
            return {"proyecto_ctx": proyecto}
    return {"proyecto_ctx": None}
