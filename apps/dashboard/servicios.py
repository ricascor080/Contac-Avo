"""
Cálculo de indicadores del dashboard ejecutivo.

Todo se filtra por la empresa recibida: esta función NUNCA debe llamarse sin empresa.
Separado de la vista para poder probarlo y reutilizarlo (reportes, API, etc.).
"""
import math
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.urls import reverse
from django.utils import timezone

from apps.operacion.models import (
    Compra, Corrida, CorridaCalibre, Embarque, Liquidacion, Productor, Recepcion,
)

CERO = Decimal("0")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _pct(parte, total):
    return (parte / total * 100) if total else CERO


def _suma(qs, campo):
    return qs.aggregate(v=Sum(campo))["v"] or CERO


def indicadores(empresa, hoy=None):
    hoy = hoy or timezone.localdate()

    recepciones = Recepcion.objects.de(empresa)
    corridas = Corrida.objects.de(empresa)

    # --- Recepción vs. empaque ---
    kg_recibidos = _suma(recepciones, "kg_netos")
    masa = corridas.aggregate(
        exportacion=Sum("exportacion_kg"), nacional=Sum("nacional_kg"),
        canica=Sum("canica_kg"), merma=Sum("merma_kg"),
    )
    masa = {k: v or CERO for k, v in masa.items()}
    neto = sum(masa.values(), CERO)
    aprovechamiento = _pct(masa["exportacion"], neto)

    balance = [
        {"clave": "exportacion", "label": "Exportación", "kg": masa["exportacion"]},
        {"clave": "nacional", "label": "Nacional", "kg": masa["nacional"]},
        {"clave": "canica", "label": "Canica / industria", "kg": masa["canica"]},
        {"clave": "merma", "label": "Merma", "kg": masa["merma"]},
    ]
    for b in balance:
        b["pct"] = _pct(b["kg"], neto)

    # --- Aprovechamiento por calibre (% del neto corrido) ---
    calibres = list(
        CorridaCalibre.objects.filter(corrida__empresa=empresa)
        .values("calibre").annotate(kg=Sum("kg")).order_by("calibre")
    )
    max_pct = max((float(_pct(c["kg"], neto)) for c in calibres), default=0)
    paso = max(1, math.ceil(max_pct / 4))  # 4 divisiones "redondas" en el eje Y
    tope = paso * 4
    for c in calibres:
        c["pct"] = _pct(c["kg"], neto)
        c["altura"] = float(c["pct"]) / tope * 100 if tope else 0
    eje_y = [paso * i for i in range(4, -1, -1)]

    # --- Embarques del mes ---
    del_mes = Embarque.objects.de(empresa).filter(fecha__year=hoy.year, fecha__month=hoy.month)
    emb = del_mes.aggregate(contenedores=Sum("contenedores"), usd=Sum("importe_usd"))

    # --- Liquidaciones ---
    liq = Liquidacion.objects.de(empresa)
    pendientes = liq.filter(pagado__lt=F("total"))
    saldo = pendientes.aggregate(v=Sum(F("total") - F("pagado")))["v"] or CERO
    lotes_sin_liquidar = recepciones.annotate(n=Count("liquidaciones")).filter(n=0)

    # --- IVA acreditable (con CFDI, y si es PPD, con REP) ---
    compras = Compra.objects.de(empresa)
    acreditable = Q(cfdi_uuid__gt="") & (Q(metodo_pago=Compra.Metodo.PUE) | Q(rep_uuid__gt=""))
    iva_export = _suma(compras.filter(acreditable, destino=Compra.Destino.EXPORTACION), "iva")
    iva_total = _suma(compras.filter(acreditable), "iva")

    return {
        "hoy": hoy,
        "mes_nombre": MESES[hoy.month - 1],
        "kg_recibidos": kg_recibidos,
        "kg_exportacion": masa["exportacion"],
        "neto": neto,
        "aprovechamiento": aprovechamiento,
        "balance": balance,
        "calibres": calibres,
        "eje_y": eje_y,
        "contenedores_mes": emb["contenedores"] or 0,
        "usd_mes": emb["usd"] or CERO,
        "saldo_liquidar": saldo,
        "liquidaciones_pendientes": pendientes.count(),
        "lotes_sin_liquidar": lotes_sin_liquidar.count(),
        "iva_export": iva_export,
        "iva_total": iva_total,
        "alertas": alertas(empresa, lotes_sin_liquidar, liq, compras),
    }


def alertas(empresa, lotes_sin_liquidar, liquidaciones, compras):
    """Pendientes de control interno/fiscal. tono: 'warn' (ámbar) o 'crit' (rojo)."""
    url = lambda slug: reverse("core:modulo", args=[slug])  # noqa: E731
    out = []

    for r in lotes_sin_liquidar.select_related("productor"):
        out.append({"tag": "Lote sin liquidar", "tono": "warn", "url": url("liquidaciones"),
                    "texto": f"{r.folio} · {r.productor.nombre} · {r.kg_netos:,.2f} kg"})

    for l in liquidaciones.filter(cfdi_uuid=""):
        out.append({"tag": "Liquidación sin CFDI", "tono": "crit", "url": url("liquidaciones"),
                    "texto": f"{l.folio} sin CFDI de compra / autofactura"})

    for c in compras.filter(cfdi_uuid=""):
        out.append({"tag": "Compra sin CFDI", "tono": "crit", "url": url("compras"),
                    "texto": f"{c.proveedor} · {c.concepto}"})

    for c in compras.filter(metodo_pago=Compra.Metodo.PPD, rep_uuid="").exclude(cfdi_uuid=""):
        out.append({"tag": "Compra PPD sin REP", "tono": "crit", "url": url("compras"),
                    "texto": f"{c.proveedor} · {c.concepto}"})

    for p in Productor.objects.de(empresa).filter(opinion_32d=Productor.Opinion32D.NEGATIVA):
        out.append({"tag": "Opinión 32-D", "tono": "crit", "url": url("productores"),
                    "texto": f"{p.nombre}: Negativa"})

    return out
