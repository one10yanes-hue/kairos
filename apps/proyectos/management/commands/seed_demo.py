from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Pobla datos de ejemplo en PRJ-0007 para aprender el flujo"

    def handle(self, *args, **options):
        from apps.proyectos.models import Proyecto, MiembroProyecto, HistoriaUsuario, Sprint, Tarea, RegistroAvance, Incidencia
        from apps.accounts.models import User

        proyecto = Proyecto.objects.get(codigo="PRJ-0007")
        hoy = timezone.now().date()

        self.stdout.write("Limpiando datos existentes de PRJ-0007...")
        Tarea.objects.filter(proyecto=proyecto).delete()
        Incidencia.objects.filter(proyecto=proyecto).delete()
        RegistroAvance.objects.filter(proyecto=proyecto).delete()
        HistoriaUsuario.objects.filter(proyecto=proyecto).delete()
        Sprint.objects.filter(proyecto=proyecto).delete()
        MiembroProyecto.objects.filter(proyecto=proyecto).delete()
        self.stdout.write("  OK")

        # IDs de usuarios
        lider = User.objects.get(pk=1)          # HUMBERTO YANES ZARATE
        ejecutor1 = User.objects.get(pk=4)      # JERSON HERRERA CERVANTES
        ejecutor2 = User.objects.get(pk=5)      # OLGA LUCIA BENAVIDES JIMENEZ
        revisor = User.objects.get(pk=3)        # CYNTHIA LORAINE SANDOVAL MENDOZA
        aprobador = User.objects.get(pk=2)      # ANGIE PATRICIA OROZCO DE LA HOZ

        # 1. Miembros (update_or_create para reactivar si existian)
        miembros_data = [
            (lider, "lider"),
            (ejecutor1, "ejecutor"),
            (ejecutor2, "ejecutor"),
            (revisor, "revisor"),
            (aprobador, "aprobador"),
        ]
        for user, rol in miembros_data:
            m, _ = MiembroProyecto.objects.update_or_create(
                proyecto=proyecto, user=user,
                defaults={"rol": rol, "activo": True},
            )
            self.stdout.write(f"  Miembro: {user.get_full_name()} -> {rol}")

        # 2. Historias en backlog
        historias_data = [
            ("Registro de usuarios", "Como admin quiero registrar usuarios con email y contraseña", "must", 5),
            ("Inicio de sesion", "Como usuario quiero iniciar sesion con mis credenciales", "must", 3),
            ("Recuperar contraseña", "Como usuario quiero recuperar mi contraseña por email", "should", 2),
            ("Dashboard de reportes", "Como admin quiero ver graficos de actividad semanal", "could", 8),
            ("Exportar datos a Excel", "Como usuario quiero exportar mi lista a Excel", "should", 3),
        ]
        historias_creadas = []
        for titulo, desc, prioridad, pts in historias_data:
            h = HistoriaUsuario.objects.create(
                proyecto=proyecto,
                titulo=titulo,
                descripcion=desc,
                prioridad=prioridad,
                puntos_historia=pts,
                creador=lider,
                orden=len(historias_creadas),
            )
            h.codigo = f"{proyecto.codigo}-US-{h.pk:03d}"
            h.save()
            historias_creadas.append(h)
            self.stdout.write(f"  Historia: {h.codigo} - {titulo} ({pts} pts)")

        # 3. Sprint con las primeras 3 historias
        sprint = Sprint.objects.create(
            proyecto=proyecto,
            nombre="Sprint Inicial",
            objetivo="Implementar autenticacion y modulo base",
            numero=1,
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=14),
        )
        for h in historias_creadas[:3]:
            h.sprint = sprint
            h.estado = "sprint_backlog"
            h.save()
        self.stdout.write(f"  Sprint: {sprint.numero} - {sprint.nombre}")

        # 4. Tareas para cada historia del sprint
        tareas_data = [
            (historias_creadas[0], "Crear modelo User con campos email/password", ejecutor1),
            (historias_creadas[0], "Implementar vista de registro con formulario", ejecutor2),
            (historias_creadas[0], "Agregar validacion de email unico", ejecutor1),
            (historias_creadas[1], "Crear template de login", ejecutor2),
            (historias_creadas[1], "Implementar autenticacion por JWT", ejecutor1),
            (historias_creadas[2], "Enviar email de recuperacion", ejecutor2),
            (historias_creadas[2], "Crear formulario de cambio de contraseña", ejecutor1),
        ]
        for historia, titulo, asignado in tareas_data:
            t = Tarea.objects.create(
                proyecto=proyecto,
                historia=historia,
                sprint=sprint,
                titulo=titulo,
                tipo="tarea",
                asignado_a=asignado,
                creador=lider,
            )
            t.codigo = f"{proyecto.codigo}-T-{t.pk:03d}"
            t.save()
            self.stdout.write(f"  Tarea: {t.codigo} - {titulo} -> {asignado.get_full_name()}")

        # 5. Tarea standalone (sin historia)
        t_standalone = Tarea.objects.create(
            proyecto=proyecto,
            sprint=sprint,
            titulo="Configurar ambiente de desarrollo",
            tipo="tarea",
            asignado_a=ejecutor1,
            creador=lider,
        )
        t_standalone.codigo = f"{proyecto.codigo}-T-{t_standalone.pk:03d}"
        t_standalone.save()
        self.stdout.write(f"  Tarea standalone: {t_standalone.codigo}")

        # 6. Bitácora
        RegistroAvance.objects.create(
            proyecto=proyecto, tipo="comentario",
            descripcion="Proyecto inicializado con datos de ejemplo",
            user=lider,
        )

        self.stdout.write(self.style.SUCCESS(f"\nDatos creados en {proyecto.codigo} ({proyecto.nombre})"))
        self.stdout.write(self.style.SUCCESS("Abre http://127.0.0.1:8000/proyectos/7/ para explorar"))
