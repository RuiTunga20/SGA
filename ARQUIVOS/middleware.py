import logging
from django.shortcuts import redirect
from django.contrib import messages

logger = logging.getLogger('security_audit')

class SecurityAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            # Logar tentativas de acesso proibido ou não encontrado (pode ser tentativa de acesso a recurso isolado)
            if response.status_code in [403, 404]:
                logger.warning(
                    f"AUDIT: User {request.user.username} (Admin: {getattr(request.user.administracao, 'nome', 'N/A')}) "
                    f"attempted to access {request.path} [{request.method}] - Status: {response.status_code}"
                )
                
        return response
