import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import TipoDocumento

count = TipoDocumento.objects.count()
print(f"Total de Tipos de Documento encontrados: {count}")

if count > 0:
    print("Tipos existentes:")
    for td in TipoDocumento.objects.all():
        print(f"- {td.nome}")
else:
    print("Nenhum Tipo de Documento encontrado.")
