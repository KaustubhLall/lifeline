from django.urls import path
from django.http import JsonResponse
from django.utils import timezone

from .views.login import LoginView, RegisterView
from .views.views import (
    ConversationListCreateView,
    ConversationDetailView,
    MessageListCreateView,
    NoteView,
    TranscriptionView
)

def health_check(request):
    """Health check endpoint for deployment verification"""
    return JsonResponse({
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "version": "1.0.0",
        "service": "LifeLine Backend"
    })

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('conversations/', ConversationListCreateView.as_view(), name='conversation-list'),
    path('conversations/<int:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/messages/', MessageListCreateView.as_view(), name='message-list'),
    path('notes/', NoteView.as_view(), name='notes'),
    path('notes/<int:message_id>/', NoteView.as_view(), name='message-notes'),
    path('transcribe/', TranscriptionView.as_view(), name='transcribe'),
]
