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

# Debug and logging settings
DEBUG_PREVIEW_CHARS = 500  # Characters to show in debug preview
LOG_MESSAGE_PREVIEW_CHARS = 100  # Characters to show in log message preview
AGENT_RESPONSE_PREVIEW_CHARS = 200  # Characters to show in agent response preview

# Audio processing settings
MIN_AUDIO_SIZE_BYTES = 1024  # Minimum audio file size for transcription
AUDIO_SEEK_END_POSITION = 2  # Position for seeking to end of audio file (os.SEEK_END)

# System constants
MS_CONVERSION_FACTOR = 1000  # Factor to convert seconds to milliseconds
