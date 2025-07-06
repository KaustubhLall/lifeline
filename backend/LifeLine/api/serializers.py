from rest_framework import serializers

from .models.chat import Conversation, Message, Memory


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "is_archived", "context"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "content", "created_at", "is_bot", "metadata", "role"]


class MemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Memory
        fields = [
            "id",
            "content",
            "title",
            "memory_type",
            "tags",
            "metadata",
            "created_at",
            "updated_at",
            "edited_at",
            "last_accessed_at",
            "importance_score",
            "last_accessed",
            "access_count",
            "is_auto_extracted",
            "extraction_confidence",
            "source_message",
            "source_conversation",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_accessed", "access_count", "last_accessed_at"]


class MemoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Memory
        fields = ["content", "title", "memory_type", "tags", "importance_score"]
