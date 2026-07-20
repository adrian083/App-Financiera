from presupuesto.models import Categoria

CATEGORIAS_INICIALES = [
    ('Alimentación', '#ef4444', 1),
    ('Transporte', '#f97316', 2),
    ('Casa', '#eab308', 3),
    ('Ocio', '#22c55e', 4),
    ('Salud', '#06b6d4', 5),
    ('Suscripciones', '#8b5cf6', 6),
    ('Educación', '#ec4899', 7),
    ('Otros', '#64748b', 8),
]


def seed_categorias_usuario(usuario):
    for nombre, color, orden in CATEGORIAS_INICIALES:
        Categoria.objects.get_or_create(
            usuario=usuario,
            nombre=nombre,
            defaults={'color': color, 'orden': orden},
        )
