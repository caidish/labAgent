# Model Playground Documentation

## Overview

The Model Playground is a comprehensive multi-model testing environment integrated into the Lab Agent System. It provides a unified interface for interacting with different AI models (GPT-4.1, GPT-4o, o-series, GPT-5) with advanced tool calling capabilities through MCP (Model Context Protocol) servers.

**✅ Latest Update**: Fixed OpenAI API integration to use the correct endpoints:
- **Chat Completions API** for GPT-4.1, GPT-4o, o-series models
- **Responses API** support ready for future models
- Proper parameter mapping (`max_tokens` vs `max_output_tokens`)
- Full streaming and tool calling compatibility

## Features

### 🤖 Multi-Model Support
- **GPT-4.1**: Latest GPT-4.1 with enhanced reasoning and long context
- **GPT-4o**: GPT-4o optimized for speed and efficiency  
- **o3**: o3 reasoning model with advanced problem-solving
- **o4-mini**: Lightweight o4-mini reasoning model for fast inference
- **GPT-5**: GPT-5 with advanced reasoning, verbosity control, and enhanced tools

### 🧠 Model-Specific Features
- **Reasoning Models** (o-series, GPT-5): Support for reasoning effort control and reasoning summaries
- **Verbosity Control** (GPT-5): Adjustable response detail level
- **Temperature & Top-p**: Fine-grained control over response randomness and diversity
- **Streaming Responses**: Real-time response display with typing indicators

### 🔧 Tool Integration
- **MCP Server Support**: Connects to multiple MCP servers simultaneously
- **ArXiv Daily**: Research paper analysis and recommendations
- **2D Flake Classification**: AI-powered materials analysis
- **Local FastMCP**: Development server at localhost:8123/mcp
- **Recursive Tool Calling**: Automatic tool chaining until completion

### 🎮 Interactive Interface
- **Real-time Streaming**: Watch responses as they're generated
- **Tool Call Visualization**: See exactly what tools are being called and their results
- **Reasoning Display**: View reasoning summaries from reasoning models
- **Configuration Persistence**: Settings persist across sessions

## Architecture

### Core Components

```
lab_agent/playground/
├── __init__.py                  # Package exports
├── model_capabilities.py       # Model feature definitions
├── responses_client.py         # OpenAI Responses API client
├── tool_adapter.py             # MCP to OpenAI tool conversion
├── tool_loop.py               # Recursive tool execution
├── mcp_manager.py             # MCP server management
└── streaming.py               # Response streaming utilities
```

### Model Capabilities System

Each model has a capability definition that controls which UI elements are shown:

```python
@dataclass
class ModelSupports:
    tools: bool = True                # Function calling support
    vision: bool = False              # Image input support  
    reasoning_items: bool = False     # Reasoning summaries
    reasoning_effort: bool = False    # Effort level control
    verbosity: bool = False           # Verbosity control
    streaming: bool = True            # Streaming responses
```

### Tool Adaptation

MCP tools are automatically converted to OpenAI Responses API format:

```python
# MCP Tool Definition
{
    "name": "analyze_paper",
    "description": "Analyze research paper relevance",
    "inputSchema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "abstract": {"type": "string"}
        }
    }
}

# Converted to OpenAI Format
{
    "type": "function",
    "function": {
        "name": "analyze_paper",
        "description": "Analyze research paper relevance",
        "parameters": {
            "type": "object", 
            "properties": {
                "title": {"type": "string"},
                "abstract": {"type": "string"}
            }
        }
    },
    "_route": {
        "kind": "mcp",
        "server_id": "arxiv_daily",
        "tool_name": "analyze_paper"
    }
}
```

### Recursive Tool Calling

The playground implements recursive tool calling that automatically:

1. Makes initial API call with available tools
2. Executes any tool calls requested by the model
3. Submits tool results back to the model
4. Repeats until no more tool calls are requested
5. Returns final response

This enables complex multi-step reasoning with tools.

## Configuration

### Model Settings (`lab_agent/config/playground_models.json`)

```json
{
  "api_endpoints": {
    "responses": "https://api.openai.com/v1/responses"
  },
  
  "mcp_servers": {
    "arxiv_daily": {
      "id": "arxiv_daily",
      "name": "ArXiv Daily",
      "transport": "internal",
      "enabled": true
    },
    
    "local_fastmcp": {
      "id": "local_fastmcp", 
      "name": "Local FastMCP Server",
      "transport": "http",
      "url": "http://localhost:8123/mcp",
      "enabled": true
    }
  },
  
  "tool_settings": {
    "max_recursive_calls": 10,
    "tool_timeout": 30
  }
}
```

### Environment Variables

Required in `.env`:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Accessing the Playground

1. Start the Lab Agent web interface:
   ```bash
   streamlit run lab_agent/web/app.py
   ```

2. Navigate to the **🎮 Playground** tab

### Basic Usage

1. **Select Model**: Choose from available models (GPT-4.1, GPT-4o, o3, o4-mini, GPT-5)
2. **Configure Parameters**: Adjust temperature, top-p, reasoning effort, verbosity
3. **Choose MCP Servers**: Select which tool servers to make available
4. **Start Chatting**: Type your message and watch the model respond with tools

### Advanced Features

#### Reasoning Models (o-series, GPT-5)
When using reasoning models, you can:
- Set reasoning effort (low/medium/high) 
- View reasoning summaries in expandable sections
- See how the model thinks through complex problems

#### Tool Integration
The playground automatically discovers and presents tools from selected MCP servers:
- **ArXiv Daily**: Search papers, get recommendations, analyze abstracts
- **2D Flake**: Upload images, classify materials, get quality scores  
- **Local FastMCP**: Custom development tools

#### Streaming Display
Watch responses generate in real-time with:
- Animated typing cursor
- Tool call progress indicators  
- Real-time tool execution feedback
- Reasoning process visibility

## Development

### Adding New Models

1. Define capabilities in `model_capabilities.py`:
```python
"new-model": ModelCapabilities(
    family=ModelFamily.GPT_5,
    model_name="new-model", 
    display_name="New Model",
    supports=ModelSupports(
        tools=True,
        reasoning_items=True,
        verbosity=True
    ),
    defaults=ModelDefaults(
        temperature=0.2,
        verbosity="medium"
    ),
    description="New model with enhanced features"
)
```

2. Update the Responses API client if needed

### Adding New MCP Servers

1. Add server configuration to `playground_models.json`:
```json
"new_server": {
    "id": "new_server",
    "name": "New Server",
    "transport": "http", 
    "url": "http://localhost:9000/mcp",
    "enabled": true
}
```

2. Implement connection logic in `mcp_manager.py`

### Custom Tools

Add built-in tools using the tool adapter:
```python
tool_adapter.create_builtin_tool(
    name="custom_tool",
    description="Custom functionality", 
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string"}
        }
    },
    handler="custom_handler"
)
```

## API Reference

### ResponsesClient

Main client for OpenAI Responses API:

```python
client = ResponsesClient()

# Create response
response = client.create_response(
    model="gpt-5",
    messages=[{"role": "user", "content": "Hello"}],
    tools=available_tools,
    config={"temperature": 0.2, "verbosity": "high"},
    stream=False
)

# Stream response  
for event in client.stream_response(model, messages, tools, config):
    print(event)
```

### ToolLoop

Handles recursive tool calling:

```python
tool_loop = ToolLoop()

# Execute with streaming
for event in tool_loop.execute_tool_loop(
    model=model,
    messages=messages, 
    tools=tools,
    tool_executor=executor_function,
    config=config,
    stream=True
):
    handle_event(event)
```

### MCPManager

Manages MCP server connections:

```python
manager = MCPManager()

# Get available servers
servers = manager.get_available_servers()

# Get tools from specific server
tools = manager.get_server_tools("arxiv_daily")

# Execute tool
result = manager.execute_tool("analyze_paper", {"title": "..."}, tool_def)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure FastMCP is installed: `pip install fastmcp>=2.0.0`

2. **MCP Connection Failures**: Check server status in the UI sidebar

3. **Tool Not Found**: Verify MCP server is enabled and tools are properly registered

4. **API Rate Limits**: Implement proper retry logic and rate limiting

5. **Streaming Issues**: Check network connectivity and API key permissions

6. **OpenAI API Errors**: 
   - **Fixed**: `Responses.stream() got an unexpected keyword argument 'max_tokens'`
   - **Solution**: Updated to use Chat Completions API for GPT-4.1, GPT-4o, o-series models
   - **Parameter mapping**: `max_tokens` for Chat Completions, `max_output_tokens` for Responses API

### Debug Mode

Enable detailed logging by setting:
```bash
LOG_LEVEL=DEBUG
```

### API Integration Notes

The playground now correctly uses:
- **Chat Completions API** (`client.chat.completions`) for all currently available models
- **Responses API** (`client.responses`) reserved for future models that require it
- Automatic API selection based on model capabilities
- Proper parameter mapping and tool calling format for each API

## Future Enhancements

- **Multi-modal Support**: Vision and audio inputs
- **Custom Prompt Templates**: Reusable conversation starters  
- **Tool Composition**: Chain multiple tools automatically
- **Conversation Export**: Save and load conversation histories
- **Performance Metrics**: Track token usage, latency, tool success rates
- **A/B Testing**: Compare responses across models

---

## Quick Start Example

```python
# Initialize playground components
from lab_agent.playground import ResponsesClient, MCPManager, ToolLoop

# Setup
client = ResponsesClient()
mcp_manager = MCPManager()
tool_loop = ToolLoop(client)

# Get tools
tools = mcp_manager.get_all_tools(["arxiv_daily", "local_fastmcp"])

# Execute conversation with tools
def tool_executor(name, args, tool_def):
    return mcp_manager.execute_tool(name, args, tool_def)

# Run streaming conversation
messages = [{"role": "user", "content": "Find recent papers about 2D materials"}]

for event in tool_loop.execute_tool_loop(
    model="gpt-5",
    messages=messages,
    tools=tools, 
    tool_executor=tool_executor,
    config={"temperature": 0.2, "verbosity": "high"},
    stream=True
):
    print(f"{event['type']}: {event}")
```

This creates a complete interactive AI assistant with tool calling capabilities!