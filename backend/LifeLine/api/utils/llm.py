import inspect
import logging
import os
import traceback
from typing import Optional, Dict, Any, List
import io

from openai import OpenAI
from .prompts import get_system_prompt, get_rag_prompt, count_tokens
from .memory_utils import get_memory_manager

# Configure logging with filename and line numbers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class APIBudgetError(LLMError):
    """Raised when the API budget is exceeded."""
    pass


class ModelNotAvailableError(LLMError):
    """Raised when the requested model is not available."""
    pass


class AudioProcessingError(LLMError):
    """Raised when audio processing fails."""
    pass


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _log_call_info(func_name: str, **kwargs):
    """Log function call with caller information."""
    frame = inspect.currentframe().f_back.f_back
    filename = frame.f_code.co_filename.split('/')[-1]
    line_number = frame.f_lineno
    logger.info(f"[{filename}:{line_number}] Calling {func_name} with params: {kwargs}")


def call_llm_text(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.0) -> str:
    """
    Call the LLM to generate text response.

    Args:
        prompt: The input prompt
        model: The model to use
        temperature: Controls randomness in the response

    Returns:
        The generated text response

    Raises:
        APIBudgetError: If the API budget is exceeded
        ModelNotAvailableError: If the model is not available
        LLMError: For other LLM-related errors
    """
    _log_call_info('call_llm_text', model=model, prompt_length=len(prompt), temperature=temperature)

    try:
        logger.info(f"Making OpenAI API call - Model: {model}, Prompt length: {len(prompt)} chars")

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        response_text = response.choices[0].message.content
        token_usage = response.usage

        logger.info(f"LLM response received - Length: {len(response_text)} chars, "
                    f"Tokens used: {token_usage.total_tokens} (prompt: {token_usage.prompt_tokens}, "
                    f"completion: {token_usage.completion_tokens})")

        return response_text

    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"LLM API call failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")

        if 'budget' in error_msg or 'quota' in error_msg or 'billing' in error_msg:
            logger.error(f"API budget/quota exceeded for model {model}")
            raise APIBudgetError("API budget exceeded. Please try again later.")
        elif 'model' in error_msg and ('available' in error_msg or 'exist' in error_msg):
            logger.error(f"Model {model} not available or doesn't exist")
            raise ModelNotAvailableError(f"Model {model} is not available.")
        else:
            logger.error(f"General LLM error with model {model}: {e}")
            raise LLMError(f"Error generating response: {e}")


def call_llm_with_rag_context(user_id: int, current_message: str, conversation_id: Optional[int] = None,
                             chat_mode: str = "conversational", model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Generate LLM response with RAG context integration.

    Args:
        user_id: ID of the user
        current_message: The user's current message
        conversation_id: Optional conversation ID for context
        chat_mode: Chat mode for system prompt selection
        model: OpenAI model to use

    Returns:
        Dictionary containing response and metadata
    """
    _log_call_info('call_llm_with_rag_context', user_id=user_id,
                   message_length=len(current_message), conversation_id=conversation_id,
                   chat_mode=chat_mode, model=model)

    try:
        # Get memory manager for user
        memory_manager = get_memory_manager(user_id)

        # Build RAG context
        rag_context = memory_manager.build_conversation_context(current_message, conversation_id)

        # Get system prompt
        system_prompt = get_system_prompt(chat_mode)

        # Build RAG-enhanced prompt
        rag_prompt = get_rag_prompt("context_integration").format(**rag_context)

        # Combine system and RAG prompts
        full_prompt = f"{system_prompt}\n\n{rag_prompt}"

        # Count tokens for logging
        prompt_tokens = count_tokens(full_prompt, model)

        logger.info(f"RAG-enhanced prompt prepared - Total tokens: {prompt_tokens}, "
                   f"Memories: {rag_context['memory_count']}, Messages: {rag_context['message_count']}")

        # Call LLM with enhanced prompt
        response = call_llm_text(full_prompt, model=model, temperature=0.7)

        # Return response with metadata
        return {
            "response": response,
            "metadata": {
                "memory_count": rag_context["memory_count"],
                "message_count": rag_context["message_count"],
                "total_context_tokens": rag_context["total_context_tokens"],
                "prompt_tokens": prompt_tokens,
                "chat_mode": chat_mode,
                "model": model
            }
        }

    except Exception as e:
        logger.error(f"Error in RAG-enhanced LLM call: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Fallback to simple LLM call
        try:
            system_prompt = get_system_prompt(chat_mode)
            simple_prompt = f"{system_prompt}\n\nUser: {current_message}\nAssistant:"

            response = call_llm_text(simple_prompt, model=model, temperature=0.7)

            return {
                "response": response,
                "metadata": {
                    "memory_count": 0,
                    "message_count": 0,
                    "total_context_tokens": 0,
                    "prompt_tokens": count_tokens(simple_prompt, model),
                    "chat_mode": chat_mode,
                    "model": model,
                    "fallback": True,
                    "error": str(e)
                }
            }
        except Exception as fallback_error:
            logger.error(f"Fallback LLM call also failed: {fallback_error}")
            raise LLMError(f"Both RAG and fallback LLM calls failed: {e}")


def call_llm_transcribe(audio_file_path: str, model: str = "whisper-1") -> str:
    """
    Transcribe audio using OpenAI Whisper.

    Args:
        audio_file_path: Path to the audio file
        model: Whisper model to use

    Returns:
        Transcribed text

    Raises:
        AudioProcessingError: If transcription fails
    """
    _log_call_info('call_llm_transcribe', audio_file_path=audio_file_path, model=model)

    try:
        logger.info(f"Starting audio transcription - File: {audio_file_path}, Model: {model}")

        with open(audio_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=model,
                file=audio_file
            )

        transcript = response.text
        logger.info(f"Audio transcription completed - Length: {len(transcript)} chars")

        return transcript

    except FileNotFoundError:
        logger.error(f"Audio file not found: {audio_file_path}")
        raise AudioProcessingError(f"Audio file not found: {audio_file_path}")
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise AudioProcessingError(f"Failed to transcribe audio: {e}")


def call_llm_transcribe_memory(audio_file, model: str = "whisper-1") -> str:
    """
    Transcribe audio using OpenAI Whisper from memory (BytesIO object).

    Args:
        audio_file: BytesIO object containing audio data
        model: Whisper model to use

    Returns:
        Transcribed text

    Raises:
        AudioProcessingError: If transcription fails
    """
    _log_call_info('call_llm_transcribe_memory', model=model,
                   audio_size=len(audio_file.getvalue()) if hasattr(audio_file, 'getvalue') else 'unknown')

    try:
        logger.info(f"Starting audio transcription from memory - Model: {model}")

        # Ensure the file pointer is at the beginning
        if hasattr(audio_file, 'seek'):
            audio_file.seek(0)

        response = client.audio.transcriptions.create(
            model=model,
            file=audio_file
        )

        transcript = response.text
        logger.info(f"Audio transcription from memory completed - Length: {len(transcript)} chars")

        return transcript

    except Exception as e:
        logger.error(f"Audio transcription from memory failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise AudioProcessingError(f"Failed to transcribe audio from memory: {e}")


def extract_memories_from_messages(user_id: int, conversation_id: int) -> List[Dict]:
    """
    Extract memories from a conversation using LLM analysis.

    Args:
        user_id: ID of the user
        conversation_id: ID of the conversation to analyze

    Returns:
        List of extracted memories
    """
    _log_call_info('extract_memories_from_messages', user_id=user_id, conversation_id=conversation_id)

    try:
        memory_manager = get_memory_manager(user_id)
        memories = memory_manager.extract_memories_from_conversation(conversation_id)

        logger.info(f"Extracted {len(memories)} memories from conversation {conversation_id}")
        return memories

    except Exception as e:
        logger.error(f"Failed to extract memories from conversation {conversation_id}: {e}")
        return []
