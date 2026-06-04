# VIVA1A - Sincronización KACTUS por Cargo

**Autor:** Plan de arquitectura e implementación
**Fecha:** 27/05/2026
**Versión:** 1.0

---

## 1. Objetivo

Sincronizar cambios de cargo, empresa y desvinculación de empleados entre KACTUS (MSSQL) y la BD local (SQLite), bajo las siguientes reglas de negocio:

| Regla | Comportamiento |
|---|---|
| 🔒 **BLOQUEO por pendientes** | Si el usuario local tiene ≥1 `Pendiente`/`EnCurso`/`Pausada` → NO se puede sincronizar cambio de cargo |
| 📝 **Histórico preservado** | `AsignacionActividad` y `RegistroTiempo` permanecen intactos |
| 🔄 **Cambio de cargo** | `user.cargo` = KACTUS `ca.nom_carg`; se agrega `UserEmpresa` y `UserSubArea` nueva si corresponde |
| 🚫 **Subarea vieja** | NO se inactiva automáticamente → el admin decide manualmente vía Gestionar Usuarios |
| ❌ **Desvinculado** | Finaliza EnCurso + Pausadas, Cancela Pendientes, Inactiva planificaciones, `User.activo=False` |
| 📊 **Visibilidad** | El admin de la nueva subarea ve al usuario en su dashboard/planificación |
| 📋 **Sync log** | Cada acción de sincronización queda registrada para auditoría |
| 🔑 **Rol** | Solo accesible por **Master** (no Admin) |

---

## 2. Arquitectura

### 2.1 Estructura de archivos

```
apps/estructura/
├── integracion_views.py       ← + sync_cargo, api_sync_comparar, api_sync_ejecutar
├── models.py                  ← no cambia (SyncLog va en auditoria)
└── urls.py                    ← + 3 rutas

apps/auditoria/
└── models.py                  ← + SyncLog

templates/estructura/
└── integracion_sync.html      ← NUEVO: template de sincronización

templates/partials/
└── sidebar_menu.html          ← + "Sincronizar por Cargo" (solo rol Master)
```

### 2.2 Flujo de la pantalla

```
GET  /master/integracion/sync/
  │
  ├─ Paso 1: Select Empresa (KACTUS homologada) + Buscar Cargo (dynamic select)
  │
  ├─ Seleccionado cargo → AJAX GET /master/integracion/api/sync/comparar/?empresa=X&cargo=Y
  │     │
  │     └─ Responde JSON con 4 categorías:
  │         ├─ "nuevos"      → empleados KACTUS sin User local
  │         ├─ "cambios"      → existen pero cargo/empresa difiere
  │         ├─ "sin_cambios"  → ya sincronizados
  │         └─ "desvinculados"→ en local con este cargo pero NO en KACTUS activo
  │
  ├─ Tabla renderizada con botones de acción por fila
  │
  └─ Acciones disponibles:
      ├─ [Habilitar]     → POST /master/integracion/api/sync/ejecutar/ (accion=crear)
      ├─ [Sincronizar]   → POST ... (accion=sincronizar) solo si pendientes=0
      └─ [Desactivar]    → POST ... (accion=desactivar) cierra todo y desactiva
```

### 2.3 Endpoints API

| Método | URL | Descripción |
|---|---|---|
| GET | `/master/integracion/api/sync/comparar/` | Compara KACTUS vs Local para empresa+cargo |
| POST | `/master/integracion/api/sync/ejecutar/` | Ejecuta acción (crear/sincronizar/desactivar) por lote o individual |

---

## 3. Modelo de Datos

### 3.1 SyncLog (NUEVO)

```python
class SyncLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="syncs")
    accion = models.CharField(max_length=30)  
    # Valores: 'CREATE', 'UPDATE_CARGO', 'UPDATE_EMPRESA', 'DEACTIVATE'
    valor_anterior = models.JSONField(default=dict)
    valor_nuevo = models.JSONField(default=dict)
    ejecutado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                       related_name="syncs_ejecutados")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sync_log"
        ordering = ["-fecha"]
```

### 3.2 Tablas existentes utilizadas

| Tabla | Uso en sincronización |
|---|---|
| `usuario` | Leer/actualizar `cargo`, `activo` |
| `user_empresa` | `update_or_create` con `activo=True` para empresa nueva |
| `user_subarea` | `get_or_create` para subarea nueva |
| `asignacion_actividad` | Leer pendientes, cerrar al desactivar |
| `planificacion_detalle` | Inactivar al desactivar |
| `registro_tiempo` | Crear `Finalizacion` al cerrar EnCurso/Pausada |
| `empresa` | Buscar por `codigo` = KACTUS `cod_empr` |
| `area`, `subarea` | Buscar/crear según KACTUS |

---

## 4. Lógica de Comparación

```python
def comparar_por_cargo(empresa_kactus: str, cargo_kactus: str) -> dict:
    """
    Retorna:
    {
        "nuevos": [...],
        "cambios": [{"cedula", "nombre", "cambios": [...], "pendientes": 0, "bloqueado": true|false}],
        "sin_cambios": [...],
        "desvinculados": [...]
    }
    """
    
    # 1. Query KACTUS: empleados activos en ese cargo+empresa
    kactus_emps = query_kactus_empleados(empresa_kactus, cargo_kactus)
    
    # 2. Query local: usuarios con ese cargo guardado
    cedulas_kactus = {e["cod_empl"] for e in kactus_emps}
    locales = User.objects.filter(activo=True)
    
    resultado = {"nuevos": [], "cambios": [], "sin_cambios": [], "desvinculados": []}
    emp_local = Empresa.objects.filter(codigo=empresa_kactus, activo=True).first()
    
    for kemp in kactus_emps:
        ced = kemp["cod_empl"]
        local = locales.filter(cedula=ced).first()
        
        if not local:
            resultado["nuevos"].append(kemp)
            continue
        
        # Verificar cambios
        cambios = []
        if local.cargo != kemp["cargo"]:
            cambios.append(f"Cargo: {local.cargo or '-'} → {kemp['cargo']}")
        
        if emp_local:
            tiene = UserEmpresa.objects.filter(user=local, empresa=emp_local, activo=True).exists()
            if not tiene:
                cambios.append(f"Empresa: +{emp_local.nombre}")
        
        if cambios:
            pendientes = AsignacionActividad.objects.filter(
                user=local, activo=True, estado__in=["Pendiente", "EnCurso", "Pausada"]
            ).count()
            resultado["cambios"].append({
                "cedula": ced,
                "nombre": kemp["nom_empl"],
                "apellido": kemp["ape_empl"],
                "cambios": cambios,
                "pendientes": pendientes,
                "bloqueado": pendientes > 0,
            })
        else:
            resultado["sin_cambios"].append({
                "cedula": ced, "nombre": kemp["nom_empl"], "apellido": kemp["ape_empl"]
            })
    
    # 3. Desvinculados: locales con este cargo pero no en KACTUS activo
    for user in locales.filter(cargo=kactus_cargo_nombre):
        if user.cedula not in cedulas_kactus:
            resultado["desvinculados"].append({
                "cedula": user.cedula, "nombre": user.nombre, "apellido": user.apellido,
                "cargo": user.cargo
            })
    
    return resultado
```

---

## 5. Acciones de Sincronización

### 5.1 CREAR (Habilitar nuevo)

Mismo flujo que "Habilitaciones por Cargo":
- Crea `User` con datos de KACTUS
- Crea `UserEmpresa`
- Crea `UserSubArea` (necesita subarea_id vía POST)
- Registra en `SyncLog`

### 5.2 SINCRONIZAR (actualizar cargo/empresa)

```python
@transaction.atomic
def ejecutar_sincronizar(user, kactus_data, admin_user):
    """
    PRECONDICIÓN: user no tiene Pendiente/EnCurso/Pausada.
    """
    cargo_anterior = user.cargo
    empresas_anteriores = list(UserEmpresa.objects.filter(
        user=user, activo=True
    ).values_list("empresa__nombre", flat=True))
    
    # 1. Actualizar cargo
    user.cargo = kactus_data["cargo"]
    user.save()
    
    # 2. Empresa (reactivar o crear)
    emp_local = Empresa.objects.filter(
        codigo=kactus_data["cod_empr"], activo=True
    ).first()
    if emp_local:
        UserEmpresa.objects.update_or_create(
            user=user, empresa=emp_local,
            defaults={"activo": True}
        )
    
    # 3. SyncLog
    SyncLog.objects.create(
        user=user,
        accion="UPDATE_CARGO",
        valor_anterior={"cargo": cargo_anterior, "empresas": empresas_anteriores},
        valor_nuevo={"cargo": kactus_data["cargo"]},
        ejecutado_por=admin_user,
    )
```

### 5.3 DESACTIVAR (usuario desvinculado)

```python
@transaction.atomic
def ejecutar_desactivar(user, admin_user):
    """
    Cierra todas las actividades abiertas y desactiva al usuario.
    """
    stats = {"en_curso": 0, "pausadas": 0, "pendientes": 0}
    
    # 1. Finalizar EnCurso
    for a in AsignacionActividad.objects.filter(user=user, activo=True, estado="EnCurso"):
        a.estado = "Finalizada"
        a.save()
        RegistroTiempo.objects.create(
            asignacion=a, evento="Finalizacion", fecha_hora=timezone.now(),
            comentario="Cerrado - usuario desvinculado de KACTUS"
        )
        stats["en_curso"] += 1
    
    # 2. Finalizar Pausadas
    for a in AsignacionActividad.objects.filter(user=user, activo=True, estado="Pausada"):
        a.estado = "Finalizada"
        a.save()
        RegistroTiempo.objects.create(
            asignacion=a, evento="Finalizacion", fecha_hora=timezone.now(),
            comentario="Cerrado - usuario desvinculado de KACTUS"
        )
        stats["pausadas"] += 1
    
    # 3. Cancelar Pendientes
    pendientes = AsignacionActividad.objects.filter(
        user=user, activo=True, estado="Pendiente"
    )
    stats["pendientes"] = pendientes.count()
    pendientes.update(estado="Cancelada")
    
    # 4. Inactivar planificaciones futuras
    PlanificacionDetalle.objects.filter(user=user, activo=True).update(activo=False)
    
    # 5. Desactivar usuario
    user.activo = False
    user.save()
    
    # 6. SyncLog
    SyncLog.objects.create(
        user=user, accion="DEACTIVATE",
        valor_anterior={"activo": True},
        valor_nuevo={"activo": False, **stats},
        ejecutado_por=admin_user,
    )
```

---

## 6. Template (integracion_sync.html)

### 6.1 Estructura visual

```
┌─ Integración ───────────────────────────────────────────────────────┐
│  Breadcrumb: Integración > Sincronizar por Cargo                    │
│                                                                      │
│  ┌── Filtros ─────────────────────────────────────────────────┐     │
│  │ 1. Empresa [▾ COMPENSAMOS S.A.S. (602)]                    │     │
│  │ 2. Cargo   [ANALISTA CONTABLE ▾]  buscar...                │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌── Resultados (aparece al seleccionar cargo) ───────────────┐     │
│  │ 🟢 Nuevos (3)           [Habilitar todos]                  │     │
│  │ ┌──────────┬─────────────────┬──────────┬──────────────────┐│     │
│  │ │ Cédula   │ Nombre          │ Cargo    │ Acción           ││     │
│  │ │ 1234567  │ Nuevo Empleado  │ ANALISTA │ [Habilitar]      ││     │
│  │ └──────────┴─────────────────┴──────────┴──────────────────┘│     │
│  │                                                               │     │
│  │ 🟡 Cambios (2)                                               │     │
│  │ ┌──────────┬──────────┬────────────────────────┬──────────┐  │     │
│  │ │ Cédula   │ Nombre   │ Cambio                 │ Acción   │  │     │
│  │ │ 10516678 │ JESUS D. │ Cargo: ANALISTA→AUX CO │ [Sincr.] │  │     │
│  │ │ 10438764 │ CYNTHIA  │ 🔴 Bloqueado: 3 Pend   │ ❌       │  │     │
│  │ └──────────┴──────────┴────────────────────────┴──────────┘  │     │
│  │                                                               │     │
│  │ ✅ Sin cambios (5)                                           │     │
│  │ ┌──────────┬─────────────────────────────────────────────────┐│     │
│  │ │ 10438764 │ CYNTHIA LORAINE SANDOVAL                        ││     │
│  │ └──────────┴─────────────────────────────────────────────────┘│     │
│  │                                                               │     │
│  │ 🔴 Desvinculados (1)        [Desactivar todos]               │     │
│  │ ┌──────────┬──────────┬──────────┬──────────────────────────┐│     │
│  │ │ Cédula   │ Nombre   │ Cargo    │ Acción                   ││     │
│  │ │ 88888888 │ EX EMPLE │ ANALISTA │ [Desactivar] ⚠️          ││     │
│  │ └──────────┴──────────┴──────────┴──────────────────────────┘│     │
│  └──────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 Comportamiento JS

- Al seleccionar empresa → habilita búsqueda de cargo (igual que Habilitaciones)
- Al seleccionar cargo → AJAX `api/sync/comparar/` → renderiza las 4 secciones
- Botones de acción por lote: envían POST con lista de cédulas + accion
- Botones individuales: envían POST con cédula única + accion
- Para "Habilitar" se abre sub-modal con selección de rol + subarea
- Confirmación antes de "Desactivar" (⚠️ irreversible)

---

## 7. Plan de Pruebas

### 7.1 Tests unitarios (Python)

```python
class SyncCargoTests(TestCase):
    
    def setUp(self):
        self.master = User.objects.create(cedula="1", rol=rol_master, ...)
        self.empresa = Empresa.objects.create(nombre="TEST", codigo="600", nit="123")
        self.cargo_old = "ANALISTA CONTABLE"
        self.cargo_new = "AUX CONTABLE"
    
    def test_comparar_nuevo_empleado(self):
        """Empleado en KACTUS pero no en local → categoría 'nuevos'"""
        result = comparar_por_cargo("600", "1005")
        self.assertEqual(len(result["nuevos"]), 1)
        self.assertEqual(len(result["cambios"]), 0)
    
    def test_comparar_cambio_cargo_sin_pendientes(self):
        """Empleado existe local con cargo diferente, sin pendientes → 'cambios', bloqueado=False"""
        User.objects.create(cedula="10516678", cargo=self.cargo_old, activo=True)
        result = comparar_por_cargo("600", "1005")
        self.assertEqual(len(result["cambios"]), 1)
        self.assertFalse(result["cambios"][0]["bloqueado"])
    
    def test_comparar_cambio_cargo_con_pendientes(self):
        """Empleado existe con cargo diferente y tiene pendientes → bloqueado=True"""
        user = User.objects.create(cedula="10516678", cargo=self.cargo_old, activo=True)
        AsignacionActividad.objects.create(user=user, estado="Pendiente", actividad=...)
        result = comparar_por_cargo("600", "1005")
        self.assertTrue(result["cambios"][0]["bloqueado"])
    
    def test_comparar_sin_cambios(self):
        """Empleado local coincide con KACTUS → 'sin_cambios'"""
        User.objects.create(cedula="10516678", cargo=self.cargo_new, activo=True)
        result = comparar_por_cargo("600", "1005")
        self.assertEqual(len(result["sin_cambios"]), 1)
    
    def test_comparar_desvinculado(self):
        """Empleado local con cargo X pero no está en KACTUS → 'desvinculados'"""
        User.objects.create(cedula="999999", cargo=self.cargo_new, activo=True)
        result = comparar_por_cargo("600", "1005")
        self.assertEqual(len(result["desvinculados"]), 1)
    
    def test_sincronizar_bloquea_con_pendientes(self):
        """No permite sincronizar si tiene pendientes"""
        user = User.objects.create(cedula="10516678", cargo=self.cargo_old)
        AsignacionActividad.objects.create(user=user, estado="Pendiente", ...)
        with self.assertRaises(ValidationError):
            ejecutar_sincronizar(user, kactus_data, admin)
    
    def test_sincronizar_actualiza_cargo(self):
        """Sincronizar exitoso actualiza cargo y empresa"""
        user = User.objects.create(cedula="10516678", cargo=self.cargo_old)
        kactus_data = {"cod_empr": "600", "cargo": self.cargo_new}
        ejecutar_sincronizar(user, kactus_data, admin)
        user.refresh_from_db()
        self.assertEqual(user.cargo, self.cargo_new)
    
    def test_desactivar_cierra_actividades(self):
        """Desactivar finaliza/cancela todo y marca inactivo"""
        user = User.objects.create(cedula="999999", cargo=self.cargo_new)
        act = AsignacionActividad.objects.create(user=user, estado="EnCurso", ...)
        ejecutar_desactivar(user, admin)
        user.refresh_from_db()
        act.refresh_from_db()
        self.assertFalse(user.activo)
        self.assertEqual(act.estado, "Finalizada")
    
    def test_desactivar_cancela_pendientes(self):
        """Pendientes pasan a Cancelada"""
        user = User.objects.create(cedula="999999", cargo=self.cargo_new)
        act = AsignacionActividad.objects.create(user=user, estado="Pendiente", ...)
        ejecutar_desactivar(user, admin)
        act.refresh_from_db()
        self.assertEqual(act.estado, "Cancelada")
```

### 7.2 Tests de integración (HTTP)

```python
class SyncAPITests(TestCase):
    
    def test_api_comparar_requiere_master(self):
        """Admin no puede acceder al endpoint"""
        self.client.login(cedula="200", fecha="2020-01-01")  # Admin
        resp = self.client.get("/master/integracion/api/sync/comparar/?empresa=600&cargo=1005")
        self.assertEqual(resp.status_code, 302)  # redirect
    
    def test_api_comparar_master_ok(self):
        """Master sí puede acceder"""
        self.client.login(cedula="1044432944", fecha="2020-01-01")  # Master
        resp = self.client.get("/master/integracion/api/sync/comparar/?empresa=600&cargo=1005")
        self.assertEqual(resp.status_code, 200)
    
    def test_api_ejecutar_sincronizar_rechaza_con_pendientes(self):
        """POST sincronizar rechaza si hay pendientes"""
        user = User.objects.create(cedula="10516678", cargo="OLD")
        AsignacionActividad.objects.create(user=user, estado="Pendiente", ...)
        resp = self.client.post("/master/integracion/api/sync/ejecutar/", {
            "accion": "sincronizar",
            "cedulas": ["10516678"],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pendientes", resp.json()["error"])
```

---

## 8. Archivos a modificar

| Archivo | Cambio |
|---|---|
| `apps/auditoria/models.py` | Agregar `SyncLog` |
| `apps/auditoria/migrations/` | Nueva migración `0003_synclog` |
| `apps/estructura/integracion_views.py` | + `sync_cargo`, `api_sync_comparar`, `api_sync_ejecutar` |
| `templates/estructura/integracion_sync.html` | Nuevo template |
| `apps/estructura/urls.py` | + 3 rutas bajo `integracion/` |
| `templates/partials/sidebar_menu.html` | + "Sincronizar por Cargo" solo para Master |
