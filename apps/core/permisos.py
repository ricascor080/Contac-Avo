"""
Decoradores de acceso para vistas.

    @requiere_empresa            -> sesión iniciada + empresa activa resuelta
    @requiere_rol("admin")       -> además, el rol del usuario debe estar en la lista
                                    (el superadmin siempre pasa)
    @solo_superadmin             -> solo administración de plataforma
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def requiere_empresa(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.empresa is None:
            # Solo le pasa al superadmin que aún no eligió empresa
            return redirect("core:empresas")
        return view(request, *args, **kwargs)

    return wrapper


def requiere_rol(*roles):
    def decorator(view):
        @requiere_empresa
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.tiene_rol(*roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def solo_superadmin(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.es_superadmin:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
