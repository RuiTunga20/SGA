from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

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

    documento = models.ForeignKey('Documento', on_delete=models.CASCADE, related_name='movimentacoes')
    tipo_movimentacao = models.CharField(max_length=20, choices=TIPO_MOVIMENTACAO_CHOICES, default='encaminhamento')

    departamento_origem = models.ForeignKey(
        'Departamento',
        on_delete=models.PROTECT,
        related_name='movimentacoes_origem',
        null=True,
        blank=True
    )
    seccao_origem = models.ForeignKey(
        'Seccoes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_origem'
    )

    departamento_destino = models.ForeignKey(
        'Departamento',
        on_delete=models.PROTECT,
        related_name='movimentacoes_destino',
        null=True,
        blank=True
    )
    seccao_destino = models.ForeignKey(
        'Seccoes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_destino'
    )

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    data_movimentacao = models.DateTimeField(auto_now_add=True)

    observacoes = models.TextField(blank=True)
    despacho = models.TextField(blank=True)

    confirmado_recebimento = models.BooleanField(default=False)
    data_confirmacao = models.DateTimeField(null=True, blank=True)
    usuario_confirmacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
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
            if self.seccao_destino.departamento != self.departamento_destino:
                raise ValidationError({
                    'seccao_destino': f'A secção "{self.seccao_destino.nome}" não pertence ao departamento "{self.departamento_destino.nome}".'
                })

        if self.departamento_origem and self.seccao_origem:
            if self.seccao_origem.departamento != self.departamento_origem:
                raise ValidationError({
                    'seccao_origem': f'A secção de origem não pertence ao departamento de origem.'
                })

        # ===== VALIDAÇÃO DE ISOLAMENTO MULTI-TENANT =====
        # Garante que origem e destino pertencem à mesma administração do documento
        
        admin_documento = getattr(self.documento, 'administracao', None) if self.documento else None
        
        # Validar departamento de destino
        if self.departamento_destino and self.departamento_destino.administracao:
            if admin_documento and self.departamento_destino.administracao != admin_documento:
                raise ValidationError({
                    'departamento_destino': f'O departamento de destino "{self.departamento_destino.nome}" pertence a outra administração.'
                })
        
        # Validar secção de destino (herda administração via departamento)
        if self.seccao_destino:
            admin_seccao = getattr(self.seccao_destino, 'administracao', None)
            if admin_documento and admin_seccao and admin_seccao != admin_documento:
                raise ValidationError({
                    'seccao_destino': f'A secção de destino "{self.seccao_destino.nome}" pertence a outra administração.'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def destino_completo(self):
        """Retorna descrição completa do destino"""
        if self.seccao_destino:
            return f"{self.seccao_destino.nome} - {self.seccao_destino.departamento.nome}"
        elif self.departamento_destino:
            return self.departamento_destino.nome
        return "Sem destino especificado"

    @property
    def origem_completa(self):
        """Retorna descrição completa da origem"""
        if self.seccao_origem:
            return f"{self.seccao_origem.nome} - {self.seccao_origem.departamento.nome}"
        elif self.departamento_origem:
            return self.departamento_origem.nome
        return "Origem não especificada"

    def __str__(self):
        return f"{self.documento.numero_protocolo} - {self.get_tipo_movimentacao_display()}"

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data_movimentacao']
