from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class Administracao(models.Model):
    TIPO_MUNICIPIO_CHOICES = [
        ('A', 'Tipo A'),
        ('B', 'Tipo B'),
        ('C', 'Tipo C'),
        ('D', 'Tipo D'),
        ('E', 'Tipo E'),
    ]
    nome = models.CharField(max_length=255)
    tipo_municipio = models.CharField(max_length=1, choices=TIPO_MUNICIPIO_CHOICES, default='A')

    def __str__(self):
        return self.nome   
    
    class Meta:
        verbose_name = "Administração"
        verbose_name_plural = "Administrações" 

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
    administracao = models.ForeignKey(
        'Administracao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_administracao'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Valida a consistência entre departamento e secção"""
        super().clean()

        # Se tem secção, valida se pertence ao departamento
        if self.seccao and self.departamento:
            if self.seccao.departamento != self.departamento:
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
            return self.seccao.departamento
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
            'departamento': self.departamento if not self.seccao else self.seccao.departamento
        }


    def __str__(self):
        if self.seccao:
            return f"{self.username} - {self.seccao.nome} ({self.seccao.departamento.nome})"
        elif self.departamento:
            return f"{self.username} - {self.departamento.nome}"
        return f"{self.username} - {self.get_nivel_acesso_display()}"
