# forms.py
from django.contrib.auth.forms import UserCreationForm
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


class EncaminharDocumentoForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoDocumento
        fields = [
            'tipo_movimentacao',
            'departamento_destino',
            'seccao_destino',
            'observacoes',
            'despacho'
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Observações sobre o encaminhamento...'
            }),
            'despacho': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Despacho ou instruções...'
            }),
            'tipo_movimentacao': forms.Select(attrs={'class': 'form-control'}),
            'departamento_destino': forms.Select(attrs={'class': 'form-control'}),
            'seccao_destino': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.documento = kwargs.pop('documento', None)
        super().__init__(*args, **kwargs)

        # ========== LÓGICA DE FILTROS BASEADA NO USUÁRIO ==========

        if self.user:
            # Determinar o departamento e secção do usuário
            departamento_usuario = None
            seccao_usuario = None

            if hasattr(self.user, 'seccao') and self.user.seccao:
                seccao_usuario = self.user.seccao
                departamento_usuario = self.user.seccao.departamento
            elif hasattr(self.user, 'departamento') and self.user.departamento:
                departamento_usuario = self.user.departamento

            # ========== CENÁRIO 1: USUÁRIO ESTÁ EM UMA SECÇÃO ==========
            if seccao_usuario:
                # DEPARTAMENTO: Apenas o SEU departamento
                self.fields['departamento_destino'].queryset = Departamento.objects.filter(
                    id=departamento_usuario.id,
                    ativo=True
                )

                # SECÇÕES: Apenas secções do SEU departamento, EXCETO a sua
                self.fields['seccao_destino'].queryset = Seccoes.objects.filter(
                    departamento=departamento_usuario,
                    ativo=True
                ).exclude(
                    id=seccao_usuario.id
                ).select_related('departamento').order_by('nome')

                self.fields['departamento_destino'].label = "Encaminhar para o Departamento (geral)"
                self.fields['seccao_destino'].label = "Ou para outra Secção do seu Departamento"

            # ========== CENÁRIO 2: USUÁRIO ESTÁ DIRETO NO DEPARTAMENTO ==========
            elif departamento_usuario:
                tipo_municipio = departamento_usuario.tipo_municipio

                # DEPARTAMENTO: Todos os departamentos do MESMO TIPO (município)
                # EXCETO o próprio departamento do usuário
                self.fields['departamento_destino'].queryset = Departamento.objects.filter(
                    tipo_municipio=tipo_municipio,
                    ativo=True
                ).exclude(
                    id=departamento_usuario.id  # Exclui o próprio departamento
                ).order_by('nome')

                # SECÇÕES: Todas as secções do SEU departamento
                self.fields['seccao_destino'].queryset = Seccoes.objects.filter(
                    departamento=departamento_usuario,
                    ativo=True
                ).select_related('departamento').order_by('nome')

                self.fields[
                    'departamento_destino'].label = f"Encaminhar para Departamento (Município Tipo {tipo_municipio})"
                self.fields['seccao_destino'].label = "Ou para Secção do seu Departamento"

            else:
                # Se não tem departamento nem secção
                self.fields['departamento_destino'].queryset = Departamento.objects.none()
                self.fields['seccao_destino'].queryset = Seccoes.objects.none()

        else:
            # Se não há usuário
            self.fields['departamento_destino'].queryset = Departamento.objects.none()
            self.fields['seccao_destino'].queryset = Seccoes.objects.none()

        # ========== AJUSTAR REQUISITOS ==========
        self.fields['departamento_destino'].required = False
        self.fields['seccao_destino'].required = False

        # Melhorar exibição das secções
        self.fields['seccao_destino'].label_from_instance = lambda obj: f"{obj.nome}"

    def clean(self):
        cleaned_data = super().clean()
        dept_destino = cleaned_data.get('departamento_destino')
        sec_destino = cleaned_data.get('seccao_destino')
        tipo_mov = cleaned_data.get('tipo_movimentacao')

        # ===== VALIDAÇÃO 1: Para encaminhamentos, deve ter UM destino =====
        if tipo_mov == 'encaminhamento':
            if not dept_destino and not sec_destino:
                raise ValidationError(
                    'Para encaminhar, você deve selecionar UM departamento OU uma secção de destino.'
                )

        # ===== VALIDAÇÃO 2: NÃO PODE selecionar AMBOS ao mesmo tempo =====
        if dept_destino and sec_destino:
            raise ValidationError(
                'Você deve escolher APENAS o departamento OU uma secção específica, não ambos.'
            )

        # ===== VALIDAÇÃO 3: Verificar se o destino é válido para o usuário =====
        if self.user and dept_destino:
            # Obter o departamento e tipo do usuário
            if hasattr(self.user, 'seccao') and self.user.seccao:
                dept_usuario = self.user.seccao.departamento
                # Se está em secção, só pode encaminhar para o próprio departamento
                if dept_destino.id != dept_usuario.id:
                    raise ValidationError(
                        'Você só pode encaminhar para o seu próprio departamento ou para secções dentro dele.'
                    )
            elif hasattr(self.user, 'departamento') and self.user.departamento:
                dept_usuario = self.user.departamento
                tipo_usuario = dept_usuario.tipo_municipio
                # Se está no departamento, pode encaminhar para qualquer dept do mesmo tipo
                if dept_destino.tipo_municipio != tipo_usuario:
                    raise ValidationError(
                        f'Você só pode encaminhar para departamentos do Município Tipo {tipo_usuario}.'
                    )
                # Não pode encaminhar para si mesmo
                if dept_destino.id == dept_usuario.id:
                    raise ValidationError(
                        'Você não pode encaminhar para o seu próprio departamento.'
                    )

        # ===== VALIDAÇÃO 4: Verificar secção destino =====
        if self.user and sec_destino:
            if hasattr(self.user, 'seccao') and self.user.seccao:
                # Não pode ser a própria secção
                if sec_destino.id == self.user.seccao.id:
                    raise ValidationError(
                        'Você não pode encaminhar para a sua própria secção.'
                    )

            # Verificar se a secção pertence ao departamento do usuário
            dept_usuario = None
            if hasattr(self.user, 'seccao') and self.user.seccao:
                dept_usuario = self.user.seccao.departamento
            elif hasattr(self.user, 'departamento') and self.user.departamento:
                dept_usuario = self.user.departamento

            if dept_usuario and sec_destino.departamento.id != dept_usuario.id:
                raise ValidationError(
                    'Você só pode encaminhar para secções do seu próprio departamento.'
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

    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
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
                  'telefone', 'departamento', 'nivel_acesso',
                  'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


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