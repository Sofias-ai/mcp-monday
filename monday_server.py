import sys
import logging
import asyncio
from typing import Dict, Any
from mcp.server.fastmcp import Context
from monday_config import mcp, board_schema, logger

if __name__ == "__main__":
    logger.debug("Starting server main program")
    
    # Force UTF-8 for the entire process
    if sys.platform == 'win32':
        import msvcrt
        import os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    
    logger.debug("Arguments received: " + str(sys.argv))
    transport_type = 'stdio' if "--transport" in sys.argv and sys.argv[sys.argv.index("--transport") + 1] == "stdio" else 'default'
    logger.debug(f"Using transport: {transport_type}")
    
    try:
        # Initialize board schema before starting the server
        asyncio.run(board_schema.initialize())
        
        # Import tools and resources
        import monday_tools
        import monday_resources
        
        logger.debug("Starting server...")
        mcp.run(transport=transport_type)
    except Exception as e:
        logger.critical(f"Fatal server error: {str(e)}", exc_info=True)
        sys.exit(1)