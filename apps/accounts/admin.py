"""Registro en /django-admin/ (solo superadmin). La operación diaria usa las pantallas del ERP."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.models import Empresa

from .models import EventoAcceso, Usuario


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "razon_social", "rfc", "giro", "temporada", "activa"]
    list_filter = ["activa", "giro"]
    search_fields = ["nombre", "razon_social", "rfc"]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "nombre", "empresa", "rol", "is_active", "last_login"]
    list_filter = ["rol", "is_active", "empresa"]
    search_fields = ["email", "nombre"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Datos", {"fields": ["nombre", "empresa", "rol"]}),
        ("Permisos", {"fields": ["is_active", "is_staff", "is_superuser"]}),
        ("Fechas", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [(None, {"fields": ["email", "nombre", "empresa", "rol", "password1", "password2"]})]


@admin.register(EventoAcceso)
class EventoAccesoAdmin(admin.ModelAdmin):
    list_display = ["fecha", "tipo", "email", "empresa", "ip", "detalle"]
    list_filter = ["tipo", "empresa"]
    search_fields = ["email", "ip", "detalle"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
