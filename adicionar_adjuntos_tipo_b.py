"""
Script para adicionar os 2 Administradores Municipais Adjuntos
que faltam em todas as Administrações do Tipo B.

Decreto Presidencial n.º 270/24 de 29 de novembro.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import Administracao, Departamento

# Os 2 Administradores Municipais Adjuntos do Tipo B
ADJUNTOS_TIPO_B = [
    {
        'nome': 'Administrador Municipal Adjunto p/ Área Técnica, Infra-estruturas e Serviços Comunitários',
        'descricao': 'Órgão de assessoria ao Administrador Municipal na área técnica, infra-estruturas e serviços comunitários',
    },
    {
        'nome': 'Administrador Municipal Adjunto p/ Área Política, Social, Económica e Financeira',
        'descricao': 'Órgão de assessoria ao Administrador Municipal na área política, social, económica e financeira',
    },
]


def adicionar_adjuntos():
    """
    Adiciona os 2 Administradores Municipais Adjuntos em todas as
    administrações do Tipo B.
    """
    # Buscar todas as administrações do Tipo B
    administracoes_tipo_b = Administracao.objects.filter(tipo_municipio='B')
    
    print(f"\n📊 Encontradas {administracoes_tipo_b.count()} administrações do Tipo B\n")
    
    total_criados = 0
    total_existentes = 0
    
    for admin in administracoes_tipo_b:
        print(f"\n{'='*60}")
        print(f"🏛️  {admin.nome} ({admin.provincia})")
        print(f"{'='*60}")
        
        for adjunto in ADJUNTOS_TIPO_B:
            departamento, created = Departamento.objects.get_or_create(
                nome=adjunto['nome'],
                administracao=admin,
                defaults={
                    'descricao': adjunto['descricao'],
                    'tipo_municipio': 'B',
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
    print(f"RESUMO FINAL - TIPO B")
    print(f"{'='*70}")
    print(f"  ✅ Total de adjuntos criados:    {total_criados}")
    print(f"  ℹ️  Total de adjuntos existentes: {total_existentes}")
    print(f"{'='*70}")
    
    return total_criados, total_existentes


if __name__ == '__main__':
    print("="*70)
    print("ADICIONAR ADMINISTRADORES MUNICIPAIS ADJUNTOS - TIPO B")
    print("Decreto Presidencial n.º 270/24 de 29 de novembro")
    print("="*70)
    
    criados, existentes = adicionar_adjuntos()
    
    print(f"\n✅ Concluído!")
