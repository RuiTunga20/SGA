from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages

class AdministracaoRequiredMixin(AccessMixin):
    """
    Mixin para garantir que o usuário tenha uma administração vinculada.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if request.user.nivel_acesso != 'admin_sistema' and not request.user.administracao:
            messages.error(request, "Seu usuário não está vinculado a nenhuma administração.")
            return redirect('login') 
            
        return super().dispatch(request, *args, **kwargs)
