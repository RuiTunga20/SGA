#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependências
pip install -r requirements.txt

# Coletar arquivos estáticos
# O WhiteNoise vai comprimir e preparar os arquivos aqui
python manage.py collectstatic --no-input

# Aplicar migrações do banco de dados
python manage.py migrate
