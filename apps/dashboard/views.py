from django.shortcuts import render

from apps.core.permisos import requiere_empresa

from .servicios import indicadores


@requiere_empresa
def inicio(request):
    return render(request, "dashboard/inicio.html", {"k": indicadores(request.empresa)})
