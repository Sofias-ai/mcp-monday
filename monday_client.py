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

async def format_board_data(data):
    """Format board data in a readable way"""
    try:
        board_data = data["data"]["boards"][0]
        board_name = board_data["name"]
        items = board_data["items_page"]["items"]
        
        output = [f"\nBoard: {board_name}"]
        output.append("-" * 80)
        
        for item in items:
            output.append(f"\nRecord ID: {item['id']}")
            output.append(f"Name: {item['name']}")
            output.append("Fields:")
            for column in item["column_values"]:
                if column["text"]:
                    output.append(f"  - {column['id']}: {column['text']}")
            output.append("-" * 40)
            
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error formatting data: {str(e)}")
        return str(data)

async def get_tool_parameters(tool_name):
    """Get parameters for a specific tool"""
    if tool_name in ["search_board_items", "delete_board_items"]:
        print("\nEnter parameters separated by comma:")
        print("Format: field_name,search_value")
        params = input("> ").strip().split(',')
        if len(params) != 2:
            print("Error: Exactly 2 parameters required (field_name,search_value)")
            return None
        return {
            "field": params[0].strip(),
            "value": params[1].strip()
        }
    elif tool_name == "create_board_item":
        print("\nEnter values for the new record separated by comma:")
        print("Format: name,date,email,type,priority,location,description,text,area,category")
        print("Example: Test 03,2025-02-17,email@domain.com,Software,High,Madrid,Long description,Short text,Finance,Request")
        values = input("> ").strip()
        if not values:
            print("Error: No values provided")
            return None
        return {
            "values": values
        }
    return {}

async def execute_tool(session, tool, params):
    """Execute a tool and display its results"""
    try:
        result = await session.call_tool(tool.name, params)
        if result and result.content:
            for content in result.content:
                if content.type == "text":
                    try:
                        json_data = json.loads(content.text)
                        
                        # Case 1: delete_board_items response
                        if "success" in json_data:
                            if json_data["success"]:
                                print(f"\nSuccess: {json_data['message']}")
                                if "deleted_items" in json_data:
                                    print("\nDeleted items:")
                                    for item in json_data["deleted_items"]:
                                        print(f"- ID: {item['id']}, Name: {item['name']}")
                            else:
                                print(f"\nError: {json_data['message']}")
                                if "error" in json_data:
                                    print(f"Details: {json_data['error']}")
                            return

                        # Case 2: search_board_items response
                        if "matches_found" in json_data:
                            print(f"\nMatches found: {json_data['matches_found']}")
                            if json_data['matches_found'] > 0:
                                print("\nMatching items:")
                                for item in json_data["items"]:
                                    print(f"\nRecord ID: {item['id']}")
                                    print(f"Name: {item['name']}")
                                    print(f"Matching field: {item['matching_field']}")
                                    print(f"Matching value: {item['matching_value']}")
                                    print("\nFields:")
                                    for field in item["fields"]:
                                        print(f"  - {field['id']}: {field['text']}")
                                    print("-" * 40)
                            return

                        # Case 3: get_board_data response (keep existing format)
                        if "data" in json_data and "boards" in json_data["data"]:
                            print(await format_board_data(json_data))
                            return

                        # Default case: display formatted JSON
                        print("\nServer response:")
                        print(json.dumps(json_data, indent=2, ensure_ascii=False))

                    except json.JSONDecodeError:
                        print(f"\nServer response (not JSON):\n{content.text}")
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
                    
                    params = await get_tool_parameters(selected_tool.name)
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
                # Removed encoding parameter from ClientSession
                async with ClientSession(read_stream, write_stream) as session:
                    logger.info("MCP client connected to server.")
                    await session.initialize()
                    logger.info("Session initialized")
                    await interactive_loop(session)
            except Exception as e:
                logger.error(f"Error during session: {str(e)}", exc_info=True)
                
    except Exception as e:
        logger.error(f"General error: {str(e)}", exc_info=True)
        raise  # Re-raise exception to ensure proper cleanup

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"Fatal error: {str(e)}")
        sys.exit(1)