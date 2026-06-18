from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea un proyecto limpio 'Practica' para aprender el flujo desde cero"

    def handle(self, *args, **options):
        from apps.proyectos.models import Proyecto
        from apps.accounts.models import User
        from datetime import date

        if Proyecto.objects.filter(codigo="PRAC-001").exists():
            self.stdout.write("Ya existe PRAC-001. Se salta creacion.")
            return

        lider = User.objects.get(pk=1)
        proyecto = Proyecto.objects.create(
            codigo="PRAC-001",
            nombre="Proyecto de Practica",
            descripcion="Proyecto vacio para practicar el flujo completo",
            manager=lider,
            fecha_inicio=date.today(),
        )
        self.stdout.write(self.style.SUCCESS(
            f"\nCreado PRAC-001 (Proyecto de Practica) - http://127.0.0.1:8000/proyectos/{proyecto.pk}/\n"
        ))
        self.stdout.write("Ahora ve al proyecto y practica:\n")
        self.stdout.write("1. Ir a 'Equipo' -> agregar miembros con distintos roles")
        self.stdout.write("2. Ir a 'Backlog' -> crear Historias")
        self.stdout.write("3. Ir a 'Sprints' -> 'Nuevo Sprint' -> seleccionar historias")
        self.stdout.write("4. Ir al 'Board' del sprint -> '+ Tarea' para crear tareas")
        self.stdout.write("5. Iniciar el Sprint -> las tareas aparecen en tableros Kanban")
        self.stdout.write("6. En el tablero Kanban (productividad), mover tareas entre columnas")
        self.stdout.write("7. Volver al Sprint Board -> drag & drop entre columnas")
        self.stdout.write("8. Finalizar Sprint")
