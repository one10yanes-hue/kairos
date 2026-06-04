from django import forms
from apps.accounts.models import Empresa
from .models import Area, SubArea, UserSubArea


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ["nombre", "nit", "direccion", "telefono", "logo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "nit": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
        }


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ["nombre", "descripcion"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class SubAreaForm(forms.ModelForm):
    class Meta:
        model = SubArea
        fields = ["area", "nombre", "descripcion"]
        widgets = {
            "area": forms.Select(attrs={"class": "form-control dynamic-select", "data-model": "area", "data-placeholder": "Buscar area por nombre..."}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class UserSubAreaForm(forms.ModelForm):
    class Meta:
        model = UserSubArea
        fields = ["user", "subarea"]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "subarea": forms.Select(attrs={"class": "form-control"}),
        }
