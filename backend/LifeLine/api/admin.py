from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models.chat import Conversation, Message, PromptDebug, Memory, MessageNote
from .models.user_auth import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login']


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['created_at', 'role', 'is_bot', 'content_preview', 'metadata_preview']
    fields = ['created_at', 'role', 'is_bot', 'content_preview', 'metadata_preview']

    def content_preview(self, obj):
        if obj.content:
            return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
        return "-"
    content_preview.short_description = "Content Preview"

    def metadata_preview(self, obj):
        if obj.metadata:
            return str(obj.metadata)
        return "-"
    metadata_preview.short_description = "Metadata"


class PromptDebugInline(admin.TabularInline):
    model = PromptDebug
    extra = 0
    readonly_fields = ['created_at', 'model_used', 'mode_used', 'prompt_length', 'response_time_ms', 'debug_link']
    fields = ['created_at', 'model_used', 'mode_used', 'prompt_length', 'response_time_ms', 'debug_link']

    def debug_link(self, obj):
        if obj.id:
            url = reverse('admin:api_promptdebug_change', args=[obj.id])
            return format_html('<a href="{}">View Debug Details</a>', url)
        return "-"
    debug_link.short_description = "Debug Details"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'message_count', 'is_archived', 'created_at', 'updated_at']
    list_filter = ['is_archived', 'created_at', 'updated_at']
    search_fields = ['title', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'message_count', 'context_display']
    inlines = [MessageInline, PromptDebugInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'is_archived')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'message_count')
        }),
        ('Context Data', {
            'fields': ('context_display',),
            'classes': ('collapse',)
        }),
    )

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "Messages"

    def context_display(self, obj):
        if obj.context:
            import json
            formatted_context = json.dumps(obj.context, indent=2)
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">{}</pre>', formatted_context)
        return "No context data"
    context_display.short_description = "Context JSON"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_link', 'sender', 'role', 'is_bot', 'content_preview', 'has_full_prompt', 'created_at']
    list_filter = ['is_bot', 'role', 'created_at', 'conversation__user']
    search_fields = ['content', 'raw_user_input', 'sender__username', 'conversation__title']
    readonly_fields = ['created_at', 'content_display', 'raw_user_input_display', 'full_prompt_display', 'metadata_display', 'debug_entries']

    fieldsets = (
        ('Message Information', {
            'fields': ('conversation', 'sender', 'role', 'is_bot', 'created_at')
        }),
        ('Content', {
            'fields': ('content_display',)
        }),
        ('Debug Information', {
            'fields': ('raw_user_input_display', 'full_prompt_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('Related Debug Entries', {
            'fields': ('debug_entries',),
            'classes': ('collapse',)
        }),
    )

    def conversation_link(self, obj):
        url = reverse('admin:api_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">{}</a>', url, obj.conversation.title or f"Conversation {obj.conversation.id}")
    conversation_link.short_description = "Conversation"

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"

    def has_full_prompt(self, obj):
        if obj.full_prompt:
            return f"✅ ({len(obj.full_prompt)} chars)"
        return "❌"
    has_full_prompt.short_description = "Full Prompt"

    def content_display(self, obj):
        return format_html('<div style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; white-space: pre-wrap;">{}</div>', obj.content)
    content_display.short_description = "Full Content"

    def raw_user_input_display(self, obj):
        if obj.raw_user_input:
            return format_html('<div style="background-color: #e3f2fd; padding: 10px; border-radius: 4px; white-space: pre-wrap;">{}</div>', obj.raw_user_input)
        return "No raw user input (this is a bot message)"
    raw_user_input_display.short_description = "Original User Input"

    def full_prompt_display(self, obj):
        if obj.full_prompt:
            return format_html('<div style="background-color: #fff3e0; padding: 10px; border-radius: 4px; white-space: pre-wrap; max-height: 600px; overflow-y: auto; font-family: monospace; font-size: 12px;"><strong>Complete Prompt Sent to LLM ({} characters):</strong><br><br>{}</div>', len(obj.full_prompt), obj.full_prompt)
        return "No full prompt (this is a bot response message)"
    full_prompt_display.short_description = "Complete LLM Prompt"

    def metadata_display(self, obj):
        if obj.metadata:
            import json
            formatted_metadata = json.dumps(obj.metadata, indent=2)
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">{}</pre>', formatted_metadata)
        return "No metadata"
    metadata_display.short_description = "Metadata JSON"

    def debug_entries(self, obj):
        debug_entries = PromptDebug.objects.filter(user_message=obj)
        if debug_entries.exists():
            links = []
            for entry in debug_entries:
                url = reverse('admin:api_promptdebug_change', args=[entry.id])
                links.append(f'<a href="{url}">Debug Entry {entry.id}</a>')
            return format_html('<br>'.join(links))
        return "No debug entries"
    debug_entries.short_description = "Debug Entries"


@admin.register(PromptDebug)
class PromptDebugAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_link', 'user_message_preview', 'model_used', 'mode_used',
                   'prompt_length', 'memories_used_count', 'response_time_ms', 'created_at']
    list_filter = ['model_used', 'mode_used', 'created_at', 'conversation__user']
    search_fields = ['user_message__content', 'conversation__title', 'conversation__user__username']
    readonly_fields = ['created_at', 'full_prompt_display', 'system_prompt_display',
                      'memory_context_display', 'conversation_history_display', 'api_error_display']

    fieldsets = (
        ('Debug Entry Information', {
            'fields': ('user_message', 'bot_response', 'conversation', 'created_at')
        }),
        ('LLM Configuration', {
            'fields': ('model_used', 'mode_used', 'temperature')
        }),
        ('Statistics', {
            'fields': ('prompt_length', 'prompt_tokens', 'response_tokens', 'total_tokens',
                      'response_time_ms', 'memories_used_count', 'relevant_memories_count',
                      'conversation_memories_count', 'history_messages_count')
        }),
        ('Full Prompt', {
            'fields': ('full_prompt_display',),
            'classes': ('collapse',)
        }),
        ('System Prompt', {
            'fields': ('system_prompt_display',),
            'classes': ('collapse',)
        }),
        ('Memory Context', {
            'fields': ('memory_context_display',),
            'classes': ('collapse',)
        }),
        ('Conversation History', {
            'fields': ('conversation_history_display',),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('api_error_display',),
            'classes': ('collapse',)
        }),
    )

    def conversation_link(self, obj):
        url = reverse('admin:api_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">{}</a>', url, obj.conversation.title or f"Conversation {obj.conversation.id}")
    conversation_link.short_description = "Conversation"

    def user_message_preview(self, obj):
        return obj.user_message.content[:50] + "..." if len(obj.user_message.content) > 50 else obj.user_message.content
    user_message_preview.short_description = "User Message"

    def full_prompt_display(self, obj):
        return format_html('<div style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; white-space: pre-wrap; max-height: 500px; overflow-y: auto;">{}</div>', obj.full_prompt)
    full_prompt_display.short_description = "Complete Prompt Sent to LLM"

    def system_prompt_display(self, obj):
        if obj.system_prompt:
            return format_html('<div style="background-color: #e3f2fd; padding: 10px; border-radius: 4px; white-space: pre-wrap;">{}</div>', obj.system_prompt)
        return "No system prompt"
    system_prompt_display.short_description = "System Prompt"

    def memory_context_display(self, obj):
        if obj.memory_context:
            return format_html('<div style="background-color: #f3e5f5; padding: 10px; border-radius: 4px; white-space: pre-wrap;">{}</div>', obj.memory_context)
        return "No memory context"
    memory_context_display.short_description = "Memory Context"

    def conversation_history_display(self, obj):
        if obj.conversation_history:
            return format_html('<div style="background-color: #e8f5e8; padding: 10px; border-radius: 4px; white-space: pre-wrap; max-height: 400px; overflow-y: auto;">{}</div>', obj.conversation_history)
        return "No conversation history"
    conversation_history_display.short_description = "Conversation History"

    def api_error_display(self, obj):
        if obj.api_error:
            return format_html('<div style="background-color: #ffebee; padding: 10px; border-radius: 4px; white-space: pre-wrap; color: #c62828;">{}</div>', obj.api_error)
        return "No errors"
    api_error_display.short_description = "API Error"


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'memory_type', 'importance_score', 'is_auto_extracted',
                   'access_count', 'created_at']
    list_filter = ['memory_type', 'is_auto_extracted', 'importance_score', 'created_at', 'user']
    search_fields = ['title', 'content', 'user__username', 'tags']
    readonly_fields = ['created_at', 'updated_at', 'last_accessed', 'content_display',
                      'embedding_info', 'metadata_display']

    fieldsets = (
        ('Memory Information', {
            'fields': ('user', 'title', 'memory_type', 'importance_score', 'is_auto_extracted')
        }),
        ('Content', {
            'fields': ('content_display',)
        }),
        ('Source Information', {
            'fields': ('source_message', 'source_conversation', 'extraction_confidence')
        }),
        ('Access Tracking', {
            'fields': ('access_count', 'last_accessed', 'created_at', 'updated_at')
        }),
        ('Tags and Metadata', {
            'fields': ('tags', 'metadata_display'),
            'classes': ('collapse',)
        }),
        ('Embedding Information', {
            'fields': ('embedding_info',),
            'classes': ('collapse',)
        }),
    )

    def content_display(self, obj):
        return format_html('<div style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; white-space: pre-wrap;">{}</div>', obj.content)
    content_display.short_description = "Memory Content"

    def embedding_info(self, obj):
        if obj.embedding:
            return f"Embedding present ({len(obj.embedding)} dimensions)"
        return "No embedding"
    embedding_info.short_description = "Embedding Status"

    def metadata_display(self, obj):
        if obj.metadata:
            import json
            formatted_metadata = json.dumps(obj.metadata, indent=2)
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">{}</pre>', formatted_metadata)
        return "No metadata"
    metadata_display.short_description = "Metadata JSON"


@admin.register(MessageNote)
class MessageNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'message_preview', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['note', 'message__content', 'created_by__username']
    readonly_fields = ['created_at']

    def message_preview(self, obj):
        return obj.message.content[:50] + "..." if len(obj.message.content) > 50 else obj.message.content
    message_preview.short_description = "Message"


# Custom admin site configuration
admin.site.site_header = "LifeLine Admin"
admin.site.site_title = "LifeLine Admin Portal"
admin.site.index_title = "Welcome to LifeLine Administration"
