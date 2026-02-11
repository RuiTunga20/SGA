"""
hierarchy_manager.py
=====================

Gerenciador centralizado para hierarquia de Departamentos e Secções.

Este módulo fornece:
- Cálculo de destinos permitidos (departamentos e secções)
- Validação de acessos IDOR
- Métodos reutilizáveis por todos os formulários

A lógica é agnóstica ao contexto (encaminhamento, criação de usuário, etc).
"""

from django.db.models import Q
from .models import Administracao, Departamento, Seccoes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_secretaria_geral(departamento) -> bool:
    """Verifica se um departamento é Secretaria Geral."""
    if not departamento:
        return False
    return "secretaria geral" in departamento.nome.lower()


def _get_contexto_usuario(user):
    """
    Retorna o contexto resolvido do usuário.
    
    Returns:
        dict com chaves: 'admin', 'dept', 'seccao', 'em_seccao'
    """
    admin = getattr(user, 'administracao', None)
    dept = getattr(user, 'departamento_efetivo', None)
    seccao = getattr(user, 'seccao', None)
    
    # Validar seccão
    if seccao and not seccao.pk:
        seccao = None
    
    return {
        'admin': admin,
        'dept': dept,
        'seccao': seccao,
        'em_seccao': seccao is not None,
    }


# ---------------------------------------------------------------------------
# API Pública
# ---------------------------------------------------------------------------

class HierarchyManager:
    """
    Gerenciador centralizado de hierarquia.
    
    Uso:
        manager = HierarchyManager(user)
        depts, seccoes, seccoes_fixas = manager.obter_destinos_permitidos()
        
        # Validar se um destino é permitido
        is_valid = manager.validar_departamento(dept_id)
    """
    
    def __init__(self, user):
        self.user = user
        self.ctx = _get_contexto_usuario(user)
    
    def obter_destinos_permitidos(self, incluir_self=True):
        """
        Calcula os querysets de departamentos e secções permitidos.
        
        Args:
            incluir_self (bool): Se True, inclui o próprio departamento/secção do usuário
        
        Returns:
            tuple(QuerySet[Departamento], QuerySet[Seccoes], bool)
            - QuerySet de departamentos
            - QuerySet de secções
            - bool: True se secções são FIXAS, False se dinâmicas
        """
        return _calcular_destinos_permitidos(
            self.user,
            self.ctx,
            incluir_self=incluir_self
        )
    
    def obter_departamentos(self, incluir_self=True):
        """Retorna apenas os departamentos permitidos."""
        depts, _, _ = self.obter_destinos_permitidos(incluir_self=incluir_self)
        return depts
    
    def obter_seccoes(self, incluir_self=True):
        """Retorna apenas as secções permitidas."""
        _, seccoes, _ = self.obter_destinos_permitidos(incluir_self=incluir_self)
        return seccoes
    
    def seccoes_sao_fixas(self):
        """Retorna True se as secções do usuário são fixas (não mudam com dept selecionado)."""
        _, _, seccoes_fixas = self.obter_destinos_permitidos()
        return seccoes_fixas
    
    def validar_departamento(self, dept_id):
        """Verifica se um departamento é permitido para o usuário."""
        depts, _, _ = self.obter_destinos_permitidos(incluir_self=False)
        return depts.filter(pk=dept_id).exists()
    
    def validar_seccao(self, seccao_id):
        """Verifica se uma secção é permitida para o usuário."""
        _, seccoes, _ = self.obter_destinos_permitidos(incluir_self=False)
        return seccoes.filter(pk=seccao_id).exists()
    
    @staticmethod
    def obter_seccoes_para_departamento(user, dept_id):
        """
        Retorna as secções de um departamento específico.
        Útil para população via AJAX/JavaScript.
        
        Returns:
            list[dict]: [{'id': 1, 'nome': 'Secção A'}, ...]
        """
        ctx = _get_contexto_usuario(user)
        admin = ctx['admin']
        dept_user = ctx['dept']
        
        if not admin:
            return []
        
        # Validar que o departamento solicitado é permitido
        depts_permitidos, _, _ = _calcular_destinos_permitidos(user, ctx, incluir_self=False)
        if not depts_permitidos.filter(pk=dept_id).exists():
            return []  # Não permitido
        
        # Retornar secções do departamento
        return list(
            Seccoes.objects.filter(
                departamento_id=dept_id
            ).values('id', 'nome')
        )


# ---------------------------------------------------------------------------
# Lógica Central
# ---------------------------------------------------------------------------

def _calcular_destinos_permitidos(user, ctx=None, incluir_self=True):
    """
    Calcula os querysets de departamentos e secções permitidos.
    
    Args:
        user: CustomUser
        ctx: dict retornado por _get_contexto_usuario (calculado se None)
        incluir_self: Se False, exclui o próprio departamento/secção
    
    Returns:
        tuple(QuerySet[Departamento], QuerySet[Seccoes], bool)
        - QuerySet de departamentos
        - QuerySet de secções
        - bool: True se secções são FIXAS (Cenário B), False se dependem do dept (Cenário A)
    """
    
    if ctx is None:
        ctx = _get_contexto_usuario(user)
    
    admin   = ctx['admin']
    dept    = ctx['dept']
    seccao  = ctx['seccao']
    em_seccao = ctx['em_seccao']

    # Superuser sem administração
    if not admin:
        if user.is_superuser:
            depts = Departamento.objects.all().order_by('administracao__nome', 'nome')
            if not incluir_self and dept:
                depts = depts.exclude(pk=dept.pk)
            
            seccoes = Seccoes.objects.all().order_by('departamento__nome', 'nome')
            if not incluir_self and seccao:
                seccoes = seccoes.exclude(pk=seccao.pk)
            
            return depts, seccoes, False
        
        return Departamento.objects.none(), Seccoes.objects.none(), False

    # =========================================================================
    # PARTE 1: Calcular queryset BASE de departamentos (hierarquia MAT/GOV/Municipal)
    # =========================================================================

    # MAT (Ministério)
    if admin.tipo_municipio == 'M':
        governos_ids = Administracao.objects.filter(
            tipo_municipio='G'
        ).values_list('id', flat=True)

        qs_dept_base = Departamento.objects.filter(
            Q(administracao=admin) |
            Q(administracao_id__in=governos_ids, nome__icontains='Secretaria Geral')
        ).distinct()

    # Governo Provincial
    elif admin.tipo_municipio == 'G':
        admins_municipais_ids = Administracao.objects.filter(
            provincia=admin.provincia
        ).exclude(tipo_municipio__in=['G', 'M']).values_list('id', flat=True)

        mat_ids = Administracao.objects.filter(
            tipo_municipio='M'
        ).values_list('id', flat=True)

        qs_dept_base = Departamento.objects.filter(
            Q(administracao=admin) |
            Q(administracao_id__in=admins_municipais_ids, nome__icontains='Secretaria Geral') |
            Q(administracao_id__in=mat_ids, nome__icontains='Secretaria Geral')
        ).distinct()

    # Secretaria Geral de Municipal
    elif _is_secretaria_geral(dept):
        governo_prov = Administracao.objects.filter(
            provincia=admin.provincia,
            tipo_municipio='G',
        ).first()

        qs_dept_base = Departamento.objects.filter(
            Q(administracao=admin) |
            (Q(administracao=governo_prov, nome__icontains='Secretaria Geral') if governo_prov else Q(pk__in=[]))
        ).distinct()

    # Padrão
    else:
        qs_dept_base = Departamento.objects.para_administracao(admin)

    # =========================================================================
    # PARTE 2: Aplicar restrições por cenário
    # =========================================================================

    if em_seccao:
        # -----------------------------------------------------------------
        # CENÁRIO A: Usuário em Secção
        # - Dept disponível: APENAS o dept pai (ou nenhum se incluir_self=False)
        # - Secções disponíveis: todas do mesmo dept, exceto a própria
        # - Secções são DINÂMICAS (dependem do dept, mas dept é único)
        # -----------------------------------------------------------------
        if incluir_self:
            qs_dept_final = qs_dept_base.filter(pk=dept.pk) if dept else Departamento.objects.none()
        else:
            qs_dept_final = Departamento.objects.none()
        
        qs_sec_final = Seccoes.objects.filter(
            departamento=dept,
        ).exclude(
            pk=seccao.pk,
        ).order_by('nome') if dept else Seccoes.objects.none()
        
        seccoes_fixas = False

    else:
        # -----------------------------------------------------------------
        # CENÁRIO B: Usuário em Departamento
        # - Dept disponível: todos do base, exceto o próprio (se incluir_self=False)
        # - Secções disponíveis: SEMPRE as do departamento DO USUÁRIO
        # - Secções são FIXAS: não mudam ao selecionar dept
        # -----------------------------------------------------------------
        if incluir_self:
            qs_dept_final = qs_dept_base.order_by('administracao__nome', 'nome')
        else:
            qs_dept_final = qs_dept_base.exclude(
                pk=dept.pk if dept else -1
            ).order_by('administracao__nome', 'nome')
        
        qs_sec_final = Seccoes.objects.filter(
            departamento=dept,
            departamento__administracao=admin,
        ).order_by('nome') if dept else Seccoes.objects.none()
        
        seccoes_fixas = True

    return qs_dept_final, qs_sec_final, seccoes_fixas


# ---------------------------------------------------------------------------
# Funções de Validação (para uso em clean() dos formulários)
# ---------------------------------------------------------------------------

def validar_destino_encaminhamento(user, dept_id=None, seccao_id=None):
    """
    Valida se um destino de encaminhamento é permitido.
    
    Args:
        user: CustomUser
        dept_id: ID do departamento (pode ser None)
        seccao_id: ID da secção (pode ser None)
    
    Returns:
        (is_valid, error_message)
    """
    if not dept_id and not seccao_id:
        return False, 'Selecione um departamento OU uma secção de destino.'
    
    if dept_id and seccao_id:
        return False, 'Escolha APENAS o departamento OU a secção, não ambos.'
    
    manager = HierarchyManager(user)
    
    if dept_id:
        if not manager.validar_departamento(dept_id):
            return False, 'O departamento selecionado não é um destino permitido para seu perfil.'
    
    if seccao_id:
        if not manager.validar_seccao(seccao_id):
            return False, 'A secção selecionada não é um destino permitido para seu perfil.'
    
    return True, None


def obter_label_dinamico(user, contexto='encaminhamento'):
    """
    Retorna labels dinâmicos baseados no tipo de administração do usuário.
    
    Args:
        user: CustomUser
        contexto: 'encaminhamento' | 'criacao_usuario' | etc
    
    Returns:
        dict com labels para departamento e secção
    """
    ctx = _get_contexto_usuario(user)
    admin = ctx['admin']
    
    labels = {
        'departamento': 'Departamento',
        'seccao': 'Secção',
    }
    
    if not admin:
        return labels
    
    if contexto == 'encaminhamento':
        if admin.tipo_municipio == 'M':
            labels['departamento'] = 'Destino (Interno ou Governo Provincial)'
        elif admin.tipo_municipio == 'G':
            labels['departamento'] = 'Destino (Interno, Municipal ou MAT)'
        
        if ctx['em_seccao']:
            labels['seccao'] = 'OU Encaminhar para Secção (do seu departamento)'
        else:
            labels['seccao'] = 'OU Encaminhar para Secção'
    
    return labels
