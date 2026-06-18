from django import forms
from apps.estructura.models import SubArea
from .models import TipoActividad, Actividad


class SubAreaModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.nombre} ({obj.area.nombre})"


class TipoActividadForm(forms.ModelForm):
    subarea = SubAreaModelChoiceField(
        queryset=SubArea.objects.none(),
        widget=forms.Select(attrs={"class": "form-select dynamic-select", "data-model": "subarea", "data-placeholder": "Buscar subarea...", "style": "font-size:0.85rem;"})
    )

    class Meta:
        model = TipoActividad
        fields = ["subarea", "nombre", "descripcion", "requiere_fecha_limite", "requiere_entregable", "es_flash", "solo_proyecto"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "style": "font-size:0.85rem;"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "style": "font-size:0.85rem;"}),
            "requiere_fecha_limite": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "requiere_entregable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "es_flash": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "solo_proyecto": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ActividadForm(forms.ModelForm):
    subarea = SubAreaModelChoiceField(
        queryset=SubArea.objects.none(),
        widget=forms.Select(attrs={"class": "form-select dynamic-select", "data-model": "subarea", "data-placeholder": "Buscar subarea...", "style": "font-size:0.85rem;"})
    )

    class Meta:
        model = Actividad
        fields = ["subarea", "tipo_actividad", "nombre", "descripcion"]
        widgets = {
            "tipo_actividad": forms.Select(attrs={"class": "form-select dynamic-select", "data-model": "tipo_actividad", "data-placeholder": "Buscar tipo...", "style": "font-size:0.85rem;"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "style": "font-size:0.85rem;"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "style": "font-size:0.85rem;"}),
        }
