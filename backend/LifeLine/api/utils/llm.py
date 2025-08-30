import inspect
import logging
import os
import traceback
from typing import Optional

from openai import OpenAI
from openai import OpenAIError

# Configure logging with filename and line numbers
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
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


# Initialize client lazily to avoid issues during Django admin operations
client = None


def get_openai_client():
    """Get or initialize the OpenAI client."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIError("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return client


def _log_call_info(func_name: str, **kwargs):
    """Log function call with caller information."""
    frame = inspect.currentframe().f_back.f_back
    filename = frame.f_code.co_filename.split("/")[-1]
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
    _log_call_info("call_llm_text", model=model, prompt_length=len(prompt), temperature=temperature)

    try:
        client = get_openai_client()
        logger.info(f"Making OpenAI API call - Model: {model}, Prompt length: {len(prompt)} chars")

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        response_text = response.choices[0].message.content
        token_usage = response.usage

        logger.info(
            f"LLM response received - Length: {len(response_text)} chars, "
            f"Tokens used: {token_usage.total_tokens} (prompt: {token_usage.prompt_tokens}, "
            f"completion: {token_usage.completion_tokens})"
        )

        return response_text

    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"LLM API call failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")

        if "budget" in error_msg or "quota" in error_msg or "billing" in error_msg:
            logger.error(f"API budget/quota exceeded for model {model}")
            raise APIBudgetError("API budget exceeded. Please try again later.")
        elif "model" in error_msg and ("available" in error_msg or "exist" in error_msg):
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
    _log_call_info("call_llm_transcribe", model=model, file_path=audio_file_path)

    try:
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        file_size = os.path.getsize(audio_file_path)
        logger.info(f"Transcribing audio file - Path: {audio_file_path}, Size: {file_size} bytes, Model: {model}")

        client = get_openai_client()
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model=model, file=audio_file)

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
    _log_call_info("call_llm_transcribe_memory", model=model, file_name=getattr(audio_file, "name", "unknown"))

    try:
        # Get file size if possible
        current_pos = audio_file.tell()
        audio_file.seek(0, 2)  # Seek to end
        file_size = audio_file.tell()
        audio_file.seek(current_pos)  # Reset position

        logger.info(f"Transcribing audio from memory - Size: {file_size} bytes, Model: {model}")

        client = get_openai_client()
        transcript = client.audio.transcriptions.create(model=model, file=audio_file)

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
    _log_call_info("call_llm_TTS", model=model, voice=voice, text_length=len(text))

    try:
        logger.info(f"Converting text to speech - Model: {model}, Voice: {voice}, Text length: {len(text)} chars")

        client = get_openai_client()
        response = client.audio.speech.create(model=model, input=text, voice=voice, response_format="mp3")

        logger.info(f"Text-to-speech conversion successful")
        return response

    except Exception as e:
        logger.error(f"Text-to-speech conversion failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise AudioProcessingError(f"Failed to convert text to speech: {e}")


def call_llm_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """
    Generate embeddings for text using OpenAI's embedding API.

    Args:
        text: The text to embed
        model: The embedding model to use

    Returns:
        The embedding vector as a list of floats

    Raises:
        LLMError: If embedding generation fails
    """
    _log_call_info("call_llm_embedding", model=model, text_length=len(text))

    try:
        logger.info(f"Generating embedding - Model: {model}, Text length: {len(text)} chars")

        client = get_openai_client()
        response = client.embeddings.create(model=model, input=text)

        embedding = response.data[0].embedding
        logger.info(f"Embedding generated successfully - Dimensions: {len(embedding)}")

        return embedding

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise LLMError(f"Failed to generate embedding: {e}")


def call_llm_conversation_memory_extraction(user_message: str, ai_response: str, current_date: str = None, model: str = "gpt-4o-mini") -> dict:
    """
    Extract memorable information from a conversation pair (user question + AI response).
    Focuses on actionable items, deadlines, and important context with clear dates.

    Args:
        user_message: The user's message/question
        ai_response: The AI's response
        current_date: Current date for context (YYYY-MM-DD format)
        model: The model to use for extraction

    Returns:
        Dict containing extracted memory information or None if no memory found

    Raises:
        LLMError: If memory extraction fails
    """
    from datetime import datetime
    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")
    
    _log_call_info("call_llm_conversation_memory_extraction", model=model, 
                   content_length=len(user_message) + len(ai_response))

    extraction_prompt = f"""
Analyze this conversation pair and extract memorable information, focusing on actionable items and important context.

Current date: {current_date}

User: {user_message}
AI: {ai_response}

Look for:
- Actionable items, tasks, or deadlines mentioned in the AI response
- Important personal information revealed in the conversation
- Goals, preferences, or decisions made
- Scheduled events, meetings, or commitments
- Key insights or important facts that should be remembered

Prioritize memories that:
1. Have clear actionable items with dates/deadlines
2. Contain important personal context
3. Include decisions or commitments made
4. Reference future events or scheduled items

If you find memorable information, respond with a JSON object:
{{
    "has_memory": true,
    "title": "Brief, clear title (include date if relevant)",
    "content": "The memorable information with full context and dates",
    "memory_type": "actionable|personal|preference|goal|event|decision",
    "importance_score": 0.0-1.0,
    "tags": ["relevant", "tags", "dates"],
    "confidence": 0.0-1.0,
    "has_deadline": true/false,
    "deadline_date": "YYYY-MM-DD" or null,
    "is_actionable": true/false
}}

If no memorable information is found, respond with:
{{
    "has_memory": false
}}

Only extract memories that would be genuinely useful to remember later.
"""

    try:
        logger.info(f"Extracting memory from conversation pair - User: {len(user_message)} chars, AI: {len(ai_response)} chars")

        response = call_llm_text(extraction_prompt, model=model, temperature=0.1)

        # Try to parse the JSON response
        import json

        try:
            memory_data = json.loads(response)
            logger.info(f"Conversation memory extraction successful - Has memory: {memory_data.get('has_memory', False)}")
            if memory_data.get('has_memory'):
                logger.info(f"Memory type: {memory_data.get('memory_type')}, Actionable: {memory_data.get('is_actionable')}, Deadline: {memory_data.get('deadline_date')}")
            return memory_data
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse conversation memory extraction response as JSON: {response}")
            return {"has_memory": False}

    except Exception as e:
        logger.error(f"Conversation memory extraction failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise LLMError(f"Failed to extract conversation memory: {e}")


def call_llm_memory_extraction(message_content: str, model: str = "gpt-4o-mini") -> dict:
    """
    Extract memorable information from a message using LLM.

    Args:
        message_content: The message content to analyze
        model: The model to use for extraction

    Returns:
        Dict containing extracted memory information or None if no memory found

    Raises:
        LLMError: If memory extraction fails
    """
    _log_call_info("call_llm_memory_extraction", model=model, content_length=len(message_content))

    extraction_prompt = f"""
    Analyze the following message and determine if it contains any information worth remembering about the user.
    Look for:
    - Personal information (name, age, location, job, relationships, etc.)
    - Preferences (likes, dislikes, interests, hobbies)
    - Goals or objectives
    - Important facts or insights
    - Context that might be useful later

    If you find memorable information, respond with a JSON object containing:
    {{
        "has_memory": true,
        "title": "Brief title for the memory",
        "content": "The memorable information extracted",
        "memory_type": "personal|preference|goal|insight|fact|context",
        "importance_score": 0.0-1.0,
        "tags": ["tag1", "tag2"],
        "confidence": 0.0-1.0
    }}

    If no memorable information is found, respond with:
    {{
        "has_memory": false
    }}

    Message to analyze:
    {message_content}
    """

    try:
        logger.info(f"Extracting memory from single message - Length: {len(message_content)} chars (Consider using conversation pair extraction instead)")

        response = call_llm_text(extraction_prompt, model=model, temperature=0.1)

        # Try to parse the JSON response
        import json

        try:
            memory_data = json.loads(response)
            logger.info(f"Memory extraction successful - Has memory: {memory_data.get('has_memory', False)}")
            return memory_data
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse memory extraction response as JSON: {response}")
            return {"has_memory": False}

    except Exception as e:
        logger.error(f"Memory extraction failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise LLMError(f"Failed to extract memory: {e}")
