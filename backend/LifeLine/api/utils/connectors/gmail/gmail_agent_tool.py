import asyncio
import logging
from typing import List, Dict, Any

from langchain_core.tools import tool
from .gmail_mcp import GmailMCPServer

logger = logging.getLogger(__name__)

class GmailAgentTool:
    """A tool class for the Gmail agent that wraps the GmailMCPServer."""

    def __init__(self, user_id: int):
        """Initializes the GmailAgentTool with a specific user context."""
        self.user_id = user_id
        self.server = GmailMCPServer(user_id=self.user_id)
        # Initialize the service immediately to check for valid credentials.
        if not self.server.initialize_service():
            # This could be exposed to the user as a setup requirement.
            logger.warning(f"[GmailAgentTool] Failed to initialize for user {self.user_id}. Authentication needed.")

    @tool
    async def search_emails(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Searches for emails in the user's Gmail account based on a query."""
        logger.info(f"[GmailAgentTool] User {self.user_id} searching emails with query: '{query}'")
        if not self.server.service:
            return {"error": "Gmail service not initialized. Please authenticate."}
        return await self.server.search_emails(query=query, max_results=max_results)

    @tool
    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Reads the full content of a specific email by its message ID."""
        logger.info(f"[GmailAgentTool] User {self.user_id} reading email ID: {message_id}")
        if not self.server.service:
            return {"error": "Gmail service not initialized. Please authenticate."}
        return await self.server.read_email(message_id=message_id)

    @tool
    async def send_email(self, to: List[str], subject: str, body: str, cc: List[str] = None, bcc: List[str] = None) -> Dict[str, Any]:
        """Sends an email from the user's account."""
        logger.info(f"[GmailAgentTool] User {self.user_id} sending email to: {to}")
        if not self.server.service:
            return {"error": "Gmail service not initialized. Please authenticate."}
        return await self.server.send_email(to=to, subject=subject, body=body, cc=cc, bcc=bcc)

    def get_tools(self) -> List[Any]:
        """Returns a list of all methods decorated with @tool."""
        return [self.search_emails, self.read_email, self.send_email]