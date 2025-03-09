import sys, asyncio,msvcrt,os
from monday_config import mcp, board_schema, logger

if __name__ == "__main__":
    logger.debug("Starting server main program")
    
    if sys.platform == 'win32':
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    
    logger.debug("Arguments received: " + str(sys.argv))

    transport_type = 'stdio'
    if "--transport" in sys.argv and len(sys.argv) > sys.argv.index("--transport") + 1:
        if sys.argv[sys.argv.index("--transport") + 1] in ["stdio", "http"]:
            transport_type = sys.argv[sys.argv.index("--transport") + 1]
    logger.debug(f"Using transport: {transport_type}")
    
    try:
        asyncio.run(board_schema.initialize())
        
        import monday_tools
        import monday_resources
        
        logger.debug("Starting server...")
        mcp.run(transport=transport_type)
        
    except Exception as e:
        logger.critical(f"Fatal server error: {str(e)}", exc_info=True)
        sys.exit(1)