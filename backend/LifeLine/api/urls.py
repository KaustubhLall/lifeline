from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.urls import path
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .views.gmail_mcp import (
    GmailAuthView,
    GmailOperationsView,
    GmailStatusView,
    GmailConfigUploadView,
    gmail_oauth_callback,
)
from .views.login import LoginView, RegisterView
from .views.user_settings import UserProfileView, ChangePasswordView, MemoryListView, MemoryDetailView
from .views.email_views import (
    EmailSearchView,
    EmailStatsView,
    EmailDetailView,
    EmailEmbeddingView,
    EmailMigrationStatusView,
)
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
    # Gmail MCP endpoints
    path("mcp/gmail/auth/", GmailAuthView.as_view(), name="gmail-mcp-auth"),
    path("mcp/gmail/operations/", GmailOperationsView.as_view(), name="gmail-mcp-operations"),
    path("mcp/gmail/status/", GmailStatusView.as_view(), name="gmail-mcp-status"),
    path("mcp/gmail/upload-config/", GmailConfigUploadView.as_view(), name="gmail-mcp-upload-config"),
    path("auth/gmail/callback/", gmail_oauth_callback, name="gmail-oauth-callback"),
    # Email API endpoints
    path("emails/search/", EmailSearchView.as_view(), name="email-search"),
    path("emails/stats/", EmailStatsView.as_view(), name="email-stats"),
    path("emails/<int:email_id>/", EmailDetailView.as_view(), name="email-detail"),
    path("emails/generate-embeddings/", EmailEmbeddingView.as_view(), name="email-embeddings"),
    path("emails/migration-status/", EmailMigrationStatusView.as_view(), name="email-migration-status"),
    # Existing endpoints
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list"),
    path("conversations/<int:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("conversations/<int:conversation_id>/messages/", MessageListCreateView.as_view(), name="message-list"),
    path("notes/", NoteView.as_view(), name="notes"),
    path("notes/<int:message_id>/", NoteView.as_view(), name="message-notes"),
    path("transcribe/", TranscriptionView.as_view(), name="transcribe"),
]
