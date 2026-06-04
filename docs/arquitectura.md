# Arquitectura Enterprise — VIVA1A
## Organización funcional multiempresa

---

## 1. Modelo Conceptual

```
GRUPO EMPRESARIAL (nivel holding)
  ├── Empresa (entidad legal)
  │     └── NIT, Razon Social, datos fiscales
  │
  ├── Area (departamento funcional, UNICA)
  │     └── Contabilidad, Tesoreria, Facturacion, Cuentas Medicas
  │           │
  │           └── SubArea (equipo funcional, UNICA)
  │                 └── Cuentas por Pagar, Nomina, Cartera
  │                       │
  │                       └── Empleado (pertenece a la SubArea)
  │                             └── Usuario del sistema
```

**Principio:** Area y SubArea son entidades UNICAS que existen una sola
vez en todo el sistema. No se duplican por empresa.

**Empresa** es solo un atributo legal del empleado (su contrato).
Un empleado puede tener acceso a una o varias empresas.

---

## 2. Jerarquía Organizacional

```
Grupo Empresarial (implícito)
  │
  ├── [E] VIVA 1A IPS S.A. (600)
  │     └── Legal: NIT 900219120
  │
  ├── [E] COMPENSAMOS S.A.S. (601)
  │     └── Legal: NIT 900299739
  │
  ├── [E] LABOR HUMANA S.A.S. (602)
  │     └── Legal: NIT 900404273
  │
  ├── [A] Contabilidad ─── [SA] Cuentas por Pagar
  │                     └── [SA] Nomina
  │
  ├── [A] Tesoreria ────── [SA] Recaudo
  │                     └── [SA] Pagos
  │
  ├── [A] Facturacion ──── [SA] Radicacion
  │                     └── [SA] Glosas
  │
  ├── [A] Cuentas Medicas ─ [SA] Auditoria
  │                       └── [SA] Autorizaciones
  │
  └── [A] Tecnologia ──── [SA] Aplicaciones Corporativas
                        └── [SA] Infraestructura
```

Donde:
- `[E]` = Empresa (entidad legal, no jerarquica)
- `[A]` = Area (funcional, unica)
- `[SA]` = SubArea (funcional, unica)

Un empleado de VIVA 1A puede trabajar en Contabilidad > Cuentas por Pagar
y tambien tener acceso a las actividades de COMPENSAMOS y LABOR HUMANA
si su rol lo permite.

---

## 3. Relaciones entre Entidades

```
┌─────────────────────────────────────────────────────────────┐
│                    ESTRUCTURA FUNCIONAL                      │
│                                                             │
│  ┌─────────┐     ┌─────────┐     ┌──────────────┐          │
│  │  Area   │────>│ SubArea │<────│  UserSubArea  │          │
│  │ (unica) │     │ (unica) │     │ (asignacion)  │          │
│  └─────────┘     └─────────┘     └──────┬───────┘          │
│       │               │                 │                  │
│       │               │                 ▼                  │
│       │               │          ┌──────────────┐          │
│       │               └──────────│   Usuario    │          │
│       │                          │  (Empleado)  │          │
│       │                          └──────┬───────┘          │
│       │                                 │                  │
└───────┼─────────────────────────────────┼──────────────────┘
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│  EmpresaArea     │            │   UserEmpresa    │
│ (relacion M:N)   │            │ (contrato legal) │
│ Area ↔ Empresa   │            │ Usuario ↔ Empresa│
└──────┬───────────┘            └──────┬───────────┘
       │                              │
       ▼                              ▼
┌──────────────────────────────────────────────┐
│              Empresa (legal)                  │
│  ┌──────────┬──────────┬──────────┐           │
│  │  VIVA 1A │COMPENSAMOS│LABOR HUM│           │
│  └──────────┴──────────┴──────────┘           │
└──────────────────────────────────────────────┘
```

### Tabla puente: EmpresaArea

```
EmpresaArea
  ├── id
  ├── empresa_id (FK → Empresa)
  ├── area_id (FK → Area)
  ├── activo (bool)
  └── (unique_together: empresa, area)

Cada Area puede estar asociada a 1 o N empresas.
Cada Empresa tiene 1 o N Areas.

Ejemplo:
  Contabilidad → VIVA 1A, COMPENSAMOS, LABOR HUMANA
  Tesoreria    → VIVA 1A, COMPENSAMOS
  Facturacion  → VIVA 1A (solo esta empresa factura)
```

---

## 4. Modelo de Datos

```python
class Empresa(models.Model):
    """Entidad legal. Sin cambios."""
    codigo = models.CharField(max_length=6, unique=True, blank=True)
    nombre = models.CharField(max_length=200)
    nit = models.CharField(max_length=50, unique=True)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField(default=True)

class Area(models.Model):
    """
    Departamento funcional. UNICO en todo el sistema.
    Ya no tiene FK directa a Empresa. La relacion es M:N via EmpresaArea.
    """
    codigo = models.CharField(max_length=6, unique=True, blank=True)
    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    empresas = models.ManyToManyField(
        Empresa, through="EmpresaArea",
        related_name="areas_funcionales"
    )

class EmpresaArea(models.Model):
    """Tabla puente: que empresas participan en cada area."""
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="relaciones_empresas")
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ["empresa", "area"]

class SubArea(models.Model):
    """
    Subdepartamento funcional. UNICO en todo el sistema.
    Pertenece a un Area. NO tiene relacion directa con Empresa.
    """
    codigo = models.CharField(max_length=6, unique=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="subareas")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ["area", "nombre"]  # nombre unico dentro del area

class EmpresaSubArea(models.Model):
    """
    OPCIONAL: si una SubArea solo aplica a ciertas empresas del Area.
    Si no existe registro, la SubArea aplica a todas las empresas del Area.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT)
    subarea = models.ForeignKey(SubArea, on_delete=models.PROTECT)
    activo = models.BooleanField(default=True)

class UserSubArea(models.Model):
    """Asignacion funcional: a que subarea pertenece el usuario."""
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="subareas")
    subarea = models.ForeignKey(SubArea, on_delete=models.PROTECT, related_name="usuarios")
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ["user", "subarea"]

class UserEmpresa(models.Model):
    """Asignacion legal: que empresas tiene el usuario (su contrato/s)."""
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="empresas")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="usuarios")
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ["user", "empresa"]
```

### Modelos que NO cambian

```python
class TipoActividad(models.Model):
    subarea = models.ForeignKey(SubArea, ...)  # igual

class Actividad(models.Model):
    subarea = models.ForeignKey(SubArea, ...)  # igual

class Planificacion(models.Model):
    subarea = models.ForeignKey(SubArea, ...)  # igual
```

---

## 5. Estructura BD (SQL)

```sql
-- Tablas nuevas
CREATE TABLE empresa_area (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id),
    area_id INTEGER NOT NULL REFERENCES area(id),
    activo INTEGER NOT NULL DEFAULT 1,
    UNIQUE(empresa_id, area_id)
);

CREATE TABLE empresa_subarea (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresa(id),
    subarea_id INTEGER NOT NULL REFERENCES subarea(id),
    activo INTEGER NOT NULL DEFAULT 1,
    UNIQUE(empresa_id, subarea_id)
);

-- Cambios en tablas existentes
-- area: ELIMINAR columna empresa_id (se migra a empresa_area)
-- subarea: SIN CAMBIOS (ya depende solo de area)
-- user_empresa: SIN CAMBIOS
-- user_subarea: SIN CAMBIOS
```

---

## 6. Migracion

### Paso 1: Crear tablas nuevas
```sql
CREATE TABLE empresa_area (...);
CREATE TABLE empresa_subarea (...);
```

### Paso 2: Migrar datos existentes
```python
# Por cada Area existente, crear registro en EmpresaArea
for area in Area.objects.all():
    EmpresaArea.objects.get_or_create(
        empresa=area.empresa,  # la empresa actual del area
        area=area
    )
```

### Paso 3: Eliminar FK empresa_id de Area
```python
# Migration: RemoveField
migrations.RemoveField(
    model_name="area",
    name="empresa",
)
```

### Paso 4: Agregar M2M through
```python
# Migration: AddField (ManyToManyField with through)
migrations.AddField(
    model_name="area",
    name="empresas",
    field=models.ManyToManyField(
        through="EmpresaArea", to="accounts.Empresa"
    ),
)
```

---

## 7. Flujos Transversales

### Habilitacion desde KACTUS

```
1. Admin busca cargos (global, sin empresa)
2. Selecciona cargos con checkboxes
3. Carga empleados → cada uno trae:
   - Su empresa legal (cod_empr) → UserEmpresa
   - Su area KACTUS → sugerencia para Area local
4. Admin selecciona Area/SubArea local
5. Sistema:
   - Crea User con datos basicos
   - Crea UserEmpresa (empresa legal)
   - Crea UserSubArea (area funcional)
   - Si el Area no esta asociada a la empresa legal,
     crea EmpresaArea automaticamente
```

### Planificacion

```
1. Admin selecciona una SubArea
2. Ve todos los usuarios de esa SubArea
   (de todas las empresas)
3. Planifica actividades para esos usuarios
4. Cada usuario ve las actividades en su Tablero
```

### Dashboard / Progreso

```
Vista por defecto: organizada por Area/SubArea
  ├── Todas las actividades de la SubArea
  ├── Usuarios de cualquier empresa
  └── Tiempo muerto, vencidas, progreso

Filtro opcional: por empresa legal
  └── Muestra solo usuarios con UserEmpresa = X
```

---

## 8. Buenas Practicas Enterprise

| Practica | Implementacion |
|----------|---------------|
| Separacion legal/funcional | Empresa (legal) vs Area/SubArea (funcional) |
| Evitar duplicacion | Area y SubArea existen UNA vez |
| Relaciones explicitas | Tabla puente EmpresaArea |
| Escalabilidad multiempresa | Agregar empresa a EmpresaArea, no duplicar area |
| Auditoria | AuditLog registra cambios en asignaciones |
| Flexibilidad | EmpresaSubArea opcional para restricciones finas |
| Consistencia | Unique constraints evitan duplicados |

---

## 9. Ejemplos Reales

### Ejemplo 1: Contabilidad Compartida

```yaml
Areas del sistema:
  - Contabilidad (asociada a: VIVA 1A, COMPENSAMOS, LABOR HUMANA)
    SubAreas:
      - Cuentas por Pagar
      - Nomina
      - Cartera

Usuarios:
  Maria (VIVA 1A)
    Empresa: VIVA 1A
    SubArea: Contabilidad > Cuentas por Pagar
    Actividades: Pago a proveedores VIVA 1A y COMPENSAMOS

  Carlos (COMPENSAMOS)
    Empresa: COMPENSAMOS
    SubArea: Contabilidad > Cuentas por Pagar
    Actividades: Pago a proveedores COMPENSAMOS

  Director Juan (LABOR HUMANA)
    Empresa: LABOR HUMANA
    SubArea: Contabilidad > Cuentas por Pagar
    Rol: Admin (planifica para Maria y Carlos)
```

### Ejemplo 2: IT Compartido

```yaml
Areas del sistema:
  - Tecnologia (asociada a: VIVA 1A, COMPENSAMOS, LABOR HUMANA)
    SubAreas:
      - Aplicaciones Corporativas
      - Infraestructura
      - Soporte Tecnico

Usuarios:
  Humberto (VIVA 1A)
    Empresa: VIVA 1A
    SubArea: Tecnologia > Aplicaciones Corporativas
    Rol: Master (gestiona todo el sistema)

  Ana (VIVA 1A)
    Empresa: VIVA 1A
    SubArea: Tecnologia > Soporte Tecnico
    Actividades: Soporte a usuarios de todas las empresas
```

### Ejemplo 3: Area Especifica

```yaml
Areas del sistema:
  - Facturacion Electronica (asociada solo a: VIVA 1A)
    SubAreas:
      - Emision
      - Radicacion

Usuarios:
  Pedro (VIVA 1A)
    Empresa: VIVA 1A
    SubArea: Facturacion > Emision
    # Solo VIVA 1A factura, las otras empresas no tienen esta area
```

---

## 10. Resumen de cambios vs estado actual

| Aspecto | Estado actual | Estado futuro |
|---------|---------------|---------------|
| Area.empresa | FK obligatorio | Eliminado (M2M via EmpresaArea) |
| Unicidad de Area | Por empresa (duplicado) | Global (unico) |
| SubArea.empresa | Heredada via Area | No existe |
| EmpresaArea | No existe | Nueva tabla puente |
| Filtros por empresa | Obligatorios | Opcionales (solo legal) |
| Dashboard | Filtrado por empresa | Filtrado por SubArea |
| Seleccion de subareas | Solo de la empresa | Todas disponibles |
| Validacion subarea↔empresa | Hard barrier | Eliminada |
