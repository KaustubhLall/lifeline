"""
API views for email functionality
"""
import logging
from typing import Dict, Any

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.email import Email, EmailMigrationStatus
from ..utils.email_utils import search_emails_by_similarity, get_email_stats, batch_generate_embeddings

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailSearchView(APIView):
    """API endpoint for semantic email search"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Search emails using semantic similarity"""
        query = request.data.get('query', '').strip()
        if not query:
            return Response(
                {"error": "Query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        limit = min(int(request.data.get('limit', 10)), 50)  # Max 50 results
        min_similarity = float(request.data.get('min_similarity', 0.3))
        
        try:
            # Search for similar emails
            similar_emails = search_emails_by_similarity(
                user=request.user,
                query=query,
                limit=limit,
                min_similarity=min_similarity
            )
            
            # Serialize email data
            results = []
            for email in similar_emails:
                results.append({
                    'id': email.id,
                    'message_id': email.message_id,
                    'subject': email.subject or 'No Subject',
                    'sender': email.sender,
                    'recipient': email.recipient,
                    'received_date': email.received_date.isoformat(),
                    'is_read': email.is_read,
                    'is_starred': email.is_starred,
                    'has_attachments': email.has_attachments,
                    'content_preview': email.get_display_content()[:200] + '...' if len(email.get_display_content()) > 200 else email.get_display_content(),
                    'labels': email.labels,
                })
            
            return Response({
                'query': query,
                'results': results,
                'total_found': len(results),
                'limit': limit,
                'min_similarity': min_similarity,
            })
            
        except Exception as e:
            logger.error(f"Email search failed for user {request.user.username}: {e}")
            return Response(
                {"error": "Email search failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmailStatsView(APIView):
    """API endpoint for email statistics"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get email statistics for the current user"""
        try:
            stats = get_email_stats(request.user)
            return Response(stats)
            
        except Exception as e:
            logger.error(f"Failed to get email stats for user {request.user.username}: {e}")
            return Response(
                {"error": "Failed to get email statistics"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmailDetailView(APIView):
    """API endpoint for email details"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, email_id):
        """Get detailed email information"""
        try:
            email = get_object_or_404(Email, id=email_id, user=request.user)
            
            return Response({
                'id': email.id,
                'message_id': email.message_id,
                'thread_id': email.thread_id,
                'subject': email.subject,
                'sender': email.sender,
                'recipient': email.recipient,
                'cc_recipients': email.cc_recipients,
                'bcc_recipients': email.bcc_recipients,
                'body_text': email.body_text,
                'body_html': email.body_html,
                'sent_date': email.sent_date.isoformat() if email.sent_date else None,
                'received_date': email.received_date.isoformat(),
                'labels': email.labels,
                'is_read': email.is_read,
                'is_starred': email.is_starred,
                'is_important': email.is_important,
                'has_attachments': email.has_attachments,
                'attachments_metadata': email.attachments_metadata,
                'is_processed': email.is_processed,
                'processing_error': email.processing_error,
                'created_at': email.created_at.isoformat(),
                'updated_at': email.updated_at.isoformat(),
            })
            
        except Exception as e:
            logger.error(f"Failed to get email {email_id} for user {request.user.username}: {e}")
            return Response(
                {"error": "Failed to get email details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmailEmbeddingView(APIView):
    """API endpoint for generating email embeddings"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate embeddings for unprocessed emails"""
        try:
            batch_size = min(int(request.data.get('batch_size', 10)), 50)  # Max 50 per batch
            
            # Generate embeddings
            stats = batch_generate_embeddings(
                user=request.user,
                batch_size=batch_size
            )
            
            return Response({
                'message': 'Embedding generation completed',
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings for user {request.user.username}: {e}")
            return Response(
                {"error": "Failed to generate embeddings"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmailMigrationStatusView(APIView):
    """API endpoint for email migration status"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get migration status for current user"""
        try:
            migration_status = EmailMigrationStatus.objects.filter(user=request.user).first()
            
            if migration_status:
                return Response({
                    'has_status': True,
                    'is_migrating': migration_status.is_migrating,
                    'total_emails_found': migration_status.total_emails_found,
                    'emails_processed': migration_status.emails_processed,
                    'emails_failed': migration_status.emails_failed,
                    'last_migration_started': migration_status.last_migration_started.isoformat() if migration_status.last_migration_started else None,
                    'last_migration_completed': migration_status.last_migration_completed.isoformat() if migration_status.last_migration_completed else None,
                    'last_error': migration_status.last_error,
                    'migration_progress': migration_status.migration_progress,
                })
            else:
                return Response({
                    'has_status': False,
                    'is_migrating': False,
                    'total_emails_found': 0,
                    'emails_processed': 0,
                    'emails_failed': 0,
                    'last_migration_started': None,
                    'last_migration_completed': None,
                    'last_error': None,
                    'migration_progress': {},
                })
                
        except Exception as e:
            logger.error(f"Failed to get migration status for user {request.user.username}: {e}")
            return Response(
                {"error": "Failed to get migration status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )