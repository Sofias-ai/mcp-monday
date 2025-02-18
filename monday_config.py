from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
from monday_types import ColumnDefinition, ColumnFormat, ValidationResult
from monday_column_handlers import COLUMN_TYPE_HANDLERS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monday_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('monday_config')

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Monday.com Configuration
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")

logger.info(f"Monday.com Configuration: URL={MONDAY_API_URL}, Board ID={MONDAY_BOARD_ID}")
logger.debug(f"API Key found: {bool(MONDAY_API_KEY)}")

# Create MCP instance
mcp = FastMCP("monday-server")

class BoardSchema:
    def __init__(self):
        self.schema = None
        self.columns_config = {}
        self.columns = {}
        self.last_update = None
        self._handlers = COLUMN_TYPE_HANDLERS

    async def initialize(self) -> None:
        if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
            raise ValueError("Missing API_KEY or BOARD_ID")

        query = """
            query {
                boards(ids: %s) {
                    name
                    board_folder_id
                    board_kind
                    columns {
                        id
                        title
                        type
                        settings_str
                        width
                        archived
                        description
                    }
                    groups {
                        id
                        title
                        color
                        position
                    }
                    tags {
                        id
                        name
                        color
                    }
                    owner {
                        id
                        name
                    }
                    permissions
                    state
                    workspace_id
                    board_folder_id
                }
            }
        """ % MONDAY_BOARD_ID

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    MONDAY_API_URL,
                    json={"query": query},
                    headers={
                        "Authorization": MONDAY_API_KEY,
                        "Content-Type": "application/json",
                    }
                )
                data = response.json()

                if "data" in data and "boards" in data["data"]:
                    board = data["data"]["boards"][0]
                    self.schema = board

                    for col in board["columns"]:
                        settings = json.loads(col["settings_str"]) if col["settings_str"] else {}
                        
                        # Configuración antigua (mantener compatibilidad)
                        self.columns_config[col["id"]] = {
                            "title": col["title"],
                            "type": col["type"],
                            "settings": settings,
                            "width": col.get("width"),
                            "archived": col.get("archived", False),
                            "description": col.get("description", "")
                        }
                        
                        col_format = ColumnFormat(
                            column_type=col["type"],
                            settings=settings
                        )
                        
                        self.columns[col["id"]] = ColumnDefinition(
                            id=col["id"],
                            title=col["title"],
                            format=col_format,
                            handler_class=self._get_handler_class(col["type"])
                        )

                    self.last_update = datetime.now()
                    logger.info("Board schema initialized successfully")
                else:
                    raise ValueError("Invalid API response format")

        except Exception as e:
            logger.error(f"Schema initialization error: {str(e)}")
            raise

    def _get_handler_class(self, column_type: str) -> Optional[str]:
        """Get the appropriate handler class for a column type"""
        if column_type in self._handlers:
            return self._handlers[column_type].__class__.__name__
        logger.warning(f"No handler found for column type: {column_type}")
        return None

    def _get_validation_rules(self, column_type: str, settings: Dict) -> Dict:
        """Get validation rules for a column type"""
        try:
            handler = self._handlers.get(column_type)
            if handler:
                rules = handler.get_validation_rules(settings)
                logger.debug(f"Validation rules for {column_type}: {json.dumps(rules, indent=2)}")
                return rules
            logger.warning(f"No handler found for column type: {column_type}")
            return {}
        except Exception as e:
            logger.error(f"Error getting validation rules: {str(e)}")
            return {}

    def get_column_format(self, column_id: str) -> Dict[str, Any]:
        """Get the required format for a specific column"""
        if column_id not in self.columns:
            raise ValueError(f"Unknown column ID: {column_id}")

        column = self.columns[column_id]
        return {
            "type": column.format.column_type,
            "settings": column.format.settings,
            "validation_rules": self._get_validation_rules(
                column.format.column_type,
                column.format.settings
            )
        }

    def format_value(self, column_id: str, value: Any) -> str:
        """Format a value according to its column type"""
        if column_id not in self.columns:
            raise ValueError(f"Unknown column ID: {column_id}")

        column = self.columns[column_id]
        handler = self._handlers.get(column.format.column_type)
        
        if not handler:
            raise ValueError(f"No handler for column type: {column.format.column_type}")
            
        try:
            column_value = handler.format_value(value, column.format.settings)
            if not column_value.validation_result.is_valid:
                raise ValueError(column_value.validation_result.message)
                
            return json.dumps(column_value.formatted_value)
        except Exception as e:
            logger.error(f"Error formatting value for column {column_id}: {str(e)}")
            raise ValueError(f"Invalid value format for column type {column.format.column_type}")

    def validate_column_value(self, column_id: str, value: Any) -> ValidationResult:
        """Validate a value for a specific column using appropriate handler"""
        if column_id not in self.columns:
            return ValidationResult(
                is_valid=False,
                message=f"Unknown column ID: {column_id}"
            )

        column = self.columns[column_id]
        handler = self._handlers.get(column.format.column_type)
        
        if not handler:
            return ValidationResult(
                is_valid=False,
                message=f"No handler available for column type: {column.format.column_type}"
            )

        try:
            return handler.validate_value(value, column.format.settings)
        except Exception as e:
            logger.error(f"Validation error for column {column_id}: {str(e)}")
            return ValidationResult(
                is_valid=False,
                message=f"Validation error: {str(e)}"
            )

    def get_columns_info(self) -> Dict[str, Any]:
        """Get complete board schema and columns information"""
        return {
            "board_info": {
                "name": self.schema.get("name"),
                "board_kind": self.schema.get("board_kind"),
                "workspace_id": self.schema.get("workspace_id"),
                "state": self.schema.get("state"),
                "permissions": self.schema.get("permissions", [])
            },
            "groups": self.schema.get("groups", []),
            "tags": self.schema.get("tags", []),
            "owner": self.schema.get("owner", {}),
            "columns": [
                {
                    "id": col_id,
                    "title": info.title,
                    "type": info.format.column_type,
                    "settings": info.format.settings,
                    "width": self.columns_config[col_id].get("width"),
                    "archived": self.columns_config[col_id].get("archived", False),
                    "description": self.columns_config[col_id].get("description", ""),
                    "validation_rules": self._get_validation_rules(
                        info.format.column_type,
                        info.format.settings
                    )
                }
                for col_id, info in self.columns.items()
            ]
        }

# Create schema instance
board_schema = BoardSchema()