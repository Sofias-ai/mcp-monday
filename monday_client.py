import asyncio, json, sys, logging
from typing import Dict, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.FileHandler('monday_client.log', encoding='utf-8'), logging.StreamHandler()])
logger = logging.getLogger('monday_client')

TOOL_CONFIGS = {
    "search_board_items": {"needs_field_value": True},
    "delete_board_items": {"needs_field_value": True},
    "create_board_item": {"needs_item_creation": True},
    "get_board_data": {}
}

async def setup_windows_encoding():
    """Configurar codificación UTF-8 en Windows"""
    if sys.platform == 'win32':
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')

async def fetch_board_schema(session) -> Dict:
    """Obtener el esquema del tablero"""
    try:
        response = await session.read_resource("monday://board/schema")
        return json.loads(response.contents[0].text) if response and response.contents else {}
    except Exception as e:
        logger.error(f"Error fetching schema: {str(e)}")
        return {}

async def get_params(tool_name: str, session: ClientSession) -> Optional[Dict]:
    """Obtener parámetros para una herramienta específica"""
    config = TOOL_CONFIGS.get(tool_name, {})
    
    if config.get("needs_field_value") or config.get("needs_item_creation"):
        schema = await fetch_board_schema(session)
        print("\nBoard Columns:")
        for i, col in enumerate(schema.get("columns", []), 1):
            settings_str = f"Values: {', '.join(list(col.get('settings', {}).get('labels', {}).values()))}" if 'labels' in col.get('settings', {}) else ""
            print(f"{i}. {col.get('title')} (Type: {col.get('type')}) ID: {col.get('id')} {settings_str}")
    
    if config.get("needs_field_value"):
        print("\nEnter field name and value (field,value):")
        try:
            field, value = input("> ").strip().split(',', 1)
            return {"args": {"field": field.strip(), "value": value.strip()}}
        except ValueError:
            print("Error: Invalid format. Expected: field,value")
            return None
    
    elif config.get("needs_item_creation"):
        schema = await fetch_board_schema(session)
        item_name = input("\nItem name> ").strip()
        print("\nEnter comma-separated column values (in displayed order, leave blank to skip):")
        
        try:
            values = [v.strip() for v in input("> ").strip().split(',')]
            column_values = {"name": item_name}
            for col, val in zip(schema.get("columns", [])[1:], values):
                if val: column_values[col["id"]] = val
            return {"args": {"item_name": item_name, "column_values": column_values}}
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
    
    return {}

async def format_output(response_text: str):
    """Formatear respuesta para mostrar en consola"""
    try:
        data = json.loads(response_text)
        
        if "success" in data:
            print(f"\n{'Search' if 'matches_found' in data else 'Action'} Results:")
            if data.get("matches_found", 0) > 0:
                print(f"Found {data['matches_found']} matches:")
                print("-" * 40)
                for item in data.get("items", []):
                    print(f"ID: {item['id']} | Name: {item['name']}")
                    if item.get("column_values"):
                        print("Details:")
                        for col in item["column_values"]: 
                            print(f"  • {col['title']}: {col['value']}")
                    print("-" * 40)
            else:
                print(f"{'No matches found' if 'matches_found' in data else data.get('message', 'Action completed')}")
            
            if data.get("errors"): 
                print("\nErrors:", ", ".join(data["errors"]))
                
        elif "data" in data and "boards" in data["data"]:
            items = data["data"]["boards"][0].get("items_page", {}).get("items", [])
            print(f"\nBoard data: {len(items)} items")
            for item in items:
                print(f"\nID: {item['id']} | Name: {item['name']}")
                for col in item.get("column_values", []):
                    if col.get('text'): print(f"  • {col['title']}: {col['text']}")
                print("-" * 40)
        else:
            print("\nRaw Response:", json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")
    except Exception as e:
        print(f"\nError formatting response: {str(e)}\nRaw data:\n{response_text[:500]}...")

async def execute_cli(session: ClientSession):
    """Bucle principal de interfaz de línea de comandos"""
    while True:
        try:

            tools = (await session.list_tools()).tools
            print("\nAvailable tools:")
            for i, tool in enumerate(tools, 1): 
                print(f"{i}. {tool.name}")
            print("0. Exit")
            
            choice = input("\nSelect option: ").strip()
            if choice == "0": break
                
            try:
                tool_index = int(choice) - 1
                if 0 <= tool_index < len(tools):
                    tool = tools[tool_index]
                    params = await get_params(tool.name, session)
                    
                    if params is not None:

                        result = await session.call_tool(tool.name, params)
                        if result and result.content:
                            for content in result.content:
                                if content.type == "text": 
                                    await format_output(content.text)
                else:
                    print("Invalid option")
            except ValueError:
                print("Please enter a valid number")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"Error: {str(e)}")

async def main():
    try:
        await setup_windows_encoding()
        server_params = StdioServerParameters(
            command=sys.executable, 
            args=["monday_server.py", "--transport", "stdio"]
        )
        
        async with stdio_client(server_params) as streams:
            async with ClientSession(*streams) as session:
                logger.info("MCP client connected to server")
                await session.initialize()
                await execute_cli(session)
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