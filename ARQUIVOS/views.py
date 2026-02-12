from django.shortcuts import render
from django.utils import timezone

# Create your views here.
# views.py

from django.db.models import OuterRef, Exists, Q

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.db import transaction
from .formularios import *
from django.db.models import Count, Case, When, IntegerField
from django.core.mail import EmailMessage
from ARQUIVOS.utils import gerar_pdf_despacho
from django.urls import reverse
from ARQUIVOS.decorators import requer_contexto_hierarquico
from django.db.models.functions import TruncDate, Now
from django.db.models import Q, Count, Case, When, IntegerField, Value, BooleanField
from django.db.models.functions import Now

# Importações Locais
from .models import (
    Documento, MovimentacaoDocumento, Departamento, Seccoes, Anexo, StatusDocumento, Notificacao, CustomUser, Seccoes,
    ArmazenamentoDocumento, LocalArmazenamento, Administracao
)
from .formularios import (
    DocumentoForm, EncaminharDocumentoForm, DespachoForm,
    ArmazenamentoDocumentoForm
)
from .decorators import requer_contexto_hierarquico, requer_mesma_administracao
from .consumers import send_notification_sync, send_pendencia_update_sync

@login_required
@requer_mesma_administracao
def dashboard(request):
    """
    Dashboard com estatísticas dinâmicas baseadas na hierarquia (Secção ou Departamento).
    """
    user = request.user
    hoje = timezone.now().date()

    # 1. Determinar o contexto exato do usuário
    seccao_usuario = getattr(user, 'seccao', None)

    # Se o user tem secção, o departamento é o pai da secção.
    # Se não, é o departamento direto.
    departamento_usuario = user.departamento
    if not departamento_usuario and seccao_usuario:
        departamento_usuario = seccao_usuario.departamento

    if not departamento_usuario:
        messages.error(request, 'Você não está associado a nenhum departamento.')
        return redirect('/')

    # 2. Configurar filtros base (Dicionários de filtros dinâmicos)
    # A lógica é: Se sou de Secção, filtro por Secção. Se sou de Depto, filtro por Depto.

    # Filtro para Destino (O que chega para mim?)
    if seccao_usuario:
        filtro_destino = {'seccao_destino': seccao_usuario}
        filtro_atual = {'seccao_atual': seccao_usuario}
    else:
        filtro_destino = {'departamento_destino': departamento_usuario}
        filtro_atual = {'departamento_atual': departamento_usuario}

    # Filtro para Origem (O que eu enviei/criei?)
    if seccao_usuario:
        filtro_origem = {'seccao_origem': seccao_usuario}
    else:
        filtro_origem = {'departamento_origem': departamento_usuario}

    # --- EXECUÇÃO DAS QUERIES ---

    # 1. Pendentes (Encaminhados para MIM que ainda não confirmei)
    documentos_pendentes = MovimentacaoDocumento.objects.filter(
        tipo_movimentacao='encaminhamento',
        confirmado_recebimento=False,
        data_movimentacao__date=hoje,
        **filtro_destino  # Desempacota: seccao_destino=X ou departamento_destino=Y
    ).count()

    # 2. Encaminhados HOJE (Enviados POR MIM)
    documentos_encaminhados_hoje = MovimentacaoDocumento.objects.filter(
        tipo_movimentacao='encaminhamento',
        data_movimentacao__date=hoje,
        **filtro_origem
    ).count()

    # 3. Registados (Criados) HOJE (Criados POR MIM/MINHA ÁREA)
    # Nota: No model Documento, verifique se tem 'seccao_origem'.
    # Se não tiver, filtramos pelo criador ou ajustamos a query.
    # Assumindo que criamos a logica de salvar a secção na criação:
    if seccao_usuario:
        # Se o modelo Documento não tem 'seccao_origem', filtramos pelos docs onde a 1ª movimentação foi da secção
        # Mas para simplificar, vamos filtrar pelo departamento E usuario se for secção, ou ajustar o model.
        # Opção robusta:
        documentos_registados_hoje = Documento.objects.filter(
            departamento_origem=departamento_usuario,
            data_criacao__date=hoje
        )
        if hasattr(Documento, 'seccao_origem'):  # Se existir no model
            documentos_registados_hoje = documentos_registados_hoje.filter(seccao_origem=seccao_usuario)
        documentos_registados_hoje = documentos_registados_hoje.count()
    else:
        documentos_registados_hoje = Documento.objects.filter(
            departamento_origem=departamento_usuario,
            data_criacao__date=hoje
        ).count()

    # 4. Total de documentos ATUALMENTE na minha posse (Secção ou Depto)
    total_documentos_na_posse = Documento.objects.filter(
        **filtro_atual
    ).count()

    # 4b. Novos contadores refinados: POSSE vs HISTÓRICO
    doc_posse = 0
    doc_historico = 0
    
    if seccao_usuario:
        # Tudo que está na secção agora
        doc_posse = Documento.objects.filter(seccao_atual=seccao_usuario).count()
        # Tudo que já passou mas está noutro lado
        doc_todos_meus = Documento.objects.para_usuario(user).count()
        doc_historico = doc_todos_meus - doc_posse
    else:
        # Tudo que está no depto sem secção agora
        doc_posse = Documento.objects.filter(
            departamento_atual=departamento_usuario, 
            seccao_atual__isnull=True
        ).count()
        # Tudo que já passou mas está noutro lado
        doc_todos_meus = Documento.objects.para_usuario(user).count()
        doc_historico = doc_todos_meus - doc_posse

    # 4c. Documentos finalizados (Arquivo Morto)
    documentos_mortos = Documento.objects.para_usuario(user).filter(
        status__in=[
            StatusDocumento.DESPACHO,
            StatusDocumento.APROVADO,
            StatusDocumento.REPROVADO,
            StatusDocumento.ARQUIVADO
        ]
    ).count()

    context = {
        'departamento_nome': departamento_usuario.nome,
        'seccao_nome': seccao_usuario.nome if seccao_usuario else None,
        'documentos_pendentes': documentos_pendentes,
        'documentos_encaminhados_hoje': documentos_encaminhados_hoje,
        'documentos_registados_hoje': documentos_registados_hoje,
        'doc_posse': doc_posse,
        'doc_historico': doc_historico,
        'documentos_mortos': documentos_mortos,
    }

    return render(request, 'Paginasdashboard.html', context)


def estatisticas_aggregate(departamento, seccao=None):
    """
    Calcula estatísticas de movimentação considerando se o alvo é Departamento ou Secção.
    Args:
        departamento: Objeto Departamento (Obrigatório)
        seccao: Objeto Seccao (Opcional) - Se passado, refina a busca.
    """

    # 1. Definir o QuerySet Base (Onde houve interação comigo)
    if seccao:
        qs = MovimentacaoDocumento.objects.filter(
            Q(seccao_origem=seccao) | Q(seccao_destino=seccao)
        )
        # Filtros condicionais para o Case/When
        filtro_recebido = Q(seccao_destino=seccao)
        filtro_enviado = Q(seccao_origem=seccao)
    else:
        qs = MovimentacaoDocumento.objects.filter(
            Q(departamento_origem=departamento) | Q(departamento_destino=departamento)
        )
        filtro_recebido = Q(departamento_destino=departamento)
        filtro_enviado = Q(departamento_origem=departamento)

    # 2. Agregar
    resultado = qs.aggregate(
        recebidos=Count(
            Case(
                When(
                    Q(tipo_movimentacao='criacao') & filtro_recebido,  # Criados para mim
                    then=1
                ),
                output_field=IntegerField()
            )
        ),
        reencaminhados=Count(
            Case(
                When(
                    Q(tipo_movimentacao='encaminhamento') & filtro_enviado,  # Eu encaminhei
                    then=1
                ),
                output_field=IntegerField()
            )
        ),
        com_despacho=Count(
            Case(
                When(
                    tipo_movimentacao='despacho',  # Despacho é global ao doc, ou filtramos por quem deu despacho?
                    # Geralmente contamos despachos feitos POR MIM:
                    # usuario__seccao=seccao (se quisermos ser especificos)
                    # Mas manteremos a lógica original simplificada:
                    then=1
                ),
                output_field=IntegerField()
            )
        )
    )

    return resultado


from django.db.models.functions import TruncDate, Now


@login_required
@requer_mesma_administracao
@requer_contexto_hierarquico
def listar_documentos(request):
    ctx = request.contexto_usuario
    user = request.user

    # 1. Base Query (Segura via Manager)
    # 1. Base Query (Segura via Manager)
    documentos = Documento.objects.para_usuario(user).select_related(
        'tipo_documento', 
        'departamento_origem', 
        'departamento_atual', 
        'seccao_atual', 
        'criado_por', 
        'responsavel_atual'
    )

    # 2. Anotações Inteligentes (Lógica no Banco de Dados)
    documentos = documentos.annotate(
        # Flag: Chegou Hoje?
        chegou_hoje=Case(
            When(data_ultima_movimentacao__date=Now(), then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        # Peso para Ordenação (Urgente = 1, Baixa = 4)
        peso_prioridade=Case(
            When(prioridade='urgente', then=Value(4)),
            When(prioridade='alta', then=Value(3)),
            When(prioridade='media', then=Value(2)),
            default=Value(1),
            output_field=IntegerField()
        )
    )

    # 3. Filtros da URL (Mantidos e Expandidos)
    status = request.GET.get('status')
    prioridade = request.GET.get('prioridade')
    local = request.GET.get('local')  # Novo filtro de localização atual

    if status: documentos = documentos.filter(status=status)
    if prioridade: documentos = documentos.filter(prioridade=prioridade)
    
    # Lógica do filtro de localização atual
    if local == 'posse':
        if getattr(user, 'seccao', None):
            documentos = documentos.filter(seccao_atual=user.seccao)
        else:
            documentos = documentos.filter(
                departamento_atual=user.departamento_id,
                seccao_atual__isnull=True
            )
    elif local == 'historico':
        if getattr(user, 'seccao', None):
            documentos = documentos.exclude(seccao_atual=user.seccao)
        else:
            documentos = documentos.exclude(
                departamento_atual=user.departamento_id,
                seccao_atual__isnull=True
            )

    # Filtro Especial: "Novos Hoje" (Opcional na URL)
    if request.GET.get('filtro') == 'novos':
        documentos = documentos.filter(data_ultima_movimentacao__date=timezone.now())

    # 4. ORDENAÇÃO ESTRATÉGICA
    # Primeiro os mais recentes, depois por prioridade
    documentos = documentos.order_by('-data_criacao', '-peso_prioridade')

    # Paginação
    paginator = Paginator(documentos, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'documentos': page_obj,
        'filtros_atuais': request.GET,
        # ... outros contextos
    }

    return render(request, 'listardoumentos.html', context)
@login_required
@requer_mesma_administracao
def listar_movimentações(request):
    """
    Lista documentos com filtros e busca
    """
    user = request.user
    
    # Filtra movimentações apenas da mesma administração
    documentos = MovimentacaoDocumento.objects.select_related(
        'documento', 
        'departamento_origem', 
        'departamento_destino', 
        'seccao_origem', 
        'seccao_destino', 
        'usuario'
    ).filter(usuario__administracao=user.administracao)
    
    # Se for admin de sistema, vê tudo (opcional)
    if user.nivel_acesso == 'admin_sistema':
        documentos = MovimentacaoDocumento.objects.select_related(
            'documento', 
            'departamento_origem', 
            'departamento_destino', 
            'seccao_origem', 
            'seccao_destino', 
            'usuario'
        ).all()
    dados = estatisticas_aggregate(user.departamento)

    # Filtro por nível de acesso
    if user.nivel_acesso not in ['admin', 'diretor']:
        documentos = MovimentacaoDocumento.objects.filter(
            Q(departamento_destino=request.user.departamento)
        ).order_by('-id')

    # Filtros da URL
    busca = request.GET.get('q')

    if busca:
        documentos = documentos.filter(
            Q(titulo__icontains=busca) |
            Q(conteudo__icontains=busca) |
            Q(numero_protocolo__icontains=busca) |
            Q(tags__icontains=busca)
        )

    # Paginação
    paginator = Paginator(documentos, 20)
    page = request.GET.get('page')
    documentos = paginator.get_page(page)

    # Dados para filtros
    departamentos = Departamento.objects.filter(ativo=True)
    tipos_documento = TipoDocumento.objects.filter(ativo=True)

    context = {
        'documentos': documentos,
        'departamentos': departamentos,
        'tipos_documento': tipos_documento,
        'dados': dados,
        'filtros_atuais': {
            'busca': busca,
        }
    }

    return render(request, 'listamovimentacao.html', context)


@login_required
@requer_mesma_administracao
def detalhe_documento(request, documento_id):
    """
    Exibir detalhes do documento e permitir ações
    """
    documento = get_object_or_404(
        Documento.objects.para_usuario(request.user).select_related(
            'tipo_documento', 
            'departamento_origem', 
            'departamento_atual', 
            'seccao_atual', 
            'criado_por', 
            'responsavel_atual'
        ), 
        id=documento_id
    )

    # Obter localização do usuário (prioriza secção)
    user_seccao = getattr(request.user, 'seccao', None)
    user_departamento = request.user.departamento_efetivo

    # Verificar se o usuário pode encaminhar/agir neste documento
    pode_encaminhar = False

    # Lista de status que bloqueiam qualquer movimentação
    status_bloqueados = [StatusDocumento.ARQUIVADO, StatusDocumento.REPROVADO, 'concluido', StatusDocumento.APROVADO]

    if documento.status not in status_bloqueados:
        # Caso 1: Usuário está em uma SECÇÃO
        if user_seccao:
            # LÓGICA CORRIGIDA:
            # O usuário só pode encaminhar se o documento estiver EXATAMENTE na sua secção.
            # Se o documento foi para o Departamento (pai), o usuário da secção perde o controle.
            pode_encaminhar = (documento.seccao_atual == user_seccao)

        # Caso 2: Usuário está DIRETO no DEPARTAMENTO (sem secção)
        elif user_departamento:
            # O usuário do departamento só mexe se o documento estiver no departamento
            # E não estiver atribuído a nenhuma secção específica abaixo dele.
            pode_encaminhar = (
                    documento.departamento_atual == user_departamento and
                    documento.seccao_atual is None
            )

    # VERIFICAR SE É ADMINISTRADOR (para despacho, aprovar, reprovar)
    niveis_admin = [
        'admin_sistema',
        'admin_municipal',
        'admin',
        'diretor_municipal',
        'diretor'
    ]
    e_administrador = request.user.nivel_acesso in niveis_admin

    # Buscar todas as movimentações para o histórico
    # Nota: 'observacoes' no seu código original parecia ser o histórico completo
    observacoes = MovimentacaoDocumento.objects.filter(documento=documento).order_by('-data_movimentacao')

    # Buscar movimentações detalhadas (para display visual na template)
    movimentacoes = documento.movimentacoes.all().select_related(
        'usuario',
        'departamento_destino',
        'departamento_origem',
        'seccao_destino',
        'seccao_origem'
    ).order_by('-data_movimentacao')

    # Movimentações pendentes de confirmação de recebimento
    # Filtra apenas o que chegou para o setor atual do usuário
    movimentacoes_pendentes = movimentacoes.filter(
        confirmado_recebimento=False
    ).filter(
        Q(seccao_destino=user_seccao) if user_seccao else Q(departamento_destino=user_departamento)
    )

    # Instanciar formulários iniciais (GET)
    encaminhar_form = EncaminharDocumentoForm(user=request.user, documento=documento)
    despacho_form = DespachoForm()

    # --- INÍCIO DO TRATAMENTO POST ---
    if request.method == 'POST':
        action = request.POST.get('action')

        # === AÇÃO 1: ENCAMINHAR DOCUMENTO ===
        if action == 'encaminhar':
            if not pode_encaminhar:
                messages.error(request, 'Você não tem permissão para encaminhar este documento no momento.')
                return redirect('detalhe_documento', documento_id=documento.id)

            encaminhar_form = EncaminharDocumentoForm(
                request.POST,
                user=request.user,
                documento=documento
            )

            if encaminhar_form.is_valid():
                try:
                    with transaction.atomic():
                        # ===== LÓGICA DE TRANSMISSÃO EM MASSA (BROADCAST) DO GOVERNO =====
                        enviar_todas = encaminhar_form.cleaned_data.get('enviar_todas', False)
                        is_governo = request.user.administracao and request.user.administracao.tipo_municipio == 'G'
                        
                        if enviar_todas and is_governo:
                             # 1. Obter todas as ADMINISTRAÇÕES da Província (exceto o próprio Governo)
                             admins_destino = Administracao.objects.filter(
                                 provincia=request.user.administracao.provincia
                             ).exclude(tipo_municipio='G')
                             
                             if not admins_destino.exists():
                                 messages.warning(request, "Nenhuma administração encontrada nesta província para enviar.")
                                 return redirect('detalhe_documento', documento_id=documento.id)
                                 
                             # 2. Iterar e criar movimentação para a "Secretaria Geral" de cada uma
                             contagem_envios = 0
                             
                             for admin_dest in admins_destino:
                                 # Buscar Secretaria Geral desta administração
                                 sec_geral = Departamento.objects.filter(
                                     administracao=admin_dest,
                                     nome__icontains="Secretaria Geral"
                                 ).first()
                                 
                                 if sec_geral:
                                     nova_mov = MovimentacaoDocumento(
                                         documento=documento,
                                         tipo_movimentacao='encaminhamento',
                                         usuario=request.user,
                                         departamento_destino=sec_geral,
                                         seccao_destino=None,
                                         observacoes=encaminhar_form.cleaned_data.get('observacoes', ''),
                                         despacho=encaminhar_form.cleaned_data.get('despacho', '')
                                     )
                                     
                                     # Definir Origem
                                     if user_seccao:
                                         nova_mov.seccao_origem = user_seccao
                                         nova_mov.departamento_origem = user_seccao.departamento
                                     elif user_departamento:
                                         nova_mov.departamento_origem = user_departamento
                                         
                                     nova_mov.save()
                                     contagem_envios += 1
                                     
                                     # Notificação (simplificada para não sobrecarregar)
                                     # TODO: Implementar notificação assíncrona/Celery para broadcast grande
                                     
                             if contagem_envios > 0:
                                 messages.success(request, f'Documento enviado para {contagem_envios} administrações municipais com sucesso!')
                                 # Não muda a localização "atual" do documento original do governo,
                                 # pois ele foi "distribuído". O original fica com o Governo.
                                 # Mas podemos atualizar status para ENCAMINHAMENTO
                                 documento.status = StatusDocumento.ENCAMINHAMENTO
                                 documento.save()
                             else:
                                 messages.warning(request, "Não foi possível encontrar as Secretarias Gerais das administrações destino.")
                                 
                             return redirect('detalhe_documento', documento_id=documento.id)

                        # ===== FLUXO NORMAL DE ENCAMINHAMENTO (Um destino) =====
                        movimentacao = encaminhar_form.save(commit=False)
                        movimentacao.documento = documento
                        movimentacao.tipo_movimentacao = 'encaminhamento'
                        movimentacao.usuario = request.user

                        # ===== DEFINIR ORIGEM (Quem está enviando) =====
                        if user_seccao:
                            movimentacao.seccao_origem = user_seccao
                            # Assume que a secção tem relação com Departamento
                            movimentacao.departamento_origem = user_seccao.departamento
                        elif user_departamento:
                            movimentacao.seccao_origem = None
                            movimentacao.departamento_origem = user_departamento

                        movimentacao.save()

                        # ===== ATUALIZAR LOCALIZAÇÃO ATUAL DO DOCUMENTO =====
                        documento.status = StatusDocumento.ENCAMINHAMENTO

                        if movimentacao.seccao_destino:
                            # Foi enviado para uma SECÇÃO ESPECÍFICA
                            documento.seccao_atual = movimentacao.seccao_destino
                            documento.departamento_atual = movimentacao.seccao_destino.departamento
                        elif movimentacao.departamento_destino:
                            # Foi enviado para um DEPARTAMENTO GERAL
                            documento.seccao_atual = None
                            documento.departamento_atual = movimentacao.departamento_destino

                        documento.save()

                        # ===== CRIAR NOTIFICAÇÕES =====
                        link_documento = request.build_absolute_uri(
                            reverse('detalhe_documento', args=[documento.id])
                        )
                        
                        # Determinar destinatários (FILTRO POR ADMINISTRAÇÃO DO DESTINO)
                        # IMPORTANTE: Agora o destino pode ser de OUTRA administração (Governo <-> Admin)
                        # Então devemos filtrar usuários da administração DO DESTINO
                        
                        admin_destino_obj = None
                        if movimentacao.seccao_destino:
                             admin_destino_obj = movimentacao.seccao_destino.departamento.administracao
                        elif movimentacao.departamento_destino:
                             admin_destino_obj = movimentacao.departamento_destino.administracao
                        
                        if movimentacao.seccao_destino:
                            utilizadores = CustomUser.objects.filter(
                                seccao=movimentacao.seccao_destino,
                                administracao=admin_destino_obj, # Usa a admin do destino!
                                is_active=True
                            )
                            destino_texto = f"secção {movimentacao.seccao_destino.nome}"
                            group_name = f"seccao_{movimentacao.seccao_destino.id}"
                        elif movimentacao.departamento_destino:
                            utilizadores = CustomUser.objects.filter(
                                departamento=movimentacao.departamento_destino,
                                administracao=admin_destino_obj, # Usa a admin do destino!
                                is_active=True
                            )
                            destino_texto = f"departamento {movimentacao.departamento_destino.nome}"
                            group_name = f"departamento_{movimentacao.departamento_destino.id}"
                        else:
                            utilizadores = []
                            group_name = None
                        
                        # Criar notificações no banco
                        if utilizadores:
                            notificacoes = [
                                Notificacao(
                                    usuario=u,
                                    mensagem=f"Documento '{documento.numero_protocolo}' encaminhado para {destino_texto}.",
                                    link=link_documento
                                )
                                for u in utilizadores
                            ]
                            Notificacao.objects.bulk_create(notificacoes)
                            
                            # Enviar via WebSocket em tempo real
                            if group_name:
                                mensagem_ws = f"Novo documento: {documento.numero_protocolo} - {documento.titulo}"
                                send_notification_sync(group_name, mensagem_ws, link_documento)

                        messages.success(request, 'Documento encaminhado com sucesso!')
                        return redirect('detalhe_documento', documento_id=documento.id)
                except Exception as e:
                    messages.error(request, f'Erro ao encaminhar: {str(e)}')
            else:
                messages.error(request, 'Erro no formulário de encaminhamento. Verifique os dados.')

        # === AÇÃO 2: DESPACHO (Apenas Admins) ===
        elif action == 'despacho':
            if not e_administrador:
                messages.error(request, 'Apenas administradores podem adicionar despacho.')
                return redirect('detalhe_documento', documento_id=documento.id)

            despacho_form = DespachoForm(request.POST)
            if despacho_form.is_valid():
                # Cria movimentação de despacho
                MovimentacaoDocumento.objects.create(
                    documento=documento,
                    tipo_movimentacao='despacho',
                    seccao_origem=user_seccao,
                    departamento_origem=user_departamento,
                    usuario=request.user,
                    despacho=despacho_form.cleaned_data['despacho']
                )

                # Atualiza status se fornecido
                novo_status = despacho_form.cleaned_data.get('novo_status')
                texto_despacho = despacho_form.cleaned_data['despacho']
                
                if novo_status:
                    documento.status = novo_status
                
                # --- GERAÇÃO DE PDF E ENVIO DE EMAIL ---
                try:
                    # 1. Gerar PDF
                    pdf_content = gerar_pdf_despacho(documento, texto_despacho, request.user, novo_status)
                    
                    # 2. Salvar no campo 'arquivo_digitalizado'
                    # Nota: Isso sobrescreve o arquivo anterior se existir, conforme solicitado
                    documento.arquivo_digitalizado.save(pdf_content.name, pdf_content, save=False)
                    documento.save()
                    
                    # 3. Enviar Email se o documento tiver email associado
                    if documento.email:
                        assunto = f"Notificação de Despacho - Protocolo {documento.numero_protocolo}"
                        mensagem = f"""
                        Prezado(a) {documento.utente},
                        
                        O seu documento com número de protocolo {documento.numero_protocolo} recebeu um despacho.
                        
                        Estado Atual: {documento.get_status_display()}
                        
                        Segue em anexo o documento oficial com os detalhes do despacho.
                        
                        Atenciosamente,
                        {request.user.administracao.nome if request.user.administracao else 'Sistema de Gestão de Arquivo'}
                        """
                        
                        email = EmailMessage(
                            assunto,
                            mensagem,
                            None, # De (usará o DEFAULT_FROM_EMAIL)
                            [documento.email]
                        )
                        
                        # Anexar o PDF gerado (ler do content file)
                        pdf_content.seek(0)
                        email.attach(pdf_content.name, pdf_content.read(), 'application/pdf')
                        email.send(fail_silently=True)
                        
                        messages.success(request, f'Despacho registado e notificação enviada para {documento.email}.')
                    else:
                        messages.success(request, 'Despacho registado. (Documento sem email para notificação)')
                        
                except Exception as e:
                    # Logar erro mas não impedir o fluxo principal
                    print(f"Erro ao gerar PDF/Email: {e}")
                    messages.warning(request, f'Despacho salvo, mas houve erro ao gerar PDF ou enviar email: {e}')

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'ok', 'message': 'Despacho registado com sucesso.', 'new_status': documento.get_status_display()})
                return redirect('detalhe_documento', documento_id=documento.id)

        # === AÇÃO 3: FINALIZAÇÃO (Aprovado/Reprovado/Arquivado) ===
        elif action in [StatusDocumento.APROVADO, StatusDocumento.REPROVADO, StatusDocumento.ARQUIVADO]:
            if not e_administrador:
                messages.error(request, 'Apenas administradores podem executar esta ação.')
                return redirect('detalhe_documento', documento_id=documento.id)

            # Criar movimentação de registro
            MovimentacaoDocumento.objects.create(
                documento=documento,
                tipo_movimentacao=action,
                seccao_origem=user_seccao,
                departamento_origem=user_departamento,
                usuario=request.user,
                observacoes=f'Documento {action} por {request.user.username}'
            )

            # Atualizar documento e fechar data
            documento.status = action
            documento.data_conclusao = timezone.now()
            documento.save()

            msg = f'Documento {action} com sucesso!'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok', 'message': msg, 'new_status': action})
            messages.success(request, msg)
            return redirect('detalhe_documento', documento_id=documento.id)

        # === AÇÃO 4: CONFIRMAR RECEBIMENTO ===
        elif action == 'confirmar_recebimento':
            movimentacao_id = request.POST.get('movimentacao_id')
            movimentacao = get_object_or_404(MovimentacaoDocumento, id=movimentacao_id)

            # Verifica se já não foi confirmado para evitar duplo clique
            if not movimentacao.confirmado_recebimento:
                movimentacao.confirmado_recebimento = True
                movimentacao.data_confirmacao = timezone.now()
                movimentacao.usuario_confirmacao = request.user
                movimentacao.save()
                
                # === NOTIFICAR O REMETENTE QUE O DOCUMENTO FOI RECEBIDO ===
                remetente = movimentacao.usuario  # Quem enviou o documento
                if remetente and remetente != request.user:
                    link_documento = request.build_absolute_uri(
                        reverse('detalhe_documento', args=[documento.id])
                    )
                    
                    # Criar notificação no banco
                    Notificacao.objects.create(
                        usuario=remetente,
                        mensagem=f"O documento '{documento.numero_protocolo}' foi recebido por {request.user.username}.",
                        link=link_documento
                    )
                    
                    # Enviar via WebSocket em tempo real
                    group_name = f"user_{remetente.id}"
                    send_notification_sync(
                        group_name,
                        f"Documento {documento.numero_protocolo} recebido por {request.user.username}",
                        link_documento
                    )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'ok', 'message': 'Recebimento confirmado!'})
                messages.success(request, 'Recebimento confirmado!')

            return redirect('detalhe_documento', documento_id=documento.id)

    # Contexto para o Template
    context = {
        'documento': documento,
        'movimentacoes': movimentacoes,
        'movimentacoes_pendentes': movimentacoes_pendentes,
        'pode_encaminhar': pode_encaminhar,
        'e_administrador': e_administrador,
        'encaminhar_form': encaminhar_form,
        'despacho_form': despacho_form,
        'observacoes': observacoes,
    }

    return render(request, 'Paginasdetalhe.html', context)
@login_required
@requer_mesma_administracao
def criar_documento(request):
    """
    Criar novo documento
    """
    # Obter departamento do usuário
    departamento_usuario = None
    seccao_usuario = None

    if hasattr(request.user, 'seccao') and request.user.seccao:
        seccao_usuario = request.user.seccao
        departamento_usuario = request.user.seccao.departamento
    elif hasattr(request.user, 'departamento') and request.user.departamento:
        departamento_usuario = request.user.departamento

    dados = estatisticas_aggregate(departamento_usuario) if departamento_usuario else {}

    if request.method == 'POST':
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.criado_por = request.user

            # Verificação de departamento
            if not departamento_usuario:
                messages.error(
                    request,
                    'Seu usuário não está associado a nenhum departamento ou secção. '
                    'Entre em contato com o administrador do sistema.'
                )
                return render(request, 'Paginascriar.html', {'form': form, 'dados': dados})

            # Atribuir ao documento
            documento.departamento_origem = departamento_usuario
            documento.departamento_atual = departamento_usuario
            documento.responsavel_atual = request.user
            
            # ATRIBUIÇÃO CRÍTICA DE ADMINISTRAÇÃO
            documento.administracao = request.user.administracao
            
            documento.save()

            # Criar movimentação de criação (SEM destino - é permitido!)
            mv = MovimentacaoDocumento.objects.create(
                documento=documento,
                tipo_movimentacao='criacao',  # TIPO CRIACAO não exige destino
                departamento_origem=departamento_usuario,
                seccao_origem=seccao_usuario,
                usuario=request.user,
                observacoes='Documento criado no sistema'
            )

            # === NOTIFICAÇÃO DE CRIAÇÃO ===
            link_documento = request.build_absolute_uri(
                reverse('detalhe_documento', args=[documento.id])
            )
            
            # Notifica usuários do próprio setor sobre a criação do novo documento
            if seccao_usuario:
                utilizadores = CustomUser.objects.filter(
                    seccao=seccao_usuario,
                    administracao=request.user.administracao,
                    is_active=True
                ).exclude(id=request.user.id)
                group_name = f"seccao_{seccao_usuario.id}"
            else:
                utilizadores = CustomUser.objects.filter(
                    departamento=departamento_usuario,
                    administracao=request.user.administracao,
                    is_active=True
                ).exclude(id=request.user.id)
                group_name = f"departamento_{departamento_usuario.id}"

            if utilizadores.exists():
                notificacoes = [
                    Notificacao(
                        usuario=u,
                        mensagem=f"Novo documento criado: {documento.numero_protocolo} - {documento.titulo}",
                        link=link_documento
                    )
                    for u in utilizadores
                ]
                Notificacao.objects.bulk_create(notificacoes)
                
                # Enviar via WebSocket
                mensagem_ws = f"Novo documento criado: {documento.numero_protocolo}"
                send_notification_sync(group_name, mensagem_ws, link_documento)

            messages.success(request, f'Documento {documento.numero_protocolo} criado com sucesso!')
            return redirect('Encaminhar', documento_id=mv.id)
    else:
        form = DocumentoForm()

    return render(request, 'Paginascriar.html', {'form': form, 'dados': dados})
@login_required
@requer_mesma_administracao
def Editar_documento(request, id):
    """
    View completa para editar um documento existente, com verificação de permissões CORRIGIDA.
    """
    # 1. Buscar os objetos necessários
    documento = get_object_or_404(Documento, id=id)
    user = request.user

    # 2. --- VERIFICAÇÃO DE PERMISSÃO CORRIGIDA E MAIS ROBUSTA ---

    # Verifica se algum movimento do tipo 'encaminhamento' já existe para este documento.
    # .exists() é muito eficiente, pois não precisa de carregar todos os objectos.
    foi_encaminhado = documento.movimentacoes.filter(tipo_movimentacao='encaminhamento').exists()

    # Condição 1: O utilizador é o criador E o documento AINDA NÃO FOI encaminhado.
    pode_editar_como_criador = (documento.criado_por == user and not foi_encaminhado)

    # Condição 2: O utilizador é um administrador ou diretor (eles podem editar sempre).
    is_admin = user.nivel_acesso in ['admin', 'diretor']

    # Se o utilizador não cumprir nenhuma das condições, o acesso é negado.
    if not (pode_editar_como_criador or is_admin):
        messages.error(request, 'Não é possível editar um documento que já foi encaminhado.')
        # Redireciona para a página de detalhes para que o utilizador veja o estado atual
        return redirect('listar_documentos')

    # --- FIM DA VERIFICAÇÃO ---

    # 3. Lógica para submissão do formulário (método POST)
    if request.method == 'POST':
        form = DocumentoForm(request.POST, request.FILES, instance=documento)

        if form.is_valid():
            form.save()
            messages.success(request, f'Documento "{documento.titulo}" atualizado com sucesso!')
            return redirect('editar_documento', id=documento.id)
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário.')

    # 4. Lógica para exibir o formulário (método GET)
    else:
        form = DocumentoForm(instance=documento)

    # 5. Contexto e renderização do template
    dados = estatisticas_aggregate(request.user.departamento)
    context = {
        'form': form,
        'documento': documento,
        'dados': dados,
        'titulo_pagina': f'Editar Documento: {documento.numero_protocolo}'
    }
    return render(request, 'Paginascriar.html', context)

# Em sua_app/views.py

@login_required
@requer_mesma_administracao
def cancelar_documento(request, documento_id):
    documento = get_object_or_404(Documento, id=documento_id)
    user = request.user

    # Apenas o criador pode cancelar, e apenas se não houver movimentações de encaminhamento
    if documento.criado_por != user:
        messages.error(request, 'Apenas o criador pode cancelar este documento.')
        return redirect('detalhe_documento', documento_id=documento.id)

    if documento.movimentacoes.filter(tipo_movimentacao='encaminhamento').exists():
        messages.error(request, 'Não é possível cancelar um documento que já foi encaminhado.')
        return redirect('detalhe_documento', documento_id=documento.id)

    if request.method == 'POST':
        documento.status = 'cancelado'
        documento.save()
        # Adicionar uma movimentação para registar o cancelamento
        MovimentacaoDocumento.objects.create(
            documento=documento,
            tipo_movimentacao='cancelamento',
            departamento_origem=user.departamento,
            usuario=user,
            observacoes='Documento cancelado pelo criador.'
        )
        messages.success(request, f'Documento {documento.numero_protocolo} foi cancelado.')
        return redirect('listar_documentos')

    # Para usar um template de confirmação (opcional)
    return render(request, 'confirmar_cancelamento.html', {'documento': documento})





@login_required
@requer_mesma_administracao
def encaminhar_documento(request, documento_id):
    """
    View para editar uma movimentação existente E SINCRONIZAR COM O DOCUMENTO PRINCIPAL.
    """
    dados = estatisticas_aggregate(request.user.departamento)

    # Busca a movimentação com select_related para otimizar queries
    try:
        movimentacao = MovimentacaoDocumento.objects.select_related(
            'documento',
            'departamento_destino',
            'departamento_origem',
            'seccao_destino',
            'seccao_origem'
        ).get(id=documento_id)
        documento = movimentacao.documento
    except MovimentacaoDocumento.DoesNotExist:
        messages.error(request, 'Movimentação não encontrada.')
        return redirect('lista_documentos')

    # Validação de permissões
    # Validação de permissões (RELAXADA)
    # Antes exigia 'change_movimentacaodocumento', o que bloqueava técnicos/chefes de secção.
    # Agora permite se o usuário estiver autenticado e ativo (já garantido pelo login_required).
    # O decorator @requer_mesma_administracao já garante isolamento de tenant.
    if not request.user.is_active:
        messages.error(request, 'Sua conta está inativa.')
        return redirect('detalhe_documento', documento_id=movimentacao.documento.id)

    if request.method == 'POST':
        form = EncaminharDocumentoForm(
            request.POST,
            instance=movimentacao,
            user=request.user,
            documento=documento
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Salvar a movimentação
                    movimentacao_atualizada = form.save(commit=False)
                    movimentacao_atualizada.departamento_origem = request.user.departamento
                    movimentacao_atualizada.seccao_origem = request.user.seccao

                    # Se tiver campos de auditoria no modelo
                    if hasattr(movimentacao_atualizada, 'data_edicao'):
                        movimentacao_atualizada.data_edicao = timezone.now()
                    if hasattr(movimentacao_atualizada, 'editado_por'):
                        movimentacao_atualizada.editado_por = request.user

                    movimentacao_atualizada.save()

                    # 2. Obter o documento principal
                    documento_a_atualizar = movimentacao_atualizada.documento

                    # 3. Sincronizar o STATUS do Documento
                    documento_a_atualizar.status = movimentacao_atualizada.tipo_movimentacao

                    # 4. Sincronizar o DEPARTAMENTO ATUAL do Documento
                    # PRIORIZA SECÇÃO: Se tem secção destino, o departamento vem da secção
                    if movimentacao_atualizada.seccao_destino:
                        documento_a_atualizar.departamento_atual = movimentacao_atualizada.seccao_destino.departamento
                        # Atualiza responsável para o chefe da secção, se existir
                        if movimentacao_atualizada.seccao_destino.responsavel:
                            documento_a_atualizar.responsavel_atual = movimentacao_atualizada.seccao_destino.responsavel
                    elif movimentacao_atualizada.departamento_destino:
                        documento_a_atualizar.departamento_atual = movimentacao_atualizada.departamento_destino
                        # Atualiza responsável para o chefe do departamento, se existir
                        if movimentacao_atualizada.departamento_destino.responsavel:
                            documento_a_atualizar.responsavel_atual = movimentacao_atualizada.departamento_destino.responsavel

                    # 5. Sincronizar a DATA DE CONCLUSÃO do Documento
                    if movimentacao_atualizada.tipo_movimentacao in ['aprovado', 'reprovado', 'arquivado']:
                        documento_a_atualizar.data_conclusao = timezone.now()

                    # 6. Salvar as alterações no Documento principal
                    documento_a_atualizar.save()

                    # 7. Criar notificações (CORRIGIDO para considerar secções)
                    if movimentacao_atualizada.tipo_movimentacao == 'encaminhamento':
                        link_documento = request.build_absolute_uri(
                            reverse('detalhe_documento', args=[documento_a_atualizar.id])
                        )

                        # DETERMINA QUEM DEVE SER NOTIFICADO (FILTRO POR ADMINISTRAÇÃO DO DESTINO)
                        admin_destino_obj = None
                        if movimentacao_atualizada.seccao_destino:
                            admin_destino_obj = movimentacao_atualizada.seccao_destino.departamento.administracao
                        elif movimentacao_atualizada.departamento_destino:
                            admin_destino_obj = movimentacao_atualizada.departamento_destino.administracao

                        if movimentacao_atualizada.seccao_destino:
                            # Notifica APENAS usuários da SECÇÃO específica (FILTRO POR ADMINISTRAÇÃO DO DESTINO)
                            utilizadores_a_notificar = CustomUser.objects.filter(
                                seccao=movimentacao_atualizada.seccao_destino,
                                administracao=admin_destino_obj,
                                is_active=True
                            )
                            destino_texto = f"secção {movimentacao_atualizada.seccao_destino.nome}"
                            group_name = f"seccao_{movimentacao_atualizada.seccao_destino.id}"

                        elif movimentacao_atualizada.departamento_destino:
                            # Notifica TODOS os usuários do DEPARTAMENTO (FILTRO POR ADMINISTRAÇÃO DO DESTINO)
                            utilizadores_a_notificar = CustomUser.objects.filter(
                                departamento=movimentacao_atualizada.departamento_destino,
                                administracao=admin_destino_obj,
                                is_active=True
                            )
                            destino_texto = f"departamento {movimentacao_atualizada.departamento_destino.nome}"
                            group_name = f"departamento_{movimentacao_atualizada.departamento_destino.id}"

                        else:
                            utilizadores_a_notificar = []
                            destino_texto = "destino não especificado"
                            group_name = None

                        # Criar notificações no banco
                        if utilizadores_a_notificar:
                            notificacoes = [
                                Notificacao(
                                    usuario=u,
                                    mensagem=f"O documento '{documento_a_atualizar.numero_protocolo}' foi encaminhado para {destino_texto}.",
                                    link=link_documento
                                )
                                for u in utilizadores_a_notificar
                            ]
                            Notificacao.objects.bulk_create(notificacoes)
                            
                            # Enviar via WebSocket em tempo real
                            if group_name:
                                mensagem_ws = f"Novo documento: {documento_a_atualizar.numero_protocolo} - {documento_a_atualizar.titulo}"
                                send_notification_sync(group_name, mensagem_ws, link_documento)
                                send_pendencia_update_sync(group_name, f"Novo documento pendente: {documento_a_atualizar.numero_protocolo}")

                messages.success(request, 'Movimentação do documento atualizada com sucesso!')
                return redirect('listar_movimento')

            except Exception as e:
                messages.error(request, f"Ocorreu um erro inesperado: {str(e)}")
                # Log para debugging
                import logging
                logging.error(f"Erro em encaminhar_documento: {e}", exc_info=True)

        else:
            messages.error(request, 'Corrija os erros abaixo.')

    else:
        form = EncaminharDocumentoForm(
            instance=movimentacao,
            user=request.user,
            documento=documento
        )

    context = {
        'form': form,
        'movimentacao': movimentacao,
        'documento': movimentacao.documento,
        'titulo': f'Editar Encaminhamento - {movimentacao.documento.numero_protocolo}',
        'acao': 'Editar',
        'dados': dados
    }
    return render(request, 'encaminhamento.html', context)



@login_required
@requer_contexto_hierarquico
def pendencias(request):
    """
    Lista pendências filtrando por hierarquia (Secção/Depto) e
    removendo itens que já tiveram andamento posterior (Obsolescência).
    """
    ctx = request.contexto_usuario

    # 1. Definir quem é o destino (Eu sou Secção ou Departamento?)
    if ctx['is_seccao']:
        filtro_destino = Q(seccao_destino=ctx['seccao'])
    else:
        # Se sou depto, vejo o que chegou pro Depto E que não tem secção específica definida
        # (Ou vejo tudo do depto, depende da sua regra. Aqui deixei ver tudo do Depto)
        filtro_destino = Q(departamento_destino=ctx['departamento'])

    # 2. SUBQUERY MÁGICA: Verificar Obsolescência
    # Procura se existe QUALQUER movimentação (encaminhamento, despacho, arquivo)
    # criada DEPOIS da movimentação atual para o mesmo documento.
    movimentacoes_futuras = MovimentacaoDocumento.objects.filter(
        documento=OuterRef('documento'),
        id__gt=OuterRef('id')  # ID maior = criado depois
    )

    # 3. Query Principal
    movimentacoes_pendentes = MovimentacaoDocumento.objects.filter(
        filtro_destino,
        confirmado_recebimento=False,
        tipo_movimentacao='encaminhamento'
    ).annotate(
        # Cria um campo temporário true/false se existir mov. futura
        ja_teve_andamento=Exists(movimentacoes_futuras)
    ).filter(
        # Só mostra se NÃO teve andamento posterior
        ja_teve_andamento=False
    ).select_related(
        'documento',
        'departamento_origem',
        'seccao_origem',
        'usuario'
    ).order_by('-data_movimentacao')

    context = {
        'movimentacoes_pendentes': movimentacoes_pendentes,
    }

    return render(request, 'Paginaspendencias.html', context)



@login_required
def confirmar_recebimento(request, movimentacao_id):
    """
    Confirma recebimento e move o documento para o destino da movimentação.
    """
    # Só aceita POST para segurança
    if request.method == 'POST':
        # Busca a movimentação
        mov = get_object_or_404(MovimentacaoDocumento, id=movimentacao_id)
        user = request.user

        # --- VERIFICAÇÃO DE PERMISSÃO ---
        # 1. Obter onde o usuário está
        user_seccao = getattr(user, 'seccao', None)
        user_depto = user.departamento
        # Fallback: Se não tem depto direto, pega da secção
        if not user_depto and user_seccao:
            user_depto = user_seccao.departamento

        # 2. Verificar se o usuário está no destino da movimentação
        eh_destino_certo = False

        # Se foi enviado para uma Secção E eu sou dessa Secção
        if mov.seccao_destino and mov.seccao_destino == user_seccao:
            eh_destino_certo = True

        # Se foi enviado para um Departamento (sem secção) E eu sou desse Depto
        elif mov.departamento_destino == user_depto and not mov.seccao_destino:
            eh_destino_certo = True

        # Admins e Diretores podem confirmar qualquer coisa
        if user.nivel_acesso in ['admin', 'diretor', 'diretor_municipal']:
            eh_destino_certo = True

        if eh_destino_certo:
            # 1. Marcar Movimentação como Confirmada
            mov.confirmado_recebimento = True
            mov.data_confirmacao = timezone.now()
            mov.usuario_confirmacao = user
            mov.save()

            # 2. Mover o Documento (ATUALIZAÇÃO SEGURA)
            doc = mov.documento

            # FIX: Usamos o destino da MOVIMENTAÇÃO, não do usuário.
            # Isso evita erro se um Admin (sem depto) confirmar.
            if mov.seccao_destino:
                doc.seccao_atual = mov.seccao_destino
                doc.departamento_atual = mov.seccao_destino.departamento
            else:
                doc.seccao_atual = None
                doc.departamento_atual = mov.departamento_destino

            # (Opcional) Atualizar responsável se o destino tiver chefe
            # if doc.seccao_atual and doc.seccao_atual.responsavel:
            #     doc.responsavel_atual = doc.seccao_atual.responsavel

            doc.save()  # Agora não dará erro de NULL constraint

            # Enviar evento de atualização de pendências via WebSocket
            # Para que outros utilizadores vejam a tabela atualizada em tempo real
            if mov.seccao_destino:
                group_name = f"seccao_{mov.seccao_destino.id}"
                send_pendencia_update_sync(group_name, f"Documento {doc.numero_protocolo} foi recebido")
            elif mov.departamento_destino:
                group_name = f"departamento_{mov.departamento_destino.id}"
                send_pendencia_update_sync(group_name, f"Documento {doc.numero_protocolo} foi recebido")

            # 3. NOTIFICAR A ORIGEM (REMETENTE) QUE O DOCUMENTO FOI RECEBIDO
            if mov.usuario:
                try:
                    nome_recebedor = user.get_full_name() or user.username
                    unidade_recebedora = user.seccao.nome if getattr(user, 'seccao', None) else (user.departamento.nome if user.departamento else 'Destino')
                    
                    mensagem_confirmacao = f"Seu documento {doc.numero_protocolo} foi recebido por {nome_recebedor} ({unidade_recebedora})."
                    link_doc = request.build_absolute_uri(reverse('detalhe_documento', args=[doc.id]))
                    
                    Notificacao.objects.create(
                        usuario=mov.usuario,
                        mensagem=mensagem_confirmacao,
                        link=link_doc
                    )
                    
                    # Notificação em tempo real (opcional, se o sistema suportar envio direto para user)
                    try:
                        # Tenta enviar socket se a função suportar user channel ou se tivermos canal do user
                        # Assumindo padrão 'user_{id}'
                        send_notification_sync(f"user_{mov.usuario.id}", mensagem_confirmacao, link_doc)
                    except:
                        pass # Ignora erro de socket para não quebrar o request
                        
                except Exception as e:
                    print(f"Erro ao criar notificação de confirmação: {e}")

            messages.success(request, f'Recebimento do documento {doc.numero_protocolo} confirmado!')
        else:
            messages.error(request, 'Você não tem permissão para confirmar este recebimento.')

    # Redireciona de volta (para pendências ou detalhe, dependendo de onde veio)
    return redirect('pendencias')
def relatorios(request):
    """
    Relatórios e estatísticas do sistema
    """
    user = request.user

    # Verificar permissão
    if user.nivel_acesso not in ['admin', 'diretor', 'gerente']:
        messages.error(request, 'Você não tem permissão para acessar relatórios.')
        return redirect('dashboard')

    # Estatísticas por status
    stats_status = Documento.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    # Estatísticas por departamento
    stats_departamento = Documento.objects.values(
        'departamento_atual__nome'
    ).annotate(count=Count('id')).order_by('-count')

    # Estatísticas por tipo
    stats_tipo = Documento.objects.values(
        'tipo_documento__nome'
    ).annotate(count=Count('id')).order_by('-count')

    # Documentos vencidos
    documentos_vencidos = Documento.objects.filter(
        data_prazo__lt=timezone.now(),
        status__in=['recebido', 'em_analise']
    ).count()

    context = {
        'stats_status': stats_status,
        'stats_departamento': stats_departamento,
        'stats_tipo': stats_tipo,
        'documentos_vencidos': documentos_vencidos,
    }

    return render(request, 'Paginasrelatorios.html', context)


# Em sua_app/views.py

@login_required
def arquivo_morto(request):
    """
    Lista os documentos que foram finalizados (aprovados, reprovados, arquivados).
    """
    user = request.user

    # A base da query são os documentos com status finalizados, filtrados pela visibilidade do utilizador
    documentos_arquivados = Documento.objects.para_usuario(user).filter(
        status__in=[
            StatusDocumento.DESPACHO, 
            StatusDocumento.APROVADO, 
            StatusDocumento.REPROVADO, 
            StatusDocumento.ARQUIVADO
        ]
    )
    print('------------------------------------')
    print(documentos_arquivados.filter(
            Q(departamento_atual=user.departamento) |
            Q(departamento_origem=user.departamento) |
            Q(criado_por=user)
        ))
    print('------------------------------------')

    # Lógica de busca (reutilizada da sua view de listar)


    # Paginação
    paginator = Paginator(documentos_arquivados.order_by('-data_conclusao'), 20)
    page = request.GET.get('page')
    documentos = paginator.get_page(page)

    context = {
        'documentos': documentos,
        'titulo_pagina': 'Arquivo Morto',
    }

    return render(request, 'Paginasarquivo_morto.html', context)

# Em ARQUIVOS/views.py
from django.http import JsonResponse

@login_required
def marcar_notificacoes_como_lidas(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            notification_id = data.get('notification_id')
            if notification_id:
                Notificacao.objects.filter(id=notification_id, usuario=request.user).update(lida=True)
            else:
                Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
            return JsonResponse({'status': 'ok'})
        except Exception:
            # Fallback para o comportamento anterior se não houver JSON ou ID
            Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
            return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def verificar_notificacoes(request):
    if not request.user.is_authenticated:
        return JsonResponse({'unread_notifications_count': 0})

    user = request.user

    # Filtro simplificado: apenas notificações diretas do usuário
    notificacoes = Notificacao.objects.filter(
        usuario=user, 
        lida=False
    ).order_by('-data_criacao')[:20]
    
    count = notificacoes.count()

    # Retornar no formato esperado pelo JavaScript
    notificacoes_lista = [
        {
            'id': n.id,
            'mensagem': n.mensagem,
            'link': n.link or '#',
            'data': n.data_criacao.strftime('%d/%m/%Y %H:%M') if n.data_criacao else ''
        }
        for n in notificacoes
    ]

    response = JsonResponse({
        'count': count,
        'unread_notifications_count': count,  # Compatibilidade
        'notificacoes': notificacoes_lista
    })
    
    # Evitar cache para garantir dados frescos
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response

# Em ARQUIVOS/views.py

@login_required
def listar_pendencias_parcial(request):
    """
    Esta view retorna apenas o HTML da tabela de pendências,
    para ser usada pelo AJAX.
    """
    user = request.user
    movimentacoes_pendentes = MovimentacaoDocumento.objects.filter(
        departamento_destino=user.departamento,
        confirmado_recebimento=False,
        tipo_movimentacao='encaminhamento'
    ).select_related('documento', 'departamento_origem', 'usuario')

    context = {
        'movimentacoes_pendentes': movimentacoes_pendentes,
    }

    # Renderiza o template parcial em vez da página completa
    return render(request, '_tabela_pendencias.html', context)
@require_http_methods(["POST"])
@login_required
def busca_ajax(request):
    """
    Busca AJAX para autocomplete
    """
    termo = request.POST.get('termo', '')

    if len(termo) < 3:
        return JsonResponse({'resultados': []})

    user = request.user
    documentos = Documento.objects.filter(
        Q(titulo__icontains=termo) |
        Q(conteudo__icontains=termo) |
        Q(numero_protocolo__icontains=termo)
    )

    # Filtrar por permissão
    if user.nivel_acesso not in ['admin', 'diretor']:
        documentos = documentos.filter(
            Q(departamento_atual=user.departamento) |
            Q(departamento_origem=user.departamento) |
            Q(criado_por=user)
        )

    resultados = []
    for doc in documentos[:10]:  # Limitar a 10 resultados
        resultados.append({
            'id': str(doc.id),
            'titulo': doc.titulo,
            'numero_protocolo': doc.numero_protocolo,
            'status': doc.get_status_display(),
            'departamento': doc.departamento_atual.nome,
        })

    return JsonResponse({'resultados': resultados})
# ==============================================================================
#  AJAX VIEWS FOR DEPENDENT DROPDOWNS (ADMIN)
# ==============================================================================

def load_departamentos(request):
    """
    Retorna os departamentos de uma determinada administração (AJAX).
    """
    administracao_id = request.GET.get('administracao')
    if administracao_id:
        departamentos = Departamento.objects.filter(administracao_id=administracao_id, ativo=True).order_by('nome')
    else:
        departamentos = Departamento.objects.none()
    
    return render(request, 'ARQUIVOS/hr/dropdown_list_options.html', {'obj_list': departamentos})

def load_seccoes(request):
    """
    Retorna as secções de um determinado departamento (AJAX).
    """
    departamento_id = request.GET.get('departamento')
    if departamento_id:
        seccoes = Seccoes.objects.filter(
            departamento_id=departamento_id, 
            departamento__administracao=request.user.administracao, # SEGURANÇA: Apenas da própria ADMIN
            ativo=True
        ).order_by('nome')
    else:
        seccoes = Seccoes.objects.none()
    
    return render(request, 'ARQUIVOS/hr/dropdown_list_options.html', {'obj_list': seccoes})


# ==============================================================================
#  ARMAZENAMENTO DE DOCUMENTOS
# ==============================================================================

@login_required
def registrar_armazenamento(request, documento_id):
    """
    Registra a localização física de um documento no arquivo.
    Esta view é chamada:
    - Automaticamente após criação do documento (se operador NÃO pode reencaminhar)
    - Após reencaminhamento (se operador PODE reencaminhar)
    """
    documento = get_object_or_404(Documento, id=documento_id)
    user = request.user
    
    # Obter departamento e secção do usuário
    departamento_usuario = None
    seccao_usuario = None
    
    if hasattr(user, 'seccao') and user.seccao:
        seccao_usuario = user.seccao
        departamento_usuario = user.seccao.departamento
    elif hasattr(user, 'departamento') and user.departamento:
        departamento_usuario = user.departamento
    
    # Verificar se já existe armazenamento ativo para este documento
    armazenamento_existente = ArmazenamentoDocumento.objects.filter(
        documento=documento,
        ativo=True
    ).first()
    
    if request.method == 'POST':
        form = ArmazenamentoDocumentoForm(
            request.POST,
            user=user,
            documento=documento
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Se já existe armazenamento ativo, desativar
                    if armazenamento_existente:
                        armazenamento_existente.ativo = False
                        armazenamento_existente.data_retirada = timezone.now()
                        armazenamento_existente.retirado_por = user
                        armazenamento_existente.motivo_movimentacao = 'Nova localização registrada'
                        armazenamento_existente.save()
                    
                    # Criar novo armazenamento
                    armazenamento = form.save(commit=False)
                    armazenamento.documento = documento
                    armazenamento.registrado_por = user
                    
                    # Buscar última movimentação se houver
                    ultima_movimentacao = documento.movimentacoes.order_by('-data_movimentacao').first()
                    if ultima_movimentacao:
                        armazenamento.movimentacao_origem = ultima_movimentacao
                    
                    armazenamento.save()
                    
                    messages.success(
                        request,
                        f'Localização do documento {documento.numero_protocolo} registrada com sucesso! '
                        f'Local: {armazenamento.localizacao_completa}'
                    )
                    return redirect('detalhe_documento', documento_id=documento.id)
                    
            except Exception as e:
                messages.error(request, f'Erro ao registrar armazenamento: {str(e)}')
        else:
            messages.error(request, 'Por favor, corrija os erros no formulário.')
    else:
        form = ArmazenamentoDocumentoForm(user=user, documento=documento)
    
    # Dados estatísticos
    dados = estatisticas_aggregate(departamento_usuario) if departamento_usuario else {}
    
    context = {
        'form': form,
        'documento': documento,
        'armazenamento_existente': armazenamento_existente,
        'dados': dados,
    }
    
    return render(request, 'armazenamento.html', context)


@login_required
def listar_armazenamentos(request, documento_id=None):
    """
    Lista os armazenamentos de documentos.
    Se documento_id é fornecido, mostra histórico de armazenamento daquele documento.
    """
    user = request.user
    
    if documento_id:
        documento = get_object_or_404(Documento, id=documento_id)
        armazenamentos = ArmazenamentoDocumento.objects.filter(
            documento=documento
        ).select_related(
            'documento', 
            'local_armazenamento', 
            'registrado_por'
        ).order_by('-data_armazenamento')
        titulo = f'Histórico de Armazenamento - {documento.numero_protocolo}'
    else:
        # Lista todos armazenamentos ativos do departamento do usuário
        departamento_usuario = None
        if hasattr(user, 'seccao') and user.seccao:
            departamento_usuario = user.seccao.departamento
        elif hasattr(user, 'departamento') and user.departamento:
            departamento_usuario = user.departamento
        
        if departamento_usuario:
            armazenamentos = ArmazenamentoDocumento.objects.filter(
                Q(local_armazenamento__departamento=departamento_usuario) |
                Q(registrado_por__departamento=departamento_usuario),
                ativo=True
            ).select_related(
                'documento', 
                'local_armazenamento', 
                'registrado_por'
            ).order_by('-data_armazenamento')
        else:
            armazenamentos = ArmazenamentoDocumento.objects.none()
        
        documento = None
        titulo = 'Documentos Armazenados'
    
    # Paginação
    paginator = Paginator(armazenamentos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'armazenamentos': page_obj,
        'documento': documento,
        'titulo': titulo,
    }
    
    return render(request, 'lista_armazenamentos.html', context)


# ==============================================================================
#  GESTÃO DE USUÁRIOS (ADMIN_SISTEMA)
# ==============================================================================

from .formularios import CriarUsuarioAdminForm

@login_required
def gestao_usuarios(request):
    """
    Página para admin_sistema criar e gerir usuários da sua administração.
    """
    # Verificar permissão: apenas admin_sistema
    if request.user.nivel_acesso != 'admin_sistema':
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('Painel')
    
    # Verificar se tem administração associada
    if not request.user.administracao:
        messages.error(request, 'Você não está associado a nenhuma administração.')
        return redirect('Painel')
    
    form = CriarUsuarioAdminForm(admin_user=request.user)
    
    if request.method == 'POST':
        form = CriarUsuarioAdminForm(request.POST, admin_user=request.user)
        if form.is_valid():
            novo_usuario = form.save()
            messages.success(
                request, 
                f'Usuário "{novo_usuario.username}" criado com sucesso!'
            )
            return redirect('gestao_usuarios')
        else:
            messages.error(request, 'Erro ao criar usuário. Verifique os dados.')
    
    # Listar usuários da mesma administração
    usuarios = CustomUser.objects.filter(
        administracao=request.user.administracao
    ).select_related('departamento', 'seccao').order_by('username')
    
    context = {
        'form': form,
        'usuarios': usuarios,
        'administracao': request.user.administracao,
    }
    
    return render(request, 'gestao_usuarios.html', context)


@login_required
def ajax_seccoes_departamento(request):
    """
    Retorna as secções de um departamento em JSON.
    Usado para preencher dinamicamente o select de secções.
    """
    departamento_id = request.GET.get('departamento_id')
    seccoes = []
    
    if departamento_id:
        try:
            seccoes = list(Seccoes.objects.filter(
                departamento_id=int(departamento_id),
                departamento__administracao=request.user.administracao # SEGURANÇA: Apenas da própria ADMIN
            ).values('id', 'nome').order_by('nome'))
        except (ValueError, TypeError):
            pass
    
    return JsonResponse({'seccoes': seccoes})
