#!/usr/bin/env python3
"""
Apple Notes MCP Server
Provides read/write access to Apple Notes via AppleScript
"""

import subprocess
import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


app = Server("apple-notes-mcp")


def run_applescript(script: str) -> str:
    """Execute AppleScript and return the result"""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def run_jxa(script: str) -> str:
    """Execute JavaScript for Automation and return the result"""
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="list_notes",
            description="List all notes with their names, folders, and creation/modification dates",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Optional: filter by folder name"
                    }
                }
            }
        ),
        Tool(
            name="search_notes",
            description="Search notes by text in title or body",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find in note titles or content"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="read_note",
            description="Read the full content of a specific note by name or ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name/title of the note to read"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="create_note",
            description="Create a new note with specified content",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The title of the new note"
                    },
                    "body": {
                        "type": "string",
                        "description": "The content of the new note"
                    },
                    "folder": {
                        "type": "string",
                        "description": "Optional: folder to create the note in (defaults to 'Notes')"
                    }
                },
                "required": ["name", "body"]
            }
        ),
        Tool(
            name="edit_note",
            description="Edit an existing note's content",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name/title of the note to edit"
                    },
                    "body": {
                        "type": "string",
                        "description": "The new content for the note"
                    }
                },
                "required": ["name", "body"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""

    if name == "list_notes":
        # List all notes with metadata
        folder_filter = arguments.get("folder", "")

        script = """
        tell application "Notes"
            set notesList to {}
            set allNotes to every note
            repeat with aNote in allNotes
                set noteInfo to {|name|:name of aNote, |folder|:name of container of aNote, |creationDate|:creation date of aNote as string, |modificationDate|:modification date of aNote as string}
                set end of notesList to noteInfo
            end repeat
            return notesList
        end tell
        """

        try:
            result = run_applescript(script)
            # Parse the AppleScript result
            notes = []
            # AppleScript returns in format: name:xxx, folder:yyy, creationDate:zzz, modificationDate:www
            if result:
                # Split by note records (this is a simplification)
                lines = result.split(", |name|:")
                for line in lines:
                    if line.strip():
                        notes.append(line.strip())

            if folder_filter:
                result_text = f"Notes in folder '{folder_filter}':\n{result}"
            else:
                result_text = f"All notes:\n{result}"

            return [TextContent(type="text", text=result_text)]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=f"Error listing notes: {e.stderr}")]

    elif name == "search_notes":
        query = arguments["query"]

        # Use JXA for better JSON handling
        script = f"""
        const notes = Application('Notes');
        const allNotes = notes.notes();
        const results = [];

        for (let note of allNotes) {{
            const name = note.name();
            const body = note.body();

            if (name.toLowerCase().includes('{query.lower()}') ||
                body.toLowerCase().includes('{query.lower()}')) {{
                results.push({{
                    name: name,
                    folder: note.container().name(),
                    preview: body.substring(0, 200)
                }});
            }}
        }}

        JSON.stringify(results);
        """

        try:
            result = run_jxa(script)
            matches = json.loads(result) if result else []

            if not matches:
                return [TextContent(type="text", text=f"No notes found matching '{query}'")]

            formatted = f"Found {len(matches)} note(s) matching '{query}':\n\n"
            for match in matches:
                formatted += f"• {match['name']} (in {match['folder']})\n"
                formatted += f"  Preview: {match['preview'][:100]}...\n\n"

            return [TextContent(type="text", text=formatted)]
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            return [TextContent(type="text", text=f"Error searching notes: {str(e)}")]

    elif name == "read_note":
        note_name = arguments["name"]

        script = f"""
        tell application "Notes"
            set matchingNotes to (every note whose name is "{note_name}")
            if (count of matchingNotes) > 0 then
                set theNote to item 1 of matchingNotes
                return body of theNote
            else
                return "Note not found"
            end if
        end tell
        """

        try:
            result = run_applescript(script)
            return [TextContent(type="text", text=f"Note: {note_name}\n\n{result}")]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=f"Error reading note: {e.stderr}")]

    elif name == "create_note":
        note_name = arguments["name"]
        note_body = arguments["body"]
        folder_name = arguments.get("folder", "Notes")

        # Escape quotes in the content
        note_name_escaped = note_name.replace('"', '\\"')
        note_body_escaped = note_body.replace('"', '\\"')

        script = f"""
        tell application "Notes"
            tell account "iCloud"
                -- Try to find the folder, create if it doesn't exist
                set targetFolder to folder "{folder_name}"

                -- Create the note
                set newNote to make new note at targetFolder with properties {{name:"{note_name_escaped}", body:"{note_body_escaped}"}}
                return name of newNote
            end tell
        end tell
        """

        try:
            result = run_applescript(script)
            return [TextContent(type="text", text=f"Successfully created note: {result}")]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=f"Error creating note: {e.stderr}")]

    elif name == "edit_note":
        note_name = arguments["name"]
        note_body = arguments["body"]

        # Escape quotes in the content
        note_body_escaped = note_body.replace('"', '\\"')

        script = f"""
        tell application "Notes"
            set matchingNotes to (every note whose name is "{note_name}")
            if (count of matchingNotes) > 0 then
                set theNote to item 1 of matchingNotes
                set body of theNote to "{note_body_escaped}"
                return "Note updated: " & name of theNote
            else
                return "Note not found"
            end if
        end tell
        """

        try:
            result = run_applescript(script)
            return [TextContent(type="text", text=result)]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=f"Error editing note: {e.stderr}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
