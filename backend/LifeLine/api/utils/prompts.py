import logging
from datetime import datetime
from typing import List, Dict

from ..utils.constants import (
    MAX_MEMORIES_IN_CONTEXT,
    MAX_MEMORY_TITLE_CHARS,
    MAX_MEMORY_DISPLAY_CHARS,
    MEMORY_TRUNCATE_CHARS,
    CONVERSATION_HISTORY_RECENT_LIMIT,
    ENHANCED_PROMPT_HISTORY_TOKENS,
)

logger = logging.getLogger(__name__)

# Base system prompts for different modes
SYSTEM_PROMPTS = {
    "conversational": """You are LifeLine, a smart AI assistant that knows the user well and provides helpful, contextual responses.

Core Principles:
- Be concise but warm - no unnecessary verbosity
- Use memories naturally without explicitly stating "I remember"
- Infer context from past conversations and user patterns
- Provide direct answers first, then elaborate if needed
- Adapt to the user's communication style and preferences

Memory Usage:
- Seamlessly integrate what you know about the user
- Reference past topics, preferences, and goals naturally
- Build on previous conversations without over-explaining
- Use context to provide more relevant, personalized responses

Response Style:
- Direct and helpful, not chatty
- Use markdown for clarity (headers, lists, emphasis)
- Anticipate follow-up needs
- Be proactive with suggestions based on user patterns

Example approach:
- Instead of: "I remember you mentioned you like coffee. Would you like me to help you find coffee shops?"
- Say: "Here are some highly-rated coffee shops near your office in downtown SD."

Be smart, contextual, and efficient.""",
    "coaching": """You are LifeLine, an AI life coach focused on helping users achieve their personal and professional goals.
You remember their goals, progress, challenges, and breakthroughs to provide continuous, personalized guidance.

Your coaching approach:
- Goal-oriented and results-focused
- Encouraging and motivational
- Practical with actionable advice
- Accountable - track progress and follow up
- Adaptive to different learning and working styles

Key responsibilities:
- Help users clarify and set SMART goals
- Break down complex objectives into manageable steps
- Track progress and celebrate achievements
- Address obstacles and setbacks constructively
- Provide accountability and gentle pressure when needed
- Remember past coaching sessions to maintain continuity

Use memories to:
- Reference previously set goals and progress
- Recall past challenges and how they were overcome
- Remember the user's preferred working styles and motivations
- Track long-term patterns and growth""",
    "therapeutic": """You are LifeLine, a supportive AI companion designed to provide emotional support and help users process their thoughts and feelings.
You remember important emotional contexts, coping strategies that work for the user, and ongoing situations.

Important: You are NOT a licensed therapist. Always encourage users to seek professional help for serious mental health concerns.

Your approach:
- Non-judgmental and accepting
- Active listening with reflective responses
- Gentle guidance toward self-discovery
- Supportive but not directive unless safety is concerned
- Mindful of emotional patterns and triggers

Use memories to:
- Remember ongoing emotional situations and their context
- Recall coping strategies that have worked for the user
- Track emotional patterns and potential triggers
- Remember support systems and resources the user has mentioned
- Maintain continuity in emotional support conversations

Always prioritize user safety and well-being.""",
    "productivity": """You are LifeLine, an AI productivity assistant that helps users optimize their work, manage time, and achieve efficiency.
You remember their work patterns, preferences, tools, and ongoing projects.

Your focus areas:
- Time management and scheduling
- Task prioritization and organization
- Workflow optimization
- Goal tracking and project management
- Work-life balance
- Tool and system recommendations

Use memories to:
- Remember the user's work schedule and preferences
- Track ongoing projects and their status
- Recall preferred productivity tools and methods
- Remember past productivity challenges and solutions
- Track patterns in work habits and energy levels
- Maintain context on professional goals and priorities""",
    "creative": """You are LifeLine, an AI creative companion that helps users explore their creativity, develop ideas, and overcome creative blocks.
You remember their creative interests, ongoing projects, and artistic journey.

Your creative support:
- Brainstorming and idea generation
- Creative problem-solving
- Constructive feedback on creative work
- Inspiration and motivation
- Technique and skill development suggestions
- Creative challenge and project ideas

Use memories to:
- Remember ongoing creative projects and their evolution
- Recall the user's creative interests and preferences
- Track creative growth and skill development
- Remember past creative challenges and breakthroughs
- Maintain context on artistic goals and aspirations
- Reference previous creative work and feedback""",
    "agent": """You are LifeLine, a smart AI assistant that takes immediate action while being conversational and helpful.

Core Behavior:
- Act first, explain briefly after
- Use context and memories to understand intent
- Be concise but friendly
- Infer reasonable defaults instead of asking obvious questions
- Reference what you remember about the user naturally

For Email Requests:
- "summarize emails" → search recent emails (1-2 days) and provide clean summary
- "actionable items" → find emails with tasks/deadlines and create markdown table
- "send email" → compose and send with reasonable subject/content
- "search for X" → search emails and summarize findings

Response Style:
- Lead with action, follow with brief context
- Use markdown for structure (tables, lists, headers)
- Reference user's name and preferences when known
- Keep responses focused and scannable

Example:
"Found 12 recent emails. Here's your summary:

**High Priority:**
• Meeting request from Sarah - needs response by Friday
• Invoice #1234 due tomorrow

**Updates:**
• Project Alpha status update
• Newsletter from TechCrunch"

Be proactive, contextual, and efficient.""",
}

# Memory integration templates - more natural and concise
MEMORY_CONTEXT_TEMPLATES = {
    "personal_context": """{memories}
""",
    "goal_tracking": """Current goals and progress:
{memories}

""",
    "ongoing_situations": """Context from recent conversations:
{memories}

""",
    "preferences_learned": """User preferences:
{memories}

""",
}

# Conversation history formatting
CONVERSATION_TEMPLATES = {
    "recent_context": """## Recent Conversation Context:
{conversation_history}

""",
    "continuation": """## Continuing Our Conversation:
{conversation_history}

User: {current_message}""",
}


def get_system_prompt(mode: str = "conversational") -> str:
    """Get the system prompt for the specified chat mode."""
    prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["conversational"])
    logger.debug(f"Retrieved system prompt for mode: {mode}")
    return prompt


def format_memory_context(memories: List[Dict], context_type: str = "personal_context") -> str:
    """
    Format memories into a concise, natural context string for the prompt.

    Args:
        memories: List of memory dictionaries with content, title, etc.
        context_type: Type of memory context to format

    Returns:
        Formatted memory context string
    """
    if not memories:
        return ""

    try:
        # Create a more natural, concise memory summary
        formatted_memories = []

        # Sort memories by importance and recency
        sorted_memories = sorted(
            memories, key=lambda x: (x.get("importance_score", 0.5), x.get("created_at", "")), reverse=True
        )

        # Group similar memories and create concise summaries
        for memory in sorted_memories[:MAX_MEMORIES_IN_CONTEXT]:  # Limit to top memories
            content = memory.get("content", "").strip()
            title = memory.get("title", "").strip()

            # Create concise memory entry
            if title and len(title) < MAX_MEMORY_TITLE_CHARS:
                memory_text = f"{title}: {content}"
            else:
                memory_text = content

            # Keep it concise - max chars per memory
            if len(memory_text) > MAX_MEMORY_DISPLAY_CHARS:
                memory_text = memory_text[:MEMORY_TRUNCATE_CHARS] + "..."

            formatted_memories.append(memory_text)

        # Join memories naturally
        if formatted_memories:
            memory_text = "\n".join([f"• {mem}" for mem in formatted_memories])
        else:
            memory_text = "No specific context available."

        template = MEMORY_CONTEXT_TEMPLATES.get(context_type, MEMORY_CONTEXT_TEMPLATES["personal_context"])

        logger.info(f"Formatted {len(memories)} memories into concise {context_type} context")
        return template.format(memories=memory_text)

    except Exception as e:
        logger.error(f"Error formatting memory context: {str(e)}")
        return ""


def format_conversation_history(messages: List[Dict], max_tokens: int = 10000) -> str:
    """
    Format conversation history with token limit using tiktoken.

    Args:
        messages: List of message dictionaries
        max_tokens: Maximum tokens to include

    Returns:
        Formatted conversation history string
    """
    if not messages:
        return ""

    try:
        import tiktoken

        # Use the encoding for GPT-4 (most common)
        encoding = tiktoken.encoding_for_model("gpt-4")

        formatted_messages = []
        total_tokens = 0

        # Process messages in reverse order (most recent first)
        for message in reversed(messages):
            role = message.get("role", "user")
            content = message.get("content", "").strip()
            timestamp = message.get("created_at", "")

            if not content:
                continue

            # Format message with role and timestamp
            if timestamp:
                try:
                    # Parse timestamp and format nicely
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        time_str = dt.strftime("%H:%M")
                        formatted_msg = f"[{time_str}] {role.title()}: {content}"
                    else:
                        formatted_msg = f"{role.title()}: {content}"
                except:
                    formatted_msg = f"{role.title()}: {content}"
            else:
                formatted_msg = f"{role.title()}: {content}"

            # Count tokens for this message
            msg_tokens = len(encoding.encode(formatted_msg))

            # Check if adding this message would exceed token limit
            if total_tokens + msg_tokens > max_tokens:
                logger.info(f"Reached token limit ({max_tokens}), truncating conversation history")
                break

            formatted_messages.insert(0, formatted_msg)  # Insert at beginning to maintain order
            total_tokens += msg_tokens

        history_text = "\n".join(formatted_messages)

        logger.info(f"Formatted conversation history: {len(formatted_messages)} messages, {total_tokens} tokens")
        return history_text

    except ImportError:
        logger.warning("tiktoken not available, falling back to simple truncation")
        # Fallback to simple message count limit
        recent_messages = (
            messages[-CONVERSATION_HISTORY_RECENT_LIMIT:]
            if len(messages) > CONVERSATION_HISTORY_RECENT_LIMIT
            else messages
        )
        formatted_messages = []

        for message in recent_messages:
            role = message.get("role", "user")
            content = message.get("content", "").strip()
            if content:
                formatted_messages.append(f"{role.title()}: {content}")

        return "\n".join(formatted_messages)

    except Exception as e:
        logger.error(f"Error formatting conversation history: {str(e)}")
        return ""


def build_enhanced_prompt(
    mode: str = "conversational",
    memories: List[Dict] = None,
    conversation_history: List[Dict] = None,
    current_message: str = "",
    user_name: str = "",
    max_history_tokens: int = ENHANCED_PROMPT_HISTORY_TOKENS,  # Token limit for enhanced prompt history
) -> str:
    """
    Build a concise, contextual prompt with system instructions, memories, and conversation context.

    Args:
        mode: Chat mode (conversational, coaching, etc.)
        memories: List of relevant memories
        conversation_history: List of recent messages
        current_message: The current user message
        user_name: User's name for personalization
        max_history_tokens: Maximum tokens for conversation history

    Returns:
        Complete formatted prompt
    """
    try:
        prompt_parts = []

        # 1. System prompt with user context
        system_prompt = get_system_prompt(mode)
        if user_name:
            system_prompt += f"\n\nUser: {user_name}"

        # 2. Integrate memory context naturally into system prompt
        if memories and len(memories) > 0:
            memory_context = format_memory_context(memories, "personal_context")
            if memory_context.strip():
                system_prompt += f"\n\nContext about {user_name or 'the user'}:\n{memory_context}"

        prompt_parts.append(system_prompt)

        # 3. Recent conversation history (more concise)
        if conversation_history and len(conversation_history) > 0:
            # Only include last few messages for immediate context
            recent_messages = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
            history_parts = []

            for msg in recent_messages:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "").strip()
                if content and len(content) < 200:  # Keep messages concise
                    history_parts.append(f"{role}: {content}")
                elif content:
                    history_parts.append(f"{role}: {content[:150]}...")

            if history_parts:
                prompt_parts.append("\nRecent conversation:\n" + "\n".join(history_parts))

        # 4. Current message
        if current_message:
            prompt_parts.append(f"\nUser: {current_message}")

        full_prompt = "\n".join(prompt_parts)

        logger.info(
            f"Built concise prompt: mode={mode}, memories={len(memories) if memories else 0}, "
            f"history_messages={len(conversation_history) if conversation_history else 0}, "
            f"total_length={len(full_prompt)}"
        )

        return full_prompt

    except Exception as e:
        logger.error(f"Error building enhanced prompt: {str(e)}")
        # Fallback to basic prompt
        basic_prompt = get_system_prompt(mode)
        if current_message:
            basic_prompt += f"\n\nUser: {current_message}"
        return basic_prompt


def generate_conversation_title_prompt(messages: List[Dict]) -> str:
    """
    Generate a prompt for creating a conversation title based on the first few messages.

    Args:
        messages: List of message dictionaries with 'content' and 'is_bot' keys

    Returns:
        A prompt for the LLM to generate a concise conversation title
    """
    conversation_text = ""
    for i, msg in enumerate(messages[:3]):  # Only use first 3 messages
        role = "Assistant" if msg.get("is_bot", False) else "User"
        conversation_text += f"{role}: {msg['content']}\n"

    prompt = f"""Based on the following conversation, generate a concise, descriptive title (3-6 words maximum) that captures the main topic or request. The title should be specific enough to help the user identify this conversation later.

Conversation:
{conversation_text.strip()}

Generate only the title, no quotes, no additional text. Examples of good titles:
- "Python Flask API Help"
- "Resume Career Advice"
- "Trip Planning to Japan"
- "Database Schema Design"

Title:"""

    return prompt


# Additional utility functions for prompt management
def get_available_modes() -> List[str]:
    """Get list of available chat modes."""
    return list(SYSTEM_PROMPTS.keys())


def validate_mode(mode: str) -> bool:
    """Check if a chat mode is valid."""
    return mode in SYSTEM_PROMPTS


def get_mode_description(mode: str) -> str:
    """Get a brief description of what each mode does."""
    descriptions = {
        "conversational": "General friendly conversation with memory of past interactions",
        "coaching": "Goal-oriented coaching and personal development support",
        "therapeutic": "Emotional support and processing (not professional therapy)",
        "productivity": "Work efficiency, time management, and productivity optimization",
        "creative": "Creative projects, brainstorming, and artistic development",
    }
    return descriptions.get(mode, "Unknown mode")
