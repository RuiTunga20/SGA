# ARQUIVOS/consumers.py
"""
WebSocket consumers for real-time notifications.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async


class NotificacaoConsumer(AsyncWebsocketConsumer):
    """
    Consumer para notificações em tempo real.
    Cada utilizador é adicionado a grupos baseados na sua secção/departamento.
    """
    
    async def connect(self):
        """Conexão WebSocket estabelecida."""
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            print(f"[WS] Conexão rejeitada - usuário não autenticado")
            await self.close()
            return
        
        # Criar grupos baseados na hierarquia do utilizador
        self.groups = await self.get_user_groups()
        
        print(f"[WS] Usuário {self.user.username} conectado. Grupos: {self.groups}")
        
        # Adicionar utilizador a todos os seus grupos
        for group_name in self.groups:
            await self.channel_layer.group_add(
                group_name,
                self.channel_name
            )
        
        await self.accept()
        
        # Enviar contagem inicial de notificações e pendências
        count = await self.get_unread_count()
        pendencias_count = await self.get_pendencias_count()
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'count': count,
            'pendencias_count': pendencias_count
        }))
        print(f"[WS] Contagem inicial enviada para {self.user.username}: notificações={count}, pendências={pendencias_count}")
    
    async def disconnect(self, close_code):
        """Conexão WebSocket fechada."""
        if hasattr(self, 'groups'):
            for group_name in self.groups:
                await self.channel_layer.group_discard(
                    group_name,
                    self.channel_name
                )
    
    async def receive(self, text_data):
        """Receber mensagem do cliente."""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_read':
                await self.mark_notifications_read()
                await self.send(text_data=json.dumps({
                    'type': 'notifications_marked_read',
                    'success': True
                }))
            
            elif action == 'get_count':
                count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'notification_count',
                    'count': count
                }))
                
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """Enviar notificação para o cliente."""
        # Obter contagem atualizada
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'message': event['message'],
            'link': event.get('link', ''),
            'count': count
        }))
        print(f"[WS] Nova notificação enviada para {self.user.username}: {event['message']}")
    
    async def notification_count_update(self, event):
        """Atualizar contagem de notificações."""
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'count': event['count']
        }))
    
    async def pendencia_update(self, event):
        """Enviar atualização de pendências para o cliente."""
        pendencias_count = await self.get_pendencias_count()
        await self.send(text_data=json.dumps({
            'type': 'pendencia_update',
            'count': pendencias_count,
            'message': event.get('message', 'Pendências atualizadas')
        }))
        print(f"[WS] Pendências atualizadas para {self.user.username}: {pendencias_count}")
    
    @database_sync_to_async
    def get_user_groups(self):
        """Obter grupos do utilizador baseados na hierarquia."""
        groups = [f"user_{self.user.id}"]
        
        if self.user.seccao:
            groups.append(f"seccao_{self.user.seccao.id}")
            groups.append(f"departamento_{self.user.seccao.departamento.id}")
        elif self.user.departamento:
            groups.append(f"departamento_{self.user.departamento.id}")
        
        return groups
    
    @database_sync_to_async
    def get_unread_count(self):
        """Obter contagem de notificações não lidas."""
        from .models import Notificacao
        return Notificacao.objects.filter(
            usuario=self.user,
            lida=False
        ).count()
    
    @database_sync_to_async
    def mark_notifications_read(self):
        """Marcar todas notificações como lidas."""
        from .models import Notificacao
        Notificacao.objects.filter(
            usuario=self.user,
            lida=False
        ).update(lida=True)
    
    @database_sync_to_async
    def get_pendencias_count(self):
        """Obter contagem de pendências não confirmadas do utilizador."""
        from .models import MovimentacaoDocumento
        from django.db.models import Q, Exists, OuterRef
        
        user = self.user
        
        # Definir filtro baseado na hierarquia do utilizador
        if user.seccao:
            filtro_destino = Q(seccao_destino=user.seccao)
        elif user.departamento:
            filtro_destino = Q(departamento_destino=user.departamento)
        else:
            return 0
        
        # SUBQUERY: Verificar Obsolescência (movimentações futuras)
        movimentacoes_futuras = MovimentacaoDocumento.objects.filter(
            documento=OuterRef('documento'),
            id__gt=OuterRef('id')
        )
        
        # Query com mesma lógica da view pendencias()
        return MovimentacaoDocumento.objects.filter(
            filtro_destino,
            confirmado_recebimento=False,
            tipo_movimentacao='encaminhamento'
        ).annotate(
            ja_teve_andamento=Exists(movimentacoes_futuras)
        ).filter(
            ja_teve_andamento=False
        ).count()


# Função helper para enviar notificações (usar em views/signals)
async def send_notification_to_group(group_name, message, link=''):
    """
    Enviar notificação para um grupo.
    Usar em views ou signals para notificar utilizadores.
    """
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    
    await channel_layer.group_send(
        group_name,
        {
            'type': 'notification_message',
            'message': message,
            'link': link
        }
    )


def send_notification_sync(group_name, message, link=''):
    """
    Versão síncrona para usar em views normais.
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'notification_message',
            'message': message,
            'link': link
        }
    )


def send_pendencia_update_sync(group_name, message='Pendências atualizadas'):
    """
    Versão síncrona para enviar atualização de pendências.
    Usar em views após encaminhamento ou confirmação de recebimento.
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'pendencia_update',
            'message': message
        }
    )
