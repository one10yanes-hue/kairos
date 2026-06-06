from django.apps import AppConfig


class ProyectosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.proyectos"
    verbose_name = "Gestión de Proyectos"

    def ready(self):
        import apps.proyectos.signals
