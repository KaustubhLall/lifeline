from django.db import models

from .user_auth import User


# Create your models here.


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    context = models.JSONField(default=dict, blank=True)  # Store conversation context/memory

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title or f'Chat {self.id}'}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_bot = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)  # Store message-specific metadata
    role = models.CharField(max_length=20, default="user")  # user, assistant, system

    # Store full prompt for debugging and prompt engineering
    full_prompt = models.TextField(blank=True, help_text="Complete prompt sent to LLM (for debugging)")
    raw_user_input = models.TextField(blank=True, help_text="Original user input before prompt construction")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        role_display = "🤖" if self.is_bot else "👤"
        return f"{role_display} {self.content[:50]}..."


class PromptDebug(models.Model):
    """Debug table to store full prompts sent to LLM for debugging"""

    user_message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="prompt_debug",
        help_text="The user message that triggered this prompt",
    )
    bot_response = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prompt_debug_response",
        help_text="The bot response generated from this prompt",
    )
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="prompt_debugs")

    # Full prompt data
    full_prompt = models.TextField(help_text="Complete prompt sent to LLM")
    system_prompt = models.TextField(blank=True, help_text="System prompt portion")
    memory_context = models.TextField(blank=True, help_text="Memory context included")
    conversation_history = models.TextField(blank=True, help_text="Conversation history included")

    # LLM call metadata
    model_used = models.CharField(max_length=50, default="gpt-4.1-nano")
    mode_used = models.CharField(max_length=20, default="conversational")
    temperature = models.FloatField(default=0.0)

    # Stats and metrics
    prompt_length = models.IntegerField(default=0, help_text="Length of full prompt in characters")
    prompt_tokens = models.IntegerField(null=True, blank=True, help_text="Token count of prompt")
    response_tokens = models.IntegerField(null=True, blank=True, help_text="Token count of response")
    total_tokens = models.IntegerField(null=True, blank=True, help_text="Total tokens used")

    # Memory and context stats
    memories_used_count = models.IntegerField(default=0, help_text="Number of memories included")
    relevant_memories_count = models.IntegerField(default=0, help_text="Number of relevant memories")
    conversation_memories_count = models.IntegerField(default=0, help_text="Number of conversation memories")
    history_messages_count = models.IntegerField(default=0, help_text="Number of history messages included")

    # Response metadata
    response_time_ms = models.IntegerField(null=True, blank=True, help_text="Response time in milliseconds")
    api_error = models.TextField(blank=True, help_text="Any API error that occurred")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Prompt Debug Entry"
        verbose_name_plural = "Prompt Debug Entries"

    def __str__(self):
        return f"Debug {self.id} - {self.user_message.sender.username} - {self.model_used}"


class Memory(models.Model):
    """Store user memories for RAG functionality"""

    MEMORY_TYPES = [
        ("personal", "Personal Information"),
        ("preference", "User Preference"),
        ("goal", "Goal or Objective"),
        ("insight", "Insight or Learning"),
        ("fact", "Important Fact"),
        ("context", "Contextual Information"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memories")
    content = models.TextField(help_text="The memory content")
    title = models.CharField(max_length=255, blank=True, null=True, help_text="Optional title for the memory")
    memory_type = models.CharField(max_length=20, choices=MEMORY_TYPES, default="personal")

    # Embedding for semantic search
    embedding = models.JSONField(blank=True, null=True, help_text="Vector embedding of the memory content")

    # Source information
    source_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extracted_memories",
        help_text="Original message this memory was extracted from",
    )
    source_conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extracted_memories",
        help_text="Conversation this memory was extracted from",
    )

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
        ordering = ["-updated_at", "-importance_score"]
        verbose_name_plural = "Memories"
        indexes = [
            models.Index(fields=["user", "memory_type"]),
            models.Index(fields=["user", "importance_score"]),
            models.Index(fields=["user", "is_auto_extracted"]),
            models.Index(fields=["user", "access_count"]),
            models.Index(fields=["user", "last_accessed"]),
        ]

    def __str__(self):
        return self.title or f"Memory {self.id}: {self.content[:50]}..."


class MessageNote(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="notes")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_notes")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.message.id}: {self.note[:50]}..."
