from django.contrib import admin
from .models import Proyecto, MiembroProyecto, Etiqueta, Sprint, HistoriaUsuario, Tarea, Incidencia, ComentarioIncidencia

admin.site.register(Proyecto)
admin.site.register(MiembroProyecto)
admin.site.register(Etiqueta)
admin.site.register(Sprint)
admin.site.register(HistoriaUsuario)
admin.site.register(Tarea)
admin.site.register(Incidencia)
admin.site.register(ComentarioIncidencia)
