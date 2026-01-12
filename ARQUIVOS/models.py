from django.db import models

# Create your models here.
# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from ARQUIVOS.managers import DocumentoManager
from django.core.exceptions import ValidationError


class CustomUser(AbstractUser):
    NIVEL_CHOICES = [
        # Níveis de Gestão
        ('admin_sistema', 'Administrador de Sistema'),
        ('admin_municipal', 'Administrador Municipal'),
        ('diretor_municipal', 'Director Municipal'),
        ('chefe_gabinete', 'Chefe de Gabinete'),
        ('chefe_seccao', 'Chefe de Secção'),
        ('supervisor', 'Supervisor'),

        # Níveis Operacionais
        ('tecnico', 'Técnico Superior/Especialista'),
        ('escriturario', 'Assistente Técnico/Escriturário'),
        ('operador', 'Operador'),
    ]

    nivel_acesso = models.CharField(max_length=30, choices=NIVEL_CHOICES, default='operador')

    # Departamento pode ser opcional se o usuário está em uma secção
    departamento = models.ForeignKey(
        'Departamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_departamento',
        default=1
    )

    # Secção é opcional - nem todos estão em secções específicas
    seccao = models.ForeignKey(
        'Seccoes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_seccao'
    )

    telefone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Valida a consistência entre departamento e secção"""
        super().clean()

        # Se tem secção, valida se pertence ao departamento
        if self.seccao and self.departamento:
            if self.seccao.Departamento != self.departamento:
                raise ValidationError({
                    'seccao': 'A secção selecionada não pertence ao departamento escolhido.'
                })

        # Validação: deve ter pelo menos departamento OU secção
        if not self.departamento and not self.seccao:
            raise ValidationError(
                'O utilizador deve pertencer a pelo menos um departamento ou secção.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def departamento_efetivo(self):
        """
        Retorna o departamento do usuário
        PRIORIZA a secção se existir
        """
        if self.seccao:
            return self.seccao.Departamento
        elif self.departamento:
            return self.departamento
        return None

    @property
    def localizacao_atual(self):
        """
        Retorna a localização específica (secção ou departamento)
        Para uso em formulários e views
        """
        return {
            'seccao': self.seccao,
            'departamento': self.departamento if not self.seccao else self.seccao.Departamento
        }


def __str__(self):
        if self.seccao:
            return f"{self.username} - {self.seccao.nome} ({self.seccao.Departamento.nome})"
        elif self.departamento:
            return f"{self.username} - {self.departamento.nome}"
        return f"{self.username} - {self.get_nivel_acesso_display()}"


class Departamento(models.Model):
    """
    Modelo para representar departamentos da organização.
    """
    TIPO_MUNICIPIO_CHOICES = [
        ('A', 'Tipo A'),
        ('B', 'Tipo B'),
        ('C', 'Tipo C'),
        ('D', 'Tipo D'),
        ('E', 'Tipo E'),
    ]

    nome = models.CharField(max_length=255, unique=False)
    codigo = models.CharField(max_length=20, unique=False, blank=True)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='departamentos_responsavel')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tipo_municipio = models.CharField(max_length=1, choices=TIPO_MUNICIPIO_CHOICES, default='A')

    def __str__(self):
        return f"{self.nome} ({self.tipo_municipio})"

    class Meta:
        verbose_name = "Direção"
        verbose_name_plural = "Direções"


class Seccoes(models.Model):
    Departamento = models.ForeignKey('Departamento', on_delete=models.CASCADE)
    nome = models.CharField(max_length=255, unique=False)
    codigo = models.CharField(max_length=20, unique=False, blank=True)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='Seccao_responsavel')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.Departamento.tipo_municipio})"

    class Meta:
        verbose_name = "Secção"
        verbose_name_plural = "Secções"
        unique_together = ('nome', 'Departamento')


class TipoDocumento(models.Model):
    """
    Tipos de documentos que podem ser cadastrados
    """
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True)
    prazo_dias = models.IntegerField(default=30, help_text="Prazo padrão em dias para processamento")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documentos"


class Documento(models.Model):
    """
    Modelo principal para documentos
    """
    STATUS_CHOICES = [
        ('criacao', 'Criação'),
        ('recebimento', 'Recebimento'),
        ('encaminhamento', 'Encaminhamento'),
        ('despacho', 'Despacho'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'reprovado'),
        ('arquivado', 'arquivado'),
    ]

    PRIORIDADE_CHOICES = [
        ('Normal', 'Normal 🟡'),
        ('Urgente', 'Urgente 🔴'),
        ('Muito Urgente', 'Muito Urgente 🔥'),
    ]
    Origem_CHOICES = [
        ('Pessoa Singular', 'Pessoa Singular'),
        ('Instituição do Estado', 'Instituição do Estado'),
        ('Instituição Pública', 'Instituição Pública'),
        ('Instituição Privada', 'Instituição Privada'),
        ('Organização cívil', 'Organização cívil'),
    ]
    Niveis_CHOICES = [
        ('Público', 'Público'),
        ('Restrito', 'Restrito'),
        ('Confidencial', 'Confidencial'),
    ]
    objects = DocumentoManager()

    numero_protocolo = models.CharField(max_length=20, unique=True, editable=False)
    titulo = models.CharField('Assunto', max_length=200)
    conteudo = models.TextField()
    tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT)
    arquivo = models.FileField(upload_to='documentos/%Y/%m/', null=True, blank=True)
    arquivo_digitalizado = models.FileField(upload_to='digitalizados/%Y/%m/', null=True, blank=True)
    data_ultima_movimentacao = models.DateTimeField(auto_now=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='encaminhamento')
    prioridade = models.CharField(max_length=13, choices=PRIORIDADE_CHOICES, default='normal')
    nivels = models.CharField('Niveis de Acesso', max_length=50, choices=Niveis_CHOICES, default='Público')

    departamento_origem = models.ForeignKey(Departamento, on_delete=models.PROTECT, related_name='documentos_origem')
    departamento_atual = models.ForeignKey(Departamento, on_delete=models.PROTECT, related_name='documentos_atual')
    seccao_atual = models.ForeignKey(
        Seccoes,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_atuais',
        help_text="Secção específica onde o documento está atualmente"
    )
    criado_por = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='documentos_criados')
    responsavel_atual = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='documentos_responsavel')

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_prazo = models.DateTimeField(null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    tags = models.CharField(max_length=500, blank=True, help_text="O numero do Armario pasta  Armario-1/doc-335")
    referencia = models.CharField(max_length=500, blank=True, help_text="referência")

    observacoes = models.TextField(blank=True)

    Utente = models.CharField('Remetente', max_length=200)
    Telefone = models.IntegerField(max_length=9)
    Email = models.EmailField(blank=True, null=True)
    Entidade = models.CharField(max_length=52, choices=Origem_CHOICES, default='Pessoa Singular')
    origem = models.CharField('Origem', max_length=52, choices=Origem_CHOICES, default='Pessoa Singular')

    @property
    def dias_na_caixa(self):
        """Retorna quantos dias o documento está parado no setor atual"""
        from django.utils import timezone
        delta = timezone.now() - self.data_ultima_movimentacao
        return delta.days

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
            ano = timezone.now().year
            self.numero_protocolo = f"{self.id}/{ano}"
            kwargs['force_insert'] = False
            super().save(update_fields=['numero_protocolo'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_protocolo} - {self.titulo}"

    def get_status_color(self):
        colors = {
            'recebido': 'primary',
            'em_analise': 'warning',
            'aprovado': 'success',
            'rejeitado': 'danger',
            'arquivado': 'secondary',
            'encaminhado': 'info',
        }
        return colors.get(self.status, 'secondary')

    def is_vencido(self):
        return timezone.now() > self.data_prazo and self.status not in ['aprovado', 'rejeitado', 'arquivado']

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-data_criacao']


class MovimentacaoDocumento(models.Model):
    TIPO_MOVIMENTACAO_CHOICES = [
        ('criacao', 'Criação'),
        ('recebimento', 'Recebimento'),
        ('encaminhamento', 'Encaminhamento'),
        ('despacho', 'Despacho'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'Reprovado'),
        ('arquivado', 'Arquivado'),
    ]

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo_movimentacao = models.CharField(max_length=20, choices=TIPO_MOVIMENTACAO_CHOICES, default='encaminhamento')

    departamento_origem = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='movimentacoes_origem',
        null=True,
        blank=True
    )
    seccao_origem = models.ForeignKey(
        Seccoes,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_origem'
    )

    departamento_destino = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='movimentacoes_destino',
        null=True,
        blank=True
    )
    seccao_destino = models.ForeignKey(
        Seccoes,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_destino'
    )

    usuario = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    data_movimentacao = models.DateTimeField(auto_now_add=True)

    observacoes = models.TextField(blank=True)
    despacho = models.TextField(blank=True)

    confirmado_recebimento = models.BooleanField(default=False)
    data_confirmacao = models.DateTimeField(null=True, blank=True)
    usuario_confirmacao = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmacoes_movimentacao'
    )

    def clean(self):
        """Validações de negócio"""
        super().clean()

        tipos_que_precisam_destino = ['encaminhamento']

        if self.tipo_movimentacao in tipos_que_precisam_destino:
            if not self.departamento_destino and not self.seccao_destino:
                raise ValidationError({
                    '__all__': 'Encaminhamentos devem ter um departamento ou secção de destino.'
                })

        if self.departamento_destino and self.seccao_destino:
            if self.seccao_destino.Departamento != self.departamento_destino:
                raise ValidationError({
                    'seccao_destino': f'A secção "{self.seccao_destino.nome}" não pertence ao departamento "{self.departamento_destino.nome}".'
                })

        if self.departamento_origem and self.seccao_origem:
            if self.seccao_origem.Departamento != self.departamento_origem:
                raise ValidationError({
                    'seccao_origem': f'A secção de origem não pertence ao departamento de origem.'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def destino_completo(self):
        """Retorna descrição completa do destino"""
        if self.seccao_destino:
            return f"{self.seccao_destino.nome} - {self.seccao_destino.Departamento.nome}"
        elif self.departamento_destino:
            return self.departamento_destino.nome
        return "Sem destino especificado"

    @property
    def origem_completa(self):
        """Retorna descrição completa da origem"""
        if self.seccao_origem:
            return f"{self.seccao_origem.nome} - {self.seccao_origem.Departamento.nome}"
        elif self.departamento_origem:
            return self.departamento_origem.nome
        return "Origem não especificada"

    def __str__(self):
        return f"{self.documento.numero_protocolo} - {self.get_tipo_movimentacao_display()}"

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data_movimentacao']


class Anexo(models.Model):
    """
    Anexos adicionais aos documentos
    """
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to='anexos/%Y/%m/')
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    usuario_upload = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.documento.numero_protocolo} - {self.nome}"

    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"


class ConfiguracaoSistema(models.Model):
    """
    Configurações gerais do sistema
    """
    chave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.chave}: {self.valor}"

    class Meta:
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"


class Notificacao(models.Model):
    """
    Modelo para guardar notificações para os utilizadores.
    """
    departamento = models.CharField(max_length=100, null=True, blank=True)
    seccao = models.CharField(max_length=100, null=True, blank=True)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notificacoes')
    mensagem = models.CharField(max_length=255)
    link = models.URLField(max_length=255, blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificação para {self.usuario.username}: {self.mensagem[:30]}..."

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ['-data_criacao']


class LocalArmazenamento(models.Model):
    """
    Modelo para cadastrar locais físicos de armazenamento de documentos.
    Estrutura: Estante > Prateleira > Dossiê
    """
    TIPO_CHOICES = [
        ('estante', 'Estante'),
        ('prateleira', 'Prateleira'),
        ('dossie', 'Dossiê'),
        ('caixa', 'Caixa'),
        ('armario', 'Armário'),
        ('pasta', 'Pasta'),
    ]

    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único do local (ex: EST-01, PRAT-01-A, DOS-001)"
    )
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='estante')
    
    # Hierarquia: permite criar estrutura aninhada
    local_pai = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='locais_filhos',
        help_text="Local pai na hierarquia (ex: Prateleira pertence a uma Estante)"
    )
    
    # Capacidade e ocupação
    capacidade_maxima = models.IntegerField(
        default=0,
        help_text="Capacidade máxima de documentos/dossiês (0 = ilimitado)"
    )
    
    # Localização física
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        related_name='locais_armazenamento',
        help_text="Departamento onde este local está fisicamente"
    )
    seccao = models.ForeignKey(
        Seccoes,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locais_armazenamento',
        help_text="Secção específica (opcional)"
    )
    
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.local_pai:
            return f"{self.local_pai} > {self.codigo} ({self.nome})"
        return f"{self.codigo} - {self.nome}"

    @property
    def caminho_completo(self):
        """Retorna o caminho hierárquico completo do local"""
        partes = [self.codigo]
        atual = self.local_pai
        while atual:
            partes.insert(0, atual.codigo)
            atual = atual.local_pai
        return " > ".join(partes)

    @property
    def documentos_armazenados_count(self):
        """Retorna quantidade de documentos armazenados neste local"""
        return self.armazenamentos.filter(ativo=True).count()

    @property
    def espaco_disponivel(self):
        """Verifica se há espaço disponível"""
        if self.capacidade_maxima == 0:
            return True
        return self.documentos_armazenados_count < self.capacidade_maxima

    class Meta:
        verbose_name = "Local de Armazenamento"
        verbose_name_plural = "Locais de Armazenamento"
        ordering = ['departamento', 'tipo', 'codigo']


class ArmazenamentoDocumento(models.Model):
    """
    Modelo para registrar onde cada documento é guardado fisicamente.
    Criado automaticamente quando:
    - Operador SEM permissão de reencaminhar dá entrada no documento
    - Operador COM permissão reencaminha o documento (após reencaminhamento)
    """
    documento = models.ForeignKey(
        Documento,
        on_delete=models.CASCADE,
        related_name='armazenamentos'
    )
    
    # Localização física - pode ser informada por código ou campos separados
    local_armazenamento = models.ForeignKey(
        LocalArmazenamento,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='armazenamentos',
        help_text="Local cadastrado no sistema"
    )
    
    # Campos manuais para quando não há local cadastrado
    estante = models.CharField(max_length=50, blank=True, help_text="Código/Nome da Estante")
    prateleira = models.CharField(max_length=50, blank=True, help_text="Código/Nome da Prateleira")
    dossie = models.CharField(max_length=50, blank=True, help_text="Código/Nome do Dossiê")
    caixa = models.CharField(max_length=50, blank=True, help_text="Código/Nome da Caixa (opcional)")
    posicao = models.CharField(max_length=50, blank=True, help_text="Posição específica dentro do local")
    
    # Metadados do registro
    registrado_por = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='armazenamentos_registrados'
    )
    data_armazenamento = models.DateTimeField(auto_now_add=True)
    
    # Flags de controle
    ativo = models.BooleanField(
        default=True,
        help_text="Indica se o documento ainda está neste local"
    )
    data_retirada = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data em que o documento foi retirado deste local"
    )
    retirado_por = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='armazenamentos_retirados'
    )
    
    # Observações e motivo
    observacoes = models.TextField(blank=True)
    motivo_movimentacao = models.CharField(
        max_length=100,
        blank=True,
        help_text="Motivo da movimentação (consulta, reencaminhamento, etc)"
    )
    
    # Referência à movimentação que gerou este armazenamento
    movimentacao_origem = models.ForeignKey(
        MovimentacaoDocumento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='armazenamentos',
        help_text="Movimentação que gerou este registro de armazenamento"
    )

    def __str__(self):
        if self.local_armazenamento:
            return f"{self.documento.numero_protocolo} em {self.local_armazenamento.caminho_completo}"
        return f"{self.documento.numero_protocolo} em {self.localizacao_manual}"

    @property
    def localizacao_manual(self):
        """Retorna a localização manual formatada"""
        partes = []
        if self.estante:
            partes.append(f"Estante: {self.estante}")
        if self.prateleira:
            partes.append(f"Prateleira: {self.prateleira}")
        if self.dossie:
            partes.append(f"Dossiê: {self.dossie}")
        if self.caixa:
            partes.append(f"Caixa: {self.caixa}")
        if self.posicao:
            partes.append(f"Posição: {self.posicao}")
        return " | ".join(partes) if partes else "Não especificado"

    @property
    def localizacao_completa(self):
        """Retorna a localização completa (cadastrada ou manual)"""
        if self.local_armazenamento:
            return self.local_armazenamento.caminho_completo
        return self.localizacao_manual

    def clean(self):
        """Validação: deve ter local cadastrado OU localização manual"""
        super().clean()
        tem_local_cadastrado = self.local_armazenamento is not None
        tem_local_manual = any([self.estante, self.prateleira, self.dossie, self.caixa])
        
        if not tem_local_cadastrado and not tem_local_manual:
            raise ValidationError(
                'Deve informar um local de armazenamento cadastrado OU preencher os campos manuais.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Armazenamento de Documento"
        verbose_name_plural = "Armazenamentos de Documentos"
        ordering = ['-data_armazenamento']