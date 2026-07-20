# FinanzasApp — PWA Multi-usuario (Django + SQLite)

Aplicación web de finanzas personales en **Pesos Colombianos (COP)**, multi-usuario, instalable como **PWA** y desplegable en **PythonAnywhere**.

## Requisitos

- Python 3.10+
- Django 5.x

## Instalación local

```powershell
cd "c:\Users\Usuario\Desktop\App Financiera"
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abre [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)

## Primer uso

1. **Registrarse** en `/registro/` — se crean categorías predeterminadas automáticamente.
2. **Configurar** salario base y día de corte (por defecto: 30).
3. Ver el **tutorial de bienvenida** (solo la primera vez).
4. Usar el **Dashboard** para registrar gastos, ingresos y transferencias a ahorro.

## Características UI

- **Logo oficial** en navbar, login, registro y tutorial (`static/icons/logo.png`).
- **Modo oscuro/claro** con botón ☀️/🌙 en el navbar (persistencia en `localStorage`).
- **Tutorial interactivo** de 4 pasos al primer acceso al dashboard.
- **PWA instalable** en celular (Chrome/Safari → Instalar aplicación).

## Módulos

| Ruta | Descripción |
|------|-------------|
| `/` | Dashboard — presupuesto del ciclo actual |
| `/ahorros/` | Ahorros, inversiones y ledger contable |
| `/historico/` | Ciclos cerrados |
| `/categorias/` | Categorías personalizadas |
| `/gastos-fijos/` | Plantillas de gastos recurrentes |

## PWA (instalar en celular)

La app incluye `static/manifest.json` y `static/js/service-worker.js`. Desde Chrome/Edge en móvil: **Menú → Instalar aplicación**.

## Despliegue en PythonAnywhere

1. Subir el proyecto y crear un virtualenv con Django 5.
2. En el panel Web → **WSGI**, apuntar a `finanzas_app.wsgi`.
3. Configurar **Static files**: `/static/` → carpeta `static/` del proyecto.
4. En `settings.py` producción: `DEBUG=False`, `ALLOWED_HOSTS` con tu dominio `.pythonanywhere.com`.
5. Ejecutar `python manage.py migrate` y `collectstatic`.

## Arquitectura

```
finanzas_app/     → settings, urls
core/             → auth, utilidades COP, templatetags
presupuesto/      → Módulo 1 (ciclos, gastos, ingresos)
ahorros/          → Módulo 2 (fondo, inversiones, ledger)
static/           → JS, manifest PWA, iconos
templates/        → UI Tailwind + Chart.js
```

## Seguridad multi-usuario

- Todos los modelos tienen `ForeignKey` / `OneToOneField` a `User`.
- Todas las vistas usan `@login_required` y filtran por `request.user`.
