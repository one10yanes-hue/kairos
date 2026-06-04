from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from apps.accounts.models import User, Empresa
from apps.estructura.models import SubArea, UserSubArea
from .models import TipoActividad, Actividad
from .forms import TipoActividadForm, ActividadForm


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.rol.nombre not in ["Admin", "Master"]:
            return redirect("root")
        return view_func(request, *args, **kwargs)
    return wrapper


def get_admin_subareas(user):
    if user.rol.nombre == "Master":
        return SubArea.objects.filter(activo=True)
    return SubArea.objects.filter(usuarios__user=user, activo=True)


def _auto_select(form, qs, field_name):
    if qs.count() == 1:
        form.fields[field_name].initial = qs.first().pk
        form.fields[field_name].empty_label = None


def _empresa_filter(request):
    subareas = get_admin_subareas(request.user)
    sub_id = request.GET.get("subarea_id")
    if sub_id:
        try:
            sub_id = int(sub_id)
        except (ValueError, TypeError):
            sub_id = None
    return Empresa.objects.none(), subareas, None, sub_id


def _tipos_queryset(subareas, sub_id=None):
    qs = TipoActividad.objects.filter(subarea__in=subareas, activo=True)
    if sub_id:
        qs = qs.filter(subarea_id=sub_id)
    return qs


@login_required
@admin_required
def tipo_actividad_list(request):
    subareas = get_admin_subareas(request.user)
    q = request.GET.get("q", "")
    tipos = TipoActividad.objects.filter(subarea__in=subareas, activo=True)
    base = tipos  # without search filter for summary
    if q:
        tipos = tipos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q) | Q(subarea__nombre__icontains=q))
    paginator = Paginator(tipos, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    return render(request, "actividades/tipo_list.html", {
        "tipos": page_obj,
        "page_obj": page_obj,
        "q": q,
        "tipos_con_fecha": base.filter(requiere_fecha_limite=True).count(),
        "tipos_sin_fecha": base.filter(requiere_fecha_limite=False).count(),
        "title": "Tipos de Actividad",
    })


@login_required
@admin_required
def tipo_actividad_create(request):
    empresas, subareas, emp_id, sub_id = _empresa_filter(request)
    if request.method == "POST":
        form = TipoActividadForm(request.POST)
        form.fields["subarea"].queryset = subareas
        if form.is_valid():
            form.save()
            messages.success(request, "Tipo de actividad creado.")
            return redirect("actividades:tipo_list")
    else:
        form = TipoActividadForm()
        form.fields["subarea"].queryset = subareas
        _auto_select(form, subareas, "subarea")
    return render(request, "actividades/tipo_form.html", {
        "form": form, "title": "Crear Tipo de Actividad",
        "empresas": empresas, "empresa_id": emp_id, "subarea_id": sub_id,
    })


@login_required
@admin_required
def tipo_actividad_edit(request, pk):
    tipo = get_object_or_404(TipoActividad, pk=pk, activo=True)
    empresas, subareas, emp_id, sub_id = _empresa_filter(request)
    if request.method == "POST":
        form = TipoActividadForm(request.POST, instance=tipo)
        form.fields["subarea"].queryset = subareas
        if form.is_valid():
            form.save()
            messages.success(request, "Tipo de actividad actualizado.")
            return redirect("actividades:tipo_list")
    else:
        form = TipoActividadForm(instance=tipo)
        form.fields["subarea"].queryset = subareas
    return render(request, "actividades/tipo_form.html", {
        "form": form, "title": "Editar Tipo de Actividad",
        "empresas": empresas, "empresa_id": emp_id, "subarea_id": sub_id,
    })


@login_required
@admin_required
def tipo_actividad_delete(request, pk):
    tipo = get_object_or_404(TipoActividad, pk=pk)
    tipo.activo = False
    tipo.save()
    messages.success(request, "Tipo de actividad inactivado.")
    return redirect("actividades:tipo_list")


@login_required
@admin_required
def actividad_list(request):
    subareas = get_admin_subareas(request.user)
    q = request.GET.get("q", "")
    tipo_filter = request.GET.get("tipo", "")
    actividades = Actividad.objects.filter(subarea__in=subareas, activo=True).select_related("tipo_actividad")
    base = actividades  # unfiltered for summary
    if q:
        actividades = actividades.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
    if tipo_filter:
        actividades = actividades.filter(tipo_actividad_id=tipo_filter)
    paginator = Paginator(actividades, 15)

    page_obj = paginator.get_page(request.GET.get("page", 1))
    tipos = TipoActividad.objects.filter(subarea__in=subareas, activo=True)
    return render(request, "actividades/actividad_list.html", {
        "actividades": page_obj,
        "page_obj": page_obj,
        "tipos": tipos,
        "q": q,
        "tipo_filter": tipo_filter,
        "total_base": base.count(),
        "title": "Actividades",
    })


@login_required
@admin_required
def actividad_create(request):
    empresas, subareas, emp_id, sub_id = _empresa_filter(request)
    tipos = _tipos_queryset(subareas, sub_id)
    if request.method == "POST":
        form = ActividadForm(request.POST)
        form.fields["subarea"].queryset = subareas
        form.fields["tipo_actividad"].queryset = tipos
        if form.is_valid():
            form.save()
            messages.success(request, "Actividad creada.")
            return redirect("actividades:actividad_list")
    else:
        initial = {}
        if sub_id:
            initial["subarea"] = sub_id
        form = ActividadForm(initial=initial)
        form.fields["subarea"].queryset = subareas
        _auto_select(form, subareas, "subarea")
        form.fields["tipo_actividad"].queryset = tipos
        _auto_select(form, tipos, "tipo_actividad")
    return render(request, "actividades/actividad_form.html", {
        "form": form, "title": "Crear Actividad",
        "empresas": empresas, "empresa_id": emp_id, "subarea_id": sub_id,
    })


@login_required
@admin_required
def actividad_edit(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk, activo=True)
    empresas, subareas, emp_id, sub_id = _empresa_filter(request)
    if not request.GET.get("subarea_id"):
        sub_id = actividad.subarea_id
    tipos = _tipos_queryset(subareas, sub_id)
    if request.method == "POST":
        form = ActividadForm(request.POST, instance=actividad)
        form.fields["subarea"].queryset = subareas
        form.fields["tipo_actividad"].queryset = tipos
        if form.is_valid():
            form.save()
            messages.success(request, "Actividad actualizada.")
            return redirect("actividades:actividad_list")
    else:
        form = ActividadForm(instance=actividad)
        form.fields["subarea"].queryset = subareas
        form.fields["tipo_actividad"].queryset = tipos
    return render(request, "actividades/actividad_form.html", {
        "form": form, "title": "Editar Actividad",
        "empresas": empresas, "empresa_id": emp_id, "subarea_id": sub_id,
    })


@login_required
@admin_required
def actividad_delete(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)
    actividad.activo = False
    actividad.save()
    messages.success(request, "Actividad inactivada.")
    return redirect("actividades:actividad_list")
