import base64
import io
import logging
import time
from threading import Thread

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.chat import Conversation, Message, MessageNote, Memory, PromptDebug
from ..serializers import MemorySerializer, MemoryCreateSerializer
from ..utils.llm import call_llm_text, APIBudgetError, ModelNotAvailableError, LLMError
from ..utils.memory_utils import (
    extract_and_store_memory,
    get_relevant_memories,
    generate_memory_context,
    get_conversation_memories,
)
from ..utils.prompts import build_enhanced_prompt, get_system_prompt, validate_mode

# Configure logging with filename and line numbers
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)
logger = logging.getLogger(__name__)
User = get_user_model()


def _log_request_info(request, action, **kwargs):
    """Log request information with client details."""
    client_ip = request.META.get("REMOTE_ADDR", "unknown")
    user_agent = request.META.get("HTTP_USER_AGENT", "unknown")
    user_info = (
        f"User: {request.user.username} (ID: {request.user.id})"
        if hasattr(request, "user") and request.user.is_authenticated
        else "Anonymous"
    )
    logger.info(f"{action} - {user_info} from {client_ip} - {kwargs}")


def async_memory_extraction(message_id, user_id):
    """Background task to extract memory from a message."""
    try:
        message = Message.objects.get(id=message_id)
        user = User.objects.get(id=user_id)

        # Call the synchronous function directly
        extract_and_store_memory(message, user)

    except Exception as e:
        logger.error(f"Background memory extraction failed for message {message_id}: {str(e)}")


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _log_request_info(request, "Fetching conversations")

        try:
            # Filter out archived conversations by default
            show_archived = request.query_params.get("show_archived", "false").lower() == "true"
            conversations = Conversation.objects.filter(user=request.user, is_archived=show_archived).order_by(
                "-updated_at"
            )

            data = [
                {
                    "id": c.id,
                    "title": c.title or f"Chat {c.id}",
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "message_count": c.messages.count(),
                    "last_message": c.messages.last().content if c.messages.exists() else None,
                }
                for c in conversations
            ]

            logger.info(f"Retrieved {len(data)} conversations for user {request.user.username}")
            return Response(data)

        except Exception as e:
            logger.error(f"Error fetching conversations for user {request.user.username}: {str(e)}", exc_info=True)
            return Response({"detail": "Failed to fetch conversations"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        _log_request_info(request, "Creating new conversation", data=request.data)

        try:
            title = request.data.get("title", "")
            model = request.data.get("model", "gpt-4.1-nano")
            mode = request.data.get("mode", "conversational")

            # Create new conversation
            conversation = Conversation.objects.create(
                user=request.user,
                title=title or f"Chat {Conversation.objects.filter(user=request.user).count() + 1}",
                context={"created_at": str(timezone.now()), "model": model, "mode": mode},
            )

            logger.info(
                f"Created new conversation {conversation.id} for user {request.user.username} - Model: {model}, Mode: {mode}"
            )

            # Get the conversation data in the same format as GET response
            data = {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "message_count": 0,
                "last_message": None,
            }

            return Response(data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating conversation for user {request.user.username}: {str(e)}", exc_info=True)
            return Response({"detail": "Failed to create conversation"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        _log_request_info(request, f"Fetching conversation details", conversation_id=conversation_id)

        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        logger.info(f"Retrieved conversation {conversation_id} details for user {request.user.username}")

        return Response(
            {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "is_archived": conversation.is_archived,
                "context": conversation.context,
            }
        )

    def patch(self, request, conversation_id):
        _log_request_info(request, f"Updating conversation", conversation_id=conversation_id, data=request.data)

        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)

        updated_fields = []
        if "title" in request.data:
            conversation.title = request.data["title"]
            updated_fields.append("title")
        if "is_archived" in request.data:
            conversation.is_archived = request.data["is_archived"]
            updated_fields.append("is_archived")

        conversation.save()
        logger.info(f"Updated conversation {conversation_id} fields: {updated_fields} for user {request.user.username}")

        return Response({"status": "updated"})

    def delete(self, request, conversation_id):
        _log_request_info(request, f"Deleting conversation", conversation_id=conversation_id)

        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        conversation.delete()

        logger.info(f"Deleted conversation {conversation_id} for user {request.user.username}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        _log_request_info(request, f"Fetching messages", conversation_id=conversation_id)

        try:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            messages = conversation.messages.all()

            data = [
                {
                    "id": m.id,
                    "sender": m.sender_id,
                    "content": m.content,
                    "created_at": m.created_at,
                    "is_bot": m.is_bot,
                    "role": m.role,
                    "metadata": m.metadata,
                }
                for m in messages
            ]

            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return Response(data)

        except Exception as e:
            logger.error(f"Error fetching messages for conversation {conversation_id}: {str(e)}", exc_info=True)
            return Response({"detail": "Failed to fetch messages"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, conversation_id):
        _log_request_info(
            request,
            f"Processing new message",
            conversation_id=conversation_id,
            message_length=len(request.data.get("content", "")),
            model=request.data.get("model", "unknown"),
            mode=request.data.get("mode", "unknown"),
        )

        try:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            user_message = request.data.get("content")
            model = request.data.get("model", "gpt-4.1-nano")
            mode = request.data.get("mode", "conversational")

            logger.info(
                f"Processing message for conversation {conversation_id} - User: {request.user.username}, Model: {model}, Mode: {mode}, Length: {len(user_message) if user_message else 0}"
            )

            if not user_message:
                logger.warning("Attempted to send empty message")
                return Response({"detail": "Message content required"}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"[ENHANCED RAG] Starting enhanced conversation processing for user {request.user.username}")

            # Get relevant memories using enhanced RAG
            logger.info(f"[ENHANCED RAG] Retrieving relevant memories for query: '{user_message[:100]}...'")
            relevant_memories = get_relevant_memories(
                user=request.user,
                query=user_message,
                limit=5,  # Increased from 3 for better context
                min_similarity=0.3,  # FIXED: Lowered from 0.6 to 0.3 for better recall
            )

            # Get conversation-specific memories
            conversation_memories = get_conversation_memories(user=request.user, conversation=conversation, limit=3)

            # Combine and deduplicate memories
            all_memories = list({m.id: m for m in (relevant_memories + conversation_memories)}.values())
            logger.info(
                f"[ENHANCED RAG] Combined {len(all_memories)} unique memories (relevant: {len(relevant_memories)}, conversation: {len(conversation_memories)})"
            )

            # Get conversation history with token counting
            logger.info(f"[CONVERSATION HISTORY] Retrieving conversation history with 10,000 token limit")
            all_messages = list(conversation.messages.order_by("created_at"))

            # Convert messages to dictionary format for token counting
            message_history = []
            for msg in all_messages:
                message_dict = {
                    "role": msg.role,
                    "content": (
                        msg.raw_user_input if msg.raw_user_input else msg.content
                    ),  # Use original user input for history
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "is_bot": msg.is_bot,
                }
                message_history.append(message_dict)

            # Validate chat mode
            if not validate_mode(mode):
                logger.warning(f"[PROMPT BUILDING] Invalid chat mode '{mode}', falling back to 'conversational'")
                mode = "conversational"

            # Build enhanced prompt with all context
            logger.info(
                f"[PROMPT BUILDING] Building enhanced prompt with mode='{mode}', {len(all_memories)} memories, {len(message_history)} history messages"
            )

            enhanced_prompt = build_enhanced_prompt(
                mode=mode,
                memories=[
                    {
                        "content": m.content,
                        "title": m.title,
                        "memory_type": m.memory_type,
                        "importance_score": m.importance_score,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                        "tags": m.tags or [],
                    }
                    for m in all_memories
                ],
                conversation_history=message_history,
                current_message=user_message,
                user_name=request.user.first_name or request.user.username,
                max_history_tokens=10000,  # Use 10k token limit as requested
            )

            logger.info(f"[PROMPT BUILDING] Enhanced prompt built - Total length: {len(enhanced_prompt)} characters")
            logger.debug(f"[PROMPT BUILDING] Final prompt preview: {enhanced_prompt[:500]}...")

            # Create user message with full prompt stored for debugging
            user_msg = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=user_message,  # Store original user message in content
                raw_user_input=user_message,  # Store original input
                full_prompt=enhanced_prompt,  # Store complete prompt for debugging
                role="user",
                metadata={
                    "model": model,
                    "mode": mode,
                    "memories_included": len(all_memories),
                    "relevant_memories": len(relevant_memories),
                    "conversation_memories": len(conversation_memories),
                    "prompt_length": len(enhanced_prompt),
                    "history_messages_included": len(message_history),
                },
            )

            logger.info(
                f"Created user message {user_msg.id} with full prompt ({len(enhanced_prompt)} chars) in conversation {conversation_id}"
            )

            # Start background memory extraction
            memory_thread = Thread(target=async_memory_extraction, args=(user_msg.id, request.user.id))
            memory_thread.daemon = True
            memory_thread.start()

            # Prepare debug information BEFORE creating debug entry
            system_prompt = get_system_prompt(mode)
            memory_context = generate_memory_context(all_memories)
            from ..utils.prompts import format_conversation_history

            conversation_history_text = format_conversation_history(message_history, 10000)

            logger.info(
                f"[DEBUG PREP] System prompt length: {len(system_prompt)}, Memory context length: {len(memory_context)}, History length: {len(conversation_history_text)}"
            )

            # Initialize debug entry with actual data
            debug_entry = PromptDebug.objects.create(
                user_message=user_msg,
                conversation=conversation,
                full_prompt=enhanced_prompt,
                system_prompt=system_prompt,
                memory_context=memory_context,
                conversation_history=conversation_history_text,
                model_used=model,
                mode_used=mode,
                temperature=0.0,
                prompt_length=len(enhanced_prompt),
                memories_used_count=len(all_memories),
                relevant_memories_count=len(relevant_memories),
                conversation_memories_count=len(conversation_memories),
                history_messages_count=len(message_history),
            )

            logger.info(
                f"[DEBUG ENTRY] Created debug entry {debug_entry.id} with system_prompt: {len(debug_entry.system_prompt)} chars, memory_context: {len(debug_entry.memory_context)} chars, conversation_history: {len(debug_entry.conversation_history)} chars"
            )

            # Agent mode: attempt tool invocation instead of direct LLM if intent matches
            if mode == "agent":
                try:
                    from ..utils.agent_mcp import handle_agent_tools

                    tool_exec = handle_agent_tools(request.user, user_message)
                except Exception as _agent_err:  # pragma: no cover
                    logger.error(f"[AGENT MODE] Tool handling error: {_agent_err}")
                    tool_exec = None

                if tool_exec:
                    tool_metadata = {
                        "model": model,
                        "mode": mode,
                        "agent_tool_operation": tool_exec.get("operation"),
                        "agent_tool_args": tool_exec.get("args"),
                        "agent_tool_raw_result": tool_exec.get("raw_result"),
                        "used_memories": len(all_memories),
                        "relevant_memories": len(relevant_memories),
                        "conversation_memories": len(conversation_memories),
                        "prompt_length": len(enhanced_prompt),
                        "history_messages_included": len(message_history),
                        "debug_entry_id": debug_entry.id,
                    }
                    bot_msg = Message.objects.create(
                        conversation=conversation,
                        sender=request.user,
                        content=tool_exec.get("response_text", "(No response)"),
                        raw_user_input="",
                        full_prompt="",
                        is_bot=True,
                        role="assistant",
                        metadata=tool_metadata,
                    )
                    debug_entry.bot_response = bot_msg
                    debug_entry.response_time_ms = 0
                    debug_entry.save()
                    conversation.context = {
                        **conversation.context,
                        "last_user_message": user_message,
                        "last_bot_response": bot_msg.content,
                        "message_count": conversation.messages.count(),
                        "current_mode": mode,
                        "current_model": model,
                        "agent_last_tool_operation": tool_exec.get("operation"),
                    }
                    conversation.save()
                    return Response(
                        {
                            "id": bot_msg.id,
                            "sender": bot_msg.sender_id,
                            "content": bot_msg.content,
                            "created_at": bot_msg.created_at,
                            "is_bot": True,
                            "role": "assistant",
                            "metadata": bot_msg.metadata,
                        },
                        status=status.HTTP_201_CREATED,
                    )

            try:
                logger.info(f"[LLM CALL] Calling LLM with model={model}, prompt_length={len(enhanced_prompt)}")
                start_time = time.time()

                bot_response = call_llm_text(enhanced_prompt, model=model)

                end_time = time.time()
                response_time_ms = int((end_time - start_time) * 1000)

                logger.info(
                    f"[LLM CALL] Received response - Length: {len(bot_response)} characters, Time: {response_time_ms}ms"
                )

                # Create bot message with full AI response stored
                bot_msg = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=bot_response,  # Store full AI response
                    raw_user_input="",  # No raw input for bot messages
                    full_prompt="",  # No prompt for bot messages (they are responses)
                    is_bot=True,
                    role="assistant",
                    metadata={
                        "model": model,
                        "mode": mode,
                        "used_memories": len(all_memories),
                        "relevant_memories": len(relevant_memories),
                        "conversation_memories": len(conversation_memories),
                        "prompt_length": len(enhanced_prompt),
                        "response_length": len(bot_response),
                        "response_time_ms": response_time_ms,
                        "history_messages_included": len(message_history),
                        "debug_entry_id": debug_entry.id,
                    },
                )

                # Update debug entry with response info
                debug_entry.bot_response = bot_msg
                debug_entry.response_time_ms = response_time_ms
                debug_entry.save()

                logger.info(
                    f"[MESSAGE CREATION] Created bot message {bot_msg.id} with full response and debug entry {debug_entry.id}"
                )

                # Update conversation context with enhanced information
                conversation.context = {
                    "last_user_message": user_message,
                    "last_bot_response": bot_response,
                    "message_count": conversation.messages.count(),
                    "current_mode": mode,
                    "current_model": model,
                    "memories_used": len(all_memories),
                    "last_rag_retrieval": {
                        "relevant_memories": len(relevant_memories),
                        "conversation_memories": len(conversation_memories),
                        "total_memories": len(all_memories),
                        "retrieval_timestamp": str(timezone.now()),
                    },
                    "last_prompt_stats": {
                        "prompt_length": len(enhanced_prompt),
                        "history_messages": len(message_history),
                        "mode_used": mode,
                    },
                    "last_debug_entry_id": debug_entry.id,
                }
                conversation.save()

                logger.info(f"[CONVERSATION UPDATE] Updated conversation {conversation_id} context with enhanced stats")

                return Response(
                    {
                        "id": bot_msg.id,
                        "sender": bot_msg.sender_id,
                        "content": bot_response,
                        "created_at": bot_msg.created_at,
                        "is_bot": True,
                        "role": "assistant",
                        "metadata": bot_msg.metadata,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except APIBudgetError as e:
                debug_entry.api_error = f"APIBudgetError: {str(e)}"
                debug_entry.save()
                logger.error(f"API budget exceeded for conversation {conversation_id}: {str(e)}")
                return Response({"detail": str(e)}, status=status.HTTP_402_PAYMENT_REQUIRED)
            except ModelNotAvailableError as e:
                debug_entry.api_error = f"ModelNotAvailableError: {str(e)}"
                debug_entry.save()
                logger.error(f"Model {model} not available for conversation {conversation_id}: {str(e)}")
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except LLMError as e:
                debug_entry.api_error = f"LLMError: {str(e)}"
                debug_entry.save()
                logger.error(f"LLM error for conversation {conversation_id}: {str(e)}")
                return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            logger.error(f"Error processing message for conversation {conversation_id}: {str(e)}", exc_info=True)
            return Response({"detail": "Failed to process message"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MemoryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _log_request_info(request, "Fetching user memories")

        try:
            # Get pagination parameters
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            memory_type = request.query_params.get("type")
            search_query = request.query_params.get("search")

            # Base queryset
            queryset = Memory.objects.filter(user=request.user)

            # Filter by type if specified
            if memory_type:
                queryset = queryset.filter(memory_type=memory_type)

            # Search functionality
            if search_query:
                relevant_memories = get_relevant_memories(request.user, search_query, limit=100)
                memory_ids = [m.id for m in relevant_memories]
                queryset = queryset.filter(id__in=memory_ids)
            else:
                # Default ordering by recency and importance
                queryset = queryset.order_by("-updated_at", "-importance_score")

            # Paginate results
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            # Serialize memories
            serializer = MemorySerializer(page_obj.object_list, many=True)

            logger.info(
                f"Retrieved {len(serializer.data)} memories (page {page}/{paginator.num_pages}) for user {request.user.username}"
            )

            return Response(
                {
                    "memories": serializer.data,
                    "pagination": {
                        "current_page": page,
                        "total_pages": paginator.num_pages,
                        "total_count": paginator.count,
                        "has_next": page_obj.has_next(),
                        "has_previous": page_obj.has_previous(),
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error fetching memories for user {request.user.username}: {str(e)}", exc_info=True)
            return Response({"detail": "Failed to fetch memories"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        _log_request_info(request, "Creating new memory", data=request.data)

        try:
            serializer = MemoryCreateSerializer(data=request.data)
            if serializer.is_valid():
                # Generate embedding for the memory
                from ..utils.llm import call_llm_embedding

                embedding = call_llm_embedding(serializer.validated_data["content"])

                memory = serializer.save(user=request.user, embedding=embedding, is_auto_extracted=False)

                logger.info(f"Created manual memory {memory.id} for user {request.user.username}")

                response_serializer = MemorySerializer(memory)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error creating memory for user {request.user.username}: {str(e)}", exc_info=True)
            return Response({"detail": "Failed to create memory"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MemoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, memory_id):
        _log_request_info(request, f"Fetching memory details", memory_id=memory_id)

        memory = get_object_or_404(Memory, id=memory_id, user=request.user)

        # Update access tracking
        memory.access_count += 1
        memory.last_accessed = timezone.now()
        memory.save(update_fields=["access_count", "last_accessed"])

        serializer = MemorySerializer(memory)
        logger.info(f"Retrieved memory {memory_id} details for user {request.user.username}")

        return Response(serializer.data)

    def patch(self, request, memory_id):
        _log_request_info(request, f"Updating memory", memory_id=memory_id, data=request.data)

        memory = get_object_or_404(Memory, id=memory_id, user=request.user)

        serializer = MemorySerializer(memory, data=request.data, partial=True)
        if serializer.is_valid():
            # If content changed, regenerate embedding
            if "content" in request.data:
                from ..utils.memory_utils import update_memory_embedding

                update_memory_embedding(memory)

            serializer.save()
            logger.info(f"Updated memory {memory_id} for user {request.user.username}")
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, memory_id):
        _log_request_info(request, f"Deleting memory", memory_id=memory_id)

        memory = get_object_or_404(Memory, id=memory_id, user=request.user)
        memory.delete()

        logger.info(f"Deleted memory {memory_id} for user {request.user.username}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class NoteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id=None):
        _log_request_info(request, f"Fetching notes", message_id=message_id)

        if message_id:
            # Get notes for specific message
            message = get_object_or_404(Message, id=message_id)
            notes = message.notes.all()
            data = [
                {
                    "id": note.id,
                    "content": note.note,
                    "created_at": note.created_at,
                    "created_by": note.created_by.username,
                }
                for note in notes
            ]
            logger.info(f"Retrieved {len(notes)} notes for message {message_id}")
        else:
            # Return empty list since we're transitioning away from UserNote
            data = []
            logger.info(f"Retrieved 0 general notes for user {request.user.username} (deprecated)")

        return Response(data)

    def post(self, request, message_id=None):
        _log_request_info(request, f"Creating note", message_id=message_id, data=request.data)

        content = request.data.get("content")
        if not content:
            logger.warning("Attempted to create note without content")
            return Response({"error": "Note content required."}, status=400)

        if message_id:
            # Create note for specific message
            message = get_object_or_404(Message, id=message_id)
            note = MessageNote.objects.create(message=message, note=content, created_by=request.user)
            logger.info(f"Created message note {note.id} for message {message_id}")

            return Response({"id": note.id, "content": note.note, "created_at": note.created_at}, status=201)
        else:
            # Redirect to memory creation instead of general notes
            return Response(
                {"error": "General notes are deprecated. Please use /memories/ endpoint instead."}, status=400
            )


class TranscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _log_request_info(
            request,
            "Processing audio transcription",
            model=request.data.get("model", "unknown"),
            audio_present=bool(request.data.get("audio")),
        )

        try:
            audio_data = request.data.get("audio")
            model = request.data.get("model", "gpt-4o-mini-transcribe")  # Use newer OpenAI transcription model
            audio_format = request.data.get("format", "webm")

            if not audio_data:
                logger.warning("No audio data provided for transcription")
                return Response({"detail": "Audio data required"}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(
                f"Processing audio transcription request for user {request.user.username} with model {model}, format {audio_format}"
            )

            # Process audio data in memory
            try:
                audio_bytes = base64.b64decode(audio_data)
                audio_size = len(audio_bytes)
                logger.info(f"Processing audio data in memory - Size: {audio_size} bytes")

                # Check minimum file size (1KB minimum to avoid empty recordings)
                if audio_size < 1024:
                    logger.warning(f"Audio file too small: {audio_size} bytes")
                    return Response(
                        {"detail": "Audio recording too short. Please record for at least 1 second."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                audio_file = io.BytesIO(audio_bytes)

                # Set appropriate filename based on format
                if "webm" in audio_format.lower():
                    audio_file.name = "audio.webm"
                elif "wav" in audio_format.lower():
                    audio_file.name = "audio.wav"
                elif "mp4" in audio_format.lower() or "m4a" in audio_format.lower():
                    audio_file.name = "audio.m4a"
                else:
                    audio_file.name = "audio.webm"  # Default fallback

                from ..utils.llm import call_llm_transcribe_memory

                text = call_llm_transcribe_memory(audio_file, model)

                logger.info(
                    f"Successfully transcribed audio for user {request.user.username}, text: '{text}' (length: {len(text)})"
                )
                return Response({"text": text.strip()})

            except Exception as e:
                logger.error(f"Transcription error for user {request.user.username}: {str(e)}", exc_info=True)
                return Response({"detail": "Failed to transcribe audio"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(
                f"Error processing transcription request for user {request.user.username}: {str(e)}", exc_info=True
            )
            return Response(
                {"detail": "Failed to process transcription request"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
