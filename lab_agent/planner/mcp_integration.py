"""
Integration between LangGraph planner and existing MCP system

Provides the bridge between the LangGraph-based task execution
and the existing MCP tools and servers.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .agent_state import AgentState, TaskNode, TaskStatus
from ..playground.mcp_manager import MCPManager
from ..utils.logger import get_logger


class MCPTaskExecutor:
    """
    Executes TaskNodes using MCP tools
    
    Bridges the gap between LangGraph task nodes and the
    existing MCP server infrastructure.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self.logger = get_logger(__name__)
    
    async def execute_node_with_mcp(self, node: TaskNode, state: AgentState) -> Dict[str, Any]:
        """Execute a task node using available MCP tools"""
        
        self.logger.info(f"Executing node {node.node_id} with MCP tools: {node.tools}")
        
        results = {}
        
        try:
            # Execute each required tool
            for tool_name in node.tools:
                if await self._is_tool_available(tool_name):
                    tool_result = await self._execute_mcp_tool(tool_name, node, state)
                    results[tool_name] = tool_result
                else:
                    # Fallback to simulation if tool not available
                    self.logger.warning(f"Tool {tool_name} not available, using simulation")
                    results[tool_name] = await self._simulate_tool_execution(tool_name, node, state)
            
            # Aggregate results based on agent type
            aggregated_result = await self._aggregate_tool_results(node, results)
            
            return aggregated_result
            
        except Exception as e:
            self.logger.error(f"MCP tool execution failed for node {node.node_id}: {e}")
            raise
    
    async def _is_tool_available(self, tool_name: str) -> bool:
        """Check if an MCP tool is available"""
        
        # Parse tool name (e.g., "instrMCP.cryostat" -> server="instrMCP", tool="cryostat")
        if "." in tool_name:
            server_id, tool_id = tool_name.split(".", 1)
        else:
            server_id = "default"
            tool_id = tool_name
        
        # Check if server is available
        available_servers = self.mcp_manager.get_available_servers()
        for server in available_servers:
            if server["id"] == server_id and server["enabled"]:
                # Check if tool exists on server
                tools = self.mcp_manager.get_server_tools(server_id)
                return any(tool["name"] == tool_id for tool in tools)
        
        return False
    
    async def _execute_mcp_tool(self, tool_name: str, node: TaskNode, state: AgentState) -> Dict[str, Any]:
        """Execute a specific MCP tool"""
        
        # Parse tool name
        if "." in tool_name:
            server_id, tool_id = tool_name.split(".", 1)
        else:
            server_id = "default"
            tool_id = tool_name
        
        # Get tool definition
        tools = self.mcp_manager.get_server_tools(server_id)
        tool_def = None
        for tool in tools:
            if tool["name"] == tool_id:
                tool_def = tool
                break
        
        if not tool_def:
            raise ValueError(f"Tool {tool_id} not found on server {server_id}")
        
        # Prepare tool arguments from node parameters
        tool_args = await self._prepare_tool_arguments(tool_id, tool_def, node, state)
        
        # Execute the tool
        result = self.mcp_manager.execute_tool(tool_id, tool_args, tool_def)
        
        self.logger.info(f"MCP tool {tool_name} executed successfully")
        return result
    
    async def _prepare_tool_arguments(self, tool_id: str, tool_def: Dict[str, Any], 
                                    node: TaskNode, state: AgentState) -> Dict[str, Any]:
        """Prepare arguments for MCP tool execution"""
        
        # Start with node parameters
        args = node.params.copy()
        
        # Add context from state
        args["task_id"] = state["task_spec"].task_id
        args["runlevel"] = state["runlevel"]
        args["memory_namespace"] = state["memory_namespace"]
        
        # Tool-specific argument preparation
        if tool_id == "cryostat":
            # Cryostat control
            if "target_T" in args:
                args["target_temperature"] = args.pop("target_T")
        
        elif tool_id == "sweep":
            # Measurement sweep
            if "type" in args:
                args["sweep_type"] = args.pop("type")
            if "range" in args:
                args["voltage_range"] = args.pop("range")
        
        elif tool_id == "analyze_paper":
            # ArXiv paper analysis
            if "title" not in args and "abstract" not in args:
                # Extract from task goal if not provided
                args["query"] = state["task_spec"].goal
        
        elif tool_id == "snap_image":
            # Microscope image capture
            if "save_path" not in args:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                args["save_path"] = f"{state['memory_namespace']}/image_{timestamp}.tiff"
        
        # Filter arguments based on tool schema
        if "inputSchema" in tool_def and "properties" in tool_def["inputSchema"]:
            valid_params = tool_def["inputSchema"]["properties"].keys()
            filtered_args = {k: v for k, v in args.items() if k in valid_params}
            return filtered_args
        
        return args
    
    async def _simulate_tool_execution(self, tool_name: str, node: TaskNode, 
                                     state: AgentState) -> Dict[str, Any]:
        """Simulate tool execution when actual tool is not available"""
        
        # Parse tool name
        if "." in tool_name:
            server_id, tool_id = tool_name.split(".", 1)
        else:
            tool_id = tool_name
        
        # Simulate based on tool type
        if tool_id == "cryostat":
            await asyncio.sleep(0.1)  # Simulate operation time
            return {
                "status": "simulated",
                "temperature": node.params.get("target_T", "4 K"),
                "message": "Cryostat operation simulated"
            }
        
        elif tool_id == "sweep":
            await asyncio.sleep(0.1)
            return {
                "status": "simulated",
                "data_points": 1000,
                "filename": f"sim_sweep_{datetime.now().strftime('%H%M%S')}.dat",
                "message": "Measurement sweep simulated"
            }
        
        elif tool_id == "analyze_paper":
            await asyncio.sleep(0.1)
            return {
                "status": "simulated",
                "relevance_score": 2,
                "summary": "Simulated paper analysis",
                "message": "Paper analysis simulated"
            }
        
        elif tool_id == "snap_image":
            await asyncio.sleep(0.1)
            return {
                "status": "simulated",
                "image_path": f"sim_image_{datetime.now().strftime('%H%M%S')}.tiff",
                "resolution": "1024x1024",
                "message": "Image capture simulated"
            }
        
        else:
            # Generic simulation
            await asyncio.sleep(0.1)
            return {
                "status": "simulated",
                "message": f"Tool {tool_id} simulated"
            }
    
    async def _aggregate_tool_results(self, node: TaskNode, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from multiple tools into a coherent node result"""
        
        aggregated = {
            "node_id": node.node_id,
            "agent": node.agent,
            "status": "completed",
            "tool_results": tool_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # Agent-specific aggregation
        if node.agent.startswith("worker.cooldown"):
            # Cooldown aggregation
            cryostat_result = tool_results.get("instrMCP.cryostat", {})
            temp_result = tool_results.get("instrMCP.temperature", {})
            
            aggregated.update({
                "final_temperature": cryostat_result.get("temperature", temp_result.get("value", "unknown")),
                "cooldown_status": cryostat_result.get("status", "unknown"),
                "operation_type": "cooldown"
            })
        
        elif node.agent.startswith("worker.sweep"):
            # Measurement sweep aggregation
            sweep_result = tool_results.get("instrMCP.sweep", {})
            daq_result = tool_results.get("instrMCP.daq", {})
            
            aggregated.update({
                "data_file": sweep_result.get("filename", daq_result.get("output_file", "unknown")),
                "data_points": sweep_result.get("data_points", daq_result.get("samples", 0)),
                "operation_type": "measurement"
            })
        
        elif node.agent.startswith("consultant.arxiv"):
            # Literature research aggregation
            search_result = tool_results.get("arxiv.search", {})
            score_result = tool_results.get("paper.score", {})
            
            aggregated.update({
                "papers_found": search_result.get("count", 0),
                "relevance_scores": score_result.get("scores", []),
                "operation_type": "research"
            })
        
        elif node.agent.startswith("assistant."):
            # Administrative task aggregation
            aggregated.update({
                "operation_type": "administrative",
                "tasks_completed": len([r for r in tool_results.values() 
                                      if r.get("status") == "completed"])
            })
        
        # Add error information if any tools failed
        failed_tools = [name for name, result in tool_results.items() 
                       if result.get("status") == "error"]
        if failed_tools:
            aggregated["failed_tools"] = failed_tools
            aggregated["status"] = "partial_failure"
        
        return aggregated


class MCPResourceManager:
    """
    Manages MCP server resources and connections for the planner
    
    Handles server lifecycle, resource allocation, and load balancing.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self.logger = get_logger(__name__)
        self.resource_usage = {}
    
    async def allocate_resources_for_task(self, state: AgentState) -> Dict[str, Any]:
        """Allocate MCP resources needed for a task"""
        
        required_servers = set()
        required_tools = set()
        
        # Collect all required resources from task graph
        for node in state["task_graph"].values():
            for tool_name in node.tools:
                required_tools.add(tool_name)
                if "." in tool_name:
                    server_id = tool_name.split(".")[0]
                    required_servers.add(server_id)
        
        # Check server availability
        available_servers = self.mcp_manager.get_available_servers()
        server_status = {}
        
        for server_id in required_servers:
            server_available = any(s["id"] == server_id and s["enabled"] 
                                 for s in available_servers)
            server_status[server_id] = server_available
        
        # Check tool availability
        tool_status = {}
        for tool_name in required_tools:
            if "." in tool_name:
                server_id, tool_id = tool_name.split(".", 1)
                if server_status.get(server_id, False):
                    tools = self.mcp_manager.get_server_tools(server_id)
                    tool_available = any(t["name"] == tool_id for t in tools)
                    tool_status[tool_name] = tool_available
                else:
                    tool_status[tool_name] = False
            else:
                # Built-in or generic tool
                tool_status[tool_name] = True
        
        allocation_result = {
            "required_servers": list(required_servers),
            "required_tools": list(required_tools),
            "server_status": server_status,
            "tool_status": tool_status,
            "all_available": all(server_status.values()) and all(tool_status.values())
        }
        
        self.logger.info(f"Resource allocation for task {state['task_spec'].task_id}: "
                        f"{'available' if allocation_result['all_available'] else 'partial'}")
        
        return allocation_result
    
    async def release_resources_for_task(self, state: AgentState):
        """Release MCP resources after task completion"""
        
        task_id = state["task_spec"].task_id
        if task_id in self.resource_usage:
            del self.resource_usage[task_id]
        
        self.logger.info(f"Released resources for task {task_id}")


class MCPToolAdapter:
    """
    Adapts MCP tools to work with LangGraph nodes
    
    Provides a consistent interface for executing MCP tools
    from within LangGraph workflows.
    """
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self.executor = MCPTaskExecutor(mcp_manager)
        self.resource_manager = MCPResourceManager(mcp_manager)
        self.logger = get_logger(__name__)
    
    async def execute_node(self, node: TaskNode, state: AgentState) -> Dict[str, Any]:
        """Execute a task node using MCP tools"""
        
        # Check resource allocation
        allocation = await self.resource_manager.allocate_resources_for_task(state)
        
        if not allocation["all_available"]:
            # Some resources unavailable - could fall back to simulation
            self.logger.warning(f"Not all resources available for node {node.node_id}")
        
        # Execute with MCP tools
        result = await self.executor.execute_node_with_mcp(node, state)
        
        # Release resources
        await self.resource_manager.release_resources_for_task(state)
        
        return result