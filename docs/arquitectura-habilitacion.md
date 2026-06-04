# Arquitectura: Reestructuracion Area/SubArea para Centros de Servicio Compartido

## Problema de fondo

Actualmente `Area` tiene un `ForeignKey` a `Empresa`:

```
Empresa → Area → SubArea → TipoActividad / Actividad / Planificacion
```

Esto asume que cada departamento pertenece a UNA sola empresa.
En un modelo de centro de servicio compartido esto es incorrecto:

- Contabilidad sirve a VIVA 1A, COMPENSAMOS y LABOR HUMANA
- IT soporta todas las empresas
- Un director de Labor Humana puede ser el director de todas las empresas

Tener que crear "Contabilidad" para cada empresa es redundante y no
refleja la realidad organizacional.

## Modelo propuesto

**Separar lo legal de lo funcional:**

```
┌─────────────────────┐     ┌──────────────────────────┐
│  Entidad Legal      │     │  Entidad Funcional       │
│                     │     │                          │
│  Empresa            │     │  Area                    │
│  ├─ nombre          │     │  ├─ nombre               │
│  ├─ NIT             │     │  └─ (sin empresa)        │
│  └─ datos fiscales  │     │                          │
│                     │     │  SubArea                 │
│  UserEmpresa        │     │  ├─ nombre               │
│  └─ usuario X       │     │  └─ area → Area          │
│     empresa legal   │     │                          │
│                     │     │  UserSubArea              │
│                     │     │  └─ usuario Y            │
│                     │     │     subarea → SubArea    │
└─────────────────────┘     └──────────────────────────┘
```

### Cambios en los modelos

```python
# ANTES:
class Area(models.Model):
    empresa = ForeignKey(Empresa)  # ← esto limita
    nombre = CharField(...)

class SubArea(models.Model):
    area = ForeignKey(Area)  # area pertenece a una empresa

# DESPUES:
class Area(models.Model):
    nombre = CharField(...)  # sin empresa, transversal

class SubArea(models.Model):
    area = ForeignKey(Area)  # area transversal
```

### Lo que NO cambia

- `UserEmpresa` → sigue igual (usuario ↔ empresa legal)
- `UserSubArea` → sigue igual (usuario ↔ subarea funcional)
- `Planificacion.subarea` → sigue igual
- `TipoActividad.subarea` → sigue igual
- `Actividad.subarea` → sigue igual
- `integracion_cargo` (POST) → crea usuarios con empresa + subarea

### Impacto en el flujo

**Antes:** Un usuario se asigna a una SubArea que pertenece a un Area
que pertenece a una Empresa. Todo en cadena.

**Despues:** Un usuario tiene dos asignaciones independientes:
- `UserEmpresa` → la(s) empresa(s) legal(es) donde trabaja
- `UserSubArea` → la(s) subarea(s) funcional(es) donde opera

Esto permite que un usuario de LABOR HUMANA trabaje en el Area
"Contabilidad" que da servicio a las 3 empresas.

## Ejemplo concreto

```
Empresas:
  VIVA 1A IPS S.A.  (600)
  COMPENSAMOS S.A.S. (601)
  LABOR HUMANA S.A.S. (602)

Areas (transversales):
  Tecnologia
  Contabilidad
  Talento Humano
  Juridico

SubAreas:
  Tecnologia > Aplicaciones Corporativas
  Tecnologia > Infraestructura
  Contabilidad > Cuentas por Pagar
  Contabilidad > Nomina
  Talento Humano > Seleccion
  Talento Humano > Bienestar

Usuario Director:
  - Empresa: LABOR HUMANA (su contrato legal)
  - SubAreas: Tecnologia/Aplicaciones, Contabilidad/CuentasxPagar
  - Puede planificar/ver actividades de TODAS las empresas en esas SubAreas

Usuario Analista:
  - Empresa: VIVA 1A (su contrato legal)
  - SubArea: Tecnologia/Aplicaciones Corporativas
  - Solo ve actividades de su SubArea
```

## Migracion de datos existentes

Si hoy hay areas duplicadas:
```
VIVA 1A > Tecnologia
COMPENSAMOS > Tecnologia
LABOR HUMANA > Tecnologia
```

Se migran a una sola Area "Tecnologia" y las SubAreas se reasignan
a esa unica Area. Las SubAreas con mismo nombre se fusionan:
```
VIVA 1A > Tecnologia > Aplicaciones  ─┐
COMPENSAMOS > Tecnologia > Aplicaciones ─┤ → Tecnologia > Aplicaciones Corporativas
LABOR HUMANA > Tecnologia > Aplicaciones ─┘
```

## Ventajas

1. **Una sola contabilidad** para todas las empresas
2. **Director transversal** maneja su equipo sin importar la empresa legal
3. **Planificacion por area funcional**, no por empresa legal
4. **Simplifica la habilitacion** desde KACTUS: el area funcional se
   asigna directamente, la empresa es solo un dato legal
5. **Escalable** a cualquier estructura organizacional

## Desventajas / Riesgos

1. Hay que migrar datos existentes (areas duplicadas)
2. Cambia la logica de filtros en Dashboard/Progreso (de empresa a subarea)
3. Algunos reportes financieros por empresa pueden requerir ajustes
4. La relacion Area→Empresa se pierde, pero se reemplaza con UserEmpresa

## Decision

¿Se hace el cambio estructural (quitar Empresa de Area) o se busca
una solucion intermedia (ej. Area con empresa nullable)?
