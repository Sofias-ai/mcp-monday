import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import logging
import json
import sys

# Configurar logging
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
    """Mostrar menú de herramientas disponibles"""
    print("\nHerramientas disponibles:")
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}: {tool.description or 'No hay descripción disponible'}")
    print("0. Salir")

async def get_tool_parameters(tool_name):
    """Obtener parámetros para una herramienta específica"""
    if tool_name == "search_board_items":
        print("\nIntroduce los parámetros separados por coma:")
        print("Formato: nombre_campo,valor_buscar")
        params = input("> ").strip().split(',')
        if len(params) != 2:
            print("Error: Se requieren exactamente 2 parámetros (nombre_campo,valor_buscar)")
            return None
        return {
            "field": params[0].strip(),
            "value": params[1].strip()
        }
    return {}

async def execute_tool(session, tool, params):
    """Ejecutar una herramienta y mostrar sus resultados"""
    try:
        result = await session.call_tool(tool.name, params)
        if result and result.content:
            for content in result.content:
                if content.type == "text":
                    try:
                        json_data = json.loads(content.text)
                        formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
                        print(f"\nRespuesta del servidor:\n{formatted_json}")
                    except json.JSONDecodeError:
                        print(f"\nRespuesta del servidor:\n{content.text}")
    except Exception as e:
        logger.error(f"Error al ejecutar la herramienta: {str(e)}")
        print(f"Error al ejecutar la herramienta: {str(e)}")

async def interactive_loop(session):
    """Bucle interactivo principal"""
    while True:
        try:
            # Obtener lista de herramientas
            response = await session.list_tools()
            tools = response.tools
            
            # Mostrar menú
            await display_tool_menu(tools)
            
            # Obtener selección del usuario
            choice = input("\nSelecciona una opción: ").strip()
            if choice == "0":
                break
                
            try:
                tool_index = int(choice) - 1
                if 0 <= tool_index < len(tools):
                    selected_tool = tools[tool_index]
                    # Obtener parámetros si son necesarios
                    params = await get_tool_parameters(selected_tool.name)
                    if params is not None:
                        # Ejecutar la herramienta
                        await execute_tool(session, selected_tool, params)
                else:
                    print("Opción no válida")
            except ValueError:
                print("Por favor, introduce un número válido")
                
        except Exception as e:
            logger.error(f"Error en el bucle interactivo: {str(e)}")
            print(f"Error: {str(e)}")

async def main():
    try:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["monday_server.py", "--transport", "stdio"]
        )

        async with stdio_client(server_params) as streams:
            read_stream, write_stream = streams
            try:
                async with ClientSession(read_stream, write_stream) as session:
                    logger.info("Cliente MCP conectado al servidor.")
                    await session.initialize()
                    logger.info("Sesión inicializada")
                    
                    # Iniciar bucle interactivo
                    await interactive_loop(session)
                    
            except Exception as e:
                logger.error(f"Error durante la sesión: {str(e)}")
            finally:
                logger.info("Cerrando sesión...")
    except Exception as e:
        logger.error(f"Error general: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma terminado por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}")
        print(f"Error fatal: {str(e)}")