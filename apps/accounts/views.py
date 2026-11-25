from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from apps.core.permisos import requiere_rol

from .forms import LoginForm, UsuarioForm
from .models import EventoAcceso, Usuario, ip_cliente, registrar_evento
from .seguridad import esta_bloqueado

T = EventoAcceso.Tipo


def _destino_seguro(request, user):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return nxt
    if user.es_superadmin:
        return "core:empresas"
    return settings.LOGIN_REDIRECT_URL


@sensitive_post_parameters("password")
@csrf_protect
@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect(_destino_seguro(request, request.user))

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()[:254]
        dueno = Usuario.objects.filter(email__iexact=email).select_related("empresa").first()
        empresa_dueno = dueno.empresa if dueno else None

        if esta_bloqueado(email, ip_cliente(request)):
            registrar_evento(request, T.LOGIN_BLOQUEADO, email=email, empresa=empresa_dueno)
            form = LoginForm(request)  # no evaluar credenciales mientras esté bloqueado
            form.initial["email"] = email
            mins = settings.LOGIN_VENTANA_MINUTOS
            messages.error(request, f"Demasiados intentos fallidos. Intenta de nuevo en {mins} minutos.")
        elif form.is_valid():
            user = form.user
            login(request, user)
            if not form.cleaned_data.get("recordarme"):
                request.session.set_expiry(0)  # expira al cerrar el navegador
            request.session.pop("empresa_id", None)
            registrar_evento(request, T.LOGIN_OK, usuario=user)
            return redirect(_destino_seguro(request, user))
        else:
            registrar_evento(request, T.LOGIN_FALLIDO, email=email, empresa=empresa_dueno, usuario=None)

    return render(request, "registration/login.html", {"form": form, "next": request.GET.get("next", "")})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        registrar_evento(request, T.LOGOUT)
    logout(request)
    messages.info(request, "Sesión cerrada.")
    return redirect("accounts:login")


@login_required
def mi_cuenta(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # no cerrar la sesión actual
        registrar_evento(request, T.PASSWORD_CAMBIADA, "Cambio propio")
        messages.success(request, "Contraseña actualizada.")
        return redirect("accounts:mi_cuenta")
    return render(request, "accounts/mi_cuenta.html", {"form": form})


# ---------- Administración de usuarios de la empresa (rol admin) ----------

@requiere_rol(Usuario.Rol.ADMIN)
def usuarios(request):
    lista = Usuario.objects.filter(empresa=request.empresa).order_by("-is_active", "nombre")
    return render(request, "accounts/usuarios.html", {"usuarios": lista})


@requiere_rol(Usuario.Rol.ADMIN)
def usuario_nuevo(request):
    form = UsuarioForm(request.POST or None, empresa=request.empresa, editor=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        registrar_evento(request, T.USUARIO_CREADO, f"{user.email} ({user.get_rol_display()})")
        messages.success(request, f"Usuario {user.email} creado.")
        return redirect("accounts:usuarios")
    return render(request, "accounts/usuario_form.html", {"form": form})


@requiere_rol(Usuario.Rol.ADMIN)
def usuario_editar(request, pk):
    # Filtrar por empresa = imposible editar usuarios de otro tenant aunque se adivine el id
    objeto = get_object_or_404(Usuario, pk=pk, empresa=request.empresa)
    form = UsuarioForm(request.POST or None, instance=objeto, empresa=request.empresa, editor=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        cambios = ", ".join(form.changed_data) or "sin cambios"
        registrar_evento(request, T.USUARIO_EDITADO, f"{user.email}: {cambios}")
        messages.success(request, "Usuario actualizado.")
        return redirect("accounts:usuarios")
    return render(request, "accounts/usuario_form.html", {"form": form, "objeto": objeto})


@requiere_rol(Usuario.Rol.ADMIN)
def bitacora(request):
    eventos = EventoAcceso.objects.filter(empresa=request.empresa).select_related("usuario")[:300]
    return render(request, "accounts/bitacora.html", {"eventos": eventos})
