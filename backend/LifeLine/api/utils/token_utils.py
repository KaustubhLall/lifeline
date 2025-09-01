"""
Token counting utilities using tiktoken for accurate token management.
"""
import logging
import tiktoken
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

from .constants import (
    MODEL_CONTEXT_LIMITS,
    TIKTOKEN_MODEL_MAPPING,
    DEFAULT_TIKTOKEN_MODEL,
    TOKEN_SAFETY_MARGIN,
    MIN_RESPONSE_TOKENS,
    SYSTEM_PROMPT_BUFFER_TOKENS,
    AGENT_MAX_CHUNK_TOKENS,
    AGENT_MODERATE_CONTENT_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    MAX_CHUNK_TOKENS_CAP,
)

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages token counting and chunking with tiktoken for accurate token management."""
    
    def __init__(self, model: str):
        self.model = model
        self.context_limit = MODEL_CONTEXT_LIMITS.get(model, 128000)  # Default to 128k
        self.tiktoken_model = TIKTOKEN_MODEL_MAPPING.get(model, DEFAULT_TIKTOKEN_MODEL)
        
        try:
            self.encoding = tiktoken.encoding_for_model(self.tiktoken_model)
        except KeyError:
            logger.warning(f"[TokenManager] Unknown model {self.tiktoken_model}, using default encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Calculate safe limits with margin
        self.safe_context_limit = int(self.context_limit * (1 - TOKEN_SAFETY_MARGIN))
        self.max_chunk_tokens = min(AGENT_MAX_CHUNK_TOKENS, self.safe_context_limit // 4)
        self.moderate_content_tokens = AGENT_MODERATE_CONTENT_TOKENS
        
        logger.info(f"[TokenManager] Initialized for {model}: context={self.context_limit}, safe_limit={self.safe_context_limit}, max_chunk={self.max_chunk_tokens}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        if not text:
            return 0
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"[TokenManager] Error counting tokens: {e}")
            # Fallback to rough estimation (4 chars per token)
            return len(text) // 4
    
    def count_message_tokens(self, messages: List[BaseMessage]) -> int:
        """Count tokens in a list of messages."""
        total_tokens = 0
        for message in messages:
            # Add tokens for message content
            if hasattr(message, 'content') and message.content:
                total_tokens += self.count_tokens(message.content)
            
            # Add overhead tokens for message structure (role, etc.)
            total_tokens += 4  # Approximate overhead per message
        
        return total_tokens
    
    def get_available_tokens(self, system_tokens: int = 0, history_tokens: int = 0) -> int:
        """Calculate available tokens for content processing."""
        used_tokens = (
            system_tokens + 
            history_tokens + 
            MIN_RESPONSE_TOKENS + 
            SYSTEM_PROMPT_BUFFER_TOKENS
        )
        
        available = self.safe_context_limit - used_tokens
        logger.info(f"[TokenManager] Token calculation: safe_limit={self.safe_context_limit}, used={used_tokens} (system={system_tokens}, history={history_tokens}), available={available}")
        
        # Ensure we always have at least some tokens available for processing
        # If calculation shows 0 or negative, provide minimum viable chunk size
        if available <= 0:
            logger.warning(f"[TokenManager] Insufficient available tokens ({available}), using emergency minimum")
            return min(5000, self.safe_context_limit // 10)  # Emergency fallback
        
        return available
    
    def should_chunk_content(self, content: str, system_tokens: int = 0, history_tokens: int = 0) -> bool:
        """Determine if content needs to be chunked."""
        content_tokens = self.count_tokens(content)
        available_tokens = self.get_available_tokens(system_tokens, history_tokens)
        
        return content_tokens > available_tokens or content_tokens > self.max_chunk_tokens
    
    def should_summarize_moderate_content(self, content: str) -> bool:
        """Determine if moderate content should be summarized."""
        return self.count_tokens(content) > self.moderate_content_tokens
    
    def chunk_content(self, content: str, system_tokens: int = 0, history_tokens: int = 0) -> List[str]:
        """Chunk content into token-safe pieces with overlap."""
        content_tokens = self.count_tokens(content)
        available_tokens = self.get_available_tokens(system_tokens, history_tokens)
        
        # Use a more conservative approach - ignore system/history for chunking
        # Focus on making chunks that fit within our max chunk size
        chunk_size_tokens = min(self.max_chunk_tokens, MAX_CHUNK_TOKENS_CAP)  # Use centralized cap
        
        if chunk_size_tokens <= CHUNK_OVERLAP_TOKENS:
            logger.error(f"[TokenManager] Insufficient tokens for chunking: {chunk_size_tokens}")
            # Emergency fallback - create very small chunks
            chunk_size_tokens = 5000
            logger.info(f"[TokenManager] Using emergency chunk size: {chunk_size_tokens}")
        
        # Adjust chunk size to account for overlap
        effective_chunk_tokens = max(chunk_size_tokens - CHUNK_OVERLAP_TOKENS, 1000)  # Minimum 1k effective tokens
        
        chunks = []
        tokens_processed = 0
        
        while tokens_processed < content_tokens:
            # Calculate character positions based on token positions
            start_char = self._token_position_to_char(content, tokens_processed)
            end_char = self._token_position_to_char(content, tokens_processed + effective_chunk_tokens)
            
            chunk = content[start_char:end_char]
            
            # Add overlap from previous chunk if not the first chunk
            if chunks and tokens_processed > 0:
                overlap_tokens = min(CHUNK_OVERLAP_TOKENS, tokens_processed)
                overlap_start_char = self._token_position_to_char(content, tokens_processed - overlap_tokens)
                overlap = content[overlap_start_char:start_char]
                chunk = overlap + chunk
            
            chunks.append(chunk)
            tokens_processed += effective_chunk_tokens
            
            # Safety check to prevent infinite loops
            if len(chunks) > 50:
                logger.warning(f"[TokenManager] Too many chunks ({len(chunks)}), stopping")
                break
        
        logger.info(f"[TokenManager] Chunked {content_tokens} tokens into {len(chunks)} chunks")
        return chunks
    
    def chunk_content_with_size(self, content: str, chunk_size_tokens: int) -> List[str]:
        """Chunk content using a specific chunk size in tokens."""
        content_tokens = self.count_tokens(content)
        
        if content_tokens <= chunk_size_tokens:
            return [content]
        
        # Adjust chunk size to account for overlap
        effective_chunk_tokens = max(chunk_size_tokens - CHUNK_OVERLAP_TOKENS, 1000)
        
        chunks = []
        tokens_processed = 0
        
        while tokens_processed < content_tokens:
            # Calculate character positions based on token positions
            start_char = self._token_position_to_char(content, tokens_processed)
            end_char = self._token_position_to_char(content, tokens_processed + effective_chunk_tokens)
            
            chunk = content[start_char:end_char]
            
            if not chunk.strip():
                break
            
            chunks.append(chunk)
            tokens_processed += effective_chunk_tokens
            
            # Safety check to prevent infinite loops
            if len(chunks) > 100:
                logger.warning(f"[TokenManager] Too many chunks ({len(chunks)}), stopping")
                break
        
        logger.info(f"[TokenManager] Chunked {content_tokens} tokens into {len(chunks)} chunks using {chunk_size_tokens} token chunks")
        return chunks
    
    def _token_position_to_char(self, text: str, token_position: int) -> int:
        """Convert token position to character position (approximate)."""
        if token_position <= 0:
            return 0
        
        # Use tiktoken to get accurate position
        try:
            tokens = self.encoding.encode(text)
            if token_position >= len(tokens):
                return len(text)
            
            # Decode up to the token position to get character position
            partial_tokens = tokens[:token_position]
            partial_text = self.encoding.decode(partial_tokens)
            return len(partial_text)
        
        except Exception as e:
            logger.error(f"[TokenManager] Error converting token position: {e}")
            # Fallback to rough estimation
            return min(token_position * 4, len(text))
    
    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        if not text:
            return text
        
        current_tokens = self.count_tokens(text)
        if current_tokens <= max_tokens:
            return text
        
        # Use tiktoken for accurate truncation
        try:
            tokens = self.encoding.encode(text)
            truncated_tokens = tokens[:max_tokens]
            return self.encoding.decode(truncated_tokens)
        except Exception as e:
            logger.error(f"[TokenManager] Error truncating text: {e}")
            # Fallback to character-based truncation
            estimated_chars = max_tokens * 4
            return text[:estimated_chars]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration."""
        return {
            "model": self.model,
            "tiktoken_model": self.tiktoken_model,
            "context_limit": self.context_limit,
            "safe_context_limit": self.safe_context_limit,
            "max_chunk_tokens": self.max_chunk_tokens,
            "moderate_content_tokens": self.moderate_content_tokens,
            "safety_margin": TOKEN_SAFETY_MARGIN,
        }


def create_token_manager(model: str) -> TokenManager:
    """Factory function to create a TokenManager for a specific model."""
    return TokenManager(model)
