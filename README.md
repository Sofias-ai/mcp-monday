# Monday.com MCP Integration

Una integración entre Monday.com y el protocolo MCP (Model Control Protocol) que permite gestionar y consultar tableros de Monday.com a través de una interfaz estandarizada.

## 📋 Requisitos

- Python 3.9+
- Una cuenta en Monday.com con una clave API
- Un tablero existente en Monday.com

## 🔧 Instalación

1. Clona este repositorio o descarga los archivos
2. Crea un entorno virtual:
   ```bash
   python -m venv mcpMondayVenv
   ```
3. Activa el entorno virtual:
   ```bash
   # En Windows
   mcpMondayVenv\Scripts\activate
   
   # En Unix/macOS
   source mcpMondayVenv/bin/activate
   ```
4. Ejecuta el script de configuración o instala las dependencias manualmente:
   ```bash
   # Opción 1: Usar el script de configuración
   python setup.py
   
   # Opción 2: Instalar dependencias manualmente
   pip install -r requirements.txt
   ```

5. Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:
   ```
   MONDAY_API_KEY=tu_api_key_de_monday
   MONDAY_BOARD_ID=id_de_tu_tablero
   ```
   
   Puedes obtener tu API key en Monday.com → Perfil → Developer → API

## ⚙️ Estructura del proyecto

- `monday_config.py`: Configuración y inicialización de MCP y Monday.com
- `monday_server.py`: Servidor MCP para Monday.com
- `monday_client.py`: Cliente interactivo para interactuar con el servidor
- `monday_tools.py`: Herramientas MCP para operar con Monday.com
- `monday_resources.py`: Recursos MCP para consultar datos de Monday.com

## 🚀 Uso

### Iniciar el servidor

```bash
python monday_server.py
```

### Iniciar el cliente

En otra terminal:

```bash
python monday_client.py
```

El cliente proporciona una interfaz interactiva para utilizar las herramientas disponibles.

## 🛠️ Herramientas disponibles

El sistema ofrece las siguientes herramientas MCP:

1. **get_board_data**: Obtiene todos los datos del tablero, incluyendo columnas e ítems
   
2. **search_board_items**: Busca ítems en el tablero por campo y valor
   - Parámetros: `field` (nombre/ID del campo), `value` (valor a buscar)
   
3. **delete_board_items**: Elimina ítems del tablero que coincidan con un campo y valor
   - Parámetros: `field` (nombre/ID del campo), `value` (valor a buscar)
   
4. **create_board_item**: Crea un nuevo ítem en el tablero
   - Parámetros: `item_name` (nombre del ítem), `column_values` (valores para columnas), `group_id` (opcional)
   
5. **update_board_item**: Actualiza un ítem existente
   - Parámetros: `item_id` (ID del ítem), `column_values` (valores a actualizar)

## 📚 Recursos disponibles

- `monday://board/schema`: Esquema completo del tablero
- `monday://board/columns/{column_id}`: Información de una columna específica
- `monday://board/items`: Todos los ítems del tablero
- `monday://board/item/{item_id}`: Detalles de un ítem específico

## ❓ Solución de problemas

### Error: ModuleNotFoundError: No module named 'requests'

Asegúrate de tener todas las dependencias instaladas:

```bash
pip install requests monday python-dotenv mcp
```

O instala todas las dependencias desde el archivo de requisitos:

```bash
pip install -r requirements.txt
```

### Error de conexión al servidor

Verifica que:
- El servidor esté en ejecución
- Las variables de entorno estén correctamente configuradas
- La API key de Monday.com tenga los permisos necesarios

## 📝 Desarrollo

Este proyecto utiliza:
- **MCP** para la interfaz del servidor y cliente
- **Monday Python SDK** para interactuar con la API de Monday.com
- **Python-dotenv** para la gestión de configuración
- **Requests** para comunicación HTTP

Para extender o modificar el proyecto, revisa los archivos principales y su estructura modular.