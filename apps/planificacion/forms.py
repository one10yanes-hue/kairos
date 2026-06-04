from django import forms
from .models import Planificacion, PlanificacionDetalle


class PlanificacionForm(forms.ModelForm):
    class Meta:
        model = Planificacion
        fields = ["subarea", "nombre", "descripcion"]
        widgets = {
            "subarea": forms.Select(attrs={"class": "form-control dynamic-select", "data-model": "subarea", "data-placeholder": "Buscar subarea..."}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class PlanificacionDetalleForm(forms.ModelForm):
    class Meta:
        model = PlanificacionDetalle
        fields = ["actividad", "user", "fecha_programada", "fecha_vencimiento"]
        widgets = {
            "actividad": forms.Select(attrs={"class": "form-control dynamic-select", "data-model": "actividad", "data-placeholder": "Buscar actividad..."}),
            "user": forms.Select(attrs={"class": "form-control dynamic-select", "data-model": "user", "data-placeholder": "Buscar usuario..."}),
            "fecha_programada": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "fecha_vencimiento": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }
