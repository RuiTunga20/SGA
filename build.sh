#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependências
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Coletar arquivos estáticos
# O WhiteNoise vai comprimir e preparar os arquivos aqui
python manage.py collectstatic --no-input

# Aplicar migrações do banco de dados
python manage.py migrate

# Popular Banco de Dados (Ordem Importante)
echo "--- Populando Administrações ---"
python popular_administracoes.py
python popular_governos.py

echo "--- Populando Departamentos Base ---"
python popular.py

echo "--- Populando Tipos de Documentos ---"
python tipodocumentos.py

echo "--- Adicionando Adjuntos por Tipo ---"
python adicionar_adjuntos_tipo_a.py
python adicionar_adjuntos_tipo_b.py
python adicionar_adjuntos_tipo_c.py
python adicionar_adjuntos_tipo_d.py
python adicionar_adjuntos_tipo_e.py

echo "--- Criando Usuário Padrão (Gestão) ---"
python manage.py populate_default_user

echo "--- Criando Usuários Padrão das Administrações (Aduige/Govuige) ---"
python criar_usuarios_padrao.py

echo "--- Criando Super Admin MAT ---"
python create_super_mat.py

