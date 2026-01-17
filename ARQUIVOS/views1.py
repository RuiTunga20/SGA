from django.shortcuts import render
from django.utils import timezone

# Create your views here.
# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.db import transaction
from .formularios import *
from django.db.models import Count, Case, When, IntegerField
from django.urls import reverse


@login_required
def dashboard(request):
    """
    Dashboard com estatísticas focadas no departamento do utilizador.
    """
    seccao = None
    user = request.user
    hoje = timezone.now().date()
    departamento_usuario = user.departamento
    print(user.seccao.departamento,departamento_usuario)
    if not departamento_usuario :
        departamento_usuario=user.seccao.departamento
    # Se o utilizador não tiver um departamento, redireciona ou mostra erro
    if not departamento_usuario :

        messages.error(request, 'Você não está associado a nenhum departamento.')
        return redirect('/') # Ou outra página apropriada

    # --- ESTATÍSTICAS DO DEPARTAMENTO ---

    # 1. Documentos pendentes no meu departamento (status 'em_analise' ou 'recebido')
    documentos_pendentes = MovimentacaoDocumento.objects.filter(
        departamento_destino=departamento_usuario,
        tipo_movimentacao='encaminhamento',
        confirmado_recebimento=False,
        data_movimentacao__date=hoje
    ).count()

    # 2. Total de documentos encaminhados PELO meu departamento HOJE
    documentos_encaminhados_hoje = MovimentacaoDocumento.objects.filter(
        departamento_origem=departamento_usuario,
        tipo_movimentacao='encaminhamento',
        data_movimentacao__date=hoje
    ).count()

    # 3. Total de documentos registados PELO meu departamento HOJE
    documentos_registados_hoje = Documento.objects.filter(
        departamento_origem=departamento_usuario,
        data_criacao__date=hoje
    ).count()

    # 4. Total de documentos existentes ATUALMENTE no meu departamento
    total_documentos_no_departamento = Documento.objects.filter(
        departamento_atual=departamento_usuario
    ).count()

    # 5. Documentos mortos (arquivados) que PERTENCEM ao meu departamento
    documentos_mortos = Documento.objects.filter(
        departamento_atual=departamento_usuario,
        status='arquivado' # Assumindo que o status final é 'arquivado'
    ).count()

    context = {
        'departamento_nome': departamento_usuario.nome,
        'documentos_pendentes': documentos_pendentes,
        'documentos_encaminhados_hoje': documentos_encaminhados_hoje,
        'documentos_registados_hoje': documentos_registados_hoje,
        'total_documentos_no_departamento': total_documentos_no_departamento,
        'documentos_mortos': documentos_mortos,
    }

    return render(request, 'Paginasdashboard.html', context)


def estatisticas_aggregate(departamento):
    """
    Versão usando aggregate para ser mais eficiente
    """
    resultado = MovimentacaoDocumento.objects.filter(
        Q(departamento_origem=departamento) | Q(departamento_destino=departamento)
    ).aggregate(
        recebidos=Count(
            Case(
                When(
                    tipo_movimentacao='criacao',
                    departamento_destino=departamento,
                    then=1
                ),
                output_field=IntegerField()
            )
        ),
        reencaminhados=Count(
            Case(
                When(
                    tipo_movimentacao='encaminhamento',
                    departamento_origem=departamento,
                    then=1
                ),
                output_field=IntegerField()
            )
        ),
        com_despacho=Count(
            Case(
                When(
                    tipo_movimentacao='despacho',
                    then=1
                ),
                output_field=IntegerField()
            )
        )
    )

    return resultado


@login_required
def listar_documentos(request):
    """
    Lista documentos com filtros e busca
    """
    user = request.user
    documentos = Documento.objects.filter(departamento_atual=user.departamento)
    dados = estatisticas_aggregate(user.departamento)
    print(user.nivel_acesso)

    # Filtro por nível de acesso
    if user.nivel_acesso  in ['admin', 'diretor']:
        documentos = Documento.objects.all()

    # Filtros da URL
    status = request.GET.get('status')
    departamento = request.GET.get('departamento')
    tipo_doc = request.GET.get('tipo')
    prioridade = request.GET.get('prioridade')
    busca = request.GET.get('q')

    if status:
        documentos = documentos.filter(status=status)
    if departamento:
        documentos = documentos.filter(departamento_atual_id=departamento)
    if tipo_doc:
        documentos = documentos.filter(tipo_documento_id=tipo_doc)
    if prioridade:
        documentos = documentos.filter(prioridade=prioridade)
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
            'status': status,
            'departamento': departamento,
            'tipo': tipo_doc,
            'prioridade': prioridade,
            'busca': busca,
        }
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
    Exibe detalhes completos do documento
    """
    documento = get_object_or_404(Documento, id=documento_id)
    user = request.user

    # Verificar permissão de acesso
    if user.nivel_acesso not in ['admin', 'diretor']:
        if not (documento.departamento_atual == user.departamento or
                documento.departamento_origem == user.departamento or
                documento.criado_por == user):
            messages.error(request, 'Você não tem permissão para acessar este documento.')
            return redirect('listar_documentos')

    # Histórico de movimentações
    movimentacoes = documento.movimentacoes.all().order_by('-data_movimentacao')

    # Formulário para nova movimentação
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'confirmar_recebimento':
            movimentacao_id = request.POST.get('movimentacao_id')
            movimentacao = get_object_or_404(MovimentacaoDocumento, id=movimentacao_id)
            movimentacao.confirmado_recebimento = True
            movimentacao.data_confirmacao = timezone.now()
            movimentacao.usuario_confirmacao = user
            movimentacao.save()
            # --- INÍCIO DA LÓGICA DE NOTIFICAÇÃO ---
            # Notificar o utilizador que enviou o documento
            utilizador_que_enviou = movimentacao.usuario
            if utilizador_que_enviou:
                link_documento = request.build_absolute_uri(
                    reverse('detalhe_documento', args=[documento.id])
                )
                Notificacao.objects.create(
                    usuario=utilizador_que_enviou,
                    mensagem=f"O recebimento do documento '{documento.numero_protocolo}' foi confirmado por {user.username}.",
                    link=link_documento
                )
            # --- FIM DA LÓGICA DE NOTIFICAÇÃO ---
            messages.success(request, 'Recebimento confirmado com sucesso!')
            return redirect('detalhe_documento', documento_id=documento.id)


        elif action == 'encaminhar':
            # Passamos os argumentos 'user' e 'documento' que faltavam
            form = EncaminharDocumentoForm(request.POST, user=request.user, documento=documento)
            print(form.errors)
            if form.is_valid():
                # Criar nova movimentação
                MovimentacaoDocumento.objects.create(
                    documento=documento,
                    tipo_movimentacao='encaminhamento',
                    departamento_origem=documento.departamento_atual,
                    departamento_destino=form.cleaned_data['departamento_destino'],
                    usuario=user,
                    observacoes=form.cleaned_data['observacoes'],
                    despacho=form.cleaned_data.get('despacho', '')
                )

                # Atualizar documento
                documento.departamento_atual = form.cleaned_data['departamento_destino']
                documento.status = 'encaminhamento'
                documento.save()
                # --- INÍCIO DA CORREÇÃO (ADICIONAR NOTIFICAÇÃO) ---
                departamento_destino_obj = form.cleaned_data['departamento_destino']
                utilizadores_a_notificar = CustomUser.objects.filter(departamento=departamento_destino_obj)

                link_documento = request.build_absolute_uri(
                    reverse('detalhe_documento', args=[documento.id])
                )

                for u in utilizadores_a_notificar:
                    Notificacao.objects.create(
                        usuario=u,
                        mensagem=f"O documento '{documento.numero_protocolo}' foi encaminhado para o seu departamento.",
                        link=link_documento
                    )
                # --- FIM DA CORREÇÃO ---

                messages.success(request, 'Documento encaminhado com sucesso!')
                return redirect('detalhe_documento', documento_id=documento.id)

        elif action == 'despacho':
            form = DespachoForm(request.POST)
            if form.is_valid():
                # Criar movimentação de despacho
                MovimentacaoDocumento.objects.create(
                    documento=documento,
                    tipo_movimentacao='despacho',
                    departamento_origem=documento.departamento_atual,
                    usuario=user,
                    despacho=form.cleaned_data['despacho'],
                    observacoes=form.cleaned_data.get('observacoes', '')
                )
                # Atualizar status se necessário
                status = form.cleaned_data.get('novo_status')
                if status:
                    documento.status = status
                    if status in ['aprovado', 'rejeitado', 'arquivado']:
                        documento.data_conclusao = timezone.now()
                    documento.save()

                messages.success(request, 'Despacho registrado com sucesso!')
                return redirect('detalhe_documento', documento_id=documento.id)
        elif action in ['aprovado', 'reprovado', 'arquivado']:
            novo_status = action
            with transaction.atomic():
                # Criar a movimentação correspondente
                MovimentacaoDocumento.objects.create(
                    documento=documento, tipo_movimentacao=novo_status,
                    departamento_origem=documento.departamento_atual, usuario=user,
                    observacoes=f'Documento marcado como "{novo_status.capitalize()}" por {user.username}.'
                )
                # Atualizar o documento principal
                documento.status = novo_status
                documento.data_conclusao = timezone.now()
                documento.save()

                # Notificar o criador do documento sobre a ação final
                if documento.criado_por != user:
                    link_documento = request.build_absolute_uri(reverse('detalhe_documento', args=[documento.id]))
                    Notificacao.objects.create(
                        usuario=documento.criado_por,
                        mensagem=f"O seu documento '{documento.numero_protocolo}' foi finalizado com o status '{novo_status.capitalize()}'.",
                        link=link_documento
                    )
            messages.success(request, f'Documento marcado como "{novo_status.capitalize()}" com sucesso!')
            return redirect('listar_documentos')  # Redireciona para a lista após uma ação final

    # Formulários para ações
    # Passamos os argumentos 'user' e 'documento' que faltavam
    encaminhar_form = EncaminharDocumentoForm(user=request.user, documento=documento)
    despacho_form = DespachoForm()

    # Movimentações pendentes de confirmação para este usuário
    movimentacoes_pendentes = MovimentacaoDocumento.objects.filter(
        documento=documento,
        departamento_destino=user.departamento,
        confirmado_recebimento=False,
        tipo_movimentacao='encaminhamento'
    )

    context = {
        'documento': documento,
        'movimentacoes': movimentacoes,
        'movimentacoes_pendentes': movimentacoes_pendentes,
        'encaminhar_form': encaminhar_form,
        'despacho_form': despacho_form,
        'pode_editar': user.nivel_acesso in ['admin', 'diretor'] or documento.criado_por == user,
        'pode_encaminhar': documento.departamento_atual == user.departamento,
    }

    return render(request, 'Paginasdetalhe.html', context)


@login_required
def criar_documento(request):
    """
    Criar novo documento
    """
    dados = estatisticas_aggregate(request.user.departamento)

    if request.method == 'POST':
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.criado_por = request.user

            # VERIFICAÇÃO 1: Certifique-se de que o usuário tem departamento
            if not hasattr(request.user, 'departamento') or request.user.departamento is None:
                messages.error(request,
                               'Usuário não possui departamento associado. Entre em contato com o administrador.')
                return render(request, 'Paginascriar.html', {'form': form})

            documento.departamento_origem = request.user.departamento
            documento.departamento_atual = request.user.departamento
            documento.responsavel_atual = request.user

            # SALVAR PRIMEIRO o documento
            documento.save()

            # Depois criar a movimentação
            mv = MovimentacaoDocumento.objects.create(
                documento=documento,
                tipo_movimentacao='encaminhamento',
                departamento_origem=request.user.departamento,
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

    try:
        movimentacao = MovimentacaoDocumento.objects.get(id=documento_id)
        documento = movimentacao.documento
    except MovimentacaoDocumento.DoesNotExist:
        messages.error(request, 'Movimentação não encontrada.')
        return redirect('lista_documentos')

    # A sua lógica de permissões original (mantida)
    if not request.user.has_perm('ARQUIVOS.change_movimentacaodocumento'):
        messages.error(request, 'Você não tem permissão para editar esta movimentação.')
        return redirect('detalhe_documento', documento_id=movimentacao.documento.id)

    if request.method == 'POST':
        form = EncaminharDocumentoForm(request.POST, instance=movimentacao, user=request.user, documento=documento)

        if form.is_valid():
            # NOVA ADIÇÃO: Usar uma transação para garantir que ambas as operações funcionem ou nenhuma funcione.
            try:
                with transaction.atomic():
                    # 1. Salvar a movimentação (sua lógica original)
                    movimentacao_atualizada = form.save(commit=False)
                    movimentacao_atualizada.departamento_origem = request.user.departamento
                    # Se tiver estes campos no modelo, eles serão atualizados
                    # movimentacao_atualizada.data_edicao = timezone.now()
                    # movimentacao_atualizada.editado_por = request.user
                    movimentacao_atualizada.save()

                    # --- INÍCIO DAS ADIÇÕES SOLICITADAS ---

                    # 2. Obter o documento principal que precisa de ser atualizado
                    documento_a_atualizar = movimentacao_atualizada.documento

                    # 3. Sincronizar o STATUS do Documento
                    # O status do documento principal passa a ser o tipo da movimentação que acabou de ser salva.
                    documento_a_atualizar.status = movimentacao_atualizada.tipo_movimentacao

                    # 4. Sincronizar o DEPARTAMENTO ATUAL do Documento
                    # Se a movimentação tiver um destino, o documento passa a "estar" nesse departamento.
                    if movimentacao_atualizada.departamento_destino:
                        documento_a_atualizar.departamento_atual = movimentacao_atualizada.departamento_destino

                    # 5. [BÓNUS] Sincronizar a DATA DE CONCLUSÃO do Documento
                    # Se a movimentação for uma ação final, preenchemos a data de conclusão.
                    if movimentacao_atualizada.tipo_movimentacao in ['aprovado', 'rejeitado', 'arquivado']:
                        documento_a_atualizar.data_conclusao = timezone.now()

                    # 6. Salvar as alterações no Documento principal
                    documento_a_atualizar.save()
                    if documento.status == 'encaminhamento':

                        departamento_destino = documento.departamento_atual
                        utilizadores_a_notificar = CustomUser.objects.filter(departamento=departamento_destino)

                        link_documento = request.build_absolute_uri(
                            reverse('detalhe_documento', args=[documento.id])
                        )

                        for u in utilizadores_a_notificar:
                            Notificacao.objects.create(
                                usuario=u,
                                mensagem=f"O documento '{documento.numero_protocolo}' foi encaminhado para o seu departamento.",
                                link=link_documento
                            )

                    # --- FIM DAS ADIÇÕES SOLICITADAS ---

                messages.success(request, 'Movimentação do documento atualizada com sucesso!')
                return redirect('listar_movimento')

            except Exception as e:
                # Se ocorrer um erro em qualquer passo, a transação é revertida.
                messages.error(request, f"Ocorreu um erro inesperado: {e}")
                print(e)

        else:
            messages.error(request, 'Corrija os erros abaixo.')
    else:
        # A sua lógica GET original (mantida)
        form = EncaminharDocumentoForm(instance=movimentacao, user=request.user, documento=documento)

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
def pendencias(request):
    """
    Lista documentos pendentes de confirmação de recebimento
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

    return render(request, 'Paginaspendencias.html', context)


@login_required
def confirmar_recebimento(request, movimentacao_id):
    # Esta view só deve aceitar pedidos POST
    if request.method == 'POST':
        movimentacao = get_object_or_404(MovimentacaoDocumento, id=movimentacao_id)

        # Verifica se o utilizador pertence ao departamento de destino
        if request.user.departamento == movimentacao.departamento_destino:
            # 1. Confirma o recebimento na movimentação
            movimentacao.confirmado_recebimento = True
            movimentacao.save()

            # 2. Atualiza o departamento atual do documento principal
            documento = movimentacao.documento
            documento.departamento_atual = movimentacao.departamento_destino
            documento.save()

            messages.success(request, f'Recebimento do documento "{documento.titulo}" confirmado com sucesso!')
        else:
            messages.error(request, 'Você não tem permissão para confirmar este recebimento.')

        # Redireciona de volta para a página de pendências
        return redirect('detalhe_documento', documento_id=documento.id)

    # Se alguém tentar aceder a esta URL via GET, apenas redireciona
    return redirect('pendencias')
@login_required
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
    """
    Esta view serve como um endpoint de API para o JavaScript.
    Ela conta as notificações não lidas e retorna o número em formato JSON.
    """
    if request.user.is_authenticated:
        count = Notificacao.objects.filter(usuario=request.user, lida=False).count()
        return JsonResponse({'unread_notifications_count': count})

    # Se por alguma razão o user não estiver autenticado, retorna 0
    return JsonResponse({'unread_notifications_count': 0})


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