import base64
import io
import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.chat import Conversation, Message, MessageNote, Memory
from ..utils.llm import (call_llm_text, call_llm_with_rag_context, extract_memories_from_messages,
                        APIBudgetError, ModelNotAvailableError, LLMError)
from ..utils.prompts import get_system_prompt
from ..utils.memory_utils import get_memory_manager

# Configure logging with filename and line numbers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)
User = get_user_model()


def _log_request_info(request, action, **kwargs):
    """Log request information with client details."""
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    user_info = f"User: {request.user.username} (ID: {request.user.id})" if hasattr(request,
                                                                                    'user') and request.user.is_authenticated else "Anonymous"
    logger.info(f"{action} - {user_info} from {client_ip} - {kwargs}")


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _log_request_info(request, "Fetching conversations")

        try:
            # Filter out archived conversations by default
            show_archived = request.query_params.get('show_archived', 'false').lower() == 'true'
            conversations = Conversation.objects.filter(
                user=request.user,
                is_archived=show_archived
            ).order_by('-updated_at')

            data = [{
                'id': c.id,
                'title': c.title or f"Chat {c.id}",
                'created_at': c.created_at,
                'updated_at': c.updated_at,
                'message_count': c.messages.count(),
                'last_message': c.messages.last().content if c.messages.exists() else None,
                'memory_count': c.extracted_memories.filter(is_active=True).count()  # Show memory count
            } for c in conversations]

            logger.info(f"Retrieved {len(data)} conversations for user {request.user.username}")
            return Response(data)

        except Exception as e:
            logger.error(f"Error fetching conversations for user {request.user.username}: {str(e)}", exc_info=True)
            return Response(
                {'detail': 'Failed to fetch conversations'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        _log_request_info(request, "Creating new conversation", data=request.data)

        try:
            title = request.data.get('title', '')
            model = request.data.get('model', 'gpt-4o-mini')
            mode = request.data.get('mode', 'conversational')
            enable_rag = request.data.get('enable_rag', True)  # RAG enabled by default

            # Create new conversation
            conversation = Conversation.objects.create(
                user=request.user,
                title=title or f"Chat {Conversation.objects.filter(user=request.user).count() + 1}",
                context={
                    'created_at': str(timezone.now()),
                    'model': model,
                    'mode': mode,
                    'enable_rag': enable_rag
                }
            )

            logger.info(
                f"Created new conversation {conversation.id} for user {request.user.username} - Model: {model}, Mode: {mode}, RAG: {enable_rag}")

            # Get the conversation data in the same format as GET response
            data = {
                'id': conversation.id,
                'title': conversation.title,
                'created_at': conversation.created_at,
                'updated_at': conversation.updated_at,
                'message_count': 0,
                'last_message': None,
                'memory_count': 0
            }

            return Response(data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating conversation for user {request.user.username}: {str(e)}", exc_info=True)
            return Response(
                {'detail': 'Failed to create conversation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        _log_request_info(request, f"Fetching conversation details", conversation_id=conversation_id)

        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        logger.info(f"Retrieved conversation {conversation_id} details for user {request.user.username}")

        return Response({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at,
            'updated_at': conversation.updated_at,
            'is_archived': conversation.is_archived,
            'context': conversation.context
        })

    def patch(self, request, conversation_id):
        _log_request_info(request, f"Updating conversation", conversation_id=conversation_id, data=request.data)

        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)

        updated_fields = []
        if 'title' in request.data:
            conversation.title = request.data['title']
            updated_fields.append('title')
        if 'is_archived' in request.data:
            conversation.is_archived = request.data['is_archived']
            updated_fields.append('is_archived')

        conversation.save()
        logger.info(f"Updated conversation {conversation_id} fields: {updated_fields} for user {request.user.username}")

        return Response({'status': 'updated'})

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

            data = [{
                'id': m.id,
                'sender': m.sender_id,
                'content': m.content,
                'created_at': m.created_at,
                'is_bot': m.is_bot,
                'role': m.role,
                'metadata': m.metadata
            } for m in messages]

            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return Response(data)

        except Exception as e:
            logger.error(f"Error fetching messages for conversation {conversation_id}: {str(e)}", exc_info=True)
            return Response(
                {'detail': 'Failed to fetch messages'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, conversation_id):
        _log_request_info(request, f"Processing new message", conversation_id=conversation_id,
                          message_length=len(request.data.get('content', '')),
                          model=request.data.get('model', 'unknown'),
                          mode=request.data.get('mode', 'unknown'))

        try:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            user_message = request.data.get('content')
            model = request.data.get('model', 'gpt-4o-mini')
            mode = request.data.get('mode', 'conversational')
            enable_rag = conversation.context.get('enable_rag', True)

            logger.info(
                f"Processing message for conversation {conversation_id} - User: {request.user.username}, Model: {model}, Mode: {mode}, RAG: {enable_rag}, Length: {len(user_message) if user_message else 0}")

            if not user_message:
                logger.warning("Attempted to send empty message")
                return Response(
                    {'detail': 'Message content required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create user message
            user_msg = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=user_message,
                role='user',
                metadata={'model': model, 'mode': mode, 'enable_rag': enable_rag}
            )

            logger.info(f"Created user message {user_msg.id} in conversation {conversation_id}")

            try:
                if enable_rag:
                    # Use RAG-enhanced response generation
                    logger.info(f"Using RAG-enhanced response for conversation {conversation_id}")

                    llm_result = call_llm_with_rag_context(
                        user_id=request.user.id,
                        current_message=user_message,
                        conversation_id=conversation_id,
                        chat_mode=mode,
                        model=model
                    )

                    bot_response = llm_result["response"]
                    response_metadata = llm_result["metadata"]

                    logger.info(f"RAG response generated - Memories: {response_metadata['memory_count']}, "
                              f"Messages: {response_metadata['message_count']}, "
                              f"Context tokens: {response_metadata['total_context_tokens']}")

                    # Extract memories from new conversation if it's a new conversation (few messages)
                    message_count = conversation.messages.count()
                    if message_count >= 3 and message_count % 5 == 0:  # Extract memories every 5 messages after the first 3
                        logger.info(f"Extracting memories from conversation {conversation_id} (message count: {message_count})")
                        try:
                            extracted_memories = extract_memories_from_messages(request.user.id, conversation_id)
                            logger.info(f"Extracted {len(extracted_memories)} new memories from conversation {conversation_id}")
                        except Exception as memory_error:
                            logger.warning(f"Failed to extract memories from conversation {conversation_id}: {memory_error}")
                else:
                    # Use traditional context-based response
                    logger.info(f"Using traditional context-based response for conversation {conversation_id}")

                    # Get conversation history
                    recent_messages = conversation.messages.order_by('-created_at')[:5]
                    context = "\n".join([
                        f"{m.role}: {m.content}"
                        for m in reversed(recent_messages)
                    ])

                    # Get system prompt for the selected mode
                    system_prompt = get_system_prompt(mode)
                    prompt = f"{system_prompt}\n\nPrevious messages:\n{context}\n\nUser: {user_message}"

                    bot_response = call_llm_text(prompt, model=model)
                    response_metadata = {
                        'memory_count': 0,
                        'message_count': len(recent_messages),
                        'total_context_tokens': 0,
                        'chat_mode': mode,
                        'model': model,
                        'traditional_context': True
                    }

                logger.info(
                    f"Received response from LLM for conversation {conversation_id}, response length: {len(bot_response)}")

                # Create bot message
                bot_msg = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=bot_response,
                    is_bot=True,
                    role='assistant',
                    metadata={
                        'model': model,
                        'mode': mode,
                        'enable_rag': enable_rag,
                        'response_metadata': response_metadata
                    }
                )

                logger.info(f"Created bot message {bot_msg.id} in conversation {conversation_id}")

                # Update conversation context
                conversation.context.update({
                    'last_user_message': user_message,
                    'last_bot_response': bot_response,
                    'message_count': conversation.messages.count(),
                    'current_mode': mode,
                    'current_model': model,
                    'last_response_metadata': response_metadata
                })
                conversation.save()

                return Response({
                    'id': bot_msg.id,
                    'sender': bot_msg.sender_id,
                    'content': bot_msg.content,
                    'created_at': bot_msg.created_at,
                    'is_bot': True,
                    'role': 'assistant',
                    'metadata': bot_msg.metadata
                }, status=status.HTTP_201_CREATED)

            except APIBudgetError as e:
                logger.error(f"API budget exceeded for conversation {conversation_id}: {str(e)}")
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
            except ModelNotAvailableError as e:
                logger.error(f"Model {model} not available for conversation {conversation_id}: {str(e)}")
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except LLMError as e:
                logger.error(f"LLM error for conversation {conversation_id}: {str(e)}")
                return Response(
                    {'detail': str(e)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

        except Exception as e:
            logger.error(f"Error processing message for conversation {conversation_id}: {str(e)}", exc_info=True)
            return Response(
                {'detail': 'Failed to process message'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NoteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id=None):
        _log_request_info(request, f"Fetching notes", message_id=message_id)

        if message_id:
            # Get notes for specific message
            message = get_object_or_404(Message, id=message_id)
            notes = message.notes.all()
            data = [{
                'id': note.id,
                'content': note.note,
                'created_at': note.created_at,
                'created_by': note.created_by.username
            } for note in notes]
            logger.info(f"Retrieved {len(notes)} notes for message {message_id}")
        else:
            # Get user's general notes
            notes = UserNote.objects.filter(user=request.user)
            data = [{
                'id': note.id,
                'title': note.title,
                'content': note.note,
                'created_at': note.created_at,
                'updated_at': note.updated_at,
                'tags': note.tags
            } for note in notes]
            logger.info(f"Retrieved {len(notes)} general notes for user {request.user.username}")

        return Response(data)

    def post(self, request, message_id=None):
        _log_request_info(request, f"Creating note", message_id=message_id, data=request.data)

        content = request.data.get('content')
        if not content:
            logger.warning("Attempted to create note without content")
            return Response({'error': 'Note content required.'}, status=400)

        if message_id:
            # Create note for specific message
            message = get_object_or_404(Message, id=message_id)
            note = MessageNote.objects.create(
                message=message,
                note=content,
                created_by=request.user
            )
            logger.info(f"Created message note {note.id} for message {message_id}")
        else:
            # Create general user note
            note = UserNote.objects.create(
                user=request.user,
                note=content,
                title=request.data.get('title'),
                tags=request.data.get('tags', [])
            )
            logger.info(f"Created user note {note.id} for user {request.user.username}")

        return Response({
            'id': note.id,
            'content': note.note,
            'created_at': note.created_at
        }, status=201)


class TranscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _log_request_info(request, "Processing audio transcription",
                          model=request.data.get('model', 'unknown'),
                          audio_present=bool(request.data.get('audio')))

        try:
            audio_data = request.data.get('audio')
            model = request.data.get('model', 'gpt-4o-mini-transcribe')  # Use newer OpenAI transcription model
            audio_format = request.data.get('format', 'webm')

            if not audio_data:
                logger.warning("No audio data provided for transcription")
                return Response(
                    {'detail': 'Audio data required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Processing audio transcription request for user {request.user.username} with model {model}, format {audio_format}")

            # Process audio data in memory
            try:
                audio_bytes = base64.b64decode(audio_data)
                audio_size = len(audio_bytes)
                logger.info(f"Processing audio data in memory - Size: {audio_size} bytes")

                # Check minimum file size (1KB minimum to avoid empty recordings)
                if audio_size < 1024:
                    logger.warning(f"Audio file too small: {audio_size} bytes")
                    return Response(
                        {'detail': 'Audio recording too short. Please record for at least 1 second.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                audio_file = io.BytesIO(audio_bytes)

                # Set appropriate filename based on format
                if 'webm' in audio_format.lower():
                    audio_file.name = "audio.webm"
                elif 'wav' in audio_format.lower():
                    audio_file.name = "audio.wav"
                elif 'mp4' in audio_format.lower() or 'm4a' in audio_format.lower():
                    audio_file.name = "audio.m4a"
                else:
                    audio_file.name = "audio.webm"  # Default fallback

                from ..utils.llm import call_llm_transcribe_memory
                text = call_llm_transcribe_memory(audio_file, model)

                logger.info(f"Successfully transcribed audio for user {request.user.username}, text: '{text}' (length: {len(text)})")
                return Response({'text': text.strip()})

            except Exception as e:
                logger.error(f"Transcription error for user {request.user.username}: {str(e)}", exc_info=True)
                return Response(
                    {'detail': 'Failed to transcribe audio'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Error processing transcription request for user {request.user.username}: {str(e)}",
                         exc_info=True)
            return Response(
                {'detail': 'Failed to process transcription request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
