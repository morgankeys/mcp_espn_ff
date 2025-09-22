import sys
from mcp.server.fastmcp import FastMCP
from .tools import create_tools


def log_error(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> None:
    log_error("Initializing FastMCP server...")
    mcp = FastMCP("espn-fantasy-football", dependancies=["espn-api", "playwright"])
    create_tools(mcp)
    log_error("Starting MCP server...")
    mcp.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error(f"ERROR DURING SERVER INITIALIZATION: {str(e)}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        log_error("Server failed to start, but kept running for logging. Press Ctrl+C to exit.")
        import time
        while True:
            time.sleep(10)


