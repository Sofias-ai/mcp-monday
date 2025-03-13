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
   
   You can get your API key in Monday.com → Profile → Developer → API

## ⚙️ Project Structure

- `monday_config.py`: Configuration and initialization of MCP and Monday.com
- `monday_server.py`: MCP server for Monday.com
- `monday_tools.py`: MCP tools to operate with Monday.com
- `monday_resources.py`: MCP resources to query Monday.com data

## 🚀 Usage

### Start the server

```bash
python monday_server.py
```

## 🛠️ Available Tools

The system offers the following MCP tools:

1. **get_board_data**: Gets all data from the board, including columns and items
   
2. **search_board_items**: Searches for items in the board by field and value
   - Parameters: `field` (field name/ID), `value` (value to search for)
   
3. **delete_board_items**: Deletes items from the board that match a field and value
   - Parameters: `field` (field name/ID), `value` (value to search for)
   
4. **create_board_item**: Creates a new item in the board
   - Parameters: `item_name` (name of the item), `column_values` (values for columns), `group_id` (optional)
   
5. **update_board_item**: Updates an existing item
   - Parameters: `item_id` (item ID), `column_values` (values to update)

## 📚 Available Resources

- `monday://board/schema`: Complete board schema
- `monday://board/columns/{column_id}`: Information about a specific column
- `monday://board/items`: All items in the board
- `monday://board/item/{item_id}`: Details of a specific item

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
- The server is running
- Environment variables are correctly configured
- Your Monday.com API key has the necessary permissions

## 📝 Development

This project uses:
- **MCP** for server and client interface
- **Monday Python SDK** to interact with the Monday.com API
- **Python-dotenv** for configuration management
- **Requests** for HTTP communication

To extend or modify the project, review the main files and their modular structure.

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
````
