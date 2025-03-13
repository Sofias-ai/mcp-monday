from monday_config import mcp, monday_client, MONDAY_BOARD_ID, logger

@mcp.tool(name="get_board_data", description="Get all data from the Monday.com board including columns and items")
async def get_board_data():
    """Get all data from the Monday.com board"""
    try:
        # Get board data using the Monday client directly
        board_data = monday_client.boards.fetch_boards_by_id(MONDAY_BOARD_ID)
        columns_data = monday_client.boards.fetch_columns_by_board_id(MONDAY_BOARD_ID)
        items_data = monday_client.boards.fetch_items_by_board_id(MONDAY_BOARD_ID, limit=100)
        
        # Format response
        result = {
            "board": {
                "id": MONDAY_BOARD_ID,
                "name": board_data["data"]["boards"][0]["name"] if "data" in board_data else "",
                "columns_count": len(columns_data["data"]["boards"][0]["columns"]) if "data" in columns_data else 0,
                "items_count": len(items_data["data"]["boards"][0]["items_page"]["items"]) if "data" in items_data else 0
            },
            "columns": columns_data["data"]["boards"][0]["columns"] if "data" in columns_data else [],
            "items": items_data["data"]["boards"][0]["items_page"]["items"] if "data" in items_data else []
        }
        
        return result
    except Exception as e:
        logger.error(f"Error getting board data: {str(e)}")
        return {"success": False, "error": str(e)}

# Helper function to get column mapping
async def get_column_mapping():
    """Get a mapping from column names to IDs"""
    columns_data = monday_client.boards.fetch_columns_by_board_id(MONDAY_BOARD_ID)
    columns_map = {}
    if "data" in columns_data and "boards" in columns_data["data"]:
        for col in columns_data["data"]["boards"][0]["columns"]:
            columns_map[col["title"].lower()] = col["id"]
            columns_map[col["id"]] = col["id"]  # Also allow direct use of IDs
    return columns_map

@mcp.tool(name="search_board_items", description="Search for items in a Monday.com board by field and value")
async def search_board_items(field: str, value: str):
    """Search for items in a Monday.com board by field and value"""
    try:
        # Get column mapping
        columns_map = await get_column_mapping()
        
        # Determine column ID
        column_id = columns_map.get(field.lower(), field)
        
        # Search using the Monday client
        items_data = monday_client.items.fetch_items_by_column_value(
            board_id=MONDAY_BOARD_ID,
            column_id=column_id,
            value=value
        )
        
        # Process results
        items = []
        if "data" in items_data and "items_page_by_column_values" in items_data["data"]:
            # Get column titles for better readability
            columns_data = monday_client.boards.fetch_columns_by_board_id(MONDAY_BOARD_ID)
            columns_dict = {}
            if "data" in columns_data and "boards" in columns_data["data"]:
                for col in columns_data["data"]["boards"][0]["columns"]:
                    columns_dict[col["id"]] = col["title"]
            
            # Format each item
            for item in items_data["data"]["items_page_by_column_values"]["items"]:
                formatted_item = {
                    "id": item["id"],
                    "name": item["name"],
                    "column_values": []
                }
                
                # Add column values with proper titles
                for cv in item["column_values"]:
                    if cv.get("text"):
                        title = columns_dict.get(cv["id"], cv["id"])
                        formatted_item["column_values"].append({
                            "column_id": cv["id"],
                            "title": title,
                            "value": cv["text"]
                        })
                
                items.append(formatted_item)
        
        return {
            "success": True,
            "matches_found": len(items),
            "items": items
        }
    except Exception as e:
        logger.error(f"Error searching items: {str(e)}")
        return {"success": False, "error": str(e)}

@mcp.tool(name="delete_board_items", description="Delete items from a Monday.com board by field and value match")
async def delete_board_items(field: str, value: str):
    """Delete items from a Monday.com board by field and value match"""
    try:
        # First search for matching items
        search_result = await search_board_items(field, value)
        
        # Check if any items were found
        if not search_result["success"] or search_result["matches_found"] == 0:
            return {
                "success": False,
                "message": "No items found to delete",
                "deleted_count": 0
            }
        
        # Delete each item found
        deleted_items = []
        errors = []
        
        for item in search_result["items"]:
            try:
                # Use the Monday client to delete the item
                result = monday_client.items.delete_item_by_id(item["id"])
                if "data" in result and "delete_item" in result["data"]:
                    deleted_items.append(item)
                else:
                    errors.append(f"Error deleting item {item['id']}: Unexpected response")
            except Exception as e:
                errors.append(f"Error deleting item {item['id']}: {str(e)}")
        
        return {
            "success": len(deleted_items) > 0,
            "message": f"Deleted {len(deleted_items)} of {len(search_result['items'])} items",
            "deleted_count": len(deleted_items),
            "deleted_items": deleted_items,
            "errors": errors if errors else None
        }
    except Exception as e:
        logger.error(f"Error deleting items: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "deleted_count": 0
        }

@mcp.tool(name="create_board_item", description="Create a new item in the Monday.com board")
async def create_board_item(item_name: str, column_values: dict, group_id: str = None):
    """Create a new item in the Monday.com board"""
    try:
        # Get default group if none is provided
        if not group_id:
            groups_data = monday_client.groups.get_groups_by_board([MONDAY_BOARD_ID])
            if "data" in groups_data and "boards" in groups_data["data"]:
                groups = groups_data["data"]["boards"][0].get("groups", [])
                if groups:
                    group_id = groups[0]["id"]
        
        # Check if we have a valid group
        if not group_id:
            return {
                "success": False,
                "message": "No group ID provided and no default group found"
            }
        
        # Use the Monday client to create the item
        result = monday_client.items.create_item(
            board_id=int(MONDAY_BOARD_ID),
            group_id=group_id,
            item_name=item_name,
            column_values=column_values
        )
        
        # Process result
        if "data" in result and "create_item" in result["data"] and result["data"]["create_item"]:
            created_item = result["data"]["create_item"]
            return {
                "success": True,
                "message": "Item created successfully",
                "item": {
                    "id": created_item["id"],
                    "name": item_name,
                    "board_id": MONDAY_BOARD_ID,
                    "group_id": group_id
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to create item",
                "response": result
            }
    except Exception as e:
        logger.error(f"Error creating item: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@mcp.tool(name="update_board_item", description="Update an existing item in the Monday.com board")
async def update_board_item(item_id: str, column_values: dict):
    """Update an existing item in the Monday.com board"""
    try:
        # Use the Monday client to update the item
        result = monday_client.items.change_multiple_column_values(
            board_id=int(MONDAY_BOARD_ID),
            item_id=item_id, 
            column_values=column_values
        )
        
        # Process result
        if "data" in result and "change_multiple_column_values" in result["data"]:
            updated_item = result["data"]["change_multiple_column_values"]
            return {
                "success": True,
                "message": "Item updated successfully",
                "item": {
                    "id": updated_item["id"],
                    "name": updated_item["name"],
                    "board_id": MONDAY_BOARD_ID
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to update item",
                "response": result
            }
    except Exception as e:
        logger.error(f"Error updating item: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }