# API Constants for LifeLine Application

# Auto-titling constants
AUTO_TITLE_MIN_MESSAGES = 3  # Minimum messages required before auto-titling can occur
AUTO_TITLE_MAX_WORDS = 8  # Maximum words allowed in generated titles
AUTO_TITLE_MAX_LENGTH = 100  # Maximum character length for titles

# Memory and context limits
MAX_HISTORY_TOKENS = 10000  # Maximum tokens for conversation history
MAX_MEMORIES_RELEVANT = 5  # Maximum relevant memories to include
MAX_MEMORIES_CONVERSATION = 3  # Maximum conversation-specific memories
MIN_SIMILARITY_THRESHOLD = 0.3  # Minimum similarity for memory retrieval

# Message and content limits
MIN_AUDIO_SIZE_BYTES = 1024  # Minimum audio file size for transcription
DEFAULT_TEMPERATURE = 0.2  # Default model temperature

# Frontend auto-refresh settings
AUTO_REFRESH_DELAY_MS = 3000  # Delay before checking for title updates (frontend)
AUTO_REFRESH_TIMEOUT_MS = 15000  # Maximum time to keep auto-refresh enabled
