# AvoControl ERP

ERP web multiempresa para empaques y comercializadoras de aguacate (Django + PostgreSQL + Docker).

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate && python manage.py cargar_demo
python manage.py runserver        # http://127.0.0.1:8000  ·  admin@valleuruapan.mx / Avocontrol2026!
```

Documentación completa (arquitectura, multiempresa, roles, procesos, despliegue): **[docs/DOCUMENTACION.md](docs/DOCUMENTACION.md)**
