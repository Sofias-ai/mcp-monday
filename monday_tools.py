from typing import Dict, Any
import json
import logging
import httpx
from datetime import datetime  # Añadida la importación
from mcp.server.fastmcp import Context
from pydantic import BaseModel

from monday_config import (
    mcp, board_schema, MONDAY_API_KEY, 
    MONDAY_API_URL, MONDAY_BOARD_ID, logger
)

@mcp.tool()
async def get_board_data(ctx: Context) -> str:
    """Get all data from Monday.com board"""
    logger.debug("Entering get_board_data")
    request_id = id(ctx)
    logger.info(f"[{request_id}] Starting get_board_data")
    
    if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
        error_msg = "Missing API_KEY or BOARD_ID in environment variables"
        logger.error(f"[{request_id}] {error_msg}")
        return error_msg

    query = """
        query {
            boards(ids: %s) {
                name
                columns {
                    id
                    title
                    type
                }
                items_page(limit: 100) {
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            type
                            value
                        }
                    }
                }
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
            
            logger.debug(f"[{request_id}] Response received. Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "boards" in data["data"]:
                    board = data["data"]["boards"][0]
                    
                    # Crear un diccionario de columnas para búsqueda rápida
                    columns_dict = {
                        col["id"]: col["title"] 
                        for col in board["columns"]
                    }
                    
                    # Formatear los items con los títulos de las columnas
                    for item in board["items_page"]["items"]:
                        for col_value in item["column_values"]:
                            col_value["title"] = columns_dict.get(col_value["id"], col_value["id"])
                    
                return json.dumps(data)
            else:
                error_msg = f"Error in response: {response.status_code} - {response.text}"
                logger.error(f"[{request_id}] {error_msg}")
                return error_msg
    except Exception as e:
        error_msg = f"Error in request: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        return error_msg

class SearchBoardItemsArguments(BaseModel):
    field: str
    value: str

class CreateBoardItemArguments(BaseModel):
    item_name: str
    column_values: Dict[str, Any]

class DeleteBoardItemsArguments(BaseModel):
    field: str
    value: str

@mcp.tool()
async def search_board_items(ctx: Context, args: SearchBoardItemsArguments) -> str:
    """Search for items in the board by field and value"""
    request_id = id(ctx)
    logger.info(f"[{request_id}] Starting search_board_items")
    logger.debug(f"[{request_id}] Search parameters - field: '{args.field}', value: '{args.value}'")

    try:
        # Primero obtenemos el schema para validar el campo
        logger.debug(f"[{request_id}] Fetching board schema to validate field")
        schema = await get_board_data(ctx)
        schema_data = json.loads(schema)
        
        if "data" not in schema_data or "boards" not in schema_data["data"]:
            logger.error(f"[{request_id}] Invalid schema format")
            return json.dumps({"success": False, "message": "Could not validate field, invalid schema"})

        board = schema_data["data"]["boards"][0]
        columns = board.get("columns", [])
        
        # Mapear IDs a títulos para búsqueda flexible
        column_map = {}
        reverse_map = {}  # Nuevo mapa inverso
        for col in columns:
            logger.debug(f"[{request_id}] Column mapping - ID: {col['id']}, Title: {col['title']}, Type: {col['type']}")
            column_map[col['id']] = col['title']
            reverse_map[col['title'].lower()] = col['id']  # Almacenar ID original

        # Determinar el ID de columna real
        search_field = args.field
        if args.field.lower() in reverse_map:
            search_field = reverse_map[args.field.lower()]
            logger.info(f"[{request_id}] Mapped field '{args.field}' to column ID '{search_field}'")
        
        # Construir la query de búsqueda
        logger.debug(f"[{request_id}] Building search query for column_id: {search_field}")
        query = """
            query {
                boards(ids: %s) {
                    items_page(query_params: {
                        rules: [{
                            column_id: "%s",
                            compare_value: "%s",
                            operator: contains_terms
                        }]
                    }) {
                        items {
                            id
                            name
                            column_values {
                                id
                                text
                                type
                                value
                            }
                        }
                    }
                }
            }
        """ % (MONDAY_BOARD_ID, search_field, args.value)
        
        logger.debug(f"[{request_id}] Executing query: {query}")

        # Ejecutar la búsqueda
        async with httpx.AsyncClient() as client:
            logger.debug(f"[{request_id}] Sending request to Monday.com API")
            response = await client.post(
                MONDAY_API_URL,
                json={"query": query},
                headers={
                    "Authorization": MONDAY_API_KEY,
                    "Content-Type": "application/json",
                }
            )
            
            logger.debug(f"[{request_id}] Response status: {response.status_code}")
            logger.debug(f"[{request_id}] Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"[{request_id}] Raw API response: {json.dumps(result, indent=2)}")
                
                if "data" in result and "boards" in result["data"]:
                    board_result = result["data"]["boards"][0]
                    items = board_result.get("items_page", {}).get("items", [])
                    
                    logger.info(f"[{request_id}] Found {len(items)} items")
                    
                    # Formatear resultados
                    formatted_items = []
                    for item in items:
                        logger.debug(f"[{request_id}] Processing item ID: {item['id']}")
                        formatted_item = {
                            "id": item["id"],
                            "name": item["name"],
                            "column_values": []
                        }
                        
                        for col_value in item["column_values"]:
                            if col_value.get("text"):
                                col_title = column_map.get(col_value["id"], col_value["id"])
                                formatted_item["column_values"].append({
                                    "title": col_title,
                                    "value": col_value["text"]
                                })
                                logger.debug(f"[{request_id}] Column value - Title: {col_title}, Value: {col_value['text']}")
                        
                        formatted_items.append(formatted_item)
                    
                    response_data = {
                        "success": True,
                        "matches_found": len(formatted_items),
                        "items": formatted_items
                    }
                    
                    logger.info(f"[{request_id}] Search completed successfully")
                    logger.debug(f"[{request_id}] Final response: {json.dumps(response_data, indent=2)}")
                    
                    return json.dumps(response_data, indent=2)
                else:
                    logger.error(f"[{request_id}] Invalid API response format")
                    return json.dumps({
                        "success": False,
                        "message": "Invalid API response format"
                    }, indent=2)
            else:
                error_msg = f"API error: {response.status_code} - {response.text}"
                logger.error(f"[{request_id}] {error_msg}")
                return json.dumps({
                    "success": False,
                    "message": error_msg
                }, indent=2)

    except Exception as e:
        error_msg = f"Error during search: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": error_msg
        }, indent=2)

@mcp.tool()
async def delete_board_items(ctx: Context, args: DeleteBoardItemsArguments) -> str:
    """Delete items from the board that match a specific field and value"""
    request_id = id(ctx)
    logger.debug(f"[{request_id}] Entering delete_board_items with field='{args.field}', value='{args.value}'")
    
    try:
        # First search for matching items
        search_result = await search_board_items(ctx, SearchBoardItemsArguments(field=args.field, value=args.value))
        search_data = json.loads(search_result)
        
        if not search_data["success"] or search_data["matches_found"] == 0:
            return json.dumps({
                "success": False,
                "message": "No items found to delete",
                "deleted_count": 0
            }, indent=2)

        # Extract IDs to delete
        item_ids = [str(item["id"]) for item in search_data["items"]]
        
        mutation = """
            mutation deleteItem($itemId: ID!) {
                delete_item (item_id: $itemId) {
                    id
                }
            }
        """
        
        headers = {
            "Authorization": MONDAY_API_KEY,
            "Content-Type": "application/json",
        }

        deleted_items = []
        deletion_errors = []

        async with httpx.AsyncClient() as client:
            for item_id in item_ids:
                try:
                    response = await client.post(
                        MONDAY_API_URL,
                        json={
                            "query": mutation,
                            "variables": {"itemId": item_id}
                        },
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if "data" in result and "delete_item" in result["data"]:
                            deleted_items.append(
                                next(item for item in search_data["items"] if item["id"] == item_id)
                            )
                        else:
                            error_msg = f"Error deleting item {item_id}: {result.get('errors', ['Unknown error'])}"
                            logger.error(error_msg)
                            deletion_errors.append(error_msg)
                    else:
                        error_msg = f"Error in response for item {item_id}: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        deletion_errors.append(error_msg)

                except Exception as e:
                    error_msg = f"Error processing item {item_id}: {str(e)}"
                    logger.error(error_msg)
                    deletion_errors.append(error_msg)

        return json.dumps({
            "success": len(deleted_items) > 0,
            "message": f"Deleted {len(deleted_items)} of {len(item_ids)} items",
            "deleted_count": len(deleted_items),
            "deleted_items": deleted_items,
            "errors": deletion_errors if deletion_errors else None
        }, indent=2)

    except Exception as e:
        error_msg = f"Error during deletion: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": error_msg,
            "deleted_count": 0
        }, indent=2)

@mcp.tool()
async def create_board_item(ctx: Context, args: CreateBoardItemArguments) -> str:
    """Create a new board item with dynamic column values"""
    request_id = id(ctx)
    logger.info(f"[{request_id}] Starting create_board_item")
    logger.debug(f"[{request_id}] Input arguments: {json.dumps(args.dict(), indent=2)}")

    try:
        column_values = {}
        logger.debug(f"[{request_id}] Processing column values:")
        
        for column_id, value in args.column_values.items():
            try:
                if not value:  # Skip empty values
                    continue
                    
                column_info = board_schema.columns_config.get(column_id)
                if not column_info:
                    logger.warning(f"[{request_id}] Column {column_id} not found in schema")
                    continue

                column_type = column_info["type"]
                settings = column_info.get("settings", {})
                
                # Formatear el valor según el tipo
                if column_type == "location":
                    try:
                        from geopy.geocoders import Nominatim
                        geolocator = Nominatim(user_agent="monday_app")
                        try:
                            location = geolocator.geocode(value)
                            if location:
                                column_values[column_id] = {
                                    "lat": str(location.latitude),
                                    "lng": str(location.longitude),
                                    "address": str(value)
                                }
                            else:
                                column_values[column_id] = {
                                    "lat": "",
                                    "lng": "",
                                    "address": str(value)
                                }
                        except Exception:
                            column_values[column_id] = {
                                "lat": "",
                                "lng": "",
                                "address": str(value)
                            }
                    except ImportError:
                        column_values[column_id] = {
                            "lat": "",
                            "lng": "",
                            "address": str(value)
                        }
                elif column_type == "status":
                    # Código completo para status
                    logger.debug(f"[{request_id}] Processing status value: {value}")
                    logger.debug(f"[{request_id}] Available labels: {json.dumps(settings.get('labels', {}), indent=2)}")
                    
                    # Buscar el índice exacto
                    label_index = None
                    for index, label in settings.get("labels", {}).items():
                        logger.debug(f"[{request_id}] Comparing '{str(value).lower()}' with '{str(label).lower()}'")
                        if str(value).lower() == str(label).lower():
                            label_index = index
                            logger.info(f"[{request_id}] Found matching label index: {index}")
                            break
                            
                    if label_index:
                        column_values[column_id] = {"index": str(label_index)}
                    else:
                        logger.warning(f"[{request_id}] No matching label found for value: {value}")
                        column_values[column_id] = {"index": ""}  # Valor vacío si no hay match
                elif column_type == "date":
                    column_values[column_id] = {"date": str(value)}
                elif column_type == "email":
                    column_values[column_id] = {
                        "email": str(value),
                        "text": str(value)
                    }
                elif column_type in ["text", "long_text", "name"]:
                    # Corregido el formato para campos de texto
                    column_values[column_id] = str(value)  # Enviar el valor directo sin wrapper

                logger.debug(f"[{request_id}] Formatted value for {column_id} ({column_type}): {json.dumps(column_values[column_id])}")

            except Exception as column_error:
                logger.error(f"[{request_id}] Error formatting column {column_id}: {str(column_error)}", exc_info=True)
                return json.dumps({
                    "success": False,
                    "message": f"Error formatting column {column_id}: {str(column_error)}"
                }, indent=2)

        # Convertir todo el diccionario a un solo string JSON
        column_values_json = json.dumps(column_values)
        logger.debug(f"[{request_id}] Final column values JSON: {column_values_json}")

        mutation = """
            mutation create_item($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
                create_item (
                    board_id: $boardId,
                    item_name: $itemName,
                    column_values: $columnValues
                ) {
                    id
                    name
                    column_values {
                        id
                        text
                        value
                        type
                    }
                }
            }
        """

        variables = {
            "boardId": MONDAY_BOARD_ID,
            "itemName": args.item_name,
            "columnValues": column_values_json  # Enviamos el string JSON
        }

        headers = {
            "Authorization": MONDAY_API_KEY,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            logger.info(f"[{request_id}] Sending create item request to Monday.com API")
            response = await client.post(
                MONDAY_API_URL,
                json={
                    "query": mutation,
                    "variables": variables
                },
                headers=headers
            )
            
            logger.debug(f"[{request_id}] API Response status: {response.status_code}")
            logger.debug(f"[{request_id}] API Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"[{request_id}] API Response body: {json.dumps(result, indent=2)}")
                
                if "data" in result and "create_item" in result["data"]:
                    created_item = result["data"]["create_item"]
                    logger.info(f"[{request_id}] Item created successfully with ID: {created_item['id']}")
                    return json.dumps({
                        "success": True,
                        "message": "Item created successfully",
                        "item": created_item
                    }, indent=2)
                else:
                    error_msg = f"Error creating item: {result.get('errors', ['Unknown error'])}"
                    logger.error(f"[{request_id}] {error_msg}")
                    logger.debug(f"[{request_id}] Full error response: {json.dumps(result, indent=2)}")
                    return json.dumps({
                        "success": False,
                        "message": error_msg,
                        "raw_response": result
                    }, indent=2)
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                logger.error(f"[{request_id}] API request failed: {error_msg}")
                return json.dumps({
                    "success": False,
                    "message": error_msg
                }, indent=2)

    except Exception as e:
        error_msg = f"Error during item creation: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": error_msg
        }, indent=2)