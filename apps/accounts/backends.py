from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Autentica por email (sin distinguir mayúsculas) y exige empresa activa."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        email = email or kwargs.get("username")
        if not email or not password:
            return None
        Usuario = get_user_model()
        try:
            user = Usuario.objects.select_related("empresa").get(email__iexact=email.strip())
        except Usuario.DoesNotExist:
            # Igualar el tiempo de respuesta para no revelar qué emails existen
            Usuario().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        if not super().user_can_authenticate(user):
            return False
        return user.es_superadmin or (user.empresa is not None and user.empresa.activa)
