import os
import django
import sys

# Setup Django environment
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import Administracao, Departamento, Seccoes

# Definição da Estrutura do MAT
ESTRUTURA_MAT = {
    "Gabinete do Ministro": [
        "Assessor do Ministro",
        "Director de Gabinete do Ministro",
        "Director Adjunto de Gabinete do Ministro",
        "Secretário(a) do Ministro"
    ],
    "Gabinete do Secretário de Estado para Administração do Território": [
        "Assessor do Secretário de Estado para Administração do Território",
        "Director de Gabinete do Secretário de Estado para Administração do Território",
        "Secretário(a) do Secretário de Estado para Administração do Território"
    ],
    "Gabinete do Secretário de Estado para as Autarquias Locais": [
        "Assessor do Secretário de Estado para as Autarquias Locais",
        "Director do Gabinete do Secretário de Estado para as Autarquias Locais",
        "Secretário(a) do Secretário de Estado para as Autarquias Locais"
    ],
    "Direcção Nacional da Administração Local do Estado": [
        "Departamento de Acompanhamento da Administração Local do Estado",
        "Departamento de Análises e Estudos da Administração Local do Estado"
    ],
    "Direcção Nacional do Poder Local": [
        "Departamento de Monitorização das Autarquias Locais",
        "Departamento de Estudos e Acompanhamento das Instituições do Poder Local"
    ],
    "Direcção Nacional de Органиização do Território": [
        "Departamento de Organização do Território",
        "Departamento de Cartografia",
        "Departamento de Divisão Político-Administrativa e Toponímia"
    ],
    "Direcção Nacional do Registo Eleitoral Oficioso": [
        "Departamento Técnico e de Coordenação do Balcão Único de Atendimento Público (BUAP)",
        "Departamento de Gestão de Dados",
        "Departamento do Registo Eleitoral Oficioso"
    ],
    "Secretaria Geral": [
        "Departamento de Gestão do Orçamento e Administração do Património",
        "Departamento de Logística",
        "Departamento de Relações Públicas e Expediente",
        "Departamento da Contratação Pública"
    ],
    "Gabinete de Recursos Humanos": [
        "Departamento de Gestão Técnica e Registo de Dados",
        "Departamento de Formação, Capacitação, Desenvolvimento do Capital Humano e Fomento da Cultura Institucional"
    ],
    "Gabinete de Estudos, Planeamento e Estatística": [
        "Departamento de Estudos e Projectos",
        "Departamento de Planeamento e Estatística",
        "Departamento de Monitorização e Controlo"
    ],
    "Gabinete Jurídico e Intercâmbio": [
        "Departamento de Estudos Jurídicos e Produção Normativa",
        "Departamento de Intercâmbio"
    ],
    "Gabinete de Tecnologia de Informação": [
        # O user disse "Não tem Departamento", mas o sistema exige Seccoes para certas lógicas???
        # Não, o sistema permite Departamento sem Secção. Mas para popular é bom ter algo.
        # Vou deixar a lista vazia conforme pedido "Não tem Departamento"
    ],
    "Gabinete de Comunicação Institucional e Imprensa": [
        "Centro de Documentação e Informação",
        "Departamento de Organização de Efemérides Nacionais"
    ]
}

def popular_mat():
    print("Iniciando população do MAT (Ministério da Administração do Território)...")
    
    nome_mat = "Ministério da Administração do Território"
    
    # Criar ou Obter a Administração do MAT
    mat, created = Administracao.objects.get_or_create(
        nome=nome_mat,
        defaults={
            'tipo_municipio': 'M',
            'provincia': 'Luanda' # Sede em Luanda
        }
    )
    
    if created:
        print(f"  > Criado novo Ministério: {nome_mat}")
    else:
        print(f"  > Ministério já existente: {nome_mat}")
        
    # Criar Estrutura Interna (Direcções Nacionais/Gabinetes)
    for direcao_nome, departamentos in ESTRUTURA_MAT.items():
        # Criar a Direcção (que é um Departamento no nosso sistema)
        direcao, dept_created = Departamento.objects.get_or_create(
            nome=direcao_nome,
            administracao=mat,
            defaults={
                'tipo_municipio': 'M',
                'descricao': f'{direcao_nome} do {nome_mat}'
            }
        )
        
        if dept_created:
            print(f"    + Direcção criada: {direcao_nome}")
        
        # Criar os Departamentos (que são Secções no nosso sistema)
        for sub_nome in departamentos:
            seccao, sec_created = Seccoes.objects.get_or_create(
                nome=sub_nome,
                departamento=direcao,
                defaults={
                    'descricao': sub_nome
                }
            )
            if sec_created:
                print(f"      - Dept/Secção criado: {sub_nome}")

if __name__ == '__main__':
    popular_mat()
