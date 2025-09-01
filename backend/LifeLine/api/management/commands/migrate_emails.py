"""
Django management command to migrate emails from Gmail MCP to local database
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from api.models.email import Email, EmailMigrationStatus
from api.models.mcp_connectors import MCPConnector
from api.utils.connectors.gmail.gmail_mcp import get_gmail_mcp_server
from api.utils.email_utils import generate_email_embedding

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate emails from Gmail MCP to local database with embeddings"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to migrate emails for (if not provided, prompts for selection)'
        )
        parser.add_argument(
            '--max-emails',
            type=int,
            default=100,
            help='Maximum number of emails to migrate (default: 100)'
        )
        parser.add_argument(
            '--skip-embeddings',
            action='store_true',
            help='Skip generating embeddings for migrated emails'
        )
        parser.add_argument(
            '--query',
            type=str,
            default='',
            help='Gmail search query to filter emails (default: empty = all emails)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-migration of existing emails'
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        try:
            # Get target user
            user = self.get_target_user(options['user'])
            
            # Check if user has Gmail MCP configured
            gmail_connector = self.get_gmail_connector(user)
            
            # Run the migration
            result = asyncio.run(self.migrate_emails(
                user=user,
                gmail_connector=gmail_connector,
                max_emails=options['max_emails'],
                skip_embeddings=options['skip_embeddings'],
                query=options['query'],
                force=options['force']
            ))
            
            # Report results
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migration completed: {result['migrated']} emails migrated, "
                    f"{result['skipped']} skipped, {result['failed']} failed"
                )
            )
            
            if not options['skip_embeddings']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Embeddings: {result['embeddings_generated']} generated, "
                        f"{result['embeddings_failed']} failed"
                    )
                )
                
        except Exception as e:
            logger.error(f"Email migration failed: {e}")
            raise CommandError(f"Email migration failed: {e}")
    
    def get_target_user(self, username: str = None) -> User:
        """Get the target user for migration"""
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"User '{username}' not found")
        
        # Interactive user selection
        users_with_gmail = User.objects.filter(
            mcp_connectors__connector_type='gmail',
            mcp_connectors__status='active'
        ).distinct()
        
        if not users_with_gmail.exists():
            raise CommandError("No users found with active Gmail MCP connectors")
        
        self.stdout.write("Available users with Gmail MCP:")
        for i, user in enumerate(users_with_gmail, 1):
            self.stdout.write(f"{i}. {user.username} ({user.email})")
        
        while True:
            try:
                choice = input("Select user (number): ").strip()
                index = int(choice) - 1
                if 0 <= index < len(users_with_gmail):
                    return list(users_with_gmail)[index]
                else:
                    self.stdout.write(self.style.ERROR("Invalid selection"))
            except (ValueError, KeyboardInterrupt):
                raise CommandError("Invalid selection or cancelled")
    
    def get_gmail_connector(self, user: User) -> MCPConnector:
        """Get active Gmail connector for user"""
        try:
            connector = MCPConnector.objects.get(
                user=user,
                connector_type='gmail',
                status='active'
            )
            return connector
        except MCPConnector.DoesNotExist:
            raise CommandError(f"No active Gmail connector found for user {user.username}")
        except MCPConnector.MultipleObjectsReturned:
            # Get the most recently used one
            connector = MCPConnector.objects.filter(
                user=user,
                connector_type='gmail',
                status='active'
            ).order_by('-last_used').first()
            return connector
    
    async def migrate_emails(
        self,
        user: User,
        gmail_connector: MCPConnector,
        max_emails: int,
        skip_embeddings: bool,
        query: str,
        force: bool
    ) -> Dict[str, int]:
        """Perform the actual email migration"""
        
        # Initialize or get migration status
        migration_status, created = EmailMigrationStatus.objects.get_or_create(user=user)
        
        if migration_status.is_migrating and not force:
            raise CommandError(f"Migration already in progress for user {user.username}")
        
        migration_status.start_migration()
        
        results = {
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'embeddings_generated': 0,
            'embeddings_failed': 0
        }
        
        try:
            # Get Gmail MCP server instance
            gmail_server = get_gmail_mcp_server(str(user.id))
            
            # Check authentication
            if not gmail_server.has_valid_credentials():
                raise CommandError(f"Gmail MCP not authenticated for user {user.username}")
            
            self.stdout.write(f"Starting email migration for {user.username}")
            
            # Search for emails
            search_result = await gmail_server.search_emails(
                query=query,
                max_results=max_emails
            )
            
            if 'error' in search_result:
                raise CommandError(f"Gmail search failed: {search_result['error']}")
            
            emails_data = search_result.get('messages', [])
            total_found = len(emails_data)
            
            migration_status.update_progress(total=total_found)
            
            self.stdout.write(f"Found {total_found} emails to process")
            
            # Process each email
            for i, email_data in enumerate(emails_data, 1):
                try:
                    self.stdout.write(f"Processing email {i}/{total_found}...")
                    
                    # Check if email already exists
                    message_id = email_data.get('id')
                    if not message_id:
                        self.stdout.write(self.style.WARNING(f"Email {i} missing message ID, skipping"))
                        results['failed'] += 1
                        continue
                    
                    if not force and Email.objects.filter(message_id=message_id).exists():
                        self.stdout.write(f"Email {message_id} already exists, skipping")
                        results['skipped'] += 1
                        continue
                    
                    # Create email record
                    email_obj = await self.create_email_from_data(user, email_data, gmail_server)
                    
                    if email_obj:
                        results['migrated'] += 1
                        migration_status.update_progress(processed=1)
                        
                        # Generate embedding if requested
                        if not skip_embeddings:
                            if generate_email_embedding(email_obj):
                                results['embeddings_generated'] += 1
                            else:
                                results['embeddings_failed'] += 1
                    else:
                        results['failed'] += 1
                        migration_status.update_progress(failed=1)
                        
                except Exception as e:
                    logger.error(f"Failed to process email {i}: {e}")
                    results['failed'] += 1
                    migration_status.update_progress(failed=1, error=str(e))
            
            migration_status.complete_migration()
            return results
            
        except Exception as e:
            migration_status.complete_migration()
            migration_status.update_progress(error=str(e))
            raise
    
    async def create_email_from_data(
        self,
        user: User,
        email_data: Dict[str, Any],
        gmail_server
    ) -> Email:
        """Create Email object from Gmail API data"""
        
        try:
            # Parse email data structure
            message_id = email_data.get('id')
            thread_id = email_data.get('threadId', '')
            
            # Extract headers and content
            headers = self.extract_headers(email_data)
            content = self.extract_content(email_data)
            
            # Parse date
            internal_date = email_data.get('internalDate')
            if internal_date:
                received_date = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
            else:
                received_date = timezone.now()
            
            # Extract labels and flags
            label_ids = email_data.get('labelIds', [])
            
            # Create or update email
            email, created = Email.objects.update_or_create(
                message_id=message_id,
                defaults={
                    'user': user,
                    'thread_id': thread_id,
                    'subject': headers.get('Subject', ''),
                    'sender': headers.get('From', ''),
                    'recipient': headers.get('To', ''),
                    'cc_recipients': self.parse_recipients(headers.get('Cc', '')),
                    'bcc_recipients': self.parse_recipients(headers.get('Bcc', '')),
                    'body_text': content.get('text', ''),
                    'body_html': content.get('html', ''),
                    'sent_date': self.parse_date(headers.get('Date')) or received_date,
                    'received_date': received_date,
                    'labels': label_ids,
                    'is_read': 'UNREAD' not in label_ids,
                    'is_starred': 'STARRED' in label_ids,
                    'is_important': 'IMPORTANT' in label_ids,
                    'has_attachments': self.has_attachments(email_data),
                    'attachments_metadata': self.extract_attachments_metadata(email_data),
                    'raw_email_data': email_data,
                }
            )
            
            return email
            
        except Exception as e:
            logger.error(f"Failed to create email from data: {e}")
            return None
    
    def extract_headers(self, email_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract headers from Gmail API email data"""
        headers = {}
        
        payload = email_data.get('payload', {})
        header_list = payload.get('headers', [])
        
        for header in header_list:
            name = header.get('name', '')
            value = header.get('value', '')
            headers[name] = value
        
        return headers
    
    def extract_content(self, email_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract text and HTML content from Gmail API email data"""
        content = {'text': '', 'html': ''}
        
        def extract_from_part(part):
            mime_type = part.get('mimeType', '')
            body = part.get('body', {})
            data = body.get('data', '')
            
            if data:
                # Decode base64
                import base64
                try:
                    decoded = base64.urlsafe_b64decode(data + '===').decode('utf-8')
                    if mime_type == 'text/plain':
                        content['text'] = decoded
                    elif mime_type == 'text/html':
                        content['html'] = decoded
                except Exception as e:
                    logger.warning(f"Failed to decode email content: {e}")
            
            # Recursively process parts
            for subpart in part.get('parts', []):
                extract_from_part(subpart)
        
        payload = email_data.get('payload', {})
        extract_from_part(payload)
        
        return content
    
    def parse_recipients(self, recipients_str: str) -> List[str]:
        """Parse comma-separated recipients"""
        if not recipients_str:
            return []
        return [email.strip() for email in recipients_str.split(',') if email.strip()]
    
    def parse_date(self, date_str: str) -> datetime:
        """Parse email date string"""
        if not date_str:
            return None
        
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return None
    
    def has_attachments(self, email_data: Dict[str, Any]) -> bool:
        """Check if email has attachments"""
        def check_part(part):
            filename = part.get('filename', '')
            if filename:
                return True
            for subpart in part.get('parts', []):
                if check_part(subpart):
                    return True
            return False
        
        payload = email_data.get('payload', {})
        return check_part(payload)
    
    def extract_attachments_metadata(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment metadata"""
        attachments = []
        
        def extract_from_part(part):
            filename = part.get('filename', '')
            if filename:
                body = part.get('body', {})
                attachments.append({
                    'filename': filename,
                    'mime_type': part.get('mimeType', ''),
                    'size': body.get('size', 0),
                    'attachment_id': body.get('attachmentId', ''),
                })
            
            for subpart in part.get('parts', []):
                extract_from_part(subpart)
        
        payload = email_data.get('payload', {})
        extract_from_part(payload)
        
        return attachments