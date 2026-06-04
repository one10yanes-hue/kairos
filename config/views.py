from django.shortcuts import render, redirect


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", {"reason": reason}, status=403)


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


def admin_root(request):
    if request.user.is_authenticated and request.user.rol.nombre in ("Admin", "Master"):
        return redirect("dashboard:dashboard_admin")
    return render(request, "404.html", status=404)


def catch_all_404(request, path=""):
    return render(request, "404.html", status=404)
