# Plan: Simplify 2D Flake Tools Using FastMCP Client

## Current Architecture
- **Current**: Complex proxy/wrapper approach with 600+ lines
  - `flake_2d_client.py` acts as a proxy to the external server
  - Manual HTTP calls with httpx to the server's endpoints
  - Complex tool definitions and error handling
  - MCP server wrapper that exposes tools to GPT

## New Architecture with FastMCP Client
Since the 2D flake server **already implements FastMCP**, we can directly use the FastMCP client to call it, eliminating our proxy layer entirely.

## Implementation Plan

### 1. Install FastMCP
```bash
pip install fastmcp
```

### 2. Create New Simplified Client (`lab_agent/mcp/fastmcp_flake_client.py`)
```python
"""
FastMCP client for 2D flake classification server
"""
import asyncio
from typing import Dict, Any, List
from fastmcp import Client
import logging

class FastMCPFlakeClient:
    """Direct FastMCP client for 2D flake server"""
    
    def __init__(self, server_url: str = "http://0.0.0.0:8000/mcp"):
        self.logger = logging.getLogger("fastmcp.flake_client")
        self.server_url = server_url
        self.client = None
        
    async def connect(self):
        """Connect to the FastMCP server"""
        self.client = Client(self.server_url)
        await self.client.__aenter__()
        self.logger.info(f"Connected to FastMCP server at {self.server_url}")
        
    async def disconnect(self):
        """Disconnect from the FastMCP server"""
        if self.client:
            await self.client.__aexit__(None, None, None)
            
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the remote FastMCP server"""
        if not self.client:
            await self.connect()
        
        # Direct FastMCP tool call
        result = await self.client.call_tool(tool_name, arguments)
        return result
    
    async def list_tools(self) -> List[Dict]:
        """List available tools from the server"""
        if not self.client:
            await self.connect()
        return await self.client.list_tools()
```

### 3. Update MCP Client (`lab_agent/mcp/client.py`)
Replace the complex Flake2DClient with the new FastMCP client:

```python
# In _initialize_tools method
if self.tool_manager.is_tool_active("flake_2d"):
    from .fastmcp_flake_client import FastMCPFlakeClient
    self.tool_groups["flake_2d"] = FastMCPFlakeClient()
    self.logger.info("MCP client: Initialized FastMCP 2D Flake client")
```

### 4. Update Tool Calling in Chatbox (`lab_agent/tools/llm_chatbox.py`)
The chatbox can now directly call FastMCP tools without translation:

```python
# In _prepare_tools_for_llm method
if self.tool_manager.is_tool_active("flake_2d"):
    # Get tools directly from FastMCP server
    flake_client = self.mcp_client.tool_groups.get("flake_2d")
    if flake_client:
        tools = await flake_client.list_tools()
        # Tools are already in FastMCP format, just add them
        for tool in tools:
            mcp_tools.append(tool)
```

### 5. Benefits of This Approach

**Before (Current Implementation):**
- 600+ lines in `flake_2d_client.py`
- Complex proxy implementation
- Manual HTTP calls and error handling
- Tool definition duplication
- Maintenance burden for API changes

**After (FastMCP Client):**
- ~50 lines total
- Direct server connection
- Automatic tool discovery
- No proxy/wrapper needed
- Server updates automatically reflected

### 6. Code Reduction Summary
- **Delete**: `flake_2d_client.py` (600+ lines)
- **Delete**: Server wrapper code in `mcp_server.py` for flake tools
- **Add**: `fastmcp_flake_client.py` (~50 lines)
- **Net reduction**: ~550 lines (>90% reduction)

### 7. Migration Steps
1. Install FastMCP package
2. Create new `fastmcp_flake_client.py`
3. Update `client.py` to use FastMCP client
4. Update tool loading in `llm_chatbox.py`
5. Test with existing recursive tool calling
6. Remove old `flake_2d_client.py` once verified

## Key Advantages
- **Simplicity**: Direct server connection, no proxy layer
- **Maintainability**: Server changes don't require client updates
- **Performance**: Fewer intermediate layers
- **Type Safety**: FastMCP handles typing automatically
- **Tool Discovery**: Automatic tool listing from server
- **Error Handling**: Built into FastMCP protocol

## Technical Details

### Current Tool Flow
```
GPT → llm_chatbox → mcp_client → flake_2d_client → HTTP calls → External Server
```

### New FastMCP Flow
```
GPT → llm_chatbox → fastmcp_client → External FastMCP Server
```

### Tool Format Compatibility
FastMCP tools use a standard format that's compatible with OpenAI's function calling:
```python
{
    "name": "tool_name",
    "description": "Tool description",
    "parameters": {
        "type": "object",
        "properties": {...},
        "required": [...]
    }
}
```

### Connection Management
The FastMCP client handles:
- Connection pooling
- Automatic reconnection
- Request/response serialization
- Error handling and retries

## Server-Side FastMCP Implementation (Reference)

For the server side, the implementation would look like:

```python
from fastmcp import FastMCP
import cv2
import numpy as np

mcp = FastMCP("2d_flake_server")

@mcp.tool
async def connect_server(url: str = "http://0.0.0.0:8000") -> Dict:
    """Connect to 2D flake server and get available models."""
    # Server logic here
    return {"connected": True, "models": [...]}

@mcp.tool  
async def upload_image(image_path: str) -> Dict:
    """Upload flake image for analysis."""
    # Upload logic here
    return {"uploaded": True, "filename": "..."}

@mcp.tool
async def classify_flake(model_name: str, image_filename: str) -> Dict:
    """Classify flake quality using specified model."""
    # Classification logic here
    return {"quality": "Good", "confidence": 0.95}

if __name__ == "__main__":
    mcp.run()  # Starts the FastMCP server
```

This approach leverages the fact that the server already speaks FastMCP, eliminating the need for our complex proxy implementation entirely!