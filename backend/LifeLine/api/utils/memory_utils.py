import logging
from typing import List, Dict, Optional
from django.utils import timezone
from ..models.chat import Memory, Message, Conversation
from ..utils.llm import call_llm_embedding, call_llm_memory_extraction, LLMError
import numpy as np

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
        logger.info(f"Extracting memory from message {message.id} for user {user.username}")

        # Extract memory using LLM
        memory_data = call_llm_memory_extraction(message.content)

        if not memory_data.get('has_memory', False):
            logger.info(f"No memory found in message {message.id}")
            return None

        # Generate embedding for the memory content
        embedding = call_llm_embedding(memory_data['content'])

        # Create memory object
        memory = Memory.objects.create(
            user=user,
            content=memory_data['content'],
            title=memory_data.get('title', ''),
            memory_type=memory_data.get('memory_type', 'personal'),
            tags=memory_data.get('tags', []),
            importance_score=memory_data.get('importance_score', 0.5),
            embedding=embedding,
            source_message=message,
            source_conversation=message.conversation,
            is_auto_extracted=True,
            extraction_confidence=memory_data.get('confidence', 0.0),
            metadata={
                'extraction_model': 'gpt-4o-mini',
                'extracted_at': str(timezone.now())
            }
        )

        logger.info(f"Successfully extracted and stored memory {memory.id} from message {message.id}")
        return memory

    except Exception as e:
        logger.error(f"Failed to extract memory from message {message.id}: {str(e)}")
        return None

def get_relevant_memories(user, query: str, limit: int = 5) -> List[Memory]:
    """
    Get memories relevant to a query using semantic similarity.

    Args:
        user: The user whose memories to search
        query: The query to search for
        limit: Maximum number of memories to return

    Returns:
        List of relevant Memory objects
    """
    try:
        # Generate embedding for the query
        query_embedding = call_llm_embedding(query)

        # Get all user memories with embeddings
        memories = Memory.objects.filter(
            user=user,
            embedding__isnull=False
        ).order_by('-importance_score', '-updated_at')

        # Calculate similarities and sort
        memory_scores = []
        for memory in memories:
            if memory.embedding:
                similarity = cosine_similarity(query_embedding, memory.embedding)
                memory_scores.append((memory, similarity))

        # Sort by similarity and return top results
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        relevant_memories = [memory for memory, score in memory_scores[:limit]]

        # Update access count and last accessed time
        for memory in relevant_memories:
            memory.access_count += 1
            memory.last_accessed = timezone.now()
            memory.save(update_fields=['access_count', 'last_accessed'])

        logger.info(f"Found {len(relevant_memories)} relevant memories for user {user.username}")
        return relevant_memories

    except Exception as e:
        logger.error(f"Failed to get relevant memories for user {user.username}: {str(e)}")
        return []

def generate_memory_context(memories: List[Memory]) -> str:
    """
    Generate a context string from a list of memories for use in conversations.

    Args:
        memories: List of Memory objects

    Returns:
        Formatted context string
    """
    if not memories:
        return ""

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
        embedding = call_llm_embedding(memory.content)
        memory.embedding = embedding
        memory.save(update_fields=['embedding'])
        logger.info(f"Updated embedding for memory {memory.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update embedding for memory {memory.id}: {str(e)}")
        return False
