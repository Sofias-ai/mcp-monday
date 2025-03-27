"""
Monday.com MCP Server implementation.
Provides the server functionality for the MCP-Monday integration.
"""
import sys
import os
from .config import mcp, logger

def configure_windows_encoding():
    """Configure Windows encoding if needed."""
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')

def determine_transport():
    """Determine the transport type from command line arguments."""
    transport_type = 'stdio'
    
    if "--transport" in sys.argv and len(sys.argv) > sys.argv.index("--transport") + 1:
        transport = sys.argv[sys.argv.index("--transport") + 1]
        if transport in ["stdio", "sse"]:
            transport_type = transport
            
    logger.info(f"Using transport: {transport_type}")
    return transport_type

def main():
    """
    Start the Monday.com MCP server.
    This is the main entry point for the server.
    """
    logger.info("Starting Monday.com MCP Server")
    
    # Configure Windows encoding if needed
    configure_windows_encoding()
    
    # Determine transport type
    transport_type = determine_transport()
    
    try:
        # Import tools and resources modules
        from . import tools
        from . import resources
        
        # Run the MCP server
        logger.info("Starting MCP server...")
        mcp.run(transport=transport_type)
        
    except Exception as e:
        logger.critical(f"Fatal server error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()