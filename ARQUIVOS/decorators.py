from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def requer_contexto_hierarquico(view_func):
    """
    Injeta 'request.contexto_usuario' com departamento/secção validados.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        ctx = {
            'departamento': None,
            'seccao': None,
            'is_seccao': False,
            'is_departamento': False
        }

        # 1. Prioridade: Secção
        if hasattr(user, 'seccao') and user.seccao:
            ctx['seccao'] = user.seccao
            ctx['departamento'] = user.seccao.Departamento
            ctx['is_seccao'] = True

        # 2. Departamento Direto
        elif hasattr(user, 'departamento') and user.departamento:
            ctx['departamento'] = user.departamento
            ctx['is_departamento'] = True

        # 3. Segurança
        else:
            messages.error(request, 'Usuário sem departamento configurado.')
            return redirect('/')

        request.contexto_usuario = ctx
        return view_func(request, *args, **kwargs)

    return _wrapped_view