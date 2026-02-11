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


class EncaminharDocumentoForm(forms.ModelForm):
    enviar_todas = forms.BooleanField(
        required=False, 
        label="Enviar para TODAS as Administrações da Província",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

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
        
        # Reescrever as opções do select de tipo de movimentação
        # REQ: Apenas "Criar" e "Encaminhar"
        self.fields['tipo_movimentacao'].choices = [
            ('criacao', 'Criar'),
            ('encaminhamento', 'Encaminhar'),
        ]

        # Assign document to instance to avoid RelatedObjectDoesNotExist during clean()
        if self.documento:
            self.instance.documento = self.documento

        # ========== LÓGICA DE FILTROS BASEADA NO USUÁRIO ==========

        # ========== LÓGICA DE FILTROS BASEADA NO USUÁRIO ==========

        if self.user:
            # Determinar a administração do usuário
            administracao_usuario = self.user.administracao
            
            if administracao_usuario:
                # ---------------------------------------------------------
                # LÓGICA ESPECIAL: Ministério (MAT)
                # ---------------------------------------------------------
                if administracao_usuario.tipo_municipio == 'M':
                    # Vê Departamentos internos do MAT
                    # E TAMBÉM "Secretaria Geral" de TODOS os Governos Provinciais
                    governos_ids = Administracao.objects.filter(
                        tipo_municipio='G'
                    ).values_list('id', flat=True)
                    
                    self.fields['departamento_destino'].queryset = Departamento.objects.filter(
                        Q(administracao=administracao_usuario) |
                        Q(administracao_id__in=governos_ids, nome__icontains="Secretaria Geral")
                    ).distinct().order_by('administracao__nome', 'nome')
                    
                    self.fields['departamento_destino'].label = "Destino (Interno ou Governo Provincial)"
                
                # ---------------------------------------------------------
                # LÓGICA ESPECIAL: Governo Provincial
                # ---------------------------------------------------------
                elif administracao_usuario.tipo_municipio == 'G':
                    # Vê Departamentos da própria admin (Governo)
                    # E TAMBÉM "Secretaria Geral" das Administrações MUNICIPAIS da mesma província
                    # E TAMBÉM "Secretaria Geral" do MAT
                    admins_municipais = Administracao.objects.filter(
                        provincia=administracao_usuario.provincia
                    ).exclude(tipo_municipio__in=['G', 'M']).values_list('id', flat=True)
                    
                    mat_ids = Administracao.objects.filter(
                        tipo_municipio='M'
                    ).values_list('id', flat=True)
                    
                    self.fields['departamento_destino'].queryset = Departamento.objects.filter(
                        Q(tipo_municipio=administracao_usuario.tipo_municipio, administracao__isnull=True) |
                        Q(administracao=administracao_usuario) |
                        Q(administracao_id__in=admins_municipais, nome__icontains="Secretaria Geral") |
                        Q(administracao_id__in=mat_ids, nome__icontains="Secretaria Geral")
                    ).distinct().order_by('administracao__nome', 'nome')
                    
                    self.fields['departamento_destino'].label = "Destino (Interno, Municipal ou MAT)"
                
                # ---------------------------------------------------------
                # LÓGICA ESPECIAL: Administração Municipal (Secretaria Geral)
                # ---------------------------------------------------------
                elif hasattr(self.user, 'departamento') and self.user.departamento and "Secretaria Geral" in self.user.departamento.nome:
                     # Vê Departamentos da própria admin
                    qs_dept = Departamento.objects.para_administracao(administracao_usuario)
                    
                    # TAMBÉM Vê "Secretaria Geral" do Governo Provincial
                    governo_prov = Administracao.objects.filter(
                        provincia=administracao_usuario.provincia,
                        tipo_municipio='G'
                    ).first()
                    
                    if governo_prov:
                        # Usar Q objects para combinar queryset de forma eficiente
                        self.fields['departamento_destino'].queryset = Departamento.objects.filter(
                            Q(tipo_municipio=administracao_usuario.tipo_municipio, administracao__isnull=True) |
                            Q(administracao=administracao_usuario) |
                            Q(administracao=governo_prov, nome__icontains="Secretaria Geral")
                        ).distinct().order_by('administracao__nome', 'nome')
                    else:
                        self.fields['departamento_destino'].queryset = qs_dept
                        
                # ---------------------------------------------------------
                # LÓGICA PADRÃO (Mesma Administração)
                # ---------------------------------------------------------
                else:
                    # Lógica diferenciada baseada na localização do usuário
                    if hasattr(self.user, 'seccao') and self.user.seccao:
                        # CENÁRIO A: Usuário está em uma SECÇÃO
                        dept_pai = self.user.seccao.departamento

                        # REQ: "no select departamento só vai aparecer o seu departamento"
                        self.fields['departamento_destino'].queryset = Departamento.objects.filter(id=dept_pai.id)

                        # REQ: "na seção só aparece outras secção do seu departamento excepto o sua"
                        self.fields['seccao_destino'].queryset = Seccoes.objects.filter(
                            departamento=dept_pai
                        ).exclude(id=self.user.seccao.id).order_by('nome')

                    else:
                        # CENÁRIO B: Usuário está no DEPARTAMENTO (Diretor/Chefe)
                        # REQ: "no departamento o seu departamento n deve aparecer no seu selct"
                        self.fields['departamento_destino'].queryset = Departamento.objects.para_administracao(administracao_usuario).exclude(
                            id=self.user.departamento.id if self.user.departamento else -1
                        ).order_by('nome')

                        # Secções: Vê TODAS as secções do departamento selecionado (via AJAX)
                        # Inicialmente vazio ou filtrado se houver dados POST
                        self.fields['seccao_destino'].queryset = Seccoes.objects.filter(
                            departamento=self.user.departamento
                        ).order_by('nome')

                    self.fields['departamento_destino'].label = "Encaminhar para Departamento"
                    self.fields['seccao_destino'].label = "Ou para Secção (Interno)"
            else:
                # Se usuário não tem administração (ex: admin sistema sem vinculo), vê tudo?
                # Ou não vê nada? Pela regra estrita, melhor não ver nada ou tudo se for superuser
                if self.user.nivel_acesso == 'admin_sistema':
                     self.fields['departamento_destino'].queryset = Departamento.objects.all()
                     self.fields['seccao_destino'].queryset = Seccoes.objects.all()
                else:
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
                admin_usuario = self.user.administracao
                
                # REGRA ESPECIAL: Ministério (MAT) pode enviar para Secretaria Geral de Governos
                if admin_usuario and admin_usuario.tipo_municipio == 'M':
                    if dept_destino.administracao != admin_usuario:
                        # É envio para outra administração - VERIFICAR se é Secretaria Geral de Governo
                        if not dept_destino.administracao or dept_destino.administracao.tipo_municipio != 'G':
                            raise ValidationError(
                                'O Ministério só pode enviar para a "Secretaria Geral" dos Governos Provinciais.'
                            )
                        if "Secretaria Geral" not in dept_destino.nome:
                            raise ValidationError(
                                'Só pode enviar para a "Secretaria Geral" do Governo Provincial.'
                            )
                    elif dept_destino.id == dept_usuario.id:
                        raise ValidationError(
                            'Você não pode encaminhar para o seu próprio departamento.'
                        )
                
                # REGRA ESPECIAL: Governo Provincial pode enviar para Secretaria Geral de Administrações e MAT
                elif admin_usuario and admin_usuario.tipo_municipio == 'G':
                    if dept_destino.administracao != admin_usuario:
                        # É envio para outra administração
                        dest_tipo = dept_destino.administracao.tipo_municipio if dept_destino.administracao else None
                        # Pode enviar para Municipal (mesma prov) ou MAT
                        if dest_tipo not in ('A', 'B', 'C', 'D', 'E', 'M'):
                            raise ValidationError(
                                'O Governo Provincial só pode enviar para administrações municipais ou para o Ministério.'
                            )
                        if "Secretaria Geral" not in dept_destino.nome:
                            raise ValidationError(
                                'Só pode enviar para a "Secretaria Geral" da administração de destino.'
                            )
                    elif dept_destino.id == dept_usuario.id:
                        raise ValidationError(
                            'Você não pode encaminhar para o seu próprio departamento.'
                        )
                
                # REGRA ESPECIAL: Secretaria Geral pode enviar para Governo Provincial ou MAT
                elif admin_usuario and "Secretaria Geral" in dept_usuario.nome:
                    if dept_destino.administracao != admin_usuario:
                        dest_tipo = dept_destino.administracao.tipo_municipio if dept_destino.administracao else None
                        # Secretaria Geral de Municipal pode enviar para Governo
                        if dest_tipo not in ('G',):
                            raise ValidationError(
                                'A Secretaria Geral só pode enviar para o Governo Provincial.'
                            )
                        if "Secretaria Geral" not in dept_destino.nome:
                            raise ValidationError(
                                'Só pode enviar para a "Secretaria Geral" do Governo Provincial.'
                            )
                    elif dept_destino.id == dept_usuario.id:
                        raise ValidationError(
                            'Você não pode encaminhar para o seu próprio departamento.'
                        )
                
                # REGRA PADRÃO: Mesma administração apenas
                else:
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
        if 'administracao' in self.data:
            try:
                admin_id = int(self.data.get('administracao'))
                administracao = Administracao.objects.get(id=admin_id)
                self.fields['departamento'].queryset = Departamento.objects.para_administracao(administracao)
            except (ValueError, TypeError, Administracao.DoesNotExist):
                pass
        elif self.instance.pk and self.instance.administracao:
            self.fields['departamento'].queryset = Departamento.objects.para_administracao(self.instance.administracao)

        if 'departamento' in self.data:
            try:
                dept_id = int(self.data.get('departamento'))
                self.fields['seccao'].queryset = Seccoes.objects.filter(departamento_id=dept_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.departamento:
            self.fields['seccao'].queryset = Seccoes.objects.filter(departamento=self.instance.departamento)


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
                self.fields['seccao'].queryset = Seccoes.objects.filter(
                    departamento_id=dept_id
                ).order_by('nome')
            except (ValueError, TypeError):
                pass

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