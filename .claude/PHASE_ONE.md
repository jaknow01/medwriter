# PHASE ONE of Development

1. Build a singular worker module - agent engine written in Llamaindex framework and MCP client written in FastMCP framework
2. Dummy MCP Server with HTTP communication to Client
3. Unit tests for all functionalities
4. Ability to interact with agent via CLI (don't dockerize it yet)

Make sure to provide extensive logging to facilitate debugging

## Standing issues
1. When asking a question I get the following error:
```
(medwriter) kuba@kuba-pecet:~/medwriter$ python -m src.cli.main
╭─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ 🏥 Medical Article Writer - Phase One                                                                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Starting MCP server...
Waiting for server to be ready...
✓ MCP server ready

Initializing agent with anthropic (claude-haiku-4-5)...
2026-02-01 18:47:28 | INFO     | src.worker.worker:__init__ | Worker instance created
2026-02-01 18:47:28 | INFO     | src.worker.worker:initialize | Initializing worker...
2026-02-01 18:47:28 | INFO     | src.worker.worker:initialize | Connecting to MCP server at http://localhost:8002/mcp
2026-02-01 18:47:28 | INFO     | src.worker.mcp_client:__init__ | Initialized MCP client for http://localhost:8002/mcp
2026-02-01 18:47:28 | INFO     | src.worker.mcp_client:connect | Connecting to MCP server at http://localhost:8002/mcp
2026-02-01 18:47:28 | INFO     | src.worker.mcp_client:connect | Successfully connected to MCP server
2026-02-01 18:47:28 | INFO     | src.worker.mcp_client:connect | Discovered 3 tools
2026-02-01 18:47:28 | INFO     | src.worker.mcp_client:get_tools | Converted 3 MCP tools to LlamaIndex format
2026-02-01 18:47:28 | INFO     | src.worker.worker:initialize | Retrieved 3 tools from MCP server
2026-02-01 18:47:28 | INFO     | src.worker.worker:initialize | Creating agent with anthropic (claude-haiku-4-5)
2026-02-01 18:47:28 | INFO     | src.worker.agent:__init__ | Initializing agent with anthropic (claude-haiku-4-5)
/usr/lib/python3.10/inspect.py:469: PydanticDeprecatedSince20: The `__fields__` attribute is deprecated, use the `model_fields` class property instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
  value = getattr(object, key)
/usr/lib/python3.10/inspect.py:469: PydanticDeprecatedSince20: The `__fields_set__` attribute is deprecated, use `model_fields_set` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
  value = getattr(object, key)
/usr/lib/python3.10/inspect.py:469: PydanticDeprecatedSince211: Accessing the 'model_computed_fields' attribute on the instance is deprecated. Instead, you should access this attribute from the model class. Deprecated in Pydantic V2.11 to be removed in V3.0.
  value = getattr(object, key)
/usr/lib/python3.10/inspect.py:469: PydanticDeprecatedSince211: Accessing the 'model_fields' attribute on the instance is deprecated. Instead, you should access this attribute from the model class. Deprecated in Pydantic V2.11 to be removed in V3.0.
  value = getattr(object, key)
2026-02-01 18:47:28 | INFO     | src.worker.agent:__init__ | Agent initialized successfully
2026-02-01 18:47:28 | INFO     | src.worker.worker:initialize | Worker initialization complete
✓ Worker initialized

Ready! Type your message or /help for commands.

>: What to do if I have a running nose?

2026-02-01 18:48:03 | INFO     | src.worker.worker:stream_query | Streaming response for query: What to do if I have a running nose?...
2026-02-01 18:48:03 | INFO     | src.worker.agent:stream_chat | Streaming response for message: What to do if I have a running nose?...
2026-02-01 18:48:03 | ERROR    | src.worker.agent:stream_chat | Error streaming message: asyncio.run() cannot be called from a running event loop
2026-02-01 18:48:03 | ERROR    | src.worker.worker:stream_query | Error streaming query: asyncio.run() cannot be called from a running event loop

Error: asyncio.run() cannot be called from a running event loop
2026-02-01 18:48:03 | ERROR    | __main__:chat_loop | Error processing query: asyncio.run() cannot be called from a running event loop

>: 
```