#!/bin/bash

# Script para migrar dados do SQLite para PostgreSQL no Docker
set -e

echo "=========================================="
echo "  Migração SQLite -> PostgreSQL (Docker)"
echo "=========================================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/home/rajawa/PycharmProjects/SGA"
cd "$PROJECT_DIR"

# Passo 1: Copiar SQLite para o container
echo -e "\n${YELLOW}[1/4] A copiar db.sqlite3 para o container...${NC}"
sudo docker cp db.sqlite3 sga_web:/app/db.sqlite3
echo -e "${GREEN}Ficheiro copiado!${NC}"

# Passo 2: Exportar dados do SQLite dentro do container
echo -e "\n${YELLOW}[2/4] A exportar dados do SQLite...${NC}"
sudo docker-compose exec -T web python << 'PYTHON_SCRIPT'
import sqlite3
import json

conn = sqlite3.connect('/app/db.sqlite3')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'django_migrations';")
tables = [row[0] for row in cursor.fetchall()]

print(f"Tabelas encontradas: {len(tables)}")

data = {}
for table in tables:
    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        if rows:
            data[table] = [dict(row) for row in rows]
            print(f"  {table}: {len(rows)} registros")
    except Exception as e:
        print(f"  Erro em {table}: {e}")

with open('/app/sqlite_data.json', 'w') as f:
    json.dump(data, f, indent=2, default=str)

print("\nDados exportados!")
conn.close()
PYTHON_SCRIPT

# Passo 3: Importar no PostgreSQL
echo -e "\n${YELLOW}[3/4] A importar dados no PostgreSQL...${NC}"
sudo docker-compose exec -T web python << 'PYTHON_SCRIPT'
import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from django.contrib.auth import get_user_model
from ARQUIVOS.models import Departamento, Documento, TipoDocumento, Seccoes

with open('/app/sqlite_data.json', 'r') as f:
    data = json.load(f)

print("\n=== Importando dados ===\n")

# 1. Importar TipoDocumento
if 'ARQUIVOS_tipodocumento' in data:
    print("Importando Tipos de Documento...")
    for row in data['ARQUIVOS_tipodocumento']:
        try:
            TipoDocumento.objects.get_or_create(
                id=row['id'],
                defaults={
                    'nome': row['nome'],
                    'descricao': row.get('descricao', ''),
                    'prazo_dias': row.get('prazo_dias', 30),
                    'ativo': row.get('ativo', True),
                }
            )
        except Exception as e:
            pass
    print(f"  ✓ {TipoDocumento.objects.count()} tipos de documento")

# 2. Importar Departamentos
if 'ARQUIVOS_departamento' in data:
    print("Importando Departamentos...")
    for row in data['ARQUIVOS_departamento']:
        try:
            Departamento.objects.get_or_create(
                id=row['id'],
                defaults={
                    'nome': row['nome'],
                    'codigo': row.get('codigo', ''),
                    'tipo_municipio': row.get('tipo_municipio', 'A'),
                    'ativo': row.get('ativo', True),
                }
            )
        except Exception as e:
            pass
    print(f"  ✓ {Departamento.objects.count()} departamentos")

# 3. Importar Secções
if 'ARQUIVOS_seccoes' in data:
    print("Importando Secções...")
    for row in data['ARQUIVOS_seccoes']:
        try:
            dept_id = row.get('Departamento_id')
            if dept_id and Departamento.objects.filter(id=dept_id).exists():
                Seccoes.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        'nome': row['nome'],
                        'codigo': row.get('codigo', ''),
                        'Departamento_id': dept_id,
                        'ativo': row.get('ativo', True),
                    }
                )
        except Exception as e:
            pass
    print(f"  ✓ {Seccoes.objects.count()} secções")

# 4. Importar Utilizadores
User = get_user_model()
if 'ARQUIVOS_customuser' in data:
    print("Importando Utilizadores...")
    for row in data['ARQUIVOS_customuser']:
        try:
            if not User.objects.filter(username=row['username']).exists():
                user = User(
                    id=row['id'],
                    username=row['username'],
                    email=row.get('email', ''),
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', ''),
                    is_staff=row.get('is_staff', False),
                    is_superuser=row.get('is_superuser', False),
                    is_active=row.get('is_active', True),
                    nivel=row.get('nivel', 'registro'),
                )
                # Configurar departamento se existir
                dept_id = row.get('departamento_id')
                if dept_id and Departamento.objects.filter(id=dept_id).exists():
                    user.departamento_id = dept_id
                
                seccao_id = row.get('seccao_id')
                if seccao_id and Seccoes.objects.filter(id=seccao_id).exists():
                    user.seccao_id = seccao_id
                
                user.password = row.get('password', '')
                user.save()
        except Exception as e:
            print(f"    Erro com {row.get('username')}: {e}")
    print(f"  ✓ {User.objects.count()} utilizadores")

# 5. Importar Documentos
if 'ARQUIVOS_documento' in data:
    print("Importando Documentos...")
    for row in data['ARQUIVOS_documento']:
        try:
            if not Documento.objects.filter(id=row['id']).exists():
                Documento.objects.create(
                    id=row['id'],
                    numero_documento=row.get('numero_documento', ''),
                    assunto=row.get('assunto', ''),
                    observacao=row.get('observacao', ''),
                    data_entrada=row.get('data_entrada'),
                    data_criacao=row.get('data_criacao'),
                    status=row.get('status', 'criacao'),
                    prioridade=row.get('prioridade', 'normal'),
                )
        except Exception as e:
            pass
    print(f"  ✓ {Documento.objects.count()} documentos")

print("\n=== Importação concluída! ===")
PYTHON_SCRIPT

# Passo 4: Verificar
echo -e "\n${YELLOW}[4/4] A verificar...${NC}"
sudo docker-compose exec -T web python manage.py shell << 'SHELL'
from django.contrib.auth import get_user_model
from ARQUIVOS.models import Departamento, Documento, Seccoes, TipoDocumento
User = get_user_model()
print(f"✓ Utilizadores: {User.objects.count()}")
print(f"✓ Departamentos: {Departamento.objects.count()}")
print(f"✓ Secções: {Seccoes.objects.count()}")
print(f"✓ Tipos Documento: {TipoDocumento.objects.count()}")
print(f"✓ Documentos: {Documento.objects.count()}")

# Listar superusers
superusers = User.objects.filter(is_superuser=True)
if superusers:
    print(f"\nSuperusers disponíveis:")
    for u in superusers:
        print(f"  - {u.username}")
SHELL

echo -e "\n${GREEN}=========================================="
echo -e "  Migração concluída!"
echo -e "==========================================${NC}"
echo ""
echo "Aceda à aplicação em: http://localhost:8000"
echo "Admin: http://localhost:8000/admin/"
