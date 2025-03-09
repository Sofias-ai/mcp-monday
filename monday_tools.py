import json, httpx
from typing import Dict, Any, Optional, Tuple
from mcp.server.fastmcp import Context
from pydantic import BaseModel
from monday_config import mcp, board_schema, MONDAY_API_KEY, MONDAY_API_URL, MONDAY_BOARD_ID, logger

class SearchBoardItemsArguments(BaseModel): field: str; value: str
class CreateBoardItemArguments(BaseModel): item_name: str; column_values: Dict[str, Any]
class DeleteBoardItemsArguments(BaseModel): field: str; value: str

async def call_monday_api(query: str, variables: Optional[Dict] = None) -> Tuple[bool, Dict]:
    try:
        headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
        payload = {"query": query}
        if variables: payload["variables"] = variables
        async with httpx.AsyncClient() as client:
            response = await client.post(MONDAY_API_URL, json=payload, headers=headers)
        return (response.status_code == 200, response.json() if response.status_code == 200 
                else {"error": f"API error: {response.status_code} - {response.text}"})
    except Exception as e:
        return False, {"error": f"Request error: {str(e)}"}

@mcp.tool()
async def get_board_data(ctx: Context) -> str:
    if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
        return "Missing API_KEY or BOARD_ID in environment variables"
    
    query = """query { boards(ids: %s) { name, columns { id, title, type }, 
             items_page(limit: 100) { items { id, name, column_values { id, text, type, value } } } } }""" % MONDAY_BOARD_ID
    
    success, data = await call_monday_api(query)
    if not success: return json.dumps(data)
    
    if "data" in data and "boards" in data["data"]:
        board = data["data"]["boards"][0]
        columns_dict = {col["id"]: col["title"] for col in board["columns"]}
        for item in board["items_page"]["items"]:
            for col_value in item["column_values"]:
                col_value["title"] = columns_dict.get(col_value["id"], col_value["id"])
    
    return json.dumps(data)

@mcp.tool()
async def search_board_items(ctx: Context, args: SearchBoardItemsArguments) -> str:
    try:
        schema_data = json.loads(await get_board_data(ctx))
        if "data" not in schema_data or "boards" not in schema_data["data"]:
            return json.dumps({"success": False, "message": "Invalid schema format"})
        
        board = schema_data["data"]["boards"][0]
        columns = board.get("columns", [])
        column_map = {col['id']: col['title'] for col in columns}
        reverse_map = {col['title'].lower(): col['id'] for col in columns}
        search_field = reverse_map.get(args.field.lower(), args.field)
        
        query = """query { boards(ids: %s) { items_page(query_params: { rules: [{ column_id: "%s", 
                compare_value: "%s", operator: contains_terms }] }) { items { id, name, column_values 
                { id, text, type, value } } } } }""" % (MONDAY_BOARD_ID, search_field, args.value)
        
        success, result = await call_monday_api(query)
        if not success: 
            return json.dumps({"success": False, "message": result.get("error", "API Error")})
        
        items = []
        if "data" in result and "boards" in result["data"]:
            board_items = result["data"]["boards"][0].get("items_page", {}).get("items", [])
            for item in board_items:
                formatted = {"id": item["id"], "name": item["name"], "column_values": []}
                for col_value in item["column_values"]:
                    if col_value.get("text"):
                        formatted["column_values"].append({
                            "title": column_map.get(col_value["id"], col_value["id"]), 
                            "value": col_value["text"]
                        })
                items.append(formatted)
        
        return json.dumps({"success": True, "matches_found": len(items), "items": items}, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "message": f"Error: {str(e)}"}, indent=2)

@mcp.tool()
async def delete_board_items(ctx: Context, args: DeleteBoardItemsArguments) -> str:
    try:
        search_data = json.loads(await search_board_items(ctx, SearchBoardItemsArguments(field=args.field, value=args.value)))
        if not search_data["success"] or search_data["matches_found"] == 0:
            return json.dumps({"success": False, "message": "No items found", "deleted_count": 0}, indent=2)

        item_ids = [item["id"] for item in search_data["items"]]
        mutation = """mutation deleteItem($itemId: ID!) { delete_item (item_id: $itemId) { id } }"""
        deleted_items, errors = [], []
        
        for item_id in item_ids:
            success, result = await call_monday_api(mutation, {"itemId": item_id})
            if success and "data" in result and "delete_item" in result["data"]:
                deleted_items.append(next(item for item in search_data["items"] if item["id"] == item_id))
            else:
                errors.append(f"Error deleting item {item_id}: {result.get('error') or result.get('errors')}")
        
        return json.dumps({
            "success": len(deleted_items) > 0,
            "message": f"Deleted {len(deleted_items)} of {len(item_ids)} items",
            "deleted_count": len(deleted_items),
            "deleted_items": deleted_items,
            "errors": errors if errors else None
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "message": f"Error: {str(e)}", "deleted_count": 0}, indent=2)

@mcp.tool()
async def create_board_item(ctx: Context, args: CreateBoardItemArguments) -> str:
    request_id = id(ctx)
    logger.info(f"[{request_id}] Creating item: {args.item_name} with values: {json.dumps(args.column_values)}")
    
    try:
        column_values = {}
        for column_id, value in args.column_values.items():
            if not value: continue
            column_info = board_schema.columns_config.get(column_id)
            if not column_info: 
                logger.warning(f"[{request_id}] Column {column_id} not found in schema")
                continue
            
            column_type = column_info["type"]
            settings = column_info.get("settings", {})
            logger.debug(f"[{request_id}] Processing column {column_id} ({column_type}) with value: {value}")
            
            try:
                if column_type == "location":
                    try:
                        from geopy.geocoders import Nominatim
                        location = Nominatim(user_agent="monday_app").geocode(value)
                        column_values[column_id] = {"lat": str(getattr(location, "latitude", "")), 
                                                   "lng": str(getattr(location, "longitude", "")), 
                                                   "address": str(value)}
                        logger.debug(f"[{request_id}] Geocoded location: {json.dumps(column_values[column_id])}")
                    except Exception as e:
                        logger.error(f"[{request_id}] Error geocoding: {str(e)}")
                        column_values[column_id] = {"lat": "", "lng": "", "address": str(value)}
                elif column_type == "status":

                    label_index = None
                    for idx, lbl in settings.get("labels", {}).items():
                        if str(lbl).lower() == str(value).lower():
                            label_index = idx
                            break
                    column_values[column_id] = {"index": str(label_index) if label_index else ""}
                    logger.debug(f"[{request_id}] Status value mapped: {value} -> {column_values[column_id]}")
                elif column_type == "date":

                    column_values[column_id] = {"date": str(value)}
                    logger.debug(f"[{request_id}] Date formatted: {column_values[column_id]}")
                elif column_type == "email":
                    column_values[column_id] = {"email": str(value), "text": str(value)}
                    logger.debug(f"[{request_id}] Email formatted: {column_values[column_id]}")
                else:

                    column_values[column_id] = str(value)
                    logger.debug(f"[{request_id}] Simple value assigned: {column_id} = {value}")
            except Exception as col_err:
                logger.error(f"[{request_id}] Error formatting column {column_id}: {str(col_err)}")
                continue
        
        column_values_json = json.dumps(column_values)
        logger.debug(f"[{request_id}] Final column_values JSON: {column_values_json}")
        mutation = """mutation create_item($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
            create_item (board_id: $boardId, item_name: $itemName, column_values: $columnValues) {
                id name column_values { id text value type }
            }
        }"""
        
        success, result = await call_monday_api(mutation, {
            "boardId": MONDAY_BOARD_ID,
            "itemName": args.item_name,
            "columnValues": column_values_json  
        })
        
        logger.debug(f"[{request_id}] API response: {json.dumps(result)}")
        
        if success and "data" in result and "create_item" in result["data"] and result["data"]["create_item"]:
            logger.info(f"[{request_id}] Item created successfully with ID: {result['data']['create_item']['id']}")
            return json.dumps({
                "success": True, 
                "message": "Item created successfully",
                "item": result["data"]["create_item"]
            }, indent=2)
        else:
            error_msg = f"Create error: {result.get('errors', '')}"
            if "data" in result and result["data"].get("create_item") is None:
                error_msg = "Failed to create item. Possibly invalid column values or permissions."
            logger.error(f"[{request_id}] {error_msg}")
            return json.dumps({
                "success": False, 
                "message": error_msg,
                "raw_response": result
            }, indent=2)
    except Exception as e:
        error_msg = f"Error during creation: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, indent=2)