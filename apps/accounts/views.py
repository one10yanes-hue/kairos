from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from apps.estructura.models import SubArea, UserSubArea
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
    usuarios = User.objects.filter(activo=True).select_related("rol").prefetch_related(
        "empresas__empresa", "subareas__subarea__area__empresa"
    )
    if q:
        usuarios = usuarios.filter(
            Q(cedula__icontains=q) | Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(email__icontains=q)
        )
    if rol_filter:
        usuarios = usuarios.filter(rol_id=rol_filter)
    paginator = Paginator(usuarios, 10)
    page = request.GET.get("page", 1)
    usuarios_page = paginator.get_page(page)
    roles = Rol.objects.filter(activo=True)
    return render(request, "accounts/usuarios.html", {"usuarios": usuarios_page, "page_obj": usuarios_page, "roles": roles, "q": q, "rol_filter": rol_filter})


@login_required
def master_usuario_create(request):
    if request.user.rol.nombre != "Master":
        return redirect("root")

    empresas = Empresa.objects.filter(activo=True)
    subareas = SubArea.objects.filter(activo=True).select_related("area__empresa")

    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            empresa_ids = request.POST.getlist("empresas")
            subarea_ids = request.POST.getlist("subareas")
            for eid in empresa_ids:
                UserEmpresa.objects.get_or_create(user=user, empresa_id=eid, defaults={"activo": True})
            for sid in subarea_ids:
                UserSubArea.objects.get_or_create(user=user, subarea_id=sid, defaults={"activo": True})
            messages.success(request, "Usuario creado con empresas y subareas asignadas.")
            return redirect("accounts:master_usuarios")
    else:
        form = UserForm()

    return render(request, "accounts/usuario_form.html", {
        "form": form, "title": "Crear Usuario",
        "empresas": empresas, "subareas": subareas,
    })


@login_required
def master_usuario_edit(request, pk):
    if request.user.rol.nombre != "Master":
        return redirect("root")
    usuario = get_object_or_404(User, pk=pk, activo=True)
    empresas = Empresa.objects.filter(activo=True)
    subareas = SubArea.objects.filter(activo=True).select_related("area__empresa")
    user_empresas = list(UserEmpresa.objects.filter(user=usuario, activo=True).values_list("empresa_id", flat=True))
    user_subareas = list(UserSubArea.objects.filter(user=usuario, activo=True).values_list("subarea_id", flat=True))

    if request.method == "POST":
        form = UserForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            empresa_ids = set(request.POST.getlist("empresas", []))
            subarea_ids = set(request.POST.getlist("subareas", []))

            current_empresas = set(UserEmpresa.objects.filter(user=usuario, activo=True).values_list("empresa_id", flat=True))
            current_subareas = set(UserSubArea.objects.filter(user=usuario, activo=True).values_list("subarea_id", flat=True))

            to_add_empresas = empresa_ids - current_empresas
            to_remove_empresas = current_empresas - empresa_ids
            to_add_subareas = subarea_ids - current_subareas
            to_remove_subareas = current_subareas - subarea_ids

            for eid in to_add_empresas:
                UserEmpresa.objects.get_or_create(user=usuario, empresa_id=eid, defaults={"activo": True})
            UserEmpresa.objects.filter(user=usuario, empresa_id__in=to_remove_empresas).update(activo=False)

            for sid in to_add_subareas:
                UserSubArea.objects.get_or_create(user=usuario, subarea_id=sid, defaults={"activo": True})
            UserSubArea.objects.filter(user=usuario, subarea_id__in=to_remove_subareas).update(activo=False)

            messages.success(request, "Usuario actualizado con empresas y subareas.")
            return redirect("accounts:master_usuarios")
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
def master_usuario_empresas(request, pk):
    if request.user.rol.nombre != "Master":
        return redirect("root")
    usuario = get_object_or_404(User, pk=pk, activo=True)
    empresas_user = UserEmpresa.objects.filter(user=usuario, activo=True)
    empresas_disponibles = Empresa.objects.filter(activo=True).exclude(
        id__in=empresas_user.values_list("empresa_id", flat=True)
    )
    if request.method == "POST":
        empresa_id = request.POST.get("empresa_id")
        if empresa_id:
            UserEmpresa.objects.get_or_create(user=usuario, empresa_id=empresa_id, defaults={"activo": True})
            messages.success(request, "Empresa asignada al usuario.")
            return redirect("accounts:master_usuario_empresas", pk=pk)
    return render(request, "accounts/usuario_empresas.html", {
        "usuario": usuario,
        "empresas_user": empresas_user,
        "empresas_disponibles": empresas_disponibles,
    })


@login_required
def master_usuario_empresa_remove(request, pk, empresa_pk):
    if request.user.rol.nombre != "Master":
        return redirect("root")
    ue = get_object_or_404(UserEmpresa, user_id=pk, empresa_id=empresa_pk)
    ue.activo = False
    ue.save()
    messages.success(request, "Empresa removida del usuario.")
    return redirect("accounts:master_usuario_empresas", pk=pk)
