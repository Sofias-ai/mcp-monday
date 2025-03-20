import json
from functools import wraps
from monday_config import mcp, monday_client, MONDAY_BOARD_ID, logger
from mcp.server.fastmcp.server import Context

# Decorators and utilities to simplify tools
def error_handler(func):
    """Handles errors in tools consistently"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return {"success": False, "error": str(e)}
    return wrapper

async def load_schema(ctx):
    """Loads and parses the board schema"""
    schema_data = await ctx.read_resource("monday://board/schema")
    return json.loads(schema_data.content)

async def load_items(ctx):
    """Loads and parses board items"""
    items_data = await ctx.read_resource("monday://board/items")
    return json.loads(items_data.content)

def parse_column_options(columns):
    """Extracts column options for the assistant"""
    result = []
    for col in columns:
        info = {"id": col.get("id", ""), "title": col.get("title", ""), "type": col.get("type", "")}
        
        if "settings_str" in col and col["settings_str"]:
            try:
                settings = json.loads(col["settings_str"])
                if "labels" in settings: info["options"] = settings["labels"]
            except: pass
        
        result.append(info)
    return result

# Optimized MCP tools for Monday.com
@mcp.tool(name="get_board_schema", description="Get Monday.com board schema")
@error_handler
async def get_board_schema(ctx: Context):
    """Get board structure information (without items)"""
    schema = await load_schema(ctx)
    
    return {
        "board": {
            "id": MONDAY_BOARD_ID,
            "name": schema.get("board_info", {}).get("name", ""),
            "columns_count": len(schema.get("columns", [])),
            "groups_count": len(schema.get("groups", [])),
        },
        "columns": parse_column_options(schema.get("columns", [])),
        "groups": schema.get("groups", [])
    }

@mcp.tool(name="get_board_items", description="Get board items")
@error_handler
async def get_board_items(ctx: Context):
    """Get items from the Monday.com board"""
    items = await load_items(ctx)
    return {"count": items.get("count", 0), "items": items.get("items", [])}

@mcp.tool(name="get_board_data", description="Get combined schema and data")
@error_handler
async def get_board_data(ctx: Context):
    """Get combined schema and items (use caution with large boards)"""
    schema = await get_board_schema(ctx)
    items = await get_board_items(ctx)
    
    # If any failed, return the error
    if "success" in schema and not schema["success"]: return schema
    if "success" in items and not items["success"]: return items
    
    return {
        "board": schema["board"],
        "columns": schema["columns"],
        "groups": schema["groups"],
        "items": items["items"],
        "items_count": items["count"]
    }

@mcp.tool(name="search_board_items", description="Search items by field and value")
@error_handler
async def search_board_items(ctx: Context, field: str, value: str):
    """Search for board items by field and value"""
    schema = await load_schema(ctx)
    
    # Column mapping (by title and id)
    columns_map = {col["title"].lower(): col["id"] for col in schema.get("columns", [])}
    columns_map.update({col["id"]: col["id"] for col in schema.get("columns", [])})
    column_id = columns_map.get(field.lower(), field)
    
    # Execute search
    items_data = monday_client.items.fetch_items_by_column_value(
        board_id=MONDAY_BOARD_ID, column_id=column_id, value=value
    )
    
    # Process results
    items = []
    if "data" in items_data and "items_page_by_column_values" in items_data["data"]:
        columns_dict = {col["id"]: col["title"] for col in schema.get("columns", [])}
        
        for item in items_data["data"]["items_page_by_column_values"]["items"]:
            column_values = [
                {"column_id": cv["id"], "title": columns_dict.get(cv["id"], cv["id"]), "value": cv["text"]}
                for cv in item["column_values"] if cv.get("text")
            ]
            
            items.append({"id": item["id"], "name": item["name"], "column_values": column_values})
    
    return {"success": True, "matches_found": len(items), "items": items}

@mcp.tool(name="delete_board_items", description="Delete items by field and value")
@error_handler
async def delete_board_items(ctx: Context, field: str, value: str):
    """Delete board items that match field and value"""
    # Search for items
    search_result = await search_board_items(ctx, field, value)
    
    if not search_result["success"] or search_result["matches_found"] == 0:
        return {"success": False, "message": "No items found to delete", "deleted_count": 0}
    
    # Delete items
    deleted_items = []
    errors = []
    
    for item in search_result["items"]:
        try:
            result = monday_client.items.delete_item_by_id(item["id"])
            if "data" in result and "delete_item" in result["data"]:
                deleted_items.append(item)
            else:
                errors.append(f"Error deleting item {item['id']}")
        except Exception as e:
            errors.append(f"Error deleting item {item['id']}: {str(e)}")
    
    return {
        "success": len(deleted_items) > 0,
        "deleted_count": len(deleted_items),
        "deleted_items": deleted_items,
        "errors": errors if errors else None
    }

@mcp.tool(name="create_board_item", description="Create a new board item")
@error_handler
async def create_board_item(ctx: Context, item_name: str, column_values: dict, group_id: str = None):
    """Create a new item in the Monday.com board"""
    # Get default group if none provided
    if not group_id:
        schema = await load_schema(ctx)
        groups = schema.get("groups", [])
        group_id = groups[0]["id"] if groups else None
    
    if not group_id:
        return {"success": False, "message": "No group ID provided and no default found"}
    
    # Create item
    result = monday_client.items.create_item(
        board_id=int(MONDAY_BOARD_ID),
        group_id=group_id,
        item_name=item_name,
        column_values=column_values
    )
    
    # Process result
    if "data" in result and "create_item" in result["data"] and result["data"]["create_item"]:
        item = result["data"]["create_item"]
        return {"success": True, "item_id": item["id"], "name": item_name, "board_id": MONDAY_BOARD_ID}
    else:
        return {"success": False, "message": "Failed to create item"}

@mcp.tool(name="update_board_item", description="Update an existing item")
@error_handler
async def update_board_item(ctx: Context, item_id: str, column_values: dict):
    """Update an existing item in the Monday.com board"""
    result = monday_client.items.change_multiple_column_values(
        board_id=int(MONDAY_BOARD_ID),
        item_id=item_id, 
        column_values=column_values
    )
    
    if "data" in result and "change_multiple_column_values" in result["data"]:
        item = result["data"]["change_multiple_column_values"]
        return {"success": True, "item_id": item["id"], "name": item["name"]}
    else:
        return {"success": False, "message": "Failed to update item"}