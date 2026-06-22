import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from apps.estructura.models import Area, SubArea, UserSubArea
from .models import User, Empresa, UserEmpresa, Rol
from .forms import LoginForm, UserForm, EmpresaForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("root")
    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            cedula = form.cleaned_data["cedula"]
            fecha_expedicion = str(form.cleaned_data["fecha_expedicion"])
            user = authenticate(request, cedula=cedula, fecha_expedicion=fecha_expedicion)
            if user:
                auth_login(request, user)
                return redirect("root")
            messages.error(request, "Cedula o fecha de expedicion incorrectas.")
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    return redirect("accounts:login")


@login_required
def master_usuarios(request):
    if request.user.rol.nombre != "Master":
        return redirect("root")
    q = request.GET.get("q", "")
    rol_filter = request.GET.get("rol", "")
    area_filter = request.GET.get("area", "")
    subarea_filter = request.GET.get("subarea", "")
    usuarios = User.objects.filter(activo=True).select_related("rol").prefetch_related(
        "empresas__empresa",
    )
    if q:
        usuarios = usuarios.filter(
            Q(cedula__icontains=q) | Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(email__icontains=q)
        )
    if rol_filter:
        usuarios = usuarios.filter(rol_id=rol_filter)
    if subarea_filter:
        usuarios = usuarios.filter(subareas__subarea_id=subarea_filter, subareas__activo=True).distinct()
    if area_filter and not subarea_filter:
        usuarios = usuarios.filter(subareas__subarea__area_id=area_filter, subareas__activo=True).distinct()
    paginator = Paginator(usuarios, 10)
    page = request.GET.get("page", 1)
    usuarios_page = paginator.get_page(page)
    roles = Rol.objects.filter(activo=True)
    areas = Area.objects.filter(activo=True).order_by("nombre")
    subareas = SubArea.objects.filter(activo=True)
    if area_filter:
        subareas = subareas.filter(area_id=area_filter)
    return render(request, "accounts/usuarios.html", {
        "usuarios": usuarios_page, "page_obj": usuarios_page,
        "roles": roles, "areas": areas, "subareas": subareas,
        "q": q, "rol_filter": rol_filter,
        "area_filter": int(area_filter) if area_filter else "",
        "subarea_filter": int(subarea_filter) if subarea_filter else "",
    })


@login_required
def master_usuario_create(request):
    if request.user.rol.nombre != "Master":
        return redirect("root")
    empresas = Empresa.objects.filter(activo=True)
    subareas = SubArea.objects.filter(activo=True)

    if request.method == "POST":
        form = UserForm(request.POST)
        empresa_ids = set(int(x) for x in request.POST.getlist("empresas") if x)
        subarea_ids = set(int(x) for x in request.POST.getlist("subareas") if x)
        if not subarea_ids:
            messages.error(request, "Debes seleccionar al menos una subarea.")
        elif form.is_valid():
                user = form.save()
                for eid in empresa_ids:
                    UserEmpresa.objects.update_or_create(user=user, empresa_id=eid, defaults={"activo": True})
                for sid in subarea_ids:
                    UserSubArea.objects.update_or_create(user=user, subarea_id=sid, defaults={"activo": True})
                messages.success(request, "Usuario creado con empresas y subareas asignadas.")
                return redirect("accounts:master_usuarios")
    else:
        form = UserForm()

    return render(request, "accounts/usuario_form.html", {
        "form": form, "title": "Crear Usuario",
        "empresas": empresas, "subareas": subareas,
        "user_empresas": [], "user_subareas": [],
    })


@login_required
def master_usuario_edit(request, pk):
    if request.user.rol.nombre != "Master":
        return redirect("root")
    usuario = get_object_or_404(User, pk=pk, activo=True)
    empresas = Empresa.objects.filter(activo=True)
    subareas = SubArea.objects.filter(activo=True)
    user_empresas = list(UserEmpresa.objects.filter(user=usuario, activo=True).values_list("empresa_id", flat=True))
    user_subareas = list(UserSubArea.objects.filter(user=usuario, activo=True).values_list("subarea_id", flat=True))

    if request.method == "POST":
        form = UserForm(request.POST, instance=usuario)
        empresa_ids = set(int(x) for x in request.POST.getlist("empresas", []) if x)
        subarea_ids = set(int(x) for x in request.POST.getlist("subareas", []) if x)
        if not subarea_ids:
            messages.error(request, "Debes seleccionar al menos una subarea.")
        elif form.is_valid():
                form.save()

                current_empresas = set(UserEmpresa.objects.filter(user=usuario, activo=True).values_list("empresa_id", flat=True))
                current_subareas = set(UserSubArea.objects.filter(user=usuario, activo=True).values_list("subarea_id", flat=True))

                to_add_empresas = empresa_ids - current_empresas
                to_remove_empresas = current_empresas - empresa_ids
                to_add_subareas = subarea_ids - current_subareas
                to_remove_subareas = current_subareas - subarea_ids

                for eid in to_add_empresas:
                    UserEmpresa.objects.update_or_create(user=usuario, empresa_id=eid, defaults={"activo": True})
                UserEmpresa.objects.filter(user=usuario, empresa_id__in=to_remove_empresas).update(activo=False)

                for sid in to_add_subareas:
                    UserSubArea.objects.update_or_create(user=usuario, subarea_id=sid, defaults={"activo": True})
                UserSubArea.objects.filter(user=usuario, subarea_id__in=to_remove_subareas).update(activo=False)

                messages.success(request, "Usuario actualizado con empresas y subareas.")
                return redirect("accounts:master_usuarios")
        # Preservar checkboxes en fallo de validacion
        user_empresas = list(empresa_ids)
        user_subareas = list(subarea_ids)
    else:
        form = UserForm(instance=usuario)

    return render(request, "accounts/usuario_form.html", {
        "form": form, "title": "Editar Usuario", "usuario": usuario,
        "empresas": empresas, "subareas": subareas,
        "user_empresas": user_empresas, "user_subareas": user_subareas,
    })


@login_required
def master_usuario_delete(request, pk):
    if request.user.rol.nombre != "Master":
        return redirect("root")
    usuario = get_object_or_404(User, pk=pk)
    usuario.activo = False
    usuario.is_active = False
    usuario.save()
    messages.success(request, "Usuario inactivado exitosamente.")
    return redirect("accounts:master_usuarios")


@login_required
@login_required
def subir_foto(request):
    if request.method != "POST":
        return redirect("gestion:perfil")
    foto = request.FILES.get("foto")
    if not foto:
        messages.error(request, "Selecciona una imagen.")
        return redirect("gestion:perfil")
    ext = os.path.splitext(foto.name)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        messages.error(request, "Formato no valido. Usa JPG, PNG, GIF o WebP.")
        return redirect("gestion:perfil")
    if foto.size > 5 * 1024 * 1024:
        messages.error(request, "La imagen no puede superar 5MB.")
        return redirect("gestion:perfil")
    request.user.foto = foto
    request.user.save()
    messages.success(request, "Foto actualizada.")
    return redirect("gestion:perfil")


@login_required
def switch_role(request):
    rol_id = request.POST.get("rol_id")
    if not rol_id:
        return redirect(request.META.get("HTTP_REFERER", "/"))
    if request.user.tiene_rol(int(rol_id)):
        request.session["rol_activo"] = int(rol_id)
        request.session.cycle_key()
        rol = Rol.objects.get(pk=int(rol_id))
        if rol.nombre == "Master":
            return redirect("estructura:empresa_list")
        elif rol.nombre == "Admin":
            return redirect("dashboard:dashboard_admin")
        else:
            return redirect("gestion:tablero")
    return redirect(request.META.get("HTTP_REFERER", "/"))
