import os
import django
import sys

# Setup Django environment
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import TipoDocumento

TIPOS_DE_DOCUMENTO = [
    {
        "nome": "Ofício",
        "descricao": "Correspondência formal enviada ou recebida pela administração.",
        "prazo_dias": 30
    },
    {
        "nome": "Memorando",
        "descricao": "Comunicação interna breve e informal entre departamentos.",
        "prazo_dias": 15
    },
    {
        "nome": "Circular",
        "descricao": "Comunicação de caráter geral destinada a todos os órgãos da administração.",
        "prazo_dias": 30
    },
    {
        "nome": "Ordem de Serviço",
        "descricao": "Determinação oficial para realização de tarefas ou procedimentos.",
        "prazo_dias": 5
    },
    {
        "nome": "Parecer Técnico",
        "descricao": "Opinião técnica fundamentada sobre determinado assunto.",
        "prazo_dias": 20
    },
    {
        "nome": "Despacho",
        "descricao": "Decisão ou deliberação proferida por autoridade competente sobre requerimento ou processo.",
        "prazo_dias": 8
    },
    {
        "nome": "Acta",
        "descricao": "Registro formal do que foi tratado em reuniões.",
        "prazo_dias": 30
    },
    {
        "nome": "Relatório",
        "descricao": "Documento descritivo sobre atividades, ocorrências ou prestação de contas.",
        "prazo_dias": 60
    },
    {
        "nome": "Informativo",
        "descricao": "Documento de caráter informativo sobre assuntos diversos.",
        "prazo_dias": 30
    },
    {
        "nome": "Requerimento",
        "descricao": "Solicitação formal feita por cidadão ou entidade à administração.",
        "prazo_dias": 15
    }
]

def popular_tipos_documento():
    print("--- POPULANDO TIPOS DE DOCUMENTO ---")
    
    total_criados = 0
    total_existentes = 0
    
    for item in TIPOS_DE_DOCUMENTO:
        obj, created = TipoDocumento.objects.get_or_create(
            nome=item['nome'],
            defaults={
                'descricao': item['descricao'],
                'prazo_dias': item['prazo_dias'],
                'ativo': True
            }
        )
        
        if created:
            print(f"[NOVO] {item['nome']} created.")
            total_criados += 1
        else:
            print(f"[EXISTENTE] {item['nome']} já existe.")
            total_existentes += 1
            
    print(f"\nResumo: {total_criados} criados, {total_existentes} existentes.")
    print("--- CONCLUÍDO ---")

if __name__ == '__main__':
    popular_tipos_documento()
