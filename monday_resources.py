from typing import Dict, Any
import json
from datetime import datetime, timedelta
import httpx

from monday_config import (
    mcp, board_schema, MONDAY_API_KEY, 
    MONDAY_API_URL, MONDAY_BOARD_ID, logger
)

# Resource Cache Configuration
CACHE_DURATION = timedelta(minutes=5)
resource_cache: Dict[str, Any] = {}
last_cache_update: Dict[str, datetime] = {}

async def check_and_refresh_cache(resource_id: str) -> None:
    """Check if cache needs refresh and update if necessary"""
    now = datetime.now()
    if (resource_id not in last_cache_update or 
        now - last_cache_update[resource_id] > CACHE_DURATION):
        await refresh_cache(resource_id)

async def refresh_cache(resource_id: str) -> None:
    """Refresh the cache for a specific resource"""
    try:
        if resource_id == "schema":
            await board_schema.initialize()
            resource_cache[resource_id] = board_schema.schema
        elif resource_id == "column_types":
            # Query para obtener todos los tipos de columna disponibles
            query = """
                query {
                    column_types: boards(ids: %s) {
                        columns {
                            id
                            title
                            type
                            settings_str
                            width
                            archived
                            description
                        }
                        board_kind
                        template
                        communication
                        permissions
                        state
                    }
                }
            """ % MONDAY_BOARD_ID

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
                if "data" in data and "column_types" in data["data"]:
                    resource_cache[resource_id] = data["data"]["column_types"]
        elif resource_id == "board_metadata":
            # Query para obtener metadata del tablero
            query = """
                query {
                    boards(ids: %s) {
                        name
                        board_folder_id
                        board_kind
                        description
                        state
                        workspace {
                            id
                            name
                            kind
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
                        subscribers {
                            id
                            name
                        }
                        owner {
                            id
                            name
                            email
                        }
                        updates {
                            id
                            body
                            created_at
                            creator {
                                id
                                name
                            }
                        }
                        views {
                            id
                            name
                            type
                            settings_str
                        }
                        permissions
                        board_folder_id
                    }
                }
            """ % MONDAY_BOARD_ID

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
                    resource_cache[resource_id] = data["data"]["boards"][0]

        last_cache_update[resource_id] = datetime.now()
        logger.info(f"Cache refreshed for resource: {resource_id}")
    except Exception as e:
        logger.error(f"Error refreshing cache for {resource_id}: {str(e)}")
        raise

@mcp.resource("monday://board/schema")
async def get_board_schema():
    """Get the complete board schema including column configurations"""
    try:
        logger.debug("get_board_schema called")
        await check_and_refresh_cache("schema")
        await check_and_refresh_cache("board_metadata")
        
        # Combinar schema con metadata
        board_info = board_schema.get_columns_info()
        if "board_metadata" in resource_cache:
            board_info.update({
                "workspace": resource_cache["board_metadata"].get("workspace", {}),
                "description": resource_cache["board_metadata"].get("description", ""),
                "subscribers": resource_cache["board_metadata"].get("subscribers", []),
                "updates": resource_cache["board_metadata"].get("updates", []),
                "views": resource_cache["board_metadata"].get("views", [])
            })
        
        logger.debug(f"Returning schema data: {json.dumps(board_info, indent=2)}")
        return board_info
        
    except Exception as e:
        logger.error(f"Error retrieving board schema: {str(e)}", exc_info=True)
        return {"error": str(e)}

@mcp.resource("monday://board/columns/{column_id}")
async def get_column_info(column_id: str) -> str:
    """
    Get detailed information about a specific column
    
    Args:
        column_id: The ID of the column to retrieve
    
    Returns:
        JSON string with column metadata including type, settings, and validation rules
    """
    try:
        if column_id not in board_schema.columns_config:
            return json.dumps({"error": f"Column {column_id} not found"})
        
        column_info = board_schema.columns_config[column_id]
        format_info = board_schema.get_column_format(column_id)
        
        # Obtener información de validación específica del tipo
        validation_info = board_schema._get_validation_rules(
            column_info["type"],
            column_info["settings"]
        )
        
        response = {
            "id": column_id,
            "title": column_info["title"],
            "type": column_info["type"],
            "settings": column_info["settings"],
            "format": format_info,
            "validation_rules": validation_info,
            "width": column_info.get("width"),
            "archived": column_info.get("archived", False),
            "description": column_info.get("description", "")
        }
        
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Error retrieving column info: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.resource("monday://board/column_types")
async def get_column_types() -> str:
    """
    Get information about all available column types and their configurations
    Returns a JSON string with column type definitions and settings
    """
    try:
        await check_and_refresh_cache("column_types")
        column_types_data = resource_cache.get("column_types", {})
        
        # Añadir información de validación para cada tipo
        for column in column_types_data.get("columns", []):
            column_type = column.get("type")
            settings = json.loads(column.get("settings_str", "{}"))
            validation_rules = board_schema._get_validation_rules(column_type, settings)
            column["validation_rules"] = validation_rules
        
        return json.dumps(column_types_data, indent=2)
    except Exception as e:
        logger.error(f"Error retrieving column types: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.resource("monday://board/metadata")
async def get_board_metadata() -> str:
    """
    Get comprehensive board metadata including workspace info, views, and updates
    """
    try:
        await check_and_refresh_cache("board_metadata")
        return json.dumps(resource_cache.get("board_metadata", {}), indent=2)
    except Exception as e:
        logger.error(f"Error retrieving board metadata: {str(e)}")
        return json.dumps({"error": str(e)})