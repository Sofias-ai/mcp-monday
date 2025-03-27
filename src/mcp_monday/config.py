"""
Configuration for the MCP-Monday integration.
Handles environment variables, logging, and client initialization.
"""
import os
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from monday import MondayClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('monday_server.log'), logging.StreamHandler()]
)
logger = logging.getLogger('monday_mcp')

# Load environment variables
load_dotenv()

# Configuration
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")

if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
    logger.error("Missing required environment variables: MONDAY_API_KEY and MONDAY_BOARD_ID must be set")

# Initialize MCP server
mcp = FastMCP(
    name="Monday.com MCP Server", 
    instructions="This server provides tools to interact with Monday.com boards and items."
)

# Initialize Monday client
monday_client = MondayClient(token=MONDAY_API_KEY)