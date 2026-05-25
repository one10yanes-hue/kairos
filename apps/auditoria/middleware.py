from .models import AuditLog


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            user = request.user if request.user.is_authenticated else None
            path = request.path
            modelo = self._extract_model(path)
            accion = self._get_accion(request.method)

            if modelo and user:
                try:
                    AuditLog.objects.create(
                        user=user,
                        accion=accion,
                        modelo_afectado=modelo,
                        id_registro=None,
                        detalle={"path": path, "method": request.method},
                        ip_address=self._get_ip(request),
                    )
                except Exception:
                    pass

        return response

    def _extract_model(self, path):
        parts = [p for p in path.strip("/").split("/") if p]
        if parts:
            model_map = {
                "empresas": "Empresa",
                "areas": "Area",
                "subareas": "SubArea",
                "usuarios": "User",
                "empresas": "Empresa",
                "tipos": "TipoActividad",
                "segmentos": "Segmento",
                "actividades": "Actividad",
                "planificaciones": "Planificacion",
                "kpis": "KPISLA",
                "actividad": "AsignacionActividad",
            }
            palabra = parts[0]
            if palabra in model_map:
                return model_map[palabra]
            if len(parts) > 1 and parts[1] in model_map:
                return model_map[parts[1]]
        return ""

    def _get_accion(self, method):
        accion_map = {"POST": "CREATE", "PUT": "UPDATE", "PATCH": "UPDATE", "DELETE": "DELETE"}
        return accion_map.get(method, "UNKNOWN")

    def _get_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
