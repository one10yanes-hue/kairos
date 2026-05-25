# Kairos - Validacion de Flujos y Mejoras Potenciales

**Version**: 3.0
**Ultima actualizacion**: 24/05/2026

---

## Indice
1. [Metodologia de Validacion](#metodologia-de-validacion)
2. [Validacion de Flujos Criticos](#validacion-de-flujos-criticos)
3. [Matriz de Riesgos](#matriz-de-riesgos)
4. [Debilidades Identificadas](#debilidades-identificadas)
5. [Mejoras Potenciales](#mejoras-potenciales)
6. [Roadmap Sugerido](#roadmap-sugerido)
7. [Historial de Cambios](#historial-de-cambios)

---

## Metodologia de Validacion

Se validaron los siguientes aspectos para cada flujo critico:

1. **Consistencia de datos**: Los estados y transiciones son validos?
2. **Seguridad**: Usuarios no autorizados pueden acceder?
3. **Concurrencia**: Que pasa si dos acciones ocurren simultaneamente?
4. **Casos borde**: Que pasa con datos incompletos o inesperados?
5. **Rendimiento**: Las consultas escalan con volumen de datos?

---

## Validacion de Flujos Criticos

### 1. Login y Autenticacion

| Aspecto | Resultado | Observacion |
|---------|-----------|-------------|
| Login con cedula + fecha_expedicion | ✅ | Backend custom funciona |
| Redireccion por rol | ✅ | Master → empresas, Admin → dashboard, Usuario → tablero |
| CSRF en formularios | ✅ | `CSRF_USE_SESSIONS = True` |
| Error 403 personalizado | ✅ | `CSRF_FAILURE_VIEW` con pagina Kairos ("Sesion expirada", boton recargar) |
| Errores 404/500 personalizados | ✅ | Paginas limpias con branding Kairos |
| Mensajes de error en login | ✅ | Se renderizan en el login y se consumen ahi (no viajan al dashboard) |
| Notificaciones toast (no desplazan) | ✅ | `position:fixed` + auto-dismiss Bootstrap 6s |

**Debilidad persistente**: Si un atacante conoce cedula+expedicion de un usuario, puede acceder. No hay 2FA ni rate limiting.

---

### 2. Planificacion (Admin)

| Aspecto | Resultado | Observacion |
|---------|-----------|-------------|
| Crear planificacion con actividades + usuarios | ✅ | Formulario unificado |
| Fecha de planificacion obligatoria | ✅ | `required` HTML + validacion backend, siempre obligatoria |
| Seleccion de subarea con tipeo AJAX | ✅ | Busca actividades/usuarios via API con debounce 300ms |
| Filtro de actividades/usuarios en form | ✅ | Busqueda server-side al escribir (tipeo real) |
| Planificacion se cierra al crearse | ✅ | `cerrada=True` |
| Duplicados: misma actividad + usuario | ✅ | `unique_together` en BD |
| Scope: Admin solo ve sus subareas | ✅ | `get_admin_subareas()` |
| Volumen de asignaciones visible | ✅ | Muestra "N act. x M usu." antes de crear |

**Debilidad**: Si Admin selecciona 10 actividades x 20 usuarios = 200 asignaciones, no hay barra de progreso.

---

### 3. Tablero Trello (Usuario)

| Aspecto | Resultado | Observacion |
|---------|-----------|-------------|
| 4 columnas (Planificadas, EnCurso, Pausadas, Finalizadas) | ✅ | Con scroll interno por columna |
| Hoy + Traslados con altura fija y scroll | ✅ | `max-height` con `overflow-y:auto` |
| Una sola actividad EnCurso | ✅ | UniqueConstraint + `_pausar_activas()` |
| Pausadas con botones completos | ✅ | Reanudar, Finalizar, Trasladar, Detalle |
| Finalizadas solo del dia actual | ✅ | `registros__fecha_hora__date=hoy` |
| Timer en vivo (EnCurso) | ✅ | Actualiza cada segundo |
| Tiempo pausado visible | ✅ | `tiempo_pausado_formateado()` |
| Polling traslados pendientes | ✅ | JS cada 30s |
| Comentario opcional al finalizar | ✅ | Sin `required` |
| Nro de actividad obligatorio al finalizar | ✅ | `required` HTML + validacion backend |

---

### 4. Traslado entre Usuarios

| Aspecto | Resultado | Observacion |
|---------|-----------|-------------|
| Solicitud pendiente (no inmediata) | ✅ | `TrasladoActividad(estado="Pendiente")` |
| Destino ve solicitud en tablero | ✅ | Seccion "Traslados" con polling |
| Aceptar/Rechazar/Cancelar | ✅ | Botones en tarjeta |
| Validacion de estado origen al aceptar | ✅ | Si ya esta Finalizada, se cancela el traslado |
| Sin duplicados pendientes | ✅ | UniqueConstraint |
| Scope: solo usuarios del mismo nivel | ✅ | Filtro por rol |

---

### 5. Gestion de Pendientes (Prórroga)

| Aspecto | Resultado | Observacion |
|---------|-----------|-------------|
| Tabla "Pendientes por Gestionar" en planificacion | ✅ | Visible al abrir detalle de planificacion |
| Reprogramar (prórroga) | ✅ | `fecha_limite` → mañana, `prorroga_count++` |
| Reasignar usuario | ✅ | Cambia `user`, `origen="Reasignado"`, `origen_user=admin` |
| Cancelar actividad | ✅ | `estado="Cancelada"` |
| Contador de prorrogas en dashboard | ✅ | KPI + columna "Prr" por usuario |
| Validacion de estado (solo Pendiente/Pausada) | ✅ | Backend rechaza otros estados |
| Trazabilidad del cambio | ✅ | `origen` + `origen_user` trackean el admin que reasigno |
| Sin duplicados al reasignar | ✅ | Mismo usuario no aparece en el select |

---

### 6. Dashboard (Admin/Master)

| Aspecto | Resultado | Observacion |
|---------|-----------|-------------|
| 6 KPIs: Total, Pendientes, Curso, Pausadas, Finalizadas, Hoy | ✅ | Cards responsive |
| KPI Prorrogas | ✅ | Total de asignaciones con `prorroga_count > 0` |
| Indicadores: Tiempo Total, Productividad, Items, Promedio x Item | ✅ | 4 cards adicionales |
| Filtro por subarea | ✅ | Select con submit automatico |
| Filtro por usuario | ✅ | Select con submit automatico |
| Filtro por fecha desde/hasta | ✅ | Inputs date con submit automatico |
| Boton Limpiar filtros | ✅ | Resetea todo |
| Grafico de distribucion (doughnut) | ✅ | Pendientes/Curso/Pausadas/Finalizadas |
| Grafico de productividad (barras) | ✅ | Por usuario |
| Tabla detalle con 12 columnas | ✅ | Incluye Items, Prr, Activo, Pausa, Prom |
| Scope por rol | ✅ | Admin solo ve sus subareas |

---

### 7. Importacion (Master)

| Aspecto | Resultado | Observacion |
|---------|-----------|-------------|
| Seleccion de empresa pre-existente | ✅ | Dropdown con empresas activas |
| Descarga de plantilla con codigo empresa | ✅ | Excel con columnas: empresa_codigo, nombre_area, nombre_subarea |
| Codigos auto-generados | ✅ | `save()` en Area/SubArea |
| Validacion de empresa activa | ✅ | Filtro en descarga e importacion |

---

### 8. Calendario (Usuario)

| Aspecto | Resultado | Observacion |
|---------|-----------|-------------|
| Vista Mes | ✅ | Grid de dias con actividades |
| Vista Semana | ✅ | Timeline horario de 7 dias |
| Vista Dia | ✅ | Timeline horario detallado |
| Navegacion entre vistas | ✅ | Click en dia → vista dia |

---

## Matriz de Riesgos

| Riesgo | Probabilidad | Impacto | Mitigacion Actual | Estado |
|--------|-------------|---------|-------------------|--------|
| **Acceso no autorizado** | Baja | Alto | Proteccion por URL + decoradores | Pendiente — agregar rate limiting |
| **Perdida de datos** | Baja | Medio | `activo=False`, PROTECT en FKs | ✅ Estable |
| **Duplicados por concurrencia** | Baja | Medio | UniqueConstraints en BD | Pendiente — `select_for_update()` |
| **Sobrecarga planificacion masiva** | Media | Bajo | Sin limite | Pendiente |
| **Importacion datos corruptos** | Media | Medio | Errores por fila | Pendiente |
| **Finaliza actividad + acepta traslado simultaneo** | Baja | Alto | Validacion de estado al aceptar | ✅ Superado |
| **Codigo duplicado** | Baja | Medio | `save()` con `generar_codigo()` | ✅ Superado |
| **CSRF pagina fea de Django** | Media | Bajo | `CSRF_FAILURE_VIEW` con pagina Kairos | ✅ Superado |
| **Notificaciones desplazan layout** | Media | Medio | Toasts `position:fixed` + auto-dismiss | ✅ Superado |
| **Errores login viajan al dashboard** | Media | Bajo | Messages en login + consumen ahi | ✅ Superado |

---

## Debilidades Identificadas

### Seguridad

| # | Debilidad | Severidad | Sugerencia | Estado |
|---|-----------|-----------|------------|--------|
| S1 | Login sin limite de intentos | Media | `django-axes` para rate limiting | Pendiente |
| S2 | No hay 2FA | Media | Evaluar en produccion | Pendiente |
| S3 | `SECRET_KEY` por defecto | Alta | Cambiar antes de produccion | Pendiente |
| S4 | `DEBUG=True` | Alta | Deshabilitar en produccion | Pendiente |
| S5 | Sin HTTPS | Alta | Configurar SSL | Pendiente |

### UX

| # | Debilidad | Severidad | Sugerencia | Estado |
|---|-----------|-----------|------------|--------|
| U1 | Filtro subarea tablero recarga pagina | Baja | Fetch AJAX | Pendiente |
| U2 | Sin detalle de actividad en traslado | Baja | Agregar resumen en solicitud | Pendiente |

### Escalabilidad

| # | Debilidad | Severidad | Sugerencia | Estado |
|---|-----------|-----------|------------|--------|
| E1 | `tiempo_efectivo()` recalculo | Media | Cache en `tiempo_total_segundos` | ✅ Superado |
| E2 | Sin paginacion API busqueda | Baja | Límite 20 resultados | ✅ Superado |
| E3 | `select_related` en reportes | Media | Ya usa `select_related` optimo | ✅ Superado |
| E4 | Sin indices en busqueda | Media | `db_index=True` en campos frecuentes | ✅ Superado |

### Funcionalidad

| # | Debilidad | Severidad | Sugerencia | Estado |
|---|-----------|-----------|------------|--------|
| F1 | Colaboracion sin UI | Baja | Boton "Colaborar" en tarjetas | Pendiente |
| F2 | Sin alertas fecha vencida | Media | Tarea programada | Pendiente |
| F3 | Sin recuperacion de contrasena | Media | Vista de reset password | Pendiente |
| F4 | Sin exportacion PDF | Baja | WeasyPrint | Pendiente |
| F5 | Sin audit trail de cambios | Media | Solo HTTP, no cambios en datos | Pendiente |

---

## Mejoras Potenciales

### Prioridad Alta

| Mejora | Esfuerzo | Impacto | Descripcion | Estado |
|--------|----------|---------|-------------|--------|
| **DEBUG=False + SECRET_KEY** | 1 hora | Alto | Configurar para produccion | Pendiente |
| **Rate limiting login** | 2 horas | Alto | `django-axes` | Pendiente |
| **Cachear tiempo efectivo** | 4 horas | Medio | Campo `tiempo_total_segundos` | ✅ Superado |
| **Indices busqueda** | 1 hora | Medio | `db_index=True` | ✅ Superado |

### Prioridad Media

| Mejora | Esfuerzo | Impacto | Descripcion | Estado |
|--------|----------|---------|-------------|--------|
| **Confirmacion volumen planificacion** | 2 horas | Medio | "N act. x M usu." visible | ✅ Superado |
| **Test unitarios** | 16 horas | Alto | Flujos criticos | Pendiente |
| **Notificaciones traslado polling** | 4 horas | Alto | JS cada 30s | ✅ Superado |

### Prioridad Baja

| Mejora | Esfuerzo | Impacto | Descripcion | Estado |
|--------|----------|---------|-------------|--------|
| Filtro AJAX tablero | 3 horas | Bajo | Select subarea via fetch | Pendiente |
| Colaboracion UI | 4 horas | Bajo | Boton + modal en tarjetas | Pendiente |
| Exportacion PDF | 6 horas | Bajo | WeasyPrint | Pendiente |

---

## Roadmap Sugerido

### Fase 1: Produccion (1-2 dias)
- [ ] Deshabilitar DEBUG
- [ ] Generar SECRET_KEY segura
- [ ] Configurar HTTPS
- [ ] Agregar rate limiting al login
- [ ] Backup de BD

### Fase 2: Estabilidad (1 semana)
- [ ] Tests unitarios para flujos criticos
- [ ] Monitoreo de rendimiento en reportes

### Fase 3: UX (2 semanas)
- [ ] Colaboracion UI
- [ ] Mejoras en calendario (posicionamiento por hora)

### Fase 4: Extras (1 mes)
- [ ] Exportacion PDF
- [ ] Alertas de fecha limite vencida
- [ ] Batch operations para planificaciones

---

## Historial de Cambios

| Version | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 23/05/2026 | Version inicial |
| 2.0 | 24/05/2026 | App → Kairos. Importacion redisenada. Codigos auto-generados. Polling traslados. Mi Perfil. Calendario 3 vistas. |
| 3.0 | 24/05/2026 | Dashboard con filtros fecha/usuario + KPIs prorrogas/items/promedio. Tiempo pausado cronometrado. Prórroga/reasignar/cancelar en planificaciones. Finalizadas solo del dia. CSRF/404/500 personalizados. Notificaciones toast fixed. Comentario opcional, nro_actividad obligatorio. DB indices y cache de tiempo. |
