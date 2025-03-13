import sys, os
from monday_config import mcp, logger

if __name__ == "__main__":
    logger.info("Starting Monday.com MCP Server")
    
    # Configure Windows encoding if needed
    if sys.platform == 'win32':
        
        import msvcrt
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    
    # Determine transport type
    transport_type = 'stdio'
    
    if "--transport" in sys.argv and len(sys.argv) > sys.argv.index("--transport") + 1:
        transport = sys.argv[sys.argv.index("--transport") + 1]
        if transport in ["stdio", "sse"]:
            transport_type = transport
            
    logger.info(f"Using transport: {transport_type}")
    
    try:
        # Import tools and resources modules
        import monday_tools
        import monday_resources
        
        # Run the MCP server
        logger.info("Starting MCP server...")
        mcp.run(transport=transport_type)
        
    except Exception as e:
        logger.critical(f"Fatal server error: {str(e)}", exc_info=True)
        sys.exit(1)