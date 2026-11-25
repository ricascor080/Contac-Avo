from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Empresa

Usuario = get_user_model()


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ["nombre", "razon_social", "rfc", "giro", "temporada", "activa"]

    def clean_rfc(self):
        return self.cleaned_data["rfc"].strip().upper()


class NuevaEmpresaForm(EmpresaForm):
    """Alta de empresa + su primer usuario administrador, en un solo paso."""

    admin_nombre = forms.CharField(label="Nombre del administrador", max_length=150)
    admin_email = forms.EmailField(label="Email del administrador")
    admin_password = forms.CharField(label="Contraseña inicial", widget=forms.PasswordInput, strip=False)

    class Meta(EmpresaForm.Meta):
        fields = ["nombre", "razon_social", "rfc", "giro", "temporada"]

    def clean_admin_email(self):
        email = self.cleaned_data["admin_email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario con ese email.")
        return email

    def clean(self):
        data = super().clean()
        pwd = data.get("admin_password")
        if pwd:
            try:
                validate_password(pwd)
            except forms.ValidationError as e:
                self.add_error("admin_password", e)
        return data
