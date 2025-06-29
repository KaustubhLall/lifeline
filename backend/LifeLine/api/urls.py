from django.urls import path
from .views.login import RegisterView, LoginView
from .views.views import (
    ConversationListCreateView,
    ConversationDetailView,
    MessageListCreateView,
    NoteView
)

urlpatterns = [
    # Auth endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    # Conversation endpoints
    path('conversations/', ConversationListCreateView.as_view(), name='conversations'),
    path('conversations/<int:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/messages/', MessageListCreateView.as_view(), name='messages'),

    # Notes endpoints
    path('notes/', NoteView.as_view(), name='user-notes'),
    path('messages/<int:message_id>/notes/', NoteView.as_view(), name='message-notes'),
]
