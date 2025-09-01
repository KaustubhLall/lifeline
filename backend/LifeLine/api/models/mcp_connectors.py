import datetime
import json

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class MCPConnector(models.Model):
    """Model for storing MCP connector configurations"""

    CONNECTOR_TYPES = [
        ("gmail", "Gmail"),
        ("outlook", "Outlook"),
        ("calendar", "Calendar"),
        ("drive", "Google Drive"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("error", "Error"),
        ("pending", "Pending Authentication"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mcp_connectors")
    connector_type = models.CharField(max_length=50, choices=CONNECTOR_TYPES)
    name = models.CharField(max_length=100, help_text="User-friendly name for the connector")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    is_enabled = models.BooleanField(default=True)

    # OAuth and authentication fields
    client_id = models.CharField(max_length=255, blank=True, null=True)
    client_secret = models.CharField(max_length=255, blank=True, null=True)
    redirect_uri = models.URLField(blank=True, null=True)
    scopes = models.JSONField(default=list, help_text="OAuth scopes required")

    # Configuration and settings
    config = models.JSONField(default=dict, help_text="Connector-specific configuration")
    # New credential storage (DB instead of filesystem-only)
    credentials_data = models.JSONField(blank=True, null=True, help_text="OAuth credential payload")
    token_expiry = models.DateTimeField(blank=True, null=True, help_text="Access token expiry")
    has_refresh_token = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_authenticated = models.DateTimeField(blank=True, null=True)
    last_used = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ["user", "connector_type", "name"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.get_connector_type_display()} ({self.name})"

    def mark_as_authenticated(self):
        """Mark connector as authenticated and active"""
        self.status = "active"
        self.last_authenticated = timezone.now()
        self.save(update_fields=["status", "last_authenticated"])

    def mark_as_used(self):
        """Update last used timestamp"""
        self.last_used = timezone.now()
        self.save(update_fields=["last_used"])

    def mark_as_error(self, error_message=None):
        """Mark connector as having an error"""
        self.status = "error"
        if error_message:
            self.config["last_error"] = error_message
        self.save(update_fields=["status", "config"])

    def store_credentials(self, credentials):
        """Persist google.oauth2.credentials.Credentials in DB fields."""
        try:
            data = json.loads(credentials.to_json())
        except Exception:
            data = {}
        self.credentials_data = data
        # Expiry may be in credentials.expiry
        expiry = getattr(credentials, "expiry", None)
        if expiry:
            # Ensure timezone-aware
            if timezone.is_naive(expiry):
                expiry = timezone.make_aware(expiry, datetime.timezone.utc)
            self.token_expiry = expiry
        self.has_refresh_token = bool(getattr(credentials, "refresh_token", None))
        self.mark_as_authenticated()
        self.save(
            update_fields=["credentials_data", "token_expiry", "has_refresh_token", "status", "last_authenticated"]
        )

    def load_credentials(self):
        """Return google.oauth2.credentials.Credentials or None."""
        from google.oauth2.credentials import Credentials

        if not self.credentials_data:
            return None
        try:
            return Credentials.from_authorized_user_info(self.credentials_data, scopes=self.scopes or [])
        except Exception:
            return None


class MCPOperation(models.Model):
    """Model for logging MCP operations"""

    OPERATION_TYPES = [
        ("send_email", "Send Email"),
        ("read_email", "Read Email"),
        ("search_emails", "Search Emails"),
        ("list_labels", "List Labels"),
        ("create_label", "Create Label"),
        ("modify_email", "Modify Email"),
        ("delete_email", "Delete Email"),
    ]

    STATUS_CHOICES = [
        ("success", "Success"),
        ("error", "Error"),
        ("pending", "Pending"),
    ]

    connector = models.ForeignKey(MCPConnector, on_delete=models.CASCADE, related_name="operations")
    operation_type = models.CharField(max_length=50, choices=OPERATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Operation details
    request_data = models.JSONField(default=dict, help_text="Request parameters")
    response_data = models.JSONField(default=dict, help_text="Response data")
    error_message = models.TextField(blank=True, null=True)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    duration_ms = models.IntegerField(blank=True, null=True, help_text="Duration in milliseconds")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.connector} - {self.get_operation_type_display()} ({self.status})"

    def mark_completed(self, response_data=None, error_message=None):
        """Mark operation as completed"""
        self.completed_at = timezone.now()
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)

        if error_message:
            self.status = "error"
            self.error_message = error_message
        else:
            self.status = "success"
            if response_data:
                self.response_data = response_data

        self.save(update_fields=["status", "completed_at", "duration_ms", "response_data", "error_message"])
