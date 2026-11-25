"""
Resuelve la empresa activa de cada petición y la deja en `request.empresa`.

- Usuario normal  -> su propia empresa (no puede cambiarla).
- Superadmin      -> la empresa que eligió en "Empresas > Entrar"
                     (guardada en la sesión como `empresa_id`).
Si la empresa de un usuario normal se desactiva, se cierra su sesión.
"""
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

from .models import Empresa


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa = None
        user = request.user

        if user.is_authenticated:
            if user.es_superadmin:
                empresa_id = request.session.get("empresa_id")
                if empresa_id:
                    request.empresa = Empresa.objects.filter(pk=empresa_id).first()
            else:
                empresa = user.empresa
                if empresa is None or not empresa.activa:
                    logout(request)
                    messages.error(request, "Tu empresa está desactivada. Contacta al administrador.")
                    return redirect("accounts:login")
                request.empresa = empresa

        return self.get_response(request)
