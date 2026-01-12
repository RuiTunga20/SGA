# Em ARQUIVOS/context_processors.py
from ARQUIVOS.models import Notificacao

def notificacoes_context(request):
    if request.user.is_authenticated:
        # Conta apenas as notificações não lidas
        unread_count = Notificacao.objects.filter(usuario=request.user, lida=False).count()
        # Pega as 5 notificações mais recesntes (lidas ou não) para o dropdown
        recent_notifications = Notificacao.objects.filter(usuario=request.user)[:5]

        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications
        }
    return {}