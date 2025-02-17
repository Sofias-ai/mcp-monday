from mcp.server.fastmcp import FastMCP, Context
import httpx
import os
from dotenv import load_dotenv
import logging
import sys
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monday_server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('monday_server')

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Monday.com Configuration
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")

logger.info(f"Monday.com Configuration: URL={MONDAY_API_URL}, Board ID={MONDAY_BOARD_ID}")
logger.debug(f"API Key found: {bool(MONDAY_API_KEY)}")

if __name__ == "__main__":
    logger.debug("Starting server main program")
    import sys
    import locale
    
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
        # Configure server encoding
        server_config = {
            'encoding': 'utf-8',
            'errors': 'replace'
        }
        
        logger.debug("Configuring MCP server")
        mcp = FastMCP("monday-server", **server_config)
        logger.info("MCP Server created")

        # Register tools before starting the server
        @mcp.tool()
        async def get_board_data(ctx: Context) -> str:
            """Get all data from Monday.com board"""
            logger.debug("Entering get_board_data")
            request_id = id(ctx)  # Unique identifier for this request
            logger.info(f"[{request_id}] Starting get_board_data")
            
            if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
                error_msg = "Missing API_KEY or BOARD_ID in environment variables"
                logger.error(f"[{request_id}] {error_msg}")
                return error_msg

            logger.debug(f"[{request_id}] Preparing headers and query")
            headers = {
                "Authorization": MONDAY_API_KEY,
                "Content-Type": "application/json",
            }
            
            query = """
                query {
                    boards(ids: %s) {
                        name
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

            logger.debug(f"[{request_id}] Query to execute: {query}")

            try:
                async with httpx.AsyncClient() as client:
                    logger.debug(f"[{request_id}] HTTP client created")
                    logger.info(f"[{request_id}] Making request to Monday.com")
                    response = await client.post(
                        MONDAY_API_URL,
                        json={"query": query},
                        headers=headers
                    )
                    
                    logger.debug(f"[{request_id}] Response received. Status: {response.status_code}, Length: {len(response.text)}")
                    logger.debug(f"[{request_id}] Response headers: {dict(response.headers)}")

                    if response.status_code == 200:
                        try:
                            # Verify that the response is valid JSON
                            json.loads(response.text)
                            logger.debug(f"[{request_id}] Valid JSON response")
                            return response.text
                        except json.JSONDecodeError as e:
                            error_msg = f"Response is not valid JSON: {str(e)}"
                            logger.error(f"[{request_id}] {error_msg}")
                            return error_msg
                    else:
                        error_msg = f"Error in response: {response.status_code} - {response.text}"
                        logger.error(f"[{request_id}] {error_msg}")
                        return error_msg
            except Exception as e:
                error_msg = f"Error in request: {str(e)}"
                logger.error(f"[{request_id}] {error_msg}", exc_info=True)
                return error_msg

        @mcp.tool()
        async def search_board_items(ctx: Context, field: str, value: str) -> str:
            """
            Search for items in the board by field and value
            
            Args:
                field: Field name to search
                value: Value to search in the field
            """
            logger.debug(f"Entering search_board_items with field='{field}', value='{value}'")
            logger.info(f"Starting search_board_items with field={field}, value={value}")
            
            if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
                error_msg = "Missing API_KEY or BOARD_ID in environment variables"
                logger.error(error_msg)
                return error_msg

            # Get board data
            board_data = await get_board_data(ctx)
            
            try:
                data = json.loads(board_data)
                if "data" not in data or "boards" not in data["data"]:
                    return "No data found in the board"

                board = data["data"]["boards"][0]
                items = board["items_page"]["items"]
                
                # List to store found results
                matching_items = []
                
                for item in items:
                    # Search in columns and name
                    matches_field = False
                    if field.lower() == "name" and value.lower() in item["name"].lower():
                        matches_field = True
                    else:
                        for column in item["column_values"]:
                            if column["text"] and (
                                (column["id"].lower() == field.lower() or 
                                 field.lower() in column["id"].lower()) and 
                                value.lower() in column["text"].lower()
                            ):
                                matches_field = True
                                break
                    
                    if matches_field:
                        # Include all item data
                        item_data = {
                            "id": item["id"],
                            "name": item["name"],
                            "matching_field": field,
                            "matching_value": value,
                            "fields": []
                        }
                        for column in item["column_values"]:
                            if column["text"]:
                                item_data["fields"].append({
                                    "id": column["id"],
                                    "text": column["text"],
                                    "type": column["type"]
                                })
                        matching_items.append(item_data)

                if not matching_items:
                    return f"No items found with field '{field}' containing '{value}'"
                
                # Format results
                results = {
                    "matches_found": len(matching_items),
                    "items": matching_items
                }
                
                return json.dumps(results, indent=2, ensure_ascii=False)
                
            except json.JSONDecodeError as e:
                error_msg = f"Error processing board data: {str(e)}"
                logger.error(error_msg)
                return error_msg
            except Exception as e:
                error_msg = f"Error during search: {str(e)}"
                logger.error(error_msg)
                return error_msg

        @mcp.tool()
        async def delete_board_items(ctx: Context, field: str, value: str) -> str:
            """
            Delete items from the board that match a specific field and value
            
            Args:
                field: Field name to match
                value: Value to match
            """
            logger.debug(f"Entering delete_board_items with field='{field}', value='{value}'")
            logger.info(f"Starting delete_board_items with field={field}, value={value}")
            
            try:
                # First search for matching items
                search_result = await search_board_items(ctx, field, value)
                search_data = json.loads(search_result)
                
                if "matches_found" not in search_data or search_data["matches_found"] == 0:
                    return json.dumps({
                        "success": False,
                        "message": "No items found to delete",
                        "deleted_count": 0
                    }, indent=2, ensure_ascii=False)

                # Extract IDs to delete
                item_ids = [str(item["id"]) for item in search_data["items"]]
                
                # Mutation to delete a single item
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
                    "API-Version": "2024-10"
                }

                deleted_items = []
                deletion_errors = []

                # Process each item individually
                async with httpx.AsyncClient() as client:
                    for item_id in item_ids:
                        logger.info(f"Attempting to delete item: {item_id}")
                        
                        variables = {
                            "itemId": item_id
                        }

                        payload = {
                            "query": mutation,
                            "variables": variables
                        }

                        try:
                            response = await client.post(
                                MONDAY_API_URL,
                                json=payload,
                                headers=headers
                            )
                            
                            logger.debug(f"Response for item {item_id}: Status {response.status_code}")
                            
                            if response.status_code == 200:
                                result = response.json()
                                if "data" in result and "delete_item" in result["data"]:
                                    deleted_items.append(next(item for item in search_data["items"] if item["id"] == item_id))
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

                # Prepare final response
                success = len(deleted_items) > 0
                total_items = len(item_ids)
                deleted_count = len(deleted_items)

                response_data = {
                    "success": success,
                    "message": f"Deleted {deleted_count} of {total_items} items",
                    "deleted_count": deleted_count,
                    "deleted_items": deleted_items
                }

                if deletion_errors:
                    response_data["errors"] = deletion_errors

                return json.dumps(response_data, indent=2, ensure_ascii=False)

            except json.JSONDecodeError as e:
                error_msg = f"Error processing JSON: {str(e)}"
                logger.error(error_msg)
                return json.dumps({
                    "success": False,
                    "message": error_msg,
                    "deleted_count": 0
                }, indent=2, ensure_ascii=False)
            except Exception as e:
                error_msg = f"Error during deletion: {str(e)}"
                logger.error(error_msg)
                return json.dumps({
                    "success": False,
                    "message": error_msg,
                    "deleted_count": 0
                }, indent=2, ensure_ascii=False)

        @mcp.tool()
        async def create_board_item(ctx: Context, values: str) -> str:
            """
            Create a new board item using comma-separated values
            
            Args:
                values: Comma-separated values for each field, in order
            """
            logger.debug(f"Entering create_board_item with values='{values}'")
            logger.info(f"Starting create_board_item with values={values}")

            try:
                # Separate values by comma and trim spaces
                field_values = [v.strip() for v in values.split(',')]
                
                # The first value will be the item name
                item_name = field_values[0]
                
                # Create column values with the correct format for each type
                column_values = {}
                
                # Mapping of fields and their specific formats
                column_mapping = [
                    ("fecha_mkn31a0n", lambda x: {"date": x, "time": "00:00:00"}),  # date
                    ("correo_electr_nico_mkn3pkxr", lambda x: {"email": x, "text": x}),  # email
                    ("label_mkn3392m", lambda x: {"label": x}),  # type (label)
                    ("priority_mkn3w5r9", lambda x: {"label": x}),  # priority (label)
                    ("ubicaci_n_mkn391kx", lambda x: {"lat": "40.4165", "lng": "-3.7026", "address": x}),  # location
                    ("texto_largo_mkn34te3", lambda x: x),  # description
                    ("texto_mkn36epx", lambda x: x),  # short text
                    ("label_mkn3ma8r", lambda x: {"label": x}),  # area (label)
                    ("label_mkn3djw1", lambda x: {"label": x})  # category (label)
                ]

                # Create column values
                for i, (col_id, formatter) in enumerate(column_mapping, 1):
                    if i < len(field_values):
                        column_values[col_id] = formatter(field_values[i])

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
                            }
                        }
                    }
                """

                variables = {
                    "boardId": MONDAY_BOARD_ID,
                    "itemName": item_name,
                    "columnValues": json.dumps(column_values)  
                }

                logger.debug(f"Mutation: {mutation}")
                logger.debug(f"Variables: {json.dumps(variables, indent=2)}")

                headers = {
                    "Authorization": MONDAY_API_KEY,
                    "Content-Type": "application/json"
                }

                async with httpx.AsyncClient() as client:
                    logger.info(f"Executing mutation to create item: {item_name}")
                    response = await client.post(
                        MONDAY_API_URL,
                        json={
                            "query": mutation,
                            "variables": variables
                        },
                        headers=headers
                    )
                    
                    logger.debug(f"Full response: {response.text}")

                    if response.status_code == 200:
                        result = response.json()
                        logger.debug(f"JSON response: {json.dumps(result, indent=2)}")
                        
                        if "data" in result and "create_item" in result["data"]:
                            if result["data"]["create_item"] is None and "errors" in result:
                                error_msg = f"Error creating item: {result['errors']}"
                                logger.error(error_msg)
                                return json.dumps({
                                    "success": False,
                                    "message": error_msg,
                                    "errors": result["errors"]
                                }, indent=2, ensure_ascii=False)
                            
                            created_item = result["data"]["create_item"]
                            return json.dumps({
                                "success": True,
                                "message": "Item created successfully",
                                "item": created_item
                            }, indent=2, ensure_ascii=False)
                        else:
                            error_msg = f"Unexpected response: {result}"
                            logger.error(error_msg)
                            return json.dumps({
                                "success": False,
                                "message": error_msg
                            }, indent=2, ensure_ascii=False)
                    else:
                        error_msg = f"Error: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        return json.dumps({
                            "success": False,
                            "message": error_msg
                        }, indent=2, ensure_ascii=False)

            except Exception as e:
                error_msg = f"Error during creation: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return json.dumps({
                    "success": False,
                    "message": error_msg
                }, indent=2, ensure_ascii=False)
        
        # Register tools explicitly
        tools = [get_board_data, search_board_items, delete_board_items]
        for tool in tools:
            if not hasattr(tool, '_mcp_tool'):
                mcp.tool()(tool)
                logger.debug(f"Tool registered: {tool.__name__}")
        
        logger.debug("Starting server...")
        mcp.run(transport=transport_type)
    except Exception as e:
        logger.critical(f"Fatal server error: {str(e)}", exc_info=True)
        sys.exit(1)