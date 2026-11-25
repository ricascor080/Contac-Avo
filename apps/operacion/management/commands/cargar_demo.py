"""
Carga datos de demostración:  python manage.py cargar_demo [--reset]

Crea un superadmin, dos empresas (para probar el aislamiento entre tenants),
sus usuarios y operación de ejemplo del mes en curso. Es idempotente: si ya
existen, no duplica. Con --reset borra los datos operativos demo y los recrea.
"""
from datetime import timedelta
from decimal import Decimal as D

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.core.models import Empresa
from apps.operacion.models import (
    Compra, Corrida, CorridaCalibre, Embarque, Liquidacion, Productor, Recepcion, TipoCambio,
)

PASSWORD_DEMO = "Avocontrol2026!"
R = Usuario.Rol

EMPRESAS = [
    {
        "slug": "valle-uruapan",
        "nombre": "Aguacates Selectos del Valle de Uruapan",
        "razon_social": "Aguacates Selectos del Valle de Uruapan, S.A. de C.V.",
        "rfc": "ASV150312AB1",
        "usuarios": [
            ("admin@valleuruapan.mx", "José Toledo Bernal", R.ADMIN),
            ("operador@valleuruapan.mx", "Lucía Pérez Campos", R.OPERADOR),
            ("consulta@valleuruapan.mx", "Contador Externo", R.CONSULTA),
        ],
    },
    {
        "slug": "empacadora-los-reyes",
        "nombre": "Empacadora Los Reyes",
        "razon_social": "Empacadora Los Reyes, S. de R.L. de C.V.",
        "rfc": "ELR180905QX2",
        "usuarios": [("admin@losreyes.mx", "Andrea Villaseñor", R.ADMIN)],
    },
]


class Command(BaseCommand):
    help = "Carga empresas, usuarios y operación de demostración."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Borra y recrea la operación demo")

    @transaction.atomic
    def handle(self, *args, reset=False, **opts):
        hoy = timezone.localdate()
        TipoCambio.objects.update_or_create(fecha=hoy.replace(day=min(11, hoy.day)), defaults={"valor": D("18.3500")})

        if not Usuario.objects.filter(email="superadmin@avocontrol.mx").exists():
            Usuario.objects.create_superuser("superadmin@avocontrol.mx", PASSWORD_DEMO)

        for datos in EMPRESAS:
            empresa, creada = Empresa.objects.get_or_create(
                slug=datos["slug"],
                defaults={"nombre": datos["nombre"], "razon_social": datos["razon_social"],
                          "rfc": datos["rfc"], "temporada": hoy.year},
            )
            for email, nombre, rol in datos["usuarios"]:
                if not Usuario.objects.filter(email=email).exists():
                    Usuario.objects.create_user(email, PASSWORD_DEMO, nombre=nombre, empresa=empresa, rol=rol)

            if reset:
                self._borrar_operacion(empresa)
            if reset or creada or not Recepcion.objects.de(empresa).exists():
                if datos["slug"] == "valle-uruapan":
                    self._operacion_uruapan(empresa, hoy)
                else:
                    self._operacion_los_reyes(empresa, hoy)

        self.stdout.write(self.style.SUCCESS("Datos demo listos."))
        self.stdout.write(f"  Contraseña de todos los usuarios demo: {PASSWORD_DEMO}")
        self.stdout.write("  superadmin@avocontrol.mx · admin@valleuruapan.mx · operador@valleuruapan.mx")
        self.stdout.write("  consulta@valleuruapan.mx · admin@losreyes.mx")

    def _borrar_operacion(self, e):
        for modelo in (Liquidacion, Embarque, Compra):
            modelo.objects.de(e).delete()
        Corrida.objects.de(e).delete()
        Recepcion.objects.de(e).delete()
        Productor.objects.de(e).delete()

    def _operacion_uruapan(self, e, hoy):
        dia = lambda n: hoy.replace(day=1) + timedelta(days=n - 1)  # noqa: E731
        P = Productor.Opinion32D
        p1 = Productor.objects.create(empresa=e, nombre="Rancho El Durazno, S.P.R.", rfc="RDU090101AA1", opinion_32d=P.POSITIVA)
        p2 = Productor.objects.create(empresa=e, nombre="Huertas Tancítaro S.P.R. de R.L.", rfc="HTA110505BB2", opinion_32d=P.POSITIVA)
        p3 = Productor.objects.create(empresa=e, nombre="María Guadalupe Ruiz Alcalá", rfc="RUAG800212CC3", opinion_32d=P.NEGATIVA)

        a = e.temporada
        r1 = Recepcion.objects.create(empresa=e, folio=f"LOT-{a}-001", fecha=dia(3), productor=p1, kg_netos=D("8900.00"))
        r2 = Recepcion.objects.create(empresa=e, folio=f"LOT-{a}-002", fecha=dia(5), productor=p2, kg_netos=D("14340.00"))
        Recepcion.objects.create(empresa=e, folio=f"LOT-{a}-003", fecha=dia(9), productor=p3, kg_netos=D("6450.00"))

        c1 = Corrida.objects.create(empresa=e, recepcion=r1, fecha=dia(4), exportacion_kg=D("6860.00"),
                                    nacional_kg=D("1260.00"), canica_kg=D("560.00"), merma_kg=D("220.00"))
        c2 = Corrida.objects.create(empresa=e, recepcion=r2, fecha=dia(6), exportacion_kg=D("11057.20"),
                                    nacional_kg=D("2020.00"), canica_kg=D("920.00"), merma_kg=D("342.80"))
        for corrida, reparto in (
            (c1, {32: "300", 36: "600", 40: "1100", 48: "2100", 60: "1680", 70: "760", 84: "320"}),
            (c2, {32: "480", 36: "950", 40: "1750", 48: "3380", 60: "2720", 70: "1220", 84: "557.20"}),
        ):
            CorridaCalibre.objects.bulk_create(
                [CorridaCalibre(corrida=corrida, calibre=k, kg=D(v)) for k, v in reparto.items()]
            )

        Embarque.objects.create(empresa=e, folio=f"EMB-{a}-001", fecha=dia(11), cliente="Fresh Harvest Imports LLC",
                                contenedores=1, importe_usd=D("44375.00"))

        Liquidacion.objects.create(empresa=e, folio=f"LIQ-{a}-001", fecha=dia(7), recepcion=r1, total=D("201250.00"),
                                   pagado=D("201250.00"), cfdi_uuid="6F1C2A1E-3B4D-4E5F-8A9B-1C2D3E4F5A6B")
        Liquidacion.objects.create(empresa=e, folio=f"LIQ-{a}-002", fecha=dia(10), recepcion=r2, total=D("329325.40"))

        M, Dst = Compra.Metodo, Compra.Destino
        Compra.objects.create(empresa=e, fecha=dia(2), proveedor="Tarimas y Maderas de Uruapan, S.A. de C.V.",
                              concepto="Tarimas tratadas NIMF-15", subtotal=D("47500.00"), iva=D("7600.00"),
                              metodo_pago=M.PUE, destino=Dst.EXPORTACION, cfdi_uuid="A1B2C3D4-0000-4000-8000-000000000001")
        Compra.objects.create(empresa=e, fecha=dia(8), proveedor="Verificadora Fitosanitaria del Occidente, S.C.",
                              concepto="Inspección fitosanitaria y certificado", subtotal=D("7000.00"), iva=D("1120.00"),
                              metodo_pago=M.PUE, destino=Dst.EXPORTACION)
        Compra.objects.create(empresa=e, fecha=dia(8), proveedor="Empaques Corrugados de Michoacán, S.A. de C.V.",
                              concepto="6,000 cajas de cartón 25 lb", subtotal=D("90000.00"), iva=D("14400.00"),
                              metodo_pago=M.PPD, destino=Dst.EXPORTACION, cfdi_uuid="A1B2C3D4-0000-4000-8000-000000000002")

    def _operacion_los_reyes(self, e, hoy):
        p = Productor.objects.create(empresa=e, nombre="Huerta La Cañada", opinion_32d=Productor.Opinion32D.POSITIVA)
        r = Recepcion.objects.create(empresa=e, folio=f"LR-{e.temporada}-001", fecha=hoy.replace(day=1), productor=p,
                                     kg_netos=D("5200.00"))
        c = Corrida.objects.create(empresa=e, recepcion=r, fecha=hoy.replace(day=1), exportacion_kg=D("4100.00"),
                                   nacional_kg=D("700.00"), canica_kg=D("300.00"), merma_kg=D("100.00"))
        CorridaCalibre.objects.bulk_create([
            CorridaCalibre(corrida=c, calibre=k, kg=D(v)) for k, v in {48: "1800", 60: "1500", 70: "800"}.items()
        ])
