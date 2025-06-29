# Lifeline-Agent

**Your life, one chat away.** Lifeline-Agent is an open-source personal knowledge assistant that unifies email, calendars, notes, docs, and other daily data into a single conversational interface. Powered by the Model Context Protocol (MCP) and FastMCP adapters, the agent can securely discover tools, fetch context, and answer natural-language questions—whether you run GPT-4, Claude, or a local Llama model.

## ✨ Key Features
- **Plug-and-play connectors** – spin up Gmail, Google Calendar, Notion, Slack, and dozens of other services with one command.  
- **Agentic reasoning** – ReAct-style loop plans tool calls, retrieves only what it needs, then summarizes.  
- **Bring-your-own model** – works with OpenAI Assistants, LangChain, LlamaIndex, or Ollama.  
- **Private-first** – tokens stored locally; run everything in Docker if you prefer full isolation.

## Quick start
```bash
# 1. Clone
git clone https://github.com/your-org/lifeline-agent && cd lifeline-agent

# 2. Start example Gmail + Calendar servers
npx @gongrzhe/server-gmail-autoauth-mcp
docker run -p 8001:8000 mcp/calendar
will
# 3. Launch the agent (CLI)
poetry install
python lifeline_agent/agent.py
```

## PRD
[LINK](https://nosy-akubra-5a2.notion.site/Lifeline-Agent-Product-Requirements-Document-22023217a12580839be3c01dcca02cbc)