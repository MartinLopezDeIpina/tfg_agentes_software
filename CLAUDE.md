# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code standards

Use descriptive variables and function names. Follow the clean code rules, but in a moderated manner. Use comments only when necessary.

Generalize when possible, create abstract solutions that consider all cases instead of multiple if statements.

## Considerations

The project is single threaded, do not create additional threads. All concurrency must be asyncrhonous concurrency. 

## Project Overview

This is a Spanish university thesis (TFG) implementing a sophisticated multi-agent AI system for intelligent assistance. The architecture combines multiple specialized agents with vector-based retrieval and advanced orchestration patterns.

## Technology Stack

- **Backend**: Python 3.x with Flask/FastAPI, LangChain/LangGraph for agent orchestration
- **Database**: PostgreSQL with pgvector extension for vector embeddings
- **AI/ML**: OpenAI GPT, Anthropic Claude, Mistral, Groq models; HuggingFace Transformers
- **Frontend**: Open WebUI (Docker container on port 3000)
- **Protocols**: MCP (Model Context Protocol) for agent communication

## Development Commands

### Running Services
```bash
# Backend API server (Flask)
cd sistema_agentes && python app.py

# MCP Code Database Server
cd servidor_mcp_bd_codigo && python -m servidor_mcp_bd_codigo

# Open WebUI Frontend (Docker)
cd frontend && docker-compose up
```

### Testing
```bash
# Run tests with coverage
pytest --cov=servidor_mcp_bd_codigo

# Agent evaluation
cd sistema_agentes && python evaluaciones.py
```

### Database Operations
```bash
# Database migrations (Alembic)
cd servidor_mcp_bd_codigo && alembic upgrade head

# Initialize vector database
python setup_database.py
```

## Architecture Overview

### Multi-Agent System (`sistema_agentes/`)
The core system implements hierarchical agent orchestration with multiple configuration patterns:
- **Main Agent**: Central coordinator with configurable architectures
- **Orchestrator + Planner**: Task decomposition and routing
- **Specialized Agents**: Code, Confluence, GitLab, Google Drive, FileSystem

### MCP Servers
- **Code Database Server** (`servidor_mcp_bd_codigo/`): Vector-based code search with Tree-sitter parsing
- **Google Drive Server** (`servidor_mcp_google_drive/`): TypeScript-based file integration
- **Confluence Server** (`servidor_mcp_confluence/`): Documentation retrieval

### Key Components
- **Agent Evaluation Framework**: Comprehensive testing with LangSmith integration
- **RAG Pipeline**: Semantic code search with cross-reference resolution
- **Memory Systems**: Clustering and retrieval for agent context
- **Fine-tuned Models**: Custom classification models in `fine_tuning/`

## Configuration Requirements

### Environment Variables
Each component requires `.env` files with API keys:
- OpenAI, Anthropic, Mistral, Groq tokens
- Google Cloud Platform credentials
- GitLab and Confluence API access
- Database connection strings

### Database Setup
PostgreSQL with pgvector extension is required for vector similarity search. Database models are defined in each MCP server's `database/` directory.

## Agent Configuration Patterns

The system supports multiple architectural patterns defined in `sistema_agentes/configuraciones/`:
- `orchestrator_only + none + basic`: Simple orchestration
- `basic + orchestrator_planner + dummy`: Planning-focused architecture  
- `basic + basic + react`: ReAct pattern implementation

## Testing and Evaluation

### Agent Evaluation
- Evaluation datasets in `evaluaciones/` directories
- Performance metrics with CSV result tracking
- A/B testing between agent configurations
- Difficulty-based question classification

### Code Quality
- SonarQube integration configured
- pytest with coverage reporting
- Integration testing through agent execution pipelines

## Important Implementation Notes

- **Code Chunking**: Uses Tree-sitter for syntax-aware code parsing across multiple languages
- **Vector Embeddings**: Sentence Transformers for semantic search capabilities  
- **Agent Communication**: MCP protocol for standardized inter-agent messaging
- **Memory Management**: Sophisticated context clustering and retrieval systems
- **Multi-modal Integration**: Handles text, code, and document retrieval seamlessly
