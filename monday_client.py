import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import logging
import json
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monday_client.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('monday_client')

async def display_tool_menu(tools):
    """Display available tools menu"""
    print("\nAvailable tools:")
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}: {tool.description or 'No description available'}")
    print("0. Exit")

async def display_board_schema(session):
    """Display the board schema to help with column selection"""
    try:
        response = await session.read_resource("monday://board/schema")
        if response and response.contents:
            schema = json.loads(response.contents[0].text)
            print("\nBoard Columns:")
            for i, column in enumerate(schema["columns"], 1):
                settings = {}
                if column.get("settings_str"):
                    try:
                        settings = json.loads(column["settings_str"])
                    except:
                        pass
                
                print(f"{i}. {column['title']} (Type: {column['type']})")
                if "labels" in settings:
                    values = list(settings["labels"].values())
                    print(f"   Valid values: {', '.join(values)}")
                print(f"   Column ID: {column['id']}")
                
    except Exception as e:
        logger.error(f"Error displaying schema: {str(e)}")
        print("Could not fetch board schema")

async def get_tool_parameters(tool_name, session):
    """Get parameters for a specific tool"""
    if tool_name in ["search_board_items", "delete_board_items"]:
        await display_board_schema(session)
        
        print("\nEnter field name and value separated by comma:")
        print("Example: name,Test")
        try:
            field, value = input("> ").strip().split(',', 1)
            return {
                "args": {
                    "field": field.strip(),
                    "value": value.strip()
                }
            }
        except ValueError:
            print("Error: Invalid format. Expected: field,value")
            return None
            
    elif tool_name == "create_board_item":
        await display_board_schema(session)
        
        print("\nEnter item name:")
        item_name = input("Name> ").strip()
        
        print("\nEnter values for columns as a comma-separated list:")
        print("The order should match the columns shown above")
        print("Leave empty for skipping a column")
        print("You need to provide 10 values (or less)")
        print("Example: 2025-02-18, test@example.com, Software, High, Madrid")
        
        try:
            values = input("> ").strip().split(',')
            values = [v.strip() for v in values]
            
            # Map values to column IDs
            schema = json.loads((await session.read_resource("monday://board/schema")).contents[0].text)
            columns = schema["columns"][1:]  # Skip 'name' column
            
            column_values = {"name": item_name}
            for col, val in zip(columns, values):
                if val:  # Only add non-empty values
                    column_values[col["id"]] = val
                    
            return {
                "args": {
                    "item_name": item_name,
                    "column_values": column_values
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing parameters: {str(e)}")
            print(f"Error: {str(e)}")
            return None
    
    return {}

async def format_response(response_text):
    """Format the response in a readable way"""
    try:
        data = json.loads(response_text)
        
        if "success" in data:
            print(f"\nSearch Results:")
            if data.get("matches_found", 0) > 0:
                print(f"Found {data['matches_found']} matches:")
                print("-" * 50)
                
                for item in data["items"]:
                    print(f"Item ID: {item['id']}")
                    print(f"Name: {item['name']}")
                    if item.get("column_values"):
                        print("Details:")
                        for col in item["column_values"]:
                            print(f"  • {col['title']}: {col['value']}")
                    print("-" * 50)
            else:
                print("No matches found")
                
            if data.get("errors"):
                print("\nErrors:")
                for error in data["errors"]:
                    print(f"- {error}")
                    
        elif "data" in data and "boards" in data["data"]:
            # Procesar datos del tablero
            board = data["data"]["boards"][0]
            
            print(f"\nBoard data:")
            items = board["items_page"]["items"]
            for item in items:
                print(f"\nItem ID: {item['id']}")
                print(f"Name: {item['name']}")
                print("Column values:")
                for col in item["column_values"]:
                    if col.get('text'):
                        # Use column title instead of ID
                        print(f"  • {col['title']}: {col['text']}")
                print("-" * 40)
            
        else:
            print("\nRaw Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
    except json.JSONDecodeError:
        print(f"\nNon-JSON Response:\n{response_text}")
    except Exception as e:
        logger.error(f"Error formatting response: {str(e)}", exc_info=True)
        print(f"Error formatting response: {str(e)}")
        print("\nRaw response:")
        print(response_text)

async def execute_tool(session, tool, params):
    """Execute a tool and display its results"""
    try:
        result = await session.call_tool(tool.name, params)
        if result and result.content:
            for content in result.content:
                if content.type == "text":
                    await format_response(content.text)
    except Exception as e:
        logger.error(f"Error executing tool: {str(e)}")
        print(f"Error executing tool: {str(e)}")

async def interactive_loop(session):
    """Main interactive loop"""
    logger.debug("Entering interactive loop")
    while True:
        try:
            logger.debug("Requesting tool list")
            response = await session.list_tools()
            tools = response.tools
            logger.debug(f"Available tools: {[tool.name for tool in tools]}")
            
            await display_tool_menu(tools)
            
            logger.debug("Waiting for user input")
            choice = input("\nSelect an option: ").strip()
            logger.debug(f"User selected: {choice}")

            if choice == "0":
                logger.info("User chose to exit")
                break
                
            try:
                tool_index = int(choice) - 1
                if 0 <= tool_index < len(tools):
                    selected_tool = tools[tool_index]
                    logger.debug(f"Selected tool: {selected_tool.name}")
                    
                    params = await get_tool_parameters(selected_tool.name, session)
                    logger.debug(f"Parameters obtained: {params}")
                    
                    if params is not None:
                        logger.debug(f"Executing tool {selected_tool.name}")
                        await execute_tool(session, selected_tool, params)
                else:
                    logger.warning(f"Invalid option selected: {choice}")
                    print("Invalid option")
            except ValueError:
                logger.warning(f"Non-numeric input: {choice}")
                print("Please enter a valid number")
                
        except Exception as e:
            logger.error(f"Error in interactive loop: {str(e)}", exc_info=True)
            print(f"Error: {str(e)}")

async def main():
    try:
        # Force UTF-8 encoding for the entire process
        if sys.platform == 'win32':
            import msvcrt
            import os
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stdin.reconfigure(encoding='utf-8', errors='replace')

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["monday_server.py", "--transport", "stdio"]
        )
        logger.debug(f"Server parameters: command={server_params.command}, args={server_params.args}")
        logger.info("Starting server connection...")

        async with stdio_client(server_params) as streams:
            read_stream, write_stream = streams
            logger.debug("Streams obtained from server")
            
            try:
                async with ClientSession(read_stream, write_stream) as session:
                    logger.info("MCP client connected to server.")
                    await session.initialize()
                    logger.info("Session initialized")
                    await interactive_loop(session)
            except Exception as e:
                logger.error(f"Error during session: {str(e)}", exc_info=True)
                
    except Exception as e:
        logger.error(f"General error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"Fatal error: {str(e)}")
        sys.exit(1)