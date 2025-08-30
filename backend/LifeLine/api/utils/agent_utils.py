import logging
import operator
import time
from typing import TypedDict, Annotated, Sequence

from langchain_core.messages import HumanMessage, ToolMessage, AnyMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from django.contrib.auth import get_user_model

from .connectors.gmail.gmail_agent_tool import GmailAgentTool
from .prompts import get_system_prompt

User = get_user_model()
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def run_agent(user: User, conversation_id: int, question: str, model: str = "gpt-4o-mini", temperature: float = 0.2) -> dict:
    """
    Pure LangGraph agent implementation for Gmail operations with enhanced prompt system.
    
    Args:
        user: Django User instance
        conversation_id: Conversation ID
        question: User's question
        model: OpenAI model to use
        temperature: Model temperature
        
    Returns:
        Dict containing agent's response and metadata
    """
    logger.info(f"[LangGraph Agent] Starting for user {user.username}")
    start_time = time.time()
    
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
            response = llm_with_tools.invoke(state["messages"])
            return {"messages": [response]}
        
        def should_continue(state):
            last_message = state["messages"][-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return "end"
        
        # Build LangGraph workflow
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(tools))
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
        workflow.add_edge("tools", "agent")
        
        # Compile and run with proper system prompt
        app = workflow.compile()
        
        # Create messages with system prompt and user question
        from langchain_core.messages import SystemMessage
        inputs = {
            "messages": [
                SystemMessage(content=full_system_prompt),
                HumanMessage(content=question)
            ]
        }
        
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
                    logger.info(f"[LangGraph Agent] Message attributes: {[attr for attr in dir(last_message) if not attr.startswith('_')]}")
                    
                    step_info["message_type"] = type(last_message).__name__
                    
                    if hasattr(last_message, 'content'):
                        logger.info(f"[LangGraph Agent] Node '{key}' content: {last_message.content[:200]}...")
                        step_info["has_content"] = bool(last_message.content)
                    
                    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                        logger.info(f"[LangGraph Agent] Node '{key}' tool calls: {last_message.tool_calls}")
                        step_info["tool_calls_count"] = len(last_message.tool_calls)
                        
                        for tc in last_message.tool_calls:
                            tool_calls.append({
                                "tool_name": tc.get("name"), 
                                "tool_args": tc.get("args"),
                                "node": key,
                                "latency_ms": step_duration
                            })
                    else:
                        step_info["tool_calls_count"] = 0
                    
                    # Capture token usage if available (multiple possible locations)
                    tokens_found = False
                    if hasattr(last_message, "usage_metadata") and last_message.usage_metadata:
                        step_info["tokens"] = {
                            "input": last_message.usage_metadata.get("input_tokens", 0),
                            "output": last_message.usage_metadata.get("output_tokens", 0),
                            "total": last_message.usage_metadata.get("total_tokens", 0)
                        }
                        tokens_found = True
                    elif hasattr(last_message, "response_metadata") and last_message.response_metadata:
                        # Check response_metadata for token usage
                        usage = last_message.response_metadata.get("token_usage")
                        if usage:
                            step_info["tokens"] = {
                                "input": usage.get("prompt_tokens", 0),
                                "output": usage.get("completion_tokens", 0),
                                "total": usage.get("total_tokens", 0)
                            }
                            tokens_found = True
                    
                    if tokens_found:
                        logger.info(f"[LangGraph Agent] Captured tokens for step {key}: {step_info['tokens']}")
                
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
                        if hasattr(last_message, 'content') and last_message.content:
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
        
        return {
            "response": final_response,
            "metadata": {
                "latency_ms": latency_ms,
                "tool_calls": tool_calls,
                "step_details": step_details,
                "total_steps": len(step_details),
                # Calculate total tokens across all steps
                "total_tokens": sum(
                    step.get("tokens", {}).get("total", 0) 
                    for step in step_details
                ),
            },
        }
        
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000)
        logger.error(f"[LangGraph Agent] Error for user {user.username} after {latency_ms}ms: {e}", exc_info=True)
        return {
            "response": "I'm sorry, but I encountered an error while processing your request. Please try again.",
            "metadata": {"latency_ms": latency_ms, "error": str(e)},
        }
