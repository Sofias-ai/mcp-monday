from mcp.server.fastmcp import FastMCP, Context
import httpx
import os
from dotenv import load_dotenv
import logging
import sys
import json

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monday_server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('monday_server')

# Cargar variables de entorno
load_dotenv()
logger.info("Variables de entorno cargadas")

# Crear servidor MCP
mcp = FastMCP("monday-server")
logger.info("Servidor MCP creado")

# Configuración de Monday.com
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")

logger.info(f"Configuración Monday.com: URL={MONDAY_API_URL}, Board ID={MONDAY_BOARD_ID}")
logger.debug(f"API Key encontrada: {bool(MONDAY_API_KEY)}")

@mcp.tool()
async def get_board_data(ctx: Context) -> str:
    """Obtener todos los datos del tablero de Monday.com"""
    logger.info("Iniciando get_board_data")
    
    if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
        error_msg = "Falta API_KEY o BOARD_ID en las variables de entorno"
        logger.error(error_msg)
        return error_msg

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

    logger.debug(f"Query a ejecutar: {query}")

    try:
        async with httpx.AsyncClient() as client:
            logger.info("Realizando petición a Monday.com")
            response = await client.post(
                MONDAY_API_URL,
                json={"query": query},
                headers=headers
            )
            
            logger.info(f"Respuesta recibida. Status code: {response.status_code}")
            logger.debug(f"Respuesta completa: {response.text}")

            if response.status_code == 200:
                return response.text
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return error_msg
    except Exception as e:
        error_msg = f"Error en la petición: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def search_board_items(ctx: Context, field: str, value: str) -> str:
    """
    Buscar elementos en el tablero por campo y valor
    
    Args:
        field: Nombre del campo a buscar
        value: Valor a buscar en el campo
    """
    logger.info(f"Iniciando search_board_items con field={field}, value={value}")
    
    if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
        error_msg = "Falta API_KEY o BOARD_ID en las variables de entorno"
        logger.error(error_msg)
        return error_msg

    # Obtener los datos del tablero
    board_data = await get_board_data(ctx)
    
    try:
        data = json.loads(board_data)
        if "data" not in data or "boards" not in data["data"]:
            return "No se encontraron datos en el tablero"

        board = data["data"]["boards"][0]
        items = board["items_page"]["items"]
        
        # Lista para almacenar los resultados encontrados
        matching_items = []
        
        for item in items:
            # Buscar en las columnas
            for column in item["column_values"]:
                if column["text"] and (
                    (column["id"].lower() == field.lower() or 
                     field.lower() in column["id"].lower()) and 
                    value.lower() in column["text"].lower()
                ):
                    matching_items.append({
                        "id": item["id"],
                        "name": item["name"],
                        "field": column["id"],
                        "value": column["text"]
                    })
                    break
            
            # Buscar también en el nombre del item si el campo es "name"
            if field.lower() == "name" and value.lower() in item["name"].lower():
                matching_items.append({
                    "id": item["id"],
                    "name": item["name"],
                    "field": "name",
                    "value": item["name"]
                })

        if not matching_items:
            return f"No se encontraron elementos con el campo '{field}' conteniendo '{value}'"
        
        # Formatear los resultados
        results = {
            "matches_found": len(matching_items),
            "items": matching_items
        }
        
        return json.dumps(results, indent=2, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        error_msg = f"Error al procesar los datos del tablero: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error durante la búsqueda: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    import sys
    logger.info("Iniciando servidor MCP")
    if "--transport" in sys.argv and sys.argv[sys.argv.index("--transport") + 1] == "stdio":
        mcp.run(transport='stdio')
    else:
        mcp.run()