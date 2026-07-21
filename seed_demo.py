"""Dev-only script to seed a demo user with realistic data.

Run with: python manage.py shell < seed_demo.py
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone

from core.utils.fechas import etiqueta_ciclo, fin_ciclo, inicio_ciclo_para_fecha
from presupuesto.models import (
    Categoria,
    CicloMensual,
    ConfiguracionUsuario,
    GastoFijoPlantilla,
    Movimiento,
)
from ahorros.models import FondoAhorro, Inversion, MovimientoPatrimonio

USERNAME = "demo"
PASSWORD = "demo12345"

# Reset demo user for a clean slate
User.objects.filter(username=USERNAME).delete()
user = User.objects.create_user(username=USERNAME, password=PASSWORD)
user.first_name = "Adrian"
user.save()

# Config
config = ConfiguracionUsuario.obtener(user)
config.salario_base = Decimal("4500000")
config.dia_corte = 30
config.dias_plazo_tolerancia = 3
config.configurado = True
config.ha_visto_tutorial = True
config.save()

# Categories with fintech colors
cats_def = [
    ("Vivienda", "#06b6d4"),
    ("Alimentación", "#10b981"),
    ("Transporte", "#f59e0b"),
    ("Ocio", "#f43f5e"),
    ("Servicios", "#8b5cf6"),
    ("Salud", "#ec4899"),
]
cats = {}
for i, (nombre, color) in enumerate(cats_def):
    cats[nombre] = Categoria.objects.create(
        usuario=user, nombre=nombre, color=color, orden=i,
    )

# Fixed expense templates
fijos = [
    ("Arriendo", "1500000", "Vivienda"),
    ("Internet y celular", "180000", "Servicios"),
    ("Energía y agua", "220000", "Servicios"),
    ("Gimnasio", "120000", "Salud"),
]
for desc, monto, cat in fijos:
    GastoFijoPlantilla.objects.create(
        usuario=user, descripcion=desc, monto=Decimal(monto), categoria=cats[cat],
    )

# Active cycle
today = date.today()
inicio = inicio_ciclo_para_fecha(today, config.dia_corte)
fin = fin_ciclo(inicio, config.dia_corte)
ciclo = CicloMensual.objects.create(
    usuario=user,
    fecha_inicio=inicio,
    fecha_fin=fin,
    etiqueta=etiqueta_ciclo(inicio, fin),
    salario_ciclo=config.salario_base,
    estado=CicloMensual.ACTIVO,
)

# Fixed movements in the cycle
for desc, monto, cat in fijos:
    Movimiento.objects.create(
        usuario=user, ciclo=ciclo, tipo=Movimiento.GASTO,
        monto=Decimal(monto), descripcion=desc, categoria=cats[cat],
        es_gasto_fijo=True,
        fecha_registro=timezone.now() - timedelta(days=12),
    )

# Variable expenses
variables = [
    ("Mercado semanal", "320000", "Alimentación", 10),
    ("Almuerzos", "145000", "Alimentación", 8),
    ("Gasolina", "260000", "Transporte", 7),
    ("Uber al aeropuerto", "48000", "Transporte", 5),
    ("Cine y cena", "95000", "Ocio", 4),
    ("Suscripción streaming", "38000", "Ocio", 3),
    ("Farmacia", "72000", "Salud", 2),
    ("Café con amigos", "54000", "Alimentación", 1),
]
for desc, monto, cat, dias in variables:
    Movimiento.objects.create(
        usuario=user, ciclo=ciclo, tipo=Movimiento.GASTO,
        monto=Decimal(monto), descripcion=desc, categoria=cats[cat],
        fecha_registro=timezone.now() - timedelta(days=dias),
    )

# Extra income
Movimiento.objects.create(
    usuario=user, ciclo=ciclo, tipo=Movimiento.INGRESO_ADICIONAL,
    monto=Decimal("650000"), descripcion="Freelance diseño web",
    fecha_registro=timezone.now() - timedelta(days=6),
)

# Savings fund + transfers
fondo = FondoAhorro.obtener(user)
fondo.saldo_disponible = Decimal("3200000")
fondo.save()
MovimientoPatrimonio.objects.create(
    usuario=user, fondo=fondo, tipo=MovimientoPatrimonio.ENTRADA_DERIVACION,
    monto=Decimal("500000"), descripcion="Derivación: Ahorro mensual", ciclo=ciclo,
)
MovimientoPatrimonio.objects.create(
    usuario=user, fondo=fondo, tipo=MovimientoPatrimonio.ENTRADA_SOBRANTE,
    monto=Decimal("420000"), descripcion="Sobrante del ciclo anterior",
)

# Investments
Inversion.objects.create(
    usuario=user, nombre="CDT Bancolombia", monto_inicial=Decimal("2000000"),
    fecha_inicio=today - timedelta(days=40),
    fecha_vencimiento=today + timedelta(days=20), estado=Inversion.ACTIVA,
    notas="CDT a 90 dias, 11% E.A.",
)
Inversion.objects.create(
    usuario=user, nombre="Acciones ECOPETROL", monto_inicial=Decimal("1500000"),
    fecha_inicio=today - timedelta(days=90),
    fecha_vencimiento=today + timedelta(days=4), estado=Inversion.ACTIVA,
    notas="Compra especulativa",
)
inv_cerrada = Inversion.objects.create(
    usuario=user, nombre="Fondo inmobiliario", monto_inicial=Decimal("1000000"),
    monto_final=Decimal("1180000"),
    fecha_inicio=today - timedelta(days=200),
    fecha_vencimiento=today - timedelta(days=10),
    fecha_cierre=timezone.now() - timedelta(days=10),
    estado=Inversion.CERRADA_GANANCIA, notas="Cerrada con ganancia",
)

# Closed historical cycles
for m in range(1, 4):
    ci = inicio - timedelta(days=30 * m)
    cf = ci + timedelta(days=29)
    cerrado = CicloMensual.objects.create(
        usuario=user, fecha_inicio=ci, fecha_fin=cf,
        etiqueta=etiqueta_ciclo(ci, cf),
        salario_ciclo=Decimal("4500000"),
        estado=CicloMensual.CERRADO,
        sobrante_transferido=Decimal(str(300000 + m * 50000)),
        fecha_cierre=timezone.now() - timedelta(days=30 * m),
    )
    Movimiento.objects.create(
        usuario=user, ciclo=cerrado, tipo=Movimiento.GASTO,
        monto=Decimal("1500000"), descripcion="Arriendo", categoria=cats["Vivienda"],
        fecha_registro=timezone.now() - timedelta(days=30 * m),
    )
    Movimiento.objects.create(
        usuario=user, ciclo=cerrado, tipo=Movimiento.GASTO,
        monto=Decimal(str(600000 + m * 40000)), descripcion="Mercado del mes",
        categoria=cats["Alimentación"],
        fecha_registro=timezone.now() - timedelta(days=30 * m),
    )

print("Demo user created: demo / demo12345")
