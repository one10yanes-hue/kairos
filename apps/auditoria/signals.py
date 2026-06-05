from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import AuditSession


from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import AuditSession


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    try:
        ahora = timezone.now()
        # Cerrar sesion abierta previa
        AuditSession.objects.filter(user=user, fin__isnull=True).update(fin=ahora)
        # Nueva sesion
        AuditSession.objects.create(
            user=user,
            session_key=request.session.session_key,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
        # Cleanup: borrar registros > 30 dias (una vez cada login)
        limite = ahora - timedelta(days=30)
        AuditSession.objects.filter(inicio__lt=limite).delete()
    except Exception:
        pass


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if not user:
        return
    try:
        ahora = timezone.now()
        key = request.session.session_key if hasattr(request, "session") else None
        if key and AuditSession.objects.filter(user=user, session_key=key, fin__isnull=True).exists():
            AuditSession.objects.filter(user=user, session_key=key, fin__isnull=True).update(fin=ahora)
        else:
            sesion = AuditSession.objects.filter(user=user, fin__isnull=True).order_by("-inicio").first()
            if sesion:
                sesion.fin = ahora
                sesion.save()
    except Exception:
        pass
