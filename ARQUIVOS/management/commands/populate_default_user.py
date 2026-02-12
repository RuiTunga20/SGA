from django.core.management.base import BaseCommand
from ARQUIVOS.models import Administracao, Departamento, CustomUser

class Command(BaseCommand):
    help = 'Create default administration, department and user'

    def handle(self, *args, **options):
        # 1. Use an existing administration (e.g., Luanda or first available)
        admin = Administracao.objects.filter(nome='Luanda').first() or Administracao.objects.first()
        
        if not admin:
            self.stdout.write(self.style.ERROR('No Administration found. Please run population scripts first.'))
            return

        self.stdout.write(f'Using Administracao: {admin.nome}')

        # 2. Use an existing department (e.g., Secretaria Geral)
        dept = Departamento.objects.filter(nome='Secretaria Geral', administracao=admin).first() or \
               Departamento.objects.filter(administracao=admin).first()
        
        if not dept:
            self.stdout.write(self.style.ERROR(f'No Department found for {admin.nome}.'))
            return

        self.stdout.write(f'Using Departamento: {dept.nome}')

        # 3. Create default user linked to admin and dept
        username = 'usuario_padrao'
        user, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                'password': 'password123', # Note: set_password needed if creating manually, but create_user handles hashing. get_or_create doesn't hash password in defaults.
                'administracao': admin,
                'departamento': dept,
                'nivel_acesso': 'admin_sistema',
                'is_superuser': True,
                'is_staff': True
            }
        )

        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created default superuser: {user.username} (password: password123)'))
        else:
            # Update existing user to be superuser
            user.is_superuser = True
            user.is_staff = True
            user.nivel_acesso = 'admin_sistema'
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated existing user {username} to superuser'))
