from django.urls import path

from .views.login import LoginView, RegisterView
from .views.views import (
    ConversationListCreateView,
    ConversationDetailView,
    MessageListCreateView,
    NoteView,
    TranscriptionView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('conversations/', ConversationListCreateView.as_view(), name='conversation-list'),
    path('conversations/<int:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/messages/', MessageListCreateView.as_view(), name='message-list'),
    path('notes/', NoteView.as_view(), name='notes'),
    path('notes/<int:message_id>/', NoteView.as_view(), name='message-notes'),
    path('transcribe/', TranscriptionView.as_view(), name='transcribe'),
]
