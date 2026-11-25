from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import Usuario


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    recordarme = forms.BooleanField(required=False, initial=True)

    error_messages = {"invalido": "Email o contraseña incorrectos, o la cuenta está inactiva."}

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        email, password = data.get("email"), data.get("password")
        if email and password:
            self.user = authenticate(self.request, email=email, password=password)
            if self.user is None:
                raise forms.ValidationError(self.error_messages["invalido"], code="invalido")
        return data


# Roles que un administrador de empresa puede asignar (nunca superadmin)
ROLES_EMPRESA = [
    (Usuario.Rol.ADMIN, "Administrador — todo, incluidos usuarios"),
    (Usuario.Rol.OPERADOR, "Operador — captura y consulta operación"),
    (Usuario.Rol.CONSULTA, "Consulta — solo lectura"),
]


class UsuarioForm(forms.ModelForm):
    """Alta/edición de usuarios DENTRO de la empresa activa."""

    rol = forms.ChoiceField(choices=ROLES_EMPRESA, widget=forms.RadioSelect)
    password = forms.CharField(
        label="Contraseña", strip=False, required=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Mínimo 10 caracteres. En edición, déjala vacía para no cambiarla.",
    )

    class Meta:
        model = Usuario
        fields = ["nombre", "email", "rol", "is_active"]

    def __init__(self, *args, empresa, editor, **kwargs):
        self.empresa = empresa
        self.editor = editor
        super().__init__(*args, **kwargs)
        self.es_nuevo = self.instance.pk is None
        if self.es_nuevo:
            self.fields["password"].required = True
            self.fields["password"].help_text = "Mínimo 10 caracteres. Compártela por un medio seguro."
        self.es_yo = not self.es_nuevo and self.instance.pk == editor.pk
        if self.es_yo:
            # Evita que un admin se quite su propio acceso por accidente
            self.fields["rol"].disabled = True
            self.fields["is_active"].disabled = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un usuario con ese email.")
        return email

    def clean_password(self):
        pwd = self.cleaned_data.get("password")
        if pwd:
            validate_password(pwd, self.instance)
        return pwd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.empresa = self.empresa  # siempre la empresa activa: no se puede "mover" usuarios
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
