from django import forms
from .models import AsignacionActividad, RegistroTiempo, TrasladoActividad, Comentario
from apps.actividades.models import Actividad


class RegistroTiempoForm(forms.ModelForm):
    class Meta:
        model = RegistroTiempo
        fields = ["comentario", "nro_actividad"]
        widgets = {
            "comentario": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Opcional"}),
            "nro_actividad": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1", "placeholder": "Cantidad o nro de actividad"}),
        }

    def clean_nro_actividad(self):
        val = self.cleaned_data.get("nro_actividad")
        if val is not None:
            try:
                val = int(val)
            except (ValueError, TypeError):
                raise forms.ValidationError("Debe ser un numero valido.")
            if val < 0:
                raise forms.ValidationError("Debe ser un numero positivo.")
        return val


class ActividadNoProgramadaForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ["subarea", "tipo_actividad", "nombre", "descripcion"]
        widgets = {
            "subarea": forms.HiddenInput(),
            "tipo_actividad": forms.HiddenInput(),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Que vas a hacer?"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Describe la actividad"}),
        }


class TrasladoForm(forms.Form):
    user_destino = forms.CharField(widget=forms.HiddenInput())
    actividad_reemplazo = forms.CharField(widget=forms.HiddenInput())
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Motivo del traslado"}),
        required=False
    )


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ["texto"]
        widgets = {
            "texto": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Agregar comentario"})
        }
