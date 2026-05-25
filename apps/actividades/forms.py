from django import forms
from .models import TipoActividad, Actividad


class TipoActividadForm(forms.ModelForm):
    class Meta:
        model = TipoActividad
        fields = ["subarea", "nombre", "descripcion", "requiere_fecha_limite"]
        widgets = {
            "subarea": forms.Select(attrs={"class": "form-control dynamic-select", "data-model": "subarea", "data-placeholder": "Buscar subarea..."}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "requiere_fecha_limite": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ["subarea", "tipo_actividad", "nombre", "descripcion"]
        widgets = {
            "subarea": forms.Select(attrs={"class": "form-control dynamic-select", "data-model": "subarea", "data-placeholder": "Buscar subarea..."}),
            "tipo_actividad": forms.Select(attrs={"class": "form-control dynamic-select", "data-model": "tipo_actividad", "data-placeholder": "Buscar tipo..."}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
