"""Agent mode MCP integration utilities.

Provides lightweight intent detection and execution for Gmail MCP operations.
Currently supports:
- list_labels
- search_emails (basic heuristic)
- summarize_emails (new): summarize recent emails subjects/content

Falls back to standard LLM flow if no tool intent detected.
"""

from __future__ import annotations
import asyncio
import re
from typing import Optional, Dict, Any, Tuple

from django.contrib.auth import get_user_model
from .connectors.gmail.gmail_mcp import get_gmail_mcp_server

User = get_user_model()

# Simple intent patterns
LABEL_PATTERNS = [r"list labels", r"show labels", r"what labels", r"labels list"]
SEARCH_PATTERNS = [r"search", r"find emails", r"look for", r"search emails"]
SUMMARY_PATTERNS = [r"summarize", r"summary", r"summarise"]

SUMMARY_NUMBER_REGEX = re.compile(r"summar(?:ize|ise)\s+(?:my\s+)?(?:last\s+)?(\d{1,3})\s+emails")
LAST_NUMBER_EMAILS_REGEX = re.compile(r"last\s+(\d{1,3})\s+emails")

DEFAULT_SUMMARY_COUNT = 20
MAX_SUMMARY_COUNT = 100


def _match_any(patterns, text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


def _extract_summary_count(text: str) -> int:
    text_l = text.lower()
    for rgx in (SUMMARY_NUMBER_REGEX, LAST_NUMBER_EMAILS_REGEX):
        m = rgx.search(text_l)
        if m:
            try:
                val = int(m.group(1))
                return max(1, min(MAX_SUMMARY_COUNT, val))
            except ValueError:
                pass
    return DEFAULT_SUMMARY_COUNT


def detect_intent(message: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Return (operation, args) if intent detected else (None, {})."""
    lower = message.lower()

    if _match_any(LABEL_PATTERNS, lower):
        return "list_labels", {}

    if _match_any(SEARCH_PATTERNS, lower) and "label" not in lower and "summar" not in lower:
        # Naive query extraction: take text after 'search'
        q = "in:inbox"
        m = re.search(r"search(?: emails| email| for)? (.+)", lower)
        if m:
            q = m.group(1).strip()
        return "search_emails", {"query": q, "max_results": 5}

    if ("email" in lower or "inbox" in lower) and _match_any(SUMMARY_PATTERNS, lower):
        count = _extract_summary_count(lower)
        return "summarize_emails", {"max_results": count}

    # Phrases like "summarize my last 50 emails" (already covered above) OR "last 50 emails summary"
    if ("summar" in lower and "email" in lower) or ("last" in lower and "emails" in lower and "summar" in lower):
        count = _extract_summary_count(lower)
        return "summarize_emails", {"max_results": count}

    return None, {}


async def execute_gmail_operation(user_id: str, operation: str, args: Dict[str, Any]) -> Dict[str, Any]:
    server = get_gmail_mcp_server(user_id)
    # Auth check
    if not server.has_valid_credentials():
        return {"error": "Gmail not authenticated. Please authenticate in settings."}

    if operation == "list_labels":
        return await server.list_labels()
    if operation == "search_emails":
        return await server.search_emails(query=args.get("query", "in:inbox"), max_results=args.get("max_results", 5))
    if operation == "summarize_emails":
        # Reuse search_emails to pull recent inbox messages
        max_results = args.get("max_results", DEFAULT_SUMMARY_COUNT)
        emails = await server.search_emails(query="in:inbox", max_results=max_results)
        return {"emails": emails.get("messages", []), "requested": max_results}

    return {"error": f"Unsupported operation: {operation}"}


def _summarize_emails_locally(emails: list, requested: int) -> str:
    if not emails:
        return "No recent emails found to summarize." f" (Requested {requested})."
    # Collect basic info
    lines = []
    for e in emails[:requested]:
        subj = e.get("subject") or "(No Subject)"
        sender = e.get("from") or "?"
        lines.append(f"From {sender}: {subj}")
    preview = "\n".join(lines)
    # Attempt LLM summarization if available
    try:
        from .llm import call_llm_text

        prompt = (
            "Provide a concise bullet summary of the user's recent emails. "
            "Group similar topics, note any urgent or repeated themes, and keep it under 120 words.\n\n"
            f"EMAIL HEADERS ({len(lines)}):\n{preview}\n\nSummary:"
        )
        summary = call_llm_text(prompt, model="gpt-4.1-nano", temperature=0.2)
        if summary:
            return summary.strip()
    except Exception:
        # Fallback to simple list preview
        pass
    return "Recent Emails:\n" + preview


def format_tool_response(operation: str, result: Dict[str, Any]) -> str:
    if "error" in result:
        return f"Tool error: {result['error']}"

    if operation == "list_labels":
        labels = result.get("labels", [])
        if not labels:
            return "No labels found."
        names = [l.get("name", "(unnamed)") for l in labels[:15]]
        more = "" if len(labels) <= 15 else f" (+{len(labels)-15} more)"
        return "Gmail Labels:\n- " + "\n- ".join(names) + more

    if operation == "search_emails":
        messages = result.get("messages", [])
        if not messages:
            return "No emails matched that search."
        lines = []
        for m in messages[:5]:
            subj = m.get("subject", "(No Subject)")
            sender = m.get("from", "?")
            lines.append(f"From {sender}: {subj}")
        more = "" if len(messages) <= 5 else f"\n...and {len(messages)-5} more."
        return "Search Results:\n" + "\n".join(lines) + more

    if operation == "summarize_emails":
        emails = result.get("emails", [])
        requested = result.get("requested", DEFAULT_SUMMARY_COUNT)
        return _summarize_emails_locally(emails, requested)

    return f"Operation {operation} completed."  # fallback


def handle_agent_tools(user, message: str) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper that runs async execution if intent detected.

    Returns dict with keys: operation, raw_result, response_text on success,
    or None if no intent.
    """
    op, args = detect_intent(message)
    if not op:
        return None

    async def _run():
        result = await execute_gmail_operation(str(user.id), op, args)
        formatted = format_tool_response(op, result)
        return {"operation": op, "raw_result": result, "response_text": formatted, "args": args}

    return asyncio.run(_run())
