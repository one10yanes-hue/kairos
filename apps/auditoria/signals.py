from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import AuditSession


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    try:
        AuditSession.objects.create(
            user=user,
            session_key=request.session.session_key,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
    except Exception:
        pass


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if not user:
        return
    try:
        key = request.session.session_key if hasattr(request, "session") else None
        if key:
            AuditSession.objects.filter(user=user, session_key=key, fin__isnull=True).update(fin=timezone.now())
        else:
            AuditSession.objects.filter(user=user, fin__isnull=True).order_by("-inicio").first().update(fin=timezone.now())
    except Exception:
        pass
