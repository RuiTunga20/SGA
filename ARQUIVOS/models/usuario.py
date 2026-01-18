from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from ARQUIVOS.managers import AdministracaoManager, UsuarioManager

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
    provincia = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nome   
    
    objects = AdministracaoManager()

    class Meta:
        verbose_name = "Administração"
        verbose_name_plural = "Administrações" 

class CustomUser(AbstractUser):
    objects = UsuarioManager()

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
    # Usuário DEVE pertencer a uma administração (OBRIGATÓRIO - Multi-Tenant)
    administracao = models.ForeignKey(
        'Administracao',
        on_delete=models.PROTECT,  # Não pode deletar admin com usuários
        null=False,  # OBRIGATÓRIO
        blank=False,
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
            
        # Validação Redundante de Segurança (Isolamento)
        if self.administracao and self.departamento and self.departamento.administracao:
            if self.departamento.administracao != self.administracao:
                raise ValidationError({
                    'departamento': f'O departamento "{self.departamento.nome}" pertence à administração "{self.departamento.administracao.nome}", mas o usuário está na administração "{self.administracao.nome}".'
                })

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

    def pode_ver_usuario(self, outro_usuario):
        """
        Verifica se este usuário pode ver o outro_usuario.
        """
        # Admin sistema vê todos
        if self.nivel_acesso == 'admin_sistema':
            return True
        
        # Se não tem administração, não vê ninguém (ou só a si mesmo?)
        if not self.administracao:
            return False
            
        # Mesma administração
        return self.administracao == outro_usuario.administracao


    def __str__(self):
        if self.seccao:
            return f"{self.username} - {self.seccao.nome} ({self.seccao.departamento.nome})"
        elif self.departamento:
            return f"{self.username} - {self.departamento.nome}"
        return f"{self.username} - {self.get_nivel_acesso_display()}"
