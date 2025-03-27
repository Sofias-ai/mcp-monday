"""
MCP-Monday integration package.
Provides tools and functionality to interact with Monday.com from MCP.
"""

def main():
    """
    Main entry point for the mcp-monday application.
    Starts the MCP server for Monday.com integration.
    """
    from mcp_monday.server import main as server_main
    server_main()

if __name__ == "__main__":
    main()