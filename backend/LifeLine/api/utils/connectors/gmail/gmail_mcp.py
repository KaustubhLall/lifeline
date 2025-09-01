import asyncio
import base64
import json
import logging
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ....models import MCPConnector
import httplib2
from google_auth_oauthlib.flow import InstalledAppFlow
import threading
import time
from ...constants import (
    GMAIL_API_MAX_RETRIES,
    GMAIL_API_RETRY_BASE_SECONDS,
    GMAIL_SEARCH_DEFAULT_MAX_RESULTS,
)

User = get_user_model()
logger = logging.getLogger(__name__)

# Shared ThreadPoolExecutor to avoid resource exhaustion
_shared_executor = None


def get_shared_executor():
    """Get or create shared ThreadPoolExecutor for all Gmail operations."""
    global _shared_executor
    if _shared_executor is None:
        _shared_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gmail-mcp")
    return _shared_executor


class GmailMCPServer:
    """Gmail MCP Server with DB-backed credentials (MCPConnector)."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
    ]

    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.service = None
        self.credentials = None
        self.executor = get_shared_executor()  # Use shared executor
        self._connector = None
        # Serialize all Gmail API calls (httplib2 is NOT thread-safe)
        self._api_lock = threading.Lock()

    def get_connector(self):
        """Get or create MCPConnector for this user."""
        if self._connector is None and self.user_id:
            try:
                self._connector, _ = MCPConnector.objects.get_or_create(
                    user_id=self.user_id,
                    connector_type="gmail",
                    name="Gmail",
                    defaults={
                        "scopes": self.SCOPES,
                        "redirect_uri": "http://localhost:8000/api/auth/gmail/callback",
                        "config": {},
                    },
                )
            except Exception as e:
                logger.error(f"[GmailMCP] Error creating MCPConnector for user {self.user_id}: {e}")
        return self._connector

    def has_valid_credentials(self) -> bool:
        """Check DB-backed credentials; refresh if needed. Migrate legacy file creds if present."""
        connector = self.get_connector()
        if not connector:
            logger.info("[GmailMCP] No connector for credential check")
            return False

        # Runtime cache
        if self.credentials and getattr(self.credentials, "valid", False):
            return True

        creds = connector.load_credentials()
        if not creds:
            # Legacy file migration
            legacy_dir = os.path.join(settings.BASE_DIR, "api", "utils", "connectors", "gmail", "credentials")
            legacy_path = os.path.join(legacy_dir, f"gmail_credentials_{self.user_id}.json")
            if os.path.exists(legacy_path):
                try:
                    logger.info(f"[GmailMCP] Migrating legacy credentials {legacy_path}")
                    creds = Credentials.from_authorized_user_file(legacy_path, self.SCOPES)
                    if creds and creds.valid:
                        connector.store_credentials(creds)
                        self.credentials = creds
                        return True
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        connector.store_credentials(creds)
                        self.credentials = creds
                        return True
                except Exception as e:
                    logger.error(f"[GmailMCP] Legacy credential migration failed: {e}")
            logger.info("[GmailMCP] No stored credentials in DB")
            return False

        if creds.valid:
            self.credentials = creds
            return True

        if creds.expired and creds.refresh_token:
            try:
                logger.info("[GmailMCP] Refreshing expired credentials")
                creds.refresh(Request())
                connector.store_credentials(creds)
                self.credentials = creds
                return True
            except Exception as e:
                logger.error(f"[GmailMCP] Refresh failed: {e}")
                connector.mark_as_error("refresh_failed")
                return False

        logger.info("[GmailMCP] Credentials invalid and no refresh token")
        return False

    def save_credentials(self, credentials: Credentials):
        """Persist credentials to MCPConnector DB record."""
        connector = self.get_connector()
        if not connector:
            logger.error("[GmailMCP] Cannot save credentials (no connector)")
            return
        try:
            connector.store_credentials(credentials)
            logger.info(f"[GmailMCP] Stored credentials in DB for user {self.user_id}")
        except Exception as e:
            logger.error(f"[GmailMCP] Save credentials error: {e}")
            raise

    def get_oauth_config_path(self) -> str:
        """Get the path for OAuth configuration"""
        return os.path.join(settings.BASE_DIR, "api", "utils", "connectors", "gmail", "oauth_config.json")

    def get_oauth_config(self) -> Dict:
        """Get OAuth configuration from environment variables or file"""
        client_id = getattr(settings, "GMAIL_OAUTH_CLIENT_ID", None)
        client_secret = getattr(settings, "GMAIL_OAUTH_CLIENT_SECRET", None)
        if client_id and client_secret:
            return {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                }
            }
        config_path = self.get_oauth_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[GmailMCP] Failed reading oauth config: {e}")
        return None

    def get_auth_url(self, redirect_uri: str = None) -> str:
        """Get authorization URL for OAuth flow"""
        oauth_config = self.get_oauth_config()
        if not oauth_config:
            raise FileNotFoundError("OAuth config missing")
        if not redirect_uri:
            redirect_uri = getattr(settings, "GMAIL_OAUTH_REDIRECT_URI", None)
            if not redirect_uri:
                redirect_uris = oauth_config.get("web", {}).get("redirect_uris") or []
                redirect_uri = redirect_uris[0] if redirect_uris else "http://localhost:8000/api/auth/gmail/callback"
        flow = InstalledAppFlow.from_client_config(oauth_config, scopes=self.SCOPES, redirect_uri=redirect_uri)
        auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", state=self.user_id, prompt="consent")
        return auth_url

    def handle_oauth_callback(self, code: str, redirect_uri: str = None) -> bool:
        """Handle OAuth callback and save credentials"""
        try:
            oauth_config = self.get_oauth_config()
            if not oauth_config:
                return False
            if not redirect_uri:
                redirect_uri = (
                    getattr(settings, "GMAIL_OAUTH_REDIRECT_URI", None)
                    or "http://localhost:8000/api/auth/gmail/callback"
                )
            flow = InstalledAppFlow.from_client_config(oauth_config, scopes=self.SCOPES, redirect_uri=redirect_uri)
            flow.fetch_token(code=code)
            creds = flow.credentials
            if not creds.refresh_token:
                logger.warning("[GmailMCP] No refresh token; may require re-consent later")
            self.save_credentials(creds)
            self.credentials = creds
            return True
        except Exception as e:
            logger.error(f"[GmailMCP] OAuth callback error: {e}")
            return False

    def initialize_service(self) -> bool:
        """Initialize Gmail service"""
        if not self.has_valid_credentials():
            logger.error("[GmailMCP] Initialization failed - invalid credentials")
            return False
        try:
            with self._api_lock:
                http_auth = AuthorizedHttp(self.credentials, http=httplib2.Http())
                self.service = build("gmail", "v1", http=http_auth, cache_discovery=False)
            return True
        except Exception as e:
            logger.error(f"[GmailMCP] Service build error: {e}")
            return False

    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: List[str] = None,
        bcc: List[str] = None,
        html_body: str = None,
        attachments: List[str] = None,
        mime_type: str = "text/plain",
    ) -> Dict[str, Any]:
        """Send an email"""
        if not self.service and not self.initialize_service():
            return {"error": "Not authenticated"}
        try:
            message = self._create_message(to, subject, body, cc, bcc, html_body, attachments, mime_type)
            def _send():
                with self._api_lock:
                    return self.service.users().messages().send(userId="me", body=message).execute()
            result = await asyncio.get_event_loop().run_in_executor(self.executor, _send)
            return {"success": True, "message_id": result["id"], "thread_id": result.get("threadId")}
        except Exception as e:
            logger.error(f"[GmailMCP] send_email error: {e}")
            return {"error": str(e)}

    def _create_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: List[str] = None,
        bcc: List[str] = None,
        html_body: str = None,
        attachments: List[str] = None,
        mime_type: str = "text/plain",
    ) -> Dict[str, str]:
        """Create email message with proper MIME construction"""
        # Always use MIMEMultipart for consistency when we have attachments or HTML
        if attachments or html_body:
            message = MIMEMultipart()
            message.attach(MIMEText(body, "plain"))
            if html_body:
                message.attach(MIMEText(html_body, "html"))
            if attachments:
                for fp in attachments:
                    if os.path.exists(fp):
                        ctype, encoding = mimetypes.guess_type(fp)
                        if ctype is None or encoding is not None:
                            ctype = "application/octet-stream"
                        main_type, sub_type = ctype.split("/", 1)
                        with open(fp, "rb") as f:
                            part = MIMEBase(main_type, sub_type)
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(fp)}"')
                        message.attach(part)
        else:
            # Use MIMEText directly for simple messages
            message = MIMEText(body, _subtype="html" if mime_type == "text/html" else "plain")

        message["to"] = ", ".join(to)
        message["subject"] = subject
        if cc:
            message["cc"] = ", ".join(cc)
        if bcc:
            message["bcc"] = ", ".join(bcc)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {"raw": raw}

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read an email by ID"""
        if not self.service and not self.initialize_service():
            return {"error": "Not authenticated"}
        try:
            def _get():
                last_err = None
                for attempt in range(GMAIL_API_MAX_RETRIES):
                    try:
                        with self._api_lock:
                            return self.service.users().messages().get(userId="me", id=message_id).execute()
                    except Exception as e:
                        last_err = e
                        time.sleep(GMAIL_API_RETRY_BASE_SECONDS * (2 ** attempt))
                raise last_err
            raw = await asyncio.get_event_loop().run_in_executor(self.executor, _get)
            return self._parse_email_message(raw)
        except Exception as e:
            logger.error(f"[GmailMCP] read_email error: {e}")
            return {"error": str(e)}

    def _parse_email_message(self, message: Dict) -> Dict[str, Any]:
        """Parse Gmail message into readable format"""
        headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}
        body = ""
        attachments = []

        def extract(parts):
            nonlocal body, attachments
            for part in parts:
                mime = part.get("mimeType")
                if mime in ("text/plain", "text/html") and not body and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                elif part.get("filename"):
                    attachments.append(
                        {
                            "filename": part.get("filename"),
                            "mimeType": mime,
                            "size": part.get("body", {}).get("size", 0),
                            "attachmentId": part.get("body", {}).get("attachmentId"),
                        }
                    )
                for sub in part.get("parts", []) or []:
                    extract([sub])

        payload = message.get("payload", {})
        if payload.get("parts"):
            extract(payload["parts"])
        elif payload.get("body", {}).get("data") and payload.get("mimeType") in ("text/plain", "text/html"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

        return {
            "id": message.get("id"),
            "threadId": message.get("threadId"),
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body,
            "attachments": attachments,
            "labels": message.get("labelIds", []),
        }

    async def search_emails(self, query: str, max_results: int = GMAIL_SEARCH_DEFAULT_MAX_RESULTS, ids_only: bool = False) -> Dict[str, Any]:
        """Search emails with Gmail query syntax"""
        if not self.service and not self.initialize_service():
            return {"error": "Not authenticated"}
        try:
            if ids_only:
                # Only fetch message IDs
                def _list():
                    last_err = None
                    for attempt in range(GMAIL_API_MAX_RETRIES):
                        try:
                            with self._api_lock:
                                return self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
                        except Exception as e:
                            last_err = e
                            time.sleep(GMAIL_API_RETRY_BASE_SECONDS * (2 ** attempt))
                    raise last_err
                response = _list()
                messages = response.get('messages', [])
                logger.info(f"[GmailMCP] Found {len(messages)} email IDs for query: '{query}'")
                return messages
            else:
                # Legacy: fetch full messages (less efficient for large queries)
                def _list_full():
                    last_err = None
                    for attempt in range(GMAIL_API_MAX_RETRIES):
                        try:
                            with self._api_lock:
                                return self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
                        except Exception as e:
                            last_err = e
                            time.sleep(GMAIL_API_RETRY_BASE_SECONDS * (2 ** attempt))
                    raise last_err
                response = _list_full()
                messages = response.get('messages', [])

                email_details = []
                if not messages:
                    logger.info(f"[GmailMCP] No emails found for query: '{query}'")
                    return []

                for message in messages:
                    def _get_full():
                        last_err = None
                        for attempt in range(GMAIL_API_MAX_RETRIES):
                            try:
                                with self._api_lock:
                                    return self.service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                            except Exception as e:
                                last_err = e
                                time.sleep(GMAIL_API_RETRY_BASE_SECONDS * (2 ** attempt))
                        raise last_err
                    msg = _get_full()
                    email_details.append(self._parse_email_data(msg))

                logger.info(f"[GmailMCP] Successfully fetched {len(email_details)} full emails for query: '{query}'")
                return email_details

        except Exception as e:
            logger.error(f"[GmailMCP] search_emails error: {e}")
            return {"error": str(e)}

    def read_emails_by_id(self, email_ids: list):
        """Reads a batch of emails by their IDs."""
        try:
            email_details = []
            for email_id in email_ids:
                def _get_full():
                    last_err = None
                    for attempt in range(GMAIL_API_MAX_RETRIES):
                        try:
                            with self._api_lock:
                                return self.service.users().messages().get(userId='me', id=email_id, format='full').execute()
                        except Exception as e:
                            last_err = e
                            time.sleep(GMAIL_API_RETRY_BASE_SECONDS * (2 ** attempt))
                    raise last_err
                msg = _get_full()
                email_details.append(self._parse_email_data(msg))
            return email_details
        except Exception as e:
            logger.error(f"[GmailMCP] read_emails_by_id error: {e}")
            return {"error": str(e)}

    def _parse_email_data(self, msg):
        """Helper to parse email data from raw message."""
        email_data = {'id': msg['id'], 'threadId': msg['threadId'], 'snippet': msg['snippet']}
        headers = msg['payload']['headers']
        for header in headers:
            if header['name'] == 'Subject':
                email_data['subject'] = header['value']
            if header['name'] == 'From':
                email_data['from'] = header['value']
            if header['name'] == 'Date':
                email_data['date'] = header['value']

        # Get body content
        if 'parts' in msg['payload']:
            parts = msg['payload']['parts']
            data = parts[0]['body']['data']
        else:
            data = msg['payload']['body']['data']

        email_data['body'] = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
        return email_data

    async def list_labels(self) -> Dict[str, Any]:
        """List all Gmail labels"""
        if not self.service and not self.initialize_service():
            return {"error": "Not authenticated"}
        try:
            labels = await asyncio.get_event_loop().run_in_executor(
                self.executor, lambda: self.service.users().labels().list(userId="me").execute()
            )
            return {"labels": labels.get("labels", [])}
        except Exception as e:
            logger.error(f"[GmailMCP] list_labels error: {e}")
            return {"error": str(e)}

    async def create_label(
        self, name: str, message_list_visibility: str = "show", label_list_visibility: str = "labelShow"
    ) -> Dict[str, Any]:
        """Create a new Gmail label"""
        if not self.service and not self.initialize_service():
            return {"error": "Not authenticated"}
        try:
            label_body = {
                "name": name,
                "messageListVisibility": message_list_visibility,
                "labelListVisibility": label_list_visibility,
            }
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, lambda: self.service.users().labels().create(userId="me", body=label_body).execute()
            )
            return result
        except Exception as e:
            logger.error(f"[GmailMCP] create_label error: {e}")
            return {"error": str(e)}

    async def modify_email(
        self, message_id: str, add_label_ids: List[str] = None, remove_label_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Modify email labels"""
        if not self.service and not self.initialize_service():
            return {"error": "Not authenticated"}

        json_body = {}
        if add_label_ids:
            json_body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            json_body["removeLabelIds"] = remove_label_ids

        if not json_body:
            return {"error": "No labels to add or remove"}

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.service.users().messages().modify(userId="me", id=message_id, body=json_body).execute(),
            )
            return result
        except Exception as e:
            logger.error(f"[GmailMCP] modify_email error: {e}")
            return {"error": str(e)}

    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Delete an email"""
        if not self.service and not self.initialize_service():
            return {"error": "Not authenticated"}
        try:
            await asyncio.get_event_loop().run_in_executor(
                self.executor, lambda: self.service.users().messages().delete(userId="me", id=message_id).execute()
            )
            return {"success": True}
        except Exception as e:
            logger.error(f"[GmailMCP] delete_email error: {e}")
            return {"error": str(e)}


# Instance cache
_mcp_instances = {}


def get_gmail_mcp_server(user_id: str) -> GmailMCPServer:
    """Get or create Gmail MCP server instance for user"""
    if user_id not in _mcp_instances:
        _mcp_instances[user_id] = GmailMCPServer(user_id)
    return _mcp_instances[user_id]


def cleanup_mcp_server(user_id: str):
    """Cleanup MCP server instance"""
    if user_id in _mcp_instances:
        del _mcp_instances[user_id]
