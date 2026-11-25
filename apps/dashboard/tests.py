from decimal import Decimal as D

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Empresa

from .servicios import indicadores


class IndicadoresTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import io
        call_command("cargar_demo", stdout=io.StringIO())

    def test_indicadores_demo_uruapan(self):
        k = indicadores(Empresa.objects.get(slug="valle-uruapan"), hoy=timezone.localdate())
        self.assertEqual(k["kg_recibidos"], D("29690.00"))
        self.assertEqual(k["kg_exportacion"], D("17917.20"))
        self.assertEqual(k["neto"], D("23240.00"))
        self.assertEqual(round(k["aprovechamiento"], 2), D("77.10"))
        self.assertEqual(k["saldo_liquidar"], D("329325.40"))
        self.assertEqual(k["lotes_sin_liquidar"], 1)
        self.assertEqual(k["contenedores_mes"], 1)
        # Solo la compra PUE con CFDI acredita IVA; la PPD sin REP y la sin CFDI no
        self.assertEqual(k["iva_export"], D("7600.00"))
        self.assertEqual(len(k["alertas"]), 5)

    def test_empresas_no_se_mezclan(self):
        k = indicadores(Empresa.objects.get(slug="empacadora-los-reyes"))
        self.assertEqual(k["kg_recibidos"], D("5200.00"))
        self.assertEqual([a["tag"] for a in k["alertas"]], ["Lote sin liquidar"])

    def test_sin_empresa_no_devuelve_datos(self):
        self.assertEqual(indicadores(None)["kg_recibidos"], D("0"))
