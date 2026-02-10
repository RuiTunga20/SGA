import os
import django

# PASSO 1: Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

# PASSO 2: Importar os modelos
try:
    from ARQUIVOS.models import Departamento, Seccoes
    from ARQUIVOS.models.organizacao import Departamento, Seccoes
    # Tenta importar o modelo Administracao (ajusta o caminho se necessário)
    try:
        from ARQUIVOS.models.organizacao import Administracao
    except ImportError:
        from ARQUIVOS.models import Administracao
except ImportError as e:
    print(f"ERRO: Verifique as importações. Detalhe: {e}")
    exit()


# --- ESTRUTURA COMPLETA COM GABINETES DE DIREÇÃO (A, B, C, D) ---

ESTRUTURA = {
    'A': {
        # --- ÓRGÃOS DE APOIO DIRETO (GABINETES) ---
        "Gabinete do Administrador Municipal": [
            "Secção de Secretariado",
            "Secção de Expediente e Protocolo",
            "Corpo de Assessores"
        ],
        "Gabinete do Administrador Adjunto para a Área Política, Social e da Comunidade": [
            "Secção de Apoio Técnico",
            "Secretariado"
        ],
        "Gabinete do Administrador Adjunto para a Área Técnica e Infra-estruturas": [
            "Secção de Apoio Técnico",
            "Secretariado"
        ],
        "Gabinete do Administrador Adjunto para a Área Económica e Financeira": [
            "Secção de Apoio Técnico",
            "Secretariado"
        ],

        # --- SERVIÇOS DE APOIO TÉCNICO E INSTRUMENTAL ---
        "Secretaria Geral": [
            "Secção de Orçamento e Finanças",
            "Secção de Património e Logística",
            "Secção de Expediente Geral"
        ],
        "Gabinete de Estudos, Planeamento e Estatística (GEPE)": [
            "Secção de Estudos e Estatística",
            "Secção de Planeamento e Monitorização"
        ],
        "Gabinete de Recursos Humanos": [
            "Secção de Gestão de Carreiras",
            "Secção de Formação e Avaliação"
        ],
        "Gabinete Jurídico e de Intercâmbio": [
            "Secção de Contencioso",
            "Secção de Apoio às Comissões de Moradores"
        ],
        "Gabinete de Comunicação Social": [
            "Secção de Imprensa",
            "Secção de Relações Públicas"
        ],

        # --- DIRECÇÕES MUNICIPAIS (EXECUTIVOS) ---
        "Direcção Municipal da Educação": [
            "Secção de Ensino Geral",
            "Secção de Alfabetização",
            "Secção de Inspecção"
        ],
        "Direcção Municipal da Saúde": [
            "Secção de Saúde Pública",
            "Secção Médica",
            "Secção de Logística Hospitalar"
        ],
        "Direcção Municipal de Infra-estruturas e Ordenamento": [
            "Secção de Urbanismo",
            "Secção de Cadastro",
            "Secção de Obras"
        ],
        "Direcção Municipal de Gestão Orçamental e Financeira": [
            "Secção de Contabilidade",
            "Secção de Tesouraria"
        ],
        "Direcção Municipal dos Registos e Modernização Administrativa": [
            "Secção de Administração Pública",
            "Secção de Registos/BUAP"
        ],
    },
    'B': {
        "Gabinete do Administrador Municipal": [
            "Secção de Apoio Directo",
            "Secretariado"
        ],
        "Gabinete do Administrador Adjunto para a Área Política e Social": [
            "Secretariado de Apoio"
        ],
        "Gabinete do Administrador Adjunto para a Área Técnica e Económica": [
            "Secretariado de Apoio"
        ],
        "Secretaria Geral": [
            "Secção de Administração e Finanças",
            "Secção de Logística"
        ],
        "Gabinete de Estudos, Planeamento e Recursos Humanos": [
            "Secção de Planeamento",
            "Secção de Pessoal"
        ],
        "Direcção Municipal de Educação e Saúde": [
            "Secção de Educação",
            "Secção de Saúde"
        ],
        "Direcção Municipal de Infra-estruturas e Serviços Técnicos": [
            "Secção de Obras e Urbanismo",
            "Secção de Energia e Águas"
        ],
    },
    'C': {
        "Gabinete do Administrador Municipal": [
            "Secção de Secretariado e Apoio Técnico"
        ],
        "Gabinete do Administrador Municipal Adjunto": [
            "Apoio Técnico e Administrativo"
        ],
        "Secretaria Municipal": [
            "Secção Administrativa e Financeira",
            "Secção de Expediente"
        ],
        "Repartição de Planeamento e Serviços Sociais": [
            "Secção de Planeamento",
            "Secção de Educação e Saúde"
        ],
        "Repartição de Serviços Técnicos e Agricultura": [
            "Secção de Obras e Urbanismo",
            "Secção de Agricultura"
        ],
    },
    'D': {
        "Gabinete do Administrador Municipal": [
            "Secretariado e Apoio Geral"
        ],
        "Repartição de Administração e Serviços Gerais": [
            "Secção de Finanças, Pessoal e Expediente"
        ],
        "Repartição de Serviços Sociais e Económicos": [
            "Secção de Educação, Saúde e Acção Social"
        ],
        "Repartição de Serviços Técnicos e Infra-estruturas": [
            "Secção de Obras e Saneamento"
        ],
    },
}


def popular_base_de_dados():
    print("--- INICIANDO POVOAMENTO DA ESTRUTURA ADMINISTRATIVA ANGOLANA ---\n")

    total_deptos_criados = 0
    total_deptos_existentes = 0
    total_seccoes_criadas = 0
    total_admins_processadas = 0
    total_admins_sem_tipo = 0

    for tipo_mun, departamentos in ESTRUTURA.items():

        # Buscar todas as administrações deste tipo
        administracoes = Administracao.objects.filter(tipo_municipio=tipo_mun)

        if not administracoes.exists():
            print(f"[AVISO] Nenhuma administração do Tipo {tipo_mun} encontrada. A ignorar.")
            total_admins_sem_tipo += 1
            continue

        print(f"\n{'='*60}")
        print(f"  TIPO {tipo_mun} — {administracoes.count()} administração(ões)")
        print(f"{'='*60}")

        for administracao in administracoes:
            print(f"\n  >> {administracao.nome}")
            total_admins_processadas += 1

            for nome_depto, lista_seccoes in departamentos.items():

                # Criar o Departamento associado à administração
                try:
                    depto_obj, created = Departamento.objects.get_or_create(
                        nome=nome_depto,
                        administracao=administracao,
                        defaults={
                            'tipo_municipio': tipo_mun,
                            'ativo': True,
                            'descricao': f"Órgão de estrutura Tipo {tipo_mun}"
                        }
                    )
                except Exception as e:
                    print(f"    [ERRO] Departamento '{nome_depto}': {e}")
                    continue

                if created:
                    total_deptos_criados += 1
                    print(f"    [NOVO]      {nome_depto}")
                else:
                    total_deptos_existentes += 1
                    print(f"    [EXISTENTE] {nome_depto}")

                # Criar as Secções ligadas ao departamento
                for nome_seccao in lista_seccoes:
                    try:
                        _, s_created = Seccoes.objects.get_or_create(
                            nome=nome_seccao,
                            departamento=depto_obj,
                            defaults={'ativo': True}
                        )
                        if s_created:
                            total_seccoes_criadas += 1
                            print(f"       -> Secção: {nome_seccao}")
                    except Exception as e:
                        print(f"       [ERRO] Secção '{nome_seccao}': {e}")

    # Resumo final
    print(f"\n{'='*60}")
    print(f"  RESUMO FINAL")
    print(f"{'='*60}")
    print(f"  Administrações processadas : {total_admins_processadas}")
    print(f"  Tipos sem administrações   : {total_admins_sem_tipo}")
    print(f"  Departamentos criados      : {total_deptos_criados}")
    print(f"  Departamentos já existentes: {total_deptos_existentes}")
    print(f"  Secções criadas            : {total_seccoes_criadas}")
    print(f"{'='*60}")
    print(f"\n✅ Concluído!")


if __name__ == '__main__':
    popular_base_de_dados()