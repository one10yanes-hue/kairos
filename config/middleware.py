class HtmxMiddleware:
    """Agrega request.htmx para detectar peticiones HTMX."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.htmx = request.headers.get('HX-Request') == 'true'
        return self.get_response(request)


class NoCacheMiddleware:
    """Evita que el navegador cachee paginas HTML.
    El boton 'Atras' siempre pedira datos frescos al servidor
    en vez de mostrar formularios llenos o estados viejos."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if "text/html" in content_type:
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
