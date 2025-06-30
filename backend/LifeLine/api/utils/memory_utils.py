import logging
import json
from typing import List, Dict, Any, Optional
from django.db.models import Q
from ..models.chat import Memory, Conversation, Message

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages user memories for RAG functionality."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def build_conversation_context(self, current_message: str, conversation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Build context for RAG-enhanced conversation.

        Args:
            current_message: The user's current message
            conversation_id: Optional conversation ID for context

        Returns:
            Dictionary containing formatted context
        """
        try:
            # Get relevant memories
            relevant_memories = self._get_relevant_memories(current_message)

            # Get conversation history if conversation_id provided
            conversation_history = []
            if conversation_id:
                conversation_history = self._get_conversation_history(conversation_id)

            # Format memories for context
            formatted_memories = self._format_memories(relevant_memories)

            # Format conversation history
            formatted_history = self._format_conversation_history(conversation_history)

            return {
                "current_message": current_message,
                "relevant_memories": formatted_memories,
                "conversation_history": formatted_history,
                "memory_count": len(relevant_memories),
                "message_count": len(conversation_history),
                "total_context_tokens": len(formatted_memories) + len(formatted_history)  # Approximation
            }

        except Exception as e:
            logger.error(f"Error building conversation context: {e}")
            return {
                "current_message": current_message,
                "relevant_memories": "No memories available",
                "conversation_history": "No conversation history available",
                "memory_count": 0,
                "message_count": 0,
                "total_context_tokens": 0
            }

    def _get_relevant_memories(self, current_message: str, limit: int = 10) -> List[Memory]:
        """Get memories relevant to the current message."""
        try:
            # Simple relevance search - in production, you'd use vector similarity
            memories = Memory.objects.filter(
                user_id=self.user_id,
                is_active=True
            ).order_by('-importance_score', '-access_count', '-updated_at')[:limit]

            return list(memories)

        except Exception as e:
            logger.error(f"Error getting relevant memories: {e}")
            return []

    def _get_conversation_history(self, conversation_id: int, limit: int = 20) -> List[Message]:
        """Get recent conversation history."""
        try:
            messages = Message.objects.filter(
                conversation_id=conversation_id
            ).order_by('-created_at')[:limit]

            return list(reversed(messages))  # Return in chronological order

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    def _format_memories(self, memories: List[Memory]) -> str:
        """Format memories for inclusion in prompts."""
        if not memories:
            return "No relevant memories found."

        formatted = []
        for memory in memories:
            formatted.append(f"[{memory.memory_type.upper()}] {memory.content}")

        return "\n".join(formatted)

    def _format_conversation_history(self, messages: List[Message]) -> str:
        """Format conversation messages for inclusion in prompts."""
        if not messages:
            return "No conversation history available."

        formatted = []
        for message in messages[-10:]:  # Limit to last 10 messages
            role = "User" if message.role == "user" else "Assistant"
            formatted.append(f"{role}: {message.content}")

        return "\n".join(formatted)

    def extract_memories_from_conversation(self, conversation_id: int) -> List[Dict]:
        """
        Extract memories from a conversation.

        Args:
            conversation_id: ID of the conversation to analyze

        Returns:
            List of extracted memory dictionaries
        """
        try:
            # Get conversation messages
            messages = Message.objects.filter(
                conversation_id=conversation_id
            ).order_by('created_at')

            if not messages:
                return []

            # For now, create simple memories from user messages
            # In production, you'd use LLM to extract structured memories
            extracted_memories = []

            for message in messages:
                if message.role == "user" and len(message.content) > 50:
                    # Simple heuristic: longer messages might contain important information
                    memory_data = {
                        "content": message.content[:200] + "..." if len(message.content) > 200 else message.content,
                        "category": "conversation",
                        "memory_type": "general",
                        "importance": "medium",
                        "context": f"From conversation {conversation_id}",
                        "source_conversation_id": conversation_id,
                        "source_message_id": message.id
                    }
                    extracted_memories.append(memory_data)

            # Save extracted memories to database
            for memory_data in extracted_memories:
                memory = Memory.objects.create(
                    user_id=self.user_id,
                    content=memory_data["content"],
                    category=memory_data["category"],
                    memory_type=memory_data["memory_type"],
                    importance=memory_data["importance"],
                    context=memory_data["context"],
                    source_conversation_id=memory_data["source_conversation_id"],
                    source_message_id=memory_data["source_message_id"],
                    importance_score=0.5,  # Default score
                    extraction_confidence=0.7,  # Simple extraction confidence
                    is_auto_extracted=True
                )
                logger.info(f"Created memory {memory.id} from conversation {conversation_id}")

            return extracted_memories

        except Exception as e:
            logger.error(f"Error extracting memories from conversation {conversation_id}: {e}")
            return []


def get_memory_manager(user_id: int) -> MemoryManager:
    """Get a memory manager instance for the specified user."""
    return MemoryManager(user_id)
