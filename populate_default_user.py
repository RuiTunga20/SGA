from django.core.management.base import BaseCommand
from ARQUIVOS.models import Administracao, Departamento, CustomUser

class Command(BaseCommand):
    help = 'Create default administration, department and user'

    def handle(self, *args, **options):
        # 1. Create administration if not exists
        admin, created_admin = Administracao.objects.get_or_create(
            nome='Administração Padrão',
            defaults={'tipo_municipio': 'A'}
        )
        if created_admin:
            self.stdout.write(self.style.SUCCESS(f'Created Administracao: {admin.nome}'))
        else:
            self.stdout.write(f'Administracao already exists: {admin.nome}')

        # 2. Create department linked to this administration
        dept, created_dept = Departamento.objects.get_or_create(
            nome='Departamento Padrão',
            administracao=admin,
            defaults={'tipo_municipio': admin.tipo_municipio}
        )
        if created_dept:
            self.stdout.write(self.style.SUCCESS(f'Created Departamento: {dept.nome}'))
        else:
            self.stdout.write(f'Departamento already exists: {dept.nome}')

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
