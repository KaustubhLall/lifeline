import logging
from typing import List, Dict, Optional

import numpy as np
from django.db import models
from django.utils import timezone

from ..models.chat import Memory, Message, Conversation
from ..utils.llm import call_llm_embedding, call_llm_memory_extraction

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def extract_and_store_memory(message: Message, user) -> Optional[Memory]:
    """
    Extract memory from a message and store it if found.

    Args:
        message: The message to analyze
        user: The user who sent the message

    Returns:
        Memory object if memory was extracted, None otherwise
    """
    try:
        logger.info(f"[MEMORY EXTRACTION] Starting extraction for message {message.id} from user {user.username}")

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
            importance_score=memory_data.get("importance_score", 0.5),
            embedding=embedding,
            source_message=message,
            source_conversation=message.conversation,
            is_auto_extracted=True,
            extraction_confidence=memory_data.get("confidence", 0.0),
            metadata={
                "extraction_model": "gpt-4o-mini",
                "extracted_at": str(timezone.now()),
                "source_message_length": len(message.content),
                "embedding_dimensions": len(embedding) if embedding else 0,
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

        logger.debug(f"[RAG RETRIEVAL] Found {memories.count()} memories with embeddings")

        # If no memories with embeddings, fall back to recent important memories
        if memories.count() == 0:
            logger.info(f"[RAG RETRIEVAL] No embeddings found, falling back to recent important memories")
            fallback_memories = Memory.objects.filter(user=user).order_by("-importance_score", "-updated_at")[:limit]
            return list(fallback_memories)

        # Calculate similarities and apply enhanced scoring
        memory_scores = []
        for memory in memories:
            if memory.embedding:
                # Base similarity score
                similarity = cosine_similarity(query_embedding, memory.embedding)

                # Enhanced scoring factors
                days_old = (timezone.now() - memory.updated_at).days
                recency_boost = max(0.0, 1.0 - (days_old / 30.0)) * 0.1  # FIXED: Boost recent memories
                importance_boost = memory.importance_score * 0.2
                access_frequency_boost = min(0.1, memory.access_count / 10.0 * 0.05)

                # Combined relevance score
                relevance_score = (
                    similarity + importance_boost + access_frequency_boost + recency_boost
                )  # FIXED: Add recency boost

                # Only include memories above similarity threshold (lowered to 0.3)
                if similarity >= min_similarity:
                    memory_scores.append((memory, similarity, relevance_score))
                    logger.debug(
                        f"[RAG RETRIEVAL] Memory {memory.id}: similarity={similarity:.3f}, "
                        f"relevance={relevance_score:.3f}, days_old={days_old}"
                    )

        # If no memories meet similarity threshold, get top memories by importance
        if not memory_scores:
            logger.info(
                f"[RAG RETRIEVAL] No memories meet similarity threshold {min_similarity}, falling back to top memories"
            )
            fallback_memories = memories.order_by("-importance_score", "-updated_at")[:limit]
            return list(fallback_memories)

        # Sort by relevance score and return top results
        memory_scores.sort(key=lambda x: x[2], reverse=True)  # Sort by relevance_score
        relevant_memories = [memory for memory, sim, rel in memory_scores[:limit]]

        # Update access tracking for returned memories
        for memory in relevant_memories:
            memory.access_count += 1
            memory.last_accessed = timezone.now()
            memory.save(update_fields=["access_count", "last_accessed"])

        logger.info(
            f"[RAG RETRIEVAL] Retrieved {len(relevant_memories)} relevant memories "
            f"(threshold: {min_similarity}, max requested: {limit})"
        )

        # Log memory details for debugging
        for i, memory in enumerate(relevant_memories):
            similarity_score = next((sim for mem, sim, rel in memory_scores if mem.id == memory.id), 0.0)
            logger.debug(
                f"[RAG RETRIEVAL] Result {i+1}: Memory {memory.id} - {memory.title or 'No title'} "
                f"(type: {memory.memory_type}, importance: {memory.importance_score}, similarity: {similarity_score:.3f})"
            )

        return relevant_memories

    except Exception as e:
        logger.error(f"[RAG RETRIEVAL] Failed to get relevant memories for user {user.username}: {str(e)}")
        # Fallback to recent memories on error
        try:
            fallback_memories = Memory.objects.filter(user=user).order_by("-importance_score", "-updated_at")[:limit]
            logger.info(f"[RAG RETRIEVAL] Error fallback: returning {len(fallback_memories)} recent memories")
            return list(fallback_memories)
        except:
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
                combined_score = (context_similarity * 0.7) + (memory.importance_score * 0.3)
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
