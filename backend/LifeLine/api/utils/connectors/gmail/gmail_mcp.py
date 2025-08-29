import base64
import asyncio
import base64
import logging
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Any
from urllib.parse import urljoin

from api.models import Conversation, Message
from django.conf import settings
from django.contrib.auth import get_user_model
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

User = get_user_model()
logger = logging.getLogger(__name__)


class GmailMCPServer:
    """Gmail MCP Server for handling Gmail operations through Model Context Protocol"""

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
        self.executor = ThreadPoolExecutor(max_workers=4)

    def get_credentials_path(self) -> str:
        """Get the path for storing user credentials"""
        credentials_dir = os.path.join(settings.BASE_DIR, "api", "utils", "connectors", "gmail", "credentials")
        os.makedirs(credentials_dir, exist_ok=True)
        return os.path.join(credentials_dir, f"gmail_credentials_{self.user_id}.json")

    def get_oauth_config_path(self) -> str:
        """Get the path for OAuth configuration"""
        return os.path.join(settings.BASE_DIR, "api", "utils", "connectors", "gmail", "oauth_config.json")

    def get_oauth_config(self) -> Dict:
        """Get OAuth configuration from environment variables or file"""
        # First, try to get from environment variables (recommended for production)
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

        # Fallback to config file for development
        config_path = self.get_oauth_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    import json

                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading OAuth config file: {e}")

        return None

    def has_valid_credentials(self) -> bool:
        """Check if user has valid Gmail credentials"""
        creds_path = self.get_credentials_path()
        if not os.path.exists(creds_path):
            logger.info(f"No credentials file found at {creds_path}")
            return False

        try:
            creds = Credentials.from_authorized_user_file(creds_path, self.SCOPES)
            if creds and creds.valid:
                self.credentials = creds
                logger.info("Found valid credentials")
                return True
            elif creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
                self.save_credentials(creds)
                self.credentials = creds
                return True
        except Exception as e:
            logger.error(f"Error checking credentials: {e}")

        return False

    def save_credentials(self, credentials: Credentials):
        """Save credentials to file"""
        creds_path = self.get_credentials_path()
        try:
            with open(creds_path, "w") as token:
                token.write(credentials.to_json())
            logger.info(f"Credentials saved to {creds_path}")
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            raise

    def get_auth_url(self, redirect_uri: str = None) -> str:
        """Get authorization URL for OAuth flow"""
        oauth_config = self.get_oauth_config()
        if not oauth_config:
            raise FileNotFoundError(
                "Gmail OAuth configuration not found. "
                "Please set GMAIL_OAUTH_CLIENT_ID and GMAIL_OAUTH_CLIENT_SECRET environment variables "
                "or upload an OAuth configuration file."
            )

        # Use provided redirect URI or get from config
        if not redirect_uri:
            # Try to get from settings first, fallback to default
            redirect_uri = getattr(settings, "GMAIL_OAUTH_REDIRECT_URI", None)
            if not redirect_uri:
                # Extract from OAuth config if available
                if oauth_config.get("web", {}).get("redirect_uris"):
                    redirect_uri = oauth_config["web"]["redirect_uris"][0]
                else:
                    # Last resort fallback
                    redirect_uri = "http://localhost:8000/api/auth/gmail/callback"

        try:
            # Create flow from config dict instead of file
            flow = Flow.from_client_config(
                oauth_config,
                scopes=self.SCOPES,
                redirect_uri=redirect_uri,
            )

            # Use user_id as state for security and user identification
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                state=self.user_id,
                prompt="consent",  # Force consent screen to ensure refresh token
            )

            logger.info(f"Generated auth URL for user {self.user_id} with redirect_uri: {redirect_uri}")
            return auth_url
        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            raise

    def handle_oauth_callback(self, code: str, redirect_uri: str = None) -> bool:
        """Handle OAuth callback and save credentials"""
        try:
            oauth_config = self.get_oauth_config()
            if not oauth_config:
                logger.error("OAuth config not found during callback")
                return False

            # Use the same redirect URI logic as auth URL generation
            if not redirect_uri:
                redirect_uri = getattr(settings, "GMAIL_OAUTH_REDIRECT_URI", None)
                if not redirect_uri:
                    if oauth_config.get("web", {}).get("redirect_uris"):
                        redirect_uri = oauth_config["web"]["redirect_uris"][0]
                    else:
                        redirect_uri = "http://localhost:8000/api/auth/gmail/callback"

            flow = Flow.from_client_config(
                oauth_config,
                scopes=self.SCOPES,
                redirect_uri=redirect_uri,
            )

            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Ensure we have a refresh token
            if not credentials.refresh_token:
                logger.warning("No refresh token received - user may need to re-authorize")

            self.save_credentials(credentials)
            self.credentials = credentials
            logger.info(f"OAuth callback successful for user {self.user_id} with redirect_uri: {redirect_uri}")
            return True
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            return False

    def initialize_service(self) -> bool:
        """Initialize Gmail service"""
        if not self.has_valid_credentials():
            logger.error("Cannot initialize service - no valid credentials")
            return False

        try:
            self.service = build("gmail", "v1", credentials=self.credentials)
            logger.info("Gmail service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing Gmail service: {e}")
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
        if not self.service:
            if not self.initialize_service():
                return {"error": "Gmail service not initialized. Please authenticate first."}

        try:
            message = self._create_message(to, subject, body, cc, bcc, html_body, attachments, mime_type)
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, lambda: self.service.users().messages().send(userId="me", body=message).execute()
            )

            return {"success": True, "message_id": result["id"], "thread_id": result["threadId"]}
        except Exception as e:
            logger.error(f"Error sending email: {e}")
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
        """Create email message"""
        if attachments or html_body:
            message = MIMEMultipart()
        else:
            message = MIMEText(body, _subtype="html" if mime_type == "text/html" else "plain")
            message = MIMEMultipart()
            message.attach(MIMEText(body, _subtype="html" if mime_type == "text/html" else "plain"))

        message["to"] = ", ".join(to)
        message["subject"] = subject

        if cc:
            message["cc"] = ", ".join(cc)
        if bcc:
            message["bcc"] = ", ".join(bcc)

        if attachments or html_body:
            if not isinstance(message, MIMEMultipart):
                msg = MIMEMultipart()
                msg["to"] = message["to"]
                msg["subject"] = message["subject"]
                if "cc" in message:
                    msg["cc"] = message["cc"]
                if "bcc" in message:
                    msg["bcc"] = message["bcc"]
                message = msg

            # Add text body
            message.attach(MIMEText(body, "plain"))

            # Add HTML body if provided
            if html_body:
                message.attach(MIMEText(html_body, "html"))

            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        content_type, encoding = mimetypes.guess_type(file_path)
                        if content_type is None or encoding is not None:
                            content_type = "application/octet-stream"

                        main_type, sub_type = content_type.split("/", 1)

                        with open(file_path, "rb") as fp:
                            attachment = MIMEBase(main_type, sub_type)
                            attachment.set_payload(fp.read())

                        encoders.encode_base64(attachment)
                        attachment.add_header(
                            "Content-Disposition", f'attachment; filename="{os.path.basename(file_path)}"'
                        )
                        message.attach(attachment)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {"raw": raw}

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read an email by ID"""
        if not self.service:
            if not self.initialize_service():
                return {"error": "Gmail service not initialized. Please authenticate first."}

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, lambda: self.service.users().messages().get(userId="me", id=message_id).execute()
            )

            return self._parse_email_message(result)
        except Exception as e:
            logger.error(f"Error reading email: {e}")
            return {"error": str(e)}

    def _parse_email_message(self, message: Dict) -> Dict[str, Any]:
        """Parse Gmail message into readable format"""
        headers = {h["name"]: h["value"] for h in message["payload"].get("headers", [])}

        body = ""
        attachments = []

        def extract_parts(parts):
            nonlocal body, attachments
            for part in parts:
                if part["mimeType"] == "text/plain" and not body:
                    if "data" in part["body"]:
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                elif part["mimeType"] == "text/html" and not body:
                    if "data" in part["body"]:
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                elif part.get("filename"):
                    attachments.append(
                        {
                            "filename": part["filename"],
                            "mimeType": part["mimeType"],
                            "size": part["body"].get("size", 0),
                            "attachmentId": part["body"].get("attachmentId"),
                        }
                    )
                elif "parts" in part:
                    extract_parts(part["parts"])

        if "parts" in message["payload"]:
            extract_parts(message["payload"]["parts"])
        elif message["payload"]["mimeType"] in ["text/plain", "text/html"]:
            if "data" in message["payload"]["body"]:
                body = base64.urlsafe_b64decode(message["payload"]["body"]["data"]).decode("utf-8")

        return {
            "id": message["id"],
            "threadId": message["threadId"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body,
            "attachments": attachments,
            "labels": message.get("labelIds", []),
        }

    async def search_emails(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search emails with Gmail query syntax"""
        if not self.service:
            if not self.initialize_service():
                return {"error": "Gmail service not initialized. Please authenticate first."}

        try:
            results = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.service.users().messages().list(userId="me", q=query, maxResults=max_results).execute(),
            )

            messages = results.get("messages", [])
            email_list = []

            for msg in messages:
                email_data = await self.read_email(msg["id"])
                if "error" not in email_data:
                    email_list.append(email_data)

            return {"messages": email_list, "total_count": len(email_list), "query": query}
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return {"error": str(e)}

    async def list_labels(self) -> Dict[str, Any]:
        """List all Gmail labels"""
        if not self.service:
            if not self.initialize_service():
                return {"error": "Gmail service not initialized. Please authenticate first."}

        try:
            results = await asyncio.get_event_loop().run_in_executor(
                self.executor, lambda: self.service.users().labels().list(userId="me").execute()
            )

            return {"labels": results.get("labels", [])}
        except Exception as e:
            logger.error(f"Error listing labels: {e}")
            return {"error": str(e)}

    async def create_label(
        self, name: str, message_list_visibility: str = "show", label_list_visibility: str = "labelShow"
    ) -> Dict[str, Any]:
        """Create a new Gmail label"""
        if not self.service:
            if not self.initialize_service():
                return {"error": "Gmail service not initialized. Please authenticate first."}

        try:
            label_object = {
                "name": name,
                "messageListVisibility": message_list_visibility,
                "labelListVisibility": label_list_visibility,
            }

            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, lambda: self.service.users().labels().create(userId="me", body=label_object).execute()
            )

            return result
        except Exception as e:
            logger.error(f"Error creating label: {e}")
            return {"error": str(e)}

    async def modify_email(
        self, message_id: str, add_label_ids: List[str] = None, remove_label_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Modify email labels"""
        if not self.service:
            if not self.initialize_service():
                return {"error": "Gmail service not initialized. Please authenticate first."}

        try:
            body = {}
            if add_label_ids:
                body["addLabelIds"] = add_label_ids
            if remove_label_ids:
                body["removeLabelIds"] = remove_label_ids

            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.service.users().messages().modify(userId="me", id=message_id, body=body).execute(),
            )

            return result
        except Exception as e:
            logger.error(f"Error modifying email: {e}")
            return {"error": str(e)}

    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Delete an email"""
        if not self.service:
            if not self.initialize_service():
                return {"error": "Gmail service not initialized. Please authenticate first."}

        try:
            await asyncio.get_event_loop().run_in_executor(
                self.executor, lambda: self.service.users().messages().delete(userId="me", id=message_id).execute()
            )

            return {"success": True, "message": "Email deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting email: {e}")
            return {"error": str(e)}


# Global instance manager for MCP servers
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
