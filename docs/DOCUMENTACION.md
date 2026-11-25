# AvoControl ERP — Documentación

> ERP web multiempresa para empaques, bodegas y comercializadoras de aguacate:
> de la báscula al contenedor y a la cédula fiscal.

Este documento se actualiza **con cada módulo nuevo**. Cada módulo agrega su sección en
[§9 Módulos](#9-módulos) siguiendo la [plantilla](#plantilla-para-documentar-un-módulo).

| | |
|---|---|
| **Versión** | 0.1 — Base: login, usuarios multiempresa y dashboard ejecutivo |
| **Última actualización** | 24/11/2026 |
| **Stack** | Django 5.1 · PostgreSQL 16 · HTML + CSS propio · Docker + Caddy |

---

## Índice

1. [Qué es y para quién](#1-qué-es-y-para-quién)
2. [Arranque rápido (desarrollo)](#2-arranque-rápido-desarrollo)
3. [Arquitectura](#3-arquitectura)
4. [Multiempresa (tenants)](#4-multiempresa-tenants)
5. [Usuarios, roles y permisos](#5-usuarios-roles-y-permisos)
6. [Seguridad del login](#6-seguridad-del-login)
7. [Guía de diseño (UI)](#7-guía-de-diseño-ui)
8. [Dashboard ejecutivo: cómo se calcula cada número](#8-dashboard-ejecutivo-cómo-se-calcula-cada-número)
9. [Módulos](#9-módulos)
10. [Despliegue a producción (Docker)](#10-despliegue-a-producción-docker)
11. [Pruebas](#11-pruebas)
12. [Convenciones para desarrollar](#12-convenciones-para-desarrollar)
13. [Hoja de ruta](#13-hoja-de-ruta)
14. [Glosario](#14-glosario)
15. [Bitácora de cambios](#15-bitácora-de-cambios)

---

## 1. Qué es y para quién

AvoControl concentra la operación de un empaque de aguacate de exportación:

- **Recepción** de fruta por lote y productor (báscula).
- **Corridas de empaque**: cuánto de cada lote salió a exportación, nacional, canica/industria y merma, y por calibre.
- **Liquidaciones** a productores, anticipos y habilitaciones.
- **Embarques** (contenedores) y ventas en USD.
- **Compras y gastos** con control de CFDI, REP e IVA acreditable.
- **Fiscal**: opinión de cumplimiento 32-D de productores, cédula fiscal de exportación, costeo por embarque.

Una sola instalación atiende a **varias empresas** (tenants). Cada empresa ve solo sus datos.

**Tipos de usuario**

| Quién | Qué hace en el sistema |
|---|---|
| Superadmin (nosotros, el proveedor) | Da de alta empresas y su primer administrador; puede "entrar" a cualquier empresa para soporte. |
| Administrador de la empresa | Todo dentro de su empresa, incluida la gestión de usuarios y la bitácora. |
| Operador | Captura y consulta la operación (báscula, corridas, embarques...). |
| Consulta | Solo lectura (dirección, contador externo, auditor). |

---

## 2. Arranque rápido (desarrollo)

Requisitos: Python 3.11+ (en desarrollo no se necesita Docker ni PostgreSQL; se usa SQLite).

```bash
# 1. Entorno virtual e instalación
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Base de datos y datos de demostración
python manage.py migrate
python manage.py cargar_demo      # --reset para recrear la operación demo

# 3. Levantar el servidor
python manage.py runserver
```

Abrir **http://127.0.0.1:8000** → redirige al login.

**Usuarios demo** (contraseña de todos: `Avocontrol2026!`)

| Email | Rol | Empresa |
|---|---|---|
| `superadmin@avocontrol.mx` | Superadmin | — (elige empresa) |
| `admin@valleuruapan.mx` | Administrador | Aguacates Selectos del Valle de Uruapan |
| `operador@valleuruapan.mx` | Operador | Aguacates Selectos del Valle de Uruapan |
| `consulta@valleuruapan.mx` | Consulta | Aguacates Selectos del Valle de Uruapan |
| `admin@losreyes.mx` | Administrador | Empacadora Los Reyes |

> La segunda empresa (Los Reyes) existe para **comprobar el aislamiento**: entra con cada admin y verás datos distintos.

**Comandos útiles**

| Comando | Para qué |
|---|---|
| `python manage.py test` | Corre las pruebas automáticas |
| `python manage.py createsuperuser` | Crea un superadmin de plataforma |
| `python manage.py makemigrations` / `migrate` | Cambios al modelo de datos |
| `python manage.py cargar_demo --reset` | Reinicia los datos demo |

Panel técnico de Django (solo superadmin): `/django-admin/`.

---

## 3. Arquitectura

### 3.1 Vista general

```
Navegador ──HTTPS──▶ Caddy (TLS, gzip) ──▶ Gunicorn + Django ──▶ PostgreSQL
                                             │
                                             ├─ TenantMiddleware → request.empresa
                                             ├─ Vistas (decoradores de permiso)
                                             ├─ Servicios (cálculos, siempre por empresa)
                                             └─ Plantillas HTML + app.css
```

Es una **aplicación renderizada en servidor** (Django templates). No hay frontend separado: una
sola base de código, un solo despliegue. Para interacciones más ricas (filtros, modales,
recargas parciales) se agregará **HTMX** cuando un módulo lo necesite.

### 3.2 Estructura de carpetas

```
config/
  settings/base.py      Configuración común (lee variables de entorno)
  settings/dev.py       Desarrollo: DEBUG, SQLite
  settings/prod.py      Producción: PostgreSQL obligatorio, cookies seguras, HSTS
  urls.py               Rutas raíz
apps/
  core/                 Empresas (tenants), middleware, permisos, menú, íconos y filtros
    models.py           Empresa, TenantModel, TenantQuerySet.de()
    middleware.py       Resuelve request.empresa
    permisos.py         @requiere_empresa, @requiere_rol, @solo_superadmin
    menu.py             Menú lateral (agregar módulos aquí)
    templatetags/ui.py  {% icon %}, |num, |money, |pct, |iniciales
    views.py            Empresas (superadmin) y página "módulo en construcción"
  accounts/             Usuarios, login, bloqueo por intentos, bitácora
    models.py           Usuario, EventoAcceso, registrar_evento()
    backends.py         Autenticación por email + empresa activa
    seguridad.py        Reglas de bloqueo de login
  operacion/            Modelos operativos (productores, recepciones, corridas, ...)
    management/commands/cargar_demo.py
  dashboard/            Dashboard ejecutivo
    servicios.py        Cálculo de indicadores (sin HTML)
templates/              HTML (base.html = layout con sidebar)
static/css/app.css      Hoja de estilos única con tokens de diseño
static/js/app.js        Comportamiento mínimo (menú, mostrar contraseña)
docker/                 entrypoint.sh, Caddyfile
docs/                   Esta documentación
```

### 3.3 Flujo de una petición

1. `SessionMiddleware` + `AuthenticationMiddleware` → identifican al usuario.
2. `TenantMiddleware` → pone `request.empresa` (ver §4).
3. Decorador de la vista (`@requiere_empresa` / `@requiere_rol`) → valida acceso.
4. La vista llama a un **servicio** que consulta con `.de(request.empresa)`.
5. Se renderiza la plantilla, que extiende `base.html`.

---

## 4. Multiempresa (tenants)

### 4.1 Modelo elegido: una base de datos, columna `empresa`

Todas las tablas con datos de negocio tienen una columna `empresa_id`. Se eligió sobre "un
esquema por empresa" porque es más simple de migrar, respaldar y reportar. Si un cliente
llegara a exigir aislamiento físico, se puede migrar a `django-tenants` (esquemas de
PostgreSQL) sin cambiar las pantallas.

### 4.2 Cómo se resuelve la empresa activa

| Usuario | `request.empresa` |
|---|---|
| Rol admin / operador / consulta | Siempre **su** empresa. No la puede cambiar. |
| Superadmin | La que eligió en *Empresas → Entrar* (guardada en sesión). Si no ha elegido, se le manda a la lista de empresas. |
| Empresa desactivada | Se cierra la sesión del usuario y ya no puede volver a entrar. |

### 4.3 La regla de oro

> **Todo modelo de negocio hereda de `TenantModel` y se consulta con `.de(request.empresa)`.**
> Nunca `Modelo.objects.all()` en una vista.

```python
from apps.core.models import TenantModel

class Huerta(TenantModel):          # agrega el campo `empresa` automáticamente
    nombre = models.CharField(max_length=120)

# En la vista:
huertas = Huerta.objects.de(request.empresa)
huerta  = get_object_or_404(Huerta.objects.de(request.empresa), pk=pk)   # nunca get(pk=pk) a secas
```

- `.de(None)` devuelve vacío: si algo falla, **falla cerrado** (no muestra datos de nadie).
- Al **crear**, asignar `empresa=request.empresa` en la vista; nunca tomarla del formulario.
- Folios únicos **por empresa**: `UniqueConstraint(fields=["empresa", "folio"])`.

---

## 5. Usuarios, roles y permisos

### 5.1 Modelo `Usuario`

- Inicia sesión con **email** (sin distinguir mayúsculas). No hay "username".
- Pertenece a **una** empresa y tiene **un** rol.
- Restricción en base de datos: *superadmin ⇔ sin empresa*; cualquier otro rol **debe** tener empresa.

### 5.2 Matriz de permisos actual

| Acción | Superadmin | Admin | Operador | Consulta |
|---|:-:|:-:|:-:|:-:|
| Ver dashboard | ✔ (empresa elegida) | ✔ | ✔ | ✔ |
| Ver módulos de operación | ✔ | ✔ | ✔ | ✔ |
| Capturar / editar operación *(próximos módulos)* | ✔ | ✔ | ✔ | — |
| Configuración de giro | ✔ | ✔ | — | — |
| Usuarios de la empresa | ✔ | ✔ | — | — |
| Bitácora de accesos | ✔ | ✔ | — | — |
| Empresas (alta, edición, entrar) | ✔ | — | — | — |

### 5.3 Proceso: dar de alta una empresa nueva

1. El superadmin entra a **Empresas → Nueva empresa**.
2. Captura datos de la empresa + nombre, email y contraseña inicial de su **primer administrador**.
3. Se crean ambos en una sola transacción (si algo falla, no se crea nada).
4. Se le entregan las credenciales al administrador por un medio seguro.
5. El administrador entra y da de alta a su equipo en **Usuarios**.

### 5.4 Proceso: alta de un usuario (lo hace el admin de la empresa)

1. **Usuarios → Nuevo usuario**: nombre, email, rol y contraseña inicial (mín. 10 caracteres, no común, no solo números).
2. El usuario queda ligado automáticamente a la empresa del admin (no se puede elegir otra).
3. El admin solo puede asignar *Administrador, Operador o Consulta* (nunca superadmin).
4. Se registra en la bitácora (`Usuario creado`).

### 5.5 Proceso: baja, cambio de rol, contraseña olvidada

- **Baja**: editar el usuario y desmarcar *Activo*. No se borra (se conserva su historial).
- **Cambio de rol**: editar el usuario. Un admin **no puede** cambiar su propio rol ni desactivarse (evita quedarse sin administradores).
- **Contraseña olvidada**: el admin edita al usuario y escribe una contraseña nueva. Cada usuario puede cambiar la suya en **Mi cuenta** (clic en su email, abajo del menú).
  *(Recuperación por email: pendiente, requiere configurar servidor SMTP.)*

### 5.6 Cómo proteger una vista nueva

```python
from apps.core.permisos import requiere_empresa, requiere_rol
from apps.accounts.models import Usuario

@requiere_empresa                                   # cualquier usuario con empresa
def lista_huertas(request): ...

@requiere_rol(Usuario.Rol.ADMIN, Usuario.Rol.OPERADOR)   # solo quien captura
def nueva_huerta(request): ...
```

En plantillas: `{% if user.puede_editar %}` para mostrar/ocultar botones de captura.

---

## 6. Seguridad del login

| Medida | Detalle |
|---|---|
| Contraseñas | Hash PBKDF2 de Django (nunca se guardan en claro). Mínimo 10 caracteres + validadores. |
| Bloqueo por intentos | 5 fallos en 15 min para un email ⇒ bloqueado 15 min (aun con la contraseña correcta). Por IP: 20 fallos. Configurable con `LOGIN_MAX_INTENTOS` y `LOGIN_VENTANA_MINUTOS`. |
| Mensaje genérico | "Email o contraseña incorrectos" — no revela si el email existe. El tiempo de respuesta es igual exista o no. |
| CSRF | Todos los formularios llevan token. Cerrar sesión solo por POST. |
| Sesión | "Mantener sesión iniciada" = 12 h; sin marcar = expira al cerrar el navegador. Cookie `HttpOnly`, `SameSite=Lax`, y `Secure` en producción. |
| Redirección segura | El parámetro `next` solo acepta rutas del mismo sitio. |
| Bitácora | Cada login, fallo, bloqueo, logout, alta/edición de usuario y entrada de superadmin queda en **Administración → Bitácora de accesos** con fecha, IP y navegador. |
| HTTPS | Caddy obtiene el certificado automáticamente; Django fuerza HTTPS y HSTS en producción. |

---

## 7. Guía de diseño (UI)

El diseño sigue la referencia aprobada del *Dashboard ejecutivo*. **Toda medida y color está en
variables CSS al inicio de `static/css/app.css`**; no escribir colores sueltos.

### 7.1 Colores

| Token | Valor | Uso |
|---|---|---|
| `--green-950` | `#11281a` | Fondo del menú lateral y panel del login |
| `--green-800` | `#1c4229` | Ítem activo del menú |
| `--green-700` | `#1f5a34` | Primario: botones, barras, tarjeta destacada |
| `--lime` | `#d6ea8a` | Acento de marca (logo) |
| `--bg` | `#f7f6f1` | Fondo de página (crema) |
| `--surface` | `#ffffff` | Tarjetas |
| `--c-exportacion` / `--c-nacional` / `--c-canica` / `--c-merma` | verde / verde claro / ámbar / rojo | Balance de masa (siempre en ese orden) |
| `--warn` / `--crit` / `--ok` | ámbar / rojo / verde | Estados y etiquetas de alertas |

### 7.2 Tipografía

- **Manrope** para texto. **JetBrains Mono** para **todas las cifras** (kg, $, %, folios, RFC) con números tabulares, para que alineen.
- Títulos de tarjeta en MAYÚSCULAS, 14.5px, peso 700.

### 7.3 Componentes disponibles

| Componente | Clase / uso |
|---|---|
| Tarjeta | `.card`, título `.card-title` |
| KPI | `.card.kpi` (+ `.kpi--primary` destacada, `.kpi--warn` con pendiente) |
| Tabla | `.table-wrap > table.table`, columnas numéricas `.num` |
| Etiqueta | `.tag.tag--ok / --warn / --crit / --info / --muted` |
| Botón | `.btn.btn-primary`, `.btn.btn-ghost`, tamaño `.btn-sm` |
| Formulario | `.card.form-card > .form-grid`, campos con `{% include "partials/field.html" with f=form.campo %}` |
| Ícono | `{% icon "nombre" %}` (lista en `apps/core/templatetags/ui.py`) |
| Números | `{{ v\|num }}` → 29,690.00 · `{{ v\|money }}` → $329,325.40 · `{{ v\|pct }}` → 77.10% |

### 7.4 Responsivo

- ≤ 1280px: KPIs en 3 columnas. ≤ 1080px: gráficas apiladas.
- ≤ 900px: el menú se vuelve deslizable (botón ☰ arriba a la izquierda); login sin panel verde.
- ≤ 520px: KPIs en una columna.
- En escritorio el menú se puede **colapsar** a solo íconos (se recuerda por navegador).

---

## 8. Dashboard ejecutivo: cómo se calcula cada número

Código: `apps/dashboard/servicios.py → indicadores(empresa)`. Todo filtrado por la empresa activa.

| Indicador | Fórmula |
|---|---|
| **Kg recibidos** | Σ `kg_netos` de todas las recepciones registradas. *(Filtrar por temporada llegará con el módulo de Recepción.)* |
| **Kg empacados de exportación** | Σ `exportacion_kg` de las corridas. |
| **Neto corrido** | Σ (exportación + nacional + canica + merma) de las corridas. |
| **Aprovechamiento export.** | Exportación ÷ neto corrido × 100. |
| **Contenedores del mes** | Σ `contenedores` de embarques con fecha en el mes actual; ventas = Σ `importe_usd`. |
| **Saldo por liquidar** | Σ (`total` − `pagado`) de liquidaciones no pagadas completas. |
| **Lotes sin liquidar** | Recepciones que no tienen ninguna liquidación. |
| **IVA acreditable exportación** | Σ IVA de compras con destino exportación que **tienen CFDI** y además son **PUE**, o son **PPD con REP** (complemento de pago). *Total acreditable* = lo mismo sin filtrar destino. |
| **Aprovechamiento por calibre** | Σ kg de exportación por calibre ÷ neto corrido × 100. El eje Y se redondea a 4 divisiones enteras. |
| **Balance de masa** | Cada destino ÷ neto corrido. |
| **TC DOF** (barra superior) | Último tipo de cambio registrado (global para todas las empresas). |

### 8.1 Alertas de control

| Alerta | Se dispara cuando | Gravedad |
|---|---|---|
| Lote sin liquidar | Una recepción no tiene liquidación | Ámbar |
| Liquidación sin CFDI | Liquidación sin UUID de CFDI de compra / autofactura | Roja |
| Compra sin CFDI | Compra sin UUID de CFDI (su IVA no es acreditable) | Roja |
| Compra PPD sin REP | Compra PPD con CFDI pero sin complemento de pago | Roja |
| Opinión 32-D | Productor con opinión de cumplimiento negativa | Roja |

"Revisar" lleva al módulo correspondiente (hoy en construcción).

---

## 9. Módulos

Estado: ✅ terminado · 🚧 en construcción · ⏳ pendiente

| Módulo | Estado | Sección |
|---|---|---|
| Login y sesión | ✅ | §6 |
| Empresas (superadmin) | ✅ | §5.3 |
| Usuarios y roles | ✅ | §5 |
| Bitácora de accesos | ✅ | §6 |
| Dashboard ejecutivo | ✅ | §8 |
| Configuración de giro | ⏳ | — |
| Productores | ⏳ | — |
| Anticipos y habilitaciones | ⏳ | — |
| Huertas | ⏳ | — |
| Clientes | ⏳ | — |
| Materiales de empaque | ⏳ | — |
| Recepción en báscula | ⏳ | — |
| Corridas de empaque | ⏳ | — |
| Liquidaciones | ⏳ | — |
| Cámaras y tarimas | ⏳ | — |
| Embarques | ⏳ | — |
| Compras y gastos | ⏳ | — |
| Costeo por embarque | ⏳ | — |
| Cédula fiscal export. | ⏳ | — |

Los modelos de `apps/operacion/models.py` son la **versión mínima** que alimenta el dashboard;
cada módulo los ampliará (campos, catálogos, validaciones).

### Plantilla para documentar un módulo

Copiar al final de esta sección al terminar cada módulo:

```markdown
### 9.x Nombre del módulo

**Objetivo:** qué problema resuelve, en una línea.
**Quién lo usa:** roles que capturan / consultan.
**Ruta:** /modulo/...    **App:** apps/...

**Proceso paso a paso**
1. ...
2. ...

**Datos (modelo)**
| Campo | Tipo | Regla |
|---|---|---|

**Reglas de negocio y validaciones**
- ...

**Impacto en otros módulos / dashboard**
- ...

**Pendientes conocidos**
- ...
```

---

## 10. Despliegue a producción (Docker)

### 10.1 Servicios

| Servicio | Imagen | Función |
|---|---|---|
| `db` | postgres:16-alpine | Base de datos (volumen `pgdata`) |
| `web` | Dockerfile del proyecto | Django + Gunicorn (3 workers). Aplica migraciones al arrancar. |
| `caddy` | caddy:2-alpine | HTTPS automático (Let's Encrypt), gzip, cabeceras de seguridad |

### 10.2 Primer despliegue

Requisitos en el servidor: Docker + Docker Compose, un dominio apuntando a la IP del servidor, puertos 80 y 443 abiertos.

```bash
git clone <repo> avocontrol && cd avocontrol
cp .env.example .env
# Editar .env: DOMINIO, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS,
#              DJANGO_CSRF_TRUSTED_ORIGINS, POSTGRES_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # genera DJANGO_SECRET_KEY

docker compose up -d --build
docker compose exec web python manage.py createsuperuser        # superadmin de plataforma
```

Entrar a `https://<dominio>` con el superadmin → **Empresas → Nueva empresa**.

### 10.3 Actualizar a una nueva versión

```bash
git pull
docker compose up -d --build        # reconstruye y aplica migraciones
```

### 10.4 Respaldos (obligatorio)

```bash
# Respaldo diario (programar con cron)
docker compose exec -T db pg_dump -U avocontrol avocontrol | gzip > respaldo_$(date +%F).sql.gz

# Restaurar
gunzip -c respaldo_2026-11-24.sql.gz | docker compose exec -T db psql -U avocontrol avocontrol
```

Guardar los respaldos **fuera** del servidor (S3, Drive, otro equipo).

### 10.5 Desarrollo vs. producción

| | Desarrollo | Producción |
|---|---|---|
| Settings | `config.settings.dev` | `config.settings.prod` |
| Base de datos | SQLite (`db.sqlite3`) | PostgreSQL (obligatorio) |
| DEBUG | Sí | No |
| HTTPS / cookies seguras | No | Sí (Caddy + HSTS) |
| Estáticos | Django | WhiteNoise (comprimidos, con hash) |

---

## 11. Pruebas

```bash
python manage.py test
```

Cubren hoy (19 pruebas):

- Login correcto, email sin mayúsculas, contraseña incorrecta, bloqueo por intentos.
- Usuario inactivo y empresa inactiva (incluida la expulsión de una sesión abierta).
- `next` externo ignorado; logout solo por POST.
- **Aislamiento**: un admin no ve ni edita usuarios de otra empresa (404).
- Un operador no administra usuarios (403); un admin no crea superadmins ni se quita su rol.
- Flujo del superadmin al elegir empresa.
- Cálculo exacto de todos los indicadores del dashboard y que las empresas no se mezclan.

**Regla:** cada módulo nuevo agrega al menos una prueba de aislamiento entre empresas.

---

## 12. Convenciones para desarrollar

- **Idioma**: código de negocio, modelos y pantallas en español (`Recepcion`, `kg_netos`); nombres técnicos de Django en inglés.
- **Dinero y kilos**: siempre `DecimalField` (nunca `float`). Kg 2 decimales, MXN/USD 2, tipo de cambio 4.
- **Cálculos** en `servicios.py` de cada app, no en vistas ni plantillas.
- **Multiempresa**: ver la regla de oro (§4.3).
- **Permisos**: toda vista lleva un decorador de `apps/core/permisos.py`.
- **Auditoría**: acciones sensibles llaman a `registrar_evento(...)`.
- **Nuevo módulo**: 1) app o modelos, 2) vistas + plantillas, 3) en `apps/core/menu.py` cambiar `slug` por `url`, 4) pruebas, 5) documentar en §9.

---

## 13. Hoja de ruta

| Etapa | Contenido |
|---|---|
| **0.1** ✅ | Base: login, multiempresa, usuarios y roles, bitácora, dashboard, Docker |
| 0.2 | Catálogos: productores (con 32-D), huertas, clientes, materiales de empaque |
| 0.3 | Recepción en báscula y corridas de empaque por calibre |
| 0.4 | Liquidaciones, anticipos y habilitaciones |
| 0.5 | Cámaras y tarimas, embarques |
| 0.6 | Compras y gastos con validación de CFDI / REP |
| 0.7 | Costeo por embarque y cédula fiscal de exportación |
| Después | Recuperación de contraseña por email, 2FA, tipo de cambio DOF automático, exportar a Excel/PDF |

---

## 14. Glosario

| Término | Significado |
|---|---|
| **Tenant / Empresa** | Cada cliente que usa el ERP; sus datos están aislados. |
| **Lote** | Fruta recibida de un productor en una entrada de báscula. |
| **Corrida** | Proceso de empaque de un lote; reparte el neto en exportación, nacional, canica y merma. |
| **Calibre** | Tamaño del aguacate (número de piezas por caja: 32, 36, 40, 48, 60, 70, 84). |
| **Canica** | Fruta pequeña o con defecto que va a industria. |
| **Merma** | Pérdida (fruta dañada, deshidratación). |
| **Liquidación** | Pago al productor por la fruta de un lote. |
| **CFDI** | Factura electrónica del SAT. |
| **PUE / PPD** | Pago en una exhibición / pago en parcialidades o diferido. |
| **REP** | Recibo electrónico de pago (complemento de pago) que ampara una factura PPD. |
| **Opinión 32-D** | Opinión de cumplimiento de obligaciones fiscales del SAT. |
| **TC DOF** | Tipo de cambio FIX publicado en el Diario Oficial de la Federación. |

---

## 15. Bitácora de cambios

| Fecha | Versión | Cambio |
|---|---|---|
| 24/11/2026 | 0.1 | Proyecto Django + Docker. Login con bloqueo, multiempresa, usuarios/roles, bitácora, panel de empresas, dashboard ejecutivo, datos demo, 19 pruebas. |
