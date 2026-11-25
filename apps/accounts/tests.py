"""Pruebas de login, bloqueo, roles y aislamiento entre empresas.  python manage.py test"""
import io

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import Empresa

from .models import EventoAcceso, Usuario

PWD = "Avocontrol2026!"


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", stdout=io.StringIO())
        cls.uruapan = Empresa.objects.get(slug="valle-uruapan")
        cls.reyes = Empresa.objects.get(slug="empacadora-los-reyes")

    def entrar(self, email):
        return self.client.post(reverse("accounts:login"), {"email": email, "password": PWD})


class LoginTests(Base):
    def test_login_ok_redirige_a_dashboard_y_registra(self):
        r = self.entrar("admin@valleuruapan.mx")
        self.assertRedirects(r, reverse("dashboard:inicio"))
        self.assertTrue(EventoAcceso.objects.filter(tipo="login_ok", email="admin@valleuruapan.mx").exists())

    def test_email_sin_distinguir_mayusculas(self):
        r = self.client.post(reverse("accounts:login"), {"email": "ADMIN@ValleUruapan.mx", "password": PWD})
        self.assertEqual(r.status_code, 302)

    def test_password_incorrecta(self):
        r = self.client.post(reverse("accounts:login"), {"email": "admin@valleuruapan.mx", "password": "mala"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "incorrectos")
        self.assertTrue(EventoAcceso.objects.filter(tipo="login_fallido").exists())

    @override_settings(LOGIN_MAX_INTENTOS=3)
    def test_bloqueo_tras_intentos_fallidos(self):
        for _ in range(3):
            self.client.post(reverse("accounts:login"), {"email": "admin@valleuruapan.mx", "password": "mala"})
        r = self.entrar("admin@valleuruapan.mx")  # aun con la contraseña correcta
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Demasiados intentos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_inactivo_no_entra(self):
        Usuario.objects.filter(email="operador@valleuruapan.mx").update(is_active=False)
        self.assertEqual(self.entrar("operador@valleuruapan.mx").status_code, 200)

    def test_empresa_inactiva_no_entra_y_expulsa_sesion(self):
        self.entrar("admin@losreyes.mx")
        Empresa.objects.filter(pk=self.reyes.pk).update(activa=False)
        r = self.client.get(reverse("dashboard:inicio"))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith(reverse("accounts:login")))
        self.assertEqual(self.entrar("admin@losreyes.mx").status_code, 200)

    def test_next_externo_ignorado(self):
        r = self.client.post(reverse("accounts:login") + "?next=https://malo.com",
                             {"email": "admin@valleuruapan.mx", "password": PWD, "next": "https://malo.com"})
        self.assertRedirects(r, reverse("dashboard:inicio"))

    def test_logout_solo_post(self):
        self.entrar("admin@valleuruapan.mx")
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertRedirects(self.client.get("/"), reverse("accounts:login") + "?next=/")


class RolesYAislamientoTests(Base):
    def test_operador_no_administra_usuarios(self):
        self.entrar("operador@valleuruapan.mx")
        self.assertEqual(self.client.get(reverse("accounts:usuarios")).status_code, 403)

    def test_admin_solo_ve_usuarios_de_su_empresa(self):
        self.entrar("admin@valleuruapan.mx")
        r = self.client.get(reverse("accounts:usuarios"))
        self.assertContains(r, "operador@valleuruapan.mx")
        self.assertNotContains(r, "admin@losreyes.mx")

    def test_admin_no_puede_editar_usuario_de_otra_empresa(self):
        otro = Usuario.objects.get(email="admin@losreyes.mx")
        self.entrar("admin@valleuruapan.mx")
        self.assertEqual(self.client.get(reverse("accounts:usuario_editar", args=[otro.pk])).status_code, 404)

    def test_admin_crea_usuario_en_su_empresa(self):
        self.entrar("admin@valleuruapan.mx")
        self.client.post(reverse("accounts:usuario_nuevo"), {
            "nombre": "Nuevo", "email": "nuevo@valleuruapan.mx", "rol": "consulta", "password": "UnaClaveLarga#2026",
        })
        u = Usuario.objects.get(email="nuevo@valleuruapan.mx")
        self.assertEqual(u.empresa, self.uruapan)
        self.assertEqual(u.rol, "consulta")

    def test_admin_no_puede_crear_superadmin(self):
        self.entrar("admin@valleuruapan.mx")
        r = self.client.post(reverse("accounts:usuario_nuevo"), {
            "nombre": "X", "email": "x@x.mx", "rol": "superadmin", "password": "UnaClaveLarga#2026",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email="x@x.mx").exists())

    def test_admin_no_se_quita_su_rol(self):
        yo = Usuario.objects.get(email="admin@valleuruapan.mx")
        self.entrar(yo.email)
        self.client.post(reverse("accounts:usuario_editar", args=[yo.pk]),
                         {"nombre": yo.nombre, "email": yo.email, "rol": "consulta"})
        yo.refresh_from_db()
        self.assertEqual(yo.rol, "admin")
        self.assertTrue(yo.is_active)

    def test_superadmin_elige_empresa(self):
        r = self.entrar("superadmin@avocontrol.mx")
        self.assertRedirects(r, reverse("core:empresas"))
        self.assertRedirects(self.client.get("/"), reverse("core:empresas"))
        self.client.post(reverse("core:empresa_entrar", args=[self.reyes.pk]))
        self.assertContains(self.client.get("/"), "Empacadora Los Reyes")

    def test_admin_de_empresa_no_ve_plataforma(self):
        self.entrar("admin@valleuruapan.mx")
        self.assertEqual(self.client.get(reverse("core:empresas")).status_code, 403)
