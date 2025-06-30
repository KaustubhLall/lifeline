from django.contrib import admin
from .models.user_auth import User
from .models.chat import Conversation, Message, MessageNote, UserNote, Memory

admin.site.register(User)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(MessageNote)
admin.site.register(UserNote)
admin.site.register(Memory)
