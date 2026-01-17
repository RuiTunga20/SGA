from django.db import models
from django.conf import settings

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
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
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
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255, unique=False)
    codigo = models.CharField(max_length=20, unique=False, blank=True)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='seccao_responsavel')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.departamento.tipo_municipio})"

    class Meta:
        verbose_name = "Secção"
        verbose_name_plural = "Secções"
        unique_together = ('nome', 'departamento')
