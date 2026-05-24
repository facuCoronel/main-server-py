"""Entry point for the FastFixPro MCP server.

Run with:
    python mcp_server.py              # stdio transport (default, for Claude Desktop / Claude Code)
    python mcp_server.py --transport sse --port 8001   # SSE transport

Claude Desktop config example (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "main-server-fastfixpro": {
          "command": "python",
          "args": ["C:/Proyectos/main-server-py/mcp_server.py"],
          "env": {
            "FASTFIXPRO_API_BASE_URL": "http://localhost:5000",
            "FASTFIXPRO_API_TOKEN": "your-token-here"
          }
        }
      }
    }
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

from src.mcp.server import mcp  # noqa: E402  (import after logging setup)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FastFixPro MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="Transport protocol")
    parser.add_argument("--port", type=int, default=8001, help="Port for SSE transport")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
