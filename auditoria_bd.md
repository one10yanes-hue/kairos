# VIVA1A - Auditoria de Base de Datos

**Fecha:** 26/05/2026

## Resumen

| Metrica | Valor |
|---------|-------|
| Errores | 2 |
| Advertencias | 5 |
| Verificaciones OK | 7 |

## Detalle por item

- [OK] `OK`: Foreign key violations: 0
- [OK] `OK`: File integrity: ok
- [INFO] `INFO`: Inactive users: 0
- [OK] `OK`: is_active != activo: 0
- [OK] `OK`: All users have empresa + subarea
- [OK] `OK`: unique_en_curso_por_usuario constraint OK
- [OK] `OK`: EnCurso for inactive users: 0
- [WARN] `WARN`: Active assignments linked to inactive plan_detalle: 0
- [ERROR] `ERROR`: Finalizacion events on non-final activities: 0
- [WARN] `WARN`: Inicio events on pending activities: 0
- [WARN] `WARN`: Active detalles in inactive plans: 0
- [OK] `OK`: Activities where subarea != tipo subarea: 0
- [ERROR] `ERROR`: Transfers accepted without destino: 0
- [INFO] `INFO`: Pending transfers: 0
- [WARN] `WARN`: Active user-empresa to inactive empresa: 0
- [WARN] `WARN`: Active user-subarea to inactive subarea: 0
- [INFO] `INFO`: Roles: 3 (Master, Admin, Usuario)
- [INFO] `INFO`: Empresas: 2
- [INFO] `INFO`: TipoActividades: 16

## Tablas con datos

