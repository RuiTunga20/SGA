"""
Script para adicionar o Administrador Municipal Adjunto
que falta em todas as Administrações do Tipo D.

Decreto Presidencial n.º 270/24 de 29 de novembro.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import Administracao, Departamento

# O Administrador Municipal Adjunto do Tipo D
ADJUNTOS_TIPO_D = [
    {
        'nome': 'Administrador Municipal Adjunto',
        'descricao': 'Órgão de assessoria ao Administrador Municipal',
    },
]


def adicionar_adjuntos():
    """
    Adiciona o Administrador Municipal Adjunto em todas as
    administrações do Tipo D.
    """
    # Buscar todas as administrações do Tipo D
    administracoes_tipo_d = Administracao.objects.filter(tipo_municipio='D')
    
    print(f"\n📊 Encontradas {administracoes_tipo_d.count()} administrações do Tipo D\n")
    
    total_criados = 0
    total_existentes = 0
    
    for admin in administracoes_tipo_d:
        print(f"\n{'='*60}")
        print(f"🏛️  {admin.nome} ({admin.provincia})")
        print(f"{'='*60}")
        
        for adjunto in ADJUNTOS_TIPO_D:
            departamento, created = Departamento.objects.get_or_create(
                nome=adjunto['nome'],
                administracao=admin,
                defaults={
                    'descricao': adjunto['descricao'],
                    'tipo_municipio': 'D',
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
    print(f"RESUMO FINAL - TIPO D")
    print(f"{'='*70}")
    print(f"  ✅ Total de adjuntos criados:    {total_criados}")
    print(f"  ℹ️  Total de adjuntos existentes: {total_existentes}")
    print(f"{'='*70}")
    
    return total_criados, total_existentes


if __name__ == '__main__':
    print("="*70)
    print("ADICIONAR ADMINISTRADOR MUNICIPAL ADJUNTO - TIPO D")
    print("Decreto Presidencial n.º 270/24 de 29 de novembro")
    print("="*70)
    
    criados, existentes = adicionar_adjuntos()
    
    print(f"\n✅ Concluído!")
