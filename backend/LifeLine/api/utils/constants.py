# API Constants for LifeLine Application

# =============================================================================
# FRONTEND-CONFIGURABLE CONSTANTS
# These are default values that can be overridden by frontend requests
# =============================================================================

# Default model and API settings (can be overridden in requests)
# DEFAULT_MODEL
# - Purpose: Backend-wide default chat model when none is provided.
# - Used by: `views/views.py` (ConversationListCreateView.post, MessageListCreateView.post),
#            `agent_utils.run_agent(model=DEFAULT_MODEL)` parameter default.
# - Rationale: Lightweight, cost-effective default that still supports our prompt sizes.
DEFAULT_MODEL = "gpt-4.1-nano"

# DEFAULT_CONVERSATIONAL_MODE
# - Purpose: Default mode for new conversations and message processing.
# - Used by: `views/views.py` when initializing conversations and handling messages.
# - Rationale: Ensures consistent routing to non-agent conversational flows unless specified otherwise.
DEFAULT_CONVERSATIONAL_MODE = "conversational"

# DEFAULT_TEMPERATURE
# - Purpose: Default randomness for generation when not specified by client.
# - Used by: `views/views.py` defaults into LLM calls; `llm.call_llm_text(..., temperature=DEFAULT_TEMPERATURE)`.
# - Rationale: Slight creativity while maintaining determinism for assistant tone.
DEFAULT_TEMPERATURE = 0.2

# TTS_DEFAULT_MODEL
# - Purpose: Default text-to-speech model for `llm.call_llm_TTS()`.
# - Used by: `llm.call_llm_TTS(model=TTS_DEFAULT_MODEL, ...)` default arg.
# - Rationale: Stable, broadly available TTS backend.
TTS_DEFAULT_MODEL = "tts-1"

# TTS_DEFAULT_VOICE
# - Purpose: Default synthetic voice for TTS responses.
# - Used by: `llm.call_llm_TTS(voice=TTS_DEFAULT_VOICE, ...)` default arg.
# - Rationale: Chosen for clarity and neutrality.
TTS_DEFAULT_VOICE = "alloy"

# TRANSCRIBE_DEFAULT_MODEL
# - Purpose: Default speech-to-text model for audio transcription.
# - Used by: `llm.call_llm_transcribe()` and `llm.call_llm_transcribe_memory()` default arg; value also originates
#            from frontend `frontend/src/hooks/useSpeechToText.js` when calling transcribe API.
# - Rationale: Transcription-specialized variant optimized for accuracy and latency.
TRANSCRIBE_DEFAULT_MODEL = "gpt-4o-mini-transcribe"

# Pagination defaults (can be overridden in query params)
# DEFAULT_PAGE_NUMBER
# - Purpose: Default page index when pagination params are omitted.
# - Used by: `views/views.py` endpoints employing pagination.
# - Rationale: Conventional 1-based pagination for user-facing APIs.
DEFAULT_PAGE_NUMBER = 1

# Frontend auto-refresh settings
# AUTO_REFRESH_DELAY_MS
# - Purpose: Client UI delay between background refresh checks (title updates, etc.).
# - Used by: Frontend; not imported by backend.
# - Rationale: Balance responsiveness with request overhead.
AUTO_REFRESH_DELAY_MS = 3000
# AUTO_REFRESH_TIMEOUT_MS
# - Purpose: Client UI maximum duration to auto-refresh before stopping.
# - Used by: Frontend; not imported by backend.
# - Rationale: Prevents indefinite background polling.
AUTO_REFRESH_TIMEOUT_MS = 15000

# =============================================================================
# BACKEND-ONLY CONFIGURATION CONSTANTS
# These are internal backend settings not exposed to frontend
# =============================================================================

# Auto-titling configuration
# AUTO_TITLE_MIN_MESSAGES
# - Purpose: Minimum message count before a conversation is eligible for auto-title.
# - Used by: `conversation_utils.should_auto_title_conversation()` and `generate_auto_title()`.
# - Rationale: Ensures enough context for a meaningful title (first 3 messages considered).
AUTO_TITLE_MIN_MESSAGES = 3
# AUTO_TITLE_MAX_WORDS
# - Purpose: Upper bound on words in generated titles.
# - Used by: `conversation_utils.generate_auto_title()` validation step.
# - Rationale: Keep titles concise for sidebar readability.
AUTO_TITLE_MAX_WORDS = 8
# AUTO_TITLE_MAX_LENGTH
# - Purpose: Character-length limit for generated titles.
# - Used by: `conversation_utils.generate_auto_title()` truncation check.
# - Rationale: Avoids overflow in UI and database fields.
AUTO_TITLE_MAX_LENGTH = 100

# Memory system configuration
# MAX_HISTORY_TOKENS
# - Purpose: Upper bound for tokens considered from recent history in enhanced prompts.
# - Used by: `views/views.py` prompt building.
# - Rationale: Control context size and latency.
MAX_HISTORY_TOKENS = 10000
# MAX_MEMORIES_RELEVANT
# - Purpose: Max number of globally relevant memories to include.
# - Used by: `views/views.py` memory retrieval before prompting.
# - Rationale: Keep context focused and compact.
MAX_MEMORIES_RELEVANT = 5
# MAX_MEMORIES_CONVERSATION
# - Purpose: Max number of conversation-scoped memories to include.
# - Used by: `views/views.py` memory retrieval.
# - Rationale: Prioritize highly related items without flooding prompt.
MAX_MEMORIES_CONVERSATION = 3
# MIN_SIMILARITY_THRESHOLD
# - Purpose: Minimum cosine similarity cutoff for including a memory.
# - Used by: `views/views.py` via `memory_utils` retrieval.
# - Rationale: Filter out weak matches.
MIN_SIMILARITY_THRESHOLD = 0.3
# CONVERSATION_MEMORIES_LIMIT
# - Purpose: Default limit for conversation-specific memory queries.
# - Used by: Currently advisory; reserved for consistent querying.
# - Rationale: Establishes standard page-size for future endpoints.
CONVERSATION_MEMORIES_LIMIT = 5
# DEFAULT_MEMORIES_BY_TYPE_LIMIT
# - Purpose: Default page-size when listing memories by type.
# - Used by: Currently advisory.
# - Rationale: Prevents overly large payloads.
DEFAULT_MEMORIES_BY_TYPE_LIMIT = 10

# LLM and AI processing settings
# LLM_EXTRACTION_TEMPERATURE
# - Purpose: Determinism level for extraction tasks.
# - Used by: `llm.call_llm_memory_extraction`, `llm.call_llm_conversation_memory_extraction` flows.
# - Rationale: Lower temperature yields stable JSON outputs for storage.
LLM_EXTRACTION_TEMPERATURE = 0.1
# EMBEDDING_DEFAULT_MODEL
# - Purpose: Default model for embedding generation.
# - Used by: `llm.call_llm_embedding(model=EMBEDDING_DEFAULT_MODEL)`.
# - Rationale: Cost-effective with sufficient quality for retrieval.
EMBEDDING_DEFAULT_MODEL = "text-embedding-3-small"
# ENHANCED_PROMPT_HISTORY_TOKENS
# - Purpose: Token cap for recent history included by enhanced prompt builders.
# - Used by: `prompts.py` when assembling prompts.
# - Rationale: Reduce context bloat while preserving recency.
ENHANCED_PROMPT_HISTORY_TOKENS = 6000

# =============================================================================
# MODEL-SPECIFIC TOKEN LIMITS AND CONFIGURATIONS
# Context window limits for different OpenAI models (as of 2025)
# These limits determine how much text can be processed in a single request
# =============================================================================
# MODEL_CONTEXT_LIMITS: Mapping of API model name -> maximum context window (tokens)
# Usage: consumed by `token_utils.TokenManager` to set context_limit and derive safe limits and chunk sizes.
# Interactions: In `token_utils.TokenManager.__init__`: `self.context_limit = MODEL_CONTEXT_LIMITS.get(model, 128000)`
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

# TOKEN_SAFETY_MARGIN
# - Purpose: Reserve a fraction of context window to avoid API limit errors.
# - Used by: `token_utils.TokenManager.safe_context_limit`.
# - Rationale: Accounts for encoding variance and overhead structures.
# - Interactions: In `TokenManager.__init__`: `self.safe_context_limit = int(self.context_limit * (1 - TOKEN_SAFETY_MARGIN))`
TOKEN_SAFETY_MARGIN = 0.1

# CHUNK_OVERLAP_TOKENS
# - Purpose: Overlap size between consecutive chunks to maintain continuity.
# - Used by: `token_utils.TokenManager.chunk_content*` helpers.
# - Rationale: Reduces coherence loss across chunk boundaries.
# - Interactions: In `TokenManager.chunk_content()` and `.chunk_content_with_size()`:
#   `effective_chunk_tokens = max(chunk_size_tokens - CHUNK_OVERLAP_TOKENS, 1000)` and overlap concatenation uses `overlap = content[overlap_start_char:start_char]` where `overlap_tokens = min(CHUNK_OVERLAP_TOKENS, tokens_processed)`
CHUNK_OVERLAP_TOKENS = 200

# MIN_RESPONSE_TOKENS
# - Purpose: Guaranteed headroom for completion tokens.
# - Used by: `token_utils.TokenManager.get_available_tokens()`.
# - Rationale: Prevents truncated outputs under heavy context.
# - Interactions: In `TokenManager.get_available_tokens()`: `used_tokens = system_tokens + history_tokens + MIN_RESPONSE_TOKENS + SYSTEM_PROMPT_BUFFER_TOKENS`; then `available = self.safe_context_limit - used_tokens`
MIN_RESPONSE_TOKENS = 2000

# SYSTEM_PROMPT_BUFFER_TOKENS
# - Purpose: Reserved tokens for system prompts, tool schemas, and dynamic memory/context.
# - Used by: `token_utils.TokenManager.get_available_tokens()`.
# - Rationale: Avoids overruns when prompts expand.
# - Interactions: See `MIN_RESPONSE_TOKENS` above for the exact `used_tokens` formula.
SYSTEM_PROMPT_BUFFER_TOKENS = 1000

# =============================================================================
# GMAIL & EMAIL SUMMARIZATION CONFIGURATION
# Single source of truth for Gmail tools and summarization behavior
# =============================================================================

# Default model and temperature for tool-level email summarization
# EMAIL_SUMMARY_MODEL_DEFAULT
# - Purpose: Forced model for Gmail summarization tool to avoid legacy 8k context errors.
# - Used by: `connectors/gmail/gmail_agent_tool.summarize_emails_by_id()` (overrides any agent-provided model).
# - Rationale: Stability and sufficient context for batch summaries.
EMAIL_SUMMARY_MODEL_DEFAULT = "gpt-4.1-nano"
# EMAIL_SUMMARY_TEMPERATURE_DEFAULT
# - Purpose: Default temperature for email summarization.
# - Used by: `gmail_agent_tool.summarize_emails_by_id()` when temperature is not provided.
# - Rationale: Deterministic extraction of facts.
EMAIL_SUMMARY_TEMPERATURE_DEFAULT = 0.0

# Preview lengths used when compressing email content before summarization
# EMAIL_BODY_PREVIEW_CHARS
# - Purpose: Max body characters included per email in summarization input.
# - Used by: `gmail_agent_tool.compact_email()` before invoking LLM.
# - Rationale: Keeps token usage controlled while preserving salient content.
EMAIL_BODY_PREVIEW_CHARS = 5000
# EMAIL_SNIPPET_PREVIEW_CHARS
# - Purpose: Max snippet characters included when full body is missing/unnecessary.
# - Used by: `gmail_agent_tool.compact_email()`.
# - Rationale: Provide quick context with minimal cost.
EMAIL_SNIPPET_PREVIEW_CHARS = 500

# GMAIL_SUMMARY_BATCH_SIZE
# - Purpose: Recommended count per summarization batch.
# - Used by: Advisory (current code does not enforce this).
# - Rationale: Balance throughput vs. token risk.
GMAIL_SUMMARY_BATCH_SIZE = 12

# GMAIL_SEARCH_DEFAULT_MAX_RESULTS
# - Purpose: Default cap on results returned by search tool.
# - Used by: `gmail_agent_tool.search_emails` default parameter.
# - Rationale: Prevent large payloads by default.
GMAIL_SEARCH_DEFAULT_MAX_RESULTS = 5

# GMAIL_API_MAX_RETRIES
# - Purpose: Recommended number of retries for transient Gmail API failures.
# - Used by: Advisory (connector implementation reference).
# - Rationale: Mitigate network/SSL flakiness.
GMAIL_API_MAX_RETRIES = 3
# GMAIL_API_RETRY_BASE_SECONDS
# - Purpose: Base backoff delay in seconds.
# - Used by: Advisory.
# - Rationale: Exponential backoff starting value.
GMAIL_API_RETRY_BASE_SECONDS = 0.3

# =============================================================================
# AGENT-SPECIFIC TOKEN MANAGEMENT
# Controls how the LangGraph agent processes large content and manages context
# =============================================================================

# AGENT_MAX_CHUNK_TOKENS
# - Purpose: Upper bound for per-chunk size during large tool output processing.
# - Used by: `token_utils.TokenManager` to bound chunk sizes.
# - Rationale: Avoid memory spikes and API pressure.
# - Interactions: In `TokenManager.__init__`: `self.max_chunk_tokens = min(AGENT_MAX_CHUNK_TOKENS, self.safe_context_limit // 4)`
AGENT_MAX_CHUNK_TOKENS = 75000

# AGENT_MODERATE_CONTENT_TOKENS
# - Purpose: Token threshold above which moderate content is summarized instead of passed verbatim.
# - Used by: `token_utils.TokenManager.should_summarize_moderate_content()`.
# - Rationale: Keep context lean for mid-sized payloads.
# - Interactions: In `TokenManager.should_summarize_moderate_content()`: `return self.count_tokens(content) > self.moderate_content_tokens`
AGENT_MODERATE_CONTENT_TOKENS = 8000

# AGENT_HISTORY_LIMIT_MESSAGES
# - Purpose: Max count of recent messages included in agent context.
# - Used by: `agent_utils.run_agent`.
# - Rationale: Improves focus and reduces token use.
AGENT_HISTORY_LIMIT_MESSAGES = 10

# AGENT_MESSAGE_TRUNCATE_TOKENS
# - Purpose: Truncate any single history message exceeding this token count.
# - Used by: `agent_utils.run_agent`.
# - Rationale: Prevent one message from dominating context budget.
AGENT_MESSAGE_TRUNCATE_TOKENS = 25000

# AGENT_RESUMMARY_THRESHOLD_TOKENS
# - Purpose: If combined chunk summaries exceed this, re-summarize to a smaller digest.
# - Used by: `agent_utils.run_agent`.
# - Rationale: Keep multi-chunk summaries within safe context.
AGENT_RESUMMARY_THRESHOLD_TOKENS = 50000

# AGENT_MAX_PARALLEL_CHUNKS
# - Purpose: Concurrency cap for processing chunked work.
# - Used by: `agent_utils.run_agent`.
# - Rationale: Balance throughput with rate limits and memory.
AGENT_MAX_PARALLEL_CHUNKS = 10

# CONCURRENCY_TOLERANCE
# - Purpose: Allowed relative error when classifying sync vs. async tool execution from timings.
# - Used by: `agent_utils` concurrency detection logic.
# - Rationale: Real-world timings are noisy; tolerance reduces false classifications.
CONCURRENCY_TOLERANCE = 0.2

# MAX_CHUNK_TOKENS_CAP
# - Purpose: Absolute upper bound for chunk size regardless of model/context.
# - Used by: `token_utils.TokenManager.chunk_content()`.
# - Rationale: Safety guard against pathological sizes.
# - Interactions: In `TokenManager.chunk_content()`: `chunk_size_tokens = min(self.max_chunk_tokens, MAX_CHUNK_TOKENS_CAP)`
MAX_CHUNK_TOKENS_CAP = 20000

# Memory scoring algorithm weights
# MEMORY_SIMILARITY_WEIGHT / MEMORY_IMPORTANCE_WEIGHT / MEMORY_RECENCY_WEIGHT
# - Purpose: Weights for base memory ranking.
# - Used by: `memory_utils.py` scoring pipeline.
# - Rationale: Emphasize semantic match while accounting for importance and freshness.
MEMORY_SIMILARITY_WEIGHT = 0.6
MEMORY_IMPORTANCE_WEIGHT = 0.3
MEMORY_RECENCY_WEIGHT = 0.1
# MEMORY_CONTEXT_SIMILARITY_WEIGHT / MEMORY_IMPORTANCE_CONTEXT_WEIGHT / MEMORY_RECENCY_DAYS_DIVISOR
# - Purpose: Weights for context-specific scoring and recency normalization.
# - Used by: `memory_utils.py` scoring pipeline.
# - Rationale: Tailor results to current conversation context.
MEMORY_CONTEXT_SIMILARITY_WEIGHT = 0.7
MEMORY_IMPORTANCE_CONTEXT_WEIGHT = 0.3
MEMORY_RECENCY_DAYS_DIVISOR = 30.0

# DEFAULT_IMPORTANCE_SCORE
# - Purpose: Fallback importance when LLM omits value.
# - Used by: `memory_utils` during storage.
# - Rationale: Midpoint default to avoid biasing ranking extremes.
DEFAULT_IMPORTANCE_SCORE = 0.5
# DEFAULT_CONFIDENCE_SCORE
# - Purpose: Fallback extraction confidence when LLM omits value.
# - Used by: `memory_utils` metadata.
# - Rationale: Conservative default implies "unknown" rather than overstated confidence.
DEFAULT_CONFIDENCE_SCORE = 0.0
# DEFAULT_MESSAGE_COUNT / DEFAULT_TOTAL_STEPS / DEFAULT_TOTAL_TOKENS
# - Purpose: Initialize counters in agent/telemetry metadata.
# - Used by: Views and agent flows when creating new records.
# - Rationale: Explicit zeros over None for simpler math/analytics.
DEFAULT_MESSAGE_COUNT = 0
DEFAULT_TOTAL_STEPS = 0
DEFAULT_TOTAL_TOKENS = 0
# DEFAULT_EMBEDDING_DIMENSIONS
# - Purpose: Placeholder dimensionality when provider doesn't return size.
# - Used by: Embedding storage paths.
# - Rationale: Avoids null field issues.
DEFAULT_EMBEDDING_DIMENSIONS = 0
# MEMORY_EXTRACTION_MODEL_DEFAULT
# - Purpose: Default model for memory extraction over conversation pairs.
# - Used by: `llm.call_llm_conversation_memory_extraction(model=...)` default arg; referenced by `memory_utils`.
# - Rationale: Efficient model with good JSON adherence.
MEMORY_EXTRACTION_MODEL_DEFAULT = "gpt-4o-mini"

# Text processing and display limits
# MAX_MEMORY_DISPLAY_CHARS / MEMORY_TRUNCATE_CHARS
# - Purpose: Limit preview size for displayed memory content.
# - Used by: Views and admin/UI serializers.
# - Rationale: Keep list views readable; reserve 3 chars for ellipsis.
MAX_MEMORY_DISPLAY_CHARS = 100
MEMORY_TRUNCATE_CHARS = 97
# MAX_MEMORY_TITLE_CHARS / MAX_MEMORIES_IN_CONTEXT / CONVERSATION_HISTORY_RECENT_LIMIT
# - Purpose: Control title lengths, number of memories injected, and short history window.
# - Used by: Views and prompt builders.
# - Rationale: Concise UI and focused prompts.
MAX_MEMORY_TITLE_CHARS = 50
MAX_MEMORIES_IN_CONTEXT = 8
CONVERSATION_HISTORY_RECENT_LIMIT = 20

# =============================================================================
# TIKTOKEN ENCODING MODEL MAPPING
# Maps OpenAI API model names to their corresponding tiktoken encoding models
# Tiktoken uses different encoding names than the API model names
# =============================================================================
# TIKTOKEN_MODEL_MAPPING: API model -> tiktoken encoding name
# - Purpose: Ensure correct encodings are used for token counting.
# - Used by: `token_utils.TokenManager`.
# - Rationale: Some API models share encodings; mapping improves accuracy.
# - Interactions: In `TokenManager.__init__`: `self.tiktoken_model = TIKTOKEN_MODEL_MAPPING.get(model, DEFAULT_TIKTOKEN_MODEL)` then `tiktoken.encoding_for_model(self.tiktoken_model)`
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

# DEFAULT_TIKTOKEN_MODEL: fallback encoding if API model not found in mapping.
# - Purpose: Safe default encoder selection.
# - Used by: `token_utils.TokenManager`.
# - Rationale: GPT-4o encoding is broadly compatible.
# - Interactions: Used via `TIKTOKEN_MODEL_MAPPING.get(..., DEFAULT_TIKTOKEN_MODEL)` in `TokenManager.__init__`
DEFAULT_TIKTOKEN_MODEL = "gpt-4o"

# Debug and logging settings
# DEBUG_PREVIEW_CHARS / LOG_MESSAGE_PREVIEW_CHARS / AGENT_RESPONSE_PREVIEW_CHARS
# - Purpose: Truncate debug payloads in logs and admin to keep storage and noise low.
# - Used by: `views/views.py` and admin/debug utilities.
# - Rationale: Prevent massive strings from polluting logs/DB.
# - Interactions:
#   In `views/views.py:MessageListCreateView.post()`
#   - Query preview when retrieving memories:
#     `logger.info(f"[ENHANCED RAG] ... '{user_message[:LOG_MESSAGE_PREVIEW_CHARS]}...'")`
#   - Final prompt preview:
#     `logger.debug(f"[PROMPT BUILDING] Final prompt preview: {enhanced_prompt[:DEBUG_PREVIEW_CHARS]}...")`
#   - Agent response preview:
#     `logger.info(f"[AGENT MODE] Agent finished with response: {final_response[:AGENT_RESPONSE_PREVIEW_CHARS]}...")`
DEBUG_PREVIEW_CHARS = 500
LOG_MESSAGE_PREVIEW_CHARS = 100
AGENT_RESPONSE_PREVIEW_CHARS = 200

# Audio processing settings
# MIN_AUDIO_SIZE_BYTES
# - Purpose: Reject empty/invalid recordings early by minimum byte size.
# - Used by: `views/views.py` transcription endpoint.
# - Rationale: Avoids unnecessary API calls and errors.
MIN_AUDIO_SIZE_BYTES = 1024
# AUDIO_SEEK_END_POSITION
# - Purpose: os.SEEK_END constant used for in-memory file size checks.
# - Used by: `llm.call_llm_transcribe_memory()`.
# - Rationale: Cross-platform clarity without importing os in constants.
AUDIO_SEEK_END_POSITION = 2

# System constants
# MS_CONVERSION_FACTOR
# - Purpose: Convert seconds to milliseconds for latency metrics.
# - Used by: `llm.call_llm_text()` and other timing calculations.
# - Rationale: Centralized conversion to keep code readable.
MS_CONVERSION_FACTOR = 1000
