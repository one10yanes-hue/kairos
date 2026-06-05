from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from apps.accounts.models import User
from apps.actividades.models import Actividad
from apps.planificacion.models import PlanificacionDetalle


class AsignacionActividad(models.Model):
    ESTADOS = [
        ("Pendiente", "Pendiente"),
        ("EnCurso", "En Curso"),
        ("Pausada", "Pausada"),
        ("Finalizada", "Finalizada"),
        ("Cancelada", "Cancelada"),
        ("Trasladada", "Trasladada"),
        ("Revision", "En Revision"),
    ]
    ESTADOS_REVISION = [
        ("pendiente", "Pendiente"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ]
    planificacion_detalle = models.ForeignKey(
        PlanificacionDetalle, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="asignaciones"
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="asignaciones")
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="asignaciones")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="Pendiente")
    origen = models.CharField(max_length=20, blank=True, null=True, help_text="Planificacion, Traslado, Manual")
    origen_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="asignaciones_origen")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    nombre_actividad = models.CharField(max_length=300, blank=True, help_text="Nombre congelado de la actividad al momento de la asignacion")
    nombre_tipo = models.CharField(max_length=200, blank=True, help_text="Nombre congelado del tipo de actividad al momento de la asignacion")
    tiempo_total_segundos = models.IntegerField(default=0, help_text="Tiempo cacheado hasta la ultima pausa/finalizacion")
    tiempo_pausado_segundos = models.IntegerField(default=0, help_text="Tiempo total en pausa cacheado")
    prorroga_count = models.IntegerField(default=0, help_text="Cantidad de veces que fue reprogramado")
    dias_vencida = models.IntegerField(default=0, help_text="Dias de retraso al momento de finalizar/trasladar")
    entregable = models.FileField(upload_to="entregables/", blank=True, null=True)
    estado_revision = models.CharField(max_length=20, choices=ESTADOS_REVISION, default="pendiente")
    revision_comentario = models.TextField(blank=True, null=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asignacion_actividad"
        verbose_name = "Asignacion de Actividad"
        verbose_name_plural = "Asignaciones de Actividad"
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=models.Q(estado="EnCurso", activo=True), name="unique_en_curso_por_usuario"),
        ]

    def __str__(self):
        return f"{self.actividad.nombre} - {self.user} ({self.estado})"

    def tiempo_efectivo(self):
        total = self.tiempo_total_segundos
        if self.estado == "EnCurso":
            ultimo = self.registros.filter(
                activo=True, evento__in=["Inicio", "Reanudacion"]
            ).order_by("-fecha_hora").first()
            if ultimo:
                total += (timezone.now() - ultimo.fecha_hora).total_seconds()
        return total

    def tiempo_pausado(self):
        total = self.tiempo_pausado_segundos
        if self.estado == "Pausada":
            ultimo = self.registros.filter(
                activo=True, evento="Pausa"
            ).order_by("-fecha_hora").first()
            if ultimo:
                total += (timezone.now() - ultimo.fecha_hora).total_seconds()
        return total

    def tiempo_total(self):
        return self.tiempo_efectivo() + self.tiempo_pausado()

    def recalcular_tiempo(self):
        registros = self.registros.filter(activo=True).order_by("fecha_hora")
        total_activo = 0
        total_pausado = 0
        inicio = None
        pausa_inicio = None
        for r in registros:
            if r.evento in ("Inicio", "Reanudacion"):
                inicio = r.fecha_hora
                if pausa_inicio:
                    total_pausado += (r.fecha_hora - pausa_inicio).total_seconds()
                    pausa_inicio = None
            elif r.evento == "Pausa":
                if inicio:
                    total_activo += (r.fecha_hora - inicio).total_seconds()
                    inicio = None
                pausa_inicio = r.fecha_hora
            elif r.evento == "Finalizacion":
                if inicio:
                    total_activo += (r.fecha_hora - inicio).total_seconds()
                    inicio = None
                if pausa_inicio:
                    total_pausado += (r.fecha_hora - pausa_inicio).total_seconds()
                    pausa_inicio = None
        self.tiempo_total_segundos = int(total_activo)
        self.tiempo_pausado_segundos = int(total_pausado)
        self.save(update_fields=["tiempo_total_segundos", "tiempo_pausado_segundos"])

    def tiempo_formateado(self):
        return self._fmt(self.tiempo_efectivo())

    def tiempo_pausado_formateado(self):
        return self._fmt(self.tiempo_pausado())

    def _fmt(self, s):
        horas = int(s // 3600)
        minutos = int((s % 3600) // 60)
        segs = int(s % 60)
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"


class RegistroTiempo(models.Model):
    EVENTOS = [
        ("Inicio", "Inicio"),
        ("Pausa", "Pausa"),
        ("Reanudacion", "Reanudacion"),
        ("Finalizacion", "Finalizacion"),
        ("Traslado", "Traslado"),
    ]
    MOTIVOS_PAUSA = [
        ("", "Sin motivo"),
        ("Almuerzo", "Almuerzo / Descanso"),
        ("Interrupcion", "Interrupcion"),
        ("Cambio de prioridad", "Cambio de prioridad / Actividad programada"),
        ("Otro", "Otro"),
    ]
    asignacion = models.ForeignKey(AsignacionActividad, on_delete=models.PROTECT, related_name="registros")
    evento = models.CharField(max_length=20, choices=EVENTOS)
    motivo_pausa = models.CharField(max_length=50, blank=True, null=True, choices=MOTIVOS_PAUSA)
    fecha_hora = models.DateTimeField(default=timezone.now)
    comentario = models.TextField(blank=True, null=True)
    nro_actividad = models.CharField(max_length=50, blank=True, null=True, help_text="Nro secuencial manual de actividades realizadas")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "registro_tiempo"
        verbose_name = "Registro de Tiempo"
        verbose_name_plural = "Registros de Tiempo"

    def __str__(self):
        return f"{self.asignacion} - {self.evento}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.asignacion.recalcular_tiempo()


class TrasladoActividad(models.Model):
    ESTADOS_TRASLADO = [
        ("Pendiente", "Pendiente"),
        ("Aceptado", "Aceptado"),
        ("Cancelado", "Cancelado"),
        ("Rechazado", "Rechazado"),
    ]
    asignacion_origen = models.ForeignKey(
        AsignacionActividad, on_delete=models.PROTECT, related_name="traslados_origen"
    )
    asignacion_destino = models.ForeignKey(
        AsignacionActividad, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="traslados_destino"
    )
    user_origen = models.ForeignKey(User, on_delete=models.PROTECT, related_name="traslados_hechos")
    user_destino = models.ForeignKey(User, on_delete=models.PROTECT, related_name="traslados_recibidos")
    actividad_reemplazo = models.ForeignKey(Actividad, on_delete=models.PROTECT, null=True, blank=True, related_name="traslados_reemplazo")
    estado = models.CharField(max_length=20, choices=ESTADOS_TRASLADO, default="Pendiente")
    motivo = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "traslado_actividad"
        verbose_name = "Traslado de Actividad"
        verbose_name_plural = "Traslados de Actividad"
        constraints = [
            models.UniqueConstraint(
                fields=["asignacion_origen", "user_destino"],
                condition=models.Q(estado="Pendiente", activo=True),
                name="unique_traslado_pendiente"
            ),
        ]

    def __str__(self):
        return f"Traslado de {self.user_origen} a {self.user_destino}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.estado == "Pendiente" and self.asignacion_origen.estado not in ["Pendiente", "EnCurso", "Pausada"]:
            raise ValidationError(
                f"No se puede crear un traslado pendiente: la actividad origen esta '{self.asignacion_origen.get_estado_display()}'."
            )


class Colaboracion(models.Model):
    asignacion = models.ForeignKey(AsignacionActividad, on_delete=models.PROTECT, related_name="colaboraciones")
    user_colaborador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="colaboraciones")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "colaboracion"
        verbose_name = "Colaboracion"
        verbose_name_plural = "Colaboraciones"
        unique_together = ["asignacion", "user_colaborador"]

    def __str__(self):
        return f"{self.user_colaborador} colabora en {self.asignacion}"


class Comentario(models.Model):
    asignacion = models.ForeignKey(AsignacionActividad, on_delete=models.PROTECT, related_name="comentarios")
    detalle = models.ForeignKey("planificacion.PlanificacionDetalle", on_delete=models.SET_NULL, null=True, blank=True, related_name="comentarios")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="comentarios")
    texto = models.TextField()
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comentario"
        verbose_name = "Comentario"
        verbose_name_plural = "Comentarios"

    def __str__(self):
        return f"{self.user}: {self.texto[:50]}"


class TiempoInactividad(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="tiempos_inactividad")
    fecha = models.DateField(db_index=True)
    inicio = models.DateTimeField(null=True, blank=True)
    fin = models.DateTimeField(null=True, blank=True)
    duracion_segundos = models.IntegerField(default=0)
    motivo = models.CharField(max_length=100, default="Tiempo sin actividad")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tiempo_inactividad"
        verbose_name = "Tiempo de Inactividad"
        verbose_name_plural = "Tiempos de Inactividad"
        ordering = ["-fecha", "-inicio"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(fin__isnull=True) | models.Q(fin__gt=models.F("inicio")),
                name="fin_posterior_a_inicio"
            ),
        ]

    def __str__(self):
        from django.utils import timezone
        inicio_str = self.inicio.strftime("%H:%M") if self.inicio else "?"
        fin_str = self.fin.strftime("%H:%M") if self.fin else "?"
        mins = int(self.duracion_segundos // 60) if self.duracion_segundos > 0 else 0
        return f"{self.user.get_full_name()} - {self.fecha} {inicio_str}-{fin_str} ({mins}min)"


class RevisionHistorial(models.Model):
    ACCIONES = [("aprobado", "Aprobado"), ("rechazado", "Rechazado")]
    asignacion = models.ForeignKey(AsignacionActividad, on_delete=models.PROTECT, related_name="historial_revision")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="revisiones_hechas")
    accion = models.CharField(max_length=20, choices=ACCIONES)
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "revision_historial"
        verbose_name = "Historial de Revision"
        verbose_name_plural = "Historial de Revisiones"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_accion_display()} - {self.asignacion} por {self.user.get_full_name()}"

