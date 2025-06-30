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

class Memory(models.Model):
    """Store user memories for RAG functionality"""
    MEMORY_TYPE_CHOICES = [
        ('preference', 'Preference'),
        ('goal', 'Goal'),
        ('personal', 'Personal'),
        ('professional', 'Professional'),
        ('relationship', 'Relationship'),
        ('challenge', 'Challenge'),
        ('skill', 'Skill'),
        ('interest', 'Interest'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memories')
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    category = models.CharField(max_length=50, default='general')  # preference, goal, personal, professional, etc.
    memory_type = models.CharField(max_length=20, choices=MEMORY_TYPE_CHOICES, default='general')
    importance = models.CharField(max_length=10, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], default='medium')
    importance_score = models.FloatField(default=0.5, help_text="Numerical importance score (0.0-1.0)")
    context = models.TextField(blank=True)  # Context about when/how this was mentioned
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name='extracted_memories')
    source_conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_memories')
    source_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True, related_name='extracted_memories')
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # Additional metadata
    embedding = models.JSONField(default=list, blank=True, help_text="Vector embedding for similarity search")
    extraction_confidence = models.FloatField(default=0.0, help_text="Confidence of memory extraction (0.0-1.0)")
    is_auto_extracted = models.BooleanField(default=True, help_text="Whether this memory was automatically extracted")
    access_count = models.IntegerField(default=0, help_text="Number of times this memory has been accessed")
    last_accessed = models.DateTimeField(null=True, blank=True, help_text="Last time this memory was used in RAG")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-importance_score', '-updated_at']
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'memory_type']),
            models.Index(fields=['user', 'importance']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'importance_score']),
            models.Index(fields=['user', 'access_count']),
            models.Index(fields=['user', 'last_accessed']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title or self.content[:50]}..."

class MessageNote(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_notes')

    class Meta:
        ordering = ['-created_at']

class Memory(models.Model):
    MEMORY_TYPES = [
        ('personal', 'Personal Information'),
        ('preference', 'User Preference'),
        ('goal', 'Goal or Objective'),
        ('insight', 'Insight or Learning'),
        ('fact', 'Important Fact'),
        ('context', 'Contextual Information'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memories')
    content = models.TextField(help_text="The memory content")
    title = models.CharField(max_length=255, blank=True, null=True, help_text="Optional title for the memory")
    memory_type = models.CharField(max_length=20, choices=MEMORY_TYPES, default='personal')

    # Embedding for semantic search
    embedding = models.JSONField(blank=True, null=True, help_text="Vector embedding of the memory content")

    # Source information
    source_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='extracted_memories',
                                     help_text="Original message this memory was extracted from")
    source_conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='extracted_memories',
                                          help_text="Conversation this memory was extracted from")

    # Metadata and tags
    tags = models.JSONField(default=list, blank=True, help_text="Tags for categorizing memories")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Relevance and importance scoring
    importance_score = models.FloatField(default=0.5, help_text="Importance score (0.0 to 1.0)")
    last_accessed = models.DateTimeField(auto_now_add=True, help_text="When this memory was last accessed")
    access_count = models.IntegerField(default=0, help_text="How many times this memory has been accessed")

    # Auto-extraction flags
    is_auto_extracted = models.BooleanField(default=False, help_text="Was this memory automatically extracted")
    extraction_confidence = models.FloatField(null=True, blank=True, help_text="Confidence score for auto-extraction")

    class Meta:
        ordering = ['-updated_at', '-importance_score']
        verbose_name_plural = "Memories"

    def __str__(self):
        return self.title or f"Memory {self.id}: {self.content[:50]}..."
