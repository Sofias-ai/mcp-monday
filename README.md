# Monday.com MCP Client

MCP Client for interacting with Monday.com through its GraphQL API.

## Requirements

- Python 3.8 or higher
- Monday.com API Token
- Monday.com Board ID

## Installation

1. Clone this repository
2. Create and activate virtual environment:
```bash
python -m venv mcpMondayVenv
# On Windows:
mcpMondayVenv\Scripts\activate
# On Linux/Mac:
source mcpMondayVenv/bin/activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Copy `.env.example` to `.env` and configure your credentials:
```properties
MONDAY_API_KEY=your_api_key
MONDAY_BOARD_ID=your_board_id
```

## Server Tools

The server provides the following tools for interacting with Monday.com:

### Available Tools

1. `get_board_data`
   - Gets all data from the configured board
   - No parameters required

2. `search_board_items`
   - Searches for items in the board by field and value
   - Parameters: 
     - `field`: Field name to search
     - `value`: Value to search for

3. `delete_board_items`
   - Deletes items from the board that match a specific field and value
   - Parameters:
     - `field`: Field name to match
     - `value`: Value to match

4. `create_board_item`
   - Creates a new item in the board
   - Parameters:
     - `values`: Comma-separated values in order:
       name,date,email,type,priority,location,description,text,area,category

## Logs

Logs are stored in:
- `monday_server.log` for server logs
