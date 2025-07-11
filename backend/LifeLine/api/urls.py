from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.urls import path
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .views.login import LoginView, RegisterView
from .views.user_settings import UserProfileView, ChangePasswordView, MemoryListView, MemoryDetailView
from .views.views import (
    ConversationListCreateView,
    ConversationDetailView,
    MessageListCreateView,
    NoteView,
    TranscriptionView,
)


def health_check(request):
    """Health check endpoint for deployment verification"""
    return JsonResponse(
        {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "version": "1.0.0",
            "service": "LifeLine Backend",
        }
    )


@require_http_methods(["GET"])
def csrf_token(request):
    """Get CSRF token for frontend requests"""
    token = get_token(request)
    return JsonResponse({"csrfToken": token})


urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("csrf/", csrf_token, name="csrf_token"),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    # User settings endpoints
    path("user/profile/", UserProfileView.as_view(), name="user-profile"),
    path("user/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("memories/", MemoryListView.as_view(), name="user-memories"),
    path("memories/<int:memory_id>/", MemoryDetailView.as_view(), name="memory-detail"),
    # Existing endpoints
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list"),
    path("conversations/<int:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("conversations/<int:conversation_id>/messages/", MessageListCreateView.as_view(), name="message-list"),
    path("notes/", NoteView.as_view(), name="notes"),
    path("notes/<int:message_id>/", NoteView.as_view(), name="message-notes"),
    path("transcribe/", TranscriptionView.as_view(), name="transcribe"),
]
