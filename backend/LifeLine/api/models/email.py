from django.db import models
from django.utils import timezone
from .user_auth import User


class Email(models.Model):
    """Model for storing emails locally with metadata and embeddings"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emails")
    
    # Gmail specific metadata (essential for external API integration)
    message_id = models.CharField(max_length=255, unique=True, help_text="Gmail message ID")
    thread_id = models.CharField(max_length=255, blank=True, null=True, help_text="Gmail thread ID")
    
    # Email headers and content
    subject = models.TextField(blank=True, null=True)
    sender = models.EmailField(help_text="From email address")
    recipient = models.EmailField(help_text="To email address")
    
    # Additional recipients
    cc_recipients = models.JSONField(default=list, blank=True, help_text="CC recipients")
    bcc_recipients = models.JSONField(default=list, blank=True, help_text="BCC recipients")
    
    # Content
    body_text = models.TextField(blank=True, null=True, help_text="Plain text body")
    body_html = models.TextField(blank=True, null=True, help_text="HTML body")
    
    # Timestamps
    sent_date = models.DateTimeField(help_text="When the email was sent")
    received_date = models.DateTimeField(help_text="When the email was received")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Gmail labels and flags
    labels = models.JSONField(default=list, blank=True, help_text="Gmail labels")
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    
    # Attachments metadata
    has_attachments = models.BooleanField(default=False)
    attachments_metadata = models.JSONField(default=list, blank=True, help_text="Attachment details")
    
    # Embedding for semantic search (similar to Memory model)
    embedding = models.JSONField(blank=True, null=True, help_text="Vector embedding of email content")
    embedding_model = models.CharField(max_length=100, blank=True, null=True, help_text="Model used for embedding")
    
    # Search and relevance
    content_for_search = models.TextField(blank=True, null=True, help_text="Processed content for search")
    
    # Metadata for external integration
    raw_email_data = models.JSONField(blank=True, null=True, help_text="Full raw email data from Gmail API")
    
    # Processing status
    is_processed = models.BooleanField(default=False, help_text="Whether email has been processed for embeddings")
    processing_error = models.TextField(blank=True, null=True, help_text="Error message if processing failed")
    
    class Meta:
        ordering = ["-received_date"]
        indexes = [
            models.Index(fields=["user", "message_id"]),
            models.Index(fields=["user", "received_date"]),
            models.Index(fields=["user", "sender"]),
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "is_processed"]),
            models.Index(fields=["thread_id"]),
        ]
        
    def __str__(self):
        return f"Email {self.message_id}: {self.subject[:50] if self.subject else 'No Subject'}"
    
    def get_display_content(self):
        """Get the best available content for display"""
        if self.body_text:
            return self.body_text
        elif self.body_html:
            # Strip HTML tags for display (basic)
            import re
            return re.sub(r'<[^>]+>', '', self.body_html)
        return ""
    
    def prepare_content_for_embedding(self):
        """Prepare email content for embedding generation"""
        content_parts = []
        
        if self.subject:
            content_parts.append(f"Subject: {self.subject}")
        
        content_parts.append(f"From: {self.sender}")
        content_parts.append(f"To: {self.recipient}")
        
        if self.cc_recipients:
            content_parts.append(f"CC: {', '.join(self.cc_recipients)}")
        
        if self.body_text:
            content_parts.append(f"Body: {self.body_text}")
        elif self.body_html:
            # Basic HTML stripping
            import re
            clean_body = re.sub(r'<[^>]+>', '', self.body_html)
            content_parts.append(f"Body: {clean_body}")
        
        return "\n".join(content_parts)


class EmailMigrationStatus(models.Model):
    """Track email migration status for users"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="email_migration_status")
    
    # Migration status
    is_migrating = models.BooleanField(default=False)
    last_migration_started = models.DateTimeField(blank=True, null=True)
    last_migration_completed = models.DateTimeField(blank=True, null=True)
    
    # Statistics
    total_emails_found = models.IntegerField(default=0)
    emails_processed = models.IntegerField(default=0)
    emails_failed = models.IntegerField(default=0)
    
    # Error tracking
    last_error = models.TextField(blank=True, null=True)
    
    # Progress tracking
    migration_progress = models.JSONField(default=dict, help_text="Detailed migration progress")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Email Migration Statuses"
        
    def __str__(self):
        return f"Migration Status for {self.user.username}"
    
    def update_progress(self, processed=0, failed=0, total=None, error=None):
        """Update migration progress"""
        if total is not None:
            self.total_emails_found = total
        self.emails_processed += processed
        self.emails_failed += failed
        if error:
            self.last_error = error
        self.save()
    
    def start_migration(self):
        """Mark migration as started"""
        self.is_migrating = True
        self.last_migration_started = timezone.now()
        self.emails_processed = 0
        self.emails_failed = 0
        self.last_error = None
        self.save()
    
    def complete_migration(self):
        """Mark migration as completed"""
        self.is_migrating = False
        self.last_migration_completed = timezone.now()
        self.save()