"""
MCP resources for Monday.com integration.
Provides resource handlers for accessing Monday.com data.
"""
import json
from datetime import datetime, timedelta
from functools import wraps
from .config import mcp, monday_client, MONDAY_BOARD_ID, logger

# Simplified cache system
CACHE = {"data": {}, "timestamp": {}, "duration": timedelta(minutes=5)}

def cached(key_template):
    """Compact decorator for resource caching"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate key with dynamic parameters
            key = key_template.format(*args, **kwargs, board=MONDAY_BOARD_ID)
            
            # Check cache
            if (key in CACHE["timestamp"] and 
                datetime.now() - CACHE["timestamp"][key] < CACHE["duration"]):
                return json.dumps(CACHE["data"][key])
            
            # Execute function and store in cache
            try:
                result = await func(*args, **kwargs)
                CACHE["data"][key] = result
                CACHE["timestamp"][key] = datetime.now()
                return json.dumps(result)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                return json.dumps({"error": str(e)})
        return wrapper
    return decorator

# Compact GraphQL queries
QUERY = {
    "schema": """query {{ 
        boards(ids: {board_id}) {{ 
            id name board_kind permissions 
            owner {{ id name }}
            groups {{ id title color position }}
            columns {{ id title type settings_str archived width description }}
            tags {{ id name color }}
        }}
    }}""",
    
    "items": """query {{ 
        boards(ids: {board_id}) {{ 
            items_page(limit: {limit}) {{ items {{ 
                id name column_values {{ id title text value }} group {{ id title }}
            }} }}
        }}
    }}""",
    
    "item": """query {{ 
        items(ids: {item_id}) {{ 
            id name column_values {{ id title text value }} group {{ id title }}
        }}
    }}"""
}

# Optimized data retrieval functions
async def fetch_data(query_key, **params):
    """Central function for executing GraphQL queries with parameters"""
    try:
        query = QUERY[query_key].format(**params)
        return monday_client.custom._query(query)
    except Exception as e:
        logger.error(f"Error in query {query_key}: {e}")
        return None

async def get_schema_data():
    """Get board schema"""
    response = await fetch_data("schema", board_id=MONDAY_BOARD_ID)
    
    if not response or "data" not in response or not response["data"].get("boards"):
        return {"board_info": {"id": MONDAY_BOARD_ID}, "columns": [], "groups": []}
    
    board = response["data"]["boards"][0]
    return {
        "board_info": {
            "id": str(MONDAY_BOARD_ID),
            "name": board.get("name", ""),
            "board_kind": board.get("board_kind", ""),
            "permissions": board.get("permissions", "")
        },
        "columns": board.get("columns", []),
        "groups": board.get("groups", []),
        "tags": board.get("tags", []),
        "owner": board.get("owner", {})
    }

async def get_items_data(limit=100):
    """Get board items"""
    try:
        response = await fetch_data("items", board_id=MONDAY_BOARD_ID, limit=limit)
        
        if response and "data" in response and "boards" in response["data"]:
            items = response["data"]["boards"][0]["items_page"]["items"]
            return {"count": len(items), "items": items}
        
        # Fallback method if GraphQL fails
        return await fallback_get_items()
    except Exception:
        return await fallback_get_items()

async def fallback_get_items():
    """Fallback method using standard API"""
    data = monday_client.boards.fetch_items_by_board_id(MONDAY_BOARD_ID, limit=100)
    items = data.get("data", {}).get("boards", [{}])[0].get("items_page", {}).get("items", [])
    return {"count": len(items), "items": items}

async def get_item_data(item_id):
    """Get a specific item"""
    response = await fetch_data("item", item_id=item_id)
    
    if response and "data" in response and response["data"].get("items"):
        return response["data"]["items"][0]
    
    # Fallback method
    data = monday_client.items.fetch_items_by_id([item_id])
    return data.get("data", {}).get("items", [None])[0]

# Optimized MCP resources
@mcp.resource("monday://board/schema")
@cached("schema:{board}")
async def get_board_schema():
    """Monday board schema"""
    return await get_schema_data()

@mcp.resource("monday://board/items")
@cached("items:{board}")
async def get_board_items():
    """Board items"""
    return await get_items_data()

@mcp.resource("monday://board/item/{item_id}")
@cached("item:{item_id}")
async def get_item(item_id):
    """Detailed information about a specific item"""
    item = await get_item_data(item_id)
    return item if item else {"error": f"Item {item_id} not found"}

@mcp.resource("monday://board/columns")
@cached("columns:{board}")
async def get_all_columns():
    """All columns in the board"""
    schema = await get_schema_data()
    return schema["columns"]

@mcp.resource("monday://board/columns/{column_id}")
@cached("column:{column_id}")
async def get_column_info(column_id):
    """Detailed information about a specific column"""
    schema = await get_schema_data()
    column = next((col for col in schema["columns"] if col["id"] == column_id), None)
    
    if not column:
        return {"error": f"Column {column_id} not found"}
    
    settings = json.loads(column["settings_str"]) if "settings_str" in column else {}
    return {
        "id": column["id"], 
        "title": column["title"], 
        "type": column["type"],
        "settings": settings, 
        "width": column.get("width"),
        "archived": column.get("archived", False),
        "description": column.get("description", "")
    }