import inspect
import logging
import os
import traceback
from typing import Optional

from openai import OpenAI

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


def call_llm_text(prompt: str, model: str = "gpt-4.1-nano", temperature: float = 0.0) -> str:
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


def call_llm_transcribe(audio_file_path: str, model: str = "gpt-4o-mini-transcribe") -> str:
    """
    Transcribe audio to text.

    Args:
        audio_file_path: Path to the audio file
        model: The model to use for transcription (default: gpt-4o-mini-transcribe)

    Returns:
        The transcribed text

    Raises:
        AudioProcessingError: If audio processing fails
        FileNotFoundError: If the audio file is not found
    """
    _log_call_info('call_llm_transcribe', model=model, file_path=audio_file_path)

    try:
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        file_size = os.path.getsize(audio_file_path)
        logger.info(f"Transcribing audio file - Path: {audio_file_path}, Size: {file_size} bytes, Model: {model}")

        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file
            )

        transcribed_text = transcript.text
        logger.info(f"Audio transcription successful - Text length: {len(transcribed_text)} chars")
        logger.debug(f"Transcribed text preview: {transcribed_text[:100]}...")

        return transcribed_text

    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise AudioProcessingError(f"Failed to transcribe audio: {e}")


def call_llm_transcribe_memory(audio_file, model: str = "gpt-4o-mini-transcribe") -> str:
    """
    Transcribe audio to text using in-memory file object.

    Args:
        audio_file: File-like object containing audio data
        model: The model to use for transcription (default: gpt-4o-mini-transcribe)

    Returns:
        The transcribed text

    Raises:
        AudioProcessingError: If audio processing fails
    """
    _log_call_info('call_llm_transcribe_memory', model=model, file_name=getattr(audio_file, 'name', 'unknown'))

    try:
        # Get file size if possible
        current_pos = audio_file.tell()
        audio_file.seek(0, 2)  # Seek to end
        file_size = audio_file.tell()
        audio_file.seek(current_pos)  # Reset position

        logger.info(f"Transcribing audio from memory - Size: {file_size} bytes, Model: {model}")

        transcript = client.audio.transcriptions.create(
            model=model,
            file=audio_file
        )

        transcribed_text = transcript.text
        logger.info(f"Audio transcription successful - Text length: {len(transcribed_text)} chars")
        logger.debug(f"Transcribed text preview: {transcribed_text[:100]}...")

        return transcribed_text

    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise AudioProcessingError(f"Failed to transcribe audio: {e}")


def call_llm_TTS(text: str, model: str = "tts-1", voice: str = "alloy") -> Optional[bytes]:
    """
    Convert text to speech.

    Args:
        text: The text to convert
        model: The TTS model to use
        voice: The voice to use

    Returns:
        The audio data as bytes

    Raises:
        AudioProcessingError: If TTS processing fails
    """
    _log_call_info('call_llm_TTS', model=model, voice=voice, text_length=len(text))

    try:
        logger.info(f"Converting text to speech - Model: {model}, Voice: {voice}, Text length: {len(text)} chars")

        response = client.audio.speech.create(
            model=model,
            input=text,
            voice=voice,
            response_format="mp3"
        )

        logger.info(f"Text-to-speech conversion successful")
        return response

    except Exception as e:
        logger.error(f"Text-to-speech conversion failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise AudioProcessingError(f"Failed to convert text to speech: {e}")
