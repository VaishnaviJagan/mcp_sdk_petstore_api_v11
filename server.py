"""Dynamic MCP Server implementation."""
from typing import Dict, Any, List, Optional
import httpx
import mcp.types as types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.responses import Response
import logging
from auth_handler import AuthHandler

logger = logging.getLogger(__name__)


class APIRequestError(Exception):
    """Custom exception for API request failures."""
    pass


class APIClient:
    """Handles HTTP requests to the target API."""
    
    def __init__(self, base_url: str, auth_handler: Optional[AuthHandler] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the target API
            auth_handler: Authentication handler
        """
        self.base_url = base_url.rstrip('/')

        # Protocol constants
        HTTP_PROTOCOL = "http"
        HTTPS_PROTOCOL = "https"
        PROTOCOL_SEPARATOR = "://"

        # Ensure base_url has protocol
        http_prefix = HTTP_PROTOCOL + PROTOCOL_SEPARATOR
        https_prefix = HTTPS_PROTOCOL + PROTOCOL_SEPARATOR

        if self.base_url.startswith('/'):
            # Relative path, assume localhost with HTTP for development
            protocol = HTTP_PROTOCOL if "localhost" in self.base_url or "127.0.0.1" in self.base_url else HTTPS_PROTOCOL
            self.base_url = f"{protocol}{PROTOCOL_SEPARATOR}localhost{self.base_url}"
        elif not self.base_url.startswith((http_prefix, https_prefix)):
            # Missing protocol - use HTTPS for security (localhost gets HTTP)
            protocol = HTTP_PROTOCOL if "localhost" in self.base_url or "127.0.0.1" in self.base_url else HTTPS_PROTOCOL
            self.base_url = f"{protocol}{PROTOCOL_SEPARATOR}{self.base_url}" 
            
        self.auth_handler = auth_handler
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.debug(f"Initialized APIClient for {self.base_url}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def execute_request(
        self,
        method: str,
        path: str,
        path_params: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Endpoint path (e.g., /users/{id})
            path_params: Path parameters to substitute
            query_params: Query parameters
            headers: Request headers
            body: Request body
            
        Returns:
            API response data
        """
        # 1. Substitute path parameters
        url_path = path
        if path_params:
            for key, value in path_params.items():
                url_path = url_path.replace(f"{{{key}}}", str(value))
        
        url = f"{self.base_url}{url_path}"
        
        # 2. Prepare headers
        request_headers = {}
        if self.auth_handler:
            request_headers.update(self.auth_handler.get_headers())
        
        if headers:
            request_headers.update(headers)
            
        # 3. Prepare query params
        request_query = {}
        if self.auth_handler:
            request_query.update(self.auth_handler.get_query_params())
            
        if query_params:
            request_query.update(query_params)
            
        # 4. Execute request
        logger.info(f"Executing {method} {url}")
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=request_query,
                headers=request_headers,
                json=body if body else None
            )
            
            # Raise for error status
            response.raise_for_status()
            
            # Return JSON if possible, else text
            try:
                return response.json()
            except (ValueError, TypeError):
                return {"data": response.text}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise APIRequestError(f"API request failed: {e.response.status_code} - {e.response.text}") from e
        except (httpx.RequestError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(f"Request failed: {e}")
            raise APIRequestError(f"Request failed: {str(e)}") from e


class ToolExecutor:
    """Executes MCP tools by calling the API client."""
    
    def __init__(self, api_client: APIClient, tools_metadata: Dict[str, Dict]):
        """
        Initialize tool executor.
        
        Args:
            api_client: Initialized API client
            tools_metadata: Metadata for each tool (method, path, etc.)
                            Keyed by tool name.
        """
        self.api_client = api_client
        self.tools_metadata = tools_metadata
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a specific tool.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments provided by the LLM
            
        Returns:
            Tool execution result
        """
        if tool_name not in self.tools_metadata:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        metadata = self.tools_metadata[tool_name]
        method = metadata["method"]
        path = metadata["path"]
        
        # Separate arguments into path, query, header, and body
        path_params = {}
        query_params = {}
        header_params = {}
        body = None
        
        # We need to know which param goes where.
        # Ideally, metadata should contain this info.
        # For now, we'll infer based on path placeholders and conventions.
        
        # 1. Extract path params
        # Path params are defined in the path string like {id}
        import re
        path_keys = re.findall(r"\{(\w+)\}", path)
        
        for key in path_keys:
            if key in arguments:
                path_params[key] = arguments.pop(key)
            else:
                # Check if argument matches without braces (e.g. 'petId' for '{petId}')
                pass
        
        # 2. Extract header params (prefixed with header_)
        keys_to_remove = []
        for key, value in arguments.items():
            if key.startswith("header_"):
                real_key = key.replace("header_", "")
                header_params[real_key] = str(value)
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            arguments.pop(key)
            
        # 3. Handle body
        # If there's a 'body' argument, use it as the request body
        if "body" in arguments:
            body = arguments.pop("body")
        elif method in ["POST", "PUT", "PATCH"] and arguments:
            # If no explicit body param, but arguments remain and it's a body-method,
            # treat remaining args as body properties (flattened body)
            body = arguments
            arguments = {} # Consumed all args
            
        # 4. Remaining args are query params
        query_params = arguments
        
        logger.info(f"Executing tool {tool_name}: {method} {path}")
        
        try:
            result = await self.api_client.execute_request(
                method=method,
                path=path,
                path_params=path_params,
                query_params=query_params,
                headers=header_params,
                body=body
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"error": str(e)}


class DynamicMCPServer:
    """
    Dynamic MCP Server that serves tools generated from OpenAPI.
    """
    
    def __init__(
        self, 
        session_id: str, 
        title: str, 
        base_url: str,
        tools: List[Dict], 
        auth_handler: Optional[AuthHandler] = None
    ):
        """
        Initialize Dynamic MCP Server.
        
        Args:
            session_id: Unique session ID
            title: Server title
            base_url: Target API base URL
            tools: List of MCP tool definitions
            auth_handler: Authentication handler
        """
        self.session_id = session_id
        self.title = title
        self.tools = tools
        
        # Initialize API Client and Tool Executor
        self.api_client = APIClient(base_url, auth_handler)
        
        # Create metadata map for executor
        tools_metadata = {
            t["name"]: t["metadata"] for t in tools
        }
        self.executor = ToolExecutor(self.api_client, tools_metadata)
        
        # Initialize MCP Server
        self.app = Server(title)
        self.transport = None
        
        # Register handlers
        self._register_handlers()
        
        logger.info(f"Initialized DynamicMCPServer '{title}' with {len(tools)} tools")

    def _register_handlers(self):
        """Register MCP tool handlers."""
        
        @self.app.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name=tool["name"],
                    description=tool["description"],
                    inputSchema=tool["inputSchema"]
                )
                for tool in self.tools
            ]
            
        @self.app.call_tool()
        async def call_tool(name: str, arguments: Any) -> List[types.TextContent]:
            """Execute a tool."""
            logger.info(f"MCP Tool Call: {name}")
            
            try:
                result = await self.executor.execute_tool(name, arguments)
                
                # Format result as text
                import json
                text_content = json.dumps(result, indent=2, default=str)
                
                return [types.TextContent(type="text", text=text_content)]
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def handle_sse(self, request: Request) -> Response:
        """
        Handle SSE connection request.
        
        Args:
            request: Starlette/FastAPI request
            
        Returns:
            SSE response
        """
        import mcp.server.sse

        # The endpoint must match the router's path structure:
        # /api/v1/byom/test/messages/{session_id}
        endpoint = f"/api/v1/byom/test/messages/{self.session_id}"
        self.transport = mcp.server.sse.SseServerTransport(endpoint)
        
        async with self.transport.connect_sse(request.scope, request.receive, request._send) as streams:
            read_stream, write_stream = streams
            
            # Create initialization options
            init_options = self.app.create_initialization_options()
            
            await self.app.run(
                read_stream, 
                write_stream, 
                initialization_options=init_options
            )

    def handle_messages(self, request: Request) -> Response:
        """
        Handle client messages (POST).

        Args:
            request: Starlette/FastAPI request

        Returns:
            Response
        """
        if not self.transport:
             return Response("Session not active", status_code=400)

        class MCPMessageResponse(Response):
            """Custom response that delegates to MCP transport."""
            def __init__(self, transport):
                self.transport = transport
                super().__init__()

            async def __call__(self, scope, receive, send):
                await self.transport.handle_post_message(scope, receive, send)

        return MCPMessageResponse(self.transport)

    async def shutdown(self):
        """Shutdown server resources."""
        await self.api_client.close()
