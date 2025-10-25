# Apple Notes MCP Server

MCP server providing read/write access to Apple Notes via AppleScript.

## Features

- List, search, read, create, and edit notes
- No Full Disk Access required
- Works with all Apple Notes folders
- Fully local execution

## Installation

```bash
git clone https://github.com/yourusername/apple-notes-mcp.git
cd apple-notes-mcp
uv venv
uv pip install -e .
```

## Usage

Add to Claude Code:

```bash
claude mcp add --scope user --transport stdio apple-notes -- /path/to/apple-notes-mcp/.venv/bin/python -m apple_notes_mcp.server
```

Or with `uv`:

```bash
claude mcp add --scope user --transport stdio apple-notes -- uv run --directory /path/to/apple-notes-mcp python -m apple_notes_mcp.server
```

## Available Tools

| Tool | Description |
|------|-------------|
| `list_notes` | List all notes with metadata |
| `search_notes` | Search notes by text |
| `read_note` | Read full note content |
| `create_note` | Create a new note |
| `edit_note` | Update existing note |

## Requirements

- macOS with Apple Notes
- Python 3.10+
- `uv` package manager

## License

MIT
