from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class CedulaExpedicionBackend(BaseBackend):
    def authenticate(self, request, cedula=None, fecha_expedicion=None, **kwargs):
        try:
            user = User.objects.get(cedula=cedula, is_active=True, activo=True)
            if user.fecha_expedicion.strftime("%Y-%m-%d") == fecha_expedicion:
                return user
        except User.DoesNotExist:
            pass
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
