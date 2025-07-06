import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

# Base system prompts for different modes
SYSTEM_PROMPTS = {
    "conversational": """You are LifeLine, a helpful and empathetic AI assistant that remembers important details about users.
You maintain context across conversations and build meaningful relationships by recalling personal information, preferences, and past discussions.

Your personality:
- Warm, friendly, and genuinely interested in the user's wellbeing
- Thoughtful and considerate in responses
- Able to reference past conversations naturally
- Supportive but not overly familiar unless the relationship has developed
- Professional yet personable

Guidelines:
- Use memories to personalize responses and show continuity
- Reference past conversations when relevant
- Ask follow-up questions based on previous discussions
- Be genuinely helpful while maintaining appropriate boundaries
- Adapt your communication style to match the user's preferences over time""",
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
}

# Memory integration templates
MEMORY_CONTEXT_TEMPLATES = {
    "personal_context": """## What I Remember About You:
{memories}

""",
    "goal_tracking": """## Your Goals & Progress:
{memories}

""",
    "ongoing_situations": """## Ongoing Situations We've Discussed:
{memories}

""",
    "preferences_learned": """## Your Preferences & Style:
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
    Format memories into a context string for the prompt.

    Args:
        memories: List of memory dictionaries with content, title, etc.
        context_type: Type of memory context to format

    Returns:
        Formatted memory context string
    """
    if not memories:
        return ""

    try:
        # Group memories by type for better organization
        memory_groups = {}
        for memory in memories:
            mem_type = memory.get("memory_type", "personal")
            if mem_type not in memory_groups:
                memory_groups[mem_type] = []
            memory_groups[mem_type].append(memory)

        # Format memories with better structure
        formatted_memories = []

        for mem_type, mem_list in memory_groups.items():
            if mem_type == "goal":
                formatted_memories.append("### Goals & Objectives:")
            elif mem_type == "preference":
                formatted_memories.append("### Personal Preferences:")
            elif mem_type == "relationship":
                formatted_memories.append("### Relationships & People:")
            elif mem_type == "experience":
                formatted_memories.append("### Important Experiences:")
            else:
                formatted_memories.append("### Personal Information:")

            for memory in mem_list:
                title = memory.get("title", "").strip()
                content = memory.get("content", "").strip()

                if title and title.lower() not in content.lower():
                    formatted_memories.append(f"- **{title}**: {content}")
                else:
                    formatted_memories.append(f"- {content}")

        memory_text = "\n".join(formatted_memories)
        template = MEMORY_CONTEXT_TEMPLATES.get(context_type, MEMORY_CONTEXT_TEMPLATES["personal_context"])

        logger.info(f"Formatted {len(memories)} memories into {context_type} context")
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
        recent_messages = messages[-20:] if len(messages) > 20 else messages
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
    max_history_tokens: int = 10000,
) -> str:
    """
    Build a comprehensive prompt with system instructions, memories, and conversation context.

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

        # 1. System prompt
        system_prompt = get_system_prompt(mode)
        if user_name:
            system_prompt += f"\n\nYou are speaking with {user_name}."
        prompt_parts.append(system_prompt)

        # 2. Memory context
        if memories:
            memory_context = format_memory_context(memories, "personal_context")
            if memory_context:
                prompt_parts.append(memory_context)

        # 3. Conversation history
        if conversation_history:
            history_context = format_conversation_history(conversation_history, max_history_tokens)
            if history_context:
                template = CONVERSATION_TEMPLATES["recent_context"]
                prompt_parts.append(template.format(conversation_history=history_context))

        # 4. Current message
        if current_message:
            prompt_parts.append(f"User: {current_message}")

        full_prompt = "\n".join(prompt_parts)

        logger.info(
            f"Built enhanced prompt: mode={mode}, memories={len(memories) if memories else 0}, "
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
