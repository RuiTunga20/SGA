"""
Script para adicionar o Administrador Municipal Adjunto e sua Secção
que faltam em todas as Administrações do Tipo E.

Decreto Presidencial n.º 270/24 de 29 de novembro.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import Administracao, Departamento, Seccoes

# O Administrador Municipal Adjunto do Tipo E e sua Secção
ADJUNTO_TIPO_E = {
    'nome': 'Administrador Municipal Adjunto',
    'descricao': 'Órgão de assessoria ao Administrador Municipal',
    'seccao': {
        'nome': 'Secretário do Administrador Municipal Adjunto',
        'descricao': 'Secretariado de apoio ao Administrador Municipal Adjunto'
    }
}


def adicionar_adjuntos():
    """
    Adiciona o Administrador Municipal Adjunto e sua Secção em todas as
    administrações do Tipo E.
    """
    # Buscar todas as administrações do Tipo E
    administracoes_tipo_e = Administracao.objects.filter(tipo_municipio='E')
    
    print(f"\n📊 Encontradas {administracoes_tipo_e.count()} administrações do Tipo E\n")
    
    total_dept_criados = 0
    total_dept_existentes = 0
    total_sec_criados = 0
    total_sec_existentes = 0
    
    for admin in administracoes_tipo_e:
        print(f"\n{'='*60}")
        print(f"🏛️  {admin.nome} ({admin.provincia})")
        print(f"{'='*60}")
        
        # 1. Criar/Obter o Departamento
        departamento, created_dept = Departamento.objects.get_or_create(
            nome=ADJUNTO_TIPO_E['nome'],
            administracao=admin,
            defaults={
                'descricao': ADJUNTO_TIPO_E['descricao'],
                'tipo_municipio': 'E',
                'ativo': True,
            }
        )
        
        if created_dept:
            total_dept_criados += 1
            print(f"  [+] DEP CRIADO: {ADJUNTO_TIPO_E['nome']}")
        else:
            total_dept_existentes += 1
            print(f"  [=] DEP Existe: {ADJUNTO_TIPO_E['nome']}")
            
        # 2. Criar/Obter a Secção ligada ao Departamento
        seccao, created_sec = Seccoes.objects.get_or_create(
            nome=ADJUNTO_TIPO_E['seccao']['nome'],
            departamento=departamento,
            defaults={
                'descricao': ADJUNTO_TIPO_E['seccao']['descricao'],
                'ativo': True,
            }
        )
        
        if created_sec:
            total_sec_criados += 1
            print(f"      [+] SEC CRIADA: {ADJUNTO_TIPO_E['seccao']['nome']}")
        else:
            total_sec_existentes += 1
            print(f"      [=] SEC Existe: {ADJUNTO_TIPO_E['seccao']['nome']}")
    
    # Resumo final
    print(f"\n\n{'='*70}")
    print(f"RESUMO FINAL - TIPO E")
    print(f"{'='*70}")
    print(f"  ✅ Departamentos criados: {total_dept_criados}")
    print(f"  ℹ️  Departamentos existentes: {total_dept_existentes}")
    print(f"  ✅ Secções criadas:       {total_sec_criados}")
    print(f"  ℹ️  Secções existentes:      {total_sec_existentes}")
    print(f"{'='*70}")
    
    return total_dept_criados, total_sec_criados


if __name__ == '__main__':
    print("="*70)
    print("ADICIONAR ADMINISTRADOR MUNICIPAL ADJUNTO E SECÇÃO - TIPO E")
    print("Decreto Presidencial n.º 270/24 de 29 de novembro")
    print("="*70)
    
    adicionar_adjuntos()
    
    print(f"\n✅ Concluído!")
