"""Vistas de plataforma (superadmin): empresas/tenants, y páginas de módulos pendientes."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import registrar_evento

from .forms import EmpresaForm, NuevaEmpresaForm
from .menu import MODULOS_PENDIENTES
from .models import Empresa
from .permisos import requiere_empresa, solo_superadmin

Usuario = get_user_model()


@requiere_empresa
def modulo_pendiente(request, slug):
    titulo = MODULOS_PENDIENTES.get(slug)
    if not titulo:
        raise Http404
    return render(request, "core/modulo_pendiente.html", {"titulo": titulo})


@solo_superadmin
def empresas(request):
    lista = Empresa.objects.annotate(
        n_usuarios=Count("usuarios"),
        n_activos=Count("usuarios", filter=Q(usuarios__is_active=True)),
    )
    return render(request, "core/empresas.html", {"empresas": lista})


@solo_superadmin
def empresa_nueva(request):
    form = NuevaEmpresaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            empresa = form.save()
            Usuario.objects.create_user(
                email=form.cleaned_data["admin_email"],
                password=form.cleaned_data["admin_password"],
                nombre=form.cleaned_data["admin_nombre"],
                empresa=empresa,
                rol=Usuario.Rol.ADMIN,
            )
        registrar_evento(request, "empresa_creada", f"{empresa.nombre} (admin {form.cleaned_data['admin_email']})", empresa)
        messages.success(request, f"Empresa «{empresa.nombre}» creada con su administrador.")
        return redirect("core:empresas")
    return render(request, "core/empresa_form.html", {"form": form, "nueva": True})


@solo_superadmin
def empresa_editar(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    form = EmpresaForm(request.POST or None, instance=empresa)
    if request.method == "POST" and form.is_valid():
        form.save()
        registrar_evento(request, "empresa_editada", empresa.nombre, empresa)
        messages.success(request, "Empresa actualizada.")
        return redirect("core:empresas")
    return render(request, "core/empresa_form.html", {"form": form, "empresa_obj": empresa})


@solo_superadmin
@require_POST
def empresa_entrar(request, pk):
    """El superadmin 'entra' a una empresa: a partir de aquí ve sus datos."""
    empresa = get_object_or_404(Empresa, pk=pk)
    request.session["empresa_id"] = empresa.pk
    registrar_evento(request, "superadmin_entra", empresa.nombre, empresa)
    messages.info(request, f"Estás viendo «{empresa.nombre}».")
    return redirect("dashboard:inicio")
