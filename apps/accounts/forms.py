from django import forms
from .models import User, Empresa, Rol
from apps.estructura.models import SubArea


class LoginForm(forms.Form):
    cedula = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Cedula"}))
    fecha_expedicion = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date", "placeholder": "Fecha de expedicion"}))


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["cedula", "fecha_expedicion", "nombre", "apellido", "cargo", "email", "telefono", "rol", "roles_adicionales", "maneja_proyectos"]
        widgets = {
            "cedula": forms.TextInput(attrs={"class": "form-control"}),
            "fecha_expedicion": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "apellido": forms.TextInput(attrs={"class": "form-control"}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "rol": forms.Select(attrs={"class": "form-control"}),
            "roles_adicionales": forms.SelectMultiple(attrs={"class": "form-control", "size": "3"}),
            "maneja_proyectos": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class UserCreateForm(UserForm):
    empresas = forms.ModelMultipleChoiceField(
        queryset=Empresa.objects.filter(activo=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    subareas = forms.ModelMultipleChoiceField(
        queryset=SubArea.objects.filter(activo=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ["nombre", "nit", "direccion", "telefono", "logo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "nit": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
        }
