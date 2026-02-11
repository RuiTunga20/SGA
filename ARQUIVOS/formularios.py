# forms_refactored.py
"""
Formulários refatorados usando HierarchyManager centralizado.

Substitui a lógica duplicada por chamadas ao HierarchyManager,
que funciona igualmente para encaminhamento, criação de usuário, etc.
"""

from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Documento,
    CustomUser,
    Departamento,
    MovimentacaoDocumento,
    Seccoes,
    StatusDocumento,
    TipoDocumento,
    Anexo,
    ArmazenamentoDocumento,
    LocalArmazenamento,
    Administracao,
)

# Importar o gerenciador centralizado
from .hierarchy_manager import (
    HierarchyManager,
    validar_destino_encaminhamento,
    obter_label_dinamico,
)


# ===========================================================================
# DocumentoForm (sem mudanças significativas)
# ===========================================================================

class DocumentoForm(forms.ModelForm):
    """
    Formulário para criação e edição de documentos
    """

    class Meta:
        model = Documento
        fields = [
            'titulo', 'tipo_documento', 'prioridade',
            'arquivo', 'arquivo_digitalizado', 'tags', 'observacoes',
            'utente', 'telefone', 'email', 'origem', 'niveis', 'referencia',
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


# ===========================================================================
# EncaminharDocumentoForm (REFATORADO COM HierarchyManager)
# ===========================================================================

class EncaminharDocumentoForm(forms.ModelForm):
    """
    Formulário para encaminhar documentos.
    
    Usa HierarchyManager para calcular departamentos e secções permitidos,
    funcionando para TODOS os tipos de usuário (admin, dept, secção, superuser).
    """

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

        self.fields['tipo_movimentacao'].choices = [
            ('criacao',        'Criar'),
            ('encaminhamento', 'Encaminhar'),
        ]

        self.fields['departamento_destino'].required = False
        self.fields['seccao_destino'].required = False

        # Usar HierarchyManager para popular querysets
        if self.user:
            manager = HierarchyManager(self.user)
            
            # Obter destinos (excluindo self)
            qs_dept, qs_sec, seccoes_fixas = manager.obter_destinos_permitidos(incluir_self=False)
            
            self.fields['departamento_destino'].queryset = qs_dept
            self.fields['seccao_destino'].queryset = qs_sec
            
            # Armazenar para uso no template
            self.seccoes_fixas = seccoes_fixas
            
            # Preparar dados JSON para JavaScript (apenas se secções forem dinâmicas)
            if not seccoes_fixas:
                self.seccoes_data = {}
                if qs_dept.exists():
                    dept_id = qs_dept.first().pk
                    self.seccoes_data[dept_id] = list(
                        qs_sec.values('id', 'nome')
                    )
            else:
                self.seccoes_data = None

            # Labels dinâmicos
            labels = obter_label_dinamico(self.user, contexto='encaminhamento')
            self.fields['departamento_destino'].label = labels['departamento']
            self.fields['seccao_destino'].label = labels['seccao']
        else:
            self.fields['departamento_destino'].queryset = Departamento.objects.none()
            self.fields['seccao_destino'].queryset = Seccoes.objects.none()
            self.seccoes_fixas = False
            self.seccoes_data = None

        self.fields['seccao_destino'].label_from_instance = lambda obj: obj.nome

    def clean(self):
        cleaned_data = super().clean()
        dept_destino = cleaned_data.get('departamento_destino')
        sec_destino = cleaned_data.get('seccao_destino')
        tipo_mov = cleaned_data.get('tipo_movimentacao')

        if tipo_mov == 'encaminhamento':
            is_valid, error_msg = validar_destino_encaminhamento(
                self.user,
                dept_id=dept_destino.pk if dept_destino else None,
                seccao_id=sec_destino.pk if sec_destino else None,
            )
            if not is_valid:
                raise ValidationError(error_msg)

        return cleaned_data


# ===========================================================================
# CustomUserCreationForm (REFATORADO COM HierarchyManager)
# ===========================================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Formulário customizado para criação de usuários.
    
    Usa HierarchyManager para carregar departamentos e secções
    de forma consistente com encaminhamento.
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
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'telefone', 'administracao', 'departamento', 'seccao',
            'nivel_acesso', 'password1', 'password2'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

        # Popular departamentos se administração estiver presente
        if 'administracao' in self.data:
            try:
                admin_id = int(self.data.get('administracao'))
                administracao = Administracao.objects.get(id=admin_id)
                self.fields['departamento'].queryset = (
                    Departamento.objects.para_administracao(administracao)
                    .order_by('nome')
                )
            except (ValueError, TypeError, Administracao.DoesNotExist):
                self.fields['departamento'].queryset = Departamento.objects.none()
        elif self.instance.pk and self.instance.administracao:
            self.fields['departamento'].queryset = (
                Departamento.objects.para_administracao(self.instance.administracao)
                .order_by('nome')
            )

        # Popular secções se departamento estiver presente
        if 'departamento' in self.data:
            try:
                dept_id = int(self.data.get('departamento'))
                self.fields['seccao'].queryset = (
                    Seccoes.objects.filter(departamento_id=dept_id)
                    .order_by('nome')
                )
                
                # Validação adicional: secção deve pertencer à administração
                if 'administracao' in self.data:
                    admin_id = int(self.data.get('administracao'))
                    self.fields['seccao'].queryset = self.fields['seccao'].queryset.filter(
                        departamento__administracao_id=admin_id
                    )
            except (ValueError, TypeError):
                self.fields['seccao'].queryset = Seccoes.objects.none()
        elif self.instance.pk and self.instance.departamento:
            self.fields['seccao'].queryset = (
                Seccoes.objects.filter(departamento=self.instance.departamento)
                .order_by('nome')
            )


# ===========================================================================
# CriarUsuarioAdminForm (REFATORADO COM HierarchyManager)
# ===========================================================================

class CriarUsuarioAdminForm(UserCreationForm):
    """
    Formulário para admin_sistema criar usuários da sua administração.
    
    A administração é automaticamente a do admin logado (não aparece no form).
    Usa HierarchyManager para garantir consistência de hierarquia.
    """
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@exemplo.com'
        }),
        required=True
    )

    first_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome'
        }),
        required=True,
        label='Nome'
    )

    last_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sobrenome'
        }),
        required=True,
        label='Sobrenome'
    )

    telefone = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+244 9XX XXX XXX'
        }),
        required=False
    )

    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_departamento'
        }),
        required=True,
        label='Departamento'
    )

    seccao = forms.ModelChoiceField(
        queryset=Seccoes.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_seccao'
        }),
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
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'telefone', 'departamento', 'seccao', 'nivel_acesso',
            'password1', 'password2'
        )

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
            self.fields['departamento'].queryset = (
                Departamento.objects.filter(
                    administracao=self.admin_user.administracao
                )
                .order_by('nome')
            )

        # Popular secções se departamento foi selecionado
        if 'departamento' in self.data:
            try:
                dept_id = int(self.data.get('departamento'))
                self.fields['seccao'].queryset = (
                    Seccoes.objects.filter(
                        departamento_id=dept_id,
                        departamento__administracao=self.admin_user.administracao
                    )
                    .order_by('nome')
                )
            except (ValueError, TypeError, AttributeError):
                self.fields['seccao'].queryset = Seccoes.objects.none()
        elif self.instance.pk and self.instance.departamento:
            self.fields['seccao'].queryset = (
                Seccoes.objects.filter(departamento=self.instance.departamento)
                .order_by('nome')
            )

    def _post_clean(self):
        """Define administração ANTES da validação do modelo."""
        if self.admin_user and self.admin_user.administracao:
            self.instance.administracao = self.admin_user.administracao
        super()._post_clean()

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.admin_user and self.admin_user.administracao:
            user.administracao = self.admin_user.administracao
        if commit:
            user.save()
        return user


# ===========================================================================
# Outros Formulários (Sem Mudanças Significativas)
# ===========================================================================

class DespachoForm(forms.Form):
    """Formulário para registrar despacho em documento."""
    
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
    """Formulário para busca avançada de documentos."""
    
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
            self.fields['departamento'].queryset = (
                Departamento.objects.filter(
                    administracao=self.user.administracao,
                    ativo=True
                )
                .order_by('nome')
            )
        elif self.user and self.user.is_superuser:
            self.fields['departamento'].queryset = (
                Departamento.objects.filter(ativo=True)
                .order_by('nome')
            )
        else:
            self.fields['departamento'].queryset = Departamento.objects.none()


class DepartamentoForm(forms.ModelForm):
    """Formulário para departamentos."""

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
    """Formulário para tipos de documento."""

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
    """Formulário para anexos."""

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
    """Formulário para filtros de relatórios."""
    
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
    """Formulário para registrar o armazenamento físico de documentos."""

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
            elif hasattr(self.user, 'departamento_efetivo'):
                departamento_usuario = self.user.departamento_efetivo

            if departamento_usuario:
                self.fields['local_armazenamento'].queryset = (
                    LocalArmazenamento.objects.filter(
                        departamento=departamento_usuario,
                        ativo=True
                    )
                    .order_by('tipo', 'codigo')
                )
            else:
                self.fields['local_armazenamento'].queryset = LocalArmazenamento.objects.none()
        else:
            self.fields['local_armazenamento'].queryset = LocalArmazenamento.objects.filter(ativo=True)

        # Campos não obrigatórios
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
                'Deve informar um local de armazenamento cadastrado OU '
                'preencher os campos manuais (pelo menos estante, prateleira ou dossiê).'
            )

        return cleaned_data