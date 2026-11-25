from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("modulo/<slug:slug>/", views.modulo_pendiente, name="modulo"),
    path("plataforma/empresas/", views.empresas, name="empresas"),
    path("plataforma/empresas/nueva/", views.empresa_nueva, name="empresa_nueva"),
    path("plataforma/empresas/<int:pk>/", views.empresa_editar, name="empresa_editar"),
    path("plataforma/empresas/<int:pk>/entrar/", views.empresa_entrar, name="empresa_entrar"),
]
