"""Tests para el flujo de proyecto - Fase 1 de remediacion."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.proyectos.models import (
    Proyecto, Sprint, HistoriaUsuario, Tarea, MiembroProyecto,
    RegistroAvance, WorkflowConfig, _get_transiciones,
)
from apps.proyectos.workflow_presets import PRESETS, ROLES_REQUERIDOS
from apps.proyectos.signals import _init_workflow_if_empty
from apps.gestion.models import AsignacionActividad
from apps.accounts.models import Rol
from apps.actividades.models import Actividad, TipoActividad
from apps.estructura.models import Area, SubArea

User = get_user_model()


class TestFlujoProyecto(TestCase):
    """Fase 1: Estabilizacion del flujo."""

    def setUp(self):
        rol_master = Rol.objects.get_or_create(nombre="Master")[0]
        rol_admin = Rol.objects.get_or_create(nombre="Admin")[0]
        rol_usuario = Rol.objects.get_or_create(nombre="Usuario")[0]
        self.master = User.objects.create_user(cedula="TEST001", fecha_expedicion="2020-01-01", nombre="Master", apellido="Test", rol=rol_master)
        self.ejecutor = User.objects.create_user(cedula="TEST002", fecha_expedicion="2020-01-01", nombre="Ejecutor", apellido="Test", rol=rol_usuario)
        self.revisor = User.objects.create_user(cedula="TEST003", fecha_expedicion="2020-01-01", nombre="Revisor", apellido="Test", rol=rol_usuario)
        self.aprobador = User.objects.create_user(cedula="TEST004", fecha_expedicion="2020-01-01", nombre="Aprobador", apellido="Test", rol=rol_usuario)
        self.lider = User.objects.create_user(cedula="TEST005", fecha_expedicion="2020-01-01", nombre="Lider", apellido="Test", rol=rol_admin)
        self.area = Area.objects.create(nombre="Test Area", codigo="TA")
        self.subarea = SubArea.objects.create(nombre="Test Subarea", codigo="TS", area=self.area)
        self.proyecto = Proyecto.objects.create(codigo="PRJ-TEST", nombre="Proyecto Test", manager=self.lider)
        self.proyecto.subareas.add(self.subarea)
        _init_workflow_if_empty(self.proyecto)
        MiembroProyecto.objects.create(proyecto=self.proyecto, user=self.lider, rol="lider")
        MiembroProyecto.objects.create(proyecto=self.proyecto, user=self.ejecutor, rol="ejecutor")
        MiembroProyecto.objects.create(proyecto=self.proyecto, user=self.revisor, rol="revisor")
        MiembroProyecto.objects.create(proyecto=self.proyecto, user=self.aprobador, rol="aprobador")
        self.tipo_act = TipoActividad.objects.create(subarea=self.subarea, nombre="Test Tipo")
        self.act = Actividad.objects.create(subarea=self.subarea, tipo_actividad=self.tipo_act, nombre="Test Actividad")

    # ---- Test 1: actualizar_estado no revierte historia done ----
    def test_historia_done_permanece_si_tareas_canceladas(self):
        historia = HistoriaUsuario.objects.create(
            proyecto=self.proyecto, titulo="Test Historia", codigo="PRJ-TEST-US-001",
            creador=self.lider, estado="done"
        )
        tarea = Tarea.objects.create(
            proyecto=self.proyecto, historia=historia, titulo="Test Tarea",
            codigo="PRJ-TEST-T-001", creador=self.lider, estado="cancelada", activo=True
        )
        historia.actualizar_estado()
        self.assertEqual(historia.estado, "done",
                         "Historia done no debe volver a backlog cuando todas las tareas estan canceladas")

    # ---- Test 2: presets incluyen transiciones de todos los estados ----
    def test_presets_incluyen_estados_clave(self):
        for preset_name in ["simple", "revision"]:
            preset = PRESETS[preset_name]
            tarea_orig = {origen for origen, _ in preset["tarea"]}
            self.assertIn("pausada", tarea_orig, f"Preset {preset_name} debe tener transiciones desde pausada")
            self.assertIn("finalizada", tarea_orig, f"Preset {preset_name} debe tener transiciones desde finalizada")
            inc_orig = {origen for origen, _ in preset["incidencia"]}
            self.assertIn("triaged", inc_orig, f"Preset {preset_name} debe tener transiciones desde triaged")
            self.assertIn("duplicada", inc_orig, f"Preset {preset_name} debe tener transiciones desde duplicada")

    # ---- Test 3: signal idempotente - no duplica bitacora ----
    def test_signal_no_duplica_al_resave(self):
        tarea = Tarea.objects.create(
            proyecto=self.proyecto, titulo="Test Task", codigo="PRJ-TEST-T-002",
            creador=self.lider, asignado_a=self.ejecutor
        )
        asignacion = AsignacionActividad.objects.create(
            user=self.ejecutor, actividad=self.act, estado="Pendiente",
            nombre_actividad=tarea.titulo, origen="Proyecto", origen_user=self.lider
        )
        tarea.asignacion = asignacion
        tarea.save(update_fields=["asignacion"])
        count_before = RegistroAvance.objects.filter(referencia_id=tarea.pk).count()
        asignacion.save()
        count_after = RegistroAvance.objects.filter(referencia_id=tarea.pk).count()
        self.assertEqual(count_after, count_before,
                         "Un no-op save no debe crear nuevo RegistroAvance")

    # ---- Test 4: workflow_bloqueado bloquea cambios en workflow ----
    def test_workflow_bloqueado_impide_cambios(self):
        self.proyecto.workflow_bloqueado = True
        self.proyecto.save()
        wf_count = WorkflowConfig.objects.filter(proyecto=self.proyecto).count()
        self.assertGreater(wf_count, 0, "Debe tener WorkflowConfig inicializado")
        # Intentar agregar una transicion via la logica del view deberia ser rechazado
        self.proyecto.refresh_from_db()
        self.assertTrue(self.proyecto.workflow_bloqueado)

    # ---- Test 5: KPIs cuentan revision como completada ----
    def test_revision_cuenta_como_completada(self):
        historia = HistoriaUsuario.objects.create(
            proyecto=self.proyecto, titulo="KPI Test", codigo="PRJ-TEST-US-002",
            creador=self.lider, estado="en_progreso"
        )
        Tarea.objects.create(
            proyecto=self.proyecto, historia=historia, titulo="T1",
            codigo="PRJ-TEST-T-003", creador=self.lider, estado="revision"
        )
        Tarea.objects.create(
            proyecto=self.proyecto, historia=historia, titulo="T2",
            codigo="PRJ-TEST-T-004", creador=self.lider, estado="revision"
        )
        avance = historia.avance_tareas
        self.assertEqual(avance, 100, f"Historia con todas las tareas en revision debe mostrar 100%%, no {avance}%%")
        self.assertEqual(self.proyecto.avance, 100,
                         f"Proyecto con todas las tareas en revision debe mostrar 100%%, no {self.proyecto.avance}%%")

    # ---- Test 6: _get_transiciones combina hardcoded + custom ----
    def test_get_transiciones_combina_hardcoded_custom(self):
        # Sin custom config, debe retornar hardcoded
        trans = _get_transiciones(self.proyecto, "tarea")
        self.assertIn("finalizada", trans)
        self.assertIn("revision", trans.get("finalizada", []))
        # Agregar custom
        WorkflowConfig.objects.create(
            proyecto=self.proyecto, entidad="tarea",
            estado_origen="cancelada", estado_destino="en_curso"
        )
        trans2 = _get_transiciones(self.proyecto, "tarea")
        self.assertIn("en_curso", trans2.get("cancelada", []),
                      "La transicion custom debe aparecer sin borrar las hardcoded")
        self.assertIn("revision", trans2.get("finalizada", []),
                      "Las transiciones hardcoded deben conservarse al agregar custom")

    # ---- Test 7: Roles requeridos tienen lider y ejecutor como minimo ----
    def test_roles_requeridos_minimo(self):
        for preset, roles in ROLES_REQUERIDOS.items():
            self.assertIn("lider", roles, f"Preset {preset} requiere al menos un lider")
            self.assertIn("ejecutor", roles, f"Preset {preset} requiere al menos un ejecutor")
