from django.shortcuts import render


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", {"reason": reason}, status=403)


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
