from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from ARQUIVOS.managers import DepartamentoManager

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
        ('G', 'Governo Provincial'),
        ('M', 'Ministério'),
    ]

    nome = models.CharField(max_length=255, unique=False)
    codigo = models.CharField(max_length=20, unique=False, blank=True)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='departamentos_responsavel')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tipo_municipio = models.CharField(max_length=1, choices=TIPO_MUNICIPIO_CHOICES, default='A')
    
    # Departamento DEVE pertencer a uma administração (OBRIGATÓRIO)
    administracao = models.ForeignKey(
        'ARQUIVOS.Administracao', 
        on_delete=models.CASCADE, 
        null=False,  # OBRIGATÓRIO - Multi-Tenant
        blank=False, 
        related_name='departamentos_especificos'
    )

    objects = DepartamentoManager()

    def clean(self):
        """Valida a consistência do departamento"""
        super().clean()
        
        # Se tem administração, o tipo deve ser compatível
        if self.administracao:
            if self.tipo_municipio != self.administracao.tipo_municipio:
                raise ValidationError({
                    'tipo_municipio': f'O tipo do departamento ({self.tipo_municipio}) deve ser igual ao da administração ({self.administracao.tipo_municipio}).'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.nome} ({self.administracao.nome})"

    class Meta:
        verbose_name = "Direção"
        verbose_name_plural = "Direções"
        unique_together = [('nome', 'administracao')]


class Seccoes(models.Model):
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255, unique=False)
    codigo = models.CharField(max_length=20, unique=False, blank=True)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='seccao_responsavel')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def administracao(self):
        """Herda administração do departamento pai"""
        return self.departamento.administracao if self.departamento else None

    def __str__(self):
        admin_nome = self.administracao.nome if self.administracao else self.departamento.tipo_municipio
        return f"{self.nome} [{admin_nome}]"

    class Meta:
        verbose_name = "Secção"
        verbose_name_plural = "Secções"
        unique_together = ('nome', 'departamento')

