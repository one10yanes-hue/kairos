# VIVA1A - Test de Flujo Completo

**Fecha:** 28/05/2026
**Errores:** 9

## Resultados por seccion

- 
=== 1. LOGIN ===
- ❌ Login Master → 200
- ❌ Login Admin → 200
- ❌ Login Usuario → 200
- 
=== 2. MASTER ROUTES ===
- ✅ Root (Master) → 302 (expected 302)
- ✅ Organizacion / Empresas → 200 (expected 200)
- ✅ Organizacion / Areas → 200 (expected 200)
- ✅ Organizacion / SubAreas → 200 (expected 200)
- ✅ Gestionar Usuarios → 200 (expected 200)
- ✅ Crear Usuario → 200 (expected 200)
- ✅ Editar Usuario → 200 (expected 200)
- ✅ Parametros / Tipos → 200 (expected 200)
- ✅ Parametros / Crear Tipo → 200 (expected 200)
- ✅ Parametros / Actividades → 200 (expected 200)
- ✅ Parametros / Crear Actividad → 200 (expected 200)
- ✅ Dashboard → 200 (expected 200)
- ✅ Progreso → 200 (expected 200)
- ✅ Linea de Tiempo → 200 (expected 200)
- ✅ Planificaciones → 200 (expected 200)
- 💥 Crear Planificacion → EXCEPTION: Cannot resolve keyword 'subarea' into field. Choices are: activo, avances, codigo, descripcion, estado, etiquetas, fecha_creacion, fecha_fin_estimada,
- ✅ Reportes → 200 (expected 200)
- ✅ Importaciones / Areas → 200 (expected 200)
- ✅ Importaciones / Usuarios → 200 (expected 200)
- ✅ Integracion / Habilitaciones → 200 (expected 200)
- ✅ Integracion / Sync → 200 (expected 200)
- 
=== 3. ADMIN ROUTES ===
- ✅ Root (Admin) → 302 (expected 302)
- ❌ Dashboard (Admin) → 302 (expected 200) | ?
- ❌ Progreso (Admin) → 302 (expected 200) | ?
- ❌ Parametros/Tipos (Admin) → 302 (expected 200) | ?
- ❌ Actividades (Admin) → 302 (expected 200) | ?
- ❌ Planificaciones (Admin) → 302 (expected 200) | ?
- ❌ Crear Planif (Admin) → 302 (expected 200) | ?
- ❌ Habilitaciones (Admin) → 302 (expected 200) | ?
- ✅ Sync (Admin - denied) → 302 (expected 302)
- ✅ Empresas (Admin - denied) → 302 (expected 302)
- ✅ Areas (Admin - denied) → 302 (expected 302)
- 
=== 4. USUARIO ROUTES ===
- ✅ Root (Usuario) → 302 (expected 302)
- ✅ Tablero → 200 (expected 200)
- ✅ Calendario → 200 (expected 200)
- ✅ Perfil → 200 (expected 200)
- ✅ Crear No Programada → 200 (expected 200)
- ✅ Dashboard (Usuario - denied) → 302 (expected 302)
- ✅ Planificaciones (Usuario - denied) → 302 (expected 302)
- 
=== 5. API ENDPOINTS ===
- ✅ API Subarea → 200 (expected 200)
- ✅ API Empresa → 200 (expected 200)
- ✅ API User → 200 (expected 200)
- ✅ API Actividad → 200 (expected 200)
- ✅ API Tipo Actividad → 200 (expected 200)
- [SKIP] KACTUS API calls (SQL Server not available)
- 
=== 6. PLANIFICACION FLOW ===
- 💥 POST Crear Planif → EXCEPTION: Cannot resolve keyword 'subarea' into field. Choices are: activo, avances, codigo, descripcion, estado, etiquetas, fecha_creacion, fecha_fin_estimada,
- 
=== 7. DB INTEGRITY ===
- ✅ FK violations: 0
- ✅ Integrity: ok

## Resumen

- Total pruebas: 58
- Errores: 9
- Exitos: 49
- FK violations: 0
