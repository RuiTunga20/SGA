from django.shortcuts import render

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
from django.urls import reverse
from ARQUIVOS.decorators import requer_contexto_hierarquico
from django.db.models.functions import TruncDate, Now
from django.db.models import Q, Count, Case, When, IntegerField, Value, BooleanField
from django.db.models.functions import Now

# Importações Locais
from .models import (
    Documento, MovimentacaoDocumento, Departamento,
    TipoDocumento, Notificacao, CustomUser, Seccoes,
    ArmazenamentoDocumento, LocalArmazenamento
)
from .formularios import (
    DocumentoForm, EncaminharDocumentoForm, DespachoForm,
    ArmazenamentoDocumentoForm
)
from .decorators import requer_contexto_hierarquico


@login_required
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
        departamento_usuario = seccao_usuario.Departamento

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

    # 4. Total de documentos ATUALMENTE na minha posse
    total_documentos_na_posse = Documento.objects.filter(
        **filtro_atual
    ).count()

    # 5. Documentos mortos (Arquivados/Finalizados)
    # Aqui geralmente queremos ver o histórico do Depto todo, mas podemos filtrar
    documentos_mortos = Documento.objects.filter(
        status='arquivado',
        departamento_atual=departamento_usuario  # Arquivo costuma ser por Depto
    ).count()

    context = {
        'departamento_nome': departamento_usuario.nome,
        'seccao_nome': seccao_usuario.nome if seccao_usuario else None,  # Adicionar ao template
        'documentos_pendentes': documentos_pendentes,
        'documentos_encaminhados_hoje': documentos_encaminhados_hoje,
        'documentos_registados_hoje': documentos_registados_hoje,
        'total_documentos_no_departamento': total_documentos_na_posse,  # Nome da var mantido, mas lógica é "na posse"
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
@requer_contexto_hierarquico
def listar_documentos(request):
    ctx = request.contexto_usuario
    user = request.user

    # 1. Base Query (Segura via Manager)
    documentos = Documento.objects.para_usuario(user)

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

    # 3. Filtros da URL (Mantidos)
    status = request.GET.get('status')
    prioridade = request.GET.get('prioridade')
    # ... outros filtros ...

    if status: documentos = documentos.filter(status=status)
    if prioridade: documentos = documentos.filter(prioridade=prioridade)

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
def listar_movimentações(request):
    """
    Lista documentos com filtros e busca
    """
    user = request.user
    documentos = MovimentacaoDocumento.objects.all()
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
def detalhe_documento(request, documento_id):
    """
    Exibir detalhes do documento e permitir ações
    """
    documento = get_object_or_404(Documento, id=documento_id)

    # Obter localização do usuário (prioriza secção)
    user_seccao = getattr(request.user, 'seccao', None)
    user_departamento = request.user.departamento_efetivo

    # Verificar se o usuário pode encaminhar/agir neste documento
    pode_encaminhar = False

    # Lista de status que bloqueiam qualquer movimentação
    status_bloqueados = ['arquivado', 'reprovado', 'concluido', 'aprovado']

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
                        movimentacao = encaminhar_form.save(commit=False)
                        movimentacao.documento = documento
                        movimentacao.tipo_movimentacao = 'encaminhamento'
                        movimentacao.usuario = request.user

                        # ===== DEFINIR ORIGEM (Quem está enviando) =====
                        if user_seccao:
                            movimentacao.seccao_origem = user_seccao
                            # Assume que a secção tem relação com Departamento
                            movimentacao.departamento_origem = user_seccao.Departamento
                        elif user_departamento:
                            movimentacao.seccao_origem = None
                            movimentacao.departamento_origem = user_departamento

                        movimentacao.save()

                        # ===== ATUALIZAR LOCALIZAÇÃO ATUAL DO DOCUMENTO =====
                        documento.status = 'encaminhamento'

                        if movimentacao.seccao_destino:
                            # Foi enviado para uma SECÇÃO ESPECÍFICA
                            documento.seccao_atual = movimentacao.seccao_destino
                            documento.departamento_atual = movimentacao.seccao_destino.Departamento
                        elif movimentacao.departamento_destino:
                            # Foi enviado para um DEPARTAMENTO GERAL
                            documento.seccao_atual = None
                            documento.departamento_atual = movimentacao.departamento_destino

                        documento.save()

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
                if novo_status:
                    documento.status = novo_status
                    documento.save()

                messages.success(request, 'Despacho adicionado com sucesso!')
                return redirect('detalhe_documento', documento_id=documento.id)

        # === AÇÃO 3: FINALIZAÇÃO (Aprovado/Reprovado/Arquivado) ===
        elif action in ['aprovado', 'reprovado', 'arquivado']:
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

            messages.success(request, f'Documento {action} com sucesso!')
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
def criar_documento(request):
    """
    Criar novo documento
    """
    # Obter departamento do usuário
    departamento_usuario = None
    seccao_usuario = None

    if hasattr(request.user, 'seccao') and request.user.seccao:
        seccao_usuario = request.user.seccao
        departamento_usuario = request.user.seccao.Departamento
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

            messages.success(request, f'Documento {documento.numero_protocolo} criado com sucesso!')
            return redirect('Encaminhar', documento_id=mv.id)
    else:
        form = DocumentoForm()

    return render(request, 'Paginascriar.html', {'form': form, 'dados': dados})
@login_required
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
    if not request.user.has_perm('ARQUIVOS.change_movimentacaodocumento'):
        messages.error(request, 'Você não tem permissão para editar esta movimentação.')
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
                        documento_a_atualizar.departamento_atual = movimentacao_atualizada.seccao_destino.Departamento
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

                        # DETERMINA QUEM DEVE SER NOTIFICADO
                        if movimentacao_atualizada.seccao_destino:
                            # Notifica APENAS usuários da SECÇÃO específica
                            utilizadores_a_notificar = CustomUser.objects.filter(
                                seccao=movimentacao_atualizada.seccao_destino,
                                is_active=True
                            )
                            destino_texto = f"secção {movimentacao_atualizada.seccao_destino.nome}"

                        elif movimentacao_atualizada.departamento_destino:
                            # Notifica TODOS os usuários do DEPARTAMENTO
                            utilizadores_a_notificar = CustomUser.objects.filter(
                                departamento=movimentacao_atualizada.departamento_destino,
                                is_active=True
                            )
                            destino_texto = f"departamento {movimentacao_atualizada.departamento_destino.nome}"

                        else:
                            utilizadores_a_notificar = []
                            destino_texto = "destino não especificado"

                        # Criar notificações em lote (mais eficiente)
                        notificacoes = [
                            Notificacao(
                                usuario=u,
                                mensagem=f"O documento '{documento_a_atualizar.numero_protocolo}' foi encaminhado para {destino_texto}.",
                                link=link_documento
                            )
                            for u in utilizadores_a_notificar
                        ]

                        if notificacoes:
                            Notificacao.objects.bulk_create(notificacoes)

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
            user_depto = user_seccao.Departamento

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
                doc.departamento_atual = mov.seccao_destino.Departamento
            else:
                doc.seccao_atual = None
                doc.departamento_atual = mov.departamento_destino

            # (Opcional) Atualizar responsável se o destino tiver chefe
            # if doc.seccao_atual and doc.seccao_atual.responsavel:
            #     doc.responsavel_atual = doc.seccao_atual.responsavel

            doc.save()  # Agora não dará erro de NULL constraint

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

    # A base da query são os documentos com status finalizados
    documentos_arquivados = Documento.objects.filter(status__in=['despacho','aprovado', 'reprovado', 'arquivado'])
    # Filtro por nível de acesso (igual à view de listar)
    if user.nivel_acesso not in ['admin', 'diretor']:
        documentos_arquivados = documentos_arquivados.filter(
            Q(departamento_atual=user.departamento) |
            Q(departamento_origem=user.departamento) |
            Q(criado_por=user)
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
        Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def verificar_notificacoes(request):
    if not request.user.is_authenticated:
        return JsonResponse({'unread_notifications_count': 0})

    user = request.user

    # --- DIAGNÓSTICO NO TERMINAL (OLHE O SEU CMD/TERMINAL) ---
    print(f"--- DEBUG NOTIFICAÇÕES PARA: {user.username} ---")

    # 1. Verifica dados do Utilizador
    user_seccao = getattr(user, 'seccao', None)
    user_dept = getattr(user, 'departamento', None)
    print(f"Dados do User -> Secção: '{user_seccao}' | Dept: '{user_dept}'")

    # 2. Monta o Filtro
    filtros = Q(usuario=user)  # Sempre busca as diretas

    if user_seccao:
        filtros |= Q(seccao=user_seccao)
        print(f"Adicionado filtro de Secção: {user_seccao}")

    if user_dept:
        filtros |= Q(departamento=user_dept)
        print(f"Adicionado filtro de Departamento: {user_dept}")

    # 3. Executa a busca
    notificacoes = Notificacao.objects.filter(filtros, lida=False).distinct()
    count = notificacoes.count()

    print(f"Total encontrado: {count}")

    # Se count for 0, vamos ver se existe ALGUMA notificação no sistema para comparar
    if count == 0:
        todas = Notificacao.objects.filter(lida=False).values('id', 'seccao', 'departamento', 'usuario__username')
        print("Atenção: 0 encontradas. Segue lista de notificações PENDENTES no sistema:")
        for n in todas:
            print(
                f" - ID {n['id']}: Para User '{n['usuario__username']}' | Para Sec '{n['seccao']}' | Para Dept '{n['departamento']}'")

    print("------------------------------------------------")

    return JsonResponse({'unread_notifications_count': count})

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
        seccoes = Seccoes.objects.filter(Departamento_id=departamento_id, ativo=True).order_by('nome')
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
        departamento_usuario = user.seccao.Departamento
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
        ).order_by('-data_armazenamento')
        titulo = f'Histórico de Armazenamento - {documento.numero_protocolo}'
    else:
        # Lista todos armazenamentos ativos do departamento do usuário
        departamento_usuario = None
        if hasattr(user, 'seccao') and user.seccao:
            departamento_usuario = user.seccao.Departamento
        elif hasattr(user, 'departamento') and user.departamento:
            departamento_usuario = user.departamento
        
        if departamento_usuario:
            armazenamentos = ArmazenamentoDocumento.objects.filter(
                Q(local_armazenamento__departamento=departamento_usuario) |
                Q(registrado_por__departamento=departamento_usuario),
                ativo=True
            ).order_by('-data_armazenamento')
        else:
            armazenamentos = ArmazenamentoDocumento.objects.none()
        
        documento = None
        titulo = 'Documentos Armazenados'
    
    # Paginação
    paginator = Paginator(armazenamentos, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'armazenamentos': page_obj,
        'documento': documento,
        'titulo': titulo,
    }
    
    return render(request, 'lista_armazenamentos.html', context)
