from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.template import Context
from apps.accounts.models import User, Rol
from apps.estructura.models import Area, SubArea
from apps.proyectos.models import Proyecto, RegistroAvance, Sprint, Tarea, Incidencia, HistoriaUsuario

# Monkey-patch para Python 3.14 / Django 5.0.x: Context.__copy__ falla con super()
if not hasattr(Context, '_patched'):
    _original_copy = Context.__copy__
    def _patched_copy(self):
        cls = Context
        duplicate = cls.__new__(cls)
        duplicate.dicts = [d.copy() for d in self.dicts]
        duplicate._masks = getattr(self, '_masks', None)
        return duplicate
    Context.__copy__ = _patched_copy
    Context._patched = True


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class ProyectoEditTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.rol_master = Rol.objects.create(nombre="Master")
        self.rol_admin = Rol.objects.create(nombre="Admin")
        self.master = User.objects.create_user(
            cedula="99999", fecha_expedicion="2020-01-01",
            nombre="Master", apellido="Test", rol=self.rol_master
        )
        self.admin = User.objects.create_user(
            cedula="88888", fecha_expedicion="2020-01-01",
            nombre="Admin", apellido="Test", rol=self.rol_admin
        )
        self.area = Area.objects.create(codigo="TECH", nombre="Tecnologia")
        self.sub1 = SubArea.objects.create(codigo="DEV", nombre="Desarrollo", area=self.area)
        self.sub2 = SubArea.objects.create(codigo="QA", nombre="QA", area=self.area)
        self.proyecto = Proyecto.objects.create(
            codigo="PROJ0001", nombre="Proyecto Test",
            manager=self.master, estado="activo"
        )
        self.proyecto.subareas.add(self.sub1, self.sub2)
        # Create dependent data for cascade tests
        self.sprint = Sprint.objects.create(
            proyecto=self.proyecto, nombre="Sprint 1", numero=1, estado="activo"
        )
        self.historia = HistoriaUsuario.objects.create(
            proyecto=self.proyecto, sprint=self.sprint,
            codigo="PROJ0001-H01", titulo="Historia 1", creador=self.master,
            estado="en_progreso"
        )
        self.tarea = Tarea.objects.create(
            proyecto=self.proyecto, codigo="PROJ0001-T01", titulo="Tarea 1",
            creador=self.master, estado="en_curso"
        )
        self.incidencia = Incidencia.objects.create(
            proyecto=self.proyecto, codigo="PROJ0001-I01", titulo="Bug 1",
            reportado_por=self.master, estado="abierta"
        )

    def _login(self, user):
        self.client.force_login(user)

    def test_edit_preserves_original_subareas(self):
        """Al editar, no se pueden quitar subareas asignadas inicialmente."""
        self._login(self.master)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "activo", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk)]},  # intenta quitar sub2
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        msgs = [m.message for m in resp.context.get("messages", [])]
        self.assertTrue(any("No puedes quitar" in m for m in msgs),
                        f"Expected subarea removal error, got: {msgs}")
        self.assertIn(self.sub2, self.proyecto.subareas.all())

    def test_edit_allows_adding_new_subareas(self):
        """Se pueden anadir subareas nuevas sin problema."""
        self._login(self.master)
        sub3 = SubArea.objects.create(codigo="OPS", nombre="Operaciones", area=self.area)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "activo", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk), str(sub3.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        msgs = [m.message for m in resp.context.get("messages", [])]
        self.assertTrue(any("actualizado" in m.lower() for m in msgs),
                        f"Expected success, got: {msgs}")
        self.proyecto.refresh_from_db()
        self.assertIn(sub3, self.proyecto.subareas.all())

    def test_edit_audit_fecha_fin_change(self):
        """Cambiar fecha fin estimada genera RegistroAvance."""
        self._login(self.master)
        self.assertIsNone(self.proyecto.fecha_fin_estimada)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "activo", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)],
             "fecha_fin_estimada": "2026-12-31"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.proyecto.refresh_from_db()
        self.assertEqual(str(self.proyecto.fecha_fin_estimada), "2026-12-31")
        qs = RegistroAvance.objects.filter(
            proyecto=self.proyecto, descripcion__icontains="Fecha fin estimada"
        )
        self.assertTrue(qs.exists(), "No se encontro registro de auditoria de fecha fin")

    def test_edit_audit_estado_change(self):
        """Cambiar estado genera RegistroAvance con el cambio."""
        self._login(self.master)
        self.assertEqual(self.proyecto.estado, "activo")
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "pausado", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        qs = RegistroAvance.objects.filter(
            proyecto=self.proyecto, descripcion__icontains="Estado cambiado"
        )
        self.assertTrue(qs.exists(), "No se encontro registro de auditoria de cambio de estado")

    def test_cancel_cascade_sprints(self):
        """Cancelar proyecto -> sprints activos pasan a cancelado."""
        self._login(self.master)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "cancelado", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.estado, "cancelado")

    def test_cancel_cascade_tareas(self):
        """Cancelar proyecto -> tareas no finalizadas/canceladas pasan a cancelada."""
        self._login(self.master)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "cancelado", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.tarea.refresh_from_db()
        self.assertEqual(self.tarea.estado, "cancelada")
        self.assertFalse(self.tarea.activo)

    def test_cancel_cascade_incidencias(self):
        """Cancelar proyecto -> incidencias abiertas pasan a cerrada."""
        self._login(self.master)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "cancelado", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.incidencia.refresh_from_db()
        self.assertEqual(self.incidencia.estado, "cerrada")
        self.assertFalse(self.incidencia.activo)

    def test_cancel_cascade_historias(self):
        """Cancelar proyecto -> historias no done pasan a activo=False."""
        self._login(self.master)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "cancelado", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.historia.refresh_from_db()
        self.assertFalse(self.historia.activo)

    def test_pause_cascade_sprints(self):
        """Pausar proyecto -> sprints activos pasan a planificado."""
        self._login(self.master)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "pausado", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.estado, "planificado")

    def test_resume_from_pause(self):
        """Reanudar de pausado -> sprints mantienen estado, solo se registra en auditoria."""
        self.proyecto.estado = "pausado"
        self.proyecto.save()
        qs_before = RegistroAvance.objects.filter(descripcion__icontains="reanudado").count()
        self._login(self.master)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "activo", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        qs_after = RegistroAvance.objects.filter(descripcion__icontains="reanudado").count()
        self.assertGreater(qs_after, qs_before, "No se encontro registro de reanudacion")
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado, "activo")

    def test_edit_rejects_invalid_dates(self):
        """Fecha inicio > fecha fin debe ser rechazada."""
        self._login(self.master)
        resp = self.client.post(
            reverse("proyectos:proyecto_edit", args=[self.proyecto.pk]),
            {"nombre": "Proyecto Test", "estado": "activo", "manager": self.master.pk,
             "subareas": [str(self.sub1.pk), str(self.sub2.pk)],
             "fecha_inicio": "2026-12-31", "fecha_fin_estimada": "2026-01-01"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        msgs = [m.message for m in resp.context.get("messages", [])]
        self.assertTrue(any("no puede ser posterior" in m.lower() for m in msgs),
                        f"Expected date validation error, got: {msgs}")
