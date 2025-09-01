"""
Email processing utilities for embedding and search functionality
"""
import logging
from typing import List, Optional, Dict, Any

from django.conf import settings
from django.contrib.auth import get_user_model

from .llm import call_llm_embedding, LLMError
from ..models.email import Email

User = get_user_model()
logger = logging.getLogger(__name__)


def generate_email_embedding(email: Email, force_regenerate: bool = False) -> bool:
    """
    Generate embedding for an email and store it in the database.
    
    Args:
        email: Email instance to generate embedding for
        force_regenerate: Whether to regenerate embedding even if it exists
        
    Returns:
        bool: True if embedding was generated successfully, False otherwise
    """
    # Skip if already has embedding and not forcing regeneration
    if email.embedding and not force_regenerate:
        logger.info(f"Email {email.message_id} already has embedding, skipping")
        return True
    
    try:
        # Prepare content for embedding
        content = email.prepare_content_for_embedding()
        
        if not content.strip():
            logger.warning(f"Email {email.message_id} has no content for embedding")
            email.processing_error = "No content available for embedding"
            email.save()
            return False
        
        # Generate embedding
        logger.info(f"Generating embedding for email {email.message_id}")
        embedding = call_llm_embedding(content)
        
        # Store embedding and mark as processed
        email.embedding = embedding
        email.embedding_model = "text-embedding-3-small"  # Default model from llm.py
        email.content_for_search = content
        email.is_processed = True
        email.processing_error = None
        email.save()
        
        logger.info(f"Successfully generated embedding for email {email.message_id}")
        return True
        
    except LLMError as e:
        logger.error(f"LLM error generating embedding for email {email.message_id}: {e}")
        email.processing_error = f"LLM error: {str(e)}"
        email.save()
        return False
    except Exception as e:
        logger.error(f"Unexpected error generating embedding for email {email.message_id}: {e}")
        email.processing_error = f"Unexpected error: {str(e)}"
        email.save()
        return False


def batch_generate_embeddings(user: User, batch_size: int = 10) -> Dict[str, int]:
    """
    Generate embeddings for all unprocessed emails for a user in batches.
    
    Args:
        user: User to process emails for
        batch_size: Number of emails to process in each batch
        
    Returns:
        Dict with statistics: {"processed": int, "failed": int, "skipped": int}
    """
    stats = {"processed": 0, "failed": 0, "skipped": 0}
    
    # Get unprocessed emails
    unprocessed_emails = Email.objects.filter(
        user=user,
        is_processed=False
    ).order_by('received_date')
    
    total_count = unprocessed_emails.count()
    logger.info(f"Found {total_count} unprocessed emails for user {user.username}")
    
    if total_count == 0:
        return stats
    
    # Process in batches
    for i in range(0, total_count, batch_size):
        batch = unprocessed_emails[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}: emails {i+1}-{min(i+batch_size, total_count)} of {total_count}")
        
        for email in batch:
            try:
                if generate_email_embedding(email):
                    stats["processed"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to process email {email.message_id}: {e}")
                stats["failed"] += 1
    
    logger.info(f"Embedding generation complete for user {user.username}: {stats}")
    return stats


def search_emails_by_similarity(
    user: User,
    query: str,
    limit: int = 10,
    min_similarity: float = 0.3
) -> List[Email]:
    """
    Search for emails similar to a query using vector similarity.
    
    Args:
        user: User to search emails for
        query: Search query
        limit: Maximum number of results to return
        min_similarity: Minimum similarity threshold
        
    Returns:
        List of Email instances ordered by similarity
    """
    try:
        # Generate embedding for the query
        query_embedding = call_llm_embedding(query)
        
        # Get emails with embeddings
        emails_with_embeddings = Email.objects.filter(
            user=user,
            is_processed=True,
            embedding__isnull=False
        )
        
        if not emails_with_embeddings.exists():
            logger.info(f"No processed emails found for user {user.username}")
            return []
        
        # Calculate similarities (this is a simplified version)
        # In a production system, you'd want to use a vector database like pgvector
        similar_emails = []
        
        for email in emails_with_embeddings:
            # Calculate cosine similarity
            similarity = calculate_cosine_similarity(query_embedding, email.embedding)
            
            if similarity >= min_similarity:
                similar_emails.append((email, similarity))
        
        # Sort by similarity and return top results
        similar_emails.sort(key=lambda x: x[1], reverse=True)
        return [email for email, _ in similar_emails[:limit]]
        
    except LLMError as e:
        logger.error(f"LLM error in email search: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in email search: {e}")
        return []


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        float: Cosine similarity score (0-1)
    """
    import math
    
    if len(vec1) != len(vec2):
        return 0.0
    
    # Calculate dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    if magnitude1 == 0.0 or magnitude2 == 0.0:
        return 0.0
    
    # Calculate cosine similarity
    similarity = dot_product / (magnitude1 * magnitude2)
    
    # Ensure result is between 0 and 1
    return max(0.0, min(1.0, similarity))


def get_email_stats(user: User) -> Dict[str, Any]:
    """
    Get email statistics for a user.
    
    Args:
        user: User to get stats for
        
    Returns:
        Dict with email statistics
    """
    emails = Email.objects.filter(user=user)
    
    stats = {
        "total_emails": emails.count(),
        "processed_emails": emails.filter(is_processed=True).count(),
        "unprocessed_emails": emails.filter(is_processed=False).count(),
        "emails_with_errors": emails.filter(processing_error__isnull=False).count(),
        "read_emails": emails.filter(is_read=True).count(),
        "unread_emails": emails.filter(is_read=False).count(),
        "starred_emails": emails.filter(is_starred=True).count(),
        "emails_with_attachments": emails.filter(has_attachments=True).count(),
    }
    
    # Add date range if emails exist
    if stats["total_emails"] > 0:
        oldest_email = emails.order_by('received_date').first()
        newest_email = emails.order_by('-received_date').first()
        stats["oldest_email_date"] = oldest_email.received_date if oldest_email else None
        stats["newest_email_date"] = newest_email.received_date if newest_email else None
    
    return stats