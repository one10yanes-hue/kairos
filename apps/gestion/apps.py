from django.apps import AppConfig


class GestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gestion"
    verbose_name = "Gestion de Actividades"

    def ready(self):
        import apps.gestion.signals
