# forms.py
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from .models import *
from .models import StatusDocumento

from django import forms
from django.core.exceptions import ValidationError
class DocumentoForm(forms.ModelForm):
    """
    Formulário para criação e edição de documentos
    """

    class Meta:
        model = Documento
        fields = [
            'titulo', 'tipo_documento', 'prioridade',
            'arquivo', 'arquivo_digitalizado', 'tags', 'observacoes','utente','telefone','email','origem','niveis','referencia',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Digite o título do documento',
                'maxlength': '200',
                'required': True,
            }),
            'utente': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Digite o Nome',
                'maxlength': '200',
                'required': True,
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Digite o Email',
                'maxlength': '200',
                'required': True,
            }),



            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'prioridade': forms.Select(attrs={
                'class': 'form-select',
                'choices': [
                    ('baixa', '🟢 Baixa'),
                    ('normal', '🟡 Normal'),
                    ('alta', '🟠 Alta'),
                    ('urgente', '🔴 Urgente')
                ]
            }),
            'arquivo': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
            }),
            'arquivo_digitalizado': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'O numero do Armario pasta  Armario-1/doc-335',
                'maxlength': '500'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Observações adicionais'

            }),
        }


"""
EncaminharDocumentoForm — CORRIGIDO: Secções no Cenário B
===========================================================
PROBLEMA IDENTIFICADO:
  No Cenário B (usuário em departamento), as secções devem ser:
  - SEMPRE do departamento do USUÁRIO (não do dept selecionado)
  - Permite encaminhar para uma secção específica interna
  
SOLUÇÃO:
  - Cenário A: secções mudam conforme dept selecionado (é o dept pai fixo)
  - Cenário B: secções FIXAS (do dept do usuário), independente da seleção
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
import json

from .models import (
    Administracao,
    CustomUser,
    Departamento,
    MovimentacaoDocumento,
    Seccoes,
    StatusDocumento,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_secretaria_geral(departamento) -> bool:
    """Verifica se um departamento é Secretaria Geral."""
    if not departamento:
        return False
    return "secretaria geral" in departamento.nome.lower()


def _get_contexto_usuario(user):
    """Retorna o contexto resolvido do usuário."""
    admin = getattr(user, 'administracao', None)
    dept = getattr(user, 'departamento_efetivo', None)
    seccao = getattr(user, 'seccao', None)
    
    if seccao and not seccao.pk:
        seccao = None
    
    return {
        'admin': admin,
        'dept': dept,
        'seccao': seccao,
        'em_seccao': seccao is not None,
    }


# ---------------------------------------------------------------------------
# Lógica central de hierarquia
# ---------------------------------------------------------------------------

def _calcular_destinos_permitidos(user):
    """
    Calcula os querysets de departamentos e secções permitidos.
    
    Returns:
        tuple(QuerySet[Departamento], QuerySet[Seccoes], bool)
        - QuerySet de departamentos
        - QuerySet de secções
        - bool: True se secções são FIXAS (Cenário B), False se dependem do dept selecionado (Cenário A)
    """
    ctx = _get_contexto_usuario(user)
    admin   = ctx['admin']
    dept    = ctx['dept']
    seccao  = ctx['seccao']
    em_seccao = ctx['em_seccao']

    # Superuser sem administração
    if not admin:
        if user.is_superuser:
            return (
                Departamento.objects.all().order_by('administracao__nome', 'nome'),
                Seccoes.objects.all().order_by('departamento__nome', 'nome'),
                False  # Superuser: secções dinâmicas
            )
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
        # - Dept disponível: APENAS o dept pai
        # - Secções disponíveis: todas do mesmo dept, exceto a própria
        # - Secções são DINÂMICAS: filtradas pelo dept selecionado (que é único)
        # -----------------------------------------------------------------
        qs_dept_final = qs_dept_base.filter(pk=dept.pk) if dept else Departamento.objects.none()
        
        qs_sec_final = Seccoes.objects.filter(
            departamento=dept,
        ).exclude(
            pk=seccao.pk,
        ).order_by('nome') if dept else Seccoes.objects.none()
        
        seccoes_fixas = False  # Secções mudam com the dept (mas dept é único, então na prática são fixas)

    else:
        # -----------------------------------------------------------------
        # CENÁRIO B: Usuário em Departamento
        # - Dept disponível: todos do base, exceto o próprio
        # - Secções disponíveis: SEMPRE as secções do departamento DO USUÁRIO
        # - Secções são FIXAS: independem do dept selecionado no select
        # -----------------------------------------------------------------
        qs_dept_final = qs_dept_base.exclude(
            pk=dept.pk if dept else -1
        ).order_by('administracao__nome', 'nome')
        
        # CORREÇÃO CRÍTICA: Secções do departamento DO USUÁRIO, não do selecionado
        qs_sec_final = Seccoes.objects.filter(
            departamento=dept,
            departamento__administracao=admin,
        ).order_by('nome') if dept else Seccoes.objects.none()
        
        seccoes_fixas = True  # Secções não mudam ao selecionar dept

    return qs_dept_final, qs_sec_final, seccoes_fixas


# ---------------------------------------------------------------------------
# Formulário
# ---------------------------------------------------------------------------

class EncaminharDocumentoForm(forms.ModelForm):

    class Meta:
        model = MovimentacaoDocumento
        fields = [
            'tipo_movimentacao',
            'departamento_destino',
            'seccao_destino',
            'observacoes',
            'despacho',
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Observações sobre o encaminhamento...',
            }),
            'despacho': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Despacho ou instruções...',
            }),
            'tipo_movimentacao': forms.Select(attrs={'class': 'form-control'}),
            'departamento_destino': forms.Select(attrs={
                'class': 'form-control',
                'data-exclusivo': 'seccao_destino'
            }),
            'seccao_destino': forms.Select(attrs={
                'class': 'form-control',
                'data-exclusivo': 'departamento_destino'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user      = kwargs.pop('user', None)
        self.documento = kwargs.pop('documento', None)

        super().__init__(*args, **kwargs)

        if self.documento:
            self.instance.documento = self.documento

        # Choices de tipo de movimentação
        self.fields['tipo_movimentacao'].choices = [
            ('criacao',        'Criar'),
            ('encaminhamento', 'Encaminhar'),
        ]

        self.fields['departamento_destino'].required = False
        self.fields['seccao_destino'].required = False

        # Popula os querysets
        if self.user:
            qs_dept, qs_sec, seccoes_fixas = _calcular_destinos_permitidos(self.user)

            self.fields['departamento_destino'].queryset = qs_dept
            self.fields['seccao_destino'].queryset = qs_sec
            
            # Armazena se as secções são fixas (para o template saber)
            self.seccoes_fixas = seccoes_fixas
            
            # Prepara dados JSON para o JavaScript (se secções forem dinâmicas)
            if not seccoes_fixas:
                # Cenário A: precisamos enviar mapa dept_id -> secções
                # Como só há 1 dept possível, simplificamos
                self.seccoes_data = {}
                if qs_dept.exists():
                    dept_id = qs_dept.first().pk
                    self.seccoes_data[dept_id] = list(
                        qs_sec.values('id', 'nome')
                    )
            else:
                # Cenário B: secções já estão no queryset, não precisa mapa
                self.seccoes_data = None

            # Labels dinâmicos
            ctx = _get_contexto_usuario(self.user)
            admin = ctx['admin']
            if admin:
                if admin.tipo_municipio == 'M':
                    self.fields['departamento_destino'].label = 'Destino (Interno ou Governo Provincial)'
                elif admin.tipo_municipio == 'G':
                    self.fields['departamento_destino'].label = 'Destino (Interno, Municipal ou MAT)'
                else:
                    self.fields['departamento_destino'].label = 'Encaminhar para Departamento'
                    
            # Label para secções
            if seccoes_fixas:
                self.fields['seccao_destino'].label = 'OU Encaminhar para Secção (do seu departamento)'
            else:
                self.fields['seccao_destino'].label = 'OU Encaminhar para Secção'
        else:
            self.fields['departamento_destino'].queryset = Departamento.objects.none()
            self.fields['seccao_destino'].queryset = Seccoes.objects.none()
            self.seccoes_fixas = False
            self.seccoes_data = None

        self.fields['seccao_destino'].label_from_instance = lambda obj: obj.nome

    def clean(self):
        cleaned_data  = super().clean()
        dept_destino  = cleaned_data.get('departamento_destino')
        sec_destino   = cleaned_data.get('seccao_destino')
        tipo_mov      = cleaned_data.get('tipo_movimentacao')

        # Regra 1: encaminhamento exige um destino
        if tipo_mov == 'encaminhamento' and not dept_destino and not sec_destino:
            raise ValidationError(
                'Para encaminhar, selecione UM departamento OU uma secção de destino.'
            )

        # Regra 2: exclusividade mútua
        if dept_destino and sec_destino:
            raise ValidationError(
                'Escolha APENAS o departamento OU a secção de destino, não ambos.'
            )

        # Regra 3: validação de segurança (IDOR protection)
        if self.user and (dept_destino or sec_destino):
            qs_dept_valido, qs_sec_valida, _ = _calcular_destinos_permitidos(self.user)

            if dept_destino and not qs_dept_valido.filter(pk=dept_destino.pk).exists():
                raise ValidationError(
                    'O departamento selecionado não é um destino permitido para o seu perfil.'
                )

            if sec_destino and not qs_sec_valida.filter(pk=sec_destino.pk).exists():
                raise ValidationError(
                    'A secção selecionada não é um destino permitido para o seu perfil.'
                )

        return cleaned_data

class DespachoForm(forms.Form):
    """
    Formulário para registrar despacho em documento
    """
    STATUS_CHOICES = [
        ('', 'Manter status atual'),
        (StatusDocumento.APROVADO, 'Aprovar'),
        (StatusDocumento.REPROVADO, 'Rejeitar'),
        (StatusDocumento.ARQUIVADO, 'Arquivar'),
    ]

    despacho = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Digite seu despacho/parecer'
        }),
        label='Despacho/Parecer',
        required=True
    )

    novo_status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Alterar Status',
        required=False
    )

    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observações adicionais (opcional)'
        }),
        label='Observações',
        required=False
    )


class BuscaAvancadaForm(forms.Form):
    """
    Formulário para busca avançada de documentos
    """
    titulo = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar no título'
        }),
        required=False
    )

    conteudo = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar no conteúdo'
        }),
        required=False
    )

    numero_protocolo = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número do protocolo'
        }),
        required=False
    )

    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label='Todos os tipos'
    )

    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label='Todos os departamentos'
    )

    status = forms.ChoiceField(
        choices=[('', 'Todos')] + StatusDocumento.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    prioridade = forms.ChoiceField(
        choices=[('', 'Todas')] + Documento.PRIORIDADE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    data_inicio = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False,
        label='Data Início'
    )

    data_fim = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False,
        label='Data Fim'
    )

    tags = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tags separadas por vírgula'
        }),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.administracao:
            self.fields['departamento'].queryset = Departamento.objects.filter(
                administracao=self.user.administracao,
                ativo=True
            ).order_by('nome')
        elif self.user and self.user.is_superuser:
            self.fields['departamento'].queryset = Departamento.objects.filter(ativo=True).order_by('nome')
        else:
            self.fields['departamento'].queryset = Departamento.objects.none()


class CustomUserCreationForm(UserCreationForm):
    """
    Formulário customizado para criação de usuários
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        required=True
    )

    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True,
        label='Nome'
    )

    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True,
        label='Sobrenome'
    )

    telefone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    administracao = forms.ModelChoiceField(
        queryset=Administracao.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label='Administração'
    )

    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.none(), # Inicialmente vazio, preenchido via AJAX/View ou POST
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )

    seccao = forms.ModelChoiceField(
        queryset=Seccoes.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label='Secção (Opcional)'
    )

    nivel_acesso = forms.ChoiceField(
        choices=CustomUser.NIVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label='Nível de Acesso'
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name',
                  'telefone', 'administracao', 'departamento', 'seccao', 'nivel_acesso',
                  'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

        # Lógica para popular querysets se houver dados (POST ou instância)
        # SEGURANÇA: Garantir que departamentos e secções pertençam à administração selecionada
        if 'administracao' in self.data:
            try:
                admin_id = int(self.data.get('administracao'))
                administracao = Administracao.objects.get(id=admin_id)
                self.fields['departamento'].queryset = Departamento.objects.para_administracao(administracao).order_by('nome')
            except (ValueError, TypeError, Administracao.DoesNotExist):
                self.fields['departamento'].queryset = Departamento.objects.none()
        elif self.instance.pk and self.instance.administracao:
            self.fields['departamento'].queryset = Departamento.objects.para_administracao(self.instance.administracao).order_by('nome')

        if 'departamento' in self.data:
            try:
                dept_id = int(self.data.get('departamento'))
                # Garantir que a secção pertence ao departamento selecionado E à administração
                self.fields['seccao'].queryset = Seccoes.objects.filter(departamento_id=dept_id).order_by('nome')
                
                # Double check de segurança (se administração estiver no form)
                if 'administracao' in self.data:
                    admin_id = int(self.data.get('administracao'))
                    self.fields['seccao'].queryset = self.fields['seccao'].queryset.filter(departamento__administracao_id=admin_id)
            except (ValueError, TypeError):
                self.fields['seccao'].queryset = Seccoes.objects.none()
        elif self.instance.pk and self.instance.departamento:
            self.fields['seccao'].queryset = Seccoes.objects.filter(departamento=self.instance.departamento).order_by('nome')
        else:
            self.fields['seccao'].queryset = Seccoes.objects.none()


class CriarUsuarioAdminForm(UserCreationForm):
    """
    Formulário para admin_sistema criar usuários da sua própria administração.
    - Administração é definida automaticamente (não aparece no form)
    - Departamentos são filtrados pela administração do admin
    - Secções são carregadas via AJAX ao selecionar departamento
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
        required=True
    )

    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
        required=True,
        label='Nome'
    )

    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sobrenome'}),
        required=True,
        label='Sobrenome'
    )

    telefone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 9XX XXX XXX'}),
        required=False
    )

    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_departamento'}),
        required=True,
        label='Departamento'
    )

    seccao = forms.ModelChoiceField(
        queryset=Seccoes.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_seccao'}),
        required=False,
        label='Secção (Opcional)'
    )

    nivel_acesso = forms.ChoiceField(
        choices=CustomUser.NIVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label='Nível de Acesso'
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name',
                  'telefone', 'departamento', 'seccao', 'nivel_acesso',
                  'password1', 'password2')

    def __init__(self, *args, **kwargs):
        self.admin_user = kwargs.pop('admin_user', None)
        super().__init__(*args, **kwargs)
        
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nome de usuário'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Senha'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmar senha'
        })

        # Filtrar departamentos pela administração do admin logado
        if self.admin_user and self.admin_user.administracao:
            self.fields['departamento'].queryset = Departamento.objects.filter(
                administracao=self.admin_user.administracao
            ).order_by('nome')

        # Popular secções se departamento foi selecionado (POST)
        if 'departamento' in self.data:
            try:
                dept_id = int(self.data.get('departamento'))
                # Garantir que a secção pertence ao departamento selecionado E à administração do admin
                self.fields['seccao'].queryset = Seccoes.objects.filter(
                    departamento_id=dept_id,
                    departamento__administracao=self.admin_user.administracao
                ).order_by('nome')
            except (ValueError, TypeError, AttributeError):
                self.fields['seccao'].queryset = Seccoes.objects.none()
        elif self.instance.pk and self.instance.departamento:
            self.fields['seccao'].queryset = Seccoes.objects.filter(departamento=self.instance.departamento).order_by('nome')
        else:
            self.fields['seccao'].queryset = Seccoes.objects.none()

    def _post_clean(self):
        """
        Define a administração ANTES da validação do modelo.
        Isto resolve o erro 'CustomUser has no administracao'.
        """
        # Definir administração na instância antes da validação
        if self.admin_user and self.admin_user.administracao:
            self.instance.administracao = self.admin_user.administracao
        # Agora chamar o _post_clean do pai que fará a validação do modelo
        super()._post_clean()

    def save(self, commit=True):
        user = super().save(commit=False)
        # Garantir que a administração está definida
        if self.admin_user and self.admin_user.administracao:
            user.administracao = self.admin_user.administracao
        if commit:
            user.save()
        return user


class DepartamentoForm(forms.ModelForm):
    """
    Formulário para departamentos
    """

    class Meta:
        model = Departamento
        fields = ['nome', 'codigo', 'descricao', 'responsavel', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TipoDocumentoForm(forms.ModelForm):
    """
    Formulário para tipos de documento
    """

    class Meta:
        model = TipoDocumento
        fields = ['nome', 'descricao', 'prazo_dias', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'prazo_dias': forms.NumberInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AnexoForm(forms.ModelForm):
    """
    Formulário para anexos
    """

    class Meta:
        model = Anexo
        fields = ['arquivo', 'nome', 'descricao']
        widgets = {
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }


class FiltroRelatorioForm(forms.Form):
    """
    Formulário para filtros de relatórios
    """
    data_inicio = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False,
        label='Data Início'
    )

    data_fim = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False,
        label='Data Fim'
    )

    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label='Todos os departamentos'
    )

    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label='Todos os tipos'
    )

    status = forms.ChoiceField(
        choices=[('', 'Todos')] + StatusDocumento.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )


class ArmazenamentoDocumentoForm(forms.ModelForm):
    """
    Formulário para registrar o armazenamento físico de documentos
    """

    class Meta:
        model = ArmazenamentoDocumento
        fields = [
            'local_armazenamento',
            'estante', 'prateleira', 'dossie', 'caixa', 'posicao',
            'observacoes'
        ]
        widgets = {
            'local_armazenamento': forms.Select(attrs={
                'class': 'form-select',
            }),
            'estante': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: EST-01',
                'maxlength': '50',
            }),
            'prateleira': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: PRAT-A',
                'maxlength': '50',
            }),
            'dossie': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: DOS-001',
                'maxlength': '50',
            }),
            'caixa': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: CX-05 (opcional)',
                'maxlength': '50',
            }),
            'posicao': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Posição 3',
                'maxlength': '50',
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Observações sobre o armazenamento'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.documento = kwargs.pop('documento', None)
        super().__init__(*args, **kwargs)

        # Filtrar locais de armazenamento por departamento do usuário
        if self.user:
            departamento_usuario = None
            if hasattr(self.user, 'seccao') and self.user.seccao:
                departamento_usuario = self.user.seccao.departamento
            elif hasattr(self.user, 'departamento') and self.user.departamento:
                departamento_usuario = self.user.departamento

            if departamento_usuario:
                self.fields['local_armazenamento'].queryset = LocalArmazenamento.objects.filter(
                    departamento=departamento_usuario,
                    ativo=True
                ).order_by('tipo', 'codigo')
            else:
                self.fields['local_armazenamento'].queryset = LocalArmazenamento.objects.none()
        else:
            self.fields['local_armazenamento'].queryset = LocalArmazenamento.objects.filter(ativo=True)

        # Campos não obrigatórios (validação customizada no clean)
        self.fields['local_armazenamento'].required = False
        self.fields['estante'].required = False
        self.fields['prateleira'].required = False
        self.fields['dossie'].required = False
        self.fields['caixa'].required = False
        self.fields['posicao'].required = False

    def clean(self):
        cleaned_data = super().clean()
        local_cadastrado = cleaned_data.get('local_armazenamento')
        estante = cleaned_data.get('estante')
        prateleira = cleaned_data.get('prateleira')
        dossie = cleaned_data.get('dossie')
        caixa = cleaned_data.get('caixa')

        tem_local_cadastrado = local_cadastrado is not None
        tem_local_manual = any([estante, prateleira, dossie, caixa])

        if not tem_local_cadastrado and not tem_local_manual:
            raise ValidationError(
                'Deve informar um local de armazenamento cadastrado OU preencher os campos manuais (pelo menos estante, prateleira ou dossiê).'
            )

        return cleaned_data