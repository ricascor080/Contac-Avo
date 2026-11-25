"""
Bloqueo de login por fuerza bruta.

- Por email: LOGIN_MAX_INTENTOS fallos dentro de LOGIN_VENTANA_MINUTOS (contados
  desde el último login exitoso de ese email) bloquean ese email.
- Por IP: 4x ese límite (una oficina puede compartir IP entre varios usuarios).
El bloqueo se libera solo al pasar la ventana.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import EventoAcceso

T = EventoAcceso.Tipo


def esta_bloqueado(email, ip):
    ahora = timezone.now()
    desde = ahora - timedelta(minutes=settings.LOGIN_VENTANA_MINUTOS)
    maximo = settings.LOGIN_MAX_INTENTOS

    if email:
        ultimo_ok = (
            EventoAcceso.objects.filter(tipo=T.LOGIN_OK, email__iexact=email, fecha__gte=desde)
            .values_list("fecha", flat=True)
            .first()
        )
        fallos_email = EventoAcceso.objects.filter(
            tipo=T.LOGIN_FALLIDO, email__iexact=email, fecha__gte=max(desde, ultimo_ok or desde)
        ).count()
        if fallos_email >= maximo:
            return True

    if ip:
        fallos_ip = EventoAcceso.objects.filter(tipo=T.LOGIN_FALLIDO, ip=ip, fecha__gte=desde).count()
        if fallos_ip >= maximo * 4:
            return True

    return False
