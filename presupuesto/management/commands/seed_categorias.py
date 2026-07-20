from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from presupuesto.utils import seed_categorias_usuario


class Command(BaseCommand):
    help = 'Carga categorías predeterminadas para uno o todos los usuarios'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Usuario específico')

    def handle(self, *args, **options):
        username = options.get('username')
        if username:
            users = User.objects.filter(username=username)
        else:
            users = User.objects.all()
        for user in users:
            seed_categorias_usuario(user)
        self.stdout.write(self.style.SUCCESS(f'Categorías sembradas para {users.count()} usuario(s).'))
