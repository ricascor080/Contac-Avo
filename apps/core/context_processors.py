"""Variables disponibles en todas las plantillas: menú filtrado por rol y tipo de cambio."""
from django.urls import reverse

from .menu import MENU


def erp(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    path = request.path
    secciones = []
    for titulo, items in MENU:
        visibles = []
        for item in items:
            roles = item.get("roles")
            if roles and not user.tiene_rol(*roles):
                continue
            href = reverse(item["url"]) if "url" in item else reverse("core:modulo", args=[item["slug"]])
            activo = path == href if href == "/" else path.startswith(href)
            visibles.append({**item, "href": href, "activo": activo})
        if visibles:
            secciones.append({"titulo": titulo, "items": visibles})

    from apps.operacion.models import TipoCambio

    return {
        "menu": secciones,
        "empresa": getattr(request, "empresa", None),
        "tipo_cambio": TipoCambio.objects.order_by("-fecha").first(),
    }
