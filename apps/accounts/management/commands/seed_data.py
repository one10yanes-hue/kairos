from django.core.management.base import BaseCommand
from datetime import date
from apps.accounts.models import Rol, User, Empresa, UserEmpresa
from apps.estructura.models import Area, SubArea, UserSubArea
from apps.actividades.models import TipoActividad


class Command(BaseCommand):
    help = "Crea datos iniciales: roles, usuarios, empresa, jerarquia, tipos"

    def handle(self, *args, **options):
        self.stdout.write("Creando datos iniciales...\n")

        # Roles
        for nombre, desc in [("Master", "Super administrador"), ("Admin", "Administrador de subarea"), ("Usuario", "Usuario operativo")]:
            r, c = Rol.objects.get_or_create(nombre=nombre, defaults={"descripcion": desc})
            self.stdout.write(f"  {'[CREADO]' if c else '[EXISTE]'} Rol: {r.nombre}")

        # Empresa
        emp, c = Empresa.objects.get_or_create(nit="900123456-7", defaults={
            "nombre": "VIVA1A SAS", "direccion": "Calle 123 #45-67", "telefono": "6011234567",
        })
        self.stdout.write(f"  {'[CREADO]' if c else '[EXISTE]'} Empresa: {emp.nombre}")

        # Areas y SubAreas
        areas_data = [
            ("Operaciones", [("Procesos", "Procesos operativos")]),
            ("Financiera", [("Contabilidad", "Gestion contable"), ("Tesoreria", "Gestion de tesoreria")]),
            ("Talento Humano", [("Nomina", "Gestion de nomina"), ("Seleccion", "Reclutamiento y seleccion")]),
        ]
        for area_name, subareas in areas_data:
            area, _ = Area.objects.get_or_create(empresa=emp, nombre=area_name)
            self.stdout.write(f"  {'[CREADO]' if _ else '[EXISTE]'} Area: {area.nombre}")
            for sub_name, sub_desc in subareas:
                sub, _ = SubArea.objects.get_or_create(area=area, nombre=sub_name, defaults={"descripcion": sub_desc})
                self.stdout.write(f"    {'[CREADO]' if _ else '[EXISTE]'} SubArea: {sub.nombre}")

        # Usuarios
        sub_contabilidad = SubArea.objects.get(nombre="Contabilidad")
        sub_tesoreria = SubArea.objects.get(nombre="Tesoreria")
        sub_procesos = SubArea.objects.get(nombre="Procesos")
        sub_nomina = SubArea.objects.get(nombre="Nomina")

        users_data = [
            ("1044432944", "Humberto", "Yanes", "2020-01-01",  "Master", True, "Super Administrador", sub_procesos),
            ("200", "Andrea", "Chavez", "2020-01-01", "Admin", False, "Contador Publico", sub_contabilidad),
            ("300", "Juan", "Perez", "2020-01-01", "Usuario", False, "Auxiliar Contable", sub_contabilidad),
            ("400", "Pedro", "Ramirez", "2020-01-01", "Usuario", False, "Auxiliar de Tesoreria", sub_tesoreria),
        ]

        for cedula, nombre, apellido, fexp, rol_nombre, is_super, cargo, subarea in users_data:
            rol = Rol.objects.get(nombre=rol_nombre)
            user, created = User.objects.get_or_create(
                cedula=cedula,
                defaults={
                    "fecha_expedicion": date(2020, 1, 1),
                    "nombre": nombre,
                    "apellido": apellido,
                    "cargo": cargo,
                    "email": f"{cedula}@viva1a.com",
                    "rol": rol,
                    "is_staff": True,
                    "is_superuser": is_super,
                },
            )
            if created:
                user.set_password("1234")
                user.save()
                UserEmpresa.objects.get_or_create(user=user, empresa=emp)
                UserSubArea.objects.get_or_create(user=user, subarea=subarea)
            self.stdout.write(f"  {'[CREADO]' if created else '[EXISTE]'} {cedula} {nombre} {apellido} [{rol_nombre}] cargo={cargo} -> {subarea.nombre}")

        # Tipos de Actividad en Contabilidad
        for subarea in [sub_contabilidad, sub_tesoreria, sub_procesos, sub_nomina]:
            for t_nombre, t_desc in [
                ("Programada", "Actividad planificada con fecha"),
                ("No Programada", "Actividad eventual o imprevista"),
                ("Mejora", "Actividad de mejora continua"),
                ("Procesos", "Actividad de proceso estandar"),
            ]:
                tipo, _ = TipoActividad.objects.get_or_create(subarea=subarea, nombre=t_nombre, defaults={"descripcion": t_desc})
                self.stdout.write(f"    {'[CREADO]' if _ else '[EXISTE]'} Tipo: {tipo.nombre} ({subarea.nombre})")

        self.stdout.write(self.style.SUCCESS("\n--- Datos iniciales creados ---"))
        self.stdout.write("Credenciales: cedula / 2020-01-01 (password interno: 1234)")
        self.stdout.write("  1044432944 Humberto Yanes  [Master]")
        self.stdout.write("  200        Andrea Chavez   [Admin]  - Contabilidad")
        self.stdout.write("  300        Juan Perez      [Usuario] - Contabilidad")
        self.stdout.write("  400        Pedro Ramirez   [Usuario] - Tesoreria")
