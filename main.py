#!/usr/bin/env python3
"""
Standalone MCP Server: mcp_sdk_petstore_api_v11
Generated on: 2026-01-30 11:25:01

This server uses SSE (Server-Sent Events) transport for MCP communication.
It runs as an HTTP server that MCP clients can connect to.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
from auth_handler import AuthHandler
from server import DynamicMCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global server instance
mcp_server: DynamicMCPServer = None


def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, 'r') as f:
        return json.load(f)


def load_tools():
    """Load tool definitions from tools.json."""
    tools_path = Path(__file__).parent / "tools.json"
    with open(tools_path, 'r') as f:
        data = json.load(f)
        return data.get("tools", [])


async def handle_sse(request):
    """Handle SSE connection for MCP protocol."""
    return await mcp_server.handle_sse(request)


async def handle_messages(request):
    """Handle client messages (POST)."""
    return mcp_server.handle_messages(request)


async def health_check(request):
    """Health check endpoint."""
    return Response(
        json.dumps({
            "status": "healthy",
            "server": mcp_server.title if mcp_server else "Not initialized",
            "tools_count": len(mcp_server.tools) if mcp_server else 0
        }),
        media_type="application/json"
    )


# Define routes
routes = [
    Route("/sse", handle_sse),
    Route("/messages/{session_id:path}", handle_messages, methods=["POST"]),
    Route("/health", health_check),
]

# Create Starlette app
app = Starlette(routes=routes)


def initialize_server():
    """Initialize the MCP server."""
    global mcp_server
    
    logger.info("Initializing MCP Server...")
    
    # Load configuration
    config = load_config()
    logger.info(f"Loaded configuration for server: {config['server_name']}")
    
    # Load tools
    tools = load_tools()
    logger.info(f"Loaded {len(tools)} tools")
    
    # Create auth handler
    auth_handler = AuthHandler(config.get("auth_config"))
    
    # Create MCP server
    mcp_server = DynamicMCPServer(
        session_id=config.get("session_id", "standalone"),
        title=config["server_name"],
        base_url=config["base_url"],
        tools=tools,
        auth_handler=auth_handler
    )
    
    logger.info(f"MCP Server '{config['server_name']}' initialized successfully")
    return config


def main():
    """Main entry point."""
    # Initialize server
    config = initialize_server()
    
    # Get host and port from config or use defaults
    host = config.get("host", "0.0.0.0")
    port = config.get("port", 8000)
    
    # Build MCP URL
    protocol = "http" if host in ["localhost", "127.0.0.1", "0.0.0.0"] else "https"
    display_host = "localhost" if host == "0.0.0.0" else host
    mcp_url = f"{protocol}://{display_host}:{port}/sse"
    
    logger.info("=" * 60)
    logger.info(f"MCP Server is starting...")
    logger.info(f"Server Name: {config['server_name']}")
    logger.info(f"Tools Available: {len(mcp_server.tools)}")
    logger.info(f"")
    logger.info(f"MCP Connection URL:")
    logger.info(f"  {mcp_url}")
    logger.info(f"")
    logger.info(f"Health Check:")
    logger.info(f"  {protocol}://{display_host}:{port}/health")
    logger.info(f"")
    logger.info(f"Server will be available at: {host}:{port}")
    logger.info("=" * 60)
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        import sys
        sys.exit(1)
