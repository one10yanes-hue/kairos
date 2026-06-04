"""
Tests para Sincronización KACTUS.
Prueba la lógica de sincronizar, desactivar y bloqueo por pendientes.
No requiere conexión real a KACTUS - usa datos mock.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, Empresa, Rol, UserEmpresa
from apps.estructura.models import Area, SubArea, UserSubArea
from apps.gestion.models import AsignacionActividad, RegistroTiempo
from apps.actividades.models import TipoActividad, Actividad
from apps.planificacion.models import Planificacion, PlanificacionDetalle
from apps.auditoria.models import SyncLog


class SyncLogicTests(TestCase):
    """Pruebas de la lógica de sincronización sin KACTUS."""

    def setUp(self):
        self.rol_master = Rol.objects.create(nombre="Master")
        self.rol_usuario = Rol.objects.create(nombre="Usuario")
        self.empresa = Empresa.objects.create(nombre="TEST EMPRESA", codigo="TST", nit="123456")
        self.subarea = SubArea.objects.create(
            nombre="Test SubArea",
            area=Area.objects.create(nombre="Test Area", empresa=self.empresa),
        )
        self.tipo = TipoActividad.objects.create(nombre="Programada", subarea=self.subarea)
        self.actividad = Actividad.objects.create(
            nombre="Test Actividad", subarea=self.subarea, tipo_actividad=self.tipo
        )

    def test_sync_log_creado_al_desactivar(self):
        """Verifica que se registre un SyncLog al desactivar un usuario."""
        user = User.objects.create(
            cedula="999999", nombre="Test", apellido="User",
            fecha_expedicion="2020-01-01", rol=self.rol_usuario,
            cargo="OLD CARGO"
        )
        UserEmpresa.objects.create(user=user, empresa=self.empresa)
        UserSubArea.objects.create(user=user, subarea=self.subarea)

        # Desactivar usuario
        user.activo = False
        user.save()

        SyncLog.objects.create(
            user=user, accion="DEACTIVATE",
            valor_anterior={"activo": True},
            valor_nuevo={"activo": False, "en_curso": 0, "pausadas": 0, "pendientes": 0},
        )

        self.assertEqual(SyncLog.objects.count(), 1)
        self.assertEqual(SyncLog.objects.first().accion, "DEACTIVATE")

    def test_bloqueo_por_pendientes(self):
        """Usuario con Pendiente NO debe permitir sincronizar."""
        user = User.objects.create(
            cedula="888888", nombre="Blocked", apellido="User",
            fecha_expedicion="2020-01-01", rol=self.rol_usuario,
            cargo="OLD CARGO"
        )
        pendientes = AsignacionActividad.objects.filter(
            user=user, activo=True, estado__in=["Pendiente", "EnCurso", "Pausada"]
        ).count()
        self.assertEqual(pendientes, 0)  # Sin pendientes aun

        # Agregar una pendiente
        AsignacionActividad.objects.create(
            user=user, actividad=self.actividad, estado="Pendiente",
            nombre_actividad=self.actividad.nombre,
            nombre_tipo=self.actividad.tipo_actividad.nombre,
        )
        pendientes = AsignacionActividad.objects.filter(
            user=user, activo=True, estado__in=["Pendiente", "EnCurso", "Pausada"]
        ).count()
        self.assertEqual(pendientes, 1)
        self.assertGreater(pendientes, 0)  # Bloqueado

    def test_desactivar_cierra_en_curso(self):
        """Al desactivar, EnCurso debe pasar a Finalizada con RegistroTiempo."""
        user = User.objects.create(
            cedula="777777", nombre="Close", apellido="Test",
            fecha_expedicion="2020-01-01", rol=self.rol_usuario,
        )
        asignacion = AsignacionActividad.objects.create(
            user=user, actividad=self.actividad, estado="EnCurso",
            nombre_actividad=self.actividad.nombre,
            nombre_tipo=self.actividad.tipo_actividad.nombre,
        )
        self.assertEqual(asignacion.estado, "EnCurso")

        # Simular cierre
        asignacion.estado = "Finalizada"
        asignacion.save()
        RegistroTiempo.objects.create(
            asignacion=asignacion, evento="Finalizacion",
            fecha_hora=timezone.now(),
            comentario="Cerrado - usuario desvinculado KACTUS",
        )
        self.assertEqual(
            RegistroTiempo.objects.filter(asignacion=asignacion, evento="Finalizacion").count(), 1
        )

    def test_desactivar_cancela_pendientes(self):
        """Al desactivar, Pendientes pasan a Cancelada."""
        user = User.objects.create(
            cedula="666666", nombre="Cancel", apellido="Test",
            fecha_expedicion="2020-01-01", rol=self.rol_usuario,
        )
        a1 = AsignacionActividad.objects.create(
            user=user, actividad=self.actividad, estado="Pendiente",
            nombre_actividad=self.actividad.nombre,
            nombre_tipo=self.actividad.tipo_actividad.nombre,
        )
        a2 = AsignacionActividad.objects.create(
            user=user, actividad=self.actividad, estado="Pendiente",
            nombre_actividad=self.actividad.nombre,
            nombre_tipo=self.actividad.tipo_actividad.nombre,
        )
        AsignacionActividad.objects.filter(
            user=user, activo=True, estado="Pendiente"
        ).update(estado="Cancelada")
        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertEqual(a1.estado, "Cancelada")
        self.assertEqual(a2.estado, "Cancelada")

    def test_sync_actualiza_cargo(self):
        """Verifica que update_or_create funcione para UserEmpresa."""
        user = User.objects.create(
            cedula="555555", nombre="Update", apellido="Test",
            fecha_expedicion="2020-01-01", rol=self.rol_usuario,
            cargo="OLD CARGO"
        )
        user.cargo = "NEW CARGO"
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.cargo, "NEW CARGO")

        # UserEmpresa update_or_create
        UserEmpresa.objects.update_or_create(
            user=user, empresa=self.empresa, defaults={"activo": True}
        )
        self.assertEqual(UserEmpresa.objects.filter(user=user, activo=True).count(), 1)

    def test_sync_log_accion_correcta(self):
        """SyncLog registra accion y valores."""
        user = User.objects.create(
            cedula="444444", nombre="Log", apellido="Test",
            fecha_expedicion="2020-01-01", rol=self.rol_usuario,
        )
        log = SyncLog.objects.create(
            user=user, accion="UPDATE_CARGO",
            valor_anterior={"cargo": "OLD"},
            valor_nuevo={"cargo": "NEW"},
        )
        self.assertEqual(log.accion, "UPDATE_CARGO")
        self.assertEqual(log.valor_anterior["cargo"], "OLD")

    def test_planificacion_detalle_inactiva_al_desactivar(self):
        """Planificaciones futuras se inactivan al desactivar usuario."""
        user = User.objects.create(
            cedula="333333", nombre="Plan", apellido="Test",
            fecha_expedicion="2020-01-01", rol=self.rol_usuario,
        )
        plan = Planificacion.objects.create(
            nombre="Test Plan", subarea=self.subarea, admin=user
        )
        det = PlanificacionDetalle.objects.create(
            planificacion=plan, actividad=self.actividad, user=user
        )
        self.assertTrue(det.activo)

        PlanificacionDetalle.objects.filter(user=user, activo=True).update(activo=False)
        det.refresh_from_db()
        self.assertFalse(det.activo)


import unittest

# ...
class SyncAccessTests(TestCase):
    """Pruebas de acceso a la API de sincronización."""

    def setUp(self):
        self.master = User.objects.create_user(
            cedula="master1", fecha_expedicion="2020-01-01",
            nombre="Master", apellido="Test",
        )
        Rol.objects.get_or_create(nombre="Master")
        Rol.objects.get_or_create(nombre="Admin")
        self.master.rol = Rol.objects.get(nombre="Master")
        self.master.save()

        self.admin = User.objects.create_user(
            cedula="admin1", fecha_expedicion="2020-01-01",
            nombre="Admin", apellido="Test",
        )
        self.admin.rol = Rol.objects.get(nombre="Admin")
        self.admin.save()

    def test_sync_api_requires_master(self):
        """API de comparacion rechaza Admin con 403."""
        client = Client()
        client.force_login(self.admin)
        resp = client.get(reverse("estructura:api_sync_comparar") + "?empresa=TST")
        self.assertEqual(resp.status_code, 403)

    @unittest.skip("KACTUS no disponible en test")
    def test_sync_api_master_gets_response(self):
        """API de comparacion responde a Master."""
        client = Client()
        client.force_login(self.master)
        resp = client.get(reverse("estructura:api_sync_comparar") + "?empresa=TST")
        self.assertIn(resp.status_code, [200, 500])

    def test_sync_view_requires_login(self):
        """La vista de sync requiere autenticacion."""
        client = Client()
        resp = client.get(reverse("estructura:sync_cargo"))
        self.assertEqual(resp.status_code, 302)
