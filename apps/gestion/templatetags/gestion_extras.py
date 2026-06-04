from django import template
from django.utils import timezone
from datetime import timedelta, date as dt_date

register = template.Library()


def _local_date(dt):
    """Convierte datetime a fecha local (America/Bogota)."""
    if not dt:
        return None
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    if hasattr(dt, "date"):
        return dt.date()
    if isinstance(dt, dt_date):
        return dt
    return None


@register.filter
def deadline_class(fecha):
    d = _local_date(fecha)
    if not d:
        return ""
    hoy = timezone.localtime(timezone.now()).date()
    if d < hoy:
        return "bg-danger text-white"
    if d <= hoy + timedelta(days=1):
        return "bg-warning text-dark"
    return "bg-info text-white"


@register.filter
def deadline_label(fecha):
    d = _local_date(fecha)
    if not d:
        return ""
    hoy = timezone.localtime(timezone.now()).date()
    if d < hoy:
        dias = (hoy - d).days
        if dias == 0:
            return "Vencida hoy"
        return f"Vencida hace {dias}d"
    if d == hoy:
        return "Vence hoy"
    if d == hoy + timedelta(days=1):
        return "Vence manana"
    return f"Vence en {(d - hoy).days}d"


@register.filter
def days_overdue(fecha):
    d = _local_date(fecha)
    if not d:
        return 0
    hoy = timezone.localtime(timezone.now()).date()
    if d < hoy:
        return (hoy - d).days
    return 0
