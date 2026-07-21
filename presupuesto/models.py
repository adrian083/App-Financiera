from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from core.utils.fechas import etiqueta_ciclo, fin_ciclo, inicio_ciclo_para_fecha


class ConfiguracionUsuario(models.Model):
    """Configuración financiera por usuario."""

    usuario = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='configuracion',
    )
    salario_base = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
        verbose_name='Salario base mensual',
    )
    dia_corte = models.PositiveSmallIntegerField(
        default=30,
        verbose_name='Día de corte/pago',
    )
    dias_plazo_tolerancia = models.IntegerField(
        default=3,
        verbose_name='Días de plazo/tolerancia',
    )
    moneda = models.CharField(
        max_length=3,
        default='COP',
        verbose_name='Moneda de visualización',
    )
    configurado = models.BooleanField(default=False)
    ha_visto_tutorial = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Configuración de usuario'
        verbose_name_plural = 'Configuraciones de usuario'

    def __str__(self):
        return f'Config {self.usuario.username} (corte día {self.dia_corte})'

    @classmethod
    def obtener(cls, usuario):
        obj, _ = cls.objects.get_or_create(usuario=usuario)
        return obj


class Categoria(models.Model):
    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='categorias',
    )
    nombre = models.CharField(max_length=80)
    color = models.CharField(max_length=7, default='#6366f1')
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        unique_together = [['usuario', 'nombre']]

    def __str__(self):
        return self.nombre


class CicloMensual(models.Model):
    ACTIVO = 'activo'
    CERRADO = 'cerrado'
    PENDIENTE = 'pendiente'
    ESTADOS = [
        (ACTIVO, 'Activo'),
        (CERRADO, 'Cerrado'),
        (PENDIENTE, 'Pendiente de confirmación'),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='ciclos',
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    etiqueta = models.CharField(max_length=80)
    salario_ciclo = models.DecimalField(max_digits=14, decimal_places=0, default=Decimal('0'))
    estado = models.CharField(max_length=12, choices=ESTADOS, default=ACTIVO)
    sobrante_transferido = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
    )
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Ciclo mensual'
        verbose_name_plural = 'Ciclos mensuales'

    def __str__(self):
        return self.etiqueta

    @classmethod
    def crear_desde_fecha(cls, usuario, fecha, salario, dia_corte, estado=ACTIVO):
        inicio = inicio_ciclo_para_fecha(fecha, dia_corte)
        fin = fin_ciclo(inicio, dia_corte)
        return cls.objects.create(
            usuario=usuario,
            fecha_inicio=inicio,
            fecha_fin=fin,
            etiqueta=etiqueta_ciclo(inicio, fin),
            salario_ciclo=salario,
            estado=estado,
        )

    @classmethod
    def obtener_activo(cls, usuario):
        return cls.objects.filter(usuario=usuario, estado=cls.ACTIVO).first()

    @classmethod
    def obtener_pendiente(cls, usuario):
        return cls.objects.filter(usuario=usuario, estado=cls.PENDIENTE).first()

    def total_ingresos_adicionales(self):
        return self.movimientos.filter(
            tipo=Movimiento.INGRESO_ADICIONAL,
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    def total_inyecciones_ahorro(self):
        return self.movimientos.filter(
            tipo=Movimiento.INYECCION_AHORRO,
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    def total_gastos(self):
        return self.movimientos.filter(
            tipo=Movimiento.GASTO,
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    def total_enviado_ahorro(self):
        return self.movimientos.filter(
            tipo=Movimiento.ENVIO_AHORRO,
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    def total_ingresos(self):
        return self.salario_ciclo + self.total_ingresos_adicionales() + self.total_inyecciones_ahorro()

    def saldo_disponible(self):
        return self.total_ingresos() - self.total_gastos() - self.total_enviado_ahorro()

    def calcular_sobrante(self):
        return max(self.saldo_disponible(), Decimal('0'))

    def gastos_por_categoria(self):
        return list(
            self.movimientos.filter(tipo=Movimiento.GASTO, categoria__isnull=False)
            .values('categoria__nombre', 'categoria__color')
            .annotate(total=Sum('monto'))
            .order_by('-total')
        )


class GastoFijoPlantilla(models.Model):
    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='gastos_fijos_plantilla',
    )
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=14, decimal_places=0)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name='gastos_fijos',
    )
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['descripcion']
        verbose_name = 'Gasto fijo (plantilla)'
        verbose_name_plural = 'Gastos fijos (plantillas)'

    def __str__(self):
        return f'{self.descripcion} ({self.monto})'


class Movimiento(models.Model):
    INGRESO_ADICIONAL = 'ingreso'
    GASTO = 'gasto'
    ENVIO_AHORRO = 'envio_ahorro'
    INYECCION_AHORRO = 'inyeccion'

    TIPOS = [
        (INGRESO_ADICIONAL, 'Ingreso adicional'),
        (GASTO, 'Gasto'),
        (ENVIO_AHORRO, 'Envío a ahorro'),
        (INYECCION_AHORRO, 'Inyección de ahorro'),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='movimientos',
    )
    ciclo = models.ForeignKey(
        CicloMensual, on_delete=models.CASCADE, related_name='movimientos',
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    monto = models.DecimalField(max_digits=14, decimal_places=0)
    descripcion = models.CharField(max_length=300)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movimientos',
    )
    es_gasto_fijo = models.BooleanField(default=False)
    pagado = models.BooleanField(default=True, verbose_name='Pagado')
    fecha_vencimiento = models.DateField(
        null=True, blank=True, verbose_name='Fecha de vencimiento',
    )
    plantilla_origen = models.ForeignKey(
        GastoFijoPlantilla, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_generados',
    )
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Movimiento'
        verbose_name_plural = 'Movimientos'

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.descripcion}'
