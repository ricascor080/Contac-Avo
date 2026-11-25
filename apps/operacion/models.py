"""
Modelos operativos mínimos para alimentar el dashboard.

Todos heredan de TenantModel (campo `empresa` + `objects.de(empresa)`).
Cantidades en Decimal: kg con 2 decimales, dinero con 2, tipo de cambio con 4.
Cada módulo (Recepción, Corridas, Liquidaciones, ...) ampliará estos modelos.
"""
from decimal import Decimal

from django.db import models

from apps.core.models import TenantModel

KG = {"max_digits": 12, "decimal_places": 2}
MXN = {"max_digits": 14, "decimal_places": 2}


class TipoCambio(models.Model):
    """Tipo de cambio FIX publicado en el DOF (global, no por empresa)."""

    fecha = models.DateField(unique=True)
    valor = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha} {self.valor}"


class Productor(TenantModel):
    class Opinion32D(models.TextChoices):
        POSITIVA = "positiva", "Positiva"
        NEGATIVA = "negativa", "Negativa"
        SIN_CONSULTA = "sin_consulta", "Sin consultar"

    nombre = models.CharField(max_length=200)
    rfc = models.CharField("RFC", max_length=13, blank=True)
    opinion_32d = models.CharField(max_length=15, choices=Opinion32D.choices, default=Opinion32D.SIN_CONSULTA)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "productores"

    def __str__(self):
        return self.nombre


class Recepcion(TenantModel):
    """Lote recibido en báscula."""

    folio = models.CharField(max_length=30)
    fecha = models.DateField()
    productor = models.ForeignKey(Productor, on_delete=models.PROTECT, related_name="recepciones")
    kg_netos = models.DecimalField(**KG)

    class Meta:
        ordering = ["-fecha", "-folio"]
        constraints = [models.UniqueConstraint(fields=["empresa", "folio"], name="recepcion_folio_unico")]

    def __str__(self):
        return self.folio


class Corrida(TenantModel):
    """Corrida de empaque de un lote: cómo se repartió el neto corrido."""

    recepcion = models.ForeignKey(Recepcion, on_delete=models.PROTECT, related_name="corridas")
    fecha = models.DateField()
    exportacion_kg = models.DecimalField(**KG, default=Decimal("0"))
    nacional_kg = models.DecimalField(**KG, default=Decimal("0"))
    canica_kg = models.DecimalField("canica / industria kg", **KG, default=Decimal("0"))
    merma_kg = models.DecimalField(**KG, default=Decimal("0"))

    class Meta:
        ordering = ["-fecha"]

    @property
    def neto_kg(self):
        return self.exportacion_kg + self.nacional_kg + self.canica_kg + self.merma_kg


class CorridaCalibre(models.Model):
    """Desglose del kg de exportación por calibre (32, 36, 40, 48, 60, 70, 84)."""

    corrida = models.ForeignKey(Corrida, on_delete=models.CASCADE, related_name="calibres")
    calibre = models.PositiveSmallIntegerField()
    kg = models.DecimalField(**KG)

    class Meta:
        ordering = ["calibre"]
        constraints = [models.UniqueConstraint(fields=["corrida", "calibre"], name="calibre_unico_por_corrida")]


class Embarque(TenantModel):
    folio = models.CharField(max_length=30)
    fecha = models.DateField()
    cliente = models.CharField(max_length=200)
    contenedores = models.PositiveSmallIntegerField(default=1)
    importe_usd = models.DecimalField(**MXN)

    class Meta:
        ordering = ["-fecha"]


class Liquidacion(TenantModel):
    """Liquidación al productor por un lote."""

    folio = models.CharField(max_length=30)
    fecha = models.DateField()
    recepcion = models.ForeignKey(Recepcion, on_delete=models.PROTECT, related_name="liquidaciones")
    total = models.DecimalField(**MXN)
    pagado = models.DecimalField(**MXN, default=Decimal("0"))
    cfdi_uuid = models.CharField("UUID CFDI de compra / autofactura", max_length=36, blank=True)

    class Meta:
        ordering = ["-fecha"]

    @property
    def saldo(self):
        return self.total - self.pagado


class Compra(TenantModel):
    class Metodo(models.TextChoices):
        PUE = "PUE", "PUE — una exhibición"
        PPD = "PPD", "PPD — parcialidades/diferido"

    class Destino(models.TextChoices):
        EXPORTACION = "exportacion", "Exportación"
        NACIONAL = "nacional", "Nacional"
        GENERAL = "general", "General"

    fecha = models.DateField()
    proveedor = models.CharField(max_length=200)
    concepto = models.CharField(max_length=255)
    subtotal = models.DecimalField(**MXN)
    iva = models.DecimalField(**MXN, default=Decimal("0"))
    metodo_pago = models.CharField(max_length=3, choices=Metodo.choices, default=Metodo.PUE)
    destino = models.CharField(max_length=15, choices=Destino.choices, default=Destino.GENERAL)
    cfdi_uuid = models.CharField(max_length=36, blank=True)
    rep_uuid = models.CharField("UUID complemento de pago (REP)", max_length=36, blank=True)

    class Meta:
        ordering = ["-fecha"]

    @property
    def iva_acreditable(self):
        """El IVA solo se acredita con CFDI; si es PPD, además con su REP (pago efectivamente hecho)."""
        if not self.cfdi_uuid:
            return False
        return self.metodo_pago == self.Metodo.PUE or bool(self.rep_uuid)
