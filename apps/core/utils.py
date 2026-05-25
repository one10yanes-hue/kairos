import random
import string
from django.db.models import Q, Model

CHARS = string.ascii_letters + string.digits + "-_"
MODELS_CACHE = []


def _get_all_models():
    global MODELS_CACHE
    if not MODELS_CACHE:
        from apps.accounts.models import Empresa
        from apps.estructura.models import Area, SubArea
        from apps.actividades.models import TipoActividad, Actividad
        MODELS_CACHE = [Empresa, Area, SubArea, TipoActividad, Actividad]
    return MODELS_CACHE


def generar_codigo(longitud=6):
    """Genera un codigo unico de N caracteres no existente en ninguna tabla."""
    for _ in range(100):
        codigo = "".join(random.choices(CHARS, k=longitud))
        if not _codigo_existe(codigo):
            return codigo
    raise RuntimeError("No se pudo generar un codigo unico despues de 100 intentos.")


def _codigo_existe(codigo):
    """Verifica si un codigo ya existe en alguna de las tablas."""
    for model in _get_all_models():
        if model.objects.filter(codigo=codigo).exists():
            return True
    return False
