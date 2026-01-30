# mcp_sdk_petstore_api_v11 - MCP Server

This is a standalone MCP (Model Context Protocol) server generated from an OpenAPI specification.

## What is this?

This package contains everything needed to run an MCP server that exposes API endpoints as tools that can be used by AI assistants like Claude, ChatGPT, and others that support the MCP protocol.

**Transport Mode**: This server uses **SSE (Server-Sent Events)** transport - it runs as an HTTP server that MCP clients connect to via a URL.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

## Quick Start

1. **Extract the package**:
   ```bash
   unzip mcp_sdk_petstore_api_v11.zip
   cd mcp_sdk_petstore_api_v11
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure authentication** (if your API requires it):
   - Edit `config.json` and update the `auth_config` section
   - See the "Authentication" section below for examples

4. **Run the server**:
   ```bash
   python main.py
   ```

5. **Note the MCP URL** from the output:
   ```
   MCP Connection URL:
     http://localhost:8000/sse
   ```

6. **Connect from your MCP client** using this URL

## Running the Server

Start the server with:

```bash
python main.py
```

You should see output like:

```
============================================================
MCP Server is starting...
Server Name: mcp_sdk_petstore_api_v11
Tools Available: X

MCP Connection URL:
  http://localhost:8000/sse

Health Check:
  http://localhost:8000/health

Server will be available at: 0.0.0.0:8000
============================================================
```

The server will continue running until you press Ctrl+C.

### Changing Host/Port

Edit `config.json` to change the host or port:

```json
{
  "host": "0.0.0.0",
  "port": 8000
}
```

- `0.0.0.0` means the server listens on all network interfaces
- Use `127.0.0.1` or `localhost` to only allow local connections
- Change `port` to any available port number

## Connecting MCP Clients

### Using the MCP URL

Your MCP client needs the **SSE endpoint URL**: `http://localhost:8000/sse`

### Claude Desktop (SSE Mode)

If your Claude Desktop supports SSE transport, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp_sdk_petstore_api_v11": {
      "url": "http://localhost:8000/sse",
      "transport": "sse"
    }
  }
}
```

### Cursor / Custom MCP Clients

Configure your client to connect to the SSE endpoint:
- **URL**: `http://localhost:8000/sse`
- **Transport**: SSE / Server-Sent Events
- **Method**: GET (for SSE connection), POST (for messages endpoint at `/messages`)

### Testing with curl

Verify the server is running:

```bash
# Health check
curl http://localhost:8000/health

# Connect to SSE endpoint (will stream events)
curl -N http://localhost:8000/sse
```

## Understanding the Package Structure

### config.json
Contains the server configuration:
- `server_name`: The name of your MCP server
- `base_url`: The base URL of the target API that this MCP server will proxy
- `host`: Server host (default: `0.0.0.0`)
- `port`: Server port (default: `8000`)
- `auth_config`: Authentication configuration for the target API (optional)
- `session_id`: Unique identifier for this server instance

### tools.json
Contains the tool definitions generated from your OpenAPI specification. These are the endpoints that will be available as tools to AI assistants.

Each tool includes:
- `name`: Unique tool identifier
- `description`: What the tool does
- `inputSchema`: JSON Schema defining the tool's parameters
- `metadata`: HTTP method, path, and other endpoint details

### main.py
The entry point that:
1. Loads configuration and tools
2. Sets up authentication handler
3. Creates the DynamicMCPServer instance
4. Starts the HTTP server with SSE endpoints
5. Exposes the MCP protocol over HTTP

### server.py
Contains the core MCP server logic:
- `DynamicMCPServer`: Main MCP server implementation
- `APIClient`: Handles HTTP requests to your target API
- `ToolExecutor`: Executes tools by calling the API client

### auth_handler.py
Handles authentication for API calls:
- Supports API Key (header/query), Bearer tokens, Basic auth, OAuth2
- Automatically adds auth headers/params to API requests

## Authentication

If your API requires authentication, update the `auth_config` in `config.json`:

### API Key (Header)
```json
{
  "type": "apiKey",
  "credentials": {
    "location": "header",
    "name": "X-API-Key",
    "value": "your-api-key-here"
  }
}
```

### API Key (Query)
```json
{
  "type": "apiKey",
  "credentials": {
    "location": "query",
    "name": "api_key",
    "value": "your-api-key-here"
  }
}
```

### Bearer Token
```json
{
  "type": "http",
  "credentials": {
    "scheme": "bearer",
    "token": "your-bearer-token-here"
  }
}
```

### Basic Auth
```json
{
  "type": "http",
  "credentials": {
    "scheme": "basic",
    "username": "your-username",
    "password": "your-password"
  }
}
```

## Frequently Asked Questions

### Q: What is the MCP server URL?

**A**: The MCP server URL is displayed when you start the server:

```
MCP Connection URL:
  http://localhost:8000/sse
```

By default, it's `http://localhost:8000/sse`. You can change the host/port in `config.json`.

### Q: How do I know if the server is running?

**A**: Several ways to check:

1. **Look at the console output** - you'll see the startup message with the URL
2. **Check the health endpoint**:
   ```bash
   curl http://localhost:8000/health
   ```
3. **View server logs** - all requests are logged to the console
4. **Connect with an MCP client** - if it can list/use tools, the server is working

### Q: Can I access the server from another machine?

**A**: Yes! Change the host in `config.json`:

```json
{
  "host": "0.0.0.0",
  "port": 8000
}
```

Then use your machine's IP address or hostname:
- From same network: `http://192.168.1.100:8000/sse`
- With proper DNS/routing: `http://your-hostname:8000/sse`

**Security Note**: When exposing the server publicly, ensure the target API credentials are properly secured and consider adding authentication to the MCP server itself.

### Q: Can multiple clients connect simultaneously?

**A**: Yes! The server uses SSE transport and can handle multiple concurrent client connections. Each client will have its own session.

## Troubleshooting

### Import Errors
Make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

If using a virtual environment, ensure it's activated before running.

### Port Already in Use
If you see an error like `Address already in use`:
1. Change the port in `config.json` to a different number
2. Or stop the process using that port:
   ```bash
   # Find process using port 8000
   lsof -i :8000
   # Kill it
   kill -9 <PID>
   ```

### Cannot Connect to MCP Server
- Verify the server is running (check console output)
- Test the health endpoint: `curl http://localhost:8000/health`
- Check firewall settings if connecting from another machine
- Ensure the MCP client is using the correct URL

### Connection Issues to Target API
- Verify the `base_url` in `config.json` is correct
- Check that the target API is accessible from your machine
- Verify authentication credentials if the API requires it
- Test the API endpoints directly with curl to ensure they work
- Check server logs for detailed error messages

### Tool Execution Fails
- Check the server console for error messages
- Verify the tool definitions in `tools.json` match the API spec
- Ensure the target API endpoint is functioning correctly
- Verify authentication is configured if the API requires it
- Check if required parameters are being passed correctly

### Server Crashes or Won't Start
- Check Python version: `python --version` (needs 3.10+)
- Review error messages in the console
- Ensure `config.json` and `tools.json` are valid JSON
- Try running with verbose logging to see more details

## Files Description

- `main.py`: Entry point for the MCP server
- `server.py`: MCP server implementation
- `auth_handler.py`: Authentication handler for API calls
- `config.json`: Server configuration
- `tools.json`: Tool definitions from OpenAPI spec
- `requirements.txt`: Python dependencies
- `README.md`: This file

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify your configuration in `config.json`
3. Ensure the target API is accessible

## Generated

This MCP server was generated on 2026-01-30 11:25:01 using the Integra BYOM platform.
