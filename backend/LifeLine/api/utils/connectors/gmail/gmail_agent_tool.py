import asyncio
import json
import logging
from typing import List, Dict, Any

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from .gmail_mcp import GmailMCPServer, get_shared_executor
from ...token_utils import create_token_manager
from ...constants import (
    AGENT_RESUMMARY_THRESHOLD_TOKENS,
    AGENT_MAX_PARALLEL_CHUNKS,
    EMAIL_SUMMARY_MODEL_DEFAULT,
    EMAIL_SUMMARY_TEMPERATURE_DEFAULT,
    EMAIL_BODY_PREVIEW_CHARS,
    EMAIL_SNIPPET_PREVIEW_CHARS,
    GMAIL_SEARCH_DEFAULT_MAX_RESULTS,
)

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

    def _run_async(self, coro):
        """Helper method to run async coroutines in sync context."""
        try:
            # Use a thread pool to run the async function
            executor = get_shared_executor()
            future = executor.submit(asyncio.run, coro)
            return future.result()
        except Exception as e:
            logger.error(f"[GmailAgentTool] Error running async function: {e}")
            return {"error": f"Failed to execute operation: {str(e)}"}

    def get_tools(self) -> List[Any]:
        """Returns a list of all tools for this Gmail agent."""

        @tool
        def search_emails(query: str, max_results: int = GMAIL_SEARCH_DEFAULT_MAX_RESULTS, ids_only: bool = False) -> Dict[str, Any]:
            """Searches for emails in the user's Gmail account based on a query."""
            logger.info(f"[GmailAgentTool] User {self.user_id} searching emails with query: '{query}'")
            if not self.server.service:
                return {"error": "Gmail service not initialized. Please authenticate."}

            # Get the raw email data
            raw_result = self._run_async(self.server.search_emails(query=query, max_results=max_results, ids_only=ids_only))
            
            return raw_result

        @tool
        def read_email(message_id: str) -> Dict[str, Any]:
            """Reads the full content of a specific email by its message ID."""
            logger.info(f"[GmailAgentTool] User {self.user_id} reading email ID: {message_id}")
            if not self.server.service:
                return {"error": "Gmail service not initialized. Please authenticate."}

            return self._run_async(self.server.read_email(message_id=message_id))

        @tool
        def send_email(
            to: List[str], subject: str, body: str, cc: List[str] = None, bcc: List[str] = None
        ) -> Dict[str, Any]:
            """Sends an email from the user's account."""
            logger.info(f"[GmailAgentTool] User {self.user_id} sending email to: {to}")
            if not self.server.service:
                return {"error": "Gmail service not initialized. Please authenticate."}

            return self._run_async(self.server.send_email(to=to, subject=subject, body=body, cc=cc, bcc=bcc))

        @tool
        def read_emails_by_id(message_ids: List[str]) -> str:
            """Reads the content of specific emails given their message IDs.

            Args:
                message_ids: A list of email message IDs to read.

            Returns:
                A JSON string containing the content of the requested emails.
            """
            logger.info(f"[GmailAgentTool] User {self.user_id} reading {len(message_ids)} emails by ID.")
            if not self.server.service:
                return json.dumps({"error": "Gmail client not initialized"})

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def fetch_all():
                # IMPORTANT: Process sequentially. httplib2 (used by googleapiclient) is NOT thread-safe.
                # Parallel executes against the same service/http cause SSL WRONG_VERSION_NUMBER on Windows.
                results = []
                for msg_id in message_ids:
                    try:
                        res = await self.server.read_email(msg_id)
                        results.append(res)
                    except Exception as e:
                        logger.error(f"[GmailAgentTool] Error reading message {msg_id}: {e}")
                        results.append({"error": str(e), "id": msg_id})
                return results

            emails = loop.run_until_complete(fetch_all())

            results = [email for email in emails if "error" not in email]
            errors = [email for email in emails if "error" in email]

            response = {
                "messages": results,
                "count": len(results),
            }

            if errors:
                response['errors'] = errors

            return json.dumps(response)

        @tool
        def summarize_emails_by_id(message_ids: List[str], model: str = None, temperature: float = None) -> str:
            """Fetch and summarize emails by IDs with structured extraction (amounts, due dates, actions).

            Returns a COMPACT JSON with per-email extracted facts and citations, not full bodies, to avoid token overflow.
            Use this for large batches. If you need the full body of a specific email, call read_email(id).
            """
            logger.info(f"[GmailAgentTool] User {self.user_id} summarizing {len(message_ids)} emails by ID.")
            if not self.server.service:
                return json.dumps({"error": "Gmail client not initialized"})

            # Fetch emails sequentially to avoid httplib2 concurrency issues
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def fetch_all():
                results = []
                for msg_id in message_ids:
                    try:
                        res = await self.server.read_email(msg_id)
                        results.append(res)
                    except Exception as e:
                        logger.error(f"[GmailAgentTool] Error reading message {msg_id}: {e}")
                        results.append({"error": str(e), "id": msg_id})
                return results

            emails = loop.run_until_complete(fetch_all())
            emails = [e for e in emails if isinstance(e, dict) and "error" not in e]

            # Prepare concise inputs for summarizer
            def compact_email(e: Dict[str, Any]) -> Dict[str, Any]:
                preview = e.get("body") or ""
                if len(preview) > EMAIL_BODY_PREVIEW_CHARS:
                    preview = preview[:EMAIL_BODY_PREVIEW_CHARS]
                return {
                    "id": e.get("id"),
                    "subject": e.get("subject"),
                    "from": e.get("from"),
                    "date": e.get("date"),
                    "snippet": (e.get("snippet") if "snippet" in e else (preview[:EMAIL_SNIPPET_PREVIEW_CHARS] if preview else "")),
                    "body_preview": preview,
                }

            compact = [compact_email(e) for e in emails]

            # Tool-level summarization using a configurable small model to keep context small for the agent
            chosen_model = model or EMAIL_SUMMARY_MODEL_DEFAULT
            chosen_temp = EMAIL_SUMMARY_TEMPERATURE_DEFAULT if temperature is None else temperature
            llm = ChatOpenAI(model=chosen_model, temperature=chosen_temp)
            system = (
                "You extract structured facts from emails about utility bills and actions. "
                "For each email, output a JSON object with: id, issuer, subject, from, date, amount, due_date, billing_period, "
                "action_required (yes/no), action_items (list), and a short evidence string (quote or phrase). Keep evidence short."
            )
            user_prompt = (
                "Extract structured facts from the following emails. If a field is unknown, set it to null. "
                "Amounts should be numeric with currency symbol if present. Dates in ISO (YYYY-MM-DD) if inferable.\n\n" +
                json.dumps({"emails": compact}, ensure_ascii=False)
            )
            try:
                resp = llm.invoke([{"role": "system", "content": system}, {"role": "user", "content": user_prompt}])
                content = resp.content if hasattr(resp, "content") else str(resp)
                # Wrap result in a JSON envelope
                return json.dumps({"extracted": content, "count": len(compact)})
            except Exception as e:
                logger.error(f"[GmailAgentTool] Summarization error: {e}")
                return json.dumps({"error": str(e), "count": len(compact)})

        return [search_emails, read_email, send_email, read_emails_by_id, summarize_emails_by_id]
