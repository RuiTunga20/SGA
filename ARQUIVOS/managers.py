from django.db import models
from django.db.models import Q
from ARQUIVOS.models.mixins import SoftDeleteManager


class DocumentoManager(SoftDeleteManager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            'tipo_documento',
            'departamento_origem',
            'departamento_atual',
            'seccao_atual',
            'criado_por',
            'responsavel_atual'
        )

    def para_usuario(self, user):
        """
        Filtra documentos visíveis para o usuário baseado na hierarquia e ADMINISTRAÇÃO.
        """
        qs = self.get_queryset()

        # 0. Regra de Ouro: Isolamento por Administração
        if user.nivel_acesso != 'admin_sistema':
            if not user.administracao:
                return qs.none()
            
            # AGORA FILTRAMOS PELO CAMPO DIRETO NO DOCUMENTO
            # Isso resolve o problema de documentos em departamentos genéricos
            qs = qs.filter(administracao=user.administracao)

        # 1. Admins veem tudo (da sua administração)
        niveis_admin = ['admin_sistema', 'admin_municipal', 'admin', 'diretor', 'diretor_municipal']
        if user.is_superuser or user.nivel_acesso in niveis_admin:
            return qs

        # 2. Usuário de Secção
        if hasattr(user, 'seccao') and user.seccao:
            return qs.filter(
                Q(seccao_atual=user.seccao) |
                (Q(departamento_atual=user.seccao.departamento) & Q(seccao_atual__isnull=True))
            )

        # 3. Usuário de Departamento
        if hasattr(user, 'departamento') and user.departamento:
            return qs.filter(departamento_atual=user.departamento)

        # 4. Fallback
        return qs.none()


class AdministracaoManager(models.Manager):
    """Manager para Administracao"""
    pass


class DepartamentoManager(models.Manager):
    """Manager para Departamento com lógica de isolamento"""

    def para_administracao(self, administracao):
        """
        Retorna departamentos que a administração pode ver:
        1. Departamentos genéricos do mesmo tipo da administração (ex: Tipo A)
        2. Departamentos específicos vinculados a esta administração
        """
        if not administracao:
            return self.none()

        return self.filter(
            Q(tipo_municipio=administracao.tipo_municipio, administracao__isnull=True) |  # Genéricos do mesmo tipo
            Q(administracao=administracao)  # Específicos desta administração
        ).distinct()


from django.contrib.auth.models import UserManager as BaseUserManager

class UsuarioManager(BaseUserManager):
    """Manager para CustomUser com lógica de isolamento"""

    def da_mesma_administracao(self, usuario):
        """
        Retorna apenas usuários da mesma administração do usuário solicitante.
        Se o usuário for admin de sistema, pode ver todos.
        """
        if not usuario or not usuario.is_authenticated:
            return self.none()

        # Admin Sistema (sem administração vinculada) vê TODAS
        if usuario.nivel_acesso == 'admin_sistema':
            return self.all()

        if not usuario.administracao:
            return self.none()

        return self.filter(administracao=usuario.administracao)

    def para_usuario(self, usuario):
        """Alias para da_mesma_administracao"""
        return self.da_mesma_administracao(usuario)