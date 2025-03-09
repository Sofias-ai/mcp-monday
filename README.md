# Monday.com MCP Server

Este proyecto implementa un **servidor MCP (Model Context Protocol)** optimizado que proporciona una **interfaz avanzada** para interactuar con la **API de Monday.com**. El servidor facilita la gestión de **tableros, columnas y elementos** con validación inteligente, caché y herramientas de transformación de datos.

---

## 🚀 **Características Principales**

✅ **Interfaz basada en MCP**: Utiliza `mcp.server.fastmcp` para exponer recursos y herramientas.

✅ **Validaciones Inteligentes**: Normaliza y valida datos antes de enviarlos a Monday.com.

✅ **Soporte para Múltiples Tipos de Columnas**: Status, Text, Date, Email, Location, etc. (33 tipos soportados).

✅ **Caché Optimizado**: Reduce la carga en la API de Monday.com con caché integrado.

✅ **Cliente Interactivo Incluido**: Permite probar las funcionalidades desde la terminal.

✅ **Arquitectura Modular**: Código dividido en módulos específicos para facilitar mantenimiento y extensibilidad.

✅ **Fácil Integración para Clientes y Agentes**: Puede ser utilizado por cualquier aplicación externa.

---

## 📌 **Arquitectura del Servidor**

```plaintext
┌────────────────────────┐
│      Cliente MCP       │  
│ (App, Agente, API, CLI)│
└────────▲───────────────┘
         │  
         │    📡 Comunicación vía MCP
         ▼  
┌───────────────────────────────────┐
│       Servidor MCP                │
├───────────────────────────────────┤
│ - monday_server.py                │  🟢 Punto de Entrada
│ - monday_tools.py                 │  🔧 Funciones de Manipulación
│ - monday_resources.py             │  📚 Recursos y Caché
│ - monday_column_handlers.py       │  🛠 Punto de Entrada para Manejadores
│ - monday_column_handlers_basic.py │  🧱 Manejadores de Tipos Básicos
│ - monday_column_handlers_advanced.│  🔥 Manejadores de Tipos Avanzados
│ - monday_validators.py            │  ✅ Validaciones Avanzadas
│ - monday_types.py                 │  🔢 Definiciones de Tipos de Datos
│ - monday_config.py                │  ⚙️ Configuración General
│ - monday_client.py                │  🖥️ Cliente Interactivo
└───────────────────────────────────┘
```

---

## 📂 **Estructura del Proyecto**

```plaintext
📦 monday-mcp-server
 ┣ 📜 .env                           # Variables de entorno (API Key y Board ID)
 ┣ 📜 requirements.txt               # Dependencias del proyecto
 ┣ 📜 monday_server.py               # Punto de entrada del servidor MCP
 ┣ 📜 monday_tools.py                # Implementación de herramientas MCP
 ┣ 📜 monday_resources.py            # Recursos en caché y consultas a Monday.com
 ┣ 📜 monday_column_handlers.py      # Punto de entrada para manejadores de columnas
 ┣ 📜 monday_column_handlers_basic.py# Manejadores para tipos básicos de columnas
 ┣ 📜 monday_column_handlers_advanced.py # Manejadores para tipos avanzados
 ┣ 📜 monday_validators.py           # Validaciones avanzadas
 ┣ 📜 monday_types.py                # Definiciones de tipos de datos
 ┣ 📜 monday_config.py               # Configuración del servidor y API
 ┣ 📜 monday_client.py               # Cliente interactivo para pruebas
 ┗ 📜 README.md                      # Documentación detallada
```

---

## 🛠️ **Componentes del Sistema**

### 1. Manejadores de Columnas

El sistema ha sido refactorizado para dividir los manejadores de columnas en dos grupos:

- **Manejadores Básicos**: 
  - `TextColumnHandler`, `LongTextColumnHandler`, `NumberColumnHandler`
  - `DateColumnHandler`, `EmailColumnHandler`, `PhoneColumnHandler`
  - `CheckboxColumnHandler`, `LinkColumnHandler`
  - Otros tipos simples para datos atómicos

- **Manejadores Avanzados**:
  - `StatusColumnHandler`, `DropdownColumnHandler` (selecciones)
  - `LocationColumnHandler`, `CountryColumnHandler` (geolocalización)
  - `FormulaColumnHandler`, `TimeTrackingColumnHandler`
  - Tipos visuales, metadatos y relaciones complejas

### 2. Sistema de Validación

- **Validadores Genéricos**: Sistema modular de validación con soporte para:
  - Validación de tipos básicos (texto, número, fecha)
  - Validación de formatos específicos (email, URL, teléfono)
  - Validación de datos complejos (coordenadas, fórmulas, relaciones)
  - Sugerencias inteligentes para valores incorrectos

### 3. Comunicación MCP

- **Recursos**: Acceso a datos de Monday.com mediante endpoints tipo REST
- **Herramientas**: Operaciones de manipulación (búsqueda, creación, eliminación)
- **Caché Inteligente**: Reduce llamadas a la API almacenando información de uso frecuente

---

## 🔧 **Instalación**

1️⃣ **Clonar el repositorio**
```bash
git clone https://github.com/sssSofiaS/mcp-monday.git
cd mcp-monday
```

2️⃣ **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3️⃣ **Configurar credenciales** en `.env`
```plaintext
MONDAY_API_KEY=tu-api-key-de-monday
MONDAY_BOARD_ID=tu-id-de-tablero
```

4️⃣ **Iniciar el servidor**
```bash
python monday_server.py
```

---

## 📡 **Uso del Servidor desde un Cliente**

### 🔗 **Conectando un Cliente MCP**

Cualquier aplicación externa puede comunicarse con este servidor usando MCP.
Ejemplo de conexión desde Python:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

async def connect_to_monday_server():
    server_params = StdioServerParameters(
        command="python",
        args=["monday_server.py", "--transport", "stdio"]
    )
    
    async with stdio_client(server_params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            print("Conectado al servidor MCP de Monday.com")

asyncio.run(connect_to_monday_server())
```

---

## 🔎 **Herramientas Disponibles**

Estas son las herramientas MCP que pueden ser invocadas desde un cliente:

### **1️⃣ Obtener Datos del Tablero**
```python
response = await session.call_tool("get_board_data")
print(response.json())
```

### **2️⃣ Buscar Elementos**
```python
response = await session.call_tool("search_board_items", {
    "args": {
        "field": "nombre_columna_status",
        "value": "En Progreso"
    }
})
```

### **3️⃣ Crear un Elemento**
```python
response = await session.call_tool("create_board_item", {
    "args": {
        "item_name": "Nueva Tarea",
        "column_values": {
            "columna_status": "En Progreso",
            "columna_fecha": "2025-03-09",  # Usa formato ISO8601 para fechas
            "columna_email": "contacto@ejemplo.com"
        }
    }
})
```

### **4️⃣ Eliminar Elementos**
```python
response = await session.call_tool("delete_board_items", {
    "args": {
        "field": "columna_status",
        "value": "Completado"
    }
})
```

---

## 🔄 **Recursos MCP Disponibles**

El servidor también expone recursos que pueden ser consumidos por clientes MCP:

### **1️⃣ Esquema del Tablero**
```python
response = await session.read_resource("monday://board/schema")
schema = json.loads(response.contents[0].text)
```

### **2️⃣ Información de Columnas**
```python
response = await session.read_resource("monday://board/columns/column_id")
column_info = json.loads(response.contents[0].text)
```

### **3️⃣ Tipos de Columnas**
```python
response = await session.read_resource("monday://board/column_types")
types = json.loads(response.contents[0].text)
```

### **4️⃣ Metadatos del Tablero**
```python
response = await session.read_resource("monday://board/metadata")
metadata = json.loads(response.contents[0].text)
```

---

## 🖥️ **Cliente Interactivo**

El proyecto incluye un cliente de línea de comandos para interactuar con el servidor:

```bash
python monday_client.py
```

El cliente muestra un menú interactivo que permite:
- Ver los datos del tablero
- Buscar elementos por campo y valor
- Crear nuevos elementos
- Eliminar elementos existentes

---

## 🛠 **Depuración y Registro**

El servidor genera logs en `monday_server.log` y `monday_client.log`. Puedes cambiar el nivel de detalle:

```bash
# En monday_client.py o monday_config.py, modifica:
logging.basicConfig(level=logging.DEBUG,  # Cambia a INFO, WARNING, ERROR según necesites
                   ...)
```

---

## ⚙️ **Mejoras Recientes**

- **División de Manejadores**: Separación en módulos básicos y avanzados para mejor mantenimiento
- **Validación Mejorada**: Nuevo sistema genérico de validación más flexible y potente
- **Optimización de Código**: Refactorización para reducir duplicación y mejorar legibilidad
- **Procesamiento de Fechas**: Mejor manejo de formatos de fecha para compatibilidad con Monday.com
- **Caché Mejorado**: Sistema de caché más eficiente para reducir llamadas a la API

---

## 📋 **Guía de Resolución de Problemas**

### Problemas comunes y soluciones:

1. **Error de formato de fecha**:
   - Asegúrate de usar formato ISO8601 (YYYY-MM-DD) para fechas
   - Ejemplo: `2025-03-09` en lugar de `09/03/2025`

2. **Columnas no encontradas**:
   - Verifica que los IDs de columna sean correctos usando `monday://board/schema`
   - Los IDs tienen formato como `text_mknk13m2` o `status_mknkkbmd`

3. **Valores de columna rechazados**:
   - Consulta las reglas de validación con `monday://board/columns/{column_id}`
   - Para columnas de status, debe ser un valor exacto de las opciones disponibles

4. **Problemas de conexión**:
   - Asegúrate de tener API_KEY válida en .env
   - Verifica conectividad a api.monday.com

---