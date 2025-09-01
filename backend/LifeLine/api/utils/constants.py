# API Constants for LifeLine Application

# =============================================================================
# FRONTEND-CONFIGURABLE CONSTANTS
# These are default values that can be overridden by frontend requests
# =============================================================================

# Default model and API settings (can be overridden in requests)
DEFAULT_MODEL = "gpt-4.1-nano"  # Default LLM model
DEFAULT_CONVERSATIONAL_MODE = "conversational"  # Default conversation mode
DEFAULT_TEMPERATURE = 0.2  # Default model temperature
TTS_DEFAULT_MODEL = "tts-1"  # Default text-to-speech model
TTS_DEFAULT_VOICE = "alloy"  # Default TTS voice

# Pagination defaults (can be overridden in query params)
DEFAULT_PAGE_NUMBER = 1  # Default page number for pagination

# Frontend auto-refresh settings
AUTO_REFRESH_DELAY_MS = 3000  # Delay before checking for title updates (frontend)
AUTO_REFRESH_TIMEOUT_MS = 15000  # Maximum time to keep auto-refresh enabled

# =============================================================================
# BACKEND-ONLY CONFIGURATION CONSTANTS
# These are internal backend settings not exposed to frontend
# =============================================================================

# Auto-titling configuration
AUTO_TITLE_MIN_MESSAGES = 3  # Minimum messages required before auto-titling can occur
AUTO_TITLE_MAX_WORDS = 8  # Maximum words allowed in generated titles
AUTO_TITLE_MAX_LENGTH = 100  # Maximum character length for titles

# Memory system configuration
MAX_HISTORY_TOKENS = 10000  # Maximum tokens for conversation history
MAX_MEMORIES_RELEVANT = 5  # Maximum relevant memories to include
MAX_MEMORIES_CONVERSATION = 3  # Maximum conversation-specific memories
MIN_SIMILARITY_THRESHOLD = 0.3  # Minimum similarity for memory retrieval
CONVERSATION_MEMORIES_LIMIT = 5  # Default limit for conversation-specific memories
DEFAULT_MEMORIES_BY_TYPE_LIMIT = 10  # Default limit for memories by type query

# LLM and AI processing settings
LLM_EXTRACTION_TEMPERATURE = 0.1  # Temperature for memory extraction LLM calls
EMBEDDING_DEFAULT_MODEL = "text-embedding-3-small"  # Default embedding model
ENHANCED_PROMPT_HISTORY_TOKENS = 6000  # Token limit for enhanced prompt history

# =============================================================================
# MODEL-SPECIFIC TOKEN LIMITS AND CONFIGURATIONS
# Context window limits for different OpenAI models (as of 2025)
# These limits determine how much text can be processed in a single request
# =============================================================================
MODEL_CONTEXT_LIMITS = {
    # Latest GPT-5 family models (2025)
    "gpt-5": 1000000,  # 1M tokens - Latest flagship model with massive context
    "gpt-5-turbo": 1000000,  # 1M tokens - Faster version of GPT-5
    # GPT-4.1 family models (2024-2025)
    "gpt-4.1": 1000000,  # 1M tokens - Advanced reasoning with huge context
    "gpt-4.1-turbo": 1000000,  # 1M tokens - Faster GPT-4.1 variant
    "gpt-4.1-nano": 128000,  # 128k tokens - Lightweight GPT-4.1 for efficiency
    # GPT-4o family models (2024)
    "gpt-4o": 128000,  # 128k tokens - Multimodal flagship model
    "gpt-4o-mini": 128000,  # 128k tokens - Cost-effective GPT-4o variant
    "gpt-4o-audio-preview": 128000,  # 128k tokens - Audio-capable preview
    # Legacy GPT-4 family models
    "gpt-4-turbo": 128000,  # 128k tokens - Previous generation turbo
    "gpt-4-turbo-preview": 128000,  # 128k tokens - Preview version
    "gpt-4": 8192,  # 8k tokens - Original GPT-4 (legacy)
    "gpt-4-32k": 32768,  # 32k tokens - Extended context GPT-4 (legacy)
    # GPT-3.5 family models (legacy)
    "gpt-3.5-turbo": 16385,  # 16k tokens - Legacy model for basic tasks
    "gpt-3.5-turbo-16k": 16385,  # 16k tokens - Extended context variant
}

# =============================================================================
# TOKEN SAFETY MARGINS AND CHUNKING CONFIGURATION
# These constants control how we manage token limits to prevent API errors
# =============================================================================

# SAFETY_MARGIN: Reserve 10% of context window to account for:
# - Token counting inaccuracies between tiktoken and OpenAI's internal counting
# - Unexpected overhead from message formatting and API structures
# - Buffer for model response generation without hitting limits
TOKEN_SAFETY_MARGIN = 0.1

# CHUNK_OVERLAP: Number of tokens to overlap between consecutive chunks
# Purpose: Maintains context continuity when processing large documents
# Helps the model understand connections between chunk boundaries
CHUNK_OVERLAP_TOKENS = 200

# MIN_RESPONSE_TOKENS: Minimum tokens reserved for the model's response
# Ensures the model has enough space to generate a complete, useful response
# Prevents truncated responses due to context window exhaustion
MIN_RESPONSE_TOKENS = 2000

# SYSTEM_PROMPT_BUFFER: Extra tokens reserved for system prompts and overhead
# Accounts for: system messages, prompt formatting, API metadata, tool definitions
# Provides buffer for dynamic prompt components (memories, context, etc.)
SYSTEM_PROMPT_BUFFER_TOKENS = 1000

# =============================================================================
# GMAIL & EMAIL SUMMARIZATION CONFIGURATION
# Single source of truth for Gmail tools and summarization behavior
# =============================================================================

# Default model and temperature for tool-level email summarization
EMAIL_SUMMARY_MODEL_DEFAULT = "gpt-4o-mini"
EMAIL_SUMMARY_TEMPERATURE_DEFAULT = 0.0

# Preview lengths used when compressing email content before summarization
EMAIL_BODY_PREVIEW_CHARS = 1200
EMAIL_SNIPPET_PREVIEW_CHARS = 180

# Batch size guidance for processing email IDs
GMAIL_SUMMARY_BATCH_SIZE = 12

# Default max results for Gmail search
GMAIL_SEARCH_DEFAULT_MAX_RESULTS = 5

# Gmail API retry/backoff settings to mitigate transient SSL/transport errors
GMAIL_API_MAX_RETRIES = 3
GMAIL_API_RETRY_BASE_SECONDS = 0.3

# =============================================================================
# AGENT-SPECIFIC TOKEN MANAGEMENT
# Controls how the LangGraph agent processes large content and manages context
# =============================================================================

# AGENT_MAX_CHUNK_TOKENS: Maximum size of each chunk when processing large tool outputs
# Purpose: Breaks down massive email/document data into digestible pieces
# Balance: Large enough to preserve context, small enough to avoid token limits
# Used when tool outputs exceed available context space
AGENT_MAX_CHUNK_TOKENS = 75000

# AGENT_MODERATE_CONTENT_TOKENS: Threshold for triggering focused summarization
# Purpose: Content above this size gets summarized instead of passed through
# Prevents moderately large content from consuming too much context
# Applied to tool outputs that don't need full chunking but are still large
AGENT_MODERATE_CONTENT_TOKENS = 8000

# AGENT_HISTORY_LIMIT_MESSAGES: Maximum conversation history messages to include
# Purpose: Limits conversation context to prevent token overflow
# Keeps only the most recent exchanges to maintain relevance
# Older messages are excluded to make room for current processing
AGENT_HISTORY_LIMIT_MESSAGES = 10

# AGENT_MESSAGE_TRUNCATE_TOKENS: Maximum tokens per individual history message
# Purpose: Prevents any single message from consuming excessive context
# Long messages get truncated while preserving their essential content
# Ensures balanced token allocation across conversation history
AGENT_MESSAGE_TRUNCATE_TOKENS = 25000

# AGENT_RESUMMARY_THRESHOLD_TOKENS: Threshold for re-summarizing combined chunk summaries
# Purpose: Only re-summarize if combined summaries exceed this limit
# Prevents unnecessary re-summarization when individual summaries are already concise
# Should be significantly smaller than model context to leave room for system prompt + history
AGENT_RESUMMARY_THRESHOLD_TOKENS = 50000

# AGENT_MAX_PARALLEL_CHUNKS: Maximum number of chunks to process in parallel
# Purpose: Limits concurrent API calls to prevent rate limiting and memory issues
# Balance: High enough for speed, low enough to avoid overwhelming the API
AGENT_MAX_PARALLEL_CHUNKS = 10

# Memory scoring algorithm weights
MEMORY_SIMILARITY_WEIGHT = 0.6  # Weight for semantic similarity in memory scoring
MEMORY_IMPORTANCE_WEIGHT = 0.3  # Weight for importance score in memory scoring
MEMORY_RECENCY_WEIGHT = 0.1  # Weight for recency in memory scoring
MEMORY_CONTEXT_SIMILARITY_WEIGHT = 0.7  # Weight for context similarity
MEMORY_IMPORTANCE_CONTEXT_WEIGHT = 0.3  # Weight for importance in context scoring
MEMORY_RECENCY_DAYS_DIVISOR = 30.0  # Days divisor for recency calculation

# Default values and fallbacks
DEFAULT_IMPORTANCE_SCORE = 0.5  # Default importance score for memories
DEFAULT_CONFIDENCE_SCORE = 0.0  # Default confidence score
DEFAULT_MESSAGE_COUNT = 0  # Default message count for new conversations
DEFAULT_TOTAL_STEPS = 0  # Default total steps for agent metadata
DEFAULT_TOTAL_TOKENS = 0  # Default total tokens for agent metadata
DEFAULT_EMBEDDING_DIMENSIONS = 0  # Default embedding dimensions when none available

# Text processing and display limits
MAX_MEMORY_DISPLAY_CHARS = 100  # Maximum characters to display per memory
MEMORY_TRUNCATE_CHARS = 97  # Characters before truncation (leaving 3 for "...")
MAX_MEMORY_TITLE_CHARS = 50  # Maximum characters for memory title
MAX_MEMORIES_IN_CONTEXT = 8  # Maximum memories to include in context
CONVERSATION_HISTORY_RECENT_LIMIT = 20  # Number of recent messages to include

# =============================================================================
# TIKTOKEN ENCODING MODEL MAPPING
# Maps OpenAI API model names to their corresponding tiktoken encoding models
# Tiktoken uses different encoding names than the API model names
# =============================================================================

# TIKTOKEN_MODEL_MAPPING: Maps API model names to tiktoken encoding identifiers
# Purpose: Ensures accurate token counting by using the correct encoding
# Tiktoken doesn't have encodings for every model variant, so we map to base models
# This mapping is critical for accurate token counting and chunking decisions
TIKTOKEN_MODEL_MAPPING = {
    # GPT-5 family -> use GPT-4o encoding (most similar available)
    "gpt-5": "gpt-4o",
    "gpt-5-turbo": "gpt-4o",
    # GPT-4.1 family -> use GPT-4o encoding (most similar available)
    "gpt-4.1": "gpt-4o",
    "gpt-4.1-turbo": "gpt-4o",
    "gpt-4.1-nano": "gpt-4o",
    # GPT-4o family -> use native GPT-4o encoding
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o",
    "gpt-4o-audio-preview": "gpt-4o",
    # GPT-4 family -> use GPT-4 encoding
    "gpt-4-turbo": "gpt-4",
    "gpt-4-turbo-preview": "gpt-4",
    "gpt-4": "gpt-4",
    "gpt-4-32k": "gpt-4",
    # GPT-3.5 family -> use native encoding
    "gpt-3.5-turbo": "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo",
}

# DEFAULT_TIKTOKEN_MODEL: Fallback encoding for unknown or new models
# Purpose: Provides safe default when encountering unrecognized model names
# Uses GPT-4o encoding as it's the most current and widely compatible
DEFAULT_TIKTOKEN_MODEL = "gpt-4o"

# Debug and logging settings
DEBUG_PREVIEW_CHARS = 500  # Characters to show in debug preview
LOG_MESSAGE_PREVIEW_CHARS = 100  # Characters to show in log message preview
AGENT_RESPONSE_PREVIEW_CHARS = 200  # Characters to show in agent response preview

# Audio processing settings
MIN_AUDIO_SIZE_BYTES = 1024  # Minimum audio file size for transcription
AUDIO_SEEK_END_POSITION = 2  # Position for seeking to end of audio file (os.SEEK_END)

# System constants
MS_CONVERSION_FACTOR = 1000  # Factor to convert seconds to milliseconds
