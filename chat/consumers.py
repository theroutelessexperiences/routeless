import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from marketplace.models import Conversation, Message
from asgiref.sync import sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        # Check authentication
        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        # Check permission (is this user part of the conversation?)
        is_participant = await self.is_user_in_conversation(self.conversation_id, self.scope['user'].id)
        if not is_participant:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_text = text_data_json.get('message', '').strip()

        if not message_text:
            return
            
        # Basic rate limiting (max 5 messages per 5 seconds per user)
        import time
        if not hasattr(self, '_message_timestamps'):
            self._message_timestamps = []
        
        current_time = time.time()
        # Keep only timestamps from last 5 seconds
        self._message_timestamps = [ts for ts in self._message_timestamps if current_time - ts < 5.0]
        
        if len(self._message_timestamps) >= 5:
            # Rate limited, send error back explicitly or silently drop
            await self.send(text_data=json.dumps({
                'error': 'You are sending messages too fast. Please wait a moment.'
            }))
            return
            
        self._message_timestamps.append(current_time)
            
        # Basic input sanitization to prevent XSS
        import html
        message_text = html.escape(message_text)[:1000]  # Limit length as well

        sender_id = self.scope['user'].id

        # Save message to database
        message_obj = await self.save_message(self.conversation_id, sender_id, message_text)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender_id': sender_id,
                'sender_name': self.scope['user'].username,
                'message_id': message_obj.id,
                'created_at': message_obj.created_at.strftime('%b. %d, %Y, %I:%M %p')
            }
        )

        # Notify the other user
        recipient_id = await self.get_recipient_id(self.conversation_id, sender_id)
        if recipient_id:
            from chat.utils import send_realtime_notification
            await sync_to_async(send_realtime_notification)(
                user_id=recipient_id,
                title="New Message",
                message=f"You received a new message from {self.scope['user'].username}",
                link=f"/messages/{self.conversation_id}/"
            )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        sender_name = event['sender_name']
        message_id = event['message_id']
        created_at = event['created_at']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'message_id': message_id,
            'created_at': created_at
        }))

        # If we received the chat message from the group but we didn't send it, don't trigger a notification.
        # Actually, notification is better triggered upon saving.
        
    @database_sync_to_async
    def get_recipient_id(self, conversation_id, sender_id):
        conv = Conversation.objects.get(id=conversation_id)
        return conv.host_id if conv.user_id == sender_id else conv.user_id

    @database_sync_to_async
    def is_user_in_conversation(self, conversation_id, user_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
            return conv.user_id == user_id or conv.host_id == user_id
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, conversation_id, sender_id, text):
        conv = Conversation.objects.get(id=conversation_id)
        sender = User.objects.get(id=sender_id)
        return Message.objects.create(
            conversation=conv,
            sender=sender,
            text=text
        )

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return
            
        self.user_id = self.scope['user'].id
        self.room_group_name = f'notify_{self.user_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def user_notification(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event['notification']))
