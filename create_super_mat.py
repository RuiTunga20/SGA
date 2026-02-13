import os
import django
import sys

# Setup Django environment
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import Administracao, Departamento, CustomUser

def create_super_admin():
    print("--- CRIANDO SUPERUSER ---")
    
    # 1. Get MAT Admin
    # 1. Get MAT Admin
    mat = Administracao.objects.filter(tipo_municipio='M').first()
    if not mat:
        print("Erro: MAT não encontrado.")
        return

    # 2. Get a Department from MAT
    dept_mat = Departamento.objects.filter(administracao=mat).first()
    if not dept_mat:
        print("Erro: MAT sem departamentos.")
        return

    print(f"Admin: {mat.nome}")
    print(f"Dept: {dept_mat.nome}")

    # 3. Create Superuser
    username = 'Mat'
    email = 'superadmin@mat.gov.ao'
    password = '@123456@!'

    if CustomUser.objects.filter(username=username).exists():
        print(f"Usuário {username} já existe. Atualizando password...")
        u = CustomUser.objects.get(username=username)
        u.set_password(password)
        u.save()
        print("Password atualizada.")
    else:
        print(f"Criando usuário {username}...")
        u = CustomUser.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            administracao=mat,
            departamento=dept_mat
        )
        print("Usuário criado com sucesso.")

if __name__ == '__main__':
    create_super_admin()
