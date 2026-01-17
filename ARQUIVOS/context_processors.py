# Em ARQUIVOS/context_processors.py
from ARQUIVOS.models import Notificacao

def notificacoes_context(request):
    if request.user.is_authenticated:
        user = request.user
        
        # Filtro simplificado: apenas notificações do usuário
        unread_count = Notificacao.objects.filter(usuario=user, lida=False).count()
        
        # Pega as 10 notificações mais recentes NÃO LIDAS para o dropdown
        recent_notifications = Notificacao.objects.filter(
            usuario=user, lida=False
        ).order_by('-data_criacao')[:10]

        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications
        }
    return {}