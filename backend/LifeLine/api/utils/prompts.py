import logging
from typing import List, Dict, Any, Optional
import tiktoken
from datetime import datetime

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS = {
    "conversational": """You are a helpful and friendly conversational AI assistant. 
Your responses should be natural, engaging, and informative while maintaining a casual tone.
You aim to make the conversation flow naturally while being helpful and accurate.

When responding, consider the user's previous messages and any relevant memories about them to provide personalized assistance.""",

    "coaching": """You are a supportive and insightful AI coach. 
Your role is to help users achieve their goals through structured guidance, motivation, and accountability.
Ask clarifying questions about their goals, break down complex objectives into manageable steps,
and provide constructive feedback while maintaining a encouraging and professional demeanor.
Keep track of previously discussed goals and progress in the conversation.

Use the provided user memories and conversation history to maintain continuity in your coaching approach.""",

    "memory_integration": """You are an AI assistant with access to the user's memories and conversation history.
Use this context to provide personalized, relevant responses that build upon previous interactions.
Reference past conversations when appropriate, but don't overwhelm the user with too much historical context.
Focus on being helpful while maintaining natural conversation flow."""
}

MEMORY_PROMPTS = {
    "memory_extraction": """Based on the following conversation, extract important information about the user that should be remembered for future interactions. Focus on:
- Personal preferences and interests
- Goals and aspirations
- Important life events or circumstances
- Professional information
- Relationship details that are relevant
- Specific needs or challenges mentioned

Format your response as a JSON object with clear, concise memory entries:
{
    "memories": [
        {
            "category": "preference|goal|personal|professional|relationship|challenge",
            "content": "Clear, concise description of what to remember",
            "importance": "high|medium|low",
            "context": "Brief context about when/how this was mentioned"
        }
    ]
}

Conversation to analyze:
{conversation_text}""",

    "memory_relevance": """Given the user's current message and their stored memories, identify which memories are most relevant to provide helpful context for the response.

Current message: {current_message}

User memories:
{memories}

Respond with a JSON object containing the most relevant memories:
{
    "relevant_memories": [
        {
            "memory_id": "memory_identifier",
            "relevance_score": 0.9,
            "reason": "Why this memory is relevant"
        }
    ]
}"""
}

RAG_PROMPTS = {
    "context_integration": """You are responding to a user message with access to relevant context from their previous conversations and memories.

Current message: {current_message}

Relevant memories about the user:
{relevant_memories}

Recent conversation history (last {token_limit} tokens):
{conversation_history}

Provide a helpful, personalized response that naturally incorporates relevant context without overwhelming the user."""
}

def get_system_prompt(mode="conversational"):
    """Get the system prompt for the specified chat mode."""
    return SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["conversational"])

def get_memory_prompt(prompt_type="memory_extraction"):
    """Get memory-related prompts for various operations."""
    return MEMORY_PROMPTS.get(prompt_type, "")

def get_rag_prompt(prompt_type="context_integration"):
    """Get RAG-related prompts for context integration."""
    return RAG_PROMPTS.get(prompt_type, "")

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in text using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Error counting tokens: {e}. Using approximation.")
        # Fallback approximation: ~4 characters per token
        return len(text) // 4

def truncate_conversation_history(messages: List[Dict], token_limit: int = 10000, model: str = "gpt-4") -> List[Dict]:
    """
    Truncate conversation history to stay within token limit.
    Keeps the most recent messages that fit within the limit.
    """
    if not messages:
        return []

    try:
        encoding = tiktoken.encoding_for_model(model)
        truncated_messages = []
        current_tokens = 0

        # Start from the most recent message and work backwards
        for message in reversed(messages):
            message_text = f"{message.get('role', '')}: {message.get('content', '')}"
            message_tokens = len(encoding.encode(message_text))

            if current_tokens + message_tokens > token_limit:
                break

            truncated_messages.insert(0, message)
            current_tokens += message_tokens

        logger.info(f"Truncated conversation history to {len(truncated_messages)} messages ({current_tokens} tokens)")
        return truncated_messages

    except Exception as e:
        logger.error(f"Error truncating conversation history: {e}")
        # Fallback: return last 50 messages
        return messages[-50:] if len(messages) > 50 else messages

def format_memories_for_context(memories: List[Dict]) -> str:
    """Format user memories for inclusion in prompts."""
    if not memories:
        return "No previous memories available."

    formatted_memories = []
    for memory in memories:
        category = memory.get('category', 'general')
        content = memory.get('content', '')
        importance = memory.get('importance', 'medium')

        formatted_memories.append(f"[{category.upper()}] {content} (Importance: {importance})")

    return "\n".join(formatted_memories)

def format_conversation_for_context(messages: List[Dict]) -> str:
    """Format conversation messages for inclusion in prompts."""
    if not messages:
        return "No conversation history available."

    formatted_messages = []
    for message in messages:
        role = message.get('role', 'user')
        content = message.get('content', '')
        timestamp = message.get('created_at', '')

        if timestamp:
            formatted_messages.append(f"[{timestamp}] {role}: {content}")
        else:
            formatted_messages.append(f"{role}: {content}")

    return "\n".join(formatted_messages)

def build_rag_context(current_message: str, memories: List[Dict], conversation_history: List[Dict],
                     token_limit: int = 10000, model: str = "gpt-4") -> Dict[str, Any]:
    """
    Build comprehensive RAG context for LLM processing.

    Args:
        current_message: The user's current message
        memories: List of relevant user memories
        conversation_history: Recent conversation messages
        token_limit: Maximum tokens for conversation history
        model: OpenAI model name for token counting

    Returns:
        Dictionary containing formatted context for LLM
    """
    try:
        # Truncate conversation history to fit within token limit
        truncated_history = truncate_conversation_history(conversation_history, token_limit, model)

        # Format components
        formatted_memories = format_memories_for_context(memories)
        formatted_history = format_conversation_for_context(truncated_history)

        # Count tokens for logging
        memory_tokens = count_tokens(formatted_memories, model)
        history_tokens = count_tokens(formatted_history, model)

        logger.info(f"RAG context built - Memories: {memory_tokens} tokens, History: {history_tokens} tokens")

        return {
            "current_message": current_message,
            "relevant_memories": formatted_memories,
            "conversation_history": formatted_history,
            "token_limit": token_limit,
            "memory_count": len(memories),
            "message_count": len(truncated_history),
            "total_context_tokens": memory_tokens + history_tokens
        }

    except Exception as e:
        logger.error(f"Error building RAG context: {e}")
        return {
            "current_message": current_message,
            "relevant_memories": "Error loading memories",
            "conversation_history": "Error loading conversation history",
            "token_limit": token_limit,
            "memory_count": 0,
            "message_count": 0,
            "total_context_tokens": 0
        }
