from django.db import models
from django.db.models import Sum
from apps.accounts.models import User


class Proyecto(models.Model):
    ESTADOS = [
        ("activo", "Activo"),
        ("pausado", "Pausado"),
        ("finalizado", "Finalizado"),
        ("cancelado", "Cancelado"),
    ]
    codigo = models.CharField(max_length=8, unique=True)
    nombre = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True)
    objetivo = models.TextField(blank=True)

    subareas = models.ManyToManyField("estructura.SubArea", blank=True, related_name="proyectos")
    empresa = models.ForeignKey("accounts.Empresa", on_delete=models.PROTECT, null=True, blank=True, related_name="proyectos")
    manager = models.ForeignKey(User, on_delete=models.PROTECT, related_name="proyectos_gestionados")

    estado = models.CharField(max_length=20, choices=ESTADOS, default="activo")
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin_estimada = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateField(null=True, blank=True)

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "proyecto"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def avance(self):
        total = self.tareas.filter(activo=True).count()
        if total == 0:
            return 0
        return int(self.tareas.filter(activo=True, estado="finalizada").count() / total * 100)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.fecha_inicio and self.fecha_fin_estimada and self.fecha_inicio > self.fecha_fin_estimada:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha fin estimada.")


class MiembroProyecto(models.Model):
    ROLES = [
        ("lider", "Lider de Proyecto"),
        ("responsable", "Responsable"),
        ("revisor", "Revisor / QA"),
        ("aprobador", "Aprobador"),
        ("ejecutor", "Ejecutor"),
        ("observador", "Observador"),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="membresias")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="proyectos_miembro")
    rol = models.CharField(max_length=20, choices=ROLES, default="developer")
    activo = models.BooleanField(default=True)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "miembro_proyecto"
        unique_together = ["proyecto", "user"]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_rol_display()}"


class Etiqueta(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="etiquetas")
    nombre = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#6b7280")
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "etiqueta"
        unique_together = ["proyecto", "nombre"]

    def __str__(self):
        return self.nombre


class Sprint(models.Model):
    ESTADOS = [
        ("planificado", "Planificado"),
        ("activo", "Activo"),
        ("finalizado", "Finalizado"),
        ("cancelado", "Cancelado"),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="sprints")
    nombre = models.CharField(max_length=200)
    objetivo = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="planificado")
    numero = models.IntegerField()
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sprint"
        ordering = ["proyecto", "numero"]
        unique_together = ["proyecto", "numero"]

    def __str__(self):
        return f"{self.proyecto.codigo} - Sprint {self.numero}: {self.nombre}"

    @property
    def velocidad(self):
        return self.historias.filter(estado="done").aggregate(
            total=Sum("puntos_historia")
        )["total"] or 0

    @property
    def puntos_comprometidos(self):
        return self.historias.filter(activo=True).aggregate(
            total=Sum("puntos_historia")
        )["total"] or 0

    @property
    def avance_tareas(self):
        total = self.tareas.filter(activo=True).count()
        if total == 0:
            return 0
        return int(self.tareas.filter(activo=True, estado="finalizada").count() / total * 100)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError("La fecha de inicio del sprint no puede ser posterior a la fecha fin.")


class HistoriaUsuario(models.Model):
    ESTADOS = [
        ("backlog", "Backlog"),
        ("sprint_backlog", "Sprint Backlog"),
        ("en_progreso", "En Progreso"),
        ("revision", "En Revision"),
        ("done", "Done"),
    ]
    PRIORIDADES = [
        ("must", "Must Have"),
        ("should", "Should Have"),
        ("could", "Could Have"),
        ("wont", "Won't Have"),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="historias")
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="historias")
    etiquetas = models.ManyToManyField(Etiqueta, blank=True)
    codigo = models.CharField(max_length=16, unique=True)
    titulo = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True)
    criterios_aceptacion = models.TextField(blank=True)
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default="should")
    puntos_historia = models.IntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="backlog")
    orden = models.IntegerField(default=0)
    creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="historias_creadas")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historia_usuario"
        ordering = ["proyecto", "orden", "-fecha_creacion"]

    def __str__(self):
        return f"{self.codigo}: {self.titulo}"

    @property
    def avance_tareas(self):
        total = self.tareas.filter(activo=True).count()
        if total == 0:
            return 0
        return int(self.tareas.filter(activo=True, estado="finalizada").count() / total * 100)

    def actualizar_estado(self):
        tareas = self.tareas.filter(activo=True)
        if not tareas.exists():
            return
        estados = set(tareas.values_list("estado", flat=True))
        if estados == {"finalizada"}:
            self.estado = "revision"
        elif "en_curso" in estados or "pausada" in estados or "bloqueada" in estados:
            self.estado = "en_progreso"
        elif "pendiente" in estados and "finalizada" in estados:
            self.estado = "en_progreso"
        elif estados == {"pendiente"}:
            self.estado = "sprint_backlog" if self.sprint else "backlog"
        self.save(update_fields=["estado"])

    def clean(self):
        from django.core.exceptions import ValidationError
        transiciones = _get_transiciones(self.proyecto, "historia")
        if self.pk:
            try:
                old = HistoriaUsuario.objects.get(pk=self.pk)
                if old.estado != self.estado and self.estado not in transiciones.get(old.estado, []):
                    raise ValidationError(f"No se puede pasar de '{old.get_estado_display()}' a '{self.get_estado_display()}'.")
            except HistoriaUsuario.DoesNotExist:
                pass


class Tarea(models.Model):
    TIPOS = [
        ("tarea", "Tarea"),
        ("bug", "Bug"),
        ("mejora", "Mejora"),
        ("documentacion", "Documentacion"),
        ("prueba", "Prueba"),
        ("diseno", "Diseno"),
    ]
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("en_curso", "En Curso"),
        ("pausada", "Pausada"),
        ("bloqueada", "Bloqueada"),
        ("finalizada", "Finalizada"),
        ("revision", "En Revision"),
        ("cancelada", "Cancelada"),
    ]
    PRIORIDADES = [
        ("must", "Must Have"),
        ("should", "Should Have"),
        ("could", "Could Have"),
        ("wont", "Won't Have"),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="tareas")
    historia = models.ForeignKey(HistoriaUsuario, on_delete=models.CASCADE, null=True, blank=True, related_name="tareas")
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="tareas")
    etiquetas = models.ManyToManyField(Etiqueta, blank=True)
    bloqueada_por = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="bloquea_a")
    asignacion = models.OneToOneField("gestion.AsignacionActividad", on_delete=models.SET_NULL, null=True, blank=True, related_name="tarea_proyecto")
    actividad_catalogo = models.ForeignKey("actividades.Actividad", on_delete=models.PROTECT, null=True, blank=True, related_name="tareas_proyecto")
    codigo = models.CharField(max_length=16, unique=True)
    titulo = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default="tarea")
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default="should")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    asignado_a = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="tareas_asignadas")
    creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="tareas_creadas")
    fecha_limite = models.DateField(null=True, blank=True, verbose_name="Fecha limite")
    estimacion_horas = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tarea"
        ordering = ["proyecto", "sprint", "historia__orden", "fecha_creacion"]

    def __str__(self):
        return f"{self.codigo}: {self.titulo}"

    @property
    def tiempo_trabajado(self):
        asig = self.asignacion
        if asig:
            return asig.tiempo_formateado()
        return ""

    def clean(self):
        from django.core.exceptions import ValidationError
        transiciones = _get_transiciones(self.proyecto, "tarea")
        if self.pk:
            try:
                old = Tarea.objects.get(pk=self.pk)
                if old.estado != self.estado and self.estado not in transiciones.get(old.estado, []):
                    raise ValidationError(
                        f"Transicion invalida: '{old.get_estado_display()}' -> '{self.get_estado_display()}'"
                    )
            except Tarea.DoesNotExist:
                pass


class Incidencia(models.Model):
    TIPOS = [
        ("bug", "Bug"),
        ("mejora", "Mejora"),
        ("pregunta", "Pregunta / Soporte"),
        ("riesgo", "Riesgo"),
    ]
    SEVERIDAD = [
        ("critica", "Critica"),
        ("alta", "Alta"),
        ("media", "Media"),
        ("baja", "Baja"),
    ]
    ESTADOS = [
        ("abierta", "Abierta"),
        ("triaged", "En Triage"),
        ("en_progreso", "En Progreso"),
        ("resuelta", "Resuelta"),
        ("cerrada", "Cerrada"),
        ("duplicada", "Duplicada"),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="incidencias")
    etiquetas = models.ManyToManyField(Etiqueta, blank=True)
    tarea = models.ForeignKey(Tarea, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias")
    historia = models.ForeignKey(HistoriaUsuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias")
    asignacion = models.OneToOneField("gestion.AsignacionActividad", on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencia")
    codigo = models.CharField(max_length=16, unique=True)
    titulo = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True)
    pasos_reproducir = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default="bug")
    severidad = models.CharField(max_length=10, choices=SEVERIDAD, default="media")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="abierta")
    reportado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_reportadas")
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_asignadas")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "incidencia"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.codigo}: {self.titulo}"

    def clean(self):
        from django.core.exceptions import ValidationError
        transiciones = _get_transiciones(self.proyecto, "incidencia")
        if self.pk:
            try:
                old = Incidencia.objects.get(pk=self.pk)
                if old.estado != self.estado and self.estado not in transiciones.get(old.estado, []):
                    raise ValidationError(f"No se puede pasar de '{old.get_estado_display()}' a '{self.get_estado_display()}'.")
            except Incidencia.DoesNotExist:
                pass


class ComentarioIncidencia(models.Model):
    incidencia = models.ForeignKey(Incidencia, on_delete=models.CASCADE, related_name="comentarios")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="comentarios_incidencias")
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comentario_incidencia"
        ordering = ["fecha"]


class RegistroAvance(models.Model):
    TIPOS = [
        ("historia_completada", "Historia completada"),
        ("sprint_iniciado", "Sprint iniciado"),
        ("sprint_finalizado", "Sprint finalizado"),
        ("incidencia_resuelta", "Incidencia resuelta"),
        ("tarea_finalizada", "Tarea finalizada"),
        ("comentario", "Comentario"),
        ("bloqueo", "Bloqueo reportado"),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="avances")
    tipo = models.CharField(max_length=30, choices=TIPOS)
    descripcion = models.TextField()
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    referencia_id = models.IntegerField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "registro_avance"
        ordering = ["-fecha"]


# ── Workflow engine: transiciones por proyecto ──

HARDCODED_TAREA = {
    "pendiente": ["en_curso", "cancelada", "bloqueada"],
    "en_curso": ["pausada", "finalizada", "cancelada", "bloqueada"],
    "pausada": ["en_curso", "finalizada", "cancelada", "bloqueada"],
    "bloqueada": ["en_curso", "cancelada"],
    "finalizada": [],
    "revision": ["finalizada", "pendiente"],
    "cancelada": [],
}

HARDCODED_HISTORIA = {
    "backlog": ["sprint_backlog"],
    "sprint_backlog": ["en_progreso", "backlog"],
    "en_progreso": ["revision", "backlog", "sprint_backlog"],
    "revision": ["done", "en_progreso"],
    "done": ["backlog"],
}

HARDCODED_INCIDENCIA = {
    "abierta": ["triaged", "en_progreso", "cerrada", "duplicada"],
    "triaged": ["en_progreso", "cerrada"],
    "en_progreso": ["resuelta", "cerrada"],
    "resuelta": ["cerrada", "en_progreso"],
    "cerrada": ["abierta"],
    "duplicada": ["abierta"],
}


def _get_transiciones(proyecto, entidad):
    """Devuelve {estado_origen: [estados_destino]} desde WorkflowConfig o hardcodeado."""
    configs = WorkflowConfig.objects.filter(proyecto=proyecto, entidad=entidad, activo=True)
    if not configs.exists():
        if entidad == "tarea":
            return HARDCODED_TAREA
        elif entidad == "historia":
            return HARDCODED_HISTORIA
        elif entidad == "incidencia":
            return HARDCODED_INCIDENCIA
        return {}
    trans = {}
    for cfg in configs:
        trans.setdefault(cfg.estado_origen, []).append(cfg.estado_destino)
    return trans


class WorkflowConfig(models.Model):
    """Configuracion de estados y transiciones por proyecto y tipo de entidad."""
    ENTIDADES = [
        ("historia", "Historia de Usuario"),
        ("tarea", "Tarea"),
        ("incidencia", "Incidencia"),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="workflows")
    entidad = models.CharField(max_length=20, choices=ENTIDADES)
    estado_origen = models.CharField(max_length=30)
    estado_destino = models.CharField(max_length=30)
    requiere_rol = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "workflow_config"
        unique_together = ["proyecto", "entidad", "estado_origen", "estado_destino"]
