"""
Script para adicionar os 3 Administradores Municipais Adjuntos
que faltam em todas as Administrações do Tipo A.

Decreto Presidencial n.º 270/24 de 29 de novembro.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import Administracao, Departamento

# Os 3 Administradores Municipais Adjuntos do Tipo A
ADJUNTOS_TIPO_A = [
    {
        'nome': 'Administrador Municipal Adjunto p/ Área Técnica, Infra-estruturas e Serviços Comunitários',
        'descricao': 'Órgão de assessoria ao Administrador Municipal na área técnica, infra-estruturas e serviços comunitários',
    },
    {
        'nome': 'Administrador Municipal Adjunto p/ Área Económica e Financeira',
        'descricao': 'Órgão de assessoria ao Administrador Municipal na área económica e financeira',
    },
    {
        'nome': 'Administrador Municipal Adjunto p/ Área Política, Social e da Comunidade',
        'descricao': 'Órgão de assessoria ao Administrador Municipal na área política, social e da comunidade',
    },
]


def adicionar_adjuntos():
    """
    Adiciona os 3 Administradores Municipais Adjuntos em todas as
    administrações do Tipo A.
    """
    # Buscar todas as administrações do Tipo A
    administracoes_tipo_a = Administracao.objects.filter(tipo_municipio='A')
    
    print(f"\n📊 Encontradas {administracoes_tipo_a.count()} administrações do Tipo A\n")
    
    total_criados = 0
    total_existentes = 0
    
    for admin in administracoes_tipo_a:
        print(f"\n{'='*60}")
        print(f"🏛️  {admin.nome} ({admin.provincia})")
        print(f"{'='*60}")
        
        for adjunto in ADJUNTOS_TIPO_A:
            departamento, created = Departamento.objects.get_or_create(
                nome=adjunto['nome'],
                administracao=admin,
                defaults={
                    'descricao': adjunto['descricao'],
                    'tipo_municipio': 'A',
                    'ativo': True,
                }
            )
            
            if created:
                total_criados += 1
                print(f"  [+] CRIADO: {adjunto['nome']}")
            else:
                total_existentes += 1
                print(f"  [=] Existe: {adjunto['nome']}")
    
    # Resumo final
    print(f"\n\n{'='*70}")
    print(f"RESUMO FINAL")
    print(f"{'='*70}")
    print(f"  ✅ Total de adjuntos criados:    {total_criados}")
    print(f"  ℹ️  Total de adjuntos existentes: {total_existentes}")
    print(f"{'='*70}")
    
    return total_criados, total_existentes


if __name__ == '__main__':
    print("="*70)
    print("ADICIONAR ADMINISTRADORES MUNICIPAIS ADJUNTOS - TIPO A")
    print("Decreto Presidencial n.º 270/24 de 29 de novembro")
    print("="*70)
    
    criados, existentes = adicionar_adjuntos()
    
    print(f"\n✅ Concluído!")
