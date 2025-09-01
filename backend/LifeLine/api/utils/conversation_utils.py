import logging
from typing import Optional

from django.db import transaction

from .llm import call_llm_text, LLMError
from .prompts import generate_conversation_title_prompt
from ..models.chat import Conversation
from .constants import AUTO_TITLE_MIN_MESSAGES, AUTO_TITLE_MAX_WORDS, AUTO_TITLE_MAX_LENGTH

logger = logging.getLogger(__name__)


def should_auto_title_conversation(conversation: Conversation) -> bool:
    """
    Check if a conversation should be auto-titled.

    Args:
        conversation: The conversation to check

    Returns:
        True if the conversation should be auto-titled, False otherwise
    """
    # Only auto-title if:
    # 1. The conversation doesn't already have a custom title (avoid overwriting user titles)
    # 2. The conversation has at least AUTO_TITLE_MIN_MESSAGES messages (enough content for meaningful title)
    # 3. The current title is still the default format

    message_count = conversation.messages.count()
    current_title = conversation.title or ""

    # Check if title is still in default format (e.g., "Chat 1", "Chat 2", "New Chat", etc.)
    is_default_title = (
        not current_title
        or current_title.startswith("Chat ")
        or current_title == f"Chat {conversation.id}"
        or current_title == "New Chat"
    )

    # Allow titling for any conversation with at least AUTO_TITLE_MIN_MESSAGES messages and default title
    should_title = message_count >= AUTO_TITLE_MIN_MESSAGES and is_default_title

    logger.info(
        f"Auto-title check for conversation {conversation.id}: "
        f"messages={message_count}, title='{current_title}', "
        f"is_default={is_default_title}, should_title={should_title}"
    )

    return should_title


def generate_auto_title(conversation: Conversation) -> Optional[str]:
    """
    Generate an automatic title for a conversation based on its first 3 messages.

    Args:
        conversation: The conversation to generate a title for

    Returns:
        Generated title string or None if generation fails
    """
    try:
        # Get the first 3 messages in chronological order (even if there are more)
        messages = conversation.messages.order_by("created_at")[:3]

        if messages.count() < AUTO_TITLE_MIN_MESSAGES:
            logger.warning(f"Not enough messages for auto-titling conversation {conversation.id}")
            return None

        # Prepare message data for title generation
        message_data = []
        for msg in messages:
            message_data.append({"content": msg.content, "is_bot": msg.is_bot, "role": msg.role})

        # Generate the title prompt
        title_prompt = generate_conversation_title_prompt(message_data)

        logger.info(f"Generating auto-title for conversation {conversation.id} with {len(message_data)} messages")

        # Call LLM to generate title using gpt-4.1-nano as specified
        llm_response = call_llm_text(
            prompt=title_prompt,
            model="gpt-4.1-nano",
            temperature=0.0,  # Use deterministic generation for consistent titles
        )

        generated_title = llm_response["text"].strip()

        # Clean up the title (remove quotes, extra whitespace, etc.)
        generated_title = generated_title.strip("\"'").strip()

        # Validate title length and content using constants
        if len(generated_title) > AUTO_TITLE_MAX_LENGTH:  # Limit title length
            generated_title = generated_title[: AUTO_TITLE_MAX_LENGTH - 3] + "..."

        if not generated_title or len(generated_title.split()) > AUTO_TITLE_MAX_WORDS:  # Ensure it's reasonably concise
            logger.warning(f"Generated title too long or empty: '{generated_title}'")
            return None

        logger.info(f"Generated auto-title for conversation {conversation.id}: '{generated_title}'")
        return generated_title

    except LLMError as e:
        logger.error(f"LLM error generating auto-title for conversation {conversation.id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error generating auto-title for conversation {conversation.id}: {str(e)}")
        return None


def auto_title_conversation_if_needed(conversation: Conversation) -> bool:
    """
    Automatically title a conversation if it meets the criteria.

    Args:
        conversation: The conversation to potentially title

    Returns:
        True if the conversation was titled, False otherwise
    """
    try:
        if not should_auto_title_conversation(conversation):
            return False

        generated_title = generate_auto_title(conversation)

        if generated_title:
            # Use a transaction to ensure atomic update
            with transaction.atomic():
                # Refresh from database to avoid race conditions
                conversation.refresh_from_db()

                # Double-check that we should still auto-title (in case of concurrent requests)
                if should_auto_title_conversation(conversation):
                    old_title = conversation.title
                    conversation.title = generated_title
                    conversation.save(update_fields=["title"])

                    logger.info(f"Auto-titled conversation {conversation.id}: " f"'{old_title}' -> '{generated_title}'")
                    return True
                else:
                    logger.info(f"Skipping auto-title for conversation {conversation.id} " f"- criteria no longer met")
                    return False
        else:
            logger.warning(f"Failed to generate auto-title for conversation {conversation.id}")
            return False

    except Exception as e:
        logger.error(f"Error in auto-titling conversation {conversation.id}: {str(e)}")
        return False


def async_auto_title_conversation(conversation_id: int):
    """
    Background task to auto-title a conversation.
    Can be called from a separate thread to avoid blocking the main request.

    Args:
        conversation_id: ID of the conversation to potentially title
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        auto_title_conversation_if_needed(conversation)
    except Conversation.DoesNotExist:
        logger.error(f"Conversation {conversation_id} not found for auto-titling")
    except Exception as e:
        logger.error(f"Background auto-titling failed for conversation {conversation_id}: {str(e)}")
