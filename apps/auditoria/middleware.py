from .models import AuditLog

PASSWORDS_FILTER = ["password", "csrfmiddlewaretoken", "csrf_token", "_token"]

SKIP_PATHS = [
    "/login/", "/logout/",
    "/static/", "/media/",
    "/admin/", "/accounts/login/",
]

MODEL_MAP = {
    "empresas": "Empresa",
    "areas": "Area",
    "subareas": "SubArea",
    "usuarios": "User",
    "tipos": "TipoActividad",
    "actividades": "Actividad",
    "planificaciones": "Planificacion",
    "detalle": "PlanificacionDetalle",
    "actividad": "AsignacionActividad",
    "dashboard": "Dashboard",
    "progreso": "Progreso",
    "reportes": "Reporte",
    "linea-tiempo": "LineaTiempo",
    "calendar": "Calendario",
    "tablero": "Tablero",
    "perfil": "Perfil",
    "calendario": "Calendario",
    "traslado": "Traslado",
    "importaciones": "Importacion",
    "no-programada": "EventoFlash",
}


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            path = request.path
            if self._should_skip(path):
                return response

            user = request.user if request.user.is_authenticated else None
            if not user:
                return response

            try:
                modelo, id_registro = self._extract_model_and_id(path)
                data = self._get_clean_post(request)
                extra = {}
                ua = request.META.get("HTTP_USER_AGENT", "")
                if ua:
                    extra["user_agent"] = ua[:200]
                ref = request.META.get("HTTP_REFERER", "")
                if ref:
                    extra["referer"] = ref

                detalle = {"path": path, "method": request.method}
                if data:
                    detalle["data"] = data
                if extra:
                    detalle.update(extra)

                AuditLog.objects.create(
                    user=user,
                    accion=self._get_accion(request.method),
                    modelo_afectado=modelo or self._fallback_model(path),
                    id_registro=id_registro,
                    detalle=detalle,
                    ip_address=self._get_ip(request),
                )
            except Exception:
                pass

        return response

    def _should_skip(self, path):
        for skip in SKIP_PATHS:
            if path.startswith(skip):
                return True
        return False

    def _extract_model_and_id(self, path):
        parts = [p for p in path.strip("/").split("/") if p]
        modelo = ""
        id_registro = None

        # Buscar un ID numerico en la ruta y el modelo antes de el
        for i, part in enumerate(parts):
            if part.isdigit() and i > 0:
                id_registro = int(part)
                # El modelo es la palabra antes del ID
                anterior = parts[i - 1]
                # Pero puede venir despues de verbos como "editar", "eliminar", "crear"
                verbos = {"editar", "eliminar", "crear", "ver", "iniciar", "finalizar", "pausar", "reanudar", "trasladar", "cancelar", "aceptar", "rechazar", "remover"}
                if anterior in verbos and i > 1:
                    anterior = parts[i - 2]
                if anterior in MODEL_MAP:
                    modelo = MODEL_MAP[anterior]
                else:
                    modelo = anterior.capitalize()
                break

        if not modelo:
            # Sin ID: buscar la primera palabra que coincida
            for part in parts:
                if part in MODEL_MAP:
                    modelo = MODEL_MAP[part]
                    break

        return modelo, id_registro

    def _fallback_model(self, path):
        parts = [p for p in path.strip("/").split("/") if p]
        for part in parts:
            if part in MODEL_MAP:
                return MODEL_MAP[part]
            if part.isdigit() and parts.index(part) > 0:
                return parts[parts.index(part) - 1].capitalize()
        return path.strip("/").split("/")[0].capitalize() if parts else "Unknown"

    def _get_clean_post(self, request):
        if request.method != "POST":
            return {}
        raw = getattr(request, "POST", {})
        if not raw:
            raw = getattr(request, "data", {})
        clean = {}
        for key, val in raw.items():
            if isinstance(val, (list, tuple)):
                val = list(val)
            if any(f in key.lower() for f in PASSWORDS_FILTER):
                clean[key] = "***FILTERED***"
            elif isinstance(val, str) and len(val) > 200:
                clean[key] = val[:200] + "..."
            else:
                clean[key] = val
        return clean

    def _get_accion(self, method):
        accion_map = {"POST": "CREATE", "PUT": "UPDATE", "PATCH": "UPDATE", "DELETE": "DELETE"}
        return accion_map.get(method, "UNKNOWN")

    def _get_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
