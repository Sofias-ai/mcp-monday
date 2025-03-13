import json
from datetime import datetime, timedelta
from monday_config import mcp, monday_client, MONDAY_BOARD_ID, logger

# Simple cache system
CACHE_DURATION = timedelta(minutes=5)
cache = {}
cache_timestamps = {}

def is_cache_valid(key):
    """Check if cache for a specific resource is still valid"""
    return (key in cache_timestamps and
            datetime.now() - cache_timestamps[key] < CACHE_DURATION)

def update_cache(key, data):
    """Update the cache with new data"""
    cache[key] = data
    cache_timestamps[key] = datetime.now()
    return data

@mcp.resource("monday://board/schema")
async def get_board_schema():
    """Get the complete board schema"""
    cache_key = f"schema:{MONDAY_BOARD_ID}"
    
    try:
        # Check cache first
        if is_cache_valid(cache_key):
            return json.dumps(cache[cache_key])
        
        # Fetch fresh data using Monday client
        board_data = monday_client.boards.fetch_boards_by_id(MONDAY_BOARD_ID)
        columns_data = monday_client.boards.fetch_columns_by_board_id(MONDAY_BOARD_ID)
        groups_data = monday_client.groups.get_groups_by_board([MONDAY_BOARD_ID])
        
        # Build response with all relevant information
        result = {
            "board_info": {
                "id": MONDAY_BOARD_ID,
                "name": board_data["data"]["boards"][0]["name"],
                "board_kind": board_data["data"]["boards"][0]["board_kind"],
                "permissions": board_data["data"]["boards"][0]["permissions"],
            },
            "columns": columns_data["data"]["boards"][0]["columns"],
            "groups": groups_data["data"]["boards"][0]["groups"],
            "tags": board_data["data"]["boards"][0].get("tags", []),
            "owner": board_data["data"]["boards"][0].get("owner", {})
        }
        
        # Update cache and return result
        return json.dumps(update_cache(cache_key, result))
    
    except Exception as e:
        logger.error(f"Error retrieving board schema: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.resource("monday://board/columns/{column_id}")
async def get_column_info(column_id: str):
    """Get detailed information about a specific column"""
    cache_key = f"column:{column_id}"
    
    try:
        # Check cache first
        if is_cache_valid(cache_key):
            return json.dumps(cache[cache_key])
        
        # Get column information
        columns_data = monday_client.boards.fetch_columns_by_board_id(MONDAY_BOARD_ID)
        
        if "data" not in columns_data or "boards" not in columns_data["data"]:
            return json.dumps({"error": "Failed to get columns data"})
            
        columns = columns_data["data"]["boards"][0]["columns"]
        column = next((col for col in columns if col["id"] == column_id), None)
        
        if not column:
            return json.dumps({"error": f"Column {column_id} not found"})
            
        # Format column information
        settings = json.loads(column["settings_str"]) if "settings_str" in column else {}
        
        response = {
            "id": column["id"],
            "title": column["title"],
            "type": column["type"],
            "settings": settings,
            "width": column.get("width"),
            "archived": column.get("archived", False),
            "description": column.get("description", "")
        }
        
        # Update cache and return result
        return json.dumps(update_cache(cache_key, response))
    
    except Exception as e:
        logger.error(f"Error retrieving column info: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.resource("monday://board/items")
async def get_board_items():
    """Get all items from the board"""
    cache_key = f"items:{MONDAY_BOARD_ID}"
    
    try:
        # Check cache first
        if is_cache_valid(cache_key):
            return json.dumps(cache[cache_key])
            
        # Get board items
        items_data = monday_client.boards.fetch_items_by_board_id(MONDAY_BOARD_ID, limit=100)
        
        if "data" not in items_data or "boards" not in items_data["data"]:
            return json.dumps({"error": "Failed to get items data"})
        
        # Build response
        items = items_data["data"]["boards"][0]["items_page"]["items"]
        response = {
            "count": len(items),
            "items": items
        }
        
        # Update cache and return result
        return json.dumps(update_cache(cache_key, response))
    
    except Exception as e:
        logger.error(f"Error retrieving board items: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.resource("monday://board/item/{item_id}")
async def get_item(item_id: str):
    """Get detailed information about a specific item"""
    cache_key = f"item:{item_id}"
    
    try:
        # Check cache first
        if is_cache_valid(cache_key):
            return json.dumps(cache[cache_key])
            
        # Get item details
        item_data = monday_client.items.fetch_items_by_id([item_id])
        
        if "data" not in item_data or "items" not in item_data["data"]:
            return json.dumps({"error": f"Item {item_id} not found"})
        
        if not item_data["data"]["items"]:
            return json.dumps({"error": f"Item {item_id} not found"})
        
        # Return the item with its column values
        item = item_data["data"]["items"][0]
        
        # Update cache and return result
        return json.dumps(update_cache(cache_key, item))
    
    except Exception as e:
        logger.error(f"Error retrieving item details: {str(e)}")
        return json.dumps({"error": str(e)})