import logging
from datetime import datetime
from typing import List, Dict, Optional

import numpy as np
from django.db import models
from django.utils import timezone

from ..models.chat import Memory, Message, Conversation
from ..utils.constants import (
    DEFAULT_IMPORTANCE_SCORE,
    DEFAULT_CONFIDENCE_SCORE,
    DEFAULT_EMBEDDING_DIMENSIONS,
    MEMORY_SIMILARITY_WEIGHT,
    MEMORY_IMPORTANCE_WEIGHT,
    MEMORY_RECENCY_WEIGHT,
    MEMORY_RECENCY_DAYS_DIVISOR,
    MEMORY_CONTEXT_SIMILARITY_WEIGHT,
    MEMORY_IMPORTANCE_CONTEXT_WEIGHT,
)
from ..utils.llm import call_llm_embedding, call_llm_memory_extraction, call_llm_conversation_memory_extraction

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def extract_and_store_conversation_memory(user_message: Message, ai_message: Message, user) -> Optional[Memory]:
    """
    Extract memory from a conversation pair (user question + AI response) and store it if found.
    Focuses on actionable items, deadlines, and important context with clear dates.

    Args:
        user_message: The user's message
        ai_message: The AI's response message
        user: The user who sent the message

    Returns:
        Memory object if memory was extracted, None otherwise
    """
    try:
        logger.info(
            f"[CONVERSATION MEMORY] Starting extraction for conversation pair: user msg {user_message.id} + AI msg {ai_message.id}"
        )

        # Extract memory using conversation pair LLM function
        current_date = datetime.now().strftime("%Y-%m-%d")

        memory_data = call_llm_conversation_memory_extraction(
            user_message=user_message.content, ai_response=ai_message.content, current_date=current_date
        )

        if not memory_data.get("has_memory", False):
            logger.info(f"[CONVERSATION MEMORY] No extractable memory found in conversation pair")
            return None

        # Generate embedding for the memory content
        logger.debug(f"[CONVERSATION MEMORY] Generating embedding for memory content")
        embedding = call_llm_embedding(memory_data["content"])

        # Enhanced metadata for conversation-based memories
        metadata = {
            "extraction_model": "gpt-4o-mini",
            "extracted_at": str(timezone.now()),
            "extraction_date": current_date,
            "source_user_message_id": user_message.id,
            "source_ai_message_id": ai_message.id,
            "user_message_length": len(user_message.content),
            "ai_message_length": len(ai_message.content),
            "embedding_dimensions": len(embedding) if embedding else DEFAULT_EMBEDDING_DIMENSIONS,
            "has_deadline": memory_data.get("has_deadline", False),
            "deadline_date": memory_data.get("deadline_date"),
            "is_actionable": memory_data.get("is_actionable", False),
        }

        # Add deadline to tags if present
        tags = memory_data.get("tags", [])
        if memory_data.get("deadline_date"):
            tags.append(f"deadline:{memory_data['deadline_date']}")
        if memory_data.get("is_actionable"):
            tags.append("actionable")

        # Create memory object
        memory = Memory.objects.create(
            user=user,
            content=memory_data["content"],
            title=memory_data.get("title", ""),
            memory_type=memory_data.get("memory_type", "personal"),
            tags=tags,
            importance_score=memory_data.get("importance_score", DEFAULT_IMPORTANCE_SCORE),
            embedding=embedding,
            source_message=ai_message,  # Use AI message as source since it contains the actionable info
            source_conversation=user_message.conversation,
            is_auto_extracted=True,
            extraction_confidence=memory_data.get("confidence", DEFAULT_CONFIDENCE_SCORE),
            metadata=metadata,
        )

        logger.info(
            f"[CONVERSATION MEMORY] Successfully extracted and stored memory {memory.id} "
            f"(type: {memory.memory_type}, importance: {memory.importance_score}, "
            f"actionable: {memory_data.get('is_actionable')}, deadline: {memory_data.get('deadline_date')})"
        )
        return memory

    except Exception as e:
        logger.error(f"[CONVERSATION MEMORY] Failed to extract memory from conversation pair: {str(e)}")
        return None


def extract_and_store_memory(message: Message, user) -> Optional[Memory]:
    """
    Extract memory from a single message and store it if found.
    NOTE: Consider using extract_and_store_conversation_memory for better context.

    Args:
        message: The message to analyze
        user: The user who sent the message

    Returns:
        Memory object if memory was extracted, None otherwise
    """
    try:
        logger.info(
            f"[MEMORY EXTRACTION] Starting extraction for single message {message.id} from user {user.username}"
        )

        # Extract memory using LLM
        memory_data = call_llm_memory_extraction(message.content)

        if not memory_data.get("has_memory", False):
            logger.info(f"[MEMORY EXTRACTION] No extractable memory found in message {message.id}")
            return None

        # Generate embedding for the memory content
        logger.debug(f"[MEMORY EXTRACTION] Generating embedding for memory content")
        embedding = call_llm_embedding(memory_data["content"])

        # Create memory object
        memory = Memory.objects.create(
            user=user,
            content=memory_data["content"],
            title=memory_data.get("title", ""),
            memory_type=memory_data.get("memory_type", "personal"),
            tags=memory_data.get("tags", []),
            importance_score=memory_data.get("importance_score", DEFAULT_IMPORTANCE_SCORE),
            embedding=embedding,
            source_message=message,
            source_conversation=message.conversation,
            is_auto_extracted=True,
            extraction_confidence=memory_data.get("confidence", DEFAULT_CONFIDENCE_SCORE),
            metadata={
                "extraction_model": "gpt-4o-mini",
                "extracted_at": str(timezone.now()),
                "source_message_length": len(message.content),
                "embedding_dimensions": len(embedding) if embedding else DEFAULT_EMBEDDING_DIMENSIONS,
            },
        )

        logger.info(
            f"[MEMORY EXTRACTION] Successfully extracted and stored memory {memory.id} "
            f"(type: {memory.memory_type}, importance: {memory.importance_score}, "
            f"confidence: {memory.extraction_confidence})"
        )
        return memory

    except Exception as e:
        logger.error(f"[MEMORY EXTRACTION] Failed to extract memory from message {message.id}: {str(e)}")
        return None


def get_relevant_memories(user, query: str, limit: int = 5, min_similarity: float = 0.3) -> List[Memory]:
    """
    Enhanced RAG: Get memories relevant to a query using semantic similarity with improved scoring.

    Args:
        user: The user whose memories to search
        query: The query to search for
        limit: Maximum number of memories to return
        min_similarity: Minimum similarity threshold (0.0 to 1.0) - lowered to 0.3 for better recall

    Returns:
        List of relevant Memory objects sorted by relevance
    """
    try:
        logger.info(f"[RAG RETRIEVAL] Searching memories for user {user.username}, query length: {len(query)}")

        # Generate embedding for the query
        query_embedding = call_llm_embedding(query)
        logger.debug(f"[RAG RETRIEVAL] Generated query embedding with {len(query_embedding)} dimensions")

        # Get all user memories with embeddings
        memories = Memory.objects.filter(user=user, embedding__isnull=False).order_by(
            "-importance_score", "-updated_at"
        )

        if not memories.exists():
            logger.info(f"[RAG RETRIEVAL] No memories with embeddings found for user {user.username}")
            return []

        # Calculate similarities and score memories
        relevant_memories = []
        for memory in memories:
            try:
                # Calculate cosine similarity
                similarity = cosine_similarity(query_embedding, memory.embedding)

                # Apply similarity threshold
                if similarity < min_similarity:
                    continue

                # Calculate composite score: similarity + importance + recency
                recency_score = min(1.0, (timezone.now() - memory.updated_at).days / MEMORY_RECENCY_DAYS_DIVISOR)
                composite_score = (
                    similarity * MEMORY_SIMILARITY_WEIGHT  # semantic similarity
                    + memory.importance_score * MEMORY_IMPORTANCE_WEIGHT  # importance
                    + (1.0 - recency_score) * MEMORY_RECENCY_WEIGHT  # recency (newer is better)
                )

                relevant_memories.append(
                    {"memory": memory, "similarity": similarity, "composite_score": composite_score}
                )

                logger.debug(
                    f"[RAG RETRIEVAL] Memory {memory.id}: similarity={similarity:.3f}, "
                    f"importance={memory.importance_score:.3f}, composite={composite_score:.3f}"
                )

            except Exception as e:
                logger.error(f"[RAG RETRIEVAL] Error processing memory {memory.id}: {str(e)}")
                continue

        # Sort by composite score and limit results
        relevant_memories.sort(key=lambda x: x["composite_score"], reverse=True)
        top_memories = relevant_memories[:limit]

        # Track memory access - increment access count and update last_accessed_at
        memory_objects = []
        for item in top_memories:
            memory = item["memory"]
            memory.access_count += 1
            memory.last_accessed_at = timezone.now()
            memory.save(update_fields=["access_count", "last_accessed_at"])
            memory_objects.append(memory)

        logger.info(
            f"[RAG RETRIEVAL] Found {len(memory_objects)} relevant memories for user {user.username} "
            f"(avg similarity: {np.mean([item['similarity'] for item in top_memories]):.3f})"
        )

        return memory_objects

    except Exception as e:
        logger.error(f"[RAG RETRIEVAL] Error in get_relevant_memories: {str(e)}")
        return []


def get_memories_by_type(user, memory_type: str, limit: int = 10) -> List[Memory]:
    """
    Get memories of a specific type for the user.

    Args:
        user: The user whose memories to retrieve
        memory_type: Type of memories to retrieve (goal, preference, etc.)
        limit: Maximum number of memories to return

    Returns:
        List of Memory objects of the specified type
    """
    try:
        memories = Memory.objects.filter(user=user, memory_type=memory_type).order_by(
            "-importance_score", "-updated_at"
        )[:limit]

        logger.info(
            f"[MEMORY RETRIEVAL] Retrieved {len(memories)} memories of type '{memory_type}' "
            f"for user {user.username}"
        )
        return list(memories)

    except Exception as e:
        logger.error(
            f"[MEMORY RETRIEVAL] Failed to get memories of type '{memory_type}' " f"for user {user.username}: {str(e)}"
        )
        return []


def get_conversation_memories(user, conversation: Conversation, limit: int = 5) -> List[Memory]:
    """
    Get memories specifically related to a conversation.

    Args:
        user: The user whose memories to retrieve
        conversation: The conversation to get memories for
        limit: Maximum number of memories to return

    Returns:
        List of Memory objects related to the conversation
    """
    try:
        # Get memories from this conversation
        conversation_memories = Memory.objects.filter(user=user, source_conversation=conversation).order_by(
            "-importance_score", "-created_at"
        )[:limit]

        logger.info(
            f"[CONVERSATION MEMORIES] Retrieved {len(conversation_memories)} memories "
            f"from conversation {conversation.id} for user {user.username}"
        )
        return list(conversation_memories)

    except Exception as e:
        logger.error(f"[CONVERSATION MEMORIES] Failed to get conversation memories: {str(e)}")
        return []


def generate_memory_context(memories: List[Memory]) -> str:
    """
    Generate a context string from a list of memories for use in conversations.
    Enhanced with better formatting and organization.

    Args:
        memories: List of Memory objects

    Returns:
        Formatted context string
    """
    if not memories:
        logger.debug("[MEMORY CONTEXT] No memories provided")
        return ""

    try:
        logger.info(f"[MEMORY CONTEXT] Generating context from {len(memories)} memories")

        # Convert Memory objects to dictionaries for the prompt formatter
        memory_dicts = []
        for memory in memories:
            memory_dict = {
                "content": memory.content,
                "title": memory.title,
                "memory_type": memory.memory_type,
                "importance_score": memory.importance_score,
                "created_at": memory.created_at.isoformat() if memory.created_at else None,
                "tags": memory.tags or [],
            }
            memory_dicts.append(memory_dict)

        # Use the enhanced prompt formatting
        from .prompts import format_memory_context

        context = format_memory_context(memory_dicts, "personal_context")

        logger.info(f"[MEMORY CONTEXT] Generated context with {len(context)} characters")
        return context

    except Exception as e:
        logger.error(f"[MEMORY CONTEXT] Error generating memory context: {str(e)}")
        # Fallback to simple formatting
        context_parts = ["Here's what I remember about you:"]
        for memory in memories:
            memory_text = f"- {memory.content}"
            if memory.title:
                memory_text = f"- {memory.title}: {memory.content}"
            context_parts.append(memory_text)
        return "\n".join(context_parts)


def update_memory_embedding(memory: Memory) -> bool:
    """
    Update the embedding for a memory.

    Args:
        memory: The memory to update

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"[MEMORY UPDATE] Updating embedding for memory {memory.id}")
        embedding = call_llm_embedding(memory.content)
        memory.embedding = embedding
        memory.save(update_fields=["embedding", "updated_at"])
        logger.info(f"[MEMORY UPDATE] Successfully updated embedding for memory {memory.id}")
        return True
    except Exception as e:
        logger.error(f"[MEMORY UPDATE] Failed to update embedding for memory {memory.id}: {str(e)}")
        return False


def rerank_memories_by_context(memories: List[Memory], conversation_context: str) -> List[Memory]:
    """
    Re-rank memories based on additional conversation context.

    Args:
        memories: List of memories to re-rank
        conversation_context: Recent conversation context

    Returns:
        Re-ranked list of memories
    """
    try:
        if not memories or not conversation_context:
            return memories

        logger.info(f"[MEMORY RERANK] Re-ranking {len(memories)} memories with conversation context")

        # Generate embedding for conversation context
        context_embedding = call_llm_embedding(conversation_context)

        # Calculate context relevance for each memory
        memory_scores = []
        for memory in memories:
            if memory.embedding:
                context_similarity = cosine_similarity(context_embedding, memory.embedding)

                # Combine with existing importance
                combined_score = (context_similarity * MEMORY_CONTEXT_SIMILARITY_WEIGHT) + (
                    memory.importance_score * MEMORY_IMPORTANCE_CONTEXT_WEIGHT
                )
                memory_scores.append((memory, combined_score))

        # Sort by combined score
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        reranked_memories = [memory for memory, score in memory_scores]

        logger.info(f"[MEMORY RERANK] Completed re-ranking of {len(reranked_memories)} memories")
        return reranked_memories

    except Exception as e:
        logger.error(f"[MEMORY RERANK] Error re-ranking memories: {str(e)}")
        return memories  # Return original order on error


def get_memory_statistics(user) -> Dict:
    """
    Get statistics about a user's memories.

    Args:
        user: The user to get statistics for

    Returns:
        Dictionary with memory statistics
    """
    try:
        memories = Memory.objects.filter(user=user)

        stats = {
            "total_memories": memories.count(),
            "auto_extracted": memories.filter(is_auto_extracted=True).count(),
            "manual_created": memories.filter(is_auto_extracted=False).count(),
            "by_type": {},
            "avg_importance": 0,
            "total_accesses": 0,
        }

        # Count by type
        for memory_type in ["personal", "goal", "preference", "relationship", "experience"]:
            stats["by_type"][memory_type] = memories.filter(memory_type=memory_type).count()

        # Calculate averages
        if stats["total_memories"] > 0:
            stats["avg_importance"] = (
                memories.aggregate(avg_importance=models.Avg("importance_score"))["avg_importance"] or 0
            )

            stats["total_accesses"] = (
                memories.aggregate(total_accesses=models.Sum("access_count"))["total_accesses"] or 0
            )

        logger.info(
            f"[MEMORY STATS] Generated statistics for user {user.username}: "
            f"{stats['total_memories']} total memories"
        )
        return stats

    except Exception as e:
        logger.error(f"[MEMORY STATS] Error generating memory statistics: {str(e)}")
        return {"error": str(e)}
