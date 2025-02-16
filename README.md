# Monday.com MCP Client

Cliente MCP para interactuar con Monday.com a través de su API GraphQL.

## Requisitos

- Python 3.8 o superior
- Token de API de Monday.com
- ID del tablero de Monday.com

## Instalación

1. Clona este repositorio
2. Crea y activa el entorno virtual:
```bash
python -m venv mcpMondayVenv
# En Windows:
mcpMondayVenv\Scripts\activate
# En Linux/Mac:
source mcpMondayVenv/bin/activate
```
3. Instala las dependencias:
```bash
pip install -r requirements.txt
```
4. Copia el archivo `.env.example` a `.env` y configura tus credenciales:
```properties
MONDAY_API_KEY=tu_api_key
MONDAY_BOARD_ID=tu_board_id
```

## Uso

1. Inicia el servidor:
```bash
python monday_server.py --transport stdio
```

2. En otra terminal, inicia el cliente:
```bash
python monday_client.py
```

## Herramientas disponibles

- `get_board_data`: Obtiene todos los datos del tablero configurado
- `search_board_items`: Busca elementos en el tablero por campo y valor

## Logs

Los logs se almacenan en:
- `monday_server.log` para el servidor
- `monday_client.log` para el cliente
