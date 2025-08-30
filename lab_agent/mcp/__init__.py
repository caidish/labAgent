"""
MCP (Model Context Protocol) integration for Lab Agent.

This module provides MCP server and client functionality to enable
AI tools integration with the lab agent system.
"""

from .mcp_server import MCPServer
from .client import MCPClient

__all__ = ["MCPServer", "MCPClient"]