import logging
import operator
from typing import TypedDict, Annotated, Sequence

from langchain_core.messages import HumanMessage, ToolMessage, AnyMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from django.contrib.auth import get_user_model

from .connectors.gmail.gmail_agent_tool import GmailAgentTool

User = get_user_model()
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def run_agent(user: User, conversation_id: int, question: str, model: str = "gpt-4o-mini", temperature: float = 0.2) -> str:
    """
    Pure LangGraph agent implementation for Gmail operations.
    
    Args:
        user: Django User instance
        conversation_id: Conversation ID
        question: User's question
        model: OpenAI model to use
        temperature: Model temperature
        
    Returns:
        Agent's response as string
    """
    logger.info(f"[LangGraph Agent] Starting for user {user.username}")
    
    try:
        # Initialize Gmail tool and get its tools
        gmail_tool = GmailAgentTool(user_id=user.id)
        tools = gmail_tool.get_tools()
        
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
        
        # Compile and run
        app = workflow.compile()
        inputs = {"messages": [HumanMessage(content=question)]}
        
        final_response = None
        for output in app.stream(inputs):
            logger.info(f"[LangGraph Agent] Stream output keys: {list(output.keys())}")
            for key, value in output.items():
                if "messages" in value:
                    last_message = value["messages"][-1]
                    logger.info(f"[LangGraph Agent] Node '{key}' message type: {type(last_message).__name__}")
                    if hasattr(last_message, 'content'):
                        logger.info(f"[LangGraph Agent] Node '{key}' content: {last_message.content[:200]}...")
                    if hasattr(last_message, 'tool_calls'):
                        logger.info(f"[LangGraph Agent] Node '{key}' tool calls: {last_message.tool_calls}")
                    
                    # Capture the final AI response (when agent node has no tool calls)
                    if (key == "agent" and 
                        hasattr(last_message, 'tool_calls') and 
                        not last_message.tool_calls and 
                        hasattr(last_message, 'content') and 
                        last_message.content):
                        final_response = last_message.content
                        logger.info(f"[LangGraph Agent] Captured final response from agent node")
            
            # Also check for __end__ pattern
            if "__end__" in output:
                final_response = output["__end__"]["messages"][-1].content
                logger.info(f"[LangGraph Agent] Captured final response from __end__ node")
                break
        
        if final_response is None:
            return "I was unable to find a clear answer to your request. Please try rephrasing it."
        
        logger.info(f"[LangGraph Agent] Success for user {user.username}")
        return final_response
        
    except Exception as e:
        logger.error(f"[LangGraph Agent] Error for user {user.username}: {e}", exc_info=True)
        return "I'm sorry, but I encountered an error while processing your request. Please try again."
