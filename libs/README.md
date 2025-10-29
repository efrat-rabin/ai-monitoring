# Shared Libraries

Common libraries for AI monitoring actions located in the root `libs` directory.

## CursorClient

Simple client class for sending messages to Cursor CLI.

### Class: `CursorClient`

#### Constructor

```python
CursorClient(api_key: Optional[str] = None)
```

Initialize Cursor client.

**Args:**
- `api_key`: Cursor API key (defaults to CURSOR_API_KEY env var)

**Raises:**
- `ValueError`: If CURSOR_API_KEY is not set

#### Method: `install_cursor_cli`

```python
install_cursor_cli() -> bool
```

Install Cursor CLI if not already installed.

**Returns:**
- `True` if installation successful or already installed, `False` otherwise

#### Method: `verify_setup`

```python
verify_setup() -> bool
```

Verify cursor-agent is available and API key is set.

**Returns:**
- `True` if setup is valid, `False` otherwise

#### Method: `send_message`

```python
send_message(prompt: str, context: Optional[str] = None) -> Any
```

Send a message to Cursor CLI and get response.

**Args:**
- `prompt`: The prompt/question to send
- `context`: Optional context to include with the prompt

**Returns:**
- Parsed response from Cursor (dict, str, or original response)

**Raises:**
- `Exception`: If Cursor CLI is not available or call fails

### Usage

```python
import sys
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs"))
from cursor_client import CursorClient

# Create client
cursor = CursorClient()

# Install CLI if needed
if not cursor.install_cursor_cli():
    print("Failed to install Cursor CLI")
    exit(1)

# Verify setup
if not cursor.verify_setup():
    print("Setup verification failed")
    exit(1)

# Send a message
try:
    response = cursor.send_message("Analyze this log line", context='{"level":"error"}')
    print(response)
except Exception as e:
    print(f"Error: {e}")
```

### Environment Variables

- `CURSOR_API_KEY` - Required for authentication

### Requirements

- Cursor CLI must be installed (`cursor-agent` command available)
- Set `CURSOR_API_KEY` environment variable
