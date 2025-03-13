import asyncio, json, sys, logging
from typing import Dict, Optional, List, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('monday_client.log', encoding='utf-8'), 
                              logging.StreamHandler()])
logger = logging.getLogger('monday_client')

async def setup_encoding():
    """Configure proper encoding for terminal I/O"""
    if sys.platform == 'win32':
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')

async def fetch_board_schema(session) -> Dict:
    """Retrieve the board schema from the server"""
    try:
        response = await session.read_resource("monday://board/schema")
        return json.loads(response.contents[0].text) if response and response.contents else {}
    except Exception as e:
        logger.error(f"Error fetching schema: {str(e)}")
        return {}

async def fetch_columns(session) -> List[Dict]:
    """Fetch column information"""
    schema = await fetch_board_schema(session)
    columns = schema.get("columns", [])
    
    print("\nBoard Columns:")
    for i, col in enumerate(columns, 1):
        # Show value options for status/dropdown columns
        values_info = ""
        if 'settings' in col and 'labels' in col['settings']:
            values = list(col['settings']['labels'].values())
            if values:
                values_info = f"Values: {', '.join(values)}"
                
        print(f"{i}. {col.get('title')} (Type: {col.get('type')}) ID: {col.get('id')} {values_info}")
    
    return columns

async def get_tool_params(tool_name: str, session: ClientSession) -> Optional[Dict]:
    """Get parameters for the selected tool"""
    
    # Get board columns if needed for parameter selection
    if tool_name in ["search_board_items", "delete_board_items", "create_board_item", "update_board_item"]:
        columns = await fetch_columns(session)

    # Tool-specific parameter collection
    if tool_name in ["search_board_items", "delete_board_items"]:
        print("\nEnter field name/ID and value (separated by comma):")
        user_input = input("> ").strip()
        if "," not in user_input:
            print("Error: Input must contain a comma separating field and value")
            return None
            
        field, value = user_input.split(',', 1)
        return {"args": {"field": field.strip(), "value": value.strip()}}
        
    elif tool_name == "create_board_item":
        # Get item name
        item_name = input("\nItem name> ").strip()
        if not item_name:
            print("Error: Item name is required")
            return None
        
        # Get column values
        print("\nEnter column values (format: column_id=value), one per line. Empty line to finish:")
        column_values = {}
        while True:
            line = input("> ").strip()
            if not line:
                break
                
            if "=" not in line:
                print("Invalid format. Use column_id=value")
                continue
                
            col_id, value = line.split("=", 1)
            column_values[col_id.strip()] = value.strip()
        
        # Optional group selection
        print("\nSpecify group ID (optional, press Enter to use default):")
        group_id = input("> ").strip() or None
        
        return {"args": {
            "item_name": item_name,
            "column_values": column_values,
            "group_id": group_id
        }}
    
    elif tool_name == "update_board_item":
        # Get item ID
        item_id = input("\nItem ID to update> ").strip()
        if not item_id:
            print("Error: Item ID is required")
            return None
        
        # Get column values to update
        column_values = {}
        print("\nEnter column values to update (format: column_id=value), one per line. Empty line to finish:")
        while True:
            line = input("> ").strip()
            if not line:
                break
                
            if "=" not in line:
                print("Invalid format. Use column_id=value")
                continue
                
            col_id, value = line.split("=", 1)
            column_values[col_id.strip()] = value.strip()
        
        if not column_values:
            print("Error: No column values provided for update")
            return None
            
        return {"args": {"item_id": item_id, "column_values": column_values}}
    
    # For get_board_data or other tools with no params
    return {"args": {}}

async def format_response(response_text: str):
    """Format the response in a human-readable way"""
    try:
        data = json.loads(response_text)
        
        if "board" in data:
            # Handle board data response
            print(f"\nBoard Information:")
            print(f"Name: {data['board']['name']}")
            print(f"ID: {data['board']['id']}")
            print(f"Items: {data['board']['items_count']}")
            print(f"Columns: {data['board']['columns_count']}")
            
            if data.get("items"):
                print(f"\nItems Preview ({len(data['items'])} total):")
                for idx, item in enumerate(data["items"][:5], 1):
                    print(f"{idx}. {item['name']} (ID: {item['id']})")
                
                if len(data["items"]) > 5:
                    print(f"... and {len(data['items']) - 5} more items")
                    
        elif "success" in data:
            # Handle operation result
            print(f"\nOperation {'succeeded' if data['success'] else 'failed'}")
            
            if "message" in data:
                print(f"Message: {data['message']}")
                
            if "matches_found" in data:
                print(f"Found {data['matches_found']} matches")
                
                for item in data.get("items", []):
                    print(f"\nID: {item['id']} | Name: {item['name']}")
                    for val in item.get("column_values", []):
                        print(f"  • {val['title']}: {val['value']}")
                        
            if "item" in data:
                item = data["item"]
                print(f"\nItem: {item.get('name', 'Unnamed')} (ID: {item.get('id', 'unknown')})")
                
            if "errors" in data and data["errors"]:
                print("\nErrors:", ", ".join(data["errors"]))
                
        else:
            # Generic response format
            print("\nResponse:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"\nError formatting response: {str(e)}")
        print(f"Raw response: {response_text[:200]}...")

async def main_cli_loop(session: ClientSession):
    """Main CLI interactive loop"""
    print("\nMonday.com MCP Client")
    print("====================")
    
    while True:
        try:
            # Get available tools
            tools_result = await session.list_tools()
            tools = tools_result.tools
            
            # Display menu
            print("\nAvailable tools:")
            for i, tool in enumerate(tools, 1): 
                print(f"{i}. {tool.name} - {tool.description}")
            print("0. Exit")
            
            # Get user selection
            choice = input("\nSelect option: ").strip()
            if choice == "0": 
                print("Exiting...")
                break
                
            try:
                tool_index = int(choice) - 1
                if 0 <= tool_index < len(tools):
                    tool = tools[tool_index]
                    print(f"\nSelected: {tool.name}")
                    
                    # Get tool parameters
                    params = await get_tool_params(tool.name, session)
                    if params is not None:
                        print("\nCalling tool, please wait...")
                        # Call the tool
                        result = await session.call_tool(tool.name, params)
                        
                        # Format and display result
                        if result and result.content:
                            for content in result.content:
                                if content.type == "text": 
                                    await format_response(content.text)
                else:
                    print("Invalid option")
            except ValueError:
                print("Please enter a valid number")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"Error: {str(e)}")
            
async def main():
    """Main entry point"""
    try:
        print("Starting Monday.com MCP Client...")
        await setup_encoding()
        
        # Set up server
        server_params = StdioServerParameters(
            command=sys.executable, 
            args=["monday_server.py", "--transport", "stdio"]
        )
        
        # Connect to server
        print("Connecting to server...")
        async with stdio_client(server_params) as streams:
            async with ClientSession(*streams) as session:
                logger.info("Connected to MCP server")
                print("Connected successfully!")
                await session.initialize()
                await main_cli_loop(session)
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Unhandled error: {str(e)}")
        sys.exit(1)