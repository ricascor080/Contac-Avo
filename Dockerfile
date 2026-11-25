# Imagen de producción de AvoControl ERP
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Los estáticos se recopilan en build (no requieren BD ni secretos reales)
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=postgres://x:x@localhost/x \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 app && chmod +x docker/entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
