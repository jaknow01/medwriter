# MedWriter - Medical Article Drafting Tool

An interactive tool for drafting medical articles with AI assistance. Phase One implements a standalone worker with LlamaIndex agent, MCP server/client, and CLI interface.

## Features

- **LlamaIndex Agent**: ReAct agent for medical article drafting
- **Switchable LLM Providers**: Support for both OpenAI and Anthropic
- **MCP Server/Client**: HTTP-based tool communication
- **Medical Research Tools**:
  - Web search for medical information
  - Medical knowledge database
  - Citation generator
- **Interactive CLI**: Rich terminal interface with streaming responses
- **Comprehensive Logging**: Debug and production logging to console and file
- **Full Test Coverage**: Unit tests for all components

## Project Structure

```
medwriter/
├── src/
│   ├── config/          # Configuration management
│   ├── mcp_server/      # MCP server with dummy tools
│   ├── worker/          # Agent, MCP client, and worker
│   └── cli/             # CLI interface
├── tests/               # Unit tests
├── logs/                # Log files
└── .env                 # Environment variables (not in git)
```

## Installation

### Prerequisites

- Python 3.10 or higher
- OpenAI API key and/or Anthropic API key

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd medwriter
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
pip install -e ".[dev]"  # For development
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```env
# Choose your LLM provider
LLM_PROVIDER=openai  # or anthropic

# API Keys (provide at least one based on your provider)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Model selection
MODEL_NAME=gpt-4  # or claude-3-opus-20240229

# Optional: Server configuration
MCP_SERVER_URL=http://localhost:8000
MCP_SERVER_PORT=8000

# Optional: Logging
LOG_LEVEL=INFO
LOG_FILE=logs/medwriter.log
```

## Usage

### Starting the CLI

```bash
python -m src.cli.main
```

The CLI will:
1. Start the MCP server in the background
2. Initialize the agent with your configured LLM
3. Enter interactive chat mode

### CLI Commands

- `/help` - Show available commands
- `/clear` - Clear conversation history
- `/model openai|anthropic` - Switch LLM provider
- `/exit` - Quit application

### Example Session

```
🏥 Medical Article Writer - Phase One

Starting MCP server...
✓ MCP server ready
Initializing agent with openai (gpt-4)...
✓ Worker initialized

Ready! Type your message or /help for commands.

> Write an article about diabetes management

[Agent will use tools to research and draft article...]

> Generate citations for the above article

[Agent will generate formatted citations...]

> /exit
Shutting down...
Goodbye!
```

## Development

### Running Tests

Run all tests with coverage:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_agent.py -v
```

Run with coverage report:
```bash
pytest --cov=src --cov-report=html
```

### Test Coverage

The project maintains >80% test coverage across all modules:
- Configuration system
- MCP server tools
- MCP client
- LlamaIndex agent
- Worker orchestration

### Logging

Logs are written to:
- **Console**: INFO level and above (colored output)
- **File**: All levels to `logs/medwriter.log` (rotated at 10MB)

View logs in real-time:
```bash
tail -f logs/medwriter.log
```

## Architecture

```
┌─────────────┐
│     CLI     │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│   Worker    │◄────►│  MCP Client  │
└──────┬──────┘      └──────┬───────┘
       │                    │
       ▼                    │ HTTP
┌─────────────┐            │
│    Agent    │            │
│ (LlamaIndex)│            │
└─────────────┘            │
                           ▼
                    ┌──────────────┐
                    │  MCP Server  │
                    │   (FastMCP)  │
                    └──────────────┘
```

## Phase One Completion Criteria

- ✅ MCP server with 3 medical research tools
- ✅ MCP client with HTTP communication
- ✅ LlamaIndex agent with switchable LLM providers
- ✅ Worker orchestration layer
- ✅ Interactive CLI interface
- ✅ Comprehensive logging
- ✅ >80% test coverage
- ✅ Configuration system with environment variables

## Next Steps (Phase Two)

Phase Two will add:
- PostgreSQL database for conversation storage
- Redis for job queuing
- FastAPI communication layer
- Multiple workers with job distribution
- Containerization with Docker

## Troubleshooting

### MCP Server Won't Start

Check if port 8000 is already in use:
```bash
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

Change port in `.env`:
```env
MCP_SERVER_PORT=8001
```

### API Key Errors

Ensure your API key is set correctly:
```bash
# Check .env file
cat .env | grep API_KEY

# Test API key validity
python -c "from src.config.settings import settings; settings.validate_api_keys()"
```

### Import Errors

Make sure you installed the package:
```bash
pip install -e .
```

### Tests Failing

Ensure dev dependencies are installed:
```bash
pip install -e ".[dev]"
```
