"""Tool JSON schemas for sub-agent tool definitions.

These schemas are provided to the LLM so it knows how to invoke tools.
Path arguments must be relative to the project root directory.
"""

TOOL_SCHEMAS: dict[str, dict] = {
    "read": {
        "name": "read",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path to the file to read. Must be relative to the "
                        "project root directory. Absolute paths and paths "
                        "containing '..' or '~' are not allowed."
                    ),
                },
            },
            "required": ["path"],
        },
    },
    "write": {
        "name": "write",
        "description": "Write content to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path to the file to write. Must be relative to the "
                        "project root directory. Absolute paths and paths "
                        "containing '..' or '~' are not allowed."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
    "list": {
        "name": "list",
        "description": "List files and directories at a given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path to the directory to list. Must be relative to "
                        "the project root directory. Absolute paths and paths "
                        "containing '..' or '~' are not allowed."
                    ),
                },
            },
            "required": ["path"],
        },
    },
    "ask_user": {
        "name": "ask_user",
        "description": "Ask the user a question and wait for a response.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user.",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of option strings for the user to choose from.",
                },
            },
            "required": ["question"],
        },
    },
}
