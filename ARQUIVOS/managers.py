from django.db import models
from django.db.models import Q


class DocumentoManager(models.Manager):
    def para_usuario(self, user):
        """
        Filtra documentos visíveis para o usuário baseado na hierarquia.
        """
        # 1. Admins veem tudo
        niveis_admin = ['admin_sistema', 'admin_municipal', 'admin', 'diretor', 'diretor_municipal']
        if user.is_superuser or user.nivel_acesso in niveis_admin:
            return self.get_queryset()

        qs = self.get_queryset()

        # 2. Usuário de Secção
        if hasattr(user, 'seccao') and user.seccao:
            return qs.filter(
                Q(seccao_atual=user.seccao) |
                (Q(departamento_atual=user.seccao.Departamento) & Q(seccao_atual__isnull=True))
            )

        # 3. Usuário de Departamento
        if hasattr(user, 'departamento') and user.departamento:
            return qs.filter(departamento_atual=user.departamento)

        # 4. Fallback
        return qs.none()