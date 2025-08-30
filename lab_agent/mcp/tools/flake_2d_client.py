"""
2D Material Flake Classification MCP Client for Lab Agent.

This module provides MCP tools that connect to an external 2D flake classification
MCP server, acting as a bridge/proxy to expose the external server's capabilities
to the Lab Agent GPT-5-mini system.
"""

import base64
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from mcp import Tool

from .base_tool import BaseTool


class Flake2DClient(BaseTool):
    """MCP client tools for connecting to external 2D flake classification MCP server"""
    
    def __init__(self):
        super().__init__("flake_2d_client", "Client tools for external 2D flake classification MCP server")
        self.external_server_url = None
        self.connection_status = "disconnected"
        self.server_capabilities = {}
        self.last_connection_check = None
        
        if not HTTPX_AVAILABLE:
            self.logger.warning("httpx not available. Install with: pip install httpx")
    
    def get_tool_definitions(self) -> List[Tool]:
        """Get all tool definitions for this tool group"""
        return [
            Tool(
                name="connect_2d_flake_server",
                description="Connect to external 2D flake classification MCP server and discover its capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_url": {
                            "type": "string",
                            "description": "Base URL of the external MCP server (e.g., 'http://192.168.1.100:8001')"
                        },
                        "test_connection": {
                            "type": "boolean",
                            "description": "Whether to test the connection immediately",
                            "default": True
                        }
                    },
                    "required": ["server_url"]
                }
            ),
            Tool(
                name="get_2d_flake_models",
                description="Get list of available neural network models from the external server",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="upload_2d_flake_image",
                description="Upload an image file to the external 2D flake classification server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to upload (can be filename only if uploaded via web interface)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional description of the image",
                            "default": ""
                        }
                    },
                    "required": ["image_path"]
                }
            ),
            Tool(
                name="classify_2d_flake",
                description="Classify the quality of a 2D material flake using specified neural network model",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": "Name of the neural network model to use (get from get_2d_flake_models)"
                        },
                        "image_filename": {
                            "type": "string",
                            "description": "Filename of the uploaded image (from upload_2d_flake_image response)"
                        }
                    },
                    "required": ["model_name", "image_filename"]
                }
            ),
            Tool(
                name="get_2d_flake_history",
                description="Get history of 2D flake quality predictions from the external server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of history entries to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_2d_flake_server_status",
                description="Check the health and status of the external 2D flake classification server",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool"""
        self.logger.info(f"Executing 2D flake client tool: {tool_name}")
        
        if not HTTPX_AVAILABLE:
            return self.format_error_response(
                "Missing httpx dependency. Install with: pip install httpx"
            )
        
        try:
            if tool_name == "connect_2d_flake_server":
                return await self._connect_2d_flake_server(arguments)
            elif tool_name == "get_2d_flake_models":
                return await self._get_2d_flake_models(arguments)
            elif tool_name == "upload_2d_flake_image":
                return await self._upload_2d_flake_image(arguments)
            elif tool_name == "classify_2d_flake":
                return await self._classify_2d_flake(arguments)
            elif tool_name == "get_2d_flake_history":
                return await self._get_2d_flake_history(arguments)
            elif tool_name == "get_2d_flake_server_status":
                return await self._get_2d_flake_server_status(arguments)
            else:
                return self.format_error_response(f"Unknown tool: {tool_name}")
        except Exception as e:
            self.logger.error(f"Tool execution error: {e}")
            return self.format_error_response(str(e))
    
    async def _connect_2d_flake_server(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to external 2D flake classification MCP server"""
        server_url = arguments.get("server_url", "").strip()
        test_connection = arguments.get("test_connection", True)
        
        if not server_url:
            return self.format_error_response("Server URL is required")
        
        # Normalize URL
        if not server_url.startswith(('http://', 'https://')):
            server_url = f"http://{server_url}"
        
        self.external_server_url = server_url
        
        if not test_connection:
            self.connection_status = "configured"
            return self.format_success_response(
                {"server_url": server_url, "status": "configured", "tested": False},
                f"Server URL configured: {server_url}"
            )
        
        try:
            # Test basic connectivity with health endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                health_response = await client.get(f"{server_url}/health")
                health_response.raise_for_status()
                health_data = health_response.json()
            
            # Try to get MCP capabilities
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    capabilities_response = await client.get(f"{server_url}/.well-known/mcp-capabilities")
                    capabilities_response.raise_for_status()
                    self.server_capabilities = capabilities_response.json()
            except Exception as e:
                self.logger.warning(f"Could not get MCP capabilities: {e}")
                self.server_capabilities = {}
            
            self.connection_status = "connected"
            self.last_connection_check = datetime.now()
            
            response_data = {
                "server_url": server_url,
                "connection_status": "connected",
                "health_data": health_data,
                "mcp_capabilities": self.server_capabilities,
                "connected_at": self.last_connection_check.isoformat()
            }
            
            return self.format_success_response(
                response_data,
                f"Successfully connected to 2D flake MCP server at {server_url}"
            )
            
        except httpx.RequestError as e:
            self.connection_status = "error"
            return self.format_error_response(
                f"Failed to connect to server: {str(e)}",
                {"server_url": server_url, "error_type": "connection_error"}
            )
        except httpx.HTTPStatusError as e:
            self.connection_status = "error"
            return self.format_error_response(
                f"Server returned error: {e.response.status_code}",
                {"server_url": server_url, "status_code": e.response.status_code}
            )
    
    async def _get_2d_flake_models(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of available models from external server"""
        if not self._check_connection():
            return self.format_error_response("Not connected to external server. Use connect_2d_flake_server first.")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.external_server_url}/mcp/tools/list_models")
                response.raise_for_status()
                models_data = response.json()
            
            if models_data.get("success"):
                response_data = {
                    "server_url": self.external_server_url,
                    "models": models_data.get("models", []),
                    "model_count": models_data.get("count", 0),
                    "retrieved_at": datetime.now().isoformat()
                }
                
                return self.format_success_response(
                    response_data,
                    f"Retrieved {len(models_data.get('models', []))} available models"
                )
            else:
                return self.format_error_response(
                    f"Server error: {models_data.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            return self.format_error_response(
                f"Failed to get models: {str(e)}",
                {"server_url": self.external_server_url}
            )
    
    async def _upload_2d_flake_image(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Upload image to external server"""
        if not self._check_connection():
            return self.format_error_response("Not connected to external server. Use connect_2d_flake_server first.")
        
        image_path = arguments.get("image_path", "").strip()
        description = arguments.get("description", "")
        
        if not image_path:
            return self.format_error_response("Image path is required")
        
        # Check if image_path is just a filename (from web upload)
        if not os.path.exists(image_path):
            # Try looking in the uploads directory
            uploads_path = os.path.join(os.getcwd(), "uploads", "flake_images", image_path)
            if os.path.exists(uploads_path):
                image_path = uploads_path
            else:
                return self.format_error_response(f"Image file not found: {image_path}. Upload via Tools tab or provide full path.")
        
        # Check file size (50MB limit)
        file_size = os.path.getsize(image_path)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            return self.format_error_response(
                f"Image file too large: {file_size / (1024*1024):.1f}MB (max: 50MB)"
            )
        
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            original_filename = os.path.basename(image_path)
            
            # Upload to external server
            async with httpx.AsyncClient(timeout=30.0) as client:
                upload_data = {
                    "image_data": image_data,
                    "filename": original_filename
                }
                response = await client.post(
                    f"{self.external_server_url}/mcp/tools/upload_image",
                    data=upload_data
                )
                response.raise_for_status()
                upload_result = response.json()
            
            if upload_result.get("success"):
                response_data = {
                    "server_url": self.external_server_url,
                    "original_filename": original_filename,
                    "uploaded_filename": upload_result.get("filename"),
                    "file_size_bytes": upload_result.get("size", file_size),
                    "description": description,
                    "uploaded_at": datetime.now().isoformat(),
                    "server_path": upload_result.get("path", "")
                }
                
                return self.format_success_response(
                    response_data,
                    f"Successfully uploaded '{original_filename}' to external server"
                )
            else:
                return self.format_error_response(
                    f"Upload failed: {upload_result.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            return self.format_error_response(
                f"Failed to upload image: {str(e)}",
                {"image_path": image_path}
            )
    
    async def _classify_2d_flake(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Classify 2D flake quality using external server"""
        if not self._check_connection():
            return self.format_error_response("Not connected to external server. Use connect_2d_flake_server first.")
        
        model_name = arguments.get("model_name", "").strip()
        image_filename = arguments.get("image_filename", "").strip()
        
        if not model_name:
            return self.format_error_response("Model name is required")
        if not image_filename:
            return self.format_error_response("Image filename is required")
        
        try:
            # Make prediction request to external server
            async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for ML inference
                prediction_data = {
                    "model_name": model_name,
                    "image_filename": image_filename
                }
                response = await client.post(
                    f"{self.external_server_url}/mcp/tools/predict_flake_quality",
                    data=prediction_data
                )
                response.raise_for_status()
                prediction_result = response.json()
            
            if prediction_result.get("success"):
                # Format the response for our system
                confidence = prediction_result.get("confidence", {})
                quality = prediction_result.get("quality", "Unknown")
                
                # Create analysis summary
                analysis_summary = self._create_analysis_summary(quality, confidence)
                
                response_data = {
                    "classification_result": {
                        "model_name": model_name,
                        "image_filename": image_filename,
                        "prediction_class": prediction_result.get("prediction"),
                        "quality_assessment": quality,
                        "confidence_scores": confidence,
                        "timestamp": prediction_result.get("timestamp", datetime.now().isoformat())
                    },
                    "server_info": {
                        "server_url": self.external_server_url,
                        "external_mcp_server": True
                    },
                    "analysis_summary": analysis_summary,
                    "recommendation": self._get_quality_recommendation(quality, confidence)
                }
                
                return self.format_success_response(
                    response_data,
                    f"Successfully classified flake: {quality} (using {model_name})"
                )
            else:
                return self.format_error_response(
                    f"Classification failed: {prediction_result.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            return self.format_error_response(
                f"Failed to classify flake: {str(e)}",
                {"model_name": model_name, "image_filename": image_filename}
            )
    
    async def _get_2d_flake_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get prediction history from external server"""
        if not self._check_connection():
            return self.format_error_response("Not connected to external server. Use connect_2d_flake_server first.")
        
        limit = arguments.get("limit", 10)
        limit = max(1, min(50, limit))
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.external_server_url}/mcp/tools/get_prediction_history",
                    params={"limit": limit}
                )
                response.raise_for_status()
                history_result = response.json()
            
            if history_result.get("success"):
                history_entries = history_result.get("history", [])
                
                response_data = {
                    "server_url": self.external_server_url,
                    "history_entries": history_entries,
                    "total_predictions": history_result.get("total_predictions", 0),
                    "returned_count": len(history_entries),
                    "limit": limit,
                    "retrieved_at": datetime.now().isoformat()
                }
                
                return self.format_success_response(
                    response_data,
                    f"Retrieved {len(history_entries)} prediction history entries"
                )
            else:
                return self.format_error_response(
                    f"Failed to get history: {history_result.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            return self.format_error_response(
                f"Failed to get prediction history: {str(e)}"
            )
    
    async def _get_2d_flake_server_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check status of external server"""
        if not self.external_server_url:
            return self.format_error_response("No server URL configured. Use connect_2d_flake_server first.")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                health_response = await client.get(f"{self.external_server_url}/health")
                health_response.raise_for_status()
                health_data = health_response.json()
            
            self.connection_status = "connected"
            self.last_connection_check = datetime.now()
            
            response_data = {
                "server_url": self.external_server_url,
                "connection_status": "healthy",
                "health_data": health_data,
                "last_checked": self.last_connection_check.isoformat(),
                "mcp_capabilities": self.server_capabilities
            }
            
            return self.format_success_response(
                response_data,
                "External 2D flake server is healthy and responsive"
            )
            
        except Exception as e:
            self.connection_status = "error"
            return self.format_error_response(
                f"Server is not responding: {str(e)}",
                {"server_url": self.external_server_url}
            )
    
    def _check_connection(self) -> bool:
        """Check if we have a valid connection to external server"""
        return (self.external_server_url is not None and 
                self.connection_status in ["connected", "configured"])
    
    def _create_analysis_summary(self, quality: str, confidence: Dict) -> str:
        """Create human-readable analysis summary"""
        if quality.lower() == "good quality":
            good_conf = confidence.get("good_quality", 0)
            return f"The 2D material flake exhibits good quality characteristics with {good_conf:.1%} confidence. This suggests the flake has suitable properties for further research or device applications."
        elif quality.lower() == "bad quality":
            bad_conf = confidence.get("bad_quality", 0)
            return f"The 2D material flake shows poor quality characteristics with {bad_conf:.1%} confidence. The flake may have defects, contamination, or unsuitable structural properties."
        else:
            return f"Quality assessment: {quality}"
    
    def _get_quality_recommendation(self, quality: str, confidence: Dict) -> str:
        """Get recommendation based on quality assessment"""
        if quality.lower() == "good quality":
            good_conf = confidence.get("good_quality", 0)
            if good_conf > 0.8:
                return "Strong recommendation: This flake is suitable for device fabrication or detailed characterization."
            elif good_conf > 0.6:
                return "Moderate recommendation: This flake shows promise but may benefit from additional analysis."
            else:
                return "Weak recommendation: Consider additional measurements to confirm quality."
        elif quality.lower() == "bad quality":
            return "Not recommended: This flake is unlikely to be suitable for high-quality device applications."
        else:
            return "Additional analysis recommended to determine suitability."
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Base class execute method - not used directly"""
        raise NotImplementedError("Use execute_tool method instead")
    
    def get_tool_definition(self) -> Tool:
        """Base class method - not used directly"""
        raise NotImplementedError("Use get_tool_definitions method instead")