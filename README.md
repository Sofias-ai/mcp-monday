# Monday.com MCP Integration

An integration between Monday.com and the MCP (Model Control Protocol) that allows managing and querying Monday.com boards through a standardized interface.

## 📋 Requirements

- Python 3.9+
- A Monday.com account with an API key
- An existing board in Monday.com

## 🔧 Installation

1. Clone this repository or download the files
2. Create a virtual environment:
   ```bash
   python -m venv mcpMondayVenv
   ```
3. Activate the virtual environment:
   ```bash
   # On Windows
   mcpMondayVenv\Scripts\activate
   
   # On Unix/macOS
   source mcpMondayVenv/bin/activate
   ```
4. Run the setup script or install dependencies manually:
   ```bash
   # Option 1: Use the setup script
   python setup.py
   
   # Option 2: Install dependencies manually
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root with the following content:
   ```
   MONDAY_API_KEY=your_monday_api_key
   MONDAY_BOARD_ID=your_board_id
   ```
   
   You can get your API key in Monday.com → Profile → Developer → API → API v2 Token

## ⚙️ Project Structure

- `monday_config.py`: Configuration and initialization of MCP and Monday.com
- `monday_server.py`: MCP server for Monday.com
- `monday_tools.py`: MCP tools to operate with Monday.com
- `monday_resources.py`: MCP resources to query Monday.com data

## 🚀 Usage

### Start the server

You can run the server using different transport methods:

```bash
# Default (stdio)
python monday_server.py

# Explicitly specify transport
python monday_server.py --transport stdio
python monday_server.py --transport sse
```

## ✨ Features

- **Optimized GraphQL Queries**: Direct GraphQL queries for better performance
- **Smart Caching System**: 5-minute time-based cache to minimize API calls
- **Fallback Mechanisms**: Graceful degradation when GraphQL queries fail
- **Comprehensive Error Handling**: Consistent error responses across all functions
- **Windows Compatibility**: Built-in handling of Windows-specific encoding issues

## 🛠️ Available Tools

The MCP integration offers these tools for interacting with Monday.com:

1. **get_board_schema** - Get the structure of the board (columns, groups, etc.) without items
   - Returns detailed information about columns, including dropdown options

2. **get_board_items** - Get only the items from the board
   - Retrieves all items with their column values efficiently

3. **get_board_data** - Combined schema and items in one call
   - Use with caution on large boards as it retrieves all data

4. **search_board_items** - Search for items by field and value
   - Parameters: `field` (field name/ID), `value` (value to search for)
   - Supports searching by column title or ID

5. **delete_board_items** - Delete items matching a field and value
   - Parameters: `field` (field name/ID), `value` (value to search for)
   - Returns detailed information about deleted items and any errors

6. **create_board_item** - Create a new item in the board
   - Parameters: `item_name` (name of the item), `column_values` (values for columns), `group_id` (optional)
   - Automatically uses first group if group_id not provided

7. **update_board_item** - Update an existing item
   - Parameters: `item_id` (item ID), `column_values` (values to update)

## 📚 Available Resources

The server provides these resources that can be accessed through the MCP protocol:

- `monday://board/schema` - Complete board schema
- `monday://board/columns` - All columns in the board 
- `monday://board/columns/{column_id}` - Information about a specific column
- `monday://board/items` - All items in the board
- `monday://board/item/{item_id}` - Details of a specific item

## 🏎️ Performance Optimizations

This integration includes several performance-enhancing features:

1. **Resource Caching**: All resources are cached for 5 minutes to reduce API calls
2. **GraphQL-First Approach**: Uses optimized GraphQL queries for better performance
3. **Fallback Mechanisms**: Automatically falls back to standard API when GraphQL fails
4. **Error Resilience**: Continues operation even when parts of the data can't be retrieved

## ❓ Troubleshooting

### Error: ModuleNotFoundError: No module named 'requests'

Make sure you have all dependencies installed:

```bash
pip install requests monday python-dotenv mcp
```

Or install all dependencies from the requirements file:

```bash
pip install -r requirements.txt
```

### Server connection error

Verify that:
- The server is running (check the logs in monday_server.log)
- Environment variables are correctly configured in .env
- Your Monday.com API key has the necessary permissions
- The board ID exists and is accessible with your API key

### Windows encoding issues

If you encounter encoding problems on Windows, the server automatically configures binary mode and UTF-8 encoding for stdin/stdout. If problems persist, check your terminal's encoding settings.

## 📝 Development

This project uses:
- **MCP** for server and client interface
- **Monday Python SDK** to interact with the Monday.com API
- **Python-dotenv** for configuration management
- **Custom GraphQL queries** for optimized data retrieval

### Extending the integration

To add new capabilities:
1. Add GraphQL queries in `monday_resources.py` if needed
2. Implement new tool functions in `monday_tools.py`
3. Create resource endpoints in `monday_resources.py` if necessary

## 🏢 About

This server has been developed by [Sofias Tech](https://github.com/Sofias-ai), a company specializing in integration and automation solutions for productivity platforms.

This project represents one of the first open-source codes published by our company. Visit our [GitHub repository](https://github.com/Sofias-ai) to discover more tools and solutions.

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT) - see the LICENSE file for details.

```
MIT License

Copyright (c) 2023 Sofias Tech

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
