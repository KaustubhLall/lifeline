from django.db import models
from .user_auth import User

# Create your models here.

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    context = models.JSONField(default=dict, blank=True)  # Store conversation context/memory

    class Meta:
        ordering = ['-updated_at']

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_bot = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)  # Store message-specific metadata
    role = models.CharField(max_length=20, default='user')  # user, assistant, system

    class Meta:
        ordering = ['created_at']

class MessageNote(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_notes')

    class Meta:
        ordering = ['-created_at']

class UserNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-updated_at']
