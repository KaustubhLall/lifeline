import asyncio
import logging
import operator
import time
from typing import TypedDict, Annotated, Sequence

from django.contrib.auth import get_user_model
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .connectors.gmail.gmail_agent_tool import GmailAgentTool
from .constants import (
    DEFAULT_TEMPERATURE,
    AGENT_HISTORY_LIMIT_MESSAGES,
    AGENT_RESUMMARY_THRESHOLD_TOKENS,
    AGENT_MAX_PARALLEL_CHUNKS,
    AGENT_MESSAGE_TRUNCATE_TOKENS,
    CONCURRENCY_TOLERANCE,
)
from .prompts import get_system_prompt
from .token_utils import create_token_manager

import openai

User = get_user_model()
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    # The 'messages' field is annotated with `operator.add` to ensure that new messages
    # are always appended to the existing list, rather than replacing it.
    # This is the standard LangGraph way to accumulate messages in the state.
    messages: Annotated[Sequence[BaseMessage], operator.add]


def run_agent(
    user: User,
    conversation_id: int,
    question: str,
    model: str = "gpt-4o-mini",
    temperature: float = DEFAULT_TEMPERATURE,
    conversation_history: list = None,
) -> dict:
    """
    Pure LangGraph agent implementation for Gmail operations with enhanced prompt system.

    Args:
        user: Django User instance
        conversation_id: Conversation ID
        question: User's question
        model: OpenAI model to use
        temperature: Model temperature
        conversation_history: List of previous messages for context

    Returns:
        Dict containing agent's response and metadata
    """
    logger.info(f"[LangGraph Agent] Starting for user {user.username}")
    start_time = time.time()
    
    # Initialize token manager for the specific model
    token_manager = create_token_manager(model)
    logger.info(f"[LangGraph Agent] Token manager info: {token_manager.get_model_info()}")

    try:
        # Initialize Gmail tool and get its tools
        gmail_tool = GmailAgentTool(user_id=user.id)
        tools = gmail_tool.get_tools()

        # Get the agent system prompt
        agent_system_prompt = get_system_prompt("agent")
        user_context = f"\n\nUser: {user.first_name or user.username}"
        full_system_prompt = agent_system_prompt + user_context

        logger.info(f"[LangGraph Agent] Using agent system prompt: {len(full_system_prompt)} chars")

        # Set up LLM with tools
        llm = ChatOpenAI(model=model, temperature=temperature)
        llm_with_tools = llm.bind_tools(tools)

        # Define agent functions
        def call_model(state):
            # Log current state size before processing
            total_tokens = token_manager.count_message_tokens(state["messages"])
            logger.info(f"[LangGraph Agent] call_model processing {len(state['messages'])} messages ({total_tokens} tokens)")
            
            # Debug: Log message types to understand the sequence
            message_types = [type(msg).__name__ for msg in state["messages"]]
            logger.info(f"[LangGraph Agent] Message sequence: {message_types}")

            messages_to_send = state["messages"]

            logger.info(f"[LangGraph Agent] Sending {len(messages_to_send)} messages to OpenAI")
            response = llm_with_tools.invoke(messages_to_send)
            
            return {"messages": [response]}

        def summarize_tool_output(state):
            """Chunk and summarize large tool outputs to prevent token limit errors while preserving all information."""
            last_message = state["messages"][-1]
            if not isinstance(last_message, ToolMessage):
                # Return empty dict to indicate no state change needed
                return {}
            
            logger.info(f"[LangGraph Agent] Summarizer processing tool message of {len(last_message.content)} chars")

            # Calculate current context usage
            system_tokens = token_manager.count_tokens(full_system_prompt)
            history_tokens = token_manager.count_message_tokens(state["messages"][:-1])  # Exclude current tool message
            total_context_tokens = system_tokens + history_tokens + token_manager.count_tokens(last_message.content)
            
            logger.info(f"[LangGraph Agent] Context analysis: system={system_tokens}, history={history_tokens}, tool_output={token_manager.count_tokens(last_message.content)}, total={total_context_tokens}")
            
            # Check if content needs chunking based on actual token counts
            if token_manager.should_chunk_content(last_message.content, system_tokens, history_tokens):
                content_tokens = token_manager.count_tokens(last_message.content)
                logger.info(f"[LangGraph Agent] Tool output is large ({content_tokens} tokens), chunking and summarizing...")

                # Build conversation context for better summarization
                recent_history = []
                for msg in reversed(state["messages"][:-1]):
                    if isinstance(msg, HumanMessage):
                        recent_history.append(f"User: {msg.content}")
                    elif isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            tool_info = f"AI decided to call tools: {', '.join([tc['name'] for tc in msg.tool_calls])}"
                            recent_history.append(f"AI: {tool_info}")
                        elif msg.content:
                            recent_history.append(f"AI: {msg.content}")
                    if len(recent_history) >= 4:
                        break

                conversation_context = "\n".join(reversed(recent_history))
                user_query = conversation_context.split('User: ')[-1] if 'User: ' in conversation_context else 'about email data'
                
                # Use model's full context size for optimal chunking
                # Instead of conservative 25k, use 90% of model context for each chunk
                model_context_limit = token_manager.context_limit
                optimal_chunk_size = int(model_context_limit * 0.9)  # 90% of model context
                logger.info(f"[LangGraph Agent] Using optimal chunk size: {optimal_chunk_size} tokens (90% of {model_context_limit})")
                
                # Chunk the content using optimal size
                chunks = token_manager.chunk_content_with_size(last_message.content, optimal_chunk_size)
                
                logger.info(f"[LangGraph Agent] Processing {len(chunks)} chunks in parallel (max {AGENT_MAX_PARALLEL_CHUNKS} concurrent)")
                
                # Define async function to process a single chunk
                async def process_chunk_async(chunk_data):
                    i, chunk = chunk_data
                    chunk_prompt = (
                        f"You are analyzing email data for this user request: {user_query}\n\n"
                        f"This is chunk {i+1} of {len(chunks)}. Extract and summarize key information:\n"
                        f"1. Charges/amounts with dates and sources\n"
                        f"2. Action items, deadlines, or important dates\n"
                        f"3. Contact information or sender details\n"
                        f"4. Any other relevant details for the user's request\n\n"
                        f"Chunk data:\n{chunk}\n\n"
                        f"Provide a structured summary focusing on actionable information."
                    )
                    
                    try:
                        # Use async OpenAI client for parallel processing
                        chunk_response = await asyncio.to_thread(
                            llm.invoke, [HumanMessage(content=chunk_prompt)]
                        )
                        chunk_tokens = token_manager.count_tokens(chunk)
                        summary_tokens = token_manager.count_tokens(chunk_response.content)
                        logger.info(f"[LangGraph Agent] Processed chunk {i+1}/{len(chunks)} ({chunk_tokens} tokens -> {summary_tokens} tokens)")
                        return f"**Chunk {i+1} Summary:**\n{chunk_response.content}"
                    except Exception as e:
                        logger.error(f"[LangGraph Agent] Error processing chunk {i+1}: {e}")
                        return f"**Chunk {i+1} Summary:**\nError processing this chunk: {str(e)}"
                
                # Process chunks in parallel with concurrency limit
                async def process_all_chunks():
                    semaphore = asyncio.Semaphore(AGENT_MAX_PARALLEL_CHUNKS)
                    
                    async def process_with_semaphore(chunk_data):
                        async with semaphore:
                            return await process_chunk_async(chunk_data)
                    
                    tasks = [process_with_semaphore((i, chunk)) for i, chunk in enumerate(chunks)]
                    return await asyncio.gather(*tasks)
                
                # Run the async processing
                try:
                    chunk_summaries = asyncio.run(process_all_chunks())
                except Exception as e:
                    logger.error(f"[LangGraph Agent] Error in parallel processing: {e}")
                    # Fallback to sequential processing
                    chunk_summaries = []
                    for i, chunk in enumerate(chunks):
                        try:
                            chunk_response = llm.invoke([HumanMessage(content=f"Summarize this email data chunk:\n{chunk}")])
                            chunk_summaries.append(f"**Chunk {i+1} Summary:**\n{chunk_response.content}")
                        except Exception as chunk_e:
                            logger.error(f"[LangGraph Agent] Fallback error for chunk {i+1}: {chunk_e}")
                            chunk_summaries.append(f"**Chunk {i+1} Summary:**\nError processing chunk")
                
                # Combine all chunk summaries
                combined_summary = "\n\n".join(chunk_summaries)
                combined_tokens = token_manager.count_tokens(combined_summary)
                
                logger.info(f"[LangGraph Agent] Combined summaries: {combined_tokens} tokens from {len(chunks)} chunks")
                
                # Intelligent re-summarization - only if combined summaries exceed threshold
                if combined_tokens > AGENT_RESUMMARY_THRESHOLD_TOKENS:
                    logger.info(f"[LangGraph Agent] Combined summary exceeds threshold ({combined_tokens} > {AGENT_RESUMMARY_THRESHOLD_TOKENS}), consolidating...")
                    consolidation_prompt = (
                        f"Consolidate these chunk summaries into a comprehensive but concise report for: {user_query}\n\n"
                        f"Focus on:\n"
                        f"1. All charges/amounts with dates (create a table if multiple)\n"
                        f"2. Action items and deadlines\n"
                        f"3. Key contacts and important information\n"
                        f"4. Summary statistics and totals\n"
                        f"5. If tool output includes telemetry (e.g., input_count, extracted_count, metrics.usage tokens, model, duration_ms), include a short header summarizing: number of emails processed, model, and token usage.\n\n"
                        f"Chunk summaries:\n{combined_summary}\n\n"
                        f"Provide a well-organized final summary."
                    )
                    
                    try:
                        final_response = llm.invoke([HumanMessage(content=consolidation_prompt)])
                        final_summary = final_response.content
                        final_tokens = token_manager.count_tokens(final_summary)
                        logger.info(f"[LangGraph Agent] Re-summarized: {combined_tokens} -> {final_tokens} tokens")
                    except Exception as e:
                        logger.error(f"[LangGraph Agent] Error in final consolidation: {e}")
                        # Fallback: use combined summary but truncate if needed
                        available_tokens = token_manager.get_available_tokens(system_tokens, history_tokens)
                        final_summary = token_manager.truncate_to_tokens(combined_summary, available_tokens) + "\n\n[Summary truncated due to processing error]"
                else:
                    logger.info(f"[LangGraph Agent] Combined summary within threshold, no re-summarization needed")
                    final_summary = combined_summary

                # Replace the original tool message with the comprehensive summary
                new_tool_message = ToolMessage(
                    content=f"Comprehensive summary of tool output ({len(chunks)} chunks processed):\n\n{final_summary}", 
                    tool_call_id=last_message.tool_call_id
                )
                final_tokens = token_manager.count_tokens(final_summary)
                logger.info(f"[LangGraph Agent] Final summary is {final_tokens} tokens long from {content_tokens} original tokens")

                # CRITICAL: Create truly minimal context to prevent token overflow
                # The issue is that system/user messages contain too much context
                # Solution: Create fresh minimal messages with only essential content
                
                # Create minimal system message (just the core agent prompt, no history/memory)
                minimal_system_content = (
                    "You are LifeLine, a helpful AI assistant. "
                    "Analyze the provided email data summary and respond to the user's request. "
                    "Focus on actionable information, charges, dates, and key details. "
                    "If the tool output JSON includes telemetry (input_count, extracted_count, metrics with usage tokens/model), briefly state these at the top of your answer."
                )
                minimal_system_msg = state["messages"][0].__class__(content=minimal_system_content)
                
                # Create minimal user message (just the core request)
                minimal_user_content = "Please analyze my email data and provide a summary with charges, action items, and key information."
                for msg in reversed(state["messages"][:-1]):
                    if isinstance(msg, HumanMessage):
                        # Extract just the core request, truncate if needed
                        original_content = msg.content
                        if len(original_content) > 500:
                            minimal_user_content = original_content[:400] + "... [truncated for processing]"
                        else:
                            minimal_user_content = original_content
                        break
                
                minimal_user_msg = HumanMessage(content=minimal_user_content)
                
                # Create the minimal context: system + user + summary only
                essential_messages = [minimal_system_msg, minimal_user_msg, new_tool_message]
                
                # Verify the replacement is actually minimal
                replacement_tokens = token_manager.count_message_tokens(essential_messages)
                logger.info(f"[LangGraph Agent] MINIMAL State replacement: {len(state['messages'])} -> {len(essential_messages)} messages, {total_context_tokens} -> {replacement_tokens} tokens")
                
                # Safety check - if still too large, truncate the summary
                if replacement_tokens > token_manager.safe_context_limit:
                    logger.warning(f"[LangGraph Agent] Even minimal context too large ({replacement_tokens}), truncating summary")
                    max_summary_tokens = token_manager.safe_context_limit - 2000  # Leave room for system + user
                    truncated_summary = token_manager.truncate_to_tokens(new_tool_message.content, max_summary_tokens)
                    new_tool_message = ToolMessage(
                        content=truncated_summary + "\n\n[Summary truncated to fit context limits]",
                        tool_call_id=new_tool_message.tool_call_id
                    )
                    essential_messages = [minimal_system_msg, minimal_user_msg, new_tool_message]
                    final_tokens = token_manager.count_message_tokens(essential_messages)
                    logger.info(f"[LangGraph Agent] Final truncated context: {final_tokens} tokens")
                
                return {"messages": essential_messages}

            # If content is moderately large but under chunk threshold, still summarize for safety
            elif token_manager.should_summarize_moderate_content(last_message.content):
                content_tokens = token_manager.count_tokens(last_message.content)
                logger.info(f"[LangGraph Agent] Content moderately large ({content_tokens} tokens), creating focused summary")
                
                # Get user context with token-aware truncation
                user_context = "email analysis"
                for msg in reversed(state["messages"][:-1]):
                    if isinstance(msg, HumanMessage):
                        user_context = token_manager.truncate_to_tokens(msg.content, 100)  # ~100 tokens for context
                        break
                
                focused_prompt = (
                    f"User request: {user_context}\n\n"
                    f"Summarize this tool output focusing on what the user needs:\n"
                    f"1. Key charges/amounts with dates\n"
                    f"2. Action items and deadlines\n"
                    f"3. Important contacts or details\n"
                    f"4. Summary statistics\n"
                    f"5. If the tool output contains telemetry (input_count, extracted_count, metrics.usage tokens, model), start with a one-line header capturing those.\n\n"
                    f"Tool output:\n{last_message.content}\n\n"
                    f"Provide a structured, comprehensive summary."
                )
                
                try:
                    summary_response = llm.invoke([HumanMessage(content=focused_prompt)])
                    focused_summary = summary_response.content
                    
                    focused_message = ToolMessage(
                        content=f"Focused summary of tool output:\n\n{focused_summary}",
                        tool_call_id=last_message.tool_call_id
                    )
                    focused_tokens = token_manager.count_tokens(focused_summary)
                    logger.info(f"[LangGraph Agent] Created focused summary: {focused_tokens} tokens from {content_tokens} tokens")
                    # Create truly minimal context for focused summary
                    minimal_system_content = (
                        "You are LifeLine, a helpful AI assistant. "
                        "Analyze the provided email data summary and respond to the user's request. "
                        "Include any available telemetry from the tool output (counts/tokens/model) as a short header."
                    )
                    minimal_system_msg = state["messages"][0].__class__(content=minimal_system_content)
                    
                    # Create minimal user message
                    minimal_user_content = "Please analyze my email data."
                    for msg in reversed(state["messages"][:-1]):
                        if isinstance(msg, HumanMessage):
                            if len(msg.content) > 300:
                                minimal_user_content = msg.content[:250] + "... [truncated]"
                            else:
                                minimal_user_content = msg.content
                            break
                    
                    minimal_user_msg = HumanMessage(content=minimal_user_content)
                    essential_messages = [minimal_system_msg, minimal_user_msg, focused_message]
                    
                    replacement_tokens = token_manager.count_message_tokens(essential_messages)
                    logger.info(f"[LangGraph Agent] MINIMAL Focused replacement: {len(state['messages'])} -> {len(essential_messages)} messages, {replacement_tokens} tokens")
                    return {"messages": essential_messages}
                except Exception as e:
                    logger.error(f"[LangGraph Agent] Error creating focused summary: {e}")
                    # Fall back to token-aware truncation if summarization fails
                    available_tokens = token_manager.get_available_tokens(system_tokens, history_tokens)
                    truncated_content = token_manager.truncate_to_tokens(last_message.content, available_tokens) + "\n\n[Content truncated due to processing error]"
                    truncated_message = ToolMessage(
                        content=truncated_content,
                        tool_call_id=last_message.tool_call_id
                    )
                    # Create truly minimal context for truncated version
                    minimal_system_content = "You are LifeLine, a helpful AI assistant analyzing email data."
                    minimal_system_msg = state["messages"][0].__class__(content=minimal_system_content)
                    
                    minimal_user_content = "Please analyze my email data."
                    for msg in reversed(state["messages"][:-1]):
                        if isinstance(msg, HumanMessage):
                            if len(msg.content) > 200:
                                minimal_user_content = msg.content[:150] + "... [truncated]"
                            else:
                                minimal_user_content = msg.content
                            break
                    
                    minimal_user_msg = HumanMessage(content=minimal_user_content)
                    essential_messages = [minimal_system_msg, minimal_user_msg, truncated_message]
                    
                    replacement_tokens = token_manager.count_message_tokens(essential_messages)
                    logger.info(f"[LangGraph Agent] MINIMAL Truncated replacement: {len(state['messages'])} -> {len(essential_messages)} messages, {replacement_tokens} tokens")
                    return {"messages": essential_messages}
            
            # If content is manageable size, no changes needed to state
            logger.info(f"[LangGraph Agent] Tool output is manageable size, no summarization needed")
            return {}

        def should_continue(state):
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return "end"

        # Build simplified LangGraph workflow: agent -> tools -> agent
        # With AgentState using operator.add, LangGraph correctly appends tool outputs.
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(tools))

        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
        workflow.add_edge("tools", "agent")  # Tools go directly back to agent

        # Compile and run with proper system prompt
        app = workflow.compile()

        # Create messages with system prompt, conversation history, and current question
        from langchain_core.messages import SystemMessage, AIMessage

        messages = [SystemMessage(content=full_system_prompt)]

        # Add conversation history if provided, but limit it to prevent token overflow
        if conversation_history:
            # Limit history using constants
            history_limit = AGENT_HISTORY_LIMIT_MESSAGES + 1  # +1 to account for slicing
            limited_history = conversation_history[-history_limit:-1] if len(conversation_history) > 1 else []
            logger.info(f"[LangGraph Agent] Including {len(limited_history)} historical messages (limited from {len(conversation_history)})")
            
            for msg in limited_history:
                role = msg.get("role", "user")
                content = msg.get("content", "").strip()
                if content:
                    # Truncate individual messages using token-aware truncation
                    content = token_manager.truncate_to_tokens(content, AGENT_MESSAGE_TRUNCATE_TOKENS)
                    
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))

        # Add current question
        messages.append(HumanMessage(content=question))

        inputs = {"messages": messages}

        logger.info(
            f"[LangGraph Agent] Total messages in context: {len(messages)} (system + {len(messages)-2} history + current)"
        )

        final_response = None
        tool_calls = []
        step_details = []
        step_start_time = time.time()

        for output in app.stream(inputs):
            step_end_time = time.time()
            step_duration = round((step_end_time - step_start_time) * 1000)

            logger.info(f"[LangGraph Agent] Stream output keys: {list(output.keys())}")

            # Process each node in the output
            for key, value in output.items():
                step_info = {
                    "node": key,
                    "duration_ms": step_duration,
                }

                logger.info(f"[LangGraph Agent] Processing step: {key} (duration: {step_duration}ms)")

                if "messages" in value:
                    last_message = value["messages"][-1]
                    logger.info(f"[LangGraph Agent] Node '{key}' message type: {type(last_message).__name__}")

                    # Debug: Log all available attributes
                    logger.info(
                        f"[LangGraph Agent] Message attributes: {[attr for attr in dir(last_message) if not attr.startswith('_')]}"
                    )

                    step_info["message_type"] = type(last_message).__name__

                    if hasattr(last_message, "content"):
                        logger.info(f"[LangGraph Agent] Node '{key}' content: {last_message.content[:200]}...")
                        step_info["has_content"] = bool(last_message.content)

                    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        logger.info(f"[LangGraph Agent] Node '{key}' tool calls: {last_message.tool_calls}")
                        step_info["tool_calls_count"] = len(last_message.tool_calls)

                        for tc in last_message.tool_calls:
                            tool_calls.append(
                                {
                                    "tool_name": tc.get("name"),
                                    "tool_args": tc.get("args"),
                                    "node": key,
                                    # Initial placeholder; will be updated with metrics-derived latency when available
                                    "latency_ms": step_duration,
                                    "tool_call_id": tc.get("id"),
                                }
                            )
                    else:
                        step_info["tool_calls_count"] = 0

                    # Capture token usage if available (multiple possible locations)
                    tokens_found = False
                    if hasattr(last_message, "usage_metadata") and last_message.usage_metadata:
                        step_info["tokens"] = {
                            "input": last_message.usage_metadata.get("input_tokens", 0),
                            "output": last_message.usage_metadata.get("output_tokens", 0),
                            "total": last_message.usage_metadata.get("total_tokens", 0),
                        }
                        tokens_found = True
                    elif hasattr(last_message, "response_metadata") and last_message.response_metadata:
                        # Check response_metadata for token usage
                        usage = last_message.response_metadata.get("token_usage")
                        if usage:
                            step_info["tokens"] = {
                                "input": usage.get("prompt_tokens", 0),
                                "output": usage.get("completion_tokens", 0),
                                "total": usage.get("total_tokens", 0),
                            }
                            tokens_found = True

                    if tokens_found:
                        logger.info(f"[LangGraph Agent] Captured tokens for step {key}: {step_info['tokens']}")

                # If this is a ToolMessage, capture tool identity and parse metrics to enrich step/tool info
                if step_info.get("message_type") == "ToolMessage":
                    # Capture tool identity if available
                    if hasattr(last_message, "name") and last_message.name:
                        step_info["tool_name"] = last_message.name
                    if hasattr(last_message, "tool_call_id") and last_message.tool_call_id:
                        step_info["tool_call_id"] = last_message.tool_call_id
                    # Count concurrent calls of the same tool name (helps UI show "(N async calls)")
                    try:
                        tn = step_info.get("tool_name")
                        if tn:
                            step_info["tool_calls_count_by_name"] = sum(1 for tc in tool_calls if tc.get("tool_name") == tn)
                    except Exception:
                        pass

                if step_info.get("message_type") == "ToolMessage" and hasattr(last_message, "content") and last_message.content:
                    try:
                        import json
                        content_str = last_message.content
                        parsed = None
                        try:
                            parsed = json.loads(content_str)
                        except Exception:
                            # try to find first JSON object/array
                            import re
                            m = re.search(r"(\{.*\}|\[.*\])", content_str, re.DOTALL)
                            if m:
                                parsed = json.loads(m.group(1))

                        if isinstance(parsed, dict):
                            metrics = parsed.get("metrics")
                            if isinstance(metrics, dict):
                                step_info["tool_metrics"] = metrics
                                usage = metrics.get("usage")
                                if isinstance(usage, dict):
                                    step_info["tokens"] = {
                                        "input": usage.get("input_tokens", 0),
                                        "output": usage.get("output_tokens", 0),
                                        "total": usage.get("total_tokens", 0),
                                    }
                                # Attach metrics to matching tool_call by id
                                tc_id = getattr(last_message, "tool_call_id", None)
                                if tc_id:
                                    for tc in tool_calls:
                                        if tc.get("tool_call_id") == tc_id:
                                            tc["metrics"] = metrics
                                            if isinstance(usage, dict):
                                                tc["tokens"] = {
                                                    "input": usage.get("input_tokens", 0),
                                                    "output": usage.get("output_tokens", 0),
                                                    "total": usage.get("total_tokens", 0),
                                                }
                                            # Prefer metrics-provided latency for accuracy (actual API call duration)
                                            try:
                                                m_latency = metrics.get("duration_ms") or metrics.get("latency_ms")
                                                if m_latency is not None:
                                                    tc["latency_ms"] = int(m_latency)
                                            except Exception:
                                                pass
                                            # Attach this tool call to the current step index (before appending this step)
                                            try:
                                                tc["step_index"] = len(step_details)
                                            except Exception:
                                                pass
                                            break
                    except Exception as parse_e:
                        logger.debug(f"[LangGraph Agent] Could not parse ToolMessage metrics: {parse_e}")

                # Always append step info, even if no messages
                step_details.append(step_info)
                logger.info(f"[LangGraph Agent] Added step {key} to step_details (total: {len(step_details)})")

            step_start_time = time.time()

            # Check for final response in the current output
            for key, value in output.items():
                if "messages" in value:
                    last_message = value["messages"][-1]
                    # Capture the final AI response (when agent node has no tool calls)
                    if (
                        key == "agent"
                        and hasattr(last_message, "tool_calls")
                        and not last_message.tool_calls
                        and hasattr(last_message, "content")
                        and last_message.content
                    ):
                        final_response = last_message.content
                        logger.info(f"[LangGraph Agent] Captured final response from agent node")

            # Also check for __end__ pattern with safe access
            if "__end__" in output:
                try:
                    end_data = output["__end__"]
                    if isinstance(end_data, dict) and "messages" in end_data and end_data["messages"]:
                        last_message = end_data["messages"][-1]
                        if hasattr(last_message, "content") and last_message.content:
                            final_response = last_message.content
                            logger.info(f"[LangGraph Agent] Captured final response from __end__ node")
                            break
                    logger.warning(f"[LangGraph Agent] __end__ node has unexpected structure: {end_data}")
                except (KeyError, IndexError, AttributeError) as e:
                    logger.warning(f"[LangGraph Agent] Error accessing __end__ node: {e}")
                    continue

        if final_response is None:
            final_response = "I was unable to find a clear answer to your request. Please try rephrasing it."

        latency_ms = round((time.time() - start_time) * 1000)
        logger.info(f"[LangGraph Agent] Success for user {user.username} in {latency_ms}ms")

        # Compute token breakdowns
        total_tokens_all = 0
        agent_tokens = 0
        tool_tokens = 0
        steps_total_duration_ms = 0
        tool_step_tokens_total = 0
        
        logger.info(f"[LangGraph Agent] Processing {len(step_details)} steps for token breakdown")
        for i, s in enumerate(step_details):
            t = (s.get("tokens") or {}).get("total", 0)
            total_tokens_all += t
            node = s.get("node") or ""
            mt = (s.get("message_type") or "").lower()
            steps_total_duration_ms += int(s.get("duration_ms") or 0)
            
            logger.info(f"[LangGraph Agent] Step {i}: node='{node}', message_type='{mt}', tokens={t}")
            
            # More robust token attribution - check both node and message_type
            is_agent_step = (node == "agent" or "agent" in node.lower() or 
                           mt in ("aimessage", "ai") or "ai" in mt)
            is_tool_step = (node == "tools" or "tool" in node.lower() or 
                          mt in ("toolmessage", "tool", "tools") or "tool" in mt)
            
            if is_agent_step and not is_tool_step:
                agent_tokens += t
                logger.info(f"[LangGraph Agent] Added {t} tokens to agent_tokens (total: {agent_tokens})")
            elif is_tool_step:
                tool_tokens += t
                tool_step_tokens_total += t
                logger.info(f"[LangGraph Agent] Added {t} tokens to tool_tokens (total: {tool_tokens})")
            else:
                logger.info(f"[LangGraph Agent] Step {i} tokens not attributed: node='{node}', mt='{mt}', tokens={t}")
                # Fallback: if it has tokens but doesn't match our patterns, add to agent
                if t > 0:
                    agent_tokens += t
                    logger.info(f"[LangGraph Agent] Fallback: Added {t} tokens to agent_tokens (total: {agent_tokens})")

        # Log final token breakdown totals
        logger.info(f"[LangGraph Agent] Final token breakdown: total={total_tokens_all}, agent={agent_tokens}, tool={tool_tokens}")
        logger.info(f"[LangGraph Agent] Token verification: agent+tool={agent_tokens + tool_tokens}, should equal total={total_tokens_all}")

        # Aggregate per-tool tokens using tool_calls entries and infer concurrency
        tools_token_breakdown = []
        tools_total_duration_ms = 0

        # Group calls by tool name and by step index
        by_tool = {}
        by_step = {}
        for idx, tc in enumerate(tool_calls):
            name = tc.get("tool_name") or "tool"
            by_tool.setdefault(name, []).append(tc)
            step_idx = tc.get("step_index")
            if step_idx is not None:
                by_step.setdefault(step_idx, []).append(tc)
            # Sum total tools latency regardless of grouping
            try:
                tools_total_duration_ms += int(tc.get("latency_ms") or 0)
            except Exception:
                pass

        # Infer concurrency per step comparing step duration vs sum/max of call latencies
        for s_idx, calls in by_step.items():
            try:
                step = step_details[s_idx]
            except Exception:
                continue
            step_dur = int(step.get("duration_ms") or 0)
            lats = [int(c.get("latency_ms") or 0) for c in calls]
            sum_lat = sum(lats)
            max_lat = max(lats) if lats else 0
            # Determine concurrency type
            def approx(a, b):
                if b == 0:
                    return a == 0
                return abs(a - b) / max(b, 1) <= CONCURRENCY_TOLERANCE
            if len(lats) <= 1:
                ctype = "single"
            elif approx(step_dur, sum_lat):
                ctype = "sync"
            elif approx(step_dur, max_lat):
                ctype = "async"
            else:
                ctype = "mixed"
            step["concurrency_type"] = ctype
            step["tool_calls_in_step"] = len(lats)

        # Build per-tool breakdown with concurrency summary across steps
        for name, calls in by_tool.items():
            tokens_total = 0
            duration_ms_total = 0
            api_calls = len(calls)
            # track step-level types for this tool
            step_types = set()
            for c in calls:
                tokens_total += (c.get("tokens") or {}).get("total", 0)
                try:
                    duration_ms_total += int(c.get("latency_ms") or 0)
                except Exception:
                    pass
                sidx = c.get("step_index")
                if sidx is not None and 0 <= sidx < len(step_details):
                    stype = step_details[sidx].get("concurrency_type")
                    if stype:
                        step_types.add(stype)

            if "async" in step_types and ("sync" in step_types or "mixed" in step_types):
                overall = "mixed"
            elif len(step_types) == 1:
                overall = next(iter(step_types))
            elif len(step_types) == 0:
                overall = "single" if api_calls == 1 else "unknown"
            else:
                # multiple but consistent without async+sync mixture
                overall = next(iter(step_types))

            tools_token_breakdown.append({
                "tool_name": name,
                "tokens": tokens_total,
                "api_calls": api_calls,
                "duration_ms_total": duration_ms_total,
                "concurrency": overall,
            })

        return {
            "response": final_response,
            "metadata": {
                "latency_ms": latency_ms,
                "tool_calls": tool_calls,
                "step_details": step_details,
                "total_steps": len(step_details),
                # Maintain old total_tokens for backward compat
                "total_tokens": total_tokens_all,
                # Total of durations in step_details (can differ slightly from wall-clock latency)
                "steps_total_duration_ms": steps_total_duration_ms,
                "tools_total_duration_ms": tools_total_duration_ms,
                # New breakdowns
                "agent_tokens": agent_tokens,
                "tool_tokens": tool_tokens,
                "tool_step_tokens_total": tool_step_tokens_total,
                "tools_token_breakdown": tools_token_breakdown,
            },
        }

    except openai.RateLimitError as e:
        latency_ms = round((time.time() - start_time) * 1000)
        error_message = str(e)
        logger.error(f"[LangGraph Agent] Rate limit error for user {user.username} after {latency_ms}ms: {error_message}", exc_info=True)

        response_text = "I'm sorry, but I encountered an issue while processing your request. Please try again."
        if "tokens" in error_message: # Check if it's a token limit error
            response_text = "Your request generated a response that was too large to process, even after attempting to summarize it. Please try a more specific query."

        return {
            "response": response_text,
            "metadata": {"latency_ms": latency_ms, "error": error_message, "error_type": "RateLimitError"},
        }

    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000)
        logger.error(f"[LangGraph Agent] Error for user {user.username} after {latency_ms}ms: {e}", exc_info=True)
        return {
            "response": "I'm sorry, but I encountered an error while processing your request. Please try again.",
            "metadata": {"latency_ms": latency_ms, "error": str(e)},
        }
