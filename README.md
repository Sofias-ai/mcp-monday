# Monday.com MCP Server

This project implements an **MCP server** that provides an **advanced interface** for interacting with **Monday.com's API** using **Model Context Protocol (MCP)**. This server enables the management of **boards, columns, and items** with intelligent validation, caching, and data transformation tools.

---

## 🚀 **Key Features**

✔ **MCP-based Interface**: Uses `mcp.server.fastmcp` to expose resources and tools.
✔ **Intelligent Validations**: Normalizes and validates data before sending it to Monday.com.
✔ **Support for Multiple Column Types**: Status, Text, Date, Email, Location, etc.
✔ **Optimized Caching**: Reduces API load on Monday.com with built-in caching.
✔ **Included Interactive Client**: Allows testing functionalities from the terminal.
✔ **Easy Integration for Clients and Agents**: Can be used by any external application.

---

## 📌 **Server Architecture**

```plaintext
┌────────────────────────┐
│      MCP Client        │  
│ (App, Agent, API, CLI) │
└────────▲───────────────┘
         │  
         │    📡 Communication via MCP
         ▼  
┌──────────────────────────────┐
│       MCP Server             │
├──────────────────────────────┤
│ - monday_server.py           │  🟢 Entry Point
│ - monday_tools.py            │  🔧 Manipulation Functions
│ - monday_resources.py        │  📚 Resources & Caching
│ - monday_column_handlers.py  │  🛠 Validations & Formatting
│ - monday_validators.py       │  ✅ Advanced Validations
│ - monday_types.py            │  🔢 Data Type Definitions
└──────────────────────────────┘
```

---

## 📂 **Project Structure**

```plaintext
📦 monday-mcp-server
 ┣ 📜 .env                  # Environment variables (API Key & Board ID)
 ┣ 📜 requirements.txt       # Project dependencies
 ┣ 📜 monday_server.py       # MCP server entry point
 ┣ 📜 monday_tools.py        # MCP tool implementations
 ┣ 📜 monday_resources.py    # Caching resources and Monday.com queries
 ┣ 📜 monday_column_handlers.py # Data manipulation and validation
 ┣ 📜 monday_validators.py   # Advanced validations
 ┣ 📜 monday_types.py        # Data type definitions
 ┣ 📜 monday_config.py       # Server and API configuration
 ┣ 📜 monday_client.py       # Interactive client for testing tools
 ┗ 📜 README.md              # Detailed documentation
```

---

## 🔧 **Installation**

1️⃣ **Clone the repository**
```bash
git clone https://github.com/sssSofiaS/mcp-monday.git
cd monday-mcp-server
```

2️⃣ **Install dependencies**
```bash
pip install -r requirements.txt
```

3️⃣ **Configure credentials** in `.env`
```plaintext
MONDAY_API_KEY=your-api-key
MONDAY_BOARD_ID=your-board-id
```

4️⃣ **Start the server**
```bash
python monday_server.py
```

---

## 📡 **How to Use the Server from a Client**

### 🔗 **Connecting an MCP Client**

Any external application can communicate with this server using MCP. 
Example connection from Python:

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
            print("Connected to Monday.com MCP server")

asyncio.run(connect_to_monday_server())
```

---

## 🔎 **Available Tools**

These are the MCP tools that can be invoked from a client:

### **1️⃣ Retrieve Board Data**
```python
response = await session.call_tool("get_board_data")
print(response.json())
```

### **2️⃣ Search for Items**
```python
response = await session.call_tool("search_board_items", {
    "field": "status_column",
    "value": "In Progress"
})
```

### **3️⃣ Create an Item**
```python
response = await session.call_tool("create_board_item", {
    "args": {
        "item_name": "New Task",
        "column_values": {
            "status_column": "In Progress",
            "date_column": "2025-02-18",
            "email_column": "contact@example.com"
        }
    }
})
```

### **4️⃣ Delete Items**
```python
response = await session.call_tool("delete_board_items", {
    "field": "status_column",
    "value": "Done"
})
```

---

## 🛠 **Debugging & Logging**

The server generates logs in `monday_server.log`. You can enable detailed logging with:
```bash
export LOG_LEVEL=DEBUG
python monday_server.py
```

---

## ❓ **FAQ**

### ❓ What do I need to use this server?
👉 Python 3.8+ and a **Monday.com** account with an API Key.

### ❓ Can I use it in production?
👉 Yes, but consider implementing authentication and access control.

### ❓ Can I add more tools?
👉 Yes, you can add functions in `monday_tools.py` following the MCP structure.

---

## 🏆 **Conclusion**

This MCP server provides a **powerful and flexible** interface for interacting with **Monday.com**. It can be used by **applications, AI agents, automation tools, and custom scripts**.
