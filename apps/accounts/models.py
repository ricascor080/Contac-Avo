"""
Usuarios y bitácora de accesos.

Cada usuario pertenece a UNA empresa (tenant) y tiene UN rol dentro de ella.
El superadmin es el único sin empresa: administra la plataforma.
"""
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("El email es obligatorio")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        """`manage.py createsuperuser` crea un SUPERADMIN de plataforma (sin empresa)."""
        extra.update(rol=Usuario.Rol.SUPERADMIN, empresa=None, is_staff=True, is_superuser=True)
        extra.setdefault("nombre", "Administrador de plataforma")
        return self.create_user(email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    class Rol(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin (plataforma)"
        ADMIN = "admin", "Administrador"
        OPERADOR = "operador", "Operador"
        CONSULTA = "consulta", "Consulta"

    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150)
    empresa = models.ForeignKey(
        "core.Empresa", on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios"
    )
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.OPERADOR)
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField(default=False, help_text="Acceso a /django-admin/")
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["nombre"]
        verbose_name = "usuario"
        constraints = [
            # Superadmin <=> sin empresa. Cualquier otro rol DEBE tener empresa.
            models.CheckConstraint(
                condition=(Q(rol="superadmin", empresa__isnull=True) | (~Q(rol="superadmin") & Q(empresa__isnull=False))),
                name="usuario_rol_empresa_coherente",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} <{self.email}>"

    @property
    def es_superadmin(self):
        return self.rol == self.Rol.SUPERADMIN

    def tiene_rol(self, *roles):
        """True si el usuario tiene alguno de los roles. El superadmin siempre puede."""
        return self.es_superadmin or self.rol in roles

    @property
    def puede_editar(self):
        """Operador y admin capturan; consulta solo lee."""
        return self.tiene_rol(self.Rol.ADMIN, self.Rol.OPERADOR)


class EventoAcceso(models.Model):
    """Bitácora de seguridad: logins, fallos, bloqueos y cambios de usuarios."""

    class Tipo(models.TextChoices):
        LOGIN_OK = "login_ok", "Inicio de sesión"
        LOGIN_FALLIDO = "login_fallido", "Intento fallido"
        LOGIN_BLOQUEADO = "login_bloqueado", "Bloqueado por intentos"
        LOGOUT = "logout", "Cierre de sesión"
        USUARIO_CREADO = "usuario_creado", "Usuario creado"
        USUARIO_EDITADO = "usuario_editado", "Usuario editado"
        PASSWORD_CAMBIADA = "password_cambiada", "Contraseña cambiada"
        EMPRESA_CREADA = "empresa_creada", "Empresa creada"
        EMPRESA_EDITADA = "empresa_editada", "Empresa editada"
        SUPERADMIN_ENTRA = "superadmin_entra", "Superadmin entra a empresa"

    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    email = models.EmailField(blank=True, help_text="Email tecleado (útil en intentos fallidos)")
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    detalle = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-fecha"]
        indexes = [models.Index(fields=["tipo", "email", "fecha"]), models.Index(fields=["tipo", "ip", "fecha"])]

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d %H:%M} {self.tipo} {self.email}"


def ip_cliente(request):
    """IP real. Detrás de Caddy se toma el ÚLTIMO X-Forwarded-For (el que pone el proxy)."""
    if getattr(settings, "USE_X_FORWARDED_FOR", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR")


def registrar_evento(request, tipo, detalle="", empresa=None, usuario=None, email=""):
    user = usuario or (request.user if request.user.is_authenticated else None)
    if empresa is None and user is not None:
        empresa = user.empresa if not user.es_superadmin else getattr(request, "empresa", None)
    return EventoAcceso.objects.create(
        tipo=tipo,
        empresa=empresa,
        usuario=user,
        email=email or (user.email if user else ""),
        ip=ip_cliente(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        detalle=detalle[:255],
    )
