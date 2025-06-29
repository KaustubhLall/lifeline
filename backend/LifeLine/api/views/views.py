import logging
from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.auth import get_user_model
from ..models.chat import Conversation, Message, MessageNote, UserNote
from ..utils.llm import call_llm_text

logger = logging.getLogger(__name__)
User = get_user_model()

class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Filter out archived conversations by default
            show_archived = request.query_params.get('show_archived', 'false').lower() == 'true'
            conversations = Conversation.objects.filter(
                user=request.user,
                is_archived=show_archived
            )
            data = [{
                'id': c.id,
                'title': c.title or f"Conversation {c.id}",
                'created_at': c.created_at,
                'updated_at': c.updated_at,
                'message_count': c.messages.count(),
                'last_message': c.messages.last().content if c.messages.exists() else None
            } for c in conversations]
            logger.info(f"Retrieved {len(data)} conversations for user {request.user.username}")
            return Response(data)
        except Exception as e:
            logger.error(f"Error fetching conversations for user {request.user.username}: {str(e)}")
            return Response(
                {'detail': 'Failed to fetch conversations'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        try:
            title = request.data.get('title', '')
            initial_message = request.data.get('initial_message', '')

            conversation = Conversation.objects.create(
                user=request.user,
                title=title,
                context={}  # Initialize empty context
            )

            logger.info(f"Created new conversation {conversation.id} for user {request.user.username}")

            if initial_message:
                # Create initial user message
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=initial_message,
                    role='user'
                )
                logger.info(f"Added initial message to conversation {conversation.id}")

                # Get bot response
                try:
                    bot_response = call_llm_text(initial_message)
                    Message.objects.create(
                        conversation=conversation,
                        sender=request.user,
                        content=bot_response,
                        is_bot=True,
                        role='assistant'
                    )
                    logger.info(f"Added bot response to conversation {conversation.id}")
                except Exception as e:
                    logger.error(f"Error getting bot response: {str(e)}")

            return Response({
                'id': conversation.id,
                'title': conversation.title,
                'created_at': conversation.created_at
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating conversation for user {request.user.username}: {str(e)}")
            return Response(
                {'detail': 'Failed to create conversation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        return Response({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at,
            'updated_at': conversation.updated_at,
            'is_archived': conversation.is_archived,
            'context': conversation.context
        })

    def patch(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        if 'title' in request.data:
            conversation.title = request.data['title']
        if 'is_archived' in request.data:
            conversation.is_archived = request.data['is_archived']
        conversation.save()
        return Response({'status': 'updated'})

    def delete(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        try:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            messages = conversation.messages.all()
            data = [{
                'id': m.id,
                'sender': m.sender_id,  # Changed to return ID instead of username
                'content': m.content,
                'created_at': m.created_at,
                'is_bot': m.is_bot,
                'role': m.role,
                'metadata': m.metadata
            } for m in messages]
            logger.info(f"Retrieved {len(data)} messages for conversation {conversation_id}")
            return Response(data)
        except Conversation.DoesNotExist:
            logger.warning(f"Attempted to access non-existent conversation {conversation_id}")
            return Response(
                {'detail': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching messages for conversation {conversation_id}: {str(e)}")
            return Response(
                {'detail': 'Failed to fetch messages'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, conversation_id):
        try:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            user_message = request.data.get('content')

            if not user_message:
                logger.warning(f"Attempted to send empty message in conversation {conversation_id}")
                return Response(
                    {'detail': 'Message content required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create user message
            user_msg = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=user_message,
                role='user'
            )
            logger.info(f"Created user message in conversation {conversation_id}")

            try:
                # Get conversation history for context
                recent_messages = conversation.messages.order_by('-created_at')[:5]
                context = "\n".join([f"{m.role}: {m.content}" for m in reversed(recent_messages)])

                # Call LLM with context
                prompt = f"Previous messages:\n{context}\n\nUser: {user_message}"
                bot_response = call_llm_text(prompt)

                # Create bot message
                bot_msg = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=bot_response,
                    is_bot=True,
                    role='assistant'
                )

                # Update conversation context
                conversation.context = {
                    'last_user_message': user_message,
                    'last_bot_response': bot_response,
                    'message_count': conversation.messages.count()
                }
                conversation.save()

                logger.info(f"Created bot response in conversation {conversation_id}")
                return Response({
                    'id': bot_msg.id,
                    'sender': bot_msg.sender_id,
                    'content': bot_msg.content,
                    'created_at': bot_msg.created_at,
                    'is_bot': True,
                    'role': 'assistant'
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Error generating bot response: {str(e)}")
                return Response({
                    'id': user_msg.id,
                    'sender': user_msg.sender_id,
                    'content': user_msg.content,
                    'created_at': user_msg.created_at,
                    'is_bot': False,
                    'role': 'user'
                }, status=status.HTTP_201_CREATED)

        except Conversation.DoesNotExist:
            logger.warning(f"Attempted to send message to non-existent conversation {conversation_id}")
            return Response(
                {'detail': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error processing message in conversation {conversation_id}: {str(e)}")
            return Response(
                {'detail': 'Failed to process message'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NoteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id=None):
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
        return Response(data)

    def post(self, request, message_id=None):
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Note content required.'}, status=400)

        if message_id:
            # Create note for specific message
            message = get_object_or_404(Message, id=message_id)
            note = MessageNote.objects.create(
                message=message,
                note=content,
                created_by=request.user
            )
        else:
            # Create general user note
            note = UserNote.objects.create(
                user=request.user,
                note=content,
                title=request.data.get('title'),
                tags=request.data.get('tags', [])
            )

        return Response({
            'id': note.id,
            'content': note.note,
            'created_at': note.created_at
        }, status=201)
