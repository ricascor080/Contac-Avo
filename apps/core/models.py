"""
Modelo de tenant (Empresa) y base para todos los modelos multi-empresa.

REGLA DE ORO: todo modelo con datos de una empresa hereda de TenantModel y se
consulta SIEMPRE con `Modelo.objects.de(request.empresa)`. Nunca usar
`Modelo.objects.all()` en una vista.
"""
from django.db import models
from django.utils.text import slugify


class Empresa(models.Model):
    """Un tenant: un empaque, bodega o comercializadora que usa el ERP."""

    class Giro(models.TextChoices):
        EMPAQUE = "empaque", "Empaque de exportación"
        BODEGA = "bodega", "Bodega / centro de acopio"
        COMERCIALIZADORA = "comercializadora", "Comercializadora"

    nombre = models.CharField("nombre corto", max_length=120)
    razon_social = models.CharField(max_length=200)
    rfc = models.CharField("RFC", max_length=13, blank=True)
    slug = models.SlugField(max_length=60, unique=True)
    giro = models.CharField(max_length=20, choices=Giro.choices, default=Giro.EMPAQUE)
    temporada = models.PositiveIntegerField(help_text="Año de la temporada activa")
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "empresa"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nombre)[:50] or "empresa"
            slug, n = base, 2
            while Empresa.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)


class TenantQuerySet(models.QuerySet):
    def de(self, empresa):
        """Filtra por empresa. Sin empresa no devuelve nada (falla cerrado)."""
        if empresa is None:
            return self.none()
        return self.filter(empresa=empresa)


class TenantModel(models.Model):
    """Base abstracta: agrega `empresa` y el manager con `.de(empresa)`."""

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="+")
    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True
