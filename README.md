
# Clickupy: Python Client for ClickUp API v2

A Python library providing an object-oriented interface to interact with the ClickUp API v2. This library aims to simplify common operations like managing workspaces, spaces, folders, lists, and tasks.

## Features

- **Object-Oriented:** Interact with ClickUp resources (Workspaces, Spaces, Folders, Lists, Tasks) as Python objects.
- **Hierarchy Management:** Easily navigate and manage the ClickUp hierarchy (Workspace -> Space -> Folder -> List -> Task).
- **Core CRUD Operations:** Create, Read (Get), Update, Delete operations for major resources where applicable via the API.
- **Task Management:**
  - Create tasks within lists.
  - List tasks with filtering and automatic pagination support (`get_all=True`).
  - Update task details (name, description, status, priority, dates, etc.).
  - Assign/Unassign users by ID or **Name** (with ambiguity handling).
  - Add/Get task comments.
  - Add/Remove task tags (by name).
  - Add/Remove task watchers (by ID or Name).
  - Create subtasks.
  - Add/Remove task dependencies.
- **User Resolution:** Find users within a List context by name or email fragment for assignments/watchers, raising specific exceptions (`UserNotFoundByNameError`, `AmbiguousUserNameError`) on failure.
- **Rate Limiting:** Includes a built-in delay (`time.sleep`) between requests to help avoid rate limits.
- **Caching:** Basic caching for list members, spaces, folders, and lists to reduce redundant API calls.

## Installation

```bash
pip install clickupy
```

### Requirements

- Python 3.8+
- `requests`
- `python-dotenv` (for loading API key from .env file)

Install requirements:

```bash
pip install requests python-dotenv
```

## Configuration

Obtain your Personal API Token from your ClickUp account settings (Settings -> Apps).

Create a file named `.env` in the root directory of your project.

Add your API token to the `.env` file:

```env
CLICKUP_TOKEN=pk_YOUR_PERSONAL_API_TOKEN_HERE
```

The library will automatically load the token from this environment variable. Alternatively, you can pass the token directly when initializing the client:

```python
from clickupy.client import ClickUpClient
client = ClickUpClient(token="pk_YOUR_PERSONAL_API_TOKEN_HERE")
```

## Quick Start

```python
import os
from dotenv import load_dotenv
from clickupy.client import ClickUpClient
from clickupy.team import Team

load_dotenv()

try:
    client = ClickUpClient()
    print("Client initialized.")
except ValueError as e:
    print(f"Error: {e}")
    exit()

team_manager = Team(client)

workspace_name = "Your Target Workspace Name"  # <-- CHANGE THIS
my_workspace = team_manager.get_workspace(workspace_name)

if my_workspace:
    print(f"Found Workspace: {my_workspace.name} (ID: {my_workspace.id})")
    print("\nListing spaces...")
    spaces = my_workspace.list_spaces()
    if spaces:
        for space in spaces:
            print(f" - Space: {space.name} (ID: {space.id})")
    else:
        print("No spaces found in this workspace.")
else:
    print(f"Workspace '{workspace_name}' not found.")
```

## Error Handling

The library uses custom exceptions for specific known issues found in the `clickupy.exceptions` module:

- `UserNotFoundByNameError`: Raised during name resolution if a provided name query does not match any user.
- `AmbiguousUserNameError`: Raised if a provided name query matches multiple users. Includes details of matches found.
- `ClickupyException`: Base exception for other library-specific errors.

Example:

```python
from clickupy.exceptions import UserNotFoundByNameError, AmbiguousUserNameError

try:
    my_list.create_task(name="Test Ambiguity", assignees=["admin"])
except AmbiguousUserNameError as e:
    print(f"Assignment failed: {e}")
    print("Please use a more specific name or the User ID.")
except UserNotFoundByNameError as e:
    print(f"Assignment failed: User '{e.name_query}' not found in list '{e.list_id}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
```

## Rate Limiting

A default delay of 0.65 seconds is automatically added before each API request in `ClickUpClient.request` to help prevent hitting standard ClickUp API rate limits.

## Contributing

(Add contribution guidelines here if applicable)

## License

(Specify your chosen license here, e.g., MIT License, Apache 2.0)
