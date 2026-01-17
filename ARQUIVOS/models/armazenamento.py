from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

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
        'Departamento',
        on_delete=models.CASCADE,
        related_name='locais_armazenamento',
        help_text="Departamento onde este local está fisicamente"
    )
    seccao = models.ForeignKey(
        'Seccoes',
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
        'Documento',
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
        settings.AUTH_USER_MODEL,
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
        settings.AUTH_USER_MODEL,
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
        'MovimentacaoDocumento',
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
