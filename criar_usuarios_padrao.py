import os
import django
import unicodedata
import re

# Configuração do ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import Administracao, CustomUser, Departamento

def normalize_name(text):
    """Remove acentos, espaços e caracteres especiais, retornando em minúsculas."""
    if not text:
        return ""
    # Normaliza para NFD (separa acentos) e remove caracteres não-ascii
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    # Remove tudo que não for letra ou número
    text = re.sub(r'[^a-zA-Z0-9]', '', text)
    return text.lower()

def criar_usuarios_padrao():
    print("Iniciando a criação de usuários padrão...")
    
    admins = Administracao.objects.all()
    total_criados = 0
    total_erros = 0
    
    for admin in admins:
        try:
            # 1. Obter ou criar o departamento "Secretaria Geral" para esta administração
            # Nota: 'Secretaria Geral' é comum em todas as estruturas (A, B, C, D, E e G)
            secretaria_geral, _ = Departamento.objects.get_or_create(
                nome='Secretaria Geral',
                administracao=admin,
                defaults={
                    'tipo_municipio': admin.tipo_municipio,
                    'ativo': True
                }
            )
            
            # 2. Definir o nome base para o usuário
            if admin.tipo_municipio == 'G':
                # Para Governos, usamos a província (ex: Govuige)
                base_name = normalize_name(admin.provincia)
                prefix = "Gov"
            else:
                # Para Administrações, usamos o nome do município (ex: Aduige)
                base_name = normalize_name(admin.nome)
                prefix = "Ad"
            
            # Formata o username (ex: aduige, govuige)
            # Nota: Usamos tudo em minúsculas conforme solicitado pelo usuário
            username = f"{prefix.lower()}{base_name.lower()}"
            password = f"{username}123"
            
            # 3. Criar ou atualizar o usuário
            # Usamos o CustomUser.objects.create_user para lidar com o hash da senha
            user = CustomUser.objects.filter(username=username).first()
            
            if not user:
                user = CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    administracao=admin,
                    departamento=secretaria_geral,
                    nivel_acesso='admin_sistema'
                )
                print(f"[+] Usuário CRIADO: {username} para {admin.nome}")
                total_criados += 1
            else:
                # Se já existe, apenas garantimos os vínculos se necessário (opcional)
                # O usuário pediu para criar, então se já existe apenas logamos
                print(f"[=] Usuário EXISTE: {username} para {admin.nome}")
                
        except Exception as e:
            print(f"[!] ERRO ao processar {admin.nome}: {str(e)}")
            total_erros += 1

    print("\n" + "="*50)
    print(f"RESUMO FINAL")
    print(f"Total de Administrações: {admins.count()}")
    print(f"Usuários Criados: {total_criados}")
    print(f"Erros Encontrados: {total_erros}")
    print("="*50)

if __name__ == '__main__':
    criar_usuarios_padrao()
