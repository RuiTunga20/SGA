from django.db import models
from django.conf import settings

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
    Modelo simplificado para notificações.
    Cada notificação é criada diretamente para um usuário específico.
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificacoes')
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
