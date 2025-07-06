# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code standards

Use descriptive variables and function names. Follow the clean code rules, but in a moderated manner. 

IMPORTANT: use comments only in the following cases:
- In the docstring of functions
- Only if there is a sequence of lines of code that are hard to understand. Normally that would be extracted to another function, but if not, then use a comment.

Generalize when possible, create abstract solutions that consider all cases instead of multiple if statements.

## Considerations

The project is single threaded, do not create additional threads. All concurrency must be asyncrhonous concurrency. 

Do not execute the code, I will check it myself.

## Project Overview

This is a Spanish university thesis (TFG) implementing a sophisticated multi-agent AI system for intelligent assistance. The architecture combines multiple specialized agents with vector-based retrieval using the Model Context Protocol (MCP) for agent communication.

## Technology Stack

- **Backend**: Python 3.x with Quart, LangChain/LangGraph for agent orchestration
- **Database**: PostgreSQL with pgvector extension for vector embeddings
- **AI/ML**: OpenAI GPT, Anthropic Claude, Mistral, Groq models; HuggingFace Transformers
- **Frontend**: Open WebUI (Docker container on port 3000)
- **Protocols**: MCP (Model Context Protocol) for agent communication
- **TypeScript**: Node.js/TypeScript for Google Drive MCP server

The openwebui docker has a "function" proxy to communicate with the backend. It establishes a SSE connection. 

## Development Commands

### Running Services
```bash
# Main agent system (Quart async web server)
cd sistema_agentes && python src/web_app/app.py

# Alternative system entry point
cd sistema_agentes && python run_server.py

# MCP Code Database Server
cd servidor_mcp_bd_codigo && python -m servidor_mcp_bd_codigo

# Open WebUI Frontend (Docker)
cd frontend && ./script.sh

# Google Drive MCP Server (TypeScript)
cd servidor_mcp_google_drive && npm run build && node dist/index.js
```

## Architecture Overview

### Multi-Agent System (`sistema_agentes/`)
The core system implements hierarchical agent orchestration with configurable patterns:
- **Main Agent**: Central coordinator with multiple architectural configurations
- **Orchestrator + Planner**: Task decomposition and intelligent routing 
- **Specialized Agents**: Code, Confluence, GitLab, Google Drive, FileSystem
- **Web Interface**: Quart-based async API with frontend integration

### MCP Servers (Model Context Protocol)
- **Code Database Server** (`servidor_mcp_bd_codigo/`): Vector-based code search with Tree-sitter parsing
- **Google Drive Server** (`servidor_mcp_google_drive/`): TypeScript-based file integration
- **Confluence Server** (`servidor_mcp_confluence/`): Documentation retrieval

### Key Components
- **Agent Evaluation Framework**: Comprehensive testing with CSV result tracking in `src/evaluators/`
- **RAG Pipeline**: Semantic code search with cross-reference resolution
- **Memory Systems**: Clustering and retrieval for agent context
- **Code Chunking**: Tree-sitter syntax-aware parsing for multiple languages
- **Vector Embeddings**: pgvector for semantic similarity search

## Agent Configuration Patterns

The system supports multiple architectural patterns defined in agent builders:
- `orchestrator_only + none + basic`: Simple orchestration
- `basic + orchestrator_planner + dummy`: Planning-focused architecture  
- `basic + basic + react`: ReAct pattern implementation

Configuration managed through `src/main_agent/main_agent_builder.py`

