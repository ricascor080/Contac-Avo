"""
Definición del menú lateral. Para agregar un módulo nuevo:
  1. Agrega aquí su entrada (url = nombre de ruta de Django, o slug = módulo en construcción).
  2. Cuando el módulo exista, cambia `slug` por `url`.
`roles` vacío = visible para todos los roles.
"""

ADMIN = ("admin",)

MENU = [
    ("General", [
        {"label": "Dashboard", "icon": "dashboard", "url": "dashboard:inicio"},
        {"label": "Configuración de giro", "icon": "sliders", "slug": "configuracion-giro", "roles": ADMIN},
    ]),
    ("Catálogos", [
        {"label": "Productores", "icon": "users", "slug": "productores"},
        {"label": "Anticipos y habilitaciones", "icon": "banknote", "slug": "anticipos"},
        {"label": "Huertas", "icon": "sprout", "slug": "huertas"},
        {"label": "Clientes", "icon": "user", "slug": "clientes"},
        {"label": "Materiales de empaque", "icon": "package", "slug": "materiales"},
    ]),
    ("Operación", [
        {"label": "Recepción en báscula", "icon": "scale", "slug": "recepcion"},
        {"label": "Corridas de empaque", "icon": "box", "slug": "corridas"},
        {"label": "Liquidaciones", "icon": "dollar", "slug": "liquidaciones"},
        {"label": "Cámaras y tarimas", "icon": "snowflake", "slug": "camaras"},
        {"label": "Embarques", "icon": "ship", "slug": "embarques"},
        {"label": "Compras y gastos", "icon": "receipt", "slug": "compras"},
    ]),
    ("Fiscal y costos", [
        {"label": "Costeo por embarque", "icon": "calculator", "slug": "costeo"},
        {"label": "Cédula fiscal export.", "icon": "clipboard", "slug": "cedula-fiscal"},
    ]),
    ("Administración", [
        {"label": "Usuarios", "icon": "shield", "url": "accounts:usuarios", "roles": ADMIN},
        {"label": "Bitácora de accesos", "icon": "history", "url": "accounts:bitacora", "roles": ADMIN},
    ]),
]

# Módulos aún no construidos: slug -> título (se usa en la página "en construcción")
MODULOS_PENDIENTES = {
    item["slug"]: item["label"]
    for _, items in MENU
    for item in items
    if "slug" in item
}
