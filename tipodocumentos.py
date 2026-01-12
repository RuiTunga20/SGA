import os
import django

# 1. Configurar Ambiente
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

try:
    from ARQUIVOS.models import TipoDocumento
except ImportError as e:
    print(f"ERRO: Verifique o nome do app. Detalhe: {e}")
    exit()

# DADOS ORGANIZADOS COM PRAZOS ESTIMADOS (em dias)
DOCUMENTOS = [
    # --- Atos Normativos e Legislativos (Prazos maiores/indeterminados) ---
    ("Lei", "Acto normativo aprovado pelo Poder Legislativo.", 90),
    ("Decreto", "Acto administrativo da competência do Executivo.", 60),
    ("Portaria", "Documento para instruções sobre a aplicação de leis ou decretos.", 30),
    ("Resolução", "Decisão de um órgão colegial.", 30),
    ("Despacho normativo", "Determinação para execução de serviços.", 15),
    ("Regulamento Instrução normativa", "Normas internas de organização.", 45),

    # --- Documentos de Expediente e Comunicação ---
    ("Ofício", "Comunicação oficial entre autoridades.", 15),
    ("Ofício empresarial", "Comunicação oficial de empresas.", 10),
    ("Memorando", "Comunicação interna rápida.", 5),
    ("Circular", "Comunicação enviada a vários destinatários.", 7),
    ("Comunicado / Anúncio", "Informação de interesse público.", 5),
    ("Carta oficial", "Correspondência formal externa.", 15),
    ("Aviso", "Notificação ou ordem transmitida publicamente.", 5),

    # --- Gestão de Pessoas (RH) ---
    ("Aposentação", "Processo de reforma de funcionário.", 180),
    ("Exoneração", "Acto de dispensa ou cessação de funções.", 30),
    ("Promoção", "Acto de progressão na carreira.", 60),
    ("Férias", "Documento de marcação ou gozo de descanso anual.", 30),
    ("Folhas de ponto / controle de jornada", "Registo diário de presença.", 30),
    ("Fichas de registro de empregados", "Dados cadastrais do trabalhador.", 365),
    ("Licença", "Autorização para afastamento temporário.", 15),
    ("Transferência", "Mudança de local de trabalho ou quadro.", 45),
    ("Relatórios de avaliação de desempenho", "Análise periódica do funcionário.", 30),

    # --- Contratos e Acordos ---
    ("Contrato administrativo", "Acordo firmado pela Administração Pública.", 60),
    ("Contratos de trabalho", "Vínculo empregatício.", 30),
    ("Contratos comerciais", "Acordos de compra, venda ou prestação.", 45),
    ("Convênio", "Acordo de cooperação entre entidades.", 90),
    ("Acordos de confidencialidade", "Termos de sigilo (NDA).", 365),
    ("Termo de compromisso", "Documento de obrigação assumida.", 30),

    # --- Financeiro e Contabilístico ---
    ("Empenho", "Reserva de verba para despesa.", 15),
    ("Nota de liquidação", "Verificação do direito do credor.", 10),
    ("Ordem de pagamento", "Autorização para saída de fundos.", 5),
    ("Faturas / notas fiscais", "Documentos de cobrança de bens/serviços.", 30),
    ("Recibos", "Comprovante de pagamento.", 30),
    ("Extratos e comprovantes bancários", "Registos de movimentação financeira.", 30),
    ("Relatórios contábeis e financeiros", "Balanços e demonstrações.", 90),

    # --- Actos de Registro e Certificação ---
    ("Acta", "Registo escrito do que se passou numa reunião.", 5),
    ("Auto", "Registo de uma ocorrência ou acto verificado.", 15),
    ("Certidão", "Documento que atesta factos em arquivo.", 15),
    ("Protocolo", "Registo de entrega ou recebimento de documentos.", 2),
    ("Licenças, certificados e registros", "Documentos de autorização legal.", 60),

    # --- Pareceres e Planeamento ---
    ("Parecer", "Opinião técnica fundamentada.", 20),
    ("Parecer interno / análise técnica", "Análise detalhada de processo.", 15),
    ("Relatório", "Descrição detalhada de actividades ou factos.", 15),
    ("Relatórios de atividades", "Resumo de tarefas executadas.", 30),
    ("Planos de ação / planeamento estratégico", "Guia de metas e tarefas.", 365),
    ("Petição", "Pedido formal às autoridades.", 30),
    ("Requerimento", "Solicitação por escrito feita por interessado.", 15),

    # --- Outros ---
    ("Deliberação", "Decisão tomada após discussão.", 15),
    ("Despacho", "Decisão de autoridade administrativa sobre petição.", 10),
    ("Processo administrativo", "Conjunto de documentos ordenados.", 90),
    ("Termo", "Registo de início ou fim de acto administrativo.", 10),
]


def popular_tipos_documentos():
    print(f"--- Iniciando povoamento de {len(DOCUMENTOS)} Tipos de Documentos ---")

    for nome, desc, prazo in DOCUMENTOS:
        obj, created = TipoDocumento.objects.get_or_create(
            nome=nome,
            defaults={
                'descricao': desc,
                'prazo_dias': prazo,
                'ativo': True
            }
        )

        if created:
            print(f"  [+] Inserido: {nome}")
        else:
            # Caso queira atualizar os prazos de quem já existe
            obj.prazo_dias = prazo
            obj.save()
            print(f"  [.] Atualizado: {nome}")

    print("\n[SUCESSO] Todos os documentos administrativos foram carregados!")


if __name__ == '__main__':
    popular_tipos_documentos()